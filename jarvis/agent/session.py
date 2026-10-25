"""A running JarvisERP instance for one world seed: DB + search + engine + human-facing actions."""
from __future__ import annotations

import shutil
import threading
from pathlib import Path

from jarvis import config
from jarvis.agent import defend, injector, personas, policies
from jarvis.agent.context import Ctx
from jarvis.agent.engine import Engine
from jarvis.work import events, gateway, ledger, sync
from jarvis.work.db import DB, default_db_path
from jarvis.work.roles import actor
from jarvis.work.transition import get_item, transition, verify_chain
from jarvis.world import generator


class Session:
    def __init__(self, seed: int | None = None, fresh: bool = False, quiet: bool = False, speed: float = 0.0):
        self.seed = seed if seed is not None else config.world_seed()
        self.world = generator.world_dir(self.seed)
        if not (self.world / "MANIFEST.json").exists():
            generator.generate(self.seed)
        path = default_db_path(self.seed)
        if fresh and path.parent.exists():
            shutil.rmtree(path.parent)
        self.db = DB(path)
        self.ctx = Ctx(self.db, self.world, self.seed, quiet=quiet)
        self.ctx.speed = speed
        self.engine = Engine(self.ctx)
        self.lock = threading.RLock()
        self.busy = False
        self._indexed = False

    # ------------------------------------------------------------ lifecycle
    def connect(self) -> dict:
        with self.lock:
            sync.bootstrap(self.db, self.world)
            res = sync.sync_all(self.db, self.world, "initial")
            self.ctx.build_index()
            self._indexed = True
            return res

    def ensure_ready(self):
        if not self.db.kv_get("bootstrapped"):
            self.connect()
        elif not self._indexed:
            self.ctx.build_index()
            self._indexed = True

    def onboard(self):
        self.ensure_ready()
        return self.engine.onboard()

    def run_close(self):
        self.ensure_ready()
        return self.engine.run_close()

    def october(self):
        res = sync.sync_all(self.db, self.world, "october")
        self.ctx.build_index()
        out = self.engine.run_october()
        return {"sync": res, "status": out}

    def resync(self):
        return sync.sync_all(self.db, self.world, self.db.kv_get("phase", "initial"))

    def run_all(self, controller: bool = True) -> dict:
        """Full autonomous run (used by evals and `make demo-cli`)."""
        self.ensure_ready()
        self.onboard()
        if controller:
            personas.auto_controller(self.engine)
        self.engine.run_close()
        if controller:
            personas.auto_controller(self.engine)
        self.october()
        if controller:
            personas.auto_controller(self.engine)
        return self.engine.status()

    # ------------------------------------------------------------ human actions
    def approve(self, item_id: str, who: str = "maya", reason: str = "Approved") -> dict:
        transition(self.db, item_id, "approve", actor(who), reason=reason)
        return gateway.post(self.db, item_id)

    def reject(self, item_id: str, reason: str, who: str = "maya") -> dict:
        transition(self.db, item_id, "reject", actor(who), {"answer": reason}, reason=reason)
        return self.engine.after_reject(item_id) or get_item(self.db, item_id)

    def answer(self, item_id: str, text: str, who: str = "maya") -> dict:
        transition(self.db, item_id, "answer", actor(who), {"answer": text}, reason=text)
        return self.engine.after_answer(item_id)

    def decide_policy(self, policy_id: str, version: int, decision: str, who: str = "maya"):
        return policies.decide_policy(self.db, policy_id, version, decision, actor(who),
                                      "Approved by Controller" if decision == "approve" else "Rejected by Controller")

    def auto_controller(self):
        return personas.auto_controller(self.engine)

    def try_self_approve(self, item_id: str) -> dict:
        """Demo of LIMITS: the agent attempts to approve its own proposal -> denied in code and logged."""
        # Let Denied exceptions bubble up to be caught by _safe() and return 403
        transition(self.db, item_id, "approve", actor("jarvis"), reason="(attempting self-approval)")
        return {"denied": False}

    def challenge(self, item_id: str, question: str) -> dict:
        return defend.defend(self.ctx, item_id, question)

    def inject(self, text: str | None = None, template: str | None = None, params: dict | None = None) -> dict:
        return injector.inject(self, text=text, template=template, params=params or {})

    def set_fault(self, mode: str | None):
        sync.PayPalAPI.fault = mode
        sync.PayPalAPI._calls = 0
        events.publish("fault", mode=mode)
        return {"paypal_fault": mode}

    def verify(self) -> dict:
        return verify_chain(self.db)

    def beancount(self) -> dict:
        p, errs = ledger.write_beancount(self.db, self.seed)
        return {"path": str(p), "errors": errs}
