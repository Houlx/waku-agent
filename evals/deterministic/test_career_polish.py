"""Offline plain-JavaScript UI preferences and delete state transitions."""
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_locale_and_delete_frontend_state():
    subprocess.run(['node', 'evals/fixtures/career_polish_state.cjs'], cwd=ROOT, check=True)
