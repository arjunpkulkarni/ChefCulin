# FooDB vendor data

Balance axes use FooDB **Content** tables (mg/100g glutamate, sodium, sugars, fat, etc.).

## Fetch

```bash
npm run fetch:foodb
```

Downloads `foodb_2020_4_7_csv.tar.gz` from [foodb.ca/downloads](https://foodb.ca/downloads) and extracts:

- `Content.csv`
- `Compound.csv`
- `Nutrient.csv`
- `Food.csv`

Large archives and `Content.csv` are stored with **Git LFS** (GitHub’s 100MB blob limit).

After clone:

```bash
git lfs install
git lfs pull
```

Or fetch only the balance tables:

```bash
npm run fetch:foodb
```

**In git (LFS):** `Content.csv`, `foodb_csv.tar.gz`, `foodb_json.zip`  
**In git (regular):** `Food.csv`, `Compound.csv`, `Nutrient.csv`
