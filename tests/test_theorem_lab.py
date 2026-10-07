from ac import (
    Modified,
    AvoidConstant,
    SameSet,
    Repeat,
    RunStart,
    Occ,
    Positions,
    verify_on,
    VerificationStatus,
)
from ac.generate.universes import cayley_words


def test_exhaustive_lab_recovers_modified_run_start_law():
    law = SameSet(Repeat(), RunStart() - Positions([1]))
    result = verify_on(law, universe=cayley_words, through=6, hypothesis=Modified())
    assert result.status is VerificationStatus.VERIFIED
    assert result.hypotheses_matched == 1 + 2 + 5 + 15 + 53 + 217


def test_exhaustive_lab_finds_smallest_counterexample_to_occ2_equals_repeat():
    law = SameSet(Occ(2), Repeat())
    result = verify_on(law, universe=cayley_words, through=5, hypothesis=Modified())
    assert result.status is VerificationStatus.COUNTEREXAMPLE
    assert result.counterexample_n == 3
    assert result.counterexample.values == (1, 1, 1)


def test_111_restores_occ2_equals_repeat():
    law = SameSet(Occ(2), Repeat())
    cls = Modified() & AvoidConstant(3)
    result = verify_on(law, universe=cayley_words, through=6, hypothesis=cls)
    assert result.status is VerificationStatus.VERIFIED
