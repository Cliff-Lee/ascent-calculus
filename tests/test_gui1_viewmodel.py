from ac.gui.viewmodel import (
    bounded_check,
    inspect_word,
    interface_contract,
    research_status,
    trace_gap_swap_repair,
)


def test_gui1_contract_uses_required_research_labels():
    labels = set(interface_contract()["result_labels"])
    assert labels == {"proved", "verified", "open", "counterexample"}


def test_inspector_explains_modified_example():
    vm = inspect_word("133122")
    assert vm["is_modified"]
    assert vm["first_positions"] == [1, 2, 5]
    assert vm["ascent_tops"] == [1, 2, 5]
    assert vm["defect"]["size"] == 0
    assert all(row["reasons"] for row in vm["positions"])


def test_learning_classifications_use_the_python_definitions():
    ordinary_modified = inspect_word("1, 2, 1, 3, 2")
    assert ordinary_modified["is_ascent_sequence"]
    assert ordinary_modified["is_modified"]
    assert not ordinary_modified["is_revised"]
    revised = inspect_word("2, 1, 2")
    assert revised["is_revised"]
    assert not revised["is_ascent_sequence"]
    assert not revised["is_modified"]


def test_e10_one_step_trace_is_engine_backed():
    vm = trace_gap_swap_repair("12321432")
    assert vm["gap_swap"]["output"]["inspection"]["word"] == "12143232"
    assert len(vm["repair"]["steps"]) == 1
    step = vm["repair"]["steps"][0]
    assert step["before"]["inspection"]["word"] == "12143232"
    assert step["after"]["inspection"]["word"] == "12132432"
    assert step["potential_after"] < step["potential_before"]
    assert step["heavy_crossing_values"] == []
    assert step["certificate"]["ascent_top_ids_exchange_exactly"]


def test_guardrail_trace_preserves_open_provenance_message():
    status = research_status()
    guardrail = next(c for c in status["claims"] if c["id"] == "generic-repair-warning")
    assert guardrail["label"] == "counterexample"
    assert guardrail["witness"] == "14323312"
    vm = trace_gap_swap_repair("14323312")
    assert vm["repair"]["steps"][0]["after"]["inspection"]["word"] == "13243312"


def test_research_dashboard_distinguishes_current_alternating_candidate_from_legacy_failure():
    status = research_status()
    assert status["overall"]["label"] == "open"
    assert "verified through n=11" in status["overall"]["detail"]
    first_repair = next(c for c in status["claims"] if c["id"] == "reachable-fibre-shielding")
    assert first_repair["label"] == "counterexample"
    assert first_repair["witness"] == "12321443542"
    map_failure = next(c for c in status["claims"] if c["id"] == "bijection-candidate-n11")
    assert map_failure["label"] == "counterexample"
    assert "not the alternating candidate" in map_failure["detail"]
    finite = next(c for c in status["claims"] if c["id"] == "finite-bijection")
    assert finite["label"] == "verified"
    assert finite["verified_through"] == 10
    current = next(c for c in status["claims"] if c["id"] == "n11-audit")
    assert current["label"] == "verified"
    assert current["verified_through"] == 11
    assert "1,248,595" in current["detail"]


def test_bounded_check_never_returns_proved():
    vm = bounded_check("m2122", "m2212", "repair21", 7)
    assert vm["label"] == "verified"
    assert vm["completed_through"] == 7
    assert vm["finite_only"] is True
    assert "never a proof" in vm["notice"]


def test_raw_gap_swap_exposes_structural_counterexample_by_degree_8():
    vm = bounded_check("m2122", "m2212", "gap21", 8)
    assert vm["label"] == "counterexample"
    assert vm["first_failure"]["n"] == 8
    assert vm["first_failure"]["kind"] == "outside target"
