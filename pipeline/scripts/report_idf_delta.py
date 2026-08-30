"""
Beef Ingestion Build Spec, Step 6: "Report the IDF delta: how many existing
compounds changed weight, and by how much."

Run AFTER the full chain (through build_vcf_profiles.py at minimum;
compounds.jsonl must already carry the WITH-beef df_culinary/idf).

Reconstructs the WITHOUT-beef baseline analytically from the final
profiles.jsonl + compounds.jsonl, rather than by re-running the chain
twice with beef's profiles temporarily removed — df_before[cid] =
df_after[cid] minus however many beef profiles' df_eligible_compound_ids
contain it; N_before = the VCF-only culinary count. This is exact (not an
approximation) because df/idf are simple counts/logs over the same corpus,
just before vs. after the ADDITIVE 4-profile beef contribution.

Reads:  pipeline/artifacts/vcf/profiles.jsonl
        pipeline/artifacts/vcf/compounds.jsonl
Writes: pipeline/artifacts/vcf/meta.json (adds protein_beef.idf_delta_report)
"""
from __future__ import annotations

import json
import math
import statistics
from pathlib import Path

OUT_DIR = Path(__file__).resolve().parents[2] / "pipeline" / "artifacts" / "vcf"
PROFILES_JSONL = OUT_DIR / "profiles.jsonl"
COMPOUNDS_JSONL = OUT_DIR / "compounds.jsonl"
META_JSON = OUT_DIR / "meta.json"

BEEF_SOURCE = "culinai_protein_v21"


def main():
    profiles = [json.loads(l) for l in PROFILES_JSONL.read_text().splitlines() if l.strip()]
    compounds = [json.loads(l) for l in COMPOUNDS_JSONL.read_text().splitlines() if l.strip()]
    compound_by_id = {c["compound_id"]: c for c in compounds}
    new_beef_only_ids = {c["compound_id"] for c in compounds if c.get("source_family") == "beef"}

    culinary = [p for p in profiles if p.get("class") == "culinary"]
    beef_profiles = [p for p in culinary if p.get("profile_source") == BEEF_SOURCE]
    vcf_profiles = [p for p in culinary if p.get("profile_source") != BEEF_SOURCE]

    N_after = len(culinary)
    N_before = len(vcf_profiles)

    beef_df_eligible_sets = [set(p["df_eligible_compound_ids"]) for p in beef_profiles]

    n_any_change = 0
    n_real_overlap = 0
    background_deltas = []
    real_shifts = []

    for cid, c in compound_by_id.items():
        if cid in new_beef_only_ids:
            continue  # didn't exist before beef ingestion at all — no "before" value to compare
        df_after = c.get("df_culinary") or 0
        idf_after = c.get("idf")
        n_beef_docs_containing = sum(1 for s in beef_df_eligible_sets if cid in s)
        df_before = df_after - n_beef_docs_containing
        idf_before = math.log(N_before / df_before) if df_before > 0 else None

        if idf_before != idf_after:
            n_any_change += 1
            if idf_before is not None and idf_after is not None:
                background_deltas.append(idf_after - idf_before)
        if n_beef_docs_containing > 0:
            n_real_overlap += 1
            real_shifts.append({
                "compound_id": cid, "raw_compound": c.get("raw_compound"),
                "df_before": df_before, "df_after": df_after,
                "idf_before": round(idf_before, 4) if idf_before is not None else None,
                "idf_after": round(idf_after, 4) if idf_after is not None else None,
            })

    real_shifts.sort(key=lambda r: (r["idf_after"] or 0) - (r["idf_before"] or 0))

    report = {
        "n_culinary_before": N_before,
        "n_culinary_after": N_after,
        "n_existing_compounds_with_any_idf_change": n_any_change,
        "n_existing_compounds_with_real_df_increase_from_beef_overlap": n_real_overlap,
        "background_drift_note": (
            f"Every pre-existing compound's idf shifts by a small, uniform amount purely because N "
            f"(culinary corpus size) grew {N_before}->{N_after} — ln(N/df) moves for everyone when N "
            f"moves, even a compound beef never touches. Mean background shift: "
            f"{round(statistics.mean(background_deltas), 4) if background_deltas else None} nats. "
            f"That is expected arithmetic, not a finding."
        ),
        "real_overlap_note": (
            f"{n_real_overlap} existing compounds actually gained document-frequency because a beef "
            f"profile genuinely contains them (df up by 1-{len(beef_profiles)}, since only "
            f"{len(beef_profiles)} beef documents exist to add)."
        ),
        "largest_real_shifts_sample": real_shifts[:15],
    }

    meta = json.loads(META_JSON.read_text()) if META_JSON.exists() else {}
    meta.setdefault("protein_beef", {})["idf_delta_report"] = report
    META_JSON.write_text(json.dumps(meta, indent=2))
    print(f"n_existing_compounds_with_any_idf_change: {n_any_change}")
    print(f"n_existing_compounds_with_real_df_increase_from_beef_overlap: {n_real_overlap}")
    for r in real_shifts[:5]:
        print(" ", r)


if __name__ == "__main__":
    main()
