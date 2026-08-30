from pathlib import Path

import pytest

from culin_etl.build import build_artifacts
from culin_etl.parse import load_recipes

FIXTURE = Path(__file__).parent / "fixtures" / "mini_recipes.csv"


@pytest.fixture(scope="session")
def fixture_path() -> Path:
    return FIXTURE


@pytest.fixture(scope="session")
def raw_recipes(fixture_path):
    return list(load_recipes(fixture_path))


@pytest.fixture(scope="session")
def artifacts(fixture_path):
    return build_artifacts(fixture_path)


# --- Step 10: make skips loud -----------------------------------------------
#
# Before this hook, a run missing built artifacts (corpus_tables/
# compound_tables in test_reliability.py skip via pytest.skip() when
# artifacts/corpus or the compound artifacts aren't present, same for
# vcf_artifacts in test_vcf_reliability.py) reported e.g. "9 passed,
# 4 skipped" and exited 0 — indistinguishable from a clean run to anyone
# checking `$?`, which is exactly what a CI gate checks. A green run
# currently proves very little: it can mean "everything was verified" or
# "a third of the suite silently didn't run," and there's no way to tell
# which from the exit code alone.
#
# This doesn't touch what gets skipped or why — every existing pytest.skip
# call and its reason stays exactly as informative as it was. It just makes
# "something was skipped" impossible to miss: an unmissable banner naming
# every skipped test and its reason, and a nonzero exit code so a CI step
# (or a developer glancing at $?) can't mistake a partially-run suite for
# a fully green one.
def pytest_sessionfinish(session, exitstatus):
    reporter = session.config.pluginmanager.get_plugin("terminalreporter")
    skipped = reporter.stats.get("skipped", []) if reporter else []
    if not skipped:
        return
    lines = [
        "",
        "=" * 70,
        f"RELIABILITY SUITE: {len(skipped)} TEST(S) SKIPPED — NOT A CLEAN GREEN RUN",
        "=" * 70,
    ]
    for rep in skipped:
        reason = rep.longrepr[-1] if isinstance(rep.longrepr, tuple) else str(rep.longrepr)
        lines.append(f"  SKIPPED: {rep.nodeid} — {reason}")
    lines.append(
        "See each skip reason above for what to run/copy before these tests "
        "can actually verify anything."
    )
    lines.append("=" * 70)
    print("\n".join(lines))
    if exitstatus == 0:
        session.exitstatus = 1
