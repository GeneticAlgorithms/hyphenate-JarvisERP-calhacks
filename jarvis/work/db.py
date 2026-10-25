"""The system of work: one SQLite file. ACID, so a change and its audit row commit together."""
from __future__ import annotations

import json
import sqlite3
import threading
from pathlib import Path

from jarvis import config

SCHEMA = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

-- ---------------- systems of record (synced, read-only to agents) ----------------
CREATE TABLE IF NOT EXISTS raw_rows (
  raw_id TEXT PRIMARY KEY, source TEXT, file TEXT, row_num INTEGER, payload TEXT, landed_at TEXT);
CREATE TABLE IF NOT EXISTS records (               -- golden rows, one shape for every source
  record_id TEXT PRIMARY KEY, source TEXT, src_id TEXT, kind TEXT,
  txn_date TEXT, period TEXT, amount_cents INTEGER, currency TEXT,
  counterparty TEXT, description TEXT, fields TEXT, raw_ref TEXT,
  evidence_quality TEXT DEFAULT 'api', synced_at TEXT, updated_at TEXT);
CREATE INDEX IF NOT EXISTS ix_records_src ON records(source, period);
CREATE TABLE IF NOT EXISTS sync_cursor (source TEXT PRIMARY KEY, cursor TEXT, at TEXT);
CREATE TABLE IF NOT EXISTS docs (
  doc_id TEXT PRIMARY KEY, kind TEXT, title TEXT, date TEXT, vendor TEXT, fields TEXT, path TEXT, text TEXT,
  synced_at TEXT);
CREATE TABLE IF NOT EXISTS fx_rates (date TEXT PRIMARY KEY, eur_usd REAL, source TEXT);

-- ---------------- ledger (system of record; ONLY the gateway writes) ----------------
CREATE TABLE IF NOT EXISTS ledger_entries (
  entry_id TEXT PRIMARY KEY, date TEXT, period TEXT, memo TEXT, name TEXT, txn_type TEXT, num TEXT,
  source TEXT, refs TEXT, work_item_id TEXT, posted_by TEXT, posted_at TEXT);
CREATE TABLE IF NOT EXISTS ledger_lines (
  entry_id TEXT REFERENCES ledger_entries(entry_id), line_no INTEGER, account TEXT, amount_cents INTEGER,
  memo TEXT, vendor_id TEXT, PRIMARY KEY(entry_id, line_no));
CREATE TABLE IF NOT EXISTS reconciliation (
  record_id TEXT PRIMARY KEY, entry_id TEXT, work_item_id TEXT, at TEXT);
CREATE TABLE IF NOT EXISTS bills (
  bill_id TEXT PRIMARY KEY, vendor_id TEXT, vendor TEXT, date TEXT, due TEXT, amount_cents INTEGER, num TEXT,
  memo TEXT, acct TEXT, status TEXT, service_period TEXT, je_id TEXT);
CREATE TABLE IF NOT EXISTS vendors (
  vendor_id TEXT PRIMARY KEY, qbo_name TEXT, legal TEXT, domain TEXT, default_acct TEXT, products TEXT,
  tin TEXT, status TEXT DEFAULT 'active', created_by TEXT);
CREATE TABLE IF NOT EXISTS vendor_aliases (
  alias TEXT PRIMARY KEY, vendor_id TEXT, source TEXT, status TEXT, work_item_id TEXT, at TEXT);

-- ---------------- the work ----------------
CREATE TABLE IF NOT EXISTS work_items (
  item_id TEXT PRIMARY KEY, kind TEXT, anchor TEXT, state TEXT, title TEXT, period TEXT,
  source_refs TEXT, proposal TEXT, evidence TEXT, policy_id TEXT, precedent_ids TEXT,
  confidence REAL, rationale TEXT, question TEXT, answer TEXT, review TEXT,
  proposed_by TEXT, approved_by TEXT, parent_id TEXT, created_at TEXT, updated_at TEXT);
CREATE INDEX IF NOT EXISTS ix_items_anchor ON work_items(anchor);
CREATE TABLE IF NOT EXISTS policies (
  policy_id TEXT, version INTEGER, pattern TEXT, title TEXT, rule_text TEXT, matcher TEXT,
  evidence TEXT, status TEXT, proposed_by TEXT, approved_by TEXT, created_at TEXT,
  PRIMARY KEY(policy_id, version));
CREATE TABLE IF NOT EXISTS precedents (
  prec_id TEXT PRIMARY KEY, date TEXT, period TEXT, pattern TEXT, summary TEXT, decision TEXT,
  decided_by TEXT, status TEXT, refs TEXT, source_item TEXT);
CREATE TABLE IF NOT EXISTS messages (
  msg_id TEXT PRIMARY KEY, at TEXT, from_actor TEXT, to_actor TEXT, subject TEXT, body TEXT,
  item_id TEXT, direction TEXT);
CREATE TABLE IF NOT EXISTS audit_log (           -- append-only; fixes are new events
  seq INTEGER PRIMARY KEY AUTOINCREMENT, at TEXT, actor TEXT, actor_role TEXT, action TEXT,
  subject TEXT, allowed INTEGER, reason TEXT, diff TEXT, evidence TEXT, prev_hash TEXT, hash TEXT);
CREATE TRIGGER IF NOT EXISTS audit_no_update BEFORE UPDATE ON audit_log
  BEGIN SELECT RAISE(ABORT, 'audit_log is append-only'); END;
CREATE TRIGGER IF NOT EXISTS audit_no_delete BEFORE DELETE ON audit_log
  BEGIN SELECT RAISE(ABORT, 'audit_log is append-only'); END;
CREATE TABLE IF NOT EXISTS kv (k TEXT PRIMARY KEY, v TEXT);
"""

_lock = threading.RLock()


class DB:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.path, check_same_thread=False, isolation_level=None)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)
        self.lock = _lock

    # ---- helpers ----
    def q(self, sql: str, args=()) -> list[dict]:
        with self.lock:
            return [dict(r) for r in self.conn.execute(sql, args).fetchall()]

    def one(self, sql: str, args=()) -> dict | None:
        rows = self.q(sql, args)
        return rows[0] if rows else None

    def x(self, sql: str, args=()):
        with self.lock:
            return self.conn.execute(sql, args)

    def tx(self):
        """Context manager: BEGIN IMMEDIATE ... COMMIT/ROLLBACK."""
        db = self

        class _Tx:
            def __enter__(self_):
                db.lock.acquire()
                db.conn.execute("BEGIN IMMEDIATE")
                return db

            def __exit__(self_, et, ev, tb):
                try:
                    db.conn.execute("ROLLBACK" if et else "COMMIT")
                finally:
                    db.lock.release()
                return False
        return _Tx()

    def kv_get(self, k: str, default=None):
        r = self.one("SELECT v FROM kv WHERE k=?", (k,))
        return json.loads(r["v"]) if r else default

    def kv_set(self, k: str, v):
        self.x("INSERT INTO kv(k,v) VALUES(?,?) ON CONFLICT(k) DO UPDATE SET v=excluded.v", (k, json.dumps(v)))


def J(v) -> str:
    return json.dumps(v, sort_keys=True, default=str)


def L(s: str | None, default=None):
    if s is None or s == "":
        return default
    return json.loads(s)


def default_db_path(seed: int) -> Path:
    return config.RUNTIME_DIR / f"seed_{seed}" / "work.db"
