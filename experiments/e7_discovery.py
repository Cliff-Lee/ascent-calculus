from __future__ import annotations

from ac import (
    AscTop,
    Avoid,
    AvoidConstant,
    First,
    HypothesisCandidate,
    Modified,
    Occ,
    Positions,
    Repeat,
    RunStart,
    SameSet,
    generate_selector_expressions,
    mine_minimal_hypotheses,
    mine_selector_equivalence_classes,
    rank_discriminating_statistics,
    repeated_sandwich_pattern,
    verify_parameterized_schema,
)
from ac.generate.universes import cayley_words, modified_via_hat


def occurrence_union(r: int):
    selector = Positions([])
    for rank in range(2, r):
        selector = selector | Occ(rank)
    return selector


print("E7 — conjecture mining and theorem-schema discovery")
print()

print("1. Repeated-sandwich fibre-gap schema")
for a, b in ((1, 1), (1, 2), (2, 1), (2, 2)):
    print(f"  (a,b)=({a},{b}) -> pattern {repeated_sandwich_pattern(a,b)}")
print("  structural law: 2^a 1 2^b occurs iff a lower-valued entry lies")
print("  in a repeated-value gap with >=a copies to its left and >=b to its right.")
print("  exhaustive test coverage: all Cayley words through n=6 (unit suite).")
print()

print("2. Minimal-hypothesis search for Occ(2)=Repeat on modified sequences")
repairs = mine_minimal_hypotheses(
    SameSet(Occ(2), Repeat()),
    base=Modified(),
    candidates=(
        HypothesisCandidate("Av(11)", AvoidConstant(2)),
        HypothesisCandidate("Av(111)", AvoidConstant(3)),
        HypothesisCandidate("Av(1111)", AvoidConstant(4)),
    ),
    universe=cayley_words,
    through=6,
    max_terms=1,
)
for result in repairs:
    print(f"  {result.names}: support={result.finite_support}, verified={result.verification.ok}")
print("  ranked weakest empirical repair: Av(111)")
print()

print("3. Parameterized 1^r occurrence/run-start schema")
schema = verify_parameterized_schema(
    "M + Av(1^r): RunStart-{1} = Occ(2) union ... union Occ(r-1)",
    range(2, 7),
    law_factory=lambda r: SameSet(RunStart() - Positions([1]), occurrence_union(r)),
    hypothesis_factory=lambda r: Modified() & AvoidConstant(r),
    universe=cayley_words,
    through=7,
)
for instance in schema.instances:
    print(
        f"  r={instance.parameter}: ok={instance.ok}, "
        f"matched={instance.verification.hypotheses_matched}"
    )
print()

print("4. Semantic selector normal forms for Modified")
expressions = generate_selector_expressions(
    (First(), AscTop(), Repeat(), RunStart(), Positions([1])),
    max_cost=3,
    operations=("difference",),
)
classes = mine_selector_equivalence_classes(
    expressions,
    universe=cayley_words,
    through=6,
    hypothesis=Modified(),
)
for cls in classes:
    members = (cls.representative, *cls.aliases)
    if Repeat() in members and RunStart() - Positions([1]) in members:
        print("  Repeat semantic class contains RunStart-{1}")
    if First() in members and AscTop() in members:
        print("  First semantic class contains AscTop")
print()

print("5. Discriminating invariants for M(2122) vs M(2212)")
ranked = rank_discriminating_statistics(
    Modified() & Avoid("2122"),
    Modified() & Avoid("2212"),
    universe=modified_via_hat,
    through=9,
    statistics=(
        "height",
        "ascents",
        "multiplicity_partition",
        "first_positions",
        "last_positions",
        "lower_gap_profile",
        "lower_gap_count_profile",
        "fibre_span_profile",
    ),
)
for row in ranked:
    where = "none through n=9" if row.first_mismatch_n is None else f"n={row.first_mismatch_n}"
    print(f"  {row.name:26s} first mismatch: {where}")
