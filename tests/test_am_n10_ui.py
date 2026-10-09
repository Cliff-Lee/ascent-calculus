from ac.discovery.specification import ClassSpec, DegreeWindow
from ac.discovery.transformation_search import TransformationGrammarSpec
from ac.discovery.transformation_family import TransformationFamilySearchSpec, run_worker_search
from ac.gui.discovery_campaign import build_transformation_family_spec
from ac.gui.discovery_window import _scenario_evidence_lines, _scenario_map_previews


def test_discover_form_builds_separate_pattern_and_offset_grid():
    spec = build_transformation_family_spec(
        source_family="modified",
        target_family="revised",
        rule_mode="avoid",
        source_patterns="*, 111, 111",
        target_patterns="2122, 2212",
        offsets="0:+2,0:0",
        start=1,
        stop=3,
        max_cost=4,
        max_steps=2,
        candidate_budget=100,
    )
    assert len(spec.scenarios) == 2 * 2 * 2
    assert len({scenario.fingerprint for scenario in spec.scenarios}) == 8
    assert {scenario.degree_shift for scenario in spec.scenarios} == {0, 2}
    assert any(not scenario.source.rules for scenario in spec.scenarios)
    assert {tuple(rule.pattern for rule in scenario.target.rules) for scenario in spec.scenarios} == {
        ((2, 1, 2, 2),), ((2, 2, 1, 2),),
    }
    assert spec.grammar.max_steps == 2


def test_discover_form_rejects_ambiguous_or_overlarge_inputs():
    common = dict(
        source_family="modified", target_family="revised", rule_mode="avoid",
        source_patterns="111", target_patterns="111", start=1, stop=2,
    )
    try:
        build_transformation_family_spec(**common, offsets="0,1:2")
    except ValueError as exc:
        assert "source:target" in str(exc)
    else:
        raise AssertionError("malformed offset was accepted")
    try:
        build_transformation_family_spec(**common, offsets="0:0,0:0")
    except ValueError as exc:
        assert "unique" in str(exc)
    else:
        raise AssertionError("duplicate offset was accepted")


def test_family_candidate_keeps_an_auditable_sample_map_for_preview():
    grammar = TransformationGrammarSpec(
        operations=("symmetry",), selectors=(), boolean_selector_algebra=False,
        position_bound=2, occurrence_rank=1, inserted_value_bound=1,
        max_selectors=20, max_atoms=20, max_cost=2, max_steps=1,
        candidate_budget=20, expansion_budget=200,
        enumeration_budget=100_000, class_object_budget=100_000,
        evaluation_budget=500_000,
    )
    degree_window = DegreeWindow(1, 2)
    spec = TransformationFamilySearchSpec.from_grid(
        (ClassSpec("ordinary"), ClassSpec.build("ordinary", [{"mode": "avoid", "pattern": "11"}])),
        (ClassSpec("ordinary"),), degree_window, grammar,
        offset_pairs=((0, 0),), candidate_budget=20,
        enumeration_budget=100_000, class_object_budget=100_000,
        evaluation_budget=500_000,
    )

    class Context:
        def checkpoint(self, state, progress):
            pass

        def check_control(self):
            pass

    job = type("Job", (), {"question": spec, "checkpoint": {}})()
    result = run_worker_search(job, Context())
    identity = next(row for row in result["ranked_candidates"] if row["program"] == "Identity()")
    preview = identity["example_map_preview"]
    assert preview["source"]["values"] == preview["output"]["values"]
    assert preview["position_map"] == list(range(1, len(preview["source"]["values"]) + 1))
    assert preview["scenario_fingerprint"] == spec.scenarios[0].fingerprint


def test_candidate_evidence_shows_map_examples_for_each_scenario():
    def preview(index, source, output):
        return {
            "base_degree": 2,
            "scenario_fingerprint": f"scenario-{index}",
            "source": {"values": [source], "height": 1},
            "output": {"values": [output], "height": 1},
            "position_map": [1],
            "value_map": [1],
            "created_positions": [],
        }

    first, second = preview(0, 1, 1), preview(1, 1, 2)
    row = {
        "scenario_results": [
            {"scenario_index": 0, "source_class": "A", "target_class": "B", "finite_match": True,
             "source_offset": 0, "target_offset": 0, "verified_through": 2, "evaluation": {}},
            {"scenario_index": 1, "source_class": "C", "target_class": "D", "finite_match": False,
             "source_offset": 0, "target_offset": 1, "verified_through": 2, "evaluation": {}},
        ],
        "scenario_map_previews": [
            {"scenario_index": 0, "scenario_fingerprint": "scenario-0", "example_map": first},
            {"scenario_index": 1, "scenario_fingerprint": "scenario-1", "example_map": second},
        ],
    }

    lines = _scenario_evidence_lines(row)
    joined = "\n".join(lines)
    assert joined.index("Scenario 1") < joined.index("Scenario 2")
    assert "Sample map at base n=2: [1] → [1]" in joined
    assert "Sample map at base n=2: [1] → [2]" in joined
    assert [item["example_map"] for item in _scenario_map_previews(row)] == [first, second]


def test_old_candidate_preview_remains_readable_as_scenario_one():
    preview = {"base_degree": 1, "source": {"values": [1]}, "output": {"values": [1]}}
    previews = _scenario_map_previews({"example_map_preview": preview})
    assert len(previews) == 1
    assert previews[0]["scenario_index"] == 0
    assert previews[0]["example_map"] is preview
