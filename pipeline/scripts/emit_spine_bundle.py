"""
Emit the browser-side spine bundle: pipeline/artifacts/vcf/spine.jsonl -> src/data/spine.json

The app's resolution layer (src/lib/spineResolve.js) must be deterministic and
synchronous — a chef typing "garlic" cannot wait on a network round-trip, and a
resolver that varies between runs makes the shared-compound percentages
untestable. 360 entries / 581 members is small enough to ship in the bundle, so
resolution never leaves the browser.

The one thing computed here rather than in JS is each member's display name.
raw_name carries the VCF binomial ("GARLIC (Allium sativum L.)"); a chef must
see "Garlic". Parsing that once at build time keeps the runtime a pure lookup.

Run from the repo root:  python pipeline/scripts/emit_spine_bundle.py
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "pipeline" / "artifacts" / "vcf" / "spine.jsonl"
OUT = ROOT / "src" / "data" / "spine.json"

# Words that stay lowercase inside a member name once the binomial is stripped.
_KEEP_LOWER = {"raw", "heated", "dried", "fresh", "roasted", "smoked", "cooked", "fermented"}


def member_display(raw_name: str, binomial: str | None) -> str:
    """'GARLIC (Allium sativum L.)' -> 'Garlic'; 'LEEK (raw) (Allium porrum L.)' -> 'Leek (raw)'."""
    name = raw_name or ""
    if binomial:
        # Strip the binomial parenthetical wherever it sits, not just at the end.
        name = name.replace(f"({binomial})", "")
    # Any residual Latin-looking parenthetical (genus + species, or 'X species').
    name = re.sub(r"\(([A-Z][a-z]+ (?:[a-z]+|species)[^)]*)\)", "", name)
    name = re.sub(r"\s+", " ", name).strip()

    parts = re.split(r"(\([^)]*\))", name)
    out = []
    for part in parts:
        if not part:
            continue
        if part.startswith("("):
            inner = part[1:-1].strip().lower()
            out.append(f"({inner})")
        else:
            words = part.strip().split()
            out.append(
                " ".join(w.lower() if w.lower() in _KEEP_LOWER else w.capitalize() for w in words)
            )
    return " ".join(p for p in out if p).strip() or raw_name


def main() -> int:
    rows = [json.loads(line) for line in SRC.open(encoding="utf-8") if line.strip()]
    entries = []
    for r in rows:
        members = []
        for m in r.get("members") or []:
            members.append(
                {
                    "id": m["vcf_product_id"],
                    "raw_name": m["raw_name"],
                    "display": member_display(m["raw_name"], m.get("binomial")),
                    "class": m.get("class"),
                    "preparation": m.get("preparation") or [],
                    "cure_state": m.get("cure_state"),
                    "form": m.get("form"),
                }
            )
        entries.append(
            {
                "spine_id": r["spine_id"],
                # May be null: six entries have no member more generic than its
                # siblings. The resolver renders a member or the queried alias
                # instead — never the entry id. See src/lib/spineResolve.js.
                "display_name": r.get("display_name"),
                "base_ingredient": r.get("base_ingredient"),
                "aliases": r.get("aliases") or [],
                "product_group": r.get("product_group"),
                "policy": r.get("policy"),
                "resolution_confidence": r.get("resolution_confidence"),
                "default_member": r.get("default_member"),
                "members": members,
            }
        )

    entries.sort(key=lambda e: e["spine_id"])
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(entries, ensure_ascii=False), encoding="utf-8")

    culinary = sum(1 for e in entries if any(m["class"] == "culinary" for m in e["members"]))
    print(f"Wrote {len(entries)} spine entries ({sum(len(e['members']) for e in entries)} members) to {OUT}")
    print(f"  {culinary} entries have at least one culinary member; {len(entries) - culinary} are reference-only")
    print(f"  {sum(1 for e in entries if not e['display_name'])} entries carry display_name: null")
    print(f"  bundle size: {OUT.stat().st_size / 1024:.0f}K")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
