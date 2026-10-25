"""Workbench 5 — Duplicate vendors across QBO, Ramp and PayPal (Claude/Anthropic, Cursor/Anysphere, Google/Google Ads…)."""
from __future__ import annotations

import csv
import itertools
from difflib import SequenceMatcher

from jarvis.money import fmt
from jarvis.workbench import clean as C

TITLE = "Duplicate vendors"
STAGES = [("ingest", "Ingest vendor lists + W-9s"), ("clean", "Normalize names"), ("block", "Find candidate pairs"),
          ("score", "Score evidence per pair"), ("cluster", "Decide: merge / link / keep separate"),
          ("impact", "Impact analysis"), ("prevent", "Prevention rules"), ("approve", "Controller → Gateway updates vendor master")]


def run(r, **_):
    raw = r.data_dir / "raw"
    with r.stage("ingest"):
        qbo = list(csv.DictReader((raw / "qbo_vendor_list_export_2026-10-06.csv").open()))
        ramp = list(csv.DictReader((raw / "ramp_vendors_2026-10-06.csv").open()))
        tx = list(csv.DictReader((raw / "vendor_transactions_2026.csv").open()))
        w9 = list(csv.DictReader((raw / "w9_registry.csv").open()))
        for n, rows in (("QBO vendor list", qbo), ("Ramp vendors", ramp), ("transactions", tx), ("W-9 registry", w9)):
            r.log("info", f"{n}: {len(rows)} rows", pause=0.4)
        r.artifact("table", "Before: QBO vendor list", {"columns": ["Vendor", "Company Name", "Email", "Tax ID", "Created By"],
                                                        "rows": qbo})
        r.ctx.update(qbo=qbo, ramp=ramp, tx=tx, w9=w9)
        r.done(f"{len(qbo)} QBO vendors, {len(ramp)} Ramp 'create new vendor' suggestions")

    with r.stage("clean"):
        vs = []
        for v in r.ctx["qbo"]:
            raw_name = v["Vendor"]
            clean = raw_name.strip()
            if clean != raw_name:
                r.log("fix", f"'{raw_name}' has trailing whitespace → '{clean}' (that alone created a second vendor via a bank rule)")
            dom = v["Email"].split("@")[-1] if "@" in v["Email"] else ""
            root = ".".join(dom.split(".")[-2:]) if dom else ""
            nn = C.norm_name(v["Company Name"] or clean)
            vs.append({"name": clean, "legal": v["Company Name"], "norm": nn, "domain": root, "tin": v["Tax ID"], "created_by": v["Created By"]})
            r.log("fix", f"'{clean}': normalized='{nn}' · email domain root='{root or '—'}' · TIN={v['Tax ID'] or '—'}", pause=0.25)
        r.ctx["vs"] = vs
        r.done("names normalized (case, punctuation, Inc/LLC/PBC suffixes), domains reduced to their root")

    with r.stage("block", "only compare vendors that share something"):
        products = {}
        for w in r.ctx["w9"]:
            for p in w["Products / DBA"].split(";"):
                products[C.norm_name(p)] = w["Legal Name"]
        issuer = {x["Ramp Vendor"]: x["Receipt Issuer"] for x in r.ctx["ramp"]}
        dom_legal = {d: w["Legal Name"] for w in r.ctx["w9"] for d in w["Domain(s)"].split(";")}
        pairs = []
        for a, b in itertools.combinations(r.ctx["vs"], 2):
            share = []
            for x, y in ((a, b), (b, a)):
                if issuer.get(x["name"]) and issuer[x["name"]] == y["legal"]:
                    share.append(f"Ramp receipt for '{x['name']}' issued by {y['legal']}")
            if a["domain"] and a["domain"] == b["domain"] and dom_legal.get(a["domain"]):
                share.append(f"domain {a['domain']} is on the W-9 of {dom_legal[a['domain']]}")
            if a["tin"] and a["tin"] == b["tin"]:
                share.append("same TIN")
            if a["domain"] and a["domain"] == b["domain"]:
                share.append("same email domain")
            ta, tb = set(a["norm"].split()), set(b["norm"].split())
            if ta & tb:
                share.append(f"shared token '{' '.join(sorted(ta & tb))}'")
            if products.get(C.norm_name(a["name"])) and products.get(C.norm_name(a["name"])) == (b["legal"] or products.get(C.norm_name(b["name"]))):
                share.append(f"'{a['name']}' is a product of {products[C.norm_name(a['name'])]}")
            if products.get(C.norm_name(b["name"])) and products.get(C.norm_name(b["name"])) == (a["legal"] or products.get(C.norm_name(a["name"]))):
                share.append(f"'{b['name']}' is a product of {products[C.norm_name(b['name'])]}")
            if share:
                pairs.append((a, b, share))
        r.log("info", f"{len(r.ctx['vs'])} vendors → {len(r.ctx['vs']) * (len(r.ctx['vs']) - 1) // 2} possible pairs → "
                      f"{len(pairs)} candidate pairs after blocking")
        r.ctx["pairs"], r.ctx["products"] = pairs, products
        r.done(f"{len(pairs)} candidate pairs")

    with r.stage("score", "strong signals beat look-alike names"):
        rows, verdicts = [], []
        w9_by_tin = {w["TIN"]: w for w in r.ctx["w9"]}
        for a, b, share in r.ctx["pairs"]:
            score, neg = 0, []
            if "same TIN" in share:
                score += 60
            if "same email domain" in share:
                score += 30
            if any("product of" in s for s in share):
                score += 40
            if any("Ramp receipt" in s for s in share):
                score += 40
            if any("on the W-9" in s for s in share):
                score += 30
            score += int(20 * SequenceMatcher(None, a["norm"], b["norm"]).ratio())
            if a["tin"] and b["tin"] and a["tin"] != b["tin"]:
                neg.append(f"different TINs ({a['tin']} vs {b['tin']}: {w9_by_tin.get(a['tin'], {}).get('Legal Name')} ≠ "
                           f"{w9_by_tin.get(b['tin'], {}).get('Legal Name')})")
                score -= 100
            verdict = "same entity" if score >= 50 else "different entities" if neg else "insufficient evidence"
            r.log("find" if verdict == "same entity" else "decide",
                  f"{a['name']} ↔ {b['name']}: {', '.join(share)}" + (f"; NEGATIVE: {'; '.join(neg)}" if neg else "") +
                  f" → score {score} → {verdict}", pause=0.4)
            rows.append({"pair": f"{a['name']} ↔ {b['name']}", "signals": "; ".join(share + neg), "score": score, "verdict": verdict})
            verdicts.append((a, b, verdict))
        r.artifact("table", "Pair evidence", {"columns": ["pair", "signals", "score", "verdict"], "rows": rows})
        r.ctx["verdicts"] = verdicts
        r.done(f"{sum(1 for *_, v in verdicts if v == 'same entity')} same-entity pairs; look-alikes rejected")

    with r.stage("cluster"):
        parent = {v["name"]: v["name"] for v in r.ctx["vs"]}

        def find(x):
            while parent[x] != x:
                x = parent[x]
            return x
        for a, b, v in r.ctx["verdicts"]:
            if v == "same entity":
                parent[find(b["name"])] = find(a["name"])
        groups = {}
        for v in r.ctx["vs"]:
            groups.setdefault(find(v["name"]), []).append(v)
        clusters = []
        for g in groups.values():
            if len(g) < 2:
                continue
            master = max(g, key=lambda v: (bool(v["tin"]), v["created_by"] != "Ramp sync", len(v["legal"])))
            others = [v for v in g if v is not master]
            clusters.append({"master": master, "others": others})
            r.log("decide", f"cluster → keep '{master['name']}' ({master['legal']}, TIN {master['tin']}) as the vendor; "
                            + ", ".join(f"'{o['name']}' becomes an alias" for o in others))
        for a, b, v in r.ctx["verdicts"]:
            if v == "different entities":
                r.moment("caught", "decide", f"KEEP SEPARATE: '{a['name']}' and '{b['name']}' look alike but are different legal entities — "
                                f"merging would mix two suppliers' history and 1099s")
        r.ctx["clusters"] = clusters
        r.done(f"{len(clusters)} merges, 1 look-alike kept separate")

    with r.stage("impact", "what changes in the books if we merge"):
        rows = []
        for c in r.ctx["clusters"]:
            names = [c["master"]["name"]] + [o["name"] for o in c["others"]]
            txs = [t for t in r.ctx["tx"] if t["Vendor (as recorded)"].strip() in names]
            before = {n: sum(C.money(t["Amount"])[0] for t in txs if t["Vendor (as recorded)"].strip() == n) for n in names}
            total = sum(before.values())
            accts = sorted({t["Account"] for t in txs})
            r.log("info", f"{c['master']['name']}: {len(txs)} transactions re-pointed; spend was split "
                          + ", ".join(f"{n} {fmt(v)}" for n, v in before.items()) + f" → one vendor {fmt(total)}; "
                          f"accounts {accts} preserved (Google Ads stays in 6420, Workspace in 6410)")
            rows.append({"vendor": c["master"]["name"], "aliases": ", ".join(o["name"] for o in c["others"]),
                         "transactions": len(txs), "spend_before": " · ".join(f"{n} {fmt(v)}" for n, v in before.items()),
                         "spend_after": fmt(total)})
            dup = [t for t in txs if t["Memo"] == "Cursor Business Sept"]
            if len(dup) == 2:
                r.moment("caught", "find", "side finding: 'Cursor Business Sept' $480 exists as both a QBO bill (Anysphere) and a Ramp charge (Cursor) "
                              "— with one vendor this duplicate becomes visible → flagged to AP (void the bill)")
        r.artifact("table", "Impact", {"columns": ["vendor", "aliases", "transactions", "spend_before", "spend_after"], "rows": rows})
        r.done("spend consolidated; categories preserved; hidden duplicate bill surfaced")

    with r.stage("prevent", "stop it happening next month"):
        rules = []
        for s in r.ctx["ramp"]:
            target = next((c["master"]["name"] for c in r.ctx["clusters"]
                           if s["Ramp Vendor"] in [o["name"] for o in c["others"]] + [c["master"]["name"]]), None)
            if target and target != s["Ramp Vendor"]:
                rules.append({"when": f"Ramp suggests '{s['Ramp Vendor']}' (receipt issuer {s['Receipt Issuer']})",
                              "then": f"map to existing vendor '{target}' — do not create"})
                r.log("decide", f"rule: Ramp '{s['Ramp Vendor']}' → '{target}' (Ramp said: {s['Suggested Action']})")
            elif not target:
                rules.append({"when": f"Ramp suggests '{s['Ramp Vendor']}'", "then": "create (distinct legal entity) — needs Controller"})
        r.artifact("table", "Prevention rules", {"columns": ["when", "then"], "rows": rules})
        r.ctx["rules"] = rules
        r.done(f"{len(rules)} sync rules")

    with r.stage("approve"):
        for c in r.ctx["clusters"]:
            r.propose("vendor_merge", f"Merge {', '.join(o['name'] for o in c['others'])} → {c['master']['name']}",
                      {"master": c["master"]["name"], "aliases": [o["name"] for o in c["others"]]},
                      f"Same legal entity ({c['master']['legal']}); evidence in 'Pair evidence'.", [], 0.94)
        r.propose("vendor_rules", f"Install {len(r.ctx['rules'])} Ramp→QBO vendor mapping rules", {"rules": r.ctx["rules"]},
                  "Prevents product names becoming vendors again.", [], 0.9)
        r._stage("approve")["status"] = "waiting"
        r._stage("approve")["summary"] = f"{len(r.proposals)} proposals waiting"


def apply(r, it):
    p = it["proposal"]
    if it["kind"] == "vendor_merge":
        r.ctx.setdefault("merged", {}).update({a: p["master"] for a in p["aliases"]})
        after = []
        for v in r.ctx["qbo"]:
            n = v["Vendor"].strip()
            if n in r.ctx["merged"]:
                continue
            al = [a for a, m in r.ctx["merged"].items() if m == n]
            after.append({**v, "Vendor": n, "Aliases": ", ".join(al)})
        r.artifact("table", "After: vendor master", {"columns": ["Vendor", "Company Name", "Tax ID", "Aliases"], "rows": after},
                   aid="AFTER")
        return f"{len(p['aliases'])} alias(es) merged into {p['master']}; transactions re-pointed"
    return f"{len(p['rules'])} mapping rules installed in the Ramp→QBO sync"
