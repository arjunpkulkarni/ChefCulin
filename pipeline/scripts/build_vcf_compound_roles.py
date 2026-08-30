"""
VCF Compound Layer — compound role layer (post-review addition).

Run from the repo root, AFTER canonicalize_vcf_compounds.py and
build_vcf_phase.py (needs `compound_group` and `molecular_weight` on
compounds.jsonl):
    python pipeline/scripts/build_vcf_compound_roles.py

Reads:  pipeline/artifacts/vcf/compounds.jsonl
Writes: pipeline/artifacts/vcf/compound_roles.jsonl
        pipeline/artifacts/vcf/meta.json   (adds a "compound_roles" block)

--- Why this layer exists ---

Step 11e's smoke/terpene frame was attached to 37 rows, all wrong: anise
brandy, ouzo, calamus, star anise, fennel — zero smoked products. The
trigger tested for compound_group == "Phenols", and Phenols is a
STRUCTURAL class, not a functional one — it contains eugenol (clove),
thymol/carvacrol (oregano, thyme), anethole relatives (anise, fennel),
synthetic antioxidants, AND the genuine lignin-pyrolysis smoke markers,
all lumped together because they share a hydroxyl-on-aromatic-ring
skeleton. Structural validation (does this row's group membership match
the trigger's stated groups?) cannot catch this, because group membership
is precisely the thing too coarse to carry the claim.

This file is a functional tagging layer OVER compounds.jsonl, keyed on
compound_id. A compound may carry zero, one, or several roles. Each row
is one (compound_id, role) pair:
    compound_id
    role         -- smoke_marker | maillard_marker | lipid_oxidation_marker
                    | terpene_mono | terpene_sesqui
    confidence   -- high | medium
    basis        -- cas_curated | name_pattern
    note

Roles are curated per-role below; none claims completeness it doesn't
have — coverage is reported in meta.json instead. This build does not
attempt a full structural (SMILES-based) classification of the corpus;
every role here is either an explicit CAS-curated list or a documented
name-pattern / molecular-weight rule, checked against real corpus data
before being trusted, with confirmed false positives named and excluded
by hand (the same discipline as the smoke_marker curation).
"""
from __future__ import annotations

import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = REPO_ROOT / "pipeline" / "artifacts" / "vcf"
COMPOUNDS_JSONL = OUT_DIR / "compounds.jsonl"
COMPOUND_ROLES_JSONL = OUT_DIR / "compound_roles.jsonl"
META_JSON = OUT_DIR / "meta.json"


# =====================================================================
# smoke_marker — lignin pyrolysis products (guaiacols, syringols, cresols,
# simple alkylphenols). CAS-curated wherever a CAS exists; name-pattern
# fallback ONLY for the (unkn.str.) variants of an already-named compound
# in this exact list — never a blanket "contains 'guaiacol'" or "contains
# 'cresol'" match, which is exactly the mistake this layer exists to fix.
# =====================================================================

SMOKE_MARKER_CAS = {
    "90-05-1": "2-methoxyphenol (guaiacol)",
    "7786-61-0": "2-methoxy-4-vinylphenol (4-vinylguaiacol)",
    "106-44-5": "4-methylphenol (p-cresol)",
    "2628-17-3": "4-vinylphenol",
    "108-39-4": "3-methylphenol (m-cresol)",
    "95-48-7": "2-methylphenol (o-cresol)",
    "2785-89-9": "4-ethyl-2-methoxyphenol (4-ethylguaiacol)",
    "123-07-9": "4-ethylphenol",
    "93-51-6": "2-methoxy-4-methylphenol (4-methylguaiacol, creosol)",
    "2785-87-7": "2-methoxy-4-propylphenol (4-propylguaiacol)",
    "91-10-1": "2,6-dimethoxyphenol (syringol)",
    "14059-92-8": "4-ethyl-2,6-dimethoxyphenol (4-ethylsyringol)",
    "526-75-0": "2,3-dimethylphenol",
    "576-26-1": "2,6-dimethylphenol",
    "105-67-9": "2,4-dimethylphenol",
    "95-87-4": "2,5-dimethylphenol",
    "28343-22-8": "2,6-dimethoxy-4-vinylphenol (4-vinylsyringol)",
    "1300-71-6": "dimethylphenol (unkn.str.)",
    "6635-22-9": "2,6-dimethoxy-4-propenylphenol (4-propenylsyringol)",
    "6766-82-1": "2,6-dimethoxy-4-propylphenol (4-propylsyringol)",
    "2896-67-5": "2-methoxy-6-methylphenol (6-methylguaiacol)",
    "53587-16-9": "4-isopropyl-2-methoxyphenol (4-isopropylguaiacol)",
    "90534-46-6": "2-ethyl-6-methoxyphenol (6-ethylguaiacol)",
    "53667-10-0": "4-isopropyl-2,6-dimethoxyphenol (4-isopropylsyringol)",
}
# The (unkn.str.) entries with no CAS at all — resolved by compound_id
# (built from the raw name) instead.
SMOKE_MARKER_NAME_PATTERN_IDS = {
    "vcf:methylphenol_unkn_str_cresol_unkn_str": "methylphenol (unkn.str.) (cresol)",
    "vcf:2_6_dimethoxy_4_methylphenol_4_methylsyringol": "2,6-dimethoxy-4-methylphenol (4-methylsyringol)",
    "vcf:ethyl_2_methoxyphenol_unkn_str_ethylguaiacol_unkn_str": "ethyl-2-methoxyphenol (unkn.str.) (ethylguaiacol)",
    "vcf:methyl_o_cresol_unkn_str": "methyl o-cresol (unkn.str.)",
}
# One additional unambiguous alkylguaiacol found by inspecting every
# Phenols-group compound matching "methoxyphenol" in the corpus (see
# module docstring / meta.json note): a genuine alkyl-substituted
# guaiacol positional isomer not already covered above.
SMOKE_MARKER_ADDITIONAL_CAS = {
    "80652-16-0": "ethyl-methoxyphenol (unkn.str.) — additional alkylguaiacol variant",
}

# Explicitly excluded — structurally similar (methoxyphenol / alkylphenol)
# but NOT pyrolysis products. Asserted absent from the tagged set at
# build time; a future edit that accidentally widens a pattern to catch
# one of these fails the build.
SMOKE_MARKER_EXCLUDED_CAS = {
    "97-53-0": "eugenol — clove, biosynthetic methoxyphenol, not pyrolytic (df=154, the single largest false-positive source in Revision 2)",
    "6627-88-9": "5-methoxyeugenol — same family as eugenol",
    "4427-56-9": "isothymol — herb terpenoid phenol (thyme, savory)",
    "15269-16-6": "2,5-diisopropyl-4-methylphenol — thymol/carvacrol relative",
    "74926-87-7": "2,6-diisobutyl-4-methylphenol — synthetic antioxidant",
    "4130-42-1": "2,6-di-tert-butyl-4-ethylphenol — synthetic antioxidant (BHT family)",
    "2409-55-4": "2-tert-butyl-4-methylphenol — synthetic antioxidant",
    "3855-26-3": "2-ethyl-4-methylphenol — not a pyrolysis marker",
    # No CAS for this one; excluded by compound_id instead.
}
SMOKE_MARKER_EXCLUDED_NAME_PATTERN_IDS = {
    "vcf:2_1_5_dimethyl_4_hexenyl_4_methylphenol": "2-(1,5-dimethyl-4-hexenyl)-4-methylphenol — sesquiterpenoid phenol",
}
# Also considered and excluded: eugenol-family allyl/propenyl-substituted
# methoxyphenols found while searching for "the remaining alkyl variants"
# (biosynthetic, same family as eugenol/5-methoxyeugenol above, not
# pyrolytic) and two more likely synthetic antioxidants (BHA and a
# tert-butyl-methoxyphenol, paralleling the BHT-family exclusions above).
# Recorded here for anyone re-deriving this list, not tagged either way
# since they were never in the curated set to begin with:
#   90377-06-3  4-allyl-2,5-dimethoxyphenol       (eugenol-family, allyl)
#   501-19-9    5-allyl-2-methoxyphenol/chavibetol (eugenol-family, allyl)
#   110162-33-9 allyldimethoxyphenol (unkn.str.)   (eugenol-family, allyl)
#   121-00-6    2-tert-butyl-4-methoxyphenol (=BHA) (synthetic antioxidant)
#   53894-31-8  tert-butyl-2-methoxyphenol (unkn.str.) (likely antioxidant)


# =====================================================================
# maillard_marker — pyrazines, pyrroles, pyridines, thiophenes, thiazoles,
# and furanones. Name-pattern based (unlike smoke_marker, there is no
# hand-curated CAS list from the review for this role — it's shipped "as
# populated as the corpus supports," per instruction). Furanone is
# restricted to the Furans group specifically: a naive substring match
# also catches gamma-lactones whose name carries a furanone-style IUPAC
# alias (e.g. "4-hydroxybutanoic acid lactone (=dihydro-2(3H)-furanone,
# ... gamma-butyrolactone)") — those are lipid-derived lactones, not
# Maillard products, and are classified as Lactones, not Furans, in this
# corpus. Restricting the furanone pattern to compound_group == "Furans"
# excludes them without a separate exclusion list.
# =====================================================================

MAILLARD_PATTERN_ANY_GROUP = re.compile(r"pyrazine|pyrrole|pyridine|thiophene|thiazole", re.I)
MAILLARD_PATTERN_FURANS_ONLY = re.compile(r"furanone", re.I)


# =====================================================================
# lipid_oxidation_marker — hexanal (explicitly named) plus C6-C10
# alkenals/alkadienals: the compounds that distinguish a raw protein
# profile from a cooked/oxidized one. Restricted to STRAIGHT-CHAIN,
# unsubstituted alkenals/alkadienals in the C6-C10 range: a broad
# substring match on "hexenal"/"decadienal"/etc. also pulls in chain
# lengths past C10 (dodecenal, tetradecenal, hexadecenal...), branched
# and aryl/furyl-substituted variants (2-phenyl-2-hexenal, terpenoid
# aldehydes like citral/citronellal, furyl-hexenals already living in the
# Furans group), and epoxide derivatives already living in a different
# group entirely — none of which are the classic lipid-autoxidation
# series. `_parse_c6_c10_alkenal` strips stereo/position prefixes and
# requires the bare remainder to be exactly one of the ten C6-C10
# alkenal/alkadienal stems; anything with an extra substituent token
# fails that check and is left untagged.
# =====================================================================

LIPID_OXIDATION_EXPLICIT_CAS = {
    "66-25-1": "hexanal (=capronaldehyde)",
    "18829-56-6": "(E)-2-nonenal",
    "25152-84-5": "(E,E)-2,4-decadienal",
}

_C6_C10_ALKENAL_STEMS = {
    "hexenal", "heptenal", "octenal", "nonenal", "decenal",
    "hexadienal", "heptadienal", "octadienal", "nonadienal", "decadienal",
}
_ALKENAL_SEARCH_PATTERN = re.compile(
    r"hexenal|heptenal|octenal|nonenal|decenal"
    r"|hexadienal|heptadienal|octadienal|nonadienal|decadienal",
    re.I,
)


def _parse_c6_c10_alkenal(raw_name: str) -> bool:
    name = raw_name.split(" (=")[0].strip()
    core = name.replace("(unkn.str.)", "").strip()
    core = re.sub(r"^\([^)]*\)-", "", core)  # strip a leading (E)-, (E,E)-, (2E,7Z)- etc.
    core = re.sub(r"^[\d,]+-", "", core)  # strip a leading position prefix like "2-", "3,6-"
    core = core.strip().lower()
    return core in _C6_C10_ALKENAL_STEMS


# =====================================================================
# terpene_mono / terpene_sesqui — split of the Hydrocarbons group by
# EXACT molecular weight, not a rounded band. Rounding to the nearest
# integer looks tempting (monoterpenes ~136, sesquiterpenes ~204) but
# neighboring integer bands are genuinely contaminated with non-terpene
# isomers sharing the same rounded mass: MW 134 mixes p-cymene-family
# monoterpenes with plain tetramethylbenzenes; MW 138 mixes
# menthene/pinane monoterpene relatives with 1-decyne and decahydro-
# naphthalene (decalin); MW 202 (rounded) mixes real aromatic
# sesquiterpenes (calamenene, cuparene, ar-curcumene — precise MW 202.34)
# with fluoranthene and pyrene, both PAHs, at precise MW 202.25. Every
# compound at each precise mass below was inspected by name before being
# included; nonylbenzene was caught this way at exactly 204.35 (identical
# formula to a real sesquiterpene, completely different structure) and is
# excluded explicitly rather than silently mistagged.
# =====================================================================

TERPENE_MONO_MW = {136.23}  # C10H16 — inspected: 51/51 real monoterpenes, zero contamination found
TERPENE_SESQUI_MW = {204.35, 202.34, 200.32}  # C15H24 / C15H22 / C15H20 — inspected, see exclusion below
TERPENE_SESQUI_EXCLUDED_CAS = {
    "1081-77-2": "nonylbenzene — same formula (C15H24, MW 204.35) as real sesquiterpenes, alkylbenzene structure",
}

# MR-17 (2026-08-29): p-Cymene, added via beef's MR-17 classification pass
# (ingest_protein_beef.py) as compound_group="Hydrocarbons", is a genuine
# monoterpene by identity — but the MW path above can't reach it two ways
# over: it has no CAS in this corpus (so no crosswalk molecular_weight at
# all), and even with one, its real MW (134.22) sits in the exact rounded
# band this module's own docstring already documents as contaminated
# ("MW 134 mixes p-cymene-family monoterpenes with plain
# tetramethylbenzenes") and deliberately excludes from blind inclusion.
# Included here by name-confirmed identity instead — the same
# per-compound inspection standard TERPENE_MONO_MW/TERPENE_SESQUI_MW were
# built with, just applied to a compound the MW rule structurally can't see.
TERPENE_MONO_ID_OVERRIDES = {
    "beef:p_cymene": "p-Cymene — genuine monoterpene, name-confirmed; no CAS/molecular_weight "
                      "in this corpus, and MW 134 is a band already excluded from the MW rule.",
}


def _mw_matches(mw, target_set, tol=0.005) -> bool:
    if mw is None:
        return False
    return any(abs(mw - t) <= tol for t in target_set)


# =====================================================================
# MR-15 (Beef Ingestion Build Spec, Step 3): a straight-chain (unbranched,
# acyclic, fully saturated) alkane never carries a terpene role — its
# presence in a lipid-heavy matrix like beef fat is a lipid-autoxidation
# fragment, not a terpene, regardless of any molecular-weight coincidence
# with TERPENE_MONO_MW/TERPENE_SESQUI_MW above. Checked against beef's own
# alkane list (Octane .. Octadecane) before writing this: none of their
# real MWs land inside those windows (a saturated CnH2n+2 alkane can't
# share the exact unsaturated formula a terpene needs), so this guard is
# currently inert on this corpus — it exists as a hard exclusion for
# whatever the next protein family's alkanes turn out to be, not because
# a real collision was found here. name-pattern basis, not CAS-curated,
# since the rule is structural (unbranched acyclic alkane), not a fixed
# compound list.
# =====================================================================
STRAIGHT_CHAIN_ALKANE_RE = re.compile(
    r"^(meth|eth|prop|but|pent|hex|hept|oct|non|dec|undec|dodec|tridec|"
    r"tetradec|pentadec|hexadec|heptadec|octadec|nonadec|icos)ane$",
    re.IGNORECASE,
)


def is_straight_chain_alkane(raw_compound: str) -> bool:
    core = (raw_compound or "").strip()
    core = re.sub(r"\s*\(=.*\)\s*$", "", core)
    return bool(STRAIGHT_CHAIN_ALKANE_RE.match(core))


def main():
    if not COMPOUNDS_JSONL.exists():
        raise SystemExit(f"{COMPOUNDS_JSONL} not found — run canonicalize_vcf_compounds.py first.")

    compounds = [json.loads(l) for l in COMPOUNDS_JSONL.read_text().splitlines() if l.strip()]

    roles = []  # list of {compound_id, role, confidence, basis, note}
    coverage = {}
    seen_compound_role: set[tuple[str, str]] = set()

    def add_role(compound_id, role, confidence, basis, note):
        # compounds.jsonl carries one row per RAW NAME, and several raw
        # names (stereoisomer prefixes, bare vs. prefixed spellings) can
        # canonicalize to the same compound_id (61 compound_ids in this
        # corpus have 2+ raw-name rows). A role is a fact about the
        # canonical compound, not the raw-name row, so dedupe here rather
        # than emit the same (compound_id, role) more than once.
        key = (compound_id, role)
        if key in seen_compound_role:
            return
        seen_compound_role.add(key)
        roles.append(
            {
                "compound_id": compound_id,
                "role": role,
                "confidence": confidence,
                "basis": basis,
                "note": note,
            }
        )

    # --- smoke_marker ---
    smoke_tagged = set()
    for c in compounds:
        cas = c.get("cas")
        cid = c["compound_id"]
        if cas in SMOKE_MARKER_EXCLUDED_CAS or cid in SMOKE_MARKER_EXCLUDED_NAME_PATTERN_IDS:
            continue
        if cas in SMOKE_MARKER_CAS:
            add_role(cid, "smoke_marker", "high", "cas_curated", SMOKE_MARKER_CAS[cas])
            smoke_tagged.add(cid)
        elif cas in SMOKE_MARKER_ADDITIONAL_CAS:
            add_role(cid, "smoke_marker", "medium", "cas_curated", SMOKE_MARKER_ADDITIONAL_CAS[cas])
            smoke_tagged.add(cid)
        elif cid in SMOKE_MARKER_NAME_PATTERN_IDS:
            add_role(cid, "smoke_marker", "high", "name_pattern", SMOKE_MARKER_NAME_PATTERN_IDS[cid])
            smoke_tagged.add(cid)

    # Build-time assertion: no excluded compound is ever tagged, even if a
    # future edit to the curated sets above accidentally widens overlap.
    excluded_ids = set(SMOKE_MARKER_EXCLUDED_NAME_PATTERN_IDS)
    for c in compounds:
        if c.get("cas") in SMOKE_MARKER_EXCLUDED_CAS:
            excluded_ids.add(c["compound_id"])
    bad = smoke_tagged & excluded_ids
    if bad:
        raise SystemExit(f"smoke_marker tagged {len(bad)} explicitly excluded compound(s): {bad}")

    coverage["smoke_marker"] = {
        "n_tagged": len(smoke_tagged),
        "n_curated_target": 36,
        "gap_note": (
            f"Reviewer's spec named 28 compounds explicitly plus 'the "
            f"remaining alkyl-guaiacol and alkyl-syringol variants' for a "
            f"total of 36. Only one additional unambiguous alkylguaiacol "
            f"variant (CAS 80652-16-0) was found by inspecting every "
            f"Phenols-group compound matching 'methoxyphenol' in this "
            f"corpus — giving {len(smoke_tagged)}, not 36. Candidates "
            f"considered and rejected (eugenol-family allyl/propenyl "
            f"methoxyphenols, likely synthetic antioxidants) are recorded "
            f"in this script's docstring rather than tagged to hit the "
            f"target count."
        ),
    }

    # --- maillard_marker ---
    maillard_tagged = set()
    maillard_by_group = {}
    for c in compounds:
        rc = c.get("raw_compound") or ""
        cid = c["compound_id"]
        group = c.get("compound_group")
        hit = False
        if MAILLARD_PATTERN_ANY_GROUP.search(rc):
            hit = True
        elif group == "Furans" and MAILLARD_PATTERN_FURANS_ONLY.search(rc):
            hit = True
        if hit:
            add_role(
                cid, "maillard_marker", "high", "name_pattern",
                f"matched pyrazine/pyrrole/pyridine/thiophene/thiazole/furanone name pattern (group={group})",
            )
            maillard_tagged.add(cid)
            maillard_by_group[group] = maillard_by_group.get(group, 0) + 1
    coverage["maillard_marker"] = {
        "n_tagged": len(maillard_tagged),
        "by_compound_group": maillard_by_group,
        "note": (
            "Name-pattern based, no CAS-curated list from the review for "
            "this role. furanone restricted to compound_group == 'Furans' "
            "to exclude gamma-lactones whose IUPAC alias happens to "
            "contain the word 'furanone' (they are Lactones, not Furans, "
            "in this corpus's own classification) — not every 'furanone' "
            "match is a Maillard product, matching the review's own "
            "caution about 'Bases' not being blanket-taggable."
        ),
    }

    # --- lipid_oxidation_marker ---
    lipid_ox_tagged = set()
    for c in compounds:
        cas = c.get("cas")
        rc = c.get("raw_compound") or ""
        cid = c["compound_id"]
        if cas in LIPID_OXIDATION_EXPLICIT_CAS:
            add_role(cid, "lipid_oxidation_marker", "high", "cas_curated", LIPID_OXIDATION_EXPLICIT_CAS[cas])
            lipid_ox_tagged.add(cid)
        elif (
            c.get("compound_group") == "Carbonyls, aldehydes"
            and _ALKENAL_SEARCH_PATTERN.search(rc)
            and _parse_c6_c10_alkenal(rc)
        ):
            add_role(
                cid, "lipid_oxidation_marker", "high", "name_pattern",
                "unsubstituted C6-C10 alkenal/alkadienal",
            )
            lipid_ox_tagged.add(cid)
    coverage["lipid_oxidation_marker"] = {
        "n_tagged": len(lipid_ox_tagged),
        "note": (
            "3 explicitly-named compounds (hexanal, (E)-2-nonenal, "
            "(E,E)-2,4-decadienal) plus every OTHER unsubstituted C6-C10 "
            "alkenal/alkadienal isomer in Carbonyls,aldehydes. Excludes "
            "chain lengths past C10 (dodecenal, tetradecenal, "
            "hexadecenal...), branched/aryl/furyl-substituted variants "
            "(2-phenyl-2-hexenal, terpenoid citral/citronellal, "
            "furyl-hexenals), and epoxide derivatives — none of these are "
            "the classic straight-chain lipid-autoxidation series this "
            "role is meant to capture."
        ),
    }

    # --- lipid_degradation_fragment (MR-15) — straight-chain alkanes,
    # tagged BEFORE the terpene loop and used to hard-exclude them from
    # it, never the reverse order (a compound must never be checked for
    # terpene membership first and "cleared" by MW alone). ---
    alkane_tagged = set()
    for c in compounds:
        if is_straight_chain_alkane(c.get("raw_compound") or ""):
            cid = c["compound_id"]
            add_role(cid, "lipid_degradation_fragment", "high", "name_pattern",
                      "MR-15: straight-chain alkane — never terpene_mono/terpene_sesqui")
            alkane_tagged.add(cid)
    coverage["lipid_degradation_fragment"] = {
        "n_tagged": len(alkane_tagged),
        "note": "MR-15 guard (Beef Ingestion Build Spec Step 3): every straight-chain alkane in the "
                "corpus, regardless of source family. Currently inert as a terpene-collision fix on "
                "this corpus (checked: none of these MWs land in TERPENE_MONO_MW/TERPENE_SESQUI_MW) — "
                "exists as a hard exclusion for future protein families.",
    }

    # --- terpene_mono / terpene_sesqui ---
    mono_tagged = set()
    sesqui_tagged = set()
    for c in compounds:
        if c.get("compound_group") != "Hydrocarbons":
            continue
        cid = c["compound_id"]
        if cid in alkane_tagged:
            continue  # MR-15: straight-chain alkanes are never terpenes, full stop
        cas = c.get("cas")
        mw = c.get("molecular_weight")
        if _mw_matches(mw, TERPENE_MONO_MW):
            add_role(cid, "terpene_mono", "high", "name_pattern", f"MW={mw} (C10H16)")
            mono_tagged.add(cid)
        elif _mw_matches(mw, TERPENE_SESQUI_MW) and cas not in TERPENE_SESQUI_EXCLUDED_CAS:
            add_role(cid, "terpene_sesqui", "high", "name_pattern", f"MW={mw} (C15H2x)")
            sesqui_tagged.add(cid)

    # MR-17 identity overrides — compounds the MW rule can't reach (no CAS/MW
    # data) or deliberately excludes by band, but which are genuine terpenes
    # by name. Never applied to an alkane-tagged compound (MR-15 still wins).
    for cid, note in TERPENE_MONO_ID_OVERRIDES.items():
        if cid in alkane_tagged or cid in mono_tagged:
            continue
        if any(c["compound_id"] == cid for c in compounds):
            add_role(cid, "terpene_mono", "high", "identity_override", note)
            mono_tagged.add(cid)

    bad_sesqui = sesqui_tagged & {
        c["compound_id"] for c in compounds if c.get("cas") in TERPENE_SESQUI_EXCLUDED_CAS
    }
    if bad_sesqui:
        raise SystemExit(f"terpene_sesqui tagged {len(bad_sesqui)} explicitly excluded compound(s): {bad_sesqui}")

    bad_alkane_terpene = (mono_tagged | sesqui_tagged) & alkane_tagged
    if bad_alkane_terpene:
        raise SystemExit(
            f"MR-15 VIOLATION: {len(bad_alkane_terpene)} straight-chain alkane(s) tagged with a terpene "
            f"role despite the exclusion: {bad_alkane_terpene}"
        )

    n_hydrocarbons_total = sum(1 for c in compounds if c.get("compound_group") == "Hydrocarbons")
    n_hydrocarbons_with_mw = sum(
        1 for c in compounds if c.get("compound_group") == "Hydrocarbons" and c.get("molecular_weight") is not None
    )
    coverage["terpene_mono"] = {"n_tagged": len(mono_tagged)}
    coverage["terpene_sesqui"] = {"n_tagged": len(sesqui_tagged)}
    coverage["terpene_split_note"] = (
        f"{n_hydrocarbons_total} Hydrocarbons-group compounds total "
        f"({n_hydrocarbons_with_mw} with a molecular_weight). Split by "
        f"EXACT molecular weight (tolerance 0.005), not a rounded band — "
        f"see module docstring for the contamination found at rounded MW "
        f"134/138/202 (real terpenes mixed with tetramethylbenzenes, "
        f"1-decyne, decalin, and — caught and excluded — fluoranthene and "
        f"pyrene, both PAHs, at rounded MW 202). "
        f"{len(mono_tagged) + len(sesqui_tagged)} of {n_hydrocarbons_total} "
        f"({(len(mono_tagged) + len(sesqui_tagged)) / n_hydrocarbons_total:.1%}) "
        f"classified; the rest (plain alkanes/alkenes, aromatic "
        f"hydrocarbons, diterpenes, and the genuinely ambiguous MW "
        f"134/138 bands) are left unclassified rather than guessed."
    )

    with open(COMPOUND_ROLES_JSONL, "w") as f:
        for r in roles:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    meta = json.loads(META_JSON.read_text()) if META_JSON.exists() else {}
    meta["compound_roles"] = {
        "n_role_rows": len(roles),
        "n_distinct_compounds_with_a_role": len({r["compound_id"] for r in roles}),
        "coverage": coverage,
    }
    META_JSON.write_text(json.dumps(meta, indent=2))

    print(f"Wrote {len(roles)} role rows to {COMPOUND_ROLES_JSONL}")
    for role_name in ("smoke_marker", "maillard_marker", "lipid_oxidation_marker", "terpene_mono", "terpene_sesqui",
                      "lipid_degradation_fragment"):
        n = coverage.get(role_name, {}).get("n_tagged")
        print(f"  {role_name:<24} {n}")


if __name__ == "__main__":
    main()
