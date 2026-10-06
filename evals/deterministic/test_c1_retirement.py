"""Retired C1 features stay unavailable, and Career preserves dormant user data."""
import importlib.util
import sqlite3
import tomllib
from pathlib import Path

import pytest

from waku.config import Settings
from waku.runtime.career_runtime import CareerRuntime

ROOT = Path(__file__).resolve().parents[2]
RETIRED = (
    'memory', 'gateway', 'graph', 'runtime.session',
    'tools._env', 'tools.apple', 'tools.calendar', 'tools.experimental',
    'tools.github', 'tools.google_calendar', 'tools.memory_admin', 'tools.messages',
    'tools.notes', 'tools.search', 'tools.workspace', 'tools.mcp_cli',
    'tools.mcp_client', 'tools.mcp_oauth', 'tools.waku_memory',
    'ops.arena', 'ops.memory_arena', 'ops.judgment_arena', 'ops.judgment_cases',
    'ops.compare_history', 'ops.coding_eval', 'ops.judge', 'ops.scoring',
    'ops.brief', 'ops.gather', 'ops.triage',
)


@pytest.mark.parametrize('module', RETIRED)
def test_retired_modules_are_unavailable(module):
    assert importlib.util.find_spec('waku.' + module) is None


def test_feature_extras_have_no_remaining_dependency_contract():
    metadata = tomllib.loads((ROOT / 'pyproject.toml').read_text())
    assert set(metadata['project']['optional-dependencies']) == {'eval', 'dev', 'tracing'}


def test_startup_shutdown_preserves_dormant_files_and_legacy_fts(tmp_path):
    files = {'SOUL.md': b'Legacy persona\n', 'MEMORY.md': b'Legacy mirror\n',
             'chat.jsonl': b'{"text":"legacy"}\n', 'usage.jsonl': b'{"tokens":7}\n',
             'mcp.json': b'{"mcpServers":{}}\n', 'credentials.json': b'{"test":"fixture"}\n',
             'skills/custom/SKILL.md': b'User-installed instructions\n',
             'traces/legacy.jsonl': b'{"type":"legacy"}\n', '.env': b'# User configuration\n'}
    for name, contents in files.items():
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(contents)
    conn = sqlite3.connect(tmp_path / 'state.db')
    conn.executescript((ROOT / 'evals/fixtures/legacy.sql').read_text())
    conn.execute("INSERT INTO facts(subject,content) VALUES('legacy','Untouched sentinel')")
    conn.execute("INSERT INTO episodes(happened_at,summary) VALUES('2020-01-01','Untouched sentinel')")
    conn.execute("INSERT INTO chat_log(role,content) VALUES('user','Untouched sentinel')")
    conn.execute("INSERT INTO calendar_events(title,start) VALUES('Legacy','2020-01-01')")
    conn.commit()
    tables = [row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")]
    before = {name: list(conn.execute(f'SELECT * FROM "{name}"')) for name in tables}
    conn.close()

    runtime = CareerRuntime(Settings(home=tmp_path, model='offline', otel_endpoint=''))
    assert runtime.state() == {'profile': None, 'evidence': [], 'jobs': []}
    assert runtime.client is None
    runtime.close()

    conn = sqlite3.connect(tmp_path / 'state.db')
    assert {name: list(conn.execute(f'SELECT * FROM "{name}"')) for name in tables} == before
    assert conn.execute("SELECT rowid FROM facts_fts WHERE facts_fts MATCH 'sentinel'").fetchall() == [(1,)]
    assert conn.execute("SELECT rowid FROM episodes_fts WHERE episodes_fts MATCH 'sentinel'").fetchall() == [(1,)]
    conn.close()
    assert {name: (tmp_path / name).read_bytes() for name in files} == files
