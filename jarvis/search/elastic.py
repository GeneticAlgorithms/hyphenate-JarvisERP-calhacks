"""Elastic backend: per-kind indices, semantic_text when an inference endpoint exists, RRF hybrid queries,
an ES|QL helper, and an append-only audit mirror.

Runtime uses the *role* key (JARVIS_PREPARER_KEY) when present; the master key is only a fallback
for local development. `python -m jarvis.search.mint_keys` creates the restricted role keys.
"""
from __future__ import annotations

from elasticsearch import Elasticsearch, helpers

from jarvis import config

KINDS = ("doc", "precedent", "record", "vendor", "policy")


def idx(kind: str) -> str:
    return f"{config.ELASTIC_PREFIX}-{kind}s"


class ElasticBackend:
    name = "elastic"

    def __init__(self, api_key: str | None = None):
        key = api_key or config.ROLE_KEYS.get("ai_agent") or config.ELASTIC_API_KEY
        self.es = Elasticsearch(config.ELASTIC_URL, api_key=key, request_timeout=20)
        self.semantic = False
        self._ready = False

    def ping(self) -> bool:
        try:
            self.es.info()
        except Exception:
            return False
        self._ensure()
        return True

    def _inference_available(self) -> bool:
        mode = (config.env("JARVIS_ELASTIC_SEMANTIC", "auto") or "auto").lower()
        if mode == "off":
            return False
        try:
            eps = self.es.inference.get().body.get("endpoints", [])
        except Exception:
            return False
        return bool(eps) if mode in ("auto", "on") else False

    def _ensure(self):
        if self._ready:
            return
        self.semantic = self._inference_available()
        for kind in KINDS + ("audit",):
            name = idx(kind)
            if self.es.indices.exists(index=name):
                if kind != "audit":
                    m = self.es.indices.get_mapping(index=name).body
                    props = m[name]["mappings"].get("properties", {})
                    self.semantic = self.semantic and "text_sem" in props
                continue
            props = {"kind": {"type": "keyword"}, "id": {"type": "keyword"}, "meta": {"type": "object", "dynamic": True},
                     "text": {"type": "text"}}
            if kind == "audit":
                props = {"seq": {"type": "long"}, "at": {"type": "date"}, "actor": {"type": "keyword"},
                         "actor_role": {"type": "keyword"}, "action": {"type": "keyword"},
                         "subject": {"type": "keyword"}, "allowed": {"type": "boolean"}, "reason": {"type": "text"},
                         "hash": {"type": "keyword"}, "prev_hash": {"type": "keyword"}}
            elif self.semantic:
                props["text"]["copy_to"] = "text_sem"
                props["text_sem"] = {"type": "semantic_text"}
            body = {"mappings": {"properties": props}}
            if kind == "vendor":
                body["settings"] = {"index": {"mode": "lookup"}}
            try:
                self.es.indices.create(index=name, **body)
            except Exception:
                body.pop("settings", None)
                self.es.indices.create(index=name, **body)
        self._ready = True

    def bulk(self, items: list[tuple]):
        actions = ({"_index": idx(kind), "_id": doc_id,
                    "_source": {"kind": kind, "id": doc_id, "text": text, "meta": meta}} for kind, doc_id, text, meta in items)
        helpers.bulk(self.es, actions, refresh="wait_for")

    def search(self, query: str, kind: str | None, k: int, filters: dict | None) -> list[dict]:
        index = idx(kind) if kind else ",".join(idx(x) for x in KINDS)
        filt = [{"term": {f"meta.{fk}": fv}} for fk, fv in (filters or {}).items()]
        lexical = {"bool": {"must": [{"match": {"text": query}}], "filter": filt}}
        if self.semantic:
            body = {"retriever": {"rrf": {"retrievers": [
                {"standard": {"query": lexical}},
                {"standard": {"query": {"bool": {"must": [{"semantic": {"field": "text_sem", "query": query}}],
                                                 "filter": filt}}}}]}},
                "size": k, "highlight": {"fields": {"text": {}}}}
        else:
            body = {"query": lexical, "size": k, "highlight": {"fields": {"text": {}}}}
        res = self.es.search(index=index, **body)
        out = []
        for h in res["hits"]["hits"]:
            s = h["_source"]
            hl = " … ".join(h.get("highlight", {}).get("text", [])).replace("<em>", "«").replace("</em>", "»")
            out.append({"kind": s["kind"], "id": s["id"], "score": round(h.get("_score") or 0, 3), "meta": s.get("meta", {}),
                        "highlight": hl or s["text"][:160], "backend": "elastic" + ("+semantic" if self.semantic else "")})
        return out

    def esql(self, query: str, params: list | None = None) -> dict:
        return self.es.esql.query(query=query, params=params or []).body

    def mirror_audit(self, rows: list[dict]):
        actions = ({"_index": idx("audit"), "_id": str(r["seq"]), "op_type": "create",
                    "_source": {k: r.get(k) for k in ("seq", "at", "actor", "actor_role", "action", "subject", "allowed",
                                                       "reason", "hash", "prev_hash")}} for r in rows)
        helpers.bulk(self.es, actions, raise_on_error=False)
