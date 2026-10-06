"""Retired connector facade retained until Batch C2."""

from __future__ import annotations

from pathlib import Path

# The connector table stays empty until the facade retires in C2.
CONNECTORS: dict[str, str] = {}


def usage() -> str:
    return "Usage: waku connect <name>  —  available: " + ", ".join(sorted(CONNECTORS)) + "."


def connect(name: str, home: Path) -> str:
    return "General integrations are retired; configure a provider in Career Settings."


def cli_main(argv: list[str]) -> int:
    print(connect(argv[0] if argv else "", Path()))
    return 1
