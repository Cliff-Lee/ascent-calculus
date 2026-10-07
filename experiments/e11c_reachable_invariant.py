from collections import Counter

from ac.discovery.fibre_geometry import contains_repeated_sandwich
from ac.discovery.local_repair import ExtremeGapSwap, repair_modified_defects
from ac.discovery.proof_extraction import (
    repair_heavy_crossing_values,
    repair_preserves_orientation_profile,
)
from ac.generate.universes import modified_via_hat

print('E11c reachable-state provenance invariant')
print('========================================')
steps = 0
heavy_hist = Counter()
orientation_changes = 0
for x in modified_via_hat(10):
    if contains_repeated_sandwich(x, 1, 2):
        continue
    y = ExtremeGapSwap(2, 1).apply(x).output
    tr = repair_modified_defects(y)
    for state, rule in zip(tr.states, tr.rotations):
        steps += 1
        heavy_hist[len(repair_heavy_crossing_values(state, rule))] += 1
        orientation_changes += int(not repair_preserves_orientation_profile(state, rule))

print('degree-10 reachable repair steps:', steps)
print('heavy-crossing histogram:', dict(sorted(heavy_hist.items())))
print('orientation-profile changes:', orientation_changes)
print()
print('guardrail: no-heavy-crossing is not an intrinsic invariant of arbitrary repairs')
print('safe state: 14323312')
print('after one repair: 13243312')
print('next repair has a multiplicity-3 fibre crossing both blocks and can break 2212 avoidance')
