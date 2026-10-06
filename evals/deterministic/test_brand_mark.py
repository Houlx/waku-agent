"""Career identity retains upstream attribution without protected marks."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_career_readme_excludes_protected_waku_marks_and_keeps_attribution():
    readme = (ROOT / "README.md").read_text()
    assert readme.startswith("# Career Agent\n")
    assert "Sean Chen (ShenSeanChen)" in readme
    assert "[LICENSE](LICENSE)" in readme
    for name in ("waku-mark-on-light.svg", "waku-mark-on-dark.svg"):
        assert f"docs/brand/{name}" not in readme
    assert "<picture>" not in readme
