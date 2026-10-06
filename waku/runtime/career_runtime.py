"""Career assembly and owned resources; business rules stay in the coordinators."""
from __future__ import annotations

import threading
from dataclasses import asdict

from waku.config import load_settings
from waku.db import connect_career
from waku.loop.models import get_client, models_for
from waku.ops import provider_services
from waku.runtime import career


class CareerRuntime:
    """Serialize stages and complete provider transactions in a single local runtime.

    Injected clients/connections remain caller-owned. Factories create resources
    this owner closes on replacement or shutdown. Model construction stays lazy.
    """

    def __init__(self, settings=None, client=None, conn=None, *,
                 settings_factory=load_settings, client_factory=get_client,
                 connection_factory=connect_career):
        self.lock = threading.RLock()
        self._settings_factory = settings_factory
        self._client_factory = client_factory
        self._connection_factory = connection_factory
        self.settings = settings if settings is not None else settings_factory()
        self.settings.ensure_home()
        self.settings.model, self.settings.small_model = models_for(
            self.settings.provider, self.settings.model, self.settings.small_model)
        self.conn = conn if conn is not None else connection_factory(
            self.settings.home, check_same_thread=False)
        self.client = client
        self._owns_conn = conn is None
        self._owns_client = False
        self._closed = False
        self.cleanup_errors = []

    def _check_open(self):
        if self._closed:
            raise RuntimeError('Career runtime is closed.')

    def state(self):
        with self.lock:
            self._check_open()
            return career.state(self.conn)

    def action(self, payload):
        with self.lock:
            self._check_open()
            if payload.get('action') in {'normalize', 'analyze_job', 'generate_resume'}:
                if self.client is None:
                    try:
                        client = self._client_factory(self.settings)
                    except SystemExit as exc:
                        raise ValueError(provider_services.redact_error(exc)) from None
                    self.client = client
                    self._owns_client = True
                return career.action(self.conn, payload, self.settings, self.client)
            return career.action(self.conn, payload)

    def provider_status(self):
        with self.lock:
            self._check_open()
            return provider_services.provider_status(self.settings)

    def models(self, provider=None):
        from waku.ops.catalog import list_models

        # Catalog reads credentials from the environment; exclude candidate writes.
        with self.lock:
            self._check_open()
            if provider is not None and (provider not in provider_services.PROVIDERS
                                        or not provider_services.PROVIDERS[provider].is_visible()):
                return {'error': 'Provider is unavailable.'}
            result = list_models(provider)
            if result.get('error'):
                result['error'] = provider_services.redact_error(result['error'])
            return result

    def configure_provider(self, payload):
        with self.lock:
            self._check_open()
            allowed = {'provider', 'key', 'model', 'small_model', 'base_url',
                       'custom_key', 'force', 'activate'}
            if set(payload) - allowed:
                raise ValueError('Unknown provider configuration field.')
            result = provider_services.apply_provider(**payload, reload=self.reload)
            return {**asdict(result), 'status': self.provider_status()}

    def reload(self, before_swap=None):
        """Build a candidate before swapping; retain usable resources on failure."""
        with self.lock:
            self._check_open()
            conn = client = None
            try:
                settings = self._settings_factory()
                settings.ensure_home()
                settings.model, settings.small_model = models_for(
                    settings.provider, settings.model, settings.small_model)
                conn = self._connection_factory(settings.home, check_same_thread=False)
                if self.client is not None:
                    client = self._client_factory(settings)
                if before_swap is not None and (error := before_swap()):
                    raise RuntimeError(error)
            except (Exception, SystemExit) as exc:
                self._release(client, conn)
                return provider_services.redact_error(exc)
            old_client = self.client if self._owns_client else None
            old_conn = self.conn if self._owns_conn else None
            self.settings, self.conn, self.client = settings, conn, client
            self._owns_conn, self._owns_client = True, client is not None
            # Cleanup failures cannot turn a completed swap into config rollback.
            self._release(old_client, old_conn)
            return None

    def _release(self, client, conn):
        for resource in (client, conn):
            if resource is not None and callable(getattr(resource, 'close', None)):
                try:
                    resource.close()
                except Exception as exc:
                    self.cleanup_errors.append(type(exc).__name__)

    def close(self):
        with self.lock:
            if self._closed:
                return
            self._closed = True
            self._release(self.client if self._owns_client else None,
                          self.conn if self._owns_conn else None)
            self.client = self.conn = None


# The old dashboard also dispatches Career here, without borrowing its chat agent.
_runtime = None
_runtime_lock = threading.Lock()


def current_runtime():
    global _runtime
    with _runtime_lock:
        if _runtime is None:
            _runtime = CareerRuntime()
        return _runtime


def close_runtime():
    global _runtime
    with _runtime_lock:
        if _runtime is not None:
            _runtime.close()
            _runtime = None


def peek_runtime():
    """Read the transitional singleton without initializing Career."""
    return _runtime
