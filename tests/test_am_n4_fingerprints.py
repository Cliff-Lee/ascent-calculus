import itertools
import tempfile
import time
from pathlib import Path

import pytest

from ac.core.word import ChainWord
from ac.discovery.fingerprints import (
    DEFAULT_FEATURES,
    analyze_count_match_structure,
    class_structural_profile,
    compare_structural_profiles,
    structural_features,
    structural_fingerprint,
)
from ac.discovery.jobs import ResearchJobStore
from ac.discovery.specification import ClassSpec, DegreeWindow, SearchSpec
from ac.discovery.worker import PersistentWorker
from experiments.reference_ascent import (
    all_tuples,
    ascent_bottoms as ref_bottoms,
    ascent_tops as ref_tops,
    first_occurrences as ref_first,
)


def test_structural_role_features_match_literal_definitions_on_all_small_words():
    for degree in range(1, 5):
        for values in all_tuples(degree):
            features = structural_features(values)
            word = ChainWord(values)
            assert features["new_positions"] == tuple(sorted(ref_first(values)))
            assert features["asctop_positions"] == tuple(sorted(ref_tops(values)))
            assert features["ascbot_positions"] == tuple(sorted(ref_bottoms(values)))
            assert features["new_positions"] == tuple(sorted(word.first_positions))
            assert features["asctop_positions"] == tuple(sorted(word.ascent_tops))
            assert features["ascbot_positions"] == tuple(sorted(word.ascent_bottoms))
            assert features["ascent_count"] == sum(left < right for left, right in zip(values, values[1:]))
            assert features["multiplicity_profile"] == tuple(values.count(i) for i in range(1, max(values) + 1))


def test_fingerprint_explains_new_top_bottom_roles_and_classification():
    fingerprint = structural_fingerprint(ChainWord((1, 3, 1, 2, 2)))
    assert fingerprint["features"]["new_positions"] == [1, 2, 4]
    assert fingerprint["features"]["asctop_positions"] == [1, 2, 4]
    assert fingerprint["features"]["ascbot_positions"] == [1, 3]
    assert fingerprint["classification"] == {"ordinary": False, "modified": True, "revised": False}
    assert fingerprint["positions"][1] == {
        "position": 2, "value": 3, "new": True, "asctop": True, "ascbot": False,
    }
    repeated = structural_fingerprint(ChainWord((1, 3, 1, 2, 2)))
    assert repeated["sha256"] == fingerprint["sha256"]


def test_class_structural_profile_and_joint_role_distribution_are_exact():
    spec = ClassSpec("ordinary")
    features = ("new_positions", "asctop_positions", "new_count", "ascent_count")
    joint = (("new_positions", "asctop_positions"), ("new_positions", "ascent_count"))
    profile = class_structural_profile(spec, 3, features=features, joint_features=joint)
    assert profile["count"] == 5
    assert all(sum(row["count"] for row in entry["distribution"]) == 5 for entry in profile["features"].values())
    assert all(sum(row["count"] for row in entry["distribution"]) == 5 for entry in profile["joint_features"].values())
    comparison = compare_structural_profiles(profile, profile)
    assert comparison["class_counts_equal"]
    assert all(row["equal"] for row in comparison["feature_profiles"])
    assert all(row["equal"] for row in comparison["joint_profiles"])


def test_count_candidate_analysis_finds_structural_mismatches_without_claiming_a_map():
    source = ClassSpec.build("modified", [{"mode": "avoid", "pattern": "111"}])
    target = ClassSpec.build("revised", [{"mode": "avoid", "pattern": "111"}])
    match = {
        "evidence": "count_match",
        "proof_status": "not_proved",
        "degree_offset": 2,
        "source_class": {"specification": source.to_dict()},
        "target_class": {"specification": target.to_dict()},
        "degree_rows": [
            {"base_degree": 1, "source_degree": 1, "source_count": 1, "target_degree": 3, "target_count": 1},
            {"base_degree": 2, "source_degree": 2, "source_count": 2, "target_degree": 4, "target_count": 2},
        ],
    }
    report = analyze_count_match_structure(
        match,
        features=("new_positions", "asctop_positions", "ascbot_positions", "new_count", "asctop_count"),
        joint_features=(("new_positions", "asctop_positions"),),
    )
    assert report["candidate_evidence"] == "count_match"
    assert report["candidate_proof_status"] == "not_proved"
    assert report["degree_comparisons"][0]["class_counts_equal"]
    assert report["feature_summary"][0]["first_mismatch"] == 1
    assert any(not row["equal"] for row in report["degree_comparisons"][0]["feature_profiles"])
    assert "does not construct" in report["explanation"]


def test_registered_worker_checkpoints_structural_profiles_by_degree():
    with tempfile.TemporaryDirectory() as directory:
        database = Path(directory) / "jobs.sqlite3"
        store = ResearchJobStore(database)
        source = ClassSpec.build("modified", [{"mode": "avoid", "pattern": "111"}])
        target = ClassSpec.build("revised", [{"mode": "avoid", "pattern": "111"}])
        spec = SearchSpec("count_equivalence", source, DegreeWindow(1, 2), target, target_offset=2)
        job = store.create_job(
            spec,
            handler="analyze-structural-profiles",
            options={"features": ["new_count", "asctop_count"], "joint_features": [["new_count", "asctop_count"]]},
        )
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
                raise AssertionError("structural-profile worker did not finish")
            assert current.status == "completed", current.error
            assert current.result["status"] == "finite_structural_profile_analysis"
            assert [row["base_degree"] for row in current.result["rows"]] == [1, 2]
            assert current.progress["completed_degrees"] == 2
        finally:
            worker.stop()


def test_feature_request_validation_rejects_unknown_or_duplicate_names():
    with pytest.raises(ValueError, match="registered structural features"):
        class_structural_profile(ClassSpec("ordinary"), 2, features=("not-a-feature",))
    with pytest.raises(ValueError, match="unique"):
        class_structural_profile(ClassSpec("ordinary"), 2, features=("new_count", "new_count"))
    with pytest.raises(ValueError, match="distinct-value budget"):
        class_structural_profile(ClassSpec("ordinary"), 3, features=("edge_word",), max_profile_values=1)
    assert DEFAULT_FEATURES
