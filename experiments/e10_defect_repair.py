from collections import Counter

from ac.classes.theories import is_modified
from ac.discovery.fibre_geometry import contains_repeated_sandwich
from ac.discovery.local_repair import (
    ExtremeGapSwap,
    GapSwapRepair,
    defect_measure,
    modified_defect,
    repair_modified_defects,
)
from ac.generate.universes import modified_via_hat

N = 10
swap = ExtremeGapSwap(2, 1)
phi = GapSwapRepair(2, 1)
dual = phi.dual()

source_count = 0
target_count = 0
outputs = set()
structural_bad = 0
defect_size_hist = Counter()
repair_step_hist = Counter()
measure_violations = 0
pattern_violations = 0
inverse_failures = 0
unpaired_or_failed = 0

for x in modified_via_hat(N):
    # Target M(2212): no repeated-sandwich witness with capacities (2,1).
    if not contains_repeated_sandwich(x, 2, 1):
        target_count += 1

    # Source M(2122): no witness with capacities (1,2).
    if contains_repeated_sandwich(x, 1, 2):
        continue

    source_count += 1
    y = swap.apply(x).output

    # E9 pattern transport should already be complete.
    if contains_repeated_sandwich(y, 2, 1):
        pattern_violations += 1

    d = modified_defect(y)
    if not d.empty:
        structural_bad += 1
        defect_size_hist[d.size] += 1

    trace = repair_modified_defects(y)
    repair_step_hist[trace.steps] += 1
    if not trace.terminated or trace.output is None:
        unpaired_or_failed += 1
        continue

    for a, b in zip(trace.states, trace.states[1:]):
        if not defect_measure(b) < defect_measure(a):
            measure_violations += 1
        if contains_repeated_sandwich(b, 2, 1):
            pattern_violations += 1

    z = trace.output
    if not is_modified(z) or contains_repeated_sandwich(z, 2, 1):
        unpaired_or_failed += 1
        continue

    outputs.add(bytes(z.values))

    # Parameter-swapped candidate is the discovered inverse.
    back = dual.apply(z).output
    if back.values != x.values:
        inverse_failures += 1

print("E10 defect calculus and canonical local repair")
print("===============================================")
print("degree:", N)
print("source M(2122):", source_count)
print("target M(2212):", target_count)
print("extreme-gap images with structural defect:", structural_bad)
print("defect-size histogram:", dict(sorted(defect_size_hist.items())))
print("repair-step histogram:", dict(sorted(repair_step_hist.items())))
print("measure violations:", measure_violations)
print("target-pattern violations:", pattern_violations)
print("repair failures:", unpaired_or_failed)
print("dual inverse failures:", inverse_failures)
print("unique final images:", len(outputs))
print("finite bijection:", source_count == target_count == len(outputs) and not (
    measure_violations or pattern_violations or unpaired_or_failed or inverse_failures
))
