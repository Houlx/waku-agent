"""Exercise the transitional Career server and CLI using isolated local sockets."""
import http.client
import json
import sqlite3
import threading

import pytest

from waku.ops import career_dashboard
from waku.runtime.career_runtime import CareerRuntime


@pytest.fixture
def server(tmp_path, monkeypatch):
    monkeypatch.setenv('WAKU_HOME', str(tmp_path))
    monkeypatch.delenv('OTEL_EXPORTER_OTLP_ENDPOINT', raising=False)
    instance = career_dashboard.CareerServer(('127.0.0.1', 0))
    worker = threading.Thread(target=instance.serve_forever)
    worker.start()
    try:
        yield instance
    finally:
        instance.shutdown()
        instance.server_close()
        worker.join(5)


def request(server, path, payload=None):
    conn = http.client.HTTPConnection(*server.server_address, timeout=5)
    method = 'GET' if payload is None else 'POST'
    conn.request(method, path, body=None if payload is None else json.dumps(payload),
                 headers={'Content-Type': 'application/json'})
    result = conn.getresponse()
    value = (result.status, result.getheader('Content-Type'), result.read())
    conn.close()
    return value


def test_http_career_provider_and_static_surface(server):
    status, ctype, data = request(server, '/api/career')
    assert status == 200 and ctype == 'application/json'
    assert json.loads(data) == {'profile': None, 'evidence': [], 'jobs': []}
    status, _, data = request(server, '/api/provider-status')
    assert status == 200 and 'model' in json.loads(data)
    status, ctype, data = request(server, '/')
    assert status == 200 and ctype.startswith('text/html') and b'Career Agent' in data
    status, ctype, _ = request(server, '/static/career/render.js')
    assert status == 200 and ctype == 'text/javascript'
    assert server.runtime.client is None
    for path in ('/static/index.html', '/static/style.css', '/static/js/main.js',
                 '/static/design/tokens.css', '/api/chat', '/api/data', '/api/events', '/api/connections',
                 '/static/../career_dashboard.py', '/static/%2e%2e/career_dashboard.py'):
        status, ctype, data = request(server, path)
        assert status == 404 and ctype == 'application/json' and 'error' in json.loads(data)
    status, _, _ = request(server, '/api/chat', {'message': 'Do not execute'})
    assert status == 404 and server.runtime.client is None
    status, _, data = request(server, '/api/career', [])
    assert status == 200 and 'JSON object' in json.loads(data)['error']
    status, _, data = request(server, '/api/providers', {'provider': 'unknown'})
    assert status == 200 and not json.loads(data)['ok']


@pytest.mark.parametrize('args', [[], ['career']])
def test_cli_career_dispatch_and_shutdown(tmp_path, monkeypatch, capsys, args):
    from waku import __main__

    monkeypatch.setenv('WAKU_HOME', str(tmp_path))
    monkeypatch.setenv('WAKU_DASHBOARD_PORT', '0')
    monkeypatch.setenv('WAKU_DASHBOARD_HOST', '127.0.0.1')
    monkeypatch.setenv('OTEL_EXPORTER_OTLP_ENDPOINT', '')
    monkeypatch.setattr('sys.argv', ['waku', *args])
    runtimes, connections = [], []

    def stop(server):
        runtimes.append(server.runtime)
        connections.append(server.runtime.conn)
        raise KeyboardInterrupt

    monkeypatch.setattr(career_dashboard.CareerServer, 'serve_forever', stop)
    __main__.main()
    assert '/#overview' in capsys.readouterr().out
    assert runtimes[0]._closed
    with pytest.raises(sqlite3.ProgrammingError):
        connections[0].execute('SELECT 1')


def test_loopback_default(monkeypatch):
    monkeypatch.delenv('WAKU_DASHBOARD_HOST', raising=False)
    assert career_dashboard.bind_host() == '127.0.0.1'


def test_server_does_not_close_injected_runtime(tmp_path):
    from waku.config import Settings

    runtime = CareerRuntime(Settings(home=tmp_path))
    server = career_dashboard.CareerServer(('127.0.0.1', 0), runtime=runtime)
    server.server_close()
    assert runtime.state()['profile'] is None
    runtime.close()


def test_socket_failure_is_not_masked(monkeypatch):
    def denied(*args, **kwargs):
        raise PermissionError('Socket denied')

    monkeypatch.setattr('socket.socket', denied)
    with pytest.raises(PermissionError, match='Socket denied'):
        career_dashboard.CareerServer(('127.0.0.1', 0))


@pytest.mark.parametrize(('command', 'module'), [
    ('dashboard', 'waku.ops.dashboard'), ('chat', 'waku.gateway.cli')])
def test_explicit_rollback_dispatch(monkeypatch, command, module):
    import importlib

    from waku import __main__

    calls = []
    monkeypatch.setattr(importlib.import_module(module), 'main', lambda: calls.append(command))
    monkeypatch.setattr('sys.argv', ['waku', command])
    __main__.main()
    assert calls == [command]
