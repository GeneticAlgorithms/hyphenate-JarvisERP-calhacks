"""Retrieval layer. Elastic when configured (hybrid lexical + semantic), local BM25 otherwise.

Search narrows the haystack; deterministic code decides. Every query is logged with the backend
that served it, so the evidence trail says exactly where a candidate came from.
"""
from __future__ import annotations

import math
import re
from collections import Counter, defaultdict

from jarvis import config

_TOKEN = re.compile(r"[a-z0-9]+")


def tokens(s: str) -> list[str]:
    return _TOKEN.findall((s or "").lower())


class LocalSearch:
    name = "local-bm25"

    def __init__(self):
        self.docs: dict[str, dict] = {}
        self.df: Counter = Counter()
        self.tf: dict[str, Counter] = {}
        self.len: dict[str, int] = {}

    def index(self, kind: str, doc_id: str, text: str, meta: dict | None = None):
        key = f"{kind}:{doc_id}"
        if key in self.docs:
            for t in self.tf[key]:
                self.df[t] -= 1
        toks = tokens(text)
        self.docs[key] = {"kind": kind, "id": doc_id, "text": text, "meta": meta or {}}
        self.tf[key] = Counter(toks)
        self.len[key] = len(toks) or 1
        for t in self.tf[key]:
            self.df[t] += 1

    def search(self, query: str, kind: str | None = None, k: int = 10, filters: dict | None = None) -> list[dict]:
        q = tokens(query)
        if not q:
            return []
        n = len(self.docs) or 1
        avg = sum(self.len.values()) / n
        scores = defaultdict(float)
        for key, tf in self.tf.items():
            d = self.docs[key]
            if kind and d["kind"] != kind:
                continue
            if filters and any(d["meta"].get(fk) != fv for fk, fv in filters.items()):
                continue
            for t in q:
                if t in tf:
                    idf = math.log(1 + (n - self.df[t] + 0.5) / (self.df[t] + 0.5))
                    f = tf[t]
                    scores[key] += idf * f * 2.2 / (f + 1.2 * (0.25 + 0.75 * self.len[key] / avg))
        ranked = sorted(scores.items(), key=lambda x: -x[1])[:k]
        out = []
        for key, s in ranked:
            d = self.docs[key]
            out.append({"kind": d["kind"], "id": d["id"], "score": round(s, 3), "meta": d["meta"],
                        "highlight": highlight(d["text"], q), "backend": self.name})
        return out


def highlight(text: str, q: list[str], width: int = 160) -> str:
    low = (text or "").lower()
    pos = min((low.find(t) for t in q if low.find(t) >= 0), default=0)
    start = max(0, pos - 40)
    snippet = text[start:start + width].replace("\n", " ")
    for t in sorted(set(q), key=len, reverse=True):
        if len(t) > 2:
            snippet = re.sub(f"(?i)({re.escape(t)})", r"«\1»", snippet)
    return ("…" if start else "") + snippet + ("…" if start + width < len(text) else "")


class SearchFacade:
    """Index into local BM25 always; mirror into Elastic when configured and healthy."""

    def __init__(self):
        self.local = LocalSearch()
        self.elastic = None
        self.elastic_error = None
        if config.ELASTIC_URL and (config.ELASTIC_API_KEY or config.ROLE_KEYS.get("ai_agent")):
            try:
                from jarvis.search.elastic import ElasticBackend
                self.elastic = ElasticBackend()
                if not self.elastic.ping():
                    self.elastic_error = "ping failed"
                    self.elastic = None
            except Exception as e:  # pragma: no cover - depends on network
                self.elastic_error = str(e)
                self.elastic = None
        self._pending: list = []

    @property
    def backend(self) -> str:
        return self.elastic.name if self.elastic else self.local.name

    def index(self, kind: str, doc_id: str, text: str, meta: dict | None = None):
        self.local.index(kind, doc_id, text, meta)
        if self.elastic:
            self._pending.append((kind, doc_id, text, meta or {}))
            if len(self._pending) >= 200:
                self.flush()

    def flush(self):
        if self.elastic and self._pending:
            try:
                self.elastic.bulk(self._pending)
            except Exception as e:  # pragma: no cover
                self.elastic_error = str(e)
            self._pending = []

    def search(self, query: str, kind: str | None = None, k: int = 10, filters: dict | None = None) -> list[dict]:
        if self.elastic:
            try:
                self.flush()
                return self.elastic.search(query, kind, k, filters)
            except Exception as e:  # pragma: no cover
                self.elastic_error = str(e)
        return self.local.search(query, kind, k, filters)

    def mirror_audit(self, rows: list[dict]):
        if self.elastic:
            try:
                self.elastic.mirror_audit(rows)
            except Exception as e:  # pragma: no cover
                self.elastic_error = str(e)

    def status(self) -> dict:
        return {"backend": self.backend, "elastic_configured": bool(config.ELASTIC_URL),
                "elastic_error": self.elastic_error,
                "semantic": bool(self.elastic and self.elastic.semantic), "local_docs": len(self.local.docs)}
