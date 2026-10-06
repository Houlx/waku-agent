"""C2 removes general assembly while keeping standalone debugging contracts."""
import importlib.util
import sqlite3

import pytest

from waku.ops import debug


@pytest.mark.parametrize('module', (
    'app', 'connect', 'integrations', 'ops.dashboard', 'ops.browser_agent',
    'ops.settings_api', 'ops.commands',
))
def test_general_facades_are_unavailable(module):
    assert importlib.util.find_spec('waku.' + module) is None


def test_debug_sql_is_read_only_and_path_is_confined(tmp_path, monkeypatch):
    monkeypatch.setenv('WAKU_HOME', str(tmp_path))
    conn = sqlite3.connect(tmp_path / 'state.db')
    conn.execute('CREATE TABLE sentinel(value TEXT)')
    conn.execute("INSERT INTO sentinel VALUES('retained')")
    conn.commit()
    conn.close()
    assert debug.run_query({'sql': 'SELECT * FROM sentinel'})['rows'] == [['retained']]
    assert 'error' in debug.run_query({'sql': 'DELETE FROM sentinel'})
    assert 'error' in debug.run_query({'sql': 'WITH x AS (SELECT 1) DELETE FROM sentinel'})
    assert 'error' in debug.run_query({'sql': 'SELECT 1; SELECT 2'})
    assert 'outside' in debug.reveal_path('../outside')['error']
    outside = tmp_path.parent / 'outside'
    outside.mkdir(exist_ok=True)
    (tmp_path / 'escape').symlink_to(outside, target_is_directory=True)
    assert 'outside' in debug.reveal_path('escape')['error']
    assert debug.run_query({'sql': 'SELECT * FROM sentinel'})['rows'] == [['retained']]
