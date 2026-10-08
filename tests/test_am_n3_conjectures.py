import tempfile
import time
from pathlib import Path

import pytest

from ac.discovery.conjecture_search import (
    ConjectureSearchSpec,
    discover_count_conjectures,
)
from ac.discovery.jobs import ResearchJobStore
from ac.discovery.specification import ClassSpec, DegreeWindow
from ac.discovery.wilf import cayley_patterns, pattern_avoidance_counts
from ac.discovery.worker import PersistentWorker
from ac.generate.universes import ascent_sequences
from experiments.reference_ascent import contains_pattern, modified as ref_modified, revised as ref_revised


def test_conjecture_search_spec_round_trips_and_canonicalizes_search_space():
    left = ConjectureSearchSpec.build(
        families=("revised", "ordinary", "ordinary"),
        start=1, stop=5, pattern_lengths=(3, 2, 3), modes=("contain", "avoid", "avoid"),
        offsets=(2, 0, -1, 2),
    )
    right = ConjectureSearchSpec.build(
        families=("ordinary", "revised"),
        start=1, stop=5, pattern_lengths=(2, 3), modes=("avoid", "contain"),
        offsets=(-1, 0, 2),
    )
    assert left.canonical_json() == right.canonical_json()
    assert ConjectureSearchSpec.from_json(left.canonical_json()) == left
    assert left.fingerprint == right.fingerprint
    value = left.to_dict()
    value["version"] = True
    with pytest.raises(ValueError, match="unsupported"):
        ConjectureSearchSpec.from_dict(value)


def test_pattern_catalogue_counts_match_independent_subsequence_enumeration():
    for degree in range(1, 5):
        words = [word.values for word in ascent_sequences(degree)]
        total, avoidance = pattern_avoidance_counts("ordinary", degree, 2)
        assert total == len(words)
        for pattern in cayley_patterns(2):
            expected = sum(not contains_pattern(word, pattern.values) for word in words)
            assert avoidance[pattern.values] == expected


def test_automatic_search_finds_the_modified_revised_111_plus_two_count_match():
    plan = ConjectureSearchSpec.build(
        families=("modified", "revised"),
        start=1, stop=5, pattern_lengths=(3,), modes=("avoid",), offsets=(2,),
    )
    result = discover_count_conjectures(plan, keep=50)
    match = next(
        row for row in result["matches"]
        if row["source_class"]["family"] == "modified"
        and row["source_class"]["rule"] == {"mode": "avoid", "pattern": [1, 1, 1]}
        and row["target_class"]["family"] == "revised"
        and row["target_class"]["rule"] == {"mode": "avoid", "pattern": [1, 1, 1]}
    )
    assert match["evidence"] == "count_match"
    assert match["degree_offset"] == 2
    assert [row["source_count"] for row in match["degree_rows"]] == [1, 2, 4, 10, 29]
    assert [row["target_count"] for row in match["degree_rows"]] == [1, 2, 4, 10, 29]
    for row in match["degree_rows"]:
        source = ref_modified(row["source_degree"])
        target = ref_revised(row["target_degree"])
        source_count = sum(not contains_pattern(word, (1, 1, 1)) for word in source)
        target_count = sum(not contains_pattern(word, (1, 1, 1)) for word in target)
        assert source_count == row["source_count"]
        assert target_count == row["target_count"]
    assert match["proof_status"] == "not_proved"


def test_discovery_reports_first_count_counterexample_and_budget_exhaustion():
    plan = ConjectureSearchSpec.build(
        families=("ordinary",), start=1, stop=5, pattern_lengths=(3,),
        modes=("avoid", "contain"), offsets=(0,),
    )
    result = discover_count_conjectures(plan, keep=100)
    failed = next((row for row in result["matches"] if row["evidence"] == "matching_prefix"), None)
    assert failed is not None
    assert failed["counterexample"]["source_count"] != failed["counterexample"]["target_count"]
    limited = discover_count_conjectures(plan, keep=20, pair_budget=1)
    assert limited["search_status"] == "budget_exhausted"
    assert limited["tested"]["candidate_pair_checks"] == 1


def test_persistent_worker_executes_registered_conjecture_search_handler():
    with tempfile.TemporaryDirectory() as directory:
        database = Path(directory) / "jobs.sqlite3"
        store = ResearchJobStore(database)
        plan = ConjectureSearchSpec.build(
            families=("ordinary",), start=1, stop=3, pattern_lengths=(2,),
            modes=("avoid",), offsets=(0,),
        )
        job = store.create_job(plan, handler="discover-pattern-classes", options={"keep": 15})
        worker = PersistentWorker(database, idle_poll_seconds=0.02, stale_after_seconds=0)
        try:
            worker.start()
            deadline = time.monotonic() + 10
            while time.monotonic() < deadline:
                current = store.get_job(job.id)
                if current.status in {"completed", "failed"}:
                    break
                time.sleep(0.01)
            else:
                raise AssertionError("conjecture-discovery worker did not finish")
            assert current.status == "completed", current.error
            assert current.question == plan
            assert current.result["search_fingerprint"] == plan.fingerprint
            assert current.result["completed_pattern_lengths"] == [2]
            assert current.result["search_status"] == "finite_search_completed"
        finally:
            worker.stop()
