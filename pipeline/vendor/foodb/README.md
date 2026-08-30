# FooDB vendor data (local)

Balance axes read **Content.csv** (mg/100g glutamate, sodium, sugars, etc.).

## On this machine

Keep the full vendor tree under `pipeline/vendor/foodb/`. It is **not** pushed to GitHub (file size limits).

```bash
npm run fetch:foodb    # download + extract if missing (~1GB once)
npm run build:balance  # refresh src/data/balance_axes.json
```

**In git:** `Food.csv`, `Compound.csv`, `Nutrient.csv`  
**Local only:** `Content.csv`, `*.tar.gz`, `*.zip`
