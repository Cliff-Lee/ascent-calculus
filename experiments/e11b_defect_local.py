from collections import Counter

from ac.discovery.fibre_geometry import contains_repeated_sandwich
from ac.discovery.local_repair import ExtremeGapSwap, modified_defect, repair_modified_defects
from ac.discovery.proof_extraction import (
    certify_defect_rotation, defect_value_potential, defect_admissibility,
)
from ac.generate.universes import modified_via_hat

print('E11b local defect-rotation proof obligations')
print('===========================================')
repair_steps = 0
cert_failures = Counter()
potential_failures = 0
admissibility_failures = 0
rank_pairs = Counter()
first_change_hist = Counter()
new_defect_hist = Counter()
defective_states = 0

for x in modified_via_hat(10):
    if contains_repeated_sandwich(x, 1, 2):
        continue
    y = ExtremeGapSwap(2, 1).apply(x).output
    if modified_defect(y).empty:
        continue
    tr = repair_modified_defects(y)
    defective_states += len(tr.states) - 1
    for state in tr.states[:-1]:
        if not defect_admissibility(state).ok:
            admissibility_failures += 1
    for state, next_state, rule in zip(tr.states, tr.states[1:], tr.rotations):
        repair_steps += 1
        cert = certify_defect_rotation(state, rule)
        rank_pairs[(cert.first_is_rank1, cert.second_is_rank2, cert.consecutive_in_fibre)] += 1
        first_change_hist[len(cert.first_identity_changes)] += 1
        new_defect_hist[len(cert.newly_created_defect_values)] += 1
        if not cert.local_boundary_lemma_ready:
            for field in (
                'first_is_rank1', 'second_is_rank2', 'consecutive_in_fibre',
                'has_lower_predecessor_before_block', 'block_a_strictly_above_pivot',
                'second_has_lower_predecessor', 'ascent_top_ids_exchange_exactly',
                'first_change_characterization_exact', 'new_defects_strictly_above_pivot',
                'value_potential_decreases',
            ):
                if not getattr(cert, field):
                    cert_failures[field] += 1
        if not defect_value_potential(next_state) < defect_value_potential(state):
            potential_failures += 1

print('defective intermediate states:', defective_states)
print('repair steps:', repair_steps)
print('defect-admissibility failures:', admissibility_failures)
print('rank-pair signatures:', dict(rank_pairs))
print('first-identity-change histogram:', dict(sorted(first_change_hist.items())))
print('new-defect-value histogram:', dict(sorted(new_defect_hist.items())))
print('local-certificate failures:', dict(cert_failures))
print('value-potential failures:', potential_failures)
