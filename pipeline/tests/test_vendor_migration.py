"""Vendored flavor-network assets are present and buildable in-repo."""
from pathlib import Path

import pytest

from culin_etl.vendor_paths import (
    BRIDGING_SCORES_CSV,
    EDGES_CSV,
    FILTERED_GML,
    FLAVOR_NETWORK,
    FLAVOR_RECOMMENDER,
    HEALTH_MAPPING_TSV,
    INGR_INFO_TSV,
    LCC_EDGES_CSV,
    NETWORK_GML,
    RECIPE_CSV,
)


@pytest.mark.parametrize(
    "path",
    [
        EDGES_CSV,
        LCC_EDGES_CSV,
        NETWORK_GML,
        FILTERED_GML,
        BRIDGING_SCORES_CSV,
        INGR_INFO_TSV,
        HEALTH_MAPPING_TSV,
        RECIPE_CSV,
        FLAVOR_RECOMMENDER / "flavor_engine.py",
        FLAVOR_RECOMMENDER / "recommender.py",
    ],
)
def test_vendor_file_exists(path: Path):
    assert path.is_file(), f"missing vendored asset: {path}"


def test_edges_csv_has_rows():
    lines = EDGES_CSV.read_text(encoding="utf-8").splitlines()
    assert len(lines) > 90_000


def test_build_compound_from_vendor_csv(tmp_path):
    from importlib.util import module_from_spec, spec_from_file_location

    script = Path(__file__).resolve().parents[1] / "scripts" / "build_compound_artifacts.py"
    spec = spec_from_file_location("build_compound_artifacts", script)
    mod = module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)

    meta = mod.build(EDGES_CSV, tmp_path, per_seed=8, min_weight=2)
    assert meta["neighbor_rows"] > 1000
    assert (tmp_path / "neighbors.jsonl").is_file()
