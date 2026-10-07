import pytest

from ac import (
    ChainWord,
    PVar,
    P,
    At,
    Eq,
    Lt,
    Iff,
    ForAll,
    FirstAt,
    OccAt,
    RunStartAt,
    ModifiedFormula,
    RevisedFormula,
    AscentSequenceFormula,
    AvoidConstantFormula,
    ContainsPatternFormula,
    AvoidPatternFormula,
    FormulaPredicate,
    Modified,
    Revised,
    AscentSequence,
    Avoid,
    AvoidConstant,
    solve_formula,
    find_countermodel,
    smallest_countermodel,
    ModelStatus,
    ClaimStatus,
    ClaimRecord,
    ClaimRegistry,
    First,
    AscTop,
    AscBottom,
    Repeat,
    RunStart,
    Positions,
    mine_selector_laws,
)
from ac.generate.universes import cayley_words, ascent_sequences


def test_finite_logic_quantifier_and_value_access_reference_semantics():
    x = ChainWord.of([1, 3, 3, 1, 2, 2])
    i = PVar("i")
    # Every first occurrence is either position 1 or arrived via an ascent.
    formula = ForAll(
        i,
        FirstAt(i).implies(Eq(i, P(1)) | Lt(At(P(1)), At(i))),
    )
    # This deliberately crude formula is false at position 5 (1 < 2 happens to
    # save it) and serves only as a quantifier/evaluator calibration.
    assert formula.holds(x)


def test_formula_theories_agree_with_existing_recognizers_small_universes():
    mf = FormulaPredicate(ModifiedFormula())
    rf = FormulaPredicate(RevisedFormula())
    for n in range(1, 7):
        for x in cayley_words(n):
            assert mf.holds(x) == Modified().holds(x)
            assert rf.holds(x) == Revised().holds(x)

    af = FormulaPredicate(AscentSequenceFormula())
    for n in range(1, 8):
        for x in ascent_sequences(n):
            assert af.holds(x) == AscentSequence().holds(x)


def test_pattern_formula_agrees_with_pattern_engine():
    contains = FormulaPredicate(ContainsPatternFormula("2122"))
    avoids = FormulaPredicate(AvoidPatternFormula("2122"))
    for n in range(1, 7):
        for x in cayley_words(n):
            assert contains.holds(x) == (not Avoid("2122").holds(x))
            assert avoids.holds(x) == Avoid("2122").holds(x)


def test_constant_pattern_formula_agrees_with_optimized_predicate():
    f = FormulaPredicate(AvoidConstantFormula(3))
    for n in range(1, 7):
        for x in cayley_words(n):
            assert f.holds(x) == AvoidConstant(3).holds(x)


def test_fixed_model_solver_finds_exact_word():
    i = PVar("i")
    formula = ModifiedFormula() & ContainsPatternFormula("2122") & AvoidPatternFormula("2212")
    result = solve_formula(formula, n=6, height=3, backend="finite")
    assert result.status is ModelStatus.SAT
    assert result.model is not None
    assert Modified().holds(result.model)
    assert not Avoid("2122").holds(result.model)
    assert Avoid("2212").holds(result.model)


def test_smallest_countermodel_recovers_111_failure_and_111_repairs_it():
    i = PVar("i")
    occ2_equals_repeat = ForAll(i, Iff(OccAt(i, 2), ~FirstAt(i)))

    bad = smallest_countermodel(
        occ2_equals_repeat,
        assumptions=ModifiedFormula(),
        through=5,
        backend="finite",
    )
    assert bad.found
    assert bad.result.n == 3
    assert bad.result.model.values == (1, 1, 1)

    # Under 111-avoidance there is no countermodel through length 6.
    repaired = smallest_countermodel(
        occ2_equals_repeat,
        assumptions=ModifiedFormula() & AvoidConstantFormula(3),
        through=6,
        backend="finite",
    )
    assert not repaired.found


def test_modified_run_start_law_is_expressible_in_quantified_logic():
    i = PVar("i")
    law = ForAll(
        i,
        Lt(P(1), i).implies(Iff(~FirstAt(i), RunStartAt(i))),
    )
    result = smallest_countermodel(
        law,
        assumptions=ModifiedFormula(),
        through=6,
        backend="finite",
    )
    assert not result.found


def test_explicit_z3_backend_reports_unavailable_cleanly_when_dependency_missing():
    result = solve_formula(ModifiedFormula(), n=3, height=2, backend="z3")
    try:
        import z3  # noqa: F401
    except ModuleNotFoundError:
        assert result.status is ModelStatus.UNAVAILABLE
        assert "z3-solver" in result.detail
    else:
        assert result.status in {ModelStatus.SAT, ModelStatus.UNSAT}


def test_claim_registry_enforces_evidence_statuses():
    registry = ClaimRegistry()
    registry.add(
        ClaimRecord(
            "M-run-start",
            "Modified => Repeat = RunStart-{1}",
            ClaimStatus.PROVED,
            evidence="definition F=AscTop plus RunStart=complement RawAscTop away from boundary",
            dependencies=("M-definition", "run-definition"),
        )
    )
    registry.add(
        ClaimRecord(
            "2122-2212-profile",
            "height profiles agree",
            ClaimStatus.VERIFIED,
            evidence="exhaustive E5 experiment",
            verified_through=9,
        )
    )
    registry.add(
        ClaimRecord(
            "false-general-occ2",
            "Occ(2)=Repeat on all modified sequences",
            ClaimStatus.REFUTED,
            evidence="finite countermodel",
            counterexample=ChainWord.of([1, 1, 1]),
        )
    )
    assert registry.get("M-run-start").status is ClaimStatus.PROVED
    assert len(registry.by_status(ClaimStatus.VERIFIED)) == 1

    with pytest.raises(ValueError):
        ClaimRecord("bad", "claim", ClaimStatus.PROVED)


def test_selector_law_miner_rediscovers_modified_and_revised_structural_laws():
    pool = (
        First(),
        AscTop(),
        AscBottom(),
        Repeat(),
        RunStart() - Positions([1]),
    )
    mlaws = mine_selector_laws(
        pool,
        universe=cayley_words,
        through=6,
        hypothesis=Modified(),
        relations=("eq",),
    )
    assert any({law.left, law.right} == {First(), AscTop()} for law in mlaws)
    assert any({law.left, law.right} == {Repeat(), RunStart() - Positions([1])} for law in mlaws)

    rlaws = mine_selector_laws(
        pool,
        universe=cayley_words,
        through=6,
        hypothesis=Revised(),
        relations=("eq",),
    )
    assert any({law.left, law.right} == {First(), AscBottom()} for law in rlaws)


def test_existing_predicate_dsl_compiles_to_the_same_finite_logic():
    from ac import predicate_to_formula, SameSet

    predicate = Modified() & Avoid("111") & SameSet(Repeat(), RunStart() - Positions([1]))
    formula = predicate_to_formula(predicate)
    for n in range(1, 7):
        for x in cayley_words(n):
            assert formula.holds(x) == predicate.holds(x)


def test_solver_accepts_existing_predicate_dsl_directly():
    from ac import solve_predicate

    target = Modified() & ~Avoid("2122") & Avoid("2212")
    result = solve_predicate(target, n=6, height=3, backend="finite")
    assert result.status is ModelStatus.SAT
    assert result.model.values == (1, 2, 1, 3, 2, 2)


def test_ascent_formula_has_no_false_positives_on_small_chain_words():
    from ac.generate.universes import chain_words

    formula = FormulaPredicate(AscentSequenceFormula())
    for n in range(0, 6):
        for h in range(0 if n == 0 else 1, max(1, n) + 1):
            for x in chain_words(n, h):
                assert formula.holds(x) == AscentSequence().holds(x)


def test_transported_reversed_modified_theory_compiles_back_into_finite_logic():
    from ac import R, transport_predicate, predicate_to_formula

    theory = transport_predicate(Modified(), R())
    formula = predicate_to_formula(theory)
    for n in range(1, 6):
        for x in cayley_words(n):
            assert formula.holds(x) == theory.holds(x)
