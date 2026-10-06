"""Provider configuration shared by Career.

This module imports no integrations or general runtime. The caller supplies reload
ownership and, for Career, holds its execution lock across the entire transaction.
"""
from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from waku.loop.models import PROVIDERS, Provider, models_for


@dataclass(frozen=True)
class ProviderResult:
    ok: bool
    error: str = ""
    can_force: bool = False
    changed: bool = False


def redact_error(exc, values=()):
    message = str(exc)
    # Provider/SDK errors can echo both candidate and existing credentials.
    secrets = [os.getenv(p.key_env, "") for p in PROVIDERS.values()]
    secrets += [os.getenv("WAKU_API_KEY", ""), *values]
    for secret in sorted((str(v) for v in secrets if v), key=len, reverse=True):
        message = message.replace(secret, "***")
    return message or "provider configuration failed"


def _env_path() -> Path:
    from dotenv import find_dotenv

    return Path(find_dotenv(usecwd=True) or ".env")


def _write_updates(updates: Mapping[str, str], clear: tuple[str, ...]) -> None:
    from dotenv import set_key, unset_key

    path = _env_path()
    for name in clear:
        unset_key(str(path), name)
        os.environ.pop(name, None)
    for name, value in updates.items():
        set_key(str(path), name, value)
        os.environ[name] = value


def _restore(path: Path, contents: str | None, environment: Mapping[str, str | None]) -> None:
    if contents is None:
        try:
            path.unlink()
        except FileNotFoundError:
            pass
    else:
        path.write_text(contents, encoding="utf-8")
    for name, value in environment.items():
        if value is None:
            os.environ.pop(name, None)
        else:
            os.environ[name] = value


def probe_provider(values: Mapping[str, str]) -> None:
    # Catalog has the provider-specific URL logic; a list operation is safe and
    # is deliberately the same non-writing check used by the existing UI.
    from waku.ops import catalog

    provider = next((name for name, item in PROVIDERS.items() if item.key_env in values), "")
    if not provider:
        return
    # A Save must validate the candidate key/endpoint, never a cached result
    # produced by a previous credential for the same URL.
    result = catalog.list_models(provider, use_cache=False)
    if result.get("error"):
        raise ValueError(result["error"])


def _provider_can_serve(name: str) -> bool:
    """Whether `name` could answer a turn right now: it exists, and it has a
    key. `bool(env.get(key_env))` is the same test the Models grid colours a
    card with, so the two cannot disagree about what "configured" means."""
    selected = PROVIDERS.get(name)
    if selected is None:
        # Names a provider this build does not have. A stored setting outlives
        # the code that gave it meaning: a row removed from a release leaves
        # every user who had selected it pointing at nothing.
        return False
    return bool(os.environ.get(selected.key_env, ""))


def _adoptable(selected: Provider, key: str | None) -> bool:
    """Adopt only a newly entered key when the current provider has none."""
    return bool(key) and not _provider_can_serve(
        os.environ.get("WAKU_PROVIDER", ""))


def apply_provider(provider: str, *, key: str | None = None, model: str | None = None,
                   small_model: str | None = None, base_url: str | None = None,
                   custom_key: str | None = None, force: bool = False,
                   activate: bool = True, reload=None, probe=None,
                   env_path=None, write_updates=None, restore=None) -> ProviderResult:
    """Save provider fields and optionally make that provider active."""
    if provider not in PROVIDERS:
        return ProviderResult(False, error="unknown provider")
    from waku.ops import catalog

    probe = probe or probe_provider
    env_path = env_path or _env_path
    write_updates = write_updates or _write_updates
    restore = restore or _restore

    previous = os.environ.get("WAKU_PROVIDER", "")
    selected = PROVIDERS[provider]
    # Adding another provider must not hijack a working setup. The first key
    # recovers an unconfigured or removed current provider, even on a modal save.
    if not activate and _adoptable(selected, key):
        activate = True
    switching = activate and provider != previous
    updates: dict[str, str] = {"WAKU_PROVIDER": provider} if activate else {}
    if model is not None:
        updates["WAKU_MODEL"] = model
    elif switching:
        updates["WAKU_MODEL"] = catalog.default_model_for(provider)
    if small_model is not None:
        updates["WAKU_SMALL_MODEL"] = small_model
    elif switching:
        updates["WAKU_SMALL_MODEL"] = ""
    if key:
        updates[selected.key_env] = key
    # Regional providers own their endpoint choice.  Keeping it beside that
    # provider's key prevents a MiniMax URL, for example, from leaking into Kimi
    # after a switch.  A legacy WAKU_BASE_URL for the current provider is
    # migrated the next time its endpoint is saved.
    if selected.base_url_env and (base_url is not None or switching):
        legacy = os.environ.get("WAKU_BASE_URL", "") if provider == previous else ""
        selected_base_url = (base_url or legacy or selected.configured_base_url() or "").strip()
        if selected_base_url:
            updates[selected.base_url_env] = selected_base_url
        updates["WAKU_BASE_URL"] = ""
    elif base_url is not None:
        updates["WAKU_BASE_URL"] = base_url
    if custom_key is not None:
        updates["WAKU_API_KEY"] = custom_key
    # The modal always submits its selected Base URL.  Compare effective values
    # rather than field presence so reopening and saving an unchanged provider
    # does not perform a synchronous network probe every time.
    current_key = os.environ.get(selected.key_env, "")
    legacy_base_url = os.environ.get("WAKU_BASE_URL", "") if provider == previous else ""
    current_base_url = legacy_base_url or selected.configured_base_url() or ""
    candidate_base_url = (
        updates.get(selected.base_url_env, current_base_url)
        if selected.base_url_env else updates.get("WAKU_BASE_URL", current_base_url)
    )
    key_changed = bool(key and key != current_key)
    base_url_changed = (
        base_url is not None
        and candidate_base_url.rstrip("/") != current_base_url.rstrip("/")
    )
    changed_updates = {
        name: value for name, value in updates.items()
        if (os.environ.get(name) or "") != value
    }
    path = env_path()
    contents = path.read_text(encoding="utf-8") if path.exists() else None
    before = {name: os.environ.get(name) for name in changed_updates}
    try:
        # Validate a newly supplied key before persisting it.  catalog's probe
        # intentionally reads environment variables, so expose only the
        # candidate values for the duration of this non-writing request.
        candidate_key = (key or os.environ.get(selected.key_env, "") if selected.scoped_credentials
                         else custom_key or key or os.environ.get("WAKU_API_KEY", "")
                         or os.environ.get(selected.key_env, ""))
        custom_key_changed = custom_key is not None and custom_key != os.getenv("WAKU_API_KEY", "")
        if candidate_key and (key_changed or base_url_changed or custom_key_changed) and not force:
            probe_names = {"WAKU_PROVIDER", selected.key_env, "WAKU_BASE_URL", "WAKU_API_KEY"}
            if selected.base_url_env:
                probe_names.update({selected.base_url_env, "WAKU_BASE_URL"})
            probe_before = {name: os.environ.get(name) for name in probe_names}
            os.environ["WAKU_PROVIDER"] = provider
            if key:
                os.environ[selected.key_env] = key
            if custom_key is not None:
                os.environ["WAKU_API_KEY"] = custom_key
            if selected.base_url_env and selected.base_url_env in updates:
                os.environ[selected.base_url_env] = updates[selected.base_url_env]
                os.environ["WAKU_BASE_URL"] = ""
            elif base_url is not None:
                os.environ["WAKU_BASE_URL"] = base_url
            try:
                probe({selected.key_env: candidate_key})
            finally:
                for name, old in probe_before.items():
                    if old is None:
                        os.environ.pop(name, None)
                    else:
                        os.environ[name] = old
        if changed_updates:
            write_updates(changed_updates, ())
        affects_active_agent = bool(changed_updates) and (provider == previous or activate)
        if affects_active_agent and reload is not None and (error := reload()):
            raise RuntimeError(error)
    except Exception as exc:
        restore(path, contents, before)
        result = redact_error(exc, (before.get(selected.key_env), before.get("WAKU_API_KEY"),
                                     updates.get(selected.key_env), updates.get("WAKU_API_KEY")))
        return ProviderResult(False, error=result, can_force=bool(key or os.environ.get(selected.key_env)))
    return ProviderResult(True, changed=affects_active_agent)


def provider_status(settings):
    """Return resolved model access without constructing a client or probing."""
    from waku.ops.catalog import default_model_for

    selected = PROVIDERS.get(settings.provider)
    scoped = bool(selected and selected.scoped_credentials)
    key = (os.getenv(selected.key_env, '') if scoped else
           settings.api_key or (os.getenv(selected.key_env, '') if selected else '')).strip()
    model, _ = models_for(settings.provider, settings.model, settings.small_model)
    endpoint = (selected.configured_base_url() if scoped else
                settings.base_url or (selected.configured_base_url() if selected else None))
    visible = bool(selected and selected.is_visible())
    error = ''
    if not visible:
        error = f"Provider '{settings.provider}' is unavailable. Choose a configured provider."
    elif not key:
        error = f'Set {selected.key_env} in provider setup to run Career stages.'
    providers = []
    for name, item in PROVIDERS.items():
        if not item.is_visible():
            continue
        stored = os.getenv(item.key_env, '').strip()
        providers.append({
            'key': name, 'name': item.label_text(name), 'configured': bool(stored),
            'last4': stored[-4:] if stored else '',
            'model': default_model_for(name) or item.models_now()[0],
            'base_url': item.configured_base_url() or '',
            'endpoints': [{'label': e.label, 'base_url': e.base_url} for e in item.endpoints],
        })
    return {'provider': settings.provider, 'model': model, 'endpoint': endpoint or '',
            'configured': visible and bool(key), 'last4': key[-4:] if key else '',
            'error': error, 'providers': providers}
