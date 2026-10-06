"""Offline build enumeration protects retained distribution and license boundaries.

Hosted EL2 code and teaching consumers are retired. These checks still inspect
actual Hatchling members, including force-includes, rather than trusting exclusions.
"""

import ast
from pathlib import Path

from hatchling.builders.sdist import SdistBuilder
from hatchling.builders.wheel import WheelBuilder
from hatchling.metadata.core import ProjectMetadata
from hatchling.plugin.manager import PluginManager

ROOT = Path(__file__).resolve().parents[2]
RETIRED_COMPONENTS = {"hosted", "examples", "lab", "whiteboard", "whiteboards"}


def _distribution_paths(builder_cls: type) -> list[str]:
    manager = PluginManager()
    metadata = ProjectMetadata(str(ROOT), manager)
    builder = builder_cls(str(ROOT), plugin_manager=manager, metadata=metadata)
    return sorted(f.distribution_path for f in builder.recurse_included_files())


def test_retired_consumers_never_ship():
    for builder in (SdistBuilder, WheelBuilder):
        paths = _distribution_paths(builder)
        leaks = [p for p in paths if RETIRED_COMPONENTS.intersection(Path(p).parts)]
        assert not leaks, f"{builder.__name__} ships retired consumers: {leaks}"
        assert "waku/ops/static/career.html" in paths
        assert "waku/runtime/career_runtime.py" in paths
        assert "waku/providers.toml" in paths
        assert "waku/db.py" in paths
        assets = {p.relative_to(ROOT).as_posix()
                  for p in (ROOT / "waku/ops/static/career").iterdir() if p.is_file()}
        assert assets <= set(paths)
        if builder is WheelBuilder:
            assert {p.split("/", 1)[0] for p in paths} == {"waku"}


def test_runtime_data_never_ships():
    for builder in (SdistBuilder, WheelBuilder):
        leaks = [p for p in _distribution_paths(builder)
                 if (p != ".env.example"
                     and any(part.startswith((".env", ".waku")) for part in Path(p).parts))
                 or Path(p).name in {"state.db", "usage.jsonl", "credentials.json"}]
        assert not leaks, f"{builder.__name__} ships runtime data: {leaks}"


def test_retained_runtime_never_imports_hosted():
    offenders = []
    for path in (ROOT / "waku").rglob("*.py"):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            names = ([a.name for a in node.names] if isinstance(node, ast.Import)
                     else [node.module or ""] if isinstance(node, ast.ImportFrom) else [])
            if any(name.split(".")[0] == "hosted" for name in names):
                offenders.append(path.relative_to(ROOT).as_posix())
    assert not offenders, f"retained runtime imports retired EL2 modules: {offenders}"
