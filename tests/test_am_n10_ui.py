from ac.discovery.specification import ClassSpec, DegreeWindow
from ac.discovery.transformation_search import TransformationGrammarSpec
from ac.discovery.transformation_family import TransformationFamilySearchSpec, run_worker_search
from ac.gui.discovery_campaign import build_transformation_family_spec


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
