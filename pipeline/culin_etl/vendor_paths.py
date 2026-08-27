"""In-repo paths for vendored flavor-network data (no external repo deps)."""
from __future__ import annotations

from pathlib import Path

VENDOR_ROOT = Path(__file__).resolve().parents[1] / "vendor"
FLAVOR_NETWORK = VENDOR_ROOT / "flavor_network"
FLAVOR_RECOMMENDER = VENDOR_ROOT / "flavor_recommender"

EDGES_CSV = FLAVOR_NETWORK / "ingredient_filtered_named_edges.csv"
LCC_EDGES_CSV = FLAVOR_NETWORK / "ingredient_lcc_named_edges.csv"
NETWORK_GML = FLAVOR_NETWORK / "ingredient_network_weighted_fixed.gml"
FILTERED_GML = FLAVOR_NETWORK / "ingredient_filtered_named.gml"
BRIDGING_SCORES_CSV = FLAVOR_NETWORK / "ingredient_bridging_scores.csv"
INGR_INFO_TSV = FLAVOR_NETWORK / "ingr_info.tsv"
HEALTH_MAPPING_TSV = FLAVOR_NETWORK / "compound_ingredient_health_mapping.tsv"
RECIPE_CSV = FLAVOR_NETWORK / "recipe.csv"
