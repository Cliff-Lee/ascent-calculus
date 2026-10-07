from ac import (
    Modified,
    Revised,
    Avoid,
    AvoidConstant,
    SameSet,
    First,
    AscTop,
    AscBottom,
    Repeat,
    RunStart,
    Positions,
    Occ,
    PVar,
    ForAll,
    Iff,
    FirstAt,
    OccAt,
    ModifiedFormula,
    AvoidConstantFormula,
    ContainsPatternFormula,
    AvoidPatternFormula,
    smallest_countermodel,
    solve_formula,
    solve_predicate,
    ModelStatus,
    mine_selector_laws,
    verify_on,
    claim_from_verification,
)
from ac.generate.universes import cayley_words


def line(title):
    print(f"\n== {title} ==")


line("E6 finite-logic calibration")
for n in range(1, 7):
    m_old = sum(1 for x in cayley_words(n) if Modified().holds(x))
    m_fo = sum(1 for x in cayley_words(n) if ModifiedFormula().holds(x))
    r_old = sum(1 for x in cayley_words(n) if Revised().holds(x))
    print(f"n={n}: modified old/FO={m_old}/{m_fo}; revised={r_old}")

line("Direct model search for the 2122/2212 class difference")
target = ModifiedFormula() & ContainsPatternFormula("2122") & AvoidPatternFormula("2212")
model = solve_formula(target, n=6, height=3, backend="finite")
print("status:", model.status.value)
print("model:", model.model)
print("finite candidates tested at (n=6,h=3):", model.tested)

line("Smallest logical countermodel: Occ(2)=Repeat on Modified")
i = PVar("i")
occ2_repeat = ForAll(i, Iff(OccAt(i, 2), ~FirstAt(i)))
bad = smallest_countermodel(
    occ2_repeat,
    assumptions=ModifiedFormula(),
    through=5,
    backend="finite",
)
print("countermodel:", bad.result.model if bad.found else None)
print("length/height:", (bad.result.n, bad.result.height) if bad.found else None)

repaired = smallest_countermodel(
    occ2_repeat,
    assumptions=ModifiedFormula() & AvoidConstantFormula(3),
    through=6,
    backend="finite",
)
print("with 111-avoidance countermodel through n=6:", repaired.result.model if repaired.found else None)

line("Existing AC predicate DSL -> finite logic -> solver")
dsl_target = Modified() & ~Avoid("2122") & Avoid("2212")
dsl_model = solve_predicate(dsl_target, n=6, height=3, backend="finite")
print("DSL model:", dsl_model.model)

line("Automatic structural-law mining")
pool = (First(), AscTop(), AscBottom(), Repeat(), RunStart() - Positions([1]))
for name, theory in (("Modified", Modified()), ("Revised", Revised())):
    print(name)
    laws = mine_selector_laws(
        pool,
        universe=cayley_words,
        through=6,
        hypothesis=theory,
        relations=("eq",),
    )
    for law in laws:
        print("  ", law.left, "=", law.right)

line("Claim provenance")
law = SameSet(Occ(2), Repeat())
res = verify_on(
    law,
    universe=cayley_words,
    through=6,
    hypothesis=Modified() & AvoidConstant(3),
)
claim = claim_from_verification("modified-111-occ2", law, res)
print("status:", claim.status.value)
print("verified through:", claim.verified_through)
print("evidence:", claim.evidence)

line("Optional Z3 backend")
z3_try = solve_formula(ModifiedFormula(), n=4, height=3, backend="z3")
print("status:", z3_try.status.value)
if z3_try.detail:
    print(z3_try.detail)
