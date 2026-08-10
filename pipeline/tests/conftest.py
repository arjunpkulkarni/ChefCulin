from pathlib import Path

import pytest

from culin_etl.build import build_artifacts
from culin_etl.parse import load_recipes

FIXTURE = Path(__file__).parent / "fixtures" / "mini_recipes.csv"


@pytest.fixture(scope="session")
def fixture_path() -> Path:
    return FIXTURE


@pytest.fixture(scope="session")
def raw_recipes(fixture_path):
    return list(load_recipes(fixture_path))


@pytest.fixture(scope="session")
def artifacts(fixture_path):
    return build_artifacts(fixture_path)
