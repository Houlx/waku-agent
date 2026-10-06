"""Configuration — every knob is an env var, documented in .env.example.

No settings framework: a dataclass read once at startup. If you can read this
file, you can see the retained Career settings.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import NamedTuple

from dotenv import find_dotenv, load_dotenv


def _load_env() -> str:
    """Find the user's .env the way the user expects: from where they ARE.

    Bare `load_dotenv()` searches upward from the file that called it, not from
    the working directory. Inside a git checkout that is invisible — config.py
    lives in the project, so walking up from it lands on the project's .env and
    everything works. Installed from PyPI it walks up from site-packages,
    reaches the filesystem root, and finds nothing: the user stands in a folder
    holding a perfectly good .env and Waku reports "No API key". Reported from
    a clean install on 2026-07-31, from inside the repo folder itself.

    usecwd=True is the whole fix. The walk upward is kept on purpose, so
    running `waku` from a subdirectory of your project still finds the .env at
    its root — the same rule git, npm and pytest already taught everyone.

    Returns the path that was loaded (empty string if none) so provider errors can say WHICH file was read, rather than leaving
    people guessing between three .env files.
    """
    path = find_dotenv(usecwd=True)
    if path:
        load_dotenv(path)
    return path


DOTENV_PATH = _load_env()


class HomeChoice(NamedTuple):
    """Where Waku keeps its state, and which rule chose it."""
    path: Path
    rule: str   # "WAKU_HOME", "legacy" (a folder's ./.waku) or "global" (~/.waku)


# Printed to people with a legacy ./.waku. It copies the folder's contents, not
# the folder: `cp -R ./.waku ~/.waku` puts the copy at ~/.waku/.waku whenever
# ~/.waku already exists. It copies, never moves (public hard rule 1).
COPY_COMMAND = "mkdir -p ~/.waku && cp -R ./.waku/. ~/.waku/"


def resolve_home(env: Mapping[str, str] | None = None, cwd: Path | None = None,
                 user_home: Path | None = None) -> HomeChoice:
    """Waku's home is decided by the first rule that matches (spec 002):

    1. WAKU_HOME is set: use it.
    2. ./.waku/state.db exists and ~/.waku/state.db does not: keep using the
       folder's ./.waku. A person's older state stays available until they copy it.
    3. Otherwise: ~/.waku, so the same Career workspace opens from every folder.

    Rule 2 checks for ~/.waku/state.db, not for the ~/.waku folder. A ~/.waku
    holding unrelated files must not hide a person's retained state, and copying
    the old folder creates state.db, so the copy is what moves them over.
    """
    env = os.environ if env is None else env
    cwd = Path.cwd() if cwd is None else cwd
    user_home = Path.home() if user_home is None else user_home
    if env.get("WAKU_HOME"):
        return HomeChoice(Path(env["WAKU_HOME"]), "WAKU_HOME")
    legacy, global_home = cwd / ".waku", user_home / ".waku"
    if (legacy / "state.db").exists() and not (global_home / "state.db").exists():
        return HomeChoice(legacy, "legacy")
    return HomeChoice(global_home, "global")


def home_notice(cwd: Path | None = None, user_home: Path | None = None,
                env: Mapping[str, str] | None = None) -> str:
    """The one line people with a legacy ./.waku see at startup, or ""."""
    cwd = Path.cwd() if cwd is None else cwd
    choice = resolve_home(env=env, cwd=cwd, user_home=user_home)
    legacy = cwd / ".waku"
    if choice.rule == "legacy":
        return ("Career Agent is using ./.waku (your state from before v0.2). To move it to "
                f"~/.waku, where Career Agent looks from any folder: {COPY_COMMAND}")
    if (choice.rule == "global" and (legacy / "state.db").exists()
            and legacy.resolve() != choice.path.resolve()):
        return ("Career Agent is using ~/.waku and ignoring ./.waku in this folder, which holds "
                "older state. Nothing in it was moved or deleted.")
    return ""


def describe_home(choice: HomeChoice) -> str:
    """Describe the resolved runtime home: the resolved home and why."""
    why = {"WAKU_HOME": "set by WAKU_HOME",
           "legacy": "older memory in this folder, used until you copy it",
           "global": "the default"}[choice.rule]
    return f"{choice.path.resolve()} ({why})"


def _load_home_env() -> str:
    """Load <home>/.env, so a global install finds its key from any folder.

    The working directory's .env loads first (_load_env above) and may set
    WAKU_HOME, so the home is resolved after it. This file loads last and never
    overrides a value already set: a project's own .env always wins. Waku reads
    no .env outside these two places.

    Returns the path that was loaded, or "" when there is none or it is the
    same file the working directory already supplied.
    """
    path = resolve_home().path / ".env"
    if not path.is_file():
        return ""
    if DOTENV_PATH and Path(DOTENV_PATH).resolve() == path.resolve():
        return ""
    load_dotenv(path, override=False)
    return str(path)


HOME_DOTENV_PATH = _load_home_env()


@dataclass
class Settings:
    # --- LLM: pick a provider, set its key. See waku/loop/models.py PROVIDERS.
    provider: str = field(default_factory=lambda: os.getenv("WAKU_PROVIDER", "anthropic"))
    # Explicit overrides (optional): key, endpoint, and model ids. Left empty,
    # the provider's own key env var and default models are used.
    api_key: str = field(default_factory=lambda: os.getenv("WAKU_API_KEY", ""))
    base_url: str | None = field(default_factory=lambda: os.getenv("WAKU_BASE_URL") or None)
    model: str = field(default_factory=lambda: os.getenv("WAKU_MODEL", ""))
    # Secondary provider model retained for configuration compatibility.
    small_model: str = field(default_factory=lambda: os.getenv("WAKU_SMALL_MODEL", ""))
    # --- Home: where Waku keeps its state (Career DB and traces).
    # ~/.waku by default, so the same Career workspace opens from every folder; a
    # folder's older ./.waku stays active until it is copied. resolve_home()
    # above has the rules. Every file Waku writes is in it, so you can look.
    home: Path = field(default_factory=lambda: resolve_home().path)

    # --- Loop guardrails
    max_iterations: int = field(default_factory=lambda: int(os.getenv("WAKU_MAX_ITERATIONS", "10")))
    # Headroom matters for REASONING models (kimi-k3, gpt-5.x, gemini-*-pro):
    # they spend output tokens thinking before the answer, so a low cap makes
    # them hit stop_reason=max_tokens mid-thought and return an EMPTY reply
    # (watched kimi-k3 do exactly that at 2048). 8192 leaves room to think AND
    # answer; it's a ceiling, not a target, so efficient models still cost the same.
    max_tokens: int = field(default_factory=lambda: int(os.getenv("WAKU_MAX_TOKENS", "8192")))
    # --- Tracing (JSONL always; OTel exports if an endpoint is set)
    otel_endpoint: str = field(
        default_factory=lambda: os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "")
    )

    def ensure_home(self) -> Path:
        self.home.mkdir(parents=True, exist_ok=True)
        (self.home / "traces").mkdir(exist_ok=True)
        return self.home


def load_settings() -> Settings:
    return Settings()
