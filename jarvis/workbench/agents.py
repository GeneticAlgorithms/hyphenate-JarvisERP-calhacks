"""Registry of the five workbench agents."""
from jarvis.workbench import p1_timing, p2_rollforward, p3_bank, p4_evidence, p5_vendors

REGISTRY = {
    "p1_timing": {"title": p1_timing.TITLE, "stages": p1_timing.STAGES, "run": p1_timing.run, "on_reject": p1_timing.on_reject},
    "p2_rollforward": {"title": p2_rollforward.TITLE, "stages": p2_rollforward.STAGES, "run": p2_rollforward.run,
                       "apply": p2_rollforward.apply},
    "p2_late": {"title": "Package refresh after last-minute QBO change", "stages": p2_rollforward.STAGES,
                "run": p2_rollforward.run_late, "apply": p2_rollforward.apply, "data": "p2_rollforward"},
    "p3_bank": {"title": p3_bank.TITLE, "stages": p3_bank.STAGES, "run": p3_bank.run, "apply": p3_bank.apply, "on_reject": p3_bank.on_reject},
    "p4_evidence": {"title": p4_evidence.TITLE, "stages": p4_evidence.STAGES, "run": p4_evidence.run, "apply": p4_evidence.apply},
    "p5_vendors": {"title": p5_vendors.TITLE, "stages": p5_vendors.STAGES, "run": p5_vendors.run, "apply": p5_vendors.apply},
}
