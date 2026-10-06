"""The generated template follows Career and the shared provider registry."""
import os
import subprocess
import sys
import tomllib
from pathlib import Path

from scripts.generate_env_example import main, render_env_example

ROOT = Path(__file__).resolve().parents[2]


def assignments(text):
    return {line.lstrip("# ").split("=", 1)[0]
            for line in text.splitlines() if "=" in line and not line.startswith("# Process")}


def test_checked_in_template_matches_and_covers_retained_configuration():
    assert main(["--check"]) == 0
    variables = assignments(render_env_example())
    assert {
        "WAKU_PROVIDER", "WAKU_API_KEY", "WAKU_BASE_URL", "WAKU_MODEL", "WAKU_SMALL_MODEL",
        "WAKU_HOME", "WAKU_MAX_ITERATIONS", "WAKU_MAX_TOKENS", "WAKU_LLM_TIMEOUT",
        "OTEL_EXPORTER_OTLP_ENDPOINT", "WAKU_DASHBOARD_HOST", "WAKU_DASHBOARD_PORT", "PORT",
    } <= variables
    providers = tomllib.loads((ROOT / "waku/providers.toml").read_text())
    for provider in providers.values():
        if provider.get("hidden_unless_env"):
            assert provider["key_env"] not in variables
            continue
        for field in ("key_env", "base_url_env", "model_env", "small_model_env"):
            if provider.get(field):
                assert provider[field] in variables
    assert not {"TELEGRAM_BOT_TOKEN", "WAKU_SEMANTIC_STORE", "WAKU_CONSOLIDATE_EVERY"} & variables


def test_new_provider_fields_are_generated():
    assert assignments(render_env_example({"synthetic": {
        "key_env": "SYNTHETIC_API_KEY", "base_url_env": "SYNTHETIC_BASE_URL",
        "model_env": "SYNTHETIC_MODEL", "small_model_env": "SYNTHETIC_SMALL_MODEL",
    }})) >= {"SYNTHETIC_API_KEY", "SYNTHETIC_BASE_URL", "SYNTHETIC_MODEL", "SYNTHETIC_SMALL_MODEL"}


def test_stale_template_fails_and_write_repairs_only_requested_file(tmp_path):
    path = tmp_path / "example"
    path.write_text(render_env_example().replace("# WAKU_HOME=", "# REMOVED_HOME="))
    real_env = tmp_path / ".env"
    real_env.write_text("user-owned\n")
    assert main(["--check", "--path", str(path)]) == 1
    assert main(["--write", "--path", str(path)]) == 0
    assert main(["--check", "--path", str(path)]) == 0
    assert real_env.read_text() == "user-owned\n"


def test_generator_imports_no_general_backend_or_user_configuration(tmp_path):
    code = f'''
import sys
sys.path.insert(0, {str(ROOT)!r})
from scripts.generate_env_example import render_env_example
render_env_example()
assert not any(n == 'waku' or n.startswith('waku.') for n in sys.modules)
'''
    subprocess.run([sys.executable, "-c", code], cwd=tmp_path, check=True,
                   env={**os.environ, "WAKU_HOME": str(tmp_path / "absent")})
    assert not (tmp_path / "absent").exists()
