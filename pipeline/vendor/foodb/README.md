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

Large archives and `Content.csv` exceed GitHub’s file size limits and are **not** in git.

After clone, run:

```bash
npm run fetch:foodb
```

That downloads `foodb_2020_4_7_csv.tar.gz` from [foodb.ca/downloads](https://foodb.ca/downloads) and extracts `Content.csv` plus the other tables.

**Tracked in git** (under 100MB): `Food.csv`, `Compound.csv`, `Nutrient.csv`.
