import json

from ac.gui.map_search import exportable_map_report, run_map_search


def _paper_spec(stop=3):
    rule = [{"mode": "avoid", "pattern": [1, 1, 1]}]
    return {
        "question": "compare",
        "start": 1,
        "stop": stop,
        "statistic": "none",
        "left": {"family": "modified", "degree_offset": 0, "rules": rule},
        "right": {"family": "revised", "degree_offset": 2, "rules": rule},
    }


def test_search_generates_and_reports_a_block_recipe_for_the_paper_map():
    report = run_map_search(_paper_spec(), max_cost=4, max_steps=1, keep=20)

    generated = [
        candidate for candidate in report["exact"]
        if candidate["name"].startswith("Blocks · increasing runs · parent: first prior block · safe up")
    ]
    assert generated
    assert generated[0]["verified_through"] == 3
    assert report["degree_shift"] == 2
    assert report["search_grammar"]["generated_block_recipes"] == 108
    assert "memory at" not in generated[0]["expression"]
    exported = exportable_map_report(report)
    assert "_transform" not in exported["exact"][0]
    assert json.loads(json.dumps(exported))["specification"] == _paper_spec()


def test_two_step_search_is_bounded_and_includes_compositions():
    spec = _paper_spec(stop=7)
    spec["left"]["family"] = "ordinary"
    spec["right"]["family"] = "ordinary"
    try:
        run_map_search(spec, max_cost=5, max_steps=2)
    except ValueError as exc:
        assert "degree 6" in str(exc)
    else:
        raise AssertionError("two-step map search must enforce its finite testing bound")


def test_search_includes_the_paper_map_inverse_for_the_reverse_offset():
    rule = [{"mode": "avoid", "pattern": [1, 1, 1]}]
    spec = {
        "question": "compare", "start": 1, "stop": 3, "statistic": "none",
        "left": {"family": "revised", "degree_offset": 2, "rules": rule},
        "right": {"family": "modified", "degree_offset": 0, "rules": rule},
    }
    report = run_map_search(spec, max_cost=4, max_steps=1, keep=20)

    assert report["degree_shift"] == -2
    assert report["exact"]
    assert any(candidate["name"] == "Inverse paper block map · R111 → M111 · n−2" for candidate in report["exact"])


def test_search_generates_single_maximum_recipes_for_a_plus_one_shift():
    rule = [{"mode": "avoid", "pattern": [1, 1, 1]}]
    spec = {
        "question": "compare", "start": 1, "stop": 3, "statistic": "none",
        "left": {"family": "modified", "degree_offset": 0, "rules": rule},
        "right": {"family": "revised", "degree_offset": 1, "rules": rule},
    }
    report = run_map_search(spec, max_cost=4, max_steps=1, keep=5)

    assert report["degree_shift"] == 1
    assert report["search_grammar"]["generated_block_recipes"] == 108
    assert report["shift_compatible_programs"] >= 108
    assert any("insert one new max" in item["name"] for item in report["ranked"])
