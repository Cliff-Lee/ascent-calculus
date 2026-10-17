#!/usr/bin/env python3
"""Finite experiment on open ordinary-ascent-sequence avoidance enumerations.

Liu--Kitaev--Zhang (accepted 2026) leave enumerations of 0120, 0121,
and their joint avoidance open. The public Ascent Calculus core uses
positive Cayley labels, so paper patterns 0120/0121 become 1231/1232.
This program counts examples: it does not find a closed formula or proof.
"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path
from ac.generate.universes import ascent_sequences
from ac.patterns import Pattern

EXPECTED_AMBIENT = {
    1: 1, 2: 2, 3: 5, 4: 15, 5: 53, 6: 217,
    7: 1014, 8: 5335, 9: 31240, 10: 201608, 11: 1422074,
}


def run(through: int):
    p = Pattern('1231').compile()  # 0-based 0120
    q = Pattern('1232').compile()  # 0-based 0121
    for n in range(1, through + 1):
        ambient = first = second = both = 0
        for word in ascent_sequences(n):
            ambient += 1
            avoids_p = p.avoids(word)
            avoids_q = q.avoids(word)
            first += avoids_p
            second += avoids_q
            both += avoids_p and avoids_q
        assert ambient == EXPECTED_AMBIENT[n], (
            f'Unexpected Fishburn population at n={n}: {ambient}'
        )
        yield (n, ambient, first, second, both)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--through', type=int, default=8, choices=range(1, 12))
    parser.add_argument('--csv', type=Path, help='Optional CSV output; existing file will not be overwritten')
    args = parser.parse_args()
    columns = ['n', 'all_ascent', 'avoid_0120', 'avoid_0121', 'avoid_both']
    if args.csv:
        with args.csv.open('x', newline='', encoding='utf-8') as stream:
            writer = csv.writer(stream)
            writer.writerow(columns)
            for row in run(args.through):
                writer.writerow(row)
                print(*row, sep='\t')
    else:
        print(*columns, sep='\t')
        for row in run(args.through):
            print(*row, sep='\t')
    print('Finite enumeration complete; no all-length theorem established.')


if __name__ == '__main__':
    main()
