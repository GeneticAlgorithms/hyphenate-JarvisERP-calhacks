"""Terminal demo: full autonomous close with narration.   python -m jarvis.cli --seed 2026"""
from __future__ import annotations

import argparse

from jarvis.agent import personas
from jarvis.agent.session import Session
from jarvis.evals import score
from jarvis.money import fmt
from jarvis.work.transition import get_item

C = {"g": "\033[38;5;121m", "p": "\033[38;5;213m", "y": "\033[38;5;228m", "b": "\033[38;5;117m", "d": "\033[2m", "x": "\033[0m"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=2026)
    a = ap.parse_args()
    s = Session(a.seed, fresh=True, quiet=True)
    print(f"{C['b']}▶ Connecting to Afterglow Labs' systems of record…{C['x']}")
    r = s.connect()
    print(f"  bank +{r['bank']['new']} · PayPal +{r['paypal']['new']} · Ramp +{r['ramp']['new']} · docs +{r['docs']['new']}")
    print(f"{C['b']}▶ Learning the job from Jan–Aug history…{C['x']}")
    for p in s.onboard():
        print(f"  proposed {p['policy_id']} · {p['title']}  {C['d']}({len(p['evidence'])} precedents){C['x']}")
    personas.auto_controller(s.engine)
    print(f"  {C['g']}Controller approved the policies{C['x']}")
    print(f"{C['b']}▶ Closing September 2026…{C['x']}")
    s.run_close()
    for row in s.db.q("SELECT item_id FROM work_items ORDER BY created_at"):
        it = get_item(s.db, row["item_id"])
        col = {"POSTED": C["g"], "PROPOSED": C["y"], "NEEDS_INFO": C["p"], "DISMISSED": C["d"]}.get(it["state"], "")
        print(f"  {col}{it['state']:<10}{C['x']} {it['kind']:<22} {it['title'][:72]}")
    m = s.db.one("SELECT item_id FROM work_items WHERE kind='paypal_split' ORDER BY ABS(confidence) DESC, created_at DESC")
    moment = next((get_item(s.db, r["item_id"]) for r in s.db.q("SELECT item_id FROM work_items WHERE kind='paypal_split'")
                   if len(get_item(s.db, r["item_id"])["proposal"]["lines"]) >= 5), None)
    if moment:
        print(f"\n{C['y']}★ THE MOMENT — {moment['title']}{C['x']}\n  {moment['rationale']}")
        for l in moment["proposal"]["lines"]:
            print(f"    {l['acct']}  {fmt(l['cents']):>14}  {l.get('memo', '')[:70]}")
        d = s.challenge(moment["item_id"], "Why not just expense it all to software like we always do with PayPal? "
                                           "It's under materiality.")
        print(f"\n{C['p']}Maya:{C['x']} {d['question']}\n{C['g']}Jarvis:{C['x']} " + d["answer"].replace("\n", "\n  "))
    print(f"\n{C['b']}▶ Controller works the inbox (approves, says no once, answers a question)…{C['x']}")
    personas.auto_controller(s.engine)
    print(f"{C['b']}▶ October arrives…{C['x']}")
    s.october()
    personas.auto_controller(s.engine)
    st = s.engine.status()
    print(f"  bank rec ties: {st['bank_rec']['ties']} · trial balance ok: {st['trial_balance_ok']} · audit chain: {s.verify()}")
    sc = score.score(s.world / "answer_key.json", score.outcomes(s.db))
    print(f"\n{C['g']}Score vs planted answer key:{C['x']} {sc['summary']}")


if __name__ == "__main__":
    main()
