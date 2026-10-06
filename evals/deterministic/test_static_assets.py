"""Deferred connection-logo assets keep valid accessible SVGs until Batch D."""
from pathlib import Path

STATIC = Path(__file__).resolve().parents[2] / "waku/ops/static"
CONNECTION_LOGOS = {"apple_calendar.svg", "apple_tools.svg", "discord.svg", "google_calendar.svg",
                    "langmem.svg", "mem0.svg", "notion.svg", "otel.svg", "supabase.svg",
                    "tavily.svg", "telegram.svg", "typesafe.svg", "whatsapp.svg", "zep.svg"}


def test_connection_card_logos_are_local_and_complete():
    """Dynamic card image paths are generated in JS, so index.html cannot pin
    them. Keep every registry-backed logo present and valid."""
    logo_dir = STATIC / "logos" / "connections"
    assert {path.name for path in logo_dir.glob("*.svg")} == CONNECTION_LOGOS
    for name in CONNECTION_LOGOS:
        svg = (logo_dir / name).read_text()
        assert svg.startswith("<svg "), f"{name} is not an SVG"
        assert "<title>" in svg, f"{name} needs an accessible title"
