from ac.generate.universes import modified_sequences


def test_modified_111_block_law_small():
    for n in range(1, 7):
        for x in modified_sequences(n):
            if not x.avoids_constant_pattern(3):
                continue
            repeats = set(range(1, n + 1)) - set(x.first_positions)
            later_run_starts = set(x.run_starts) - {1}
            assert repeats == later_run_starts
            assert later_run_starts == set(x.occurrence_positions(2))
