"""FooDB Content.csv parsing for balance axes."""

from __future__ import annotations

from culin_etl.foodb_content import load_content_profiles
from culin_etl.vendor_paths import FOODB_CONTENT_CSV


def test_soy_sauce_has_sodium_and_glutamate():
    if not FOODB_CONTENT_CSV.exists():
        return
    profiles, _meta = load_content_profiles(["716"])
    axes = profiles.get("716", {})
    assert axes.get("salt", 0) > 100
    assert axes.get("glut", 0) > 500
