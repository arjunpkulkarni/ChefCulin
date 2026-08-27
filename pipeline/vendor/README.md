# Vendored flavor-network assets

Self-contained copies of data and code migrated from local repos so ChefCulin does not
depend on sibling checkouts under `~/CodeBases`.

## `flavor_network/` (from FlavorNetworkProject + flavor-recommender)

| File | Role |
|------|------|
| `ingredient_filtered_named_edges.csv` | Primary edge list — shared volatile compound weights (build input for `/compound`) |
| `ingredient_lcc_named_edges.csv` | Largest connected component edges |
| `ingredient_filtered_named.gml` | Filtered named graph (GML) |
| `ingredient_lcc_named.gml` | LCC graph (GML) |
| `ingredient_network_weighted_fixed.gml` | Weighted graph used by `FlavorNetworkEngine` |
| `ingredient_bridging_scores.csv` | Bridge-ingredient scores for path-based pairing |
| `ingr_info.tsv` | Ingredient id → display name |
| `compound_ingredient_health_mapping.tsv` | Ingredient ↔ health-effect links |
| `recipe.csv` | Legacy recipe co-occurrence corpus (ChefCulin uses RecipeNLG NPMI instead) |

## `flavor_recommender/` (from flavor-recommender)

| File | Role |
|------|------|
| `flavor_engine.py` | `FlavorNetworkEngine` — direct/bridged pair scoring via NetworkX |
| `recommender.py` | `HealthEffectRecommender` — health-effect → ingredient → flavor pairs |

Runtime compound lookup uses `culin_etl.compound_network` (prebuilt `artifacts/compound/`).
The vendored Python modules are available for future health/bridge features; they require
`networkx` and `pandas` (optional — not installed by default).

## Rebuild compound artifacts

```bash
npm run build:compound
```
