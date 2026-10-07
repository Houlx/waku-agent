"""Opt-in real Chromium journey with scripted loop proposals and a temporary home.

See docs/career.md for browser-only dependency setup. Ordinary evals skip this
journey unless WAKU_CAREER_BROWSER=1; the asset checks always run offline.
"""
import hashlib
import os
import subprocess
import threading
from pathlib import Path

import pytest
from dotenv import dotenv_values

from evals.deterministic.test_career_acceptance import JOBS, AcceptanceClient
from waku.config import Settings
from waku.ops import provider_services
from waku.ops.career_dashboard import CareerServer
from waku.runtime.career_runtime import CareerRuntime

ROOT = Path(__file__).resolve().parents[2]


class BrowserClient(AcceptanceClient):
    def create(self, **kwargs):
        if ('Extract atomic requirements' in kwargs['system']
                and 'Synthetic failure' in kwargs['messages'][0]['content']):
            raise ValueError('Synthetic extraction failure.')
        return super().create(**kwargs)


@pytest.mark.skipif(os.getenv('WAKU_CAREER_BROWSER') != '1', reason='Explicit browser opt-in')
def test_career_browser_journey(tmp_path, monkeypatch):
    checkout_env = ROOT / '.env'
    before = hashlib.sha256(checkout_env.read_bytes()).digest() if checkout_env.exists() else None
    monkeypatch.setenv('WAKU_HOME', str(tmp_path))
    monkeypatch.setenv('OTEL_EXPORTER_OTLP_ENDPOINT', '')
    monkeypatch.setattr(provider_services, '_env_path', lambda: tmp_path / '.env')
    monkeypatch.setenv('WAKU_PROVIDER', 'anthropic')
    monkeypatch.delenv('WAKU_MODEL', raising=False)
    monkeypatch.delenv('WAKU_API_KEY', raising=False)
    monkeypatch.delenv('WAKU_BASE_URL', raising=False)
    for provider in provider_services.PROVIDERS.values():
        monkeypatch.delenv(provider.key_env, raising=False)
        if provider.base_url_env:
            monkeypatch.delenv(provider.base_url_env, raising=False)
    settings = Settings(home=tmp_path, model='offline', otel_endpoint='')
    runtime = CareerRuntime(settings, client=BrowserClient(JOBS[0]),
                            client_factory=lambda _: BrowserClient(JOBS[0]))
    server = CareerServer(('127.0.0.1', 0), runtime=runtime)
    worker = threading.Thread(target=server.serve_forever)
    worker.start()
    try:
        env = {**os.environ, 'CAREER_BROWSER_URL': f'http://127.0.0.1:{server.server_port}'}
        result = subprocess.run(['node', str(ROOT / 'evals/fixtures/career_browser.cjs')],
                                env=env, text=True, timeout=180, check=False)
        assert result.returncode == 0
        assert dotenv_values(tmp_path / ".env").get("WAKU_MODEL") == "offline"
    finally:
        server.shutdown()
        server.server_close()
        worker.join(5)
        runtime.close()
        after = hashlib.sha256(checkout_env.read_bytes()).digest() if checkout_env.exists() else None
        assert after == before, "Browser harness changed the checkout dotenv file."
