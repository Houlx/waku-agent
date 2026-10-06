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
RETIRED_COMPONENTS = {"skills", "hosted", "examples", "lab", "whiteboard", "whiteboards"}


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


def test_restored_bundled_skills_are_excluded_from_both_builds(tmp_path):
    """A local restoration must not silently reintroduce shipped product skills."""
    import shutil

    for name in ("pyproject.toml", "README.md", "LICENSE", "LICENSE-BRAND"):
        shutil.copyfile(ROOT / name, tmp_path / name)
    (tmp_path / "waku").mkdir()
    shutil.copyfile(ROOT / "waku/__init__.py", tmp_path / "waku/__init__.py")
    for directory in ("skills/restored", "waku/skills/restored"):
        path = tmp_path / directory
        path.mkdir(parents=True)
        (path / "SKILL.md").write_text("Retired bundled content.\n")
    for builder_cls in (SdistBuilder, WheelBuilder):
        manager = PluginManager()
        builder = builder_cls(str(tmp_path), plugin_manager=manager,
                              metadata=ProjectMetadata(str(tmp_path), manager))
        paths = [f.distribution_path for f in builder.recurse_included_files()]
        assert "waku/__init__.py" in paths
        assert not any("skills" in Path(p).parts for p in paths)


def test_distributed_static_files_are_only_career_assets():
    from waku.ops.career_dashboard import CAREER_ASSETS

    for builder in (SdistBuilder, WheelBuilder):
        paths = _distribution_paths(builder)
        static = {p.removeprefix('waku/ops/static/') for p in paths
                  if p.startswith('waku/ops/static/')}
        assert static == CAREER_ASSETS | {'README.md'}
        assert not any(p.endswith('.woff2') for p in paths)
        assert not any(p.startswith('docs/brand/') for p in paths)


def test_restored_product_assets_are_excluded(tmp_path):
    import shutil

    for name in ('pyproject.toml', 'README.md', 'LICENSE', 'LICENSE-BRAND'):
        shutil.copyfile(ROOT / name, tmp_path / name)
    (tmp_path / 'waku').mkdir()
    shutil.copyfile(ROOT / 'waku/__init__.py', tmp_path / 'waku/__init__.py')
    retired = ('index.html', 'style.css', 'waku-mark.svg', 'js/restored.js',
               'design/restored.css', 'fonts/restored.woff2', 'logos/restored.svg')
    for name in (*retired, 'career.html'):
        path = tmp_path / 'waku/ops/static' / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('Synthetic asset restoration.\n')
    for builder_cls in (SdistBuilder, WheelBuilder):
        manager = PluginManager()
        builder = builder_cls(str(tmp_path), plugin_manager=manager,
                              metadata=ProjectMetadata(str(tmp_path), manager))
        paths = {f.distribution_path for f in builder.recurse_included_files()}
        assert 'waku/ops/static/career.html' in paths
        assert not paths.intersection(f'waku/ops/static/{name}' for name in retired)
