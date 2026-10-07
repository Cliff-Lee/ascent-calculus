import pytest

from ac import (
    ChainWord,
    Position,
    PositionCut,
    ValueLevel,
    ValueCut,
    IntervalScope,
    First,
    Last,
    Occ,
    Repeat,
    AscTop,
    AscBottom,
    RunStart,
    RunEnd,
    Before,
    After,
    EmptyValues,
    Multiplicity,
    BeforeValue,
    indices,
    snapshot,
    insert_at_selected_cuts,
    reverse,
    prefix_lift,
)


def test_typed_atomic_objects_validate():
    assert int(Position(3)) == 3
    assert int(PositionCut(0)) == 0
    assert int(ValueLevel(2)) == 2
    assert int(ValueCut(0)) == 0
    with pytest.raises(ValueError):
        Position(0)
    with pytest.raises(ValueError):
        ValueLevel(0)


def test_selector_semantics_on_133122():
    x = ChainWord.of([1, 3, 3, 1, 2, 2])
    assert indices(First().evaluate(x)) == frozenset({1, 2, 5})
    assert indices(Last().evaluate(x)) == frozenset({3, 4, 6})
    assert indices(Occ(2).evaluate(x)) == frozenset({3, 4, 6})
    assert indices(Repeat().evaluate(x)) == frozenset({3, 4, 6})
    assert indices(AscTop().evaluate(x)) == frozenset({1, 2, 5})
    assert indices(AscBottom().evaluate(x)) == frozenset({1, 4})
    assert indices(RunStart().evaluate(x)) == frozenset({1, 3, 4, 6})
    assert indices(RunEnd().evaluate(x)) == frozenset({2, 3, 5, 6})


def test_boolean_selector_algebra_is_typed():
    x = ChainWord.of([1, 3, 3, 1, 2, 2])
    expr = Repeat() & RunStart()
    assert indices(expr.evaluate(x)) == frozenset({3, 4, 6})
    assert indices((~First()).evaluate(x)) == frozenset({3, 4, 6})
    assert indices((First() | Last()).evaluate(x)) == frozenset({1, 2, 3, 4, 5, 6})
    with pytest.raises(TypeError):
        _ = First() | EmptyValues()


def test_scopes_are_contiguous_subword_semantics():
    x = ChainWord.of([1, 3, 3, 1, 2, 2])
    scope = IntervalScope(3, 6)  # 3,1,2,2
    assert indices(First().evaluate(x, scope=scope)) == frozenset({3, 4, 5})
    assert indices(Last().evaluate(x, scope=scope)) == frozenset({3, 4, 6})
    assert indices(AscTop().evaluate(x, scope=scope)) == frozenset({3, 5})
    assert indices(RunStart().evaluate(x, scope=scope)) == frozenset({3, 4, 6})


def test_position_and_value_cut_conversions():
    x = ChainWord.of([1, 3, 3, 1, 2, 2])
    assert indices(Before(RunStart()).evaluate(x)) == frozenset({0, 2, 3, 5})
    assert indices(After(RunEnd()).evaluate(x)) == frozenset({2, 3, 5, 6})

    y = ChainWord.of([1, 2, 1, 2, 4], height=4)
    assert indices(EmptyValues().evaluate(y)) == frozenset({3})
    assert indices(Multiplicity(2).evaluate(y)) == frozenset({1, 2})
    assert indices(BeforeValue(EmptyValues()).evaluate(y)) == frozenset({2})


def test_snapshot_records_stable_source_occurrence_ids():
    x = ChainWord.of([1, 3, 3, 1, 2, 2])
    snap = snapshot(x, First())
    assert snap.position_ids == (1, 2, 5)

    r = reverse(x).output
    assert r.position_ids == (6, 5, 4, 3, 2, 1)
    assert r.position_of_id(5) == 2

    lifted = prefix_lift(r, 3).output
    assert lifted.position_ids == r.position_ids


def test_snapshot_simultaneous_insertion_before_run_starts():
    x = ChainWord.of([1, 3, 3, 1, 2, 2])
    result = insert_at_selected_cuts(x, Before(RunStart()), value=1)
    y = result.output
    assert y.values == (1, 1, 3, 1, 3, 1, 1, 2, 1, 2)
    assert result.created_positions == (1, 4, 6, 9)
    assert result.created_position_ids == (-1, -2, -3, -4)
    # Original occurrences retain identity despite index shifts.
    assert tuple(y.position_of_id(pid) for pid in x.position_ids) == result.position_map
