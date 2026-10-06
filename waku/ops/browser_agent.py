"""Inert browser-agent facade retained for C2 provider callers."""

from __future__ import annotations

import threading

# Provider facade tests may inject a caller-owned agent; production never creates one.
_agent = None
agent_lock = threading.Lock()


def get_agent():
    raise RuntimeError("The general Waku assistant is retired; run waku career.")


def current():
    """Read the transitional singleton without constructing an assistant."""
    return _agent


def rebuild() -> str | None:
    """The transitional provider facade has no general agent to replace."""
    return None
