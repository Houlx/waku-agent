"""Career owns assembly without general assistant imports or destructive startup."""
from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
import threading
from pathlib import Path

import pytest

from evals.deterministic.test_career_acceptance import JOBS, RAW, AcceptanceClient
from waku.config import Settings
from waku.db import connect, connect_career
from waku.ops import provider_services
from waku.runtime.career_runtime import CareerRuntime


def journey(runtime, job, language='English'):
    runtime.action({'action': 'save_onboarding', 'raw': RAW})
    runtime.action({'action': 'normalize'})
    runtime.action({'action': 'confirm'})
    result = runtime.action({'action': 'analyze_job', 'jd': job['jd']})
    return runtime.action({'action': 'generate_resume', 'job_id': result['job_id'], 'language': language})


@pytest.mark.parametrize('job', JOBS, ids=lambda j: j['title'])
def test_runtime_complete_journey_and_career_only_schema(tmp_path, job):
    client = AcceptanceClient(job)
    runtime = CareerRuntime(Settings(home=tmp_path, model='offline', otel_endpoint=''), client=client)
    result = journey(runtime, job)
    assert result['jobs'][0]['coverage'] == job['score']
    assert [r['status'] for r in result['jobs'][0]['requirements']] == job['statuses']
    assert result['jobs'][0]['resume']['content']['records']
    tables = {r[0] for r in runtime.conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert not {'chat_log', 'facts', 'episodes', 'calendar_events', 'notes'} & tables
    usage = [json.loads(line) for line in (tmp_path / 'usage.jsonl').read_text().splitlines()]
    assert usage and all(row['model'] == 'offline' for row in usage)
    traces = [json.loads(line) for path in (tmp_path / 'traces').glob('*.jsonl') for line in path.read_text().splitlines()]
    assert sum(r['type'] == 'turn_end' for r in traces) == 4
    conn = runtime.conn
    runtime.close()
    with pytest.raises(sqlite3.ProgrammingError):
        conn.execute('SELECT 1')
    reopened = CareerRuntime(Settings(home=tmp_path, model='offline', otel_endpoint=''))
    assert reopened.state() == result
    reopened.close()


def test_import_startup_and_execution_with_general_modules_unavailable(tmp_path):
    # A new interpreter catches package-initializer dependencies hidden by pytest imports.
    script = '''
import importlib.abc
import socket
import subprocess
import sys
class RejectGeneral(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        blocked = ('waku.app', 'waku.memory', 'waku.runtime.session', 'waku.gateway',
                   'waku.graph', 'waku.integrations', 'waku.ops.browser_agent', 'waku.ops.dashboard')
        if any(fullname == p or fullname.startswith(p + '.') for p in blocked):
            raise AssertionError('Unrelated import: ' + fullname)
        if fullname.startswith('waku.tools.') and fullname not in ('waku.tools.registry', 'waku.tools.career'):
            raise AssertionError('General tool import: ' + fullname)
sys.meta_path.insert(0, RejectGeneral())
def forbidden(*args, **kwargs):
    raise AssertionError('Unrelated network call or subprocess')
socket.create_connection = forbidden
subprocess.Popen = forbidden
from waku.ops.career_dashboard import CareerServer
from evals.deterministic.test_career_runtime import journey, AcceptanceClient, JOBS
server = CareerServer(('127.0.0.1', 0))
runtime = server.runtime
assert runtime.client is None
assert runtime.provider_status()['configured'] is False
assert runtime.state()['profile'] is None
runtime._client_factory = lambda settings: AcceptanceClient(JOBS[0])
result = journey(runtime, JOBS[0])
assert result['jobs'][0]['coverage'] == 50.0
assert result['jobs'][0]['resume']
server.server_close()
assert runtime._closed
'''
    env = {k: v for k, v in os.environ.items() if not k.startswith(('WAKU_', 'OTEL_'))}
    for provider in provider_services.PROVIDERS.values():
        env.pop(provider.key_env, None)
    env.update(WAKU_HOME=str(tmp_path / 'home'), WAKU_MODEL='offline',
               PYTHONPATH=str(Path(__file__).resolve().parents[2]))
    result = subprocess.run([sys.executable, '-c', script], cwd=tmp_path, env=env,
                            capture_output=True, text=True, timeout=20, check=False)
    assert result.returncode == 0, result.stdout + result.stderr


def snapshot(conn):
    tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
    return {table: sorted((tuple(r) for r in conn.execute(f'SELECT * FROM "{table}"')), key=repr)
            for table in tables}


def test_existing_database_values_and_fts_are_preserved(tmp_path):
    settings = Settings(home=tmp_path, model='offline', otel_endpoint='')
    settings.ensure_home()
    conn = connect(tmp_path)
    runtime = CareerRuntime(settings, client=AcceptanceClient(JOBS[0]), conn=conn)
    result = journey(runtime, JOBS[0])
    # Include explicit edits, inactive provenance and both failed/outdated artifacts.
    profile = result['profile']['normalized']
    profile['records'][0]['description'] += ' User correction.'
    runtime.action({'action': 'save_profile', 'profile': profile})
    runtime.action({'action': 'confirm'})
    conn.execute("UPDATE career_evidence SET active=0 WHERE source_id='frontend'")
    conn.execute("INSERT INTO jobs(id,raw_jd,status) VALUES('failed-job','Retained input','failed')")
    conn.execute("INSERT INTO chat_log(role,content) VALUES('user','Legacy sentinel')")
    conn.commit()
    before = snapshot(conn)
    assert result['jobs'][0]['resume']
    assert conn.execute('SELECT user_edits_json FROM career_profile').fetchone()[0] != '{}'
    search = [tuple(r) for r in conn.execute("SELECT rowid FROM career_evidence_fts WHERE career_evidence_fts MATCH 'RAG'")]
    conn.close()
    reopened = connect_career(tmp_path)
    assert snapshot(reopened) == before
    assert [tuple(r) for r in reopened.execute("SELECT rowid FROM career_evidence_fts WHERE career_evidence_fts MATCH 'RAG'")] == search
    assert reopened.execute('SELECT confirmed FROM career_profile').fetchone()[0] == 1
    assert reopened.execute('SELECT outdated FROM resumes').fetchone()[0] == 1
    reopened.close()


class OwnedClient:
    def __init__(self):
        self.closed = 0

    def close(self):
        self.closed += 1


@pytest.fixture
def configured(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv('WAKU_HOME', str(tmp_path / 'home'))
    monkeypatch.setenv('WAKU_PROVIDER', 'anthropic')
    monkeypatch.setenv('WAKU_MODEL', 'offline-old')
    monkeypatch.setenv('WAKU_SMALL_MODEL', '')
    monkeypatch.setenv('ANTHROPIC_API_KEY', 'secret-old-1234')
    monkeypatch.delenv('WAKU_API_KEY', raising=False)
    monkeypatch.delenv('WAKU_BASE_URL', raising=False)
    monkeypatch.delenv('OTEL_EXPORTER_OTLP_ENDPOINT', raising=False)
    monkeypatch.setattr(provider_services, 'probe_provider', lambda values: None)
    (tmp_path / '.env').write_text('# Keep this comment\nWAKU_MODEL=offline-old\n')
    return tmp_path


def test_owned_replacement_shutdown_and_failed_candidate_cleanup(configured):
    clients, connections = [], []

    def client_factory(settings):
        if settings.model == 'broken':
            raise SystemExit('bad secret-new-9876')
        client = OwnedClient()
        clients.append(client)
        return client

    def connection_factory(*args, **kwargs):
        conn = connect_career(*args, **kwargs)
        connections.append(conn)
        return conn

    runtime = CareerRuntime(client_factory=client_factory, connection_factory=connection_factory)
    # Build lazily through the public AI door; missing input does not destroy the client.
    with pytest.raises(ValueError, match='Save onboarding'):
        runtime.action({'action': 'normalize'})
    assert clients[0].closed == 0
    old_conn, old_settings = runtime.conn, runtime.settings
    before = (configured / '.env').read_text()
    failed = runtime.configure_provider({'provider': 'anthropic', 'model': 'broken', 'key': 'secret-new-9876'})
    assert not failed['ok'] and 'secret-new' not in json.dumps(failed)
    assert runtime.client is clients[0] and runtime.settings is old_settings
    assert runtime.conn is old_conn and old_conn.execute('SELECT 1').fetchone()[0] == 1
    assert (configured / '.env').read_text() == before
    assert os.environ['WAKU_MODEL'] == 'offline-old'
    with pytest.raises(sqlite3.ProgrammingError):
        connections[-1].execute('SELECT 1')
    success = runtime.configure_provider({'provider': 'anthropic', 'model': 'offline-new'})
    assert success['ok'] and success['status']['model'] == 'offline-new'
    assert clients[0].closed == 1
    with pytest.raises(sqlite3.ProgrammingError):
        old_conn.execute('SELECT 1')
    fresh_conn = runtime.conn
    runtime.close()
    runtime.close()
    assert clients[-1].closed == 1
    with pytest.raises(sqlite3.ProgrammingError):
        fresh_conn.execute('SELECT 1')
    with pytest.raises(RuntimeError, match='closed'):
        runtime.state()


def test_injected_resources_remain_caller_owned(tmp_path):
    settings = Settings(home=tmp_path, model='offline')
    settings.ensure_home()
    conn, client = connect_career(tmp_path), OwnedClient()
    runtime = CareerRuntime(settings, client=client, conn=conn)
    runtime.close()
    assert client.closed == 0
    assert conn.execute('SELECT 1').fetchone()[0] == 1
    conn.close()


def test_configuration_blocks_stages_until_probe_and_swap_finish(configured, monkeypatch):
    runtime = CareerRuntime(client_factory=lambda settings: OwnedClient())
    probing, release, entering, done = (threading.Event() for _ in range(4))
    seen, errors = [], []

    def probe(values):
        probing.set()
        assert release.wait(5)

    def action(conn, payload, settings=None, client=None):
        seen.append((os.environ['WAKU_MODEL'], settings.model))
        return {}

    monkeypatch.setattr(provider_services, 'probe_provider', probe)
    monkeypatch.setattr('waku.runtime.career.action', action)

    def configure():
        try:
            assert runtime.configure_provider({'provider': 'anthropic', 'model': 'offline-new',
                                               'key': 'secret-new-9876'})['ok']
        except BaseException as exc:
            errors.append(exc)

    def stage():
        entering.set()
        try:
            runtime.action({'action': 'normalize'})
        except BaseException as exc:
            errors.append(exc)
        finally:
            done.set()

    config_thread = threading.Thread(target=configure)
    stage_thread = threading.Thread(target=stage)
    config_thread.start()
    assert probing.wait(5)
    stage_thread.start()
    assert entering.wait(5)
    try:
        assert not done.wait(0.05)
    finally:
        release.set()
        config_thread.join(5)
        stage_thread.join(5)
        runtime.close()
    assert not config_thread.is_alive() and not stage_thread.is_alive()
    assert not errors
    assert seen == [('offline-new', 'offline-new')]


def test_missing_key_is_actionable_and_readiness_does_not_build_client(configured, monkeypatch):
    monkeypatch.delenv('ANTHROPIC_API_KEY')
    runtime = CareerRuntime()
    status = runtime.provider_status()
    assert not status['configured'] and 'ANTHROPIC_API_KEY' in status['error']
    assert runtime.client is None
    with pytest.raises(ValueError, match='ANTHROPIC_API_KEY'):
        runtime.action({'action': 'normalize'})
    assert runtime.client is None
    runtime.close()


def test_openai_adapter_closes_transport(monkeypatch):
    from waku.loop.models import OpenAICompatClient

    underlying = OwnedClient()
    monkeypatch.setattr('openai.OpenAI', lambda **kwargs: underlying)
    adapter = OpenAICompatClient('fake')
    adapter.close()
    assert underlying.closed == 1


def test_stage_excludes_config_mutations_and_other_stages(configured, monkeypatch):
    runtime = CareerRuntime(client_factory=lambda settings: OwnedClient())
    running, release, configuring, second_entering, config_done, second_done = (
        threading.Event() for _ in range(6))
    errors, results = [], []

    def action(conn, payload, settings=None, client=None):
        if payload.get('first'):
            running.set()
            assert release.wait(5)
            assert os.environ['WAKU_MODEL'] == settings.model == 'offline-old'
        results.append(payload.get('first', False))
        return {}

    monkeypatch.setattr('waku.runtime.career.action', action)

    def run(fn, finished=None):
        try:
            fn()
        except BaseException as exc:
            errors.append(exc)
        finally:
            if finished:
                finished.set()

    def configure():
        configuring.set()
        assert runtime.configure_provider({'provider': 'anthropic', 'model': 'offline-new'})['ok']

    def second():
        second_entering.set()
        runtime.action({'action': 'normalize'})

    first_thread = threading.Thread(target=run, args=(lambda: runtime.action({'action': 'normalize', 'first': True}),))
    config_thread = threading.Thread(target=run, args=(configure, config_done))
    second_thread = threading.Thread(target=run, args=(second, second_done))
    first_thread.start()
    assert running.wait(5)
    config_thread.start()
    second_thread.start()
    assert configuring.wait(5) and second_entering.wait(5)
    try:
        assert not config_done.wait(0.05) and not second_done.wait(0.05)
        assert os.environ['WAKU_MODEL'] == 'offline-old'
    finally:
        release.set()
        for thread in (first_thread, config_thread, second_thread):
            thread.join(5)
        runtime.close()
    assert not errors and results == [True, False]
    assert all(not t.is_alive() for t in (first_thread, config_thread, second_thread))


def test_provider_probe_failure_restores_custom_override_and_redacts(configured, monkeypatch):
    before = (configured / '.env').read_text()
    runtime = CareerRuntime()
    initial = runtime.settings

    def probe(values):
        assert os.environ['WAKU_API_KEY'] == 'custom-secret-9876'
        assert os.environ['WAKU_BASE_URL'] == 'https://candidate.example/v1'
        raise ValueError('Rejected custom-secret-9876')

    monkeypatch.setattr(provider_services, 'probe_provider', probe)
    result = runtime.configure_provider({'provider': 'anthropic', 'custom_key': 'custom-secret-9876',
                                         'base_url': 'https://candidate.example/v1'})
    assert not result['ok'] and 'custom-secret' not in json.dumps(result)
    assert os.getenv('WAKU_BASE_URL') is None and os.getenv('WAKU_API_KEY') is None
    assert runtime.settings is initial and runtime.client is None
    assert (configured / '.env').read_text() == before
    runtime.close()


def test_provider_defaults_region_and_nonactive_saves(configured, monkeypatch):
    monkeypatch.setenv('MOONSHOT_API_KEY', 'kimi-secret-3456')
    monkeypatch.setenv('MINIMAX_API_KEY', 'minimax-secret-5678')
    monkeypatch.delenv('MOONSHOT_BASE_URL', raising=False)
    monkeypatch.delenv('MINIMAX_BASE_URL', raising=False)
    monkeypatch.setenv('WAKU_SMALL_MODEL', 'claude-haiku-4-5-20251001')
    home = configured / 'home'
    home.mkdir()
    (home / 'models.json').write_text(json.dumps({'pinned': ['kimi:kimi-fixture-default']}))
    runtime = CareerRuntime()
    original = runtime.settings
    assert next(p for p in runtime.provider_status()['providers'] if p['key'] == 'kimi')['model'] == 'kimi-fixture-default'
    result = runtime.configure_provider({'provider': 'kimi', 'activate': False,
                                         'base_url': 'https://api.moonshot.cn/anthropic'})
    assert result['ok'] and runtime.settings is original
    assert runtime.settings.provider == 'anthropic'
    result = runtime.configure_provider({'provider': 'kimi'})
    assert result['ok'] and runtime.settings.model == 'kimi-fixture-default'
    assert runtime.settings.small_model == provider_services.PROVIDERS['kimi'].models_now()[1]
    assert result['status']['endpoint'] == 'https://api.moonshot.cn/anthropic'
    result = runtime.configure_provider({'provider': 'minimax'})
    assert result['ok'] and 'moonshot' not in result['status']['endpoint']
    assert 'minimax-secret' not in json.dumps(result)
    runtime.close()


def test_first_key_adoption_stays_lazy(configured, monkeypatch):
    monkeypatch.setenv('WAKU_PROVIDER', 'removed-provider')
    monkeypatch.delenv('ANTHROPIC_API_KEY')
    runtime = CareerRuntime(client_factory=lambda s: pytest.fail('Save constructed a client'))
    result = runtime.configure_provider({'provider': 'anthropic', 'key': 'first-secret-1234', 'activate': False})
    assert result['ok'] and result['status']['provider'] == 'anthropic'
    assert result['status']['configured'] and runtime.client is None
    assert 'first-secret' not in json.dumps(result)
    runtime.close()


def test_cleanup_failure_does_not_rollback_successful_swap(configured):
    class BrokenClose(OwnedClient):
        def close(self):
            super().close()
            raise RuntimeError('Transport cleanup failed')

    clients = []

    def factory(settings):
        client = BrokenClose()
        clients.append(client)
        return client

    runtime = CareerRuntime(client_factory=factory)
    with pytest.raises(ValueError):
        runtime.action({'action': 'normalize'})
    old_conn = runtime.conn
    assert runtime.configure_provider({'provider': 'anthropic', 'model': 'new'})['ok']
    assert runtime.client is clients[-1] and runtime.settings.model == 'new'
    assert runtime.cleanup_errors == ['RuntimeError']
    with pytest.raises(sqlite3.ProgrammingError):
        old_conn.execute('SELECT 1')
    runtime.close()


def test_legacy_provider_save_updates_career_without_constructing_waku(configured, monkeypatch):
    from waku import integrations
    from waku.ops import browser_agent
    from waku.runtime import career_runtime

    runtime = CareerRuntime()
    monkeypatch.setattr(career_runtime, '_runtime', runtime)
    monkeypatch.setattr(browser_agent, '_agent', None)
    monkeypatch.setattr(browser_agent, 'get_agent', lambda: pytest.fail('Provider save constructed Waku'))
    result = integrations.apply_provider('anthropic', model='legacy-new')
    assert result.ok and runtime.provider_status()['model'] == 'legacy-new'
    runtime.close()


def test_career_initialization_does_not_migrate_legacy_chat(tmp_path):
    conn = sqlite3.connect(tmp_path / 'state.db')
    conn.execute('CREATE TABLE chat_log(id INTEGER PRIMARY KEY, role TEXT, content TEXT)')
    conn.execute("INSERT INTO chat_log VALUES(7,'user','Untouched old chat')")
    conn.commit()
    conn.close()
    reopened = connect_career(tmp_path)
    assert [r[1] for r in reopened.execute('PRAGMA table_info(chat_log)')] == ['id', 'role', 'content']
    assert tuple(reopened.execute('SELECT * FROM chat_log').fetchone()) == (7, 'user', 'Untouched old chat')
    reopened.close()


def test_candidate_is_released_when_transitional_reload_fails(configured):
    runtime = CareerRuntime(client_factory=lambda settings: OwnedClient())
    with pytest.raises(ValueError):
        runtime.action({'action': 'normalize'})
    old_client, old_conn = runtime.client, runtime.conn
    candidates = []

    def factory(settings):
        client = OwnedClient()
        candidates.append(client)
        return client

    runtime._client_factory = factory
    assert runtime.reload(before_swap=lambda: 'Legacy replacement failed') == 'Legacy replacement failed'
    assert candidates[0].closed == 1
    assert runtime.client is old_client and runtime.conn is old_conn
    assert old_client.closed == 0
    assert old_conn.execute('SELECT 1').fetchone()[0] == 1
    runtime.close()


def test_readiness_and_client_agree_on_scoped_credentials_and_models(configured, monkeypatch):
    monkeypatch.setenv('WAKU_PROVIDER', 'waku-platform')
    monkeypatch.setenv('WAKU_PLATFORM_BASE_URL', 'http://proxy.example:8080')
    monkeypatch.setenv('WAKU_PLATFORM_TOKEN', 'platform-secret-4321')
    monkeypatch.setenv('WAKU_PLATFORM_MODEL', 'claude-platform-fixture')
    monkeypatch.setenv('WAKU_PLATFORM_SMALL_MODEL', 'claude-platform-small')
    monkeypatch.setenv('WAKU_API_KEY', 'unrelated-custom-secret-8765')
    monkeypatch.setenv('WAKU_BASE_URL', 'https://unrelated.example')
    monkeypatch.setenv('WAKU_MODEL', 'claude-opus-4-8')
    monkeypatch.setenv('WAKU_LLM_TIMEOUT', '17')
    kwargs = []
    client = OwnedClient()

    def native(**values):
        kwargs.append(values)
        return client

    monkeypatch.setattr('anthropic.Anthropic', native)
    runtime = CareerRuntime()
    status = runtime.provider_status()
    assert status['configured'] and status['model'] == 'claude-platform-fixture'
    assert status['endpoint'] == 'http://proxy.example:8080' and status['last4'] == '4321'
    assert 'unrelated-custom-secret' not in json.dumps(status)
    with pytest.raises(ValueError, match='Save onboarding'):
        runtime.action({'action': 'normalize'})
    assert kwargs == [{'api_key': 'platform-secret-4321', 'base_url': 'http://proxy.example:8080', 'timeout': 17.0}]
    assert runtime.settings.model == status['model']
    runtime.close()
    assert client.closed == 1


def test_explicit_model_catalog_preserves_priced_entries(configured, monkeypatch):
    import io

    from waku.ops import catalog

    monkeypatch.setenv('OPENROUTER_API_KEY', 'catalog-secret-4321')
    monkeypatch.setattr(catalog, '_models_cache', {})
    data = {'data': [{'id': 'fixture/priced', 'pricing': {'prompt': '0.000001', 'completion': '0.000002'}}]}
    monkeypatch.setattr('urllib.request.urlopen', lambda *args, **kwargs: io.BytesIO(json.dumps(data).encode()))
    runtime = CareerRuntime()
    result = runtime.models('openrouter')
    assert result['listed']
    assert result['models'][0]['price_in'] == 1.0 and result['models'][0]['price_out'] == 2.0
    assert runtime.client is None
    runtime.close()
