"""Evaluate Jarvis vs baselines on generated worlds.

    python -m jarvis.evals.run --seeds 2026 1 2 3        # writes evals/report.json and evals/REPORT.md
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from jarvis import config
from jarvis.agent import llm
from jarvis.agent.session import Session
from jarvis.evals import baselines, score
from jarvis.world import generator


def run_seed(seed: int) -> dict:
    generator.generate(seed)
    world = generator.world_dir(seed)
    t0 = time.time()
    s = Session(seed, fresh=True, quiet=True)
    s.run_all(controller=True)
    secs = time.time() - t0
    jar = score.score(world / "answer_key.json", score.outcomes(s.db))
    b1 = score.score(world / "answer_key.json", baselines.run_b1(world), phases=("close",))
    jar_close = score.score(world / "answer_key.json", score.outcomes(s.db), phases=("close",))
    st = s.engine.status()
    chain = s.verify()
    bean = s.beancount()
    return {"seed": seed, "seconds": round(secs, 2), "jarvis": jar, "jarvis_close_only": jar_close["summary"],
            "b1_rules": b1["summary"], "bank_rec": st["bank_rec"], "trial_balance_ok": st["trial_balance_ok"],
            "audit_chain": chain, "beancount_errors": len(bean["errors"]),
            "items": st["states"]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, nargs="+", default=[2026, 1, 2, 3])
    a = ap.parse_args()
    results = [run_seed(s) for s in a.seeds]
    out_dir = config.ROOT / "evals"
    out_dir.mkdir(exist_ok=True)
    (out_dir / "report.json").write_text(json.dumps(results, indent=1, default=str))
    lines = ["# JarvisERP evaluation report", "",
             f"Seeds: {a.seeds} · LLM layer: {'on' if llm.available() else 'off (deterministic core only)'}", "",
             "Each seed is a freshly generated Afterglow Labs world with planted issues and an answer key the agent never reads.",
             "Jarvis runs autonomously; the Controller is played by the scripted persona (approves, rejects one accrual, answers one question).",
             "", "## September close (same items, Jarvis vs rules-based bank feed)", "",
             "| seed | items | Jarvis fully correct | B1 rules fully correct | Jarvis detection | B1 detection | Jarvis treatment | B1 treatment | Jarvis trap precision | B1 trap precision | Jarvis escalation | B1 escalation |",
             "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in results:
        j, b = r["jarvis_close_only"], r["b1_rules"]
        lines.append(f"| {r['seed']} | {j['items']} | **{j['fully_correct']:.0%}** | {b['fully_correct']:.0%} | "
                     f"{j['detection_recall']:.0%} | {b['detection_recall']:.0%} | {j['treatment_accuracy']:.0%} | "
                     f"{b['treatment_accuracy']:.0%} | {j['trap_precision']:.0%} | {b['trap_precision']:.0%} | "
                     f"{j['escalation_correct']:.0%} | {b['escalation_correct']:.0%} |")
    lines += ["", "## Full run incl. October true-ups (Jarvis)", "",
              "| seed | items | fully correct | bank rec ties | trial balance | audit chain | beancount errors | runtime |",
              "|---|---|---|---|---|---|---|---|"]
    for r in results:
        j = r["jarvis"]["summary"]
        lines.append(f"| {r['seed']} | {j['items']} | **{j['fully_correct']:.0%}** | "
                     f"{'✅' if r['bank_rec']['ties'] else '❌ ' + str(r['bank_rec']['difference_cents'])} | "
                     f"{'✅' if r['trial_balance_ok'] else '❌'} | {'✅ ' + str(r['audit_chain']['rows']) + ' rows' if r['audit_chain']['ok'] else '❌'} | "
                     f"{r['beancount_errors']} | {r['seconds']}s |")
    lines += ["", "## Misses (Jarvis)", ""]
    for r in results:
        for row in r["jarvis"]["rows"]:
            if not row["ok"]:
                lines.append(f"- seed {r['seed']} {row['key_id']} `{row['category']}` expected `{row['expected']}` got "
                             f"`{row['got']}` {row.get('detail', '')}")
    (out_dir / "REPORT.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
