"""Tiny in-process pub/sub. The API server forwards these to the browser over SSE."""
from __future__ import annotations

import queue
import threading
import time

_subs: list[queue.Queue] = []
_lock = threading.Lock()
_history: list[dict] = []


def publish(event_type: str, **payload):
    ev = {"t": time.time(), **payload, "type": event_type}
    with _lock:
        _history.append(ev)
        del _history[:-2000]
        for q in list(_subs):
            try:
                q.put_nowait(ev)
            except queue.Full:
                pass


def subscribe() -> queue.Queue:
    q: queue.Queue = queue.Queue(maxsize=5000)
    with _lock:
        _subs.append(q)
    return q


def unsubscribe(q: queue.Queue):
    with _lock:
        if q in _subs:
            _subs.remove(q)


def recent(n: int = 200) -> list[dict]:
    with _lock:
        return list(_history[-n:])


def reset():
    with _lock:
        _history.clear()
