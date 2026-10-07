from collections import Counter

from ac.discovery.fibre_geometry import contains_repeated_sandwich
from ac.discovery.local_repair import swap_fibre_gaps
from ac.discovery.proof_extraction import (
    ExtremeOrientation, fibre_orientation, is_extreme_oriented,
    right_oriented, left_oriented, maximum_extreme_normal_form,
    extreme_gap_proof_trace_2122_to_2212,
)
from ac.generate.universes import cayley_words, modified_via_hat

print('E11a orientation calculus')
print('========================')
semantic_checked = 0
for n in range(1, 8):
    for x in cayley_words(n):
        semantic_checked += 1
        assert right_oriented(x) == (not contains_repeated_sandwich(x, 1, 2))
        assert left_oriented(x) == (not contains_repeated_sandwich(x, 2, 1))
        for v in range(1, x.height + 1):
            if x.fibre(v):
                assert maximum_extreme_normal_form(x, v) == (
                    fibre_orientation(x, v) is not ExtremeOrientation.MIXED
                )
print('orientation/pattern semantics checked Cayley words:', semantic_checked)

oriented_words = closure_swaps = closure_failures = 0
for n in range(1, 8):
    for x in cayley_words(n):
        if not is_extreme_oriented(x):
            continue
        oriented_words += 1
        for v in range(1, x.height + 1):
            m = len(x.fibre(v))
            if m < 3:
                continue
            closure_swaps += 1
            y = swap_fibre_gaps(x, v, 1, m - 1).output
            closure_failures += int(not is_extreme_oriented(y))
print('extreme-oriented Cayley words through n=7:', oriented_words)
print('extreme-gap closure swaps checked:', closure_swaps)
print('orientation-closure failures:', closure_failures)

gap_steps = 0
trace_failures = Counter()
pivot_hist = Counter()
for n in range(1, 10):
    for x in modified_via_hat(n):
        if contains_repeated_sandwich(x, 1, 2):
            continue
        tr = extreme_gap_proof_trace_2122_to_2212(x)
        for label, ok in (
            ('source orientation', tr.source_right_oriented),
            ('target orientation', tr.output_left_oriented),
            ('pivot monotonicity', tr.strictly_increasing_pivots),
            ('target pattern', tr.pattern_target_clean),
        ):
            if not ok:
                trace_failures[label] += 1
        for step in tr.steps:
            gap_steps += 1
            pivot_hist[step.pivot] += 1
            for label, ok in (
                ('lower projection', step.lower_projection_preserved),
                ('lower orientation', step.lower_orientations_preserved),
                ('orientation closure', step.orientation_closed),
                ('processed prefix', step.smaller_target_clean),
            ):
                if not ok:
                    trace_failures[label] += 1
print('actual gap-swap steps through modified n=9:', gap_steps)
print('pivot histogram:', dict(sorted(pivot_hist.items())))
print('gap-trace failures:', dict(trace_failures))
