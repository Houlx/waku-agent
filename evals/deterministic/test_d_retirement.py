"""Final cleanup preserves Career assets, configuration and existing home data."""
from dataclasses import fields
from pathlib import Path

from waku.config import Settings
from waku.ops.career_dashboard import CAREER_ASSETS

ROOT = Path(__file__).resolve().parents[2]


def test_static_tree_is_the_career_allowlist():
    static = ROOT / 'waku/ops/static'
    files = {p.relative_to(static).as_posix() for p in static.rglob('*') if p.is_file()}
    assert files == CAREER_ASSETS | {'README.md'}


def test_settings_have_only_retained_runtime_fields():
    assert {f.name for f in fields(Settings)} == {
        'provider', 'api_key', 'base_url', 'model', 'small_model', 'home',
        'max_iterations', 'max_tokens', 'otel_endpoint',
    }


def test_obsolete_env_values_are_ignored_and_home_data_survives(tmp_path, monkeypatch):
    for variable in ('WAKU_HISTORY_TURNS', 'WAKU_CONSOLIDATE_EVERY',
                     'WAKU_RETRIEVAL_TOP_K', 'WAKU_DISABLED_PROVIDERS'):
        monkeypatch.setenv(variable, 'obsolete-value')
    existing = {name: b'preserved user data' for name in
                ('SOUL.md', 'state.db', 'usage.jsonl', '.env', 'outbox/old.txt', 'traces/old.jsonl')}
    for name, content in existing.items():
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
    settings = Settings(home=tmp_path)
    assert settings.ensure_home() == tmp_path
    for name, content in existing.items():
        assert (tmp_path / name).read_bytes() == content
    fresh = tmp_path / 'fresh'
    Settings(home=fresh).ensure_home()
    assert {p.name for p in fresh.iterdir()} == {'traces'}
