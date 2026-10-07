from ac import (
    Avoid, Modified, First, Last, AscTop, AscBottom, DescTop, DescBottom,
    RunStart, RunEnd, Repeat, RawAscTop, RawAscBottom, RawDescTop, RawDescBottom,
    R, C, Hat, HatInv, Compress, SweepLift, FibreGapPack,
    synthesize_bijections, evaluate_bijection_candidate, diagnose_candidate, analyze_finite_map,
)
from ac.generate.universes import modified_via_hat

source = Modified() & Avoid("2122")
target = Modified() & Avoid("2212")

selectors = (
    First(), Last(), AscTop(), AscBottom(), DescTop(), DescBottom(),
    RunStart(), RunEnd(), Repeat(), RawAscTop(), RawAscBottom(),
    RawDescTop(), RawDescBottom(),
)
atoms = [C(), Hat(), HatInv(), Compress()]
for selector in selectors:
    for inverse in (False, True):
        for direction in ("ltr", "rtl"):
            atoms.append(SweepLift(selector, inverse=inverse, direction=direction))

print("E8 bounded transformation synthesis")
print("===================================")
print()

# Search only mathematically meaningful symbolic programs, seeded by reversal,
# because E7 proved that reversal already transports 2122 to 2212 exactly.
report = synthesize_bijections(
    source,
    target,
    universe=modified_via_hat,
    atoms=atoms,
    max_cost=5,
    through=6,
    seed=R(),
    max_steps=2,
    keep=10,
)
print("reverse-seeded grammar search")
print("candidate programs:", report.candidates_tested)
print("exact through n=6:", len(report.exact))
print("best verified-through degrees:", [ev.verified_through for ev in report.ranked[:10]])
print()

# Diagnose reversal itself: pattern transport is perfect, structural repair is not.
rdiag = diagnose_candidate(
    R(), source, target, universe=modified_via_hat, n=6,
    target_pattern=Avoid("2212"),
)
print("reversal at n=6")
print("source size:", rdiag.source_count)
print("2212-avoidance fraction:", f"{rdiag.target_pattern_fraction:.3f}")
print("full target fraction:", f"{rdiag.target_fraction:.3f}")
print("injectivity fraction:", f"{rdiag.injectivity_fraction:.3f}")
print("mean modified defect |First Δ AscTop|:", f"{rdiag.mean_modified_defect:.3f}")
print()

# E7's fibre-gap theorem suggests a generic capacity-shift schema.  Packing
# internal copies right is not declared a bijection; synthesis must test it.
capacity = FibreGapPack(2, 1, side="right")
ev = evaluate_bijection_candidate(
    capacity, source, target, universe=modified_via_hat, through=7
)
print("fibre-gap capacity-shift candidate")
print("verified through:", ev.verified_through)
print("first failure:", ev.failure.kind.value if ev.failure else None)
if ev.failure:
    print("failure n:", ev.failure.n)
    print("source witness:", ev.failure.source.values if ev.failure.source else None)
    print("output witness:", ev.failure.output.values if ev.failure.output else None)
    print("detail:", ev.failure.detail)
print()

# The unique n=6 class difference is repaired by this candidate.
from ac import ChainWord
x = ChainWord.of([1, 2, 2, 1, 3, 2])
print("n=6 exceptional source:", x.values)
print("capacity-shift image:", capacity.apply(x).output.values)
print()

map7 = analyze_finite_map(
    capacity, source, target, universe=modified_via_hat, n=7
)
print("capacity-shift finite map at n=7")
print("collisions:", len(map7.collisions))
for out, pre in map7.collisions:
    print("  output", out.values, "<-", [x.values for x in pre])
print("missing targets:", [x.values for x in map7.missing_targets])
