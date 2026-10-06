"""Package metadata remains available for installed Career users."""
import tomllib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize("field", ["urls", "keywords", "classifiers"])
def test_pypi_metadata_is_present(field):
    metadata = tomllib.loads((ROOT / "pyproject.toml").read_text())
    assert metadata["project"].get(field)
