"""
VCF Compound Layer — Steps 1 & 2: pull/concatenate the ingredient_compounds
CSVs and parse the Product string into a structured schema.

Run from the repo root:  python pipeline/scripts/parse_vcf_products.py

Reads:  pipeline/vendor/vcf/raw/*.csv          (28 files, dtype=str)
Writes: pipeline/artifacts/vcf/step1_concat.parquet
        pipeline/artifacts/vcf/vcf_product_parse.jsonl
        pipeline/artifacts/vcf/vcf_product_parse_review.xlsx
        pipeline/artifacts/vcf/meta.json

See pipeline/README (VCF section) or the build spec for the full step-by-step
rationale. The short version, since both decisions are easy to get wrong
silently:

1. ~22.5k rows (32.5% of the raw pull) have Product == "" and Product
   Category populated instead. This is NOT a column-shift bug — VCF reports
   some compounds at the species level with no specific named product, and
   represents that by leaving Product blank and putting the species name in
   Product Category (which is a real, separately-used field elsewhere, e.g.
   "SWEET CHERRY" / "SOUR CHERRY" both carry category "CHERRY"). Dropping
   these rows (the literal "drop empty Product" reading) silently deletes
   ~94 products, including the only VCF entries for cloves, fig, star anise,
   ginger, and grape brandy. Decision (confirmed 2026-08-28): recover them by
   using Product Category as Product when Product is blank.

2. Parsing the Product string is rule-based, not exhaustive. Ambiguous cases
   (which of two comma-separated common names is the base vs. an alias; a
   head that is itself a scientific name; a parenthetical that matches no
   known category; nested parentheses) are flagged needs_review=True with a
   reason in vcf_product_parse_review.xlsx rather than silently guessed.
   Review pass (2026-08-28, James):
     - multi-name-head synonym pairs -> prefer the term a US line cook would
       recognize (KNOWN_BASE_PREFERENCE); both names kept in `aliases`.
     - "RASPBERRY, BLACKBERRY and BOYSENBERRY" isn't a synonym pair (three
       distinct berries) -> treated as raspberry.
     - fixed in code, not by hand, since each was a systematic parser bug
       rather than a one-off judgment call: "X, OTHER TYPES/VARIETIES/WILD"
       swallowing the real ingredient name into base_ingredient instead of
       cultivar; "Pistacia atlantica/palaestina, <part> OIL" losing the
       species to a bare plant-part word; nested-paren botanical citations
       (e.g. "Agastache foeniculum (Pursh) Kuntze") leaking a stray author
       fragment into base_ingredient; "(fresh pulp)"/"(fresh extrusion
       product)" being dropped instead of captured as state/form; and RUM
       Category I/II/III fragmenting into three ingredients instead of one
       with the volatile-ppm tier kept as a note.
   Two rows needed a human call the string itself couldn't resolve (see
   RAW_NAME_OVERRIDES for both, with full reasoning inline):
     - ORIGANUM (Spanish) (Coridothymus cap.(L.) Rchb.) -> "spanish oregano",
       a distinct herb from Origanum vulgare.
     - FENNEL (Foeniculum vulg., ssp. capillaceum; var.) -> "fennel" (bulb),
       with VEGETABLE FENNEL (var. azoricum (Miller)) dropped as a duplicate
       submission of the same measurement (see DUPLICATE_PRODUCTS_TO_DROP) —
       585 -> 584 products, since that row's 25 compounds were a strict
       subset of this one's 46 and it contributed nothing unique.
   All needs_review flags cleared as of this pass.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = REPO_ROOT / "pipeline" / "vendor" / "vcf" / "raw"
OUT_DIR = REPO_ROOT / "pipeline" / "artifacts" / "vcf"
OUT_DIR.mkdir(parents=True, exist_ok=True)

EXPECTED_COLS = [
    "Product", "Product Category", "Product Group", "Compound",
    "Compound Group", "Quantity Lower Bound", "Quantity Upper Bound",
]

# Resolved 2026-08-28 (James): "VEGETABLE FENNEL (var. azoricum (Miller))"
# is a duplicate submission of "FENNEL (Foeniculum vulg., ssp. capillaceum;
# var.)" — same source file (16000_17000.csv), and its 25 compounds are a
# strict subset of FENNEL's 46 (zero compounds unique to it), so dropping it
# loses no data at the corpus level. FENNEL (the more complete of the two)
# is retained and tagged as standard culinary bulb fennel in Step 2 — see
# RAW_NAME_OVERRIDES — since "azoricum" (bulb/Florence fennel) is almost
# certainly what the truncated var. designation was going to say.
#
# Resolved 2026-08-28 (James, from the family-candidates review): four more
# products are the same pattern — a plant-part or "fruit"-suffixed
# submission whose compounds are a verified strict subset of a more complete
# bare-name submission of the same species. Confirmed by compound-set
# overlap before dropping, same as the fennel case above:
#   GLOBE ARTICHOKE (Cynara scolymus L.)  ⊂ ARTICHOKE            (48/48 shared)
#   ELDERBERRY FRUIT                       ⊂ ELDERBERRY (Sambucus nigra L.) (37/37)
#   STRAWBERRY FRUIT                       ⊂ STRAWBERRY (Fragaria species) (309/309)
#   CHINESE QUINCE FLESH/FRUIT/PEEL        ⊂ CHINESE QUINCE (Pseudocydonia sinensis Schneid)
# The bare/more-complete name is retained in each case.
DUPLICATE_PRODUCTS_TO_DROP = {
    "VEGETABLE FENNEL (var. azoricum (Miller))",
    "GLOBE ARTICHOKE (Cynara scolymus L.)",
    "ELDERBERRY FRUIT",
    "STRAWBERRY FRUIT",
    "CHINESE QUINCE FLESH",
    "CHINESE QUINCE FRUIT",
    "CHINESE QUINCE PEEL",
}

# Resolved 2026-08-28 (James, from the family-candidates review): dropped
# outright rather than resolved, because their botanical/culinary identity
# is unreliable or unspecified — not a data-quality bug in our parse, a
# genuine gap in what the source row tells us:
#   SPECIAL WINE                                       — unspecified type, unknown origin.
#   TRADITIONAL RICE (cooked)                          — "traditional" undefined, ambiguous.
#   OCIMUM SPECIES                                     — species unspecified (bare genus).
#   RED SAGE (Texas sage) (S. coccinea Juss. ex Murr.) — Salvia coccinea, not the
#     culinary sage (Salvia officinalis) James wants "sage" to mean; keeping it
#     under a shared "sage" identity would silently misrepresent the product.
#   COCOA category                                     — VCF's own rollup/aggregate row:
#     Product == Product Category, and its 686 compounds are exactly the union of
#     the five other cocoa products (verified 2026-08-28) — not a real, cookable
#     product, and left in it inflates cocoa-family IDF/pairing with duplicate data.
EXCLUDED_LOW_CONFIDENCE_OR_ROLLUP = {
    "SPECIAL WINE",
    "TRADITIONAL RICE (cooked)",
    "OCIMUM SPECIES",
    "RED SAGE (Texas sage) (S. coccinea Juss. ex Murr.)",
    "COCOA category",
}

# ---------------------------------------------------------------------------
# Step 1 — pull / concatenate
# ---------------------------------------------------------------------------


def load_and_concat() -> pd.DataFrame:
    files = sorted(
        RAW_DIR.glob("*.csv"),
        key=lambda p: int(p.stem.split("_")[0]),
    )
    if not files:
        raise SystemExit(f"No CSVs found under {RAW_DIR} — run the Drive pull first.")

    frames = []
    for path in files:
        # utf-8-sig strips a BOM if present (2 of 28 files carry one),
        # no-ops if absent — do not read these with plain "utf-8".
        df = pd.read_csv(path, dtype=str, encoding="utf-8-sig", keep_default_na=False)
        if list(df.columns) != EXPECTED_COLS:
            raise SystemExit(f"Unexpected columns in {path.name}: {list(df.columns)}")
        df["__source_file"] = path.name
        frames.append(df)

    raw = pd.concat(frames, ignore_index=True)

    # Recover species-level rows — see module docstring, decision (1).
    empty_product = raw["Product"].str.strip() == ""
    has_category = raw["Product Category"].str.strip() != ""
    recovered_mask = empty_product & has_category
    raw.loc[recovered_mask, "Product"] = raw.loc[recovered_mask, "Product Category"]

    empty_product = raw["Product"].str.strip() == ""
    empty_compound = raw["Compound"].str.strip() == ""
    kept = raw[~(empty_product | empty_compound)].copy()

    # Drop known-duplicate product submissions — see DUPLICATE_PRODUCTS_TO_DROP.
    kept = kept[~kept["Product"].isin(DUPLICATE_PRODUCTS_TO_DROP)].copy()

    # Drop unreliable-identity / rollup-aggregate products — see
    # EXCLUDED_LOW_CONFIDENCE_OR_ROLLUP.
    kept = kept[~kept["Product"].isin(EXCLUDED_LOW_CONFIDENCE_OR_ROLLUP)].copy()

    return kept


# ---------------------------------------------------------------------------
# Step 2 — parse the Product string
# ---------------------------------------------------------------------------

PREP_WORDS = {
    "raw", "roasted", "boiled", "fried", "grilled", "smoked", "cooked",
    "baked", "dried", "toasted", "brewed", "hydrolyzed", "heated",
    "steamed", "canned",
}
PREP_PHRASES = {
    "fried and seasoned": ["fried"],
    "cooked fermented": ["cooked", "fermented"],
    "cooked or boiled": ["cooked", "boiled"],
    "french fried": ["fried"],
    "sweetened and dried": ["dried"],
    "dried bonito": ["dried"],
    "dried plum": ["dried"],
    "dried unripe": ["dried"],
    "salted and pickled": ["pickled"],
    "canned juice": ["canned"],
    "extract of cooked and roasted rice": ["cooked", "roasted"],
}
# Phrases that describe state/form rather than a processing step — e.g.
# "(fresh pulp)" is not a cooking prep, it's the raw material's physical
# form. Captured as (state, form) rather than dropped, since this is exactly
# the kind of signal the Form lens needs downstream.
FORM_STATE_PHRASES = {
    "fresh pulp": ("fresh", "pulp"),
    "fresh extrusion product": ("fresh", "extruded"),
}
STATE_WORDS = {"fresh", "processed", "unprocessed", "generic", "fermented", "hybrid"}
FORM_SUFFIX_WORDS = {"paste", "juice", "oil", "butter", "powder", "concentrate", "extract"}
CURE_HEAD_WORDS = {"cured", "uncured"}

# Resolved 2026-08-28 (James): for a multi-name head that's a genuine
# synonym pair, prefer the term a US line cook would recognize. Both names
# are retained in `aliases` regardless of which one wins here.
KNOWN_BASE_PREFERENCE = {
    frozenset({"filbert", "hazelnut"}): "hazelnut",
    frozenset({"aubergine", "eggplant"}): "eggplant",
    frozenset({"beli", "bael"}): "bael",
    frozenset({"ceriman", "pinanona"}): "ceriman",
    frozenset({"custard apple", "atemoya"}): "custard apple",
    frozenset({"dalieb", "palmyra palm fruit"}): "palmyra palm fruit",
    frozenset({"ethiopian pepper", "guinea pepper"}): "guinea pepper",
    frozenset({"lingonberry", "cowberry"}): "lingonberry",
    frozenset({"quince", "marmelo"}): "quince",
    frozenset({"rutabaga", "swede"}): "rutabaga",
    frozenset({"sweetsop", "sugar apple"}): "sugar apple",
    frozenset({"tapereba", "caja fruit"}): "caja fruit",
    frozenset({"wax gourd", "winter melon"}): "winter melon",
    # not a true synonym pair (raspberry, blackberry and boysenberry are
    # three distinct berries VCF grouped under one head) — resolved
    # 2026-08-28 (James): treat as raspberry.
    frozenset({"raspberry", "blackberry and boysenberry"}): "raspberry",
}

# One-off human calls that need outside domain knowledge the raw string
# doesn't itself contain — not a generalizable pattern, so kept explicit
# and auditable here rather than folded into the parser's rule logic.
RAW_NAME_OVERRIDES = {
    "ORIGANUM (Spanish) (Coridothymus cap.(L.) Rchb.)": {
        "base_ingredient": "spanish oregano",
        "aliases": ["oregano"],
        "note": (
            "resolved 2026-08-28 (James): Coridothymus capitatus is Spanish "
            "oregano, a distinct herb from Origanum vulgare, not 'origanum, "
            "the Spanish kind' — the raw string alone doesn't say this."
        ),
    },
    # Resolved 2026-08-28 (James): "LAMB and MUTTON" / "... FAT" / "... LIVER"
    # were three more atomic base_ingredients that never hit the multi-name-
    # head logic (no comma — "lamb and mutton" is one continuous phrase, not
    # "LAMB, MUTTON"), leaving them stranded from the separate "lamb" and
    # "mutton" entries. Merged all seven raw products (lamb, mutton x3, and
    # the three combined-label rows) into one "lamb and mutton" spine entry —
    # VCF's own inconsistent reporting of the same two ages of one animal
    # shouldn't fragment the ingredient identity. "fat"/"liver" (not proper
    # preparation words, and not in FORM_SUFFIX_WORDS) are kept as
    # preparation tags rather than dropped, same treatment as the Pistacia
    # plant-part fix above.
    "LAMB (roasted)": {
        "base_ingredient": "lamb and mutton",
        "aliases": ["lamb"],
        "note": "resolved 2026-08-28 (James): merged lamb + mutton into one spine entry.",
    },
    "LAMB and MUTTON": {
        "base_ingredient": "lamb and mutton",
        "note": "resolved 2026-08-28 (James): merged lamb + mutton into one spine entry.",
    },
    "LAMB and MUTTON FAT (heated)": {
        "base_ingredient": "lamb and mutton",
        "preparation_add": ["fat"],
        "note": "resolved 2026-08-28 (James): merged lamb + mutton into one spine entry.",
    },
    "LAMB and MUTTON LIVER": {
        "base_ingredient": "lamb and mutton",
        "preparation_add": ["liver"],
        "note": "resolved 2026-08-28 (James): merged lamb + mutton into one spine entry.",
    },
    "MUTTON (boiled)": {
        "base_ingredient": "lamb and mutton",
        "aliases": ["mutton"],
        "note": "resolved 2026-08-28 (James): merged lamb + mutton into one spine entry.",
    },
    "MUTTON (cooked)": {
        "base_ingredient": "lamb and mutton",
        "aliases": ["mutton"],
        "note": "resolved 2026-08-28 (James): merged lamb + mutton into one spine entry.",
    },
    "MUTTON (raw)": {
        "base_ingredient": "lamb and mutton",
        "aliases": ["mutton"],
        "note": "resolved 2026-08-28 (James): merged lamb + mutton into one spine entry.",
    },
    "FENNEL (Foeniculum vulg., ssp. capillaceum; var.)": {
        # ssp. capillaceum covers three varieties (var. vulgare = bitter,
        # var. dulce = sweet, var. azoricum = bulb/Florence) and the source
        # string's own var. designation is truncated — nothing after "var.".
        # Resolved 2026-08-28 (James): treated as standard culinary bulb
        # fennel and as a duplicate of VEGETABLE FENNEL (var. azoricum
        # (Miller)), which is dropped upstream (DUPLICATE_PRODUCTS_TO_DROP)
        # since this row's 46 compounds are a strict superset of its 25.
        # base_ingredient is plain "fennel" (the bare word defaults to bulb
        # fennel in a kitchen context; sweet/bitter fennel are separately
        # and distinctly named elsewhere in this corpus) rather than
        # "vegetable fennel", now that there's no separate row to match.
        "base_ingredient": "fennel",
        "aliases": ["vegetable fennel", "florence fennel"],
        "cultivar": "bulb (var. azoricum)",
        "note": (
            "resolved 2026-08-28 (James): source var. designation is "
            "truncated; treated as standard culinary bulb fennel. Also "
            "absorbed VEGETABLE FENNEL (var. azoricum (Miller)) as a "
            "duplicate submission — same source file, its 25 compounds are "
            "a strict subset of this row's 46 — dropped upstream rather "
            "than kept as a separate product."
        ),
    },
    # Resolved 2026-08-28 (James, family-candidates review): AMERICAN and
    # EUROPEAN cranberry are different species (Vaccinium macrocarpon vs.
    # V. oxycoccos) but James chose chef efficiency over botanical accuracy
    # here, same trade as the fennel dedup above — one "cranberry" spine
    # entry a chef can act on, rather than three fragments (these two plus
    # the existing CRANBERRY (sweetened and dried, craisin) bare product).
    "AMERICAN CRANBERRY (Vaccinium macrocarpon Ait.)": {
        "base_ingredient": "cranberry",
        "aliases": ["american cranberry"],
        "note": "resolved 2026-08-28 (James): merged into one cranberry spine entry — chef efficiency over species accuracy.",
    },
    "EUROPEAN CRANBERRY (Vaccinium oxycoccus L.)": {
        "base_ingredient": "cranberry",
        "aliases": ["european cranberry"],
        "note": "resolved 2026-08-28 (James): merged into one cranberry spine entry — chef efficiency over species accuracy.",
    },
    # Resolved 2026-08-28 (James, family-candidates review): these two never
    # hit the parser's normal preparation extraction because "roasted"/
    # "fermented" lead the string with no comma or parens to trigger it
    # (contrast "PEANUT (roasted)", which does). Left as-is they read as two
    # unrelated products ("roasted cocoa beans", "fermented cocoa beans")
    # instead of one ingredient at two processing stages. base_ingredient
    # becomes "cocoa beans" with the stage carried in `preparation`, same
    # shape as every other raw/roasted pair in this corpus.
    "ROASTED COCOA BEANS": {
        "base_ingredient": "cocoa beans",
        "preparation_add": ["roasted"],
        "note": "resolved 2026-08-28 (James): leading prep word wasn't extracted by the normal parser path; base_ingredient corrected to 'cocoa beans'.",
    },
    "FERMENTED COCOA BEANS": {
        "base_ingredient": "cocoa beans",
        "preparation_add": ["fermented"],
        "note": "resolved 2026-08-28 (James): leading prep word wasn't extracted by the normal parser path; base_ingredient corrected to 'cocoa beans'.",
    },
    # Resolved 2026-08-30 (James, "the split" / binomial-parser fix pass):
    # six rows newly surfaced as needs_review by the broadened binomial
    # detector, all sharing one shape — a paren group with a COMMA that
    # mixes a real binomial citation with a plain-English descriptor or a
    # second common/cultivar name, e.g. "(Asparagopsis taxiformis, red
    # algae)". classify_paren_group only has an all-or-nothing rule for a
    # multi-part paren ("binomial" if every comma-part looks binomial,
    # "alias" if none do) — it correctly declines to guess when the parts
    # disagree, same as it already declines on other genuinely mixed
    # parentheticals. That's a case-by-case human call, not a rule to
    # generalize, per this file's own convention (see FENNEL/ORIGANUM
    # above) — so each is resolved explicitly rather than by loosening the
    # classifier further, which risks re-opening the false-positive
    # surface just closed for demonyms.
    "ALGA (Asparagopsis taxiformis, red algae)": {
        "base_ingredient": "alga",
        "aliases": ["red algae"],
        "binomial": "Asparagopsis taxiformis",
        "note": "resolved 2026-08-30 (James): binomial + plain-English descriptor in one comma-joined paren; split explicitly.",
    },
    "KELP (Laminaria angustata, brown algae)": {
        "base_ingredient": "kelp",
        "aliases": ["brown algae"],
        "binomial": "Laminaria angustata",
        "note": "resolved 2026-08-30 (James): binomial + plain-English descriptor in one comma-joined paren; split explicitly.",
    },
    "KIWIFRUIT (Actinidia chinensis, syn. A. deliciosa)": {
        "base_ingredient": "kiwifruit",
        "aliases": ["syn. a. deliciosa"],
        "binomial": "Actinidia chinensis",
        "note": "resolved 2026-08-30 (James): primary binomial plus an abbreviated-genus synonym citation in one comma-joined paren; binomial set to the primary name, synonym kept in aliases rather than parsed further.",
    },
    "BARTLETT PEAR (Williams pear, Bon Chretien)": {
        "base_ingredient": "bartlett pear",
        "aliases": ["williams pear", "bon chretien"],
        "note": (
            "resolved 2026-08-30 (James): neither 'Williams pear' nor 'Bon "
            "Chretien' is a scientific name — both are common/cultivar "
            "synonyms for Bartlett pear (the shape detector's Capitalized-"
            "word+lowercase-word test can't tell a proper-noun cultivar "
            "name from a genus on shape alone, same class of ambiguity as "
            "the demonym case, just with an eponym instead) — no binomial "
            "is recorded for this row."
        ),
    },
    "CAPSICUM ANNUUM (Bell pepper, sweet pepper)": {
        "base_ingredient": "capsicum annuum",
        "aliases": ["bell pepper", "sweet pepper"],
        "note": (
            "resolved 2026-08-30 (James): 'Bell pepper' is a common name, "
            "not a citation — same eponym/proper-noun ambiguity as Bartlett "
            "pear above. The head 'CAPSICUM ANNUUM' is itself a bare, "
            "unmarked binomial (no author, no 'species' word) and is left "
            "unresolved rather than guessed, consistent with how every "
            "other marker-less all-caps head-only binomial in this corpus "
            "is handled — see the head-only fix note in parse_product."
        ),
    },
    # These two are exactly the "bare, marker-less head-only binomial"
    # case the parser deliberately leaves unresolved (see parse_product) —
    # both are real, undisputed binomials (Brassica campestris = B. rapa,
    # the Chinese cabbage/turnip species complex; Juniperus communis =
    # common juniper) that the string alone doesn't flag as taxonomic
    # (no author, no "species" word) and whose genus isn't independently
    # established elsewhere in this corpus via a properly-cased paren.
    # Confirmed directly relevant to "the split" 2026-08-30 (James) — both
    # feed genus-match containment for coverage-gap pairs (BRASSICA
    # CAMPESTRIS / CHINESE CABBAGE, / TURNIP; JUNIPER BERRY / JUNIPERUS
    # COMMUNIS) — resolved here as an explicit, auditable human call
    # rather than by loosening the automatic detector further.
    "BRASSICA CAMPESTRIS": {
        "base_ingredient": "brassica campestris",
        "binomial": "Brassica campestris",
        "note": "resolved 2026-08-30 (James, 'the split'): bare marker-less head-only binomial, confirmed real (B. rapa complex).",
    },
    "JUNIPERUS COMMUNIS": {
        "base_ingredient": "juniperus communis",
        "binomial": "Juniperus communis",
        "note": "resolved 2026-08-30 (James, 'the split'): bare marker-less head-only binomial, confirmed real (common juniper); genus not otherwise established elsewhere in this corpus.",
    },
    "WASABI (Wasabi japonica) (Japanese horseradish)": {
        "base_ingredient": "wasabi",
        "aliases": ["japanese horseradish"],
        "binomial": "Wasabi japonica",
        "note": (
            "resolved 2026-08-30 (James): base_ingredient 'wasabi' now "
            "coincides with the newly-recognized genus 'Wasabi' — that's "
            "correct, not a defect, since 'wasabi' is also exactly what a "
            "US line cook calls it; 'Japanese horseradish' (a plain "
            "descriptive alias, not a citation — excluded from the "
            "binomial detector by the demonym rule) is kept as an alias."
        ),
    },
    # 2026-08-30 (James, "the split" — asymmetric coverage-gap triage,
    # Bucket A): genus_of() in spine_cluster_candidates.py only resolves a
    # genus from a parsed `binomial` field or from a raw_name literally
    # matching "X SPECIES" — neither path fires for these six, so each
    # showed up paired against a genus-confirmed sibling (Thyme, Grape,
    # Plum, Xylopia, Curcuma, common juniper) with genus_call="asymmetric"
    # rather than being mechanically confirmable. Fixing the tag, not
    # merging the spine entries — whether/how these cluster is a separate,
    # later decision once a real cluster proposal exists to review.
    "THYMUS, OTHER TYPES": {
        "base_ingredient": "thymus",
        "binomial": "Thymus species",
        "note": (
            "resolved 2026-08-30 (James): 'OTHER TYPES' is the same "
            "unspecified-species catch-all shape as 'CAPSICUM SPECIES' or "
            "'CURCUMA SPECIES', just spelled without the literal word "
            "'SPECIES' that the genus detector keys on — tagged explicitly "
            "so it resolves the same way those do."
        ),
    },
    "VITIS ROTUNDIFOLIA": {
        "base_ingredient": "vitis rotundifolia",
        "binomial": "Vitis rotundifolia",
        "note": (
            "resolved 2026-08-30 (James): muscadine grape, a real, "
            "undisputed species — bare marker-less head-only binomial, "
            "same shape as Brassica campestris/Juniperus communis above."
        ),
    },
    "PRUNUS SIMONII": {
        "base_ingredient": "prunus simonii",
        "binomial": "Prunus simonii",
        "note": (
            "resolved 2026-08-30 (James): apricot plum (Simon plum), a "
            "real, undisputed species — bare marker-less head-only "
            "binomial, same shape as Brassica campestris/Juniperus "
            "communis above."
        ),
    },
    "XYLOPIA PARVIFLORA (A. RICH) BENTH.": {
        "base_ingredient": "xylopia parviflora benth.",
        "binomial": "Xylopia parviflora",
        "note": (
            "resolved 2026-08-30 (James): real species; the paren group "
            "is an author citation (A. Rich ex Benth.), not a marker the "
            "existing paren-group binomial classifier recognized on its "
            "own — tagged explicitly rather than loosening that detector "
            "further."
        ),
    },
    "CURCUMA WENYUJIN": {
        "base_ingredient": "curcuma wenyujin",
        "binomial": "Curcuma wenyujin",
        "note": (
            "resolved 2026-08-30 (James): 'wenyujin' is a real, recognized "
            "species epithet (Curcuma wenyujin Y.H.Chen & C.Ling), not a "
            "vernacular/cultivar name — confirmed before tagging, given "
            "the fennel-override lesson earlier this pass about extending "
            "genus calls by unverified analogy."
        ),
    },
    "ETHIOPIAN PEPPER, GUINEA PEPPER (X. aethiopica)": {
        "base_ingredient": "guinea pepper",
        "binomial": "Xylopia aethiopica",
        "note": (
            "resolved 2026-08-30 (James): the paren already carries the "
            "real binomial in genus-abbreviated form ('X. aethiopica') — "
            "expanded to the full genus so genus_of() can resolve it the "
            "same way as a fully-spelled binomial; Xylopia aethiopica "
            "(grains of Selim / Ethiopian/Guinea pepper) is the "
            "undisputed species this common name refers to."
        ),
    },
    "JUNIPER BERRY": {
        "base_ingredient": "juniper berry",
        "binomial": "Juniperus communis",
        "note": (
            "resolved 2026-08-30 (James): pure common name, no Latin in "
            "the raw string at all — genus_of() has no common-name lookup, "
            "so this could never resolve without an explicit tag. "
            "Juniperus communis is the undisputed species VCF's own "
            "separate 'JUNIPERUS COMMUNIS' entry already names for the "
            "same fruit; tagging this one the same binomial lets the "
            "mechanism see they're the same genus without asserting they "
            "must merge — that stays a separate cluster-review decision."
        ),
    },
}

# A multi-name head where the second segment is a variety qualifier, not an
# alternate proper name for the same food ("PEAR, OTHER TYPES" is pear of an
# unspecified variety, not a food called "other types"). Maps to `cultivar`
# rather than swapping base_ingredient.
QUALIFIER_TO_CULTIVAR = {
    "other": "unspecified",
    "other types": "unspecified",
    "other varieties": "unspecified",
    "other species": "unspecified",
    "wild": "wild",
}

# A trailing "Category <roman/numeral>" on the head (VCF's own analytical
# bucketing, e.g. rum graded by total-volatiles ppm) is not a distinct food —
# stripped from the head before base_ingredient is derived, and the tier
# recorded as a note rather than fragmenting one ingredient into several.
CATEGORY_SUFFIX_RE = re.compile(r",?\s*Category\s+([IVXLCDM]+|\d+)\s*$", re.IGNORECASE)

GENUS_SPECIES_WORD_RE = re.compile(r"^[A-Z][a-zà-ÿ]+\s+species\.?$")
TRAILING_AUTHOR_ABBR_RE = re.compile(r"\b[A-Z][a-zà-ÿ]{0,10}\.\s*$")
TAXO_JARGON_RE = re.compile(r"\b(var\.|subsp\.|cultivars?|spp\.)\b", re.IGNORECASE)
# Standard botanical citation shape with a nested basionym-author paren, e.g.
# "Agastache foeniculum (Pursh) Kuntze" or "Coridothymus cap.(L.) Rchb." —
# only reachable once nested parens are extracted without leaving stray
# characters behind (see extract_top_level_parens).
NESTED_AUTHOR_BINOMIAL_RE = re.compile(
    r"^[A-Z][a-zà-ÿ]+\s+[a-zà-ÿ][a-zà-ÿ.\-]*\.?\s*\([^)]*\)\s*[A-Z][a-zà-ÿ]*\.?\s*$"
)

# Step 3 correction to Step 2's preliminary class tagging (spec assigns
# "class" finalization to Step 3; kept here so vcf_product_parse.jsonl stays
# the single source of truth). Both are bare species-level entries (no
# prep/form) for Pistacia species this corpus otherwise uses only for
# essential oils/resin — every other member sharing their base_ingredient
# is already tagged reference (bud/fruit/leaf/gall/oleoresin oil), and
# Pistacia palaestina is given here as a synonym of Pistacia terebinthus,
# literally the "TURPENTINE" species the spec itself names as a
# reference-only example. Nothing in this corpus suggests either is eaten;
# they only defaulted to culinary because the raw string has no
# OIL/EXTRACT/OLEORESIN keyword to trip REFERENCE_SUFFIX_RE. Contrast with
# "MASTIC (Pistacia lentiscus)", which stays culinary — mastic resin has a
# real, established food use (confectionery, ice cream) that these don't.
CLASS_OVERRIDES = {
    "Pistacia atlantica": "reference",
    "Pistacia palaestina (Pistacia terebinthus L.)": "reference",
}

REFERENCE_SUFFIX_RE = re.compile(r"\b(OIL|EXTRACT|OLEORESIN)\b", re.IGNORECASE)
CULINARY_OIL_SOURCES = {
    "coconut", "olive", "peanut", "walnut", "corn", "dent corn", "sesame",
    "sunflower", "canola", "rapeseed", "soybean", "soy", "avocado", "palm",
    "grapeseed", "pistachio", "almond", "hazelnut", "pumpkin", "flaxseed",
    "linseed", "safflower", "cottonseed", "rice bran", "wheat germ",
    "walnut kernel", "annatto",
}

GENUS_WORDS: set[str] = set()

# Parser gap found 2026-08-30 (James, "the split"): the four checks above all
# require some EXTRA marker on top of the genus+species shape itself — the
# literal word "species", var./subsp./cultivar/spp. jargon, a trailing
# single-letter-style author abbreviation ending in a period, or a nested
# basionym-author paren. A binomial citation that's just "Genus species
# FullAuthorSurname" with no period at all (e.g. "Myristica fragrans
# Houttuyn") or a bare "Genus species" with no author at all (e.g. "Agave
# salmiana") satisfies none of them and silently fell into the plain-`alias`
# bucket instead — confirmed via direct check of vcf_product_parse.jsonl,
# not a hypothesis: Mace/Nutmeg's shared "Myristica fragrans Houttuyn" and
# Mezcal/Tequila's "Agave salmiana"/"Agave tequilana" all had binomial=None
# despite the string sitting right there. Fix: recognize the shape directly —
# a capitalized genus-looking first word (>=3 letters) followed by an
# all-lowercase species-epithet word — regardless of what, if anything,
# follows. This only fires on content whose case is ALREADY genus-shaped
# (Title Case genus, lowercase species), which is how this corpus renders
# real binomials inside parens.
#
# Verified against every paren group in the corpus matching this shape
# (230+ instances, by direct enumeration) before landing it: one false
# positive surfaced — "WASABI (Wasabi japonica) (Japanese horseradish)",
# where "Japanese horseradish" is a plain English alias, not a citation,
# and happens to share the shape. What distinguishes it is that word 1 is
# a nationality/regional adjective, not a genus — a closed, enumerable set
# in food-product English, unlike distinguishing a real species epithet
# from an ordinary noun (see the head-only fix below, where that line
# can't be drawn as cleanly). Excluded rather than guessed at case by
# case, same convention as SPELLING_EQUIVALENCE/KNOWN_BASE_PREFERENCE
# elsewhere in this file.
DEMONYM_ADJECTIVES = {
    "american", "european", "chinese", "japanese", "italian", "indian",
    "spanish", "german", "roman", "scotch", "french", "korean",
    "ethiopian", "english", "african", "australian", "mexican", "thai",
    "greek", "russian", "dutch", "swiss", "irish", "canadian",
}
GENUS_SPECIES_SHAPE_RE = re.compile(r"^([A-Z][a-zà-ÿ]{2,})\s+×?[a-zà-ÿ][a-zà-ÿ\-]{1,}\b")


def looks_binomial_strict(content: str) -> bool:
    c = content.strip()
    if GENUS_SPECIES_WORD_RE.match(c):
        return True
    if TAXO_JARGON_RE.search(c):
        return True
    if re.match(r"^[A-Z][a-zà-ÿ]+", c) and TRAILING_AUTHOR_ABBR_RE.search(c):
        return True
    if NESTED_AUTHOR_BINOMIAL_RE.match(c):
        return True
    m = GENUS_SPECIES_SHAPE_RE.match(c)
    if m and m.group(1).lower() not in DEMONYM_ADJECTIVES:
        return True
    return False


def _reconstruct_binomial_casing(words: list[str]) -> str:
    """Standard botanical citation casing (Genus lowercase-species
    Author.) from an ALL-CAPS source head — see the head-only binomial
    fix in parse_product. The source gives us no case information to
    recover verbatim, so this reconstructs the conventional form rather
    than guessing at the original: first word capitalized (genus), middle
    words lowercase (species epithet), a trailing word ending in "." kept
    capitalized (author abbreviation, e.g. "Roxb.", "Val.")."""
    out = []
    for i, w in enumerate(words):
        lw = w.lower()
        if i == 0:
            out.append(lw[:1].upper() + lw[1:])
        elif lw.endswith("."):
            out.append(lw[:1].upper() + lw[1:])
        else:
            out.append(lw)
    return " ".join(out)


def extract_top_level_parens(s: str) -> tuple[str, list[str]]:
    """Balanced paren extraction. A plain \\([^)]*\\) regex isn't nesting-aware
    and mis-splits a top-level group that itself contains a parenthetical —
    the standard botanical citation shape "Genus species (Basionym Author)
    Combining Author)" — leaving a stray "(" or ")" in the remaining head
    text instead of one clean group. This walks the string with a depth
    counter so a top-level group's content (including any nested parens) is
    captured whole, and nothing leaks into the returned head."""
    groups: list[str] = []
    out: list[str] = []
    depth = 0
    start = None
    for i, ch in enumerate(s):
        if ch == "(":
            if depth == 0:
                start = i + 1
            depth += 1
        elif ch == ")":
            if depth > 0:
                depth -= 1
                if depth == 0 and start is not None:
                    groups.append(s[start:i])
                    start = None
        elif depth == 0:
            out.append(ch)
    return "".join(out), groups


def looks_binomial(content: str) -> bool:
    c = content.strip()
    if looks_binomial_strict(c):
        return True
    words = c.split()
    if len(words) >= 2:
        first = words[0].lower().rstrip(".")
        if first in GENUS_WORDS and words[1][:1].islower():
            return True
    return False


def classify_paren_group(content: str):
    raw = content.strip()
    low = raw.lower()
    parts = [p.strip() for p in raw.split(",")]
    parts_low = [p.lower() for p in parts]

    if all(p in PREP_WORDS for p in parts_low) and parts_low[0] != "":
        return ("prep", parts_low)
    if low in PREP_PHRASES:
        return ("prep_phrase", PREP_PHRASES[low])
    if low in FORM_STATE_PHRASES:
        return ("form_state", FORM_STATE_PHRASES[low])
    if low == "generic":
        return ("cultivar", "generic")
    if low in STATE_WORDS:
        return ("state", low)
    if low in FORM_SUFFIX_WORDS:
        return ("form", low)
    # infraspecific variety marker ("var. dulce (Miller)", "var. chia") ->
    # cultivar, not a full binomial — checked ahead of the binomial test
    # since TAXO_JARGON_RE alone would also pass this as "binomial".
    if re.match(r"^\s*(var\.|subsp\.)", low):
        return ("cultivar", raw)
    if raw.startswith("="):
        # scientific-synonym marker, e.g. "(= Psalliota)" -> genus Psalliota
        # is a former/alternate name for the same organism.
        return ("synonym_alias", raw.lstrip("=").strip().lower())
    if re.match(r"^total volatiles\b", low):
        # VCF's own analytical intensity bucket (e.g. rum graded by total
        # volatile-compound ppm) — not a food property, kept as a note.
        return ("volatile_note", raw)
    if parts and all(looks_binomial(p) for p in parts):
        return ("binomial", raw)
    if all(re.match(r"^[A-Za-z][A-Za-z .\-']*$", p) for p in parts):
        if not any(looks_binomial(p) for p in parts):
            return ("alias", [p.lower() for p in parts])
    return ("unclassified", raw)


def split_head(head: str):
    cure_state = None
    state = None
    form = None
    segs = [s.strip() for s in head.split(",")]
    kept_segs = []
    for s in segs:
        if s.lower() in CURE_HEAD_WORDS:
            cure_state = s.lower()
        else:
            kept_segs.append(s)
    head = ", ".join(kept_segs)

    words = head.split()
    while words and words[-1].lower() in (FORM_SUFFIX_WORDS | STATE_WORDS):
        last = words.pop().lower()
        if last in FORM_SUFFIX_WORDS:
            form = last
        elif last in STATE_WORDS:
            state = last
    head = " ".join(words)
    return head, cure_state, state, form


def parse_product(raw_name: str, product_group: str, pid: int) -> dict:
    reasons: list[str] = []
    needs_review = False

    head, paren_groups = extract_top_level_parens(raw_name)
    head = head.strip().rstrip(",").strip()

    # A trailing "Category <roman>" (VCF's own analytical bucket, not a
    # distinct food) is stripped before base_ingredient is derived; the tier
    # is recorded via the paired "total volatiles..." paren group below.
    category_tier = None
    cat_match = CATEGORY_SUFFIX_RE.search(head)
    if cat_match:
        category_tier = f"category {cat_match.group(1).lower()}"
        head = head[: cat_match.start()].rstrip(", ").strip()

    head_clean, cure_state, state, form = split_head(head)

    aliases: list[str] = []
    preparation: list[str] = []
    cultivar = None
    binomial = None

    for group in paren_groups:
        kind, payload = classify_paren_group(group)
        if kind == "prep":
            preparation.extend(payload)
        elif kind == "prep_phrase":
            preparation.extend(payload)
            if not payload:
                reasons.append(f"paren phrase not mapped to a prep/state value: '{group.strip()}'")
                needs_review = True
        elif kind == "state":
            state = state or payload
        elif kind == "form":
            form = form or payload
        elif kind == "cultivar":
            cultivar = payload
        elif kind == "binomial":
            if binomial:
                reasons.append(f"multiple binomial-like paren groups; kept first, extra: '{group.strip()}'")
                needs_review = True
            else:
                binomial = payload.strip()
        elif kind == "form_state":
            fs_state, fs_form = payload
            state = state or fs_state
            form = form or fs_form
        elif kind == "synonym_alias":
            aliases.append(payload)
        elif kind == "volatile_note":
            note = f"{category_tier}: {payload.lower()}" if category_tier else payload.lower()
            aliases.append(note)
        elif kind == "alias":
            aliases.extend(payload)
        else:
            reasons.append(f"unclassified parenthetical: '{group.strip()}'")
            needs_review = True

    head_segs = [s.strip() for s in head_clean.split(",") if s.strip()]
    base_ingredient = None
    if not head_segs:
        reasons.append("empty head after stripping modifiers")
        needs_review = True
    elif len(head_segs) == 1:
        base_ingredient = head_segs[0].lower()
        # Parser gap found 2026-08-30 (James, "the split"): a product whose
        # ENTIRE head is a bare scientific name with no parens at all (VCF
        # sometimes reports species-level rows this way, e.g. "JUNIPERUS
        # COMMUNIS", "CURCUMA AERUGINOSA ROXB.") never ran through ANY
        # binomial check — that logic only ever looked inside paren groups
        # or the two-segment comma case. Being ALL CAPS, it also can't be
        # caught by shape (GENUS_SPECIES_SHAPE_RE needs a lowercase second
        # word to signal "this is Title Case", which all-caps destroys) —
        # so GENUS_WORDS membership of word 1 is the only signal available.
        # That alone is too loose: a first pass using it bare produced real
        # false positives ("ANGELICA ROOT OIL" -> binomial "Angelica root",
        # "CITRUS FRUITS" -> "Citrus fruits", "MENTHA OILS" -> "Mentha
        # oils") because "angelica"/"citrus"/"mentha" are all real,
        # correctly-known genera elsewhere in the corpus, but "root"/
        # "fruits"/"oils" are plant-part or form words, not species
        # epithets — and nothing in an ALL-CAPS head distinguishes a real
        # epithet from an ordinary English noun the way case does in a
        # properly-rendered paren. So this additionally requires an
        # explicit taxonomic marker elsewhere in the head — a trailing
        # author abbreviation (ends in ".": "ROXB.", "VAL."), the literal
        # "SPECIES" placeholder, or var./subsp./cultivar/spp. jargon — the
        # same markers looks_binomial_strict already trusts, just checked
        # against ALL-CAPS text directly since periods and the word
        # "species" survive case-folding. "CURCUMA AERUGINOSA ROXB." and
        # "CURCUMA HEYNEANA VAL." both carry one; "CURCUMA WENYUJIN" (bare
        # genus + epithet, no marker) and "JUNIPERUS COMMUNIS" (genus not
        # independently established anywhere else in the corpus either) do
        # not, and are left unresolved rather than guessed — the same
        # "flag/leave, don't silently guess" rule this file already
        # follows elsewhere.
        head_words = head_segs[0].split()
        has_taxo_marker = bool(head_words) and (
            head_words[-1].endswith(".")
            or head_words[-1].lower() == "species"
            or TAXO_JARGON_RE.search(head_segs[0])
        )
        if (
            binomial is None
            and len(head_words) >= 2
            and len(head_words[0]) > 2
            and head_words[0].lower().rstrip(".") in GENUS_WORDS
            and has_taxo_marker
        ):
            binomial = _reconstruct_binomial_casing(head_words)
    else:
        key = frozenset(s.lower() for s in head_segs)
        last_low = head_segs[-1].lower()
        if key in KNOWN_BASE_PREFERENCE:
            preferred = KNOWN_BASE_PREFERENCE[key]
            base_ingredient = preferred
            aliases = [s.lower() for s in head_segs if s.lower() != preferred] + aliases
        elif len(head_segs) == 2 and last_low in QUALIFIER_TO_CULTIVAR:
            # "PEAR, OTHER TYPES" etc — the second segment is a variety
            # qualifier, not an alternate proper name; resolved 2026-08-28
            # (James), generalized from the pear case.
            base_ingredient = head_segs[0].lower()
            cultivar = cultivar or QUALIFIER_TO_CULTIVAR[last_low]
        elif len(head_segs) == 2 and looks_binomial(head_segs[0]):
            # "Pistacia atlantica, LEAF OIL" — the first segment is the
            # species identity (no common name given), the second is the
            # plant part the oil was drawn from. The old last-segment
            # heuristic discarded the species and left a bare body-part
            # word as base_ingredient.
            binomial = binomial or head_segs[0]
            base_ingredient = head_segs[0].lower()
            preparation.append(last_low)
        else:
            base_ingredient = head_segs[-1].lower()
            aliases = [s.lower() for s in head_segs[:-1]] + aliases
            reasons.append(f"multi-name head {head_segs} — base_ingredient guessed as last segment")
            needs_review = True

    seen: set[str] = set()
    prep_out = []
    for p in preparation:
        if p not in seen:
            seen.add(p)
            prep_out.append(p)

    if raw_name in RAW_NAME_OVERRIDES:
        override = RAW_NAME_OVERRIDES[raw_name]
        base_ingredient = override["base_ingredient"]
        aliases = list(override.get("aliases", aliases))
        if "cultivar" in override:
            cultivar = override["cultivar"]
        if "binomial" in override:
            binomial = override["binomial"]
        if "preparation_add" in override:
            for p in override["preparation_add"]:
                if p not in prep_out:
                    prep_out.append(p)
        reasons = [override["note"]]
        needs_review = False

    # Skip this check for rows already resolved by an explicit override —
    # that override IS the human call this check exists to prompt; running
    # it again afterward just re-flags an already-decided row (found
    # 2026-08-30: WASABI, where "wasabi" legitimately is both the genus and
    # the chef-facing name, and the override says so).
    if raw_name not in RAW_NAME_OVERRIDES and base_ingredient and aliases:
        first_word = base_ingredient.split()[0]
        if first_word in GENUS_WORDS:
            reasons.append(
                f"base_ingredient '{base_ingredient}' looks like a scientific name; "
                f"aliases {aliases} may be the more chef-friendly base"
            )
            needs_review = True

    is_reference = bool(REFERENCE_SUFFIX_RE.search(raw_name))
    if is_reference and base_ingredient and base_ingredient in CULINARY_OIL_SOURCES:
        is_reference = False
    if raw_name in CLASS_OVERRIDES:
        is_reference = CLASS_OVERRIDES[raw_name] == "reference"

    return {
        "vcf_product_id": pid,
        "raw_name": raw_name,
        "base_ingredient": base_ingredient,
        "aliases": sorted(set(aliases)),
        "preparation": prep_out,
        "cure_state": cure_state,
        "state": state,
        "form": form,
        "cultivar": cultivar,
        "binomial": binomial,
        "product_group": product_group,
        "class": "reference" if is_reference else "culinary",
        "needs_review": needs_review,
        "review_reason": "; ".join(reasons) if reasons else "",
    }


def main():
    kept = load_and_concat()
    kept.to_parquet(OUT_DIR / "step1_concat.parquet", index=False)

    products = (
        kept[["Product", "Product Group"]]
        .drop_duplicates(subset=["Product"])
        .sort_values("Product")
        .reset_index(drop=True)
    )

    global GENUS_WORDS
    for raw_name in products["Product"]:
        _, groups = extract_top_level_parens(raw_name)
        for group in groups:
            for part in group.split(","):
                part = part.strip()
                if looks_binomial_strict(part):
                    first = part.split()[0].lower().rstrip(".") if part.split() else ""
                    if len(first) > 2:
                        GENUS_WORDS.add(first)

    rows = [
        parse_product(r.Product, r._1, pid)
        for pid, r in enumerate(products.itertuples(index=False), start=1)
    ]

    with open(OUT_DIR / "vcf_product_parse.jsonl", "w") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    out = pd.DataFrame(rows)
    review = out.copy()
    for col in ("aliases", "preparation"):
        review[col] = review[col].apply(lambda x: "; ".join(x) if x else "")
    review = review.sort_values(["needs_review", "product_group", "raw_name"], ascending=[False, True, True])
    review.to_excel(OUT_DIR / "vcf_product_parse_review.xlsx", index=False, sheet_name="parse_review")

    # Found 2026-08-30 (James, binomial-parser fix pass): this was the ONE
    # script in the whole pipeline that wrote meta.json as a fresh literal
    # dict instead of load-then-merge — every other build_vcf_*.py script
    # reads the existing file first and only sets its own top-level key.
    # Re-running this script (Steps 1&2, upstream of everything) silently
    # discarded every OTHER block meta.json carried — including hand-
    # authored audit blocks no script regenerates (spine_clustering,
    # build1_rebaseline, vendor_workbook_provenance, build1_provenance_
    # audit, DI-BEEF-001) — the moment this script ran again. Confirmed as
    # the actual mechanism behind a real loss encountered while rebasing
    # the parser fix through the pipeline; fixed here so it can't recur.
    meta = json.loads((OUT_DIR / "meta.json").read_text()) if (OUT_DIR / "meta.json").exists() else {}
    meta.update({
        "n_products": len(out),
        "n_needs_review": int(out["needs_review"].sum()),
        "class_counts": out["class"].value_counts().to_dict(),
        "n_source_files": len(list(RAW_DIR.glob("*.csv"))),
        "n_rows_kept": len(kept),
        "n_distinct_compounds": kept["Compound"].nunique(),
    })
    with open(OUT_DIR / "meta.json", "w") as f:
        json.dump(meta, f, indent=2)

    print(f"Wrote {len(out)} parsed products, {meta['n_needs_review']} flagged for review, to {OUT_DIR}")


if __name__ == "__main__":
    main()
