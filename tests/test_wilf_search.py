from ac.discovery.wilf import cayley_patterns, search_wilf_matches


def test_cayley_pattern_catalogue_has_expected_sizes():
    assert len(cayley_patterns(2)) == 3
    assert len(cayley_patterns(3)) == 13
    assert len(cayley_patterns(4)) == 75


def test_shifted_scan_finds_modified_revised_111_match():
    report = search_wilf_matches(
        "modified",
        "revised",
        pattern_length=3,
        start=1,
        stop=5,
        offsets=(2,),
    )

    row = next(
        candidate for candidate in report["shown"]
        if candidate["left_pattern"] == [1, 1, 1]
        and candidate["right_pattern"] == [1, 1, 1]
    )
    assert row["all_match"]
    assert row["start"] == 1
    assert row["stop"] == 5
    assert [item["left_count"] for item in row["counts"]] == [1, 2, 4, 10, 29]
    assert [item["right_count"] for item in row["counts"]] == [1, 2, 4, 10, 29]


def test_same_family_scan_omits_self_comparisons_and_limits_results():
    report = search_wilf_matches(
        "ordinary",
        "ordinary",
        pattern_length=3,
        start=1,
        stop=5,
        offsets=(0,),
        keep=7,
    )
    assert len(report["shown"]) <= 7
    assert all(row["left_pattern"] != row["right_pattern"] for row in report["shown"])


def test_scan_rejects_invalid_pattern_length_and_out_of_range_shift():
    try:
        cayley_patterns(5)
    except ValueError as exc:
        assert "between 2 and 4" in str(exc)
    else:
        raise AssertionError("unsupported pattern length should be rejected")

    try:
        search_wilf_matches("ordinary", "revised", offsets=(8,))
    except ValueError as exc:
        assert "between -5 and +5" in str(exc)
    else:
        raise AssertionError("unsupported degree shift should be rejected")
