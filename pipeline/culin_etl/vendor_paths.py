"""In-repo paths for vendored flavor-network data (no external repo deps)."""
from __future__ import annotations

from pathlib import Path

VENDOR_ROOT = Path(__file__).resolve().parents[1] / "vendor"
FLAVOR_NETWORK = VENDOR_ROOT / "flavor_network"
FLAVOR_RECOMMENDER = VENDOR_ROOT / "flavor_recommender"
FOODB_ROOT = VENDOR_ROOT / "foodb"
FOODB_CSV_DIR = FOODB_ROOT / "foodb_2020_04_07_csv"
FOODB_CONTENT_CSV = FOODB_CSV_DIR / "Content.csv"
FOODB_COMPOUND_CSV = FOODB_CSV_DIR / "Compound.csv"
FOODB_NUTRIENT_CSV = FOODB_CSV_DIR / "Nutrient.csv"
FOODB_FOOD_CSV = FOODB_CSV_DIR / "Food.csv"

EDGES_CSV = FLAVOR_NETWORK / "ingredient_filtered_named_edges.csv"
LCC_EDGES_CSV = FLAVOR_NETWORK / "ingredient_lcc_named_edges.csv"
NETWORK_GML = FLAVOR_NETWORK / "ingredient_network_weighted_fixed.gml"
FILTERED_GML = FLAVOR_NETWORK / "ingredient_filtered_named.gml"
BRIDGING_SCORES_CSV = FLAVOR_NETWORK / "ingredient_bridging_scores.csv"
INGR_INFO_TSV = FLAVOR_NETWORK / "ingr_info.tsv"
HEALTH_MAPPING_TSV = FLAVOR_NETWORK / "compound_ingredient_health_mapping.tsv"
RECIPE_CSV = FLAVOR_NETWORK / "recipe.csv"
