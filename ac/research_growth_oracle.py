"""Independent inversion-word and edge oracle; no production imports."""
from itertools import combinations, product


def words(patterns, degree):
    if type(degree) is not int or not 0 <= degree <= 7:
        raise ValueError('Oracle degree budget is 0..7')
    for word in product(*(range(i) for i in range(1,degree+1))):
        forbidden = False
        for pattern in patterns:
            for positions in combinations(range(degree),len(pattern)):
                chosen = tuple(word[i] for i in positions)
                if all((chosen[i] < chosen[j]) == (pattern[i] < pattern[j]) and
                       (chosen[i] == chosen[j]) == (pattern[i] == pattern[j])
                       for i in range(len(pattern)) for j in range(len(pattern))):
                    forbidden = True
                    break
            if forbidden:
                break
        if not forbidden:
            yield word


def parent(word, side):
    if not word or side not in ('left','right'):
        raise ValueError('Nonempty word and supported growth side required')
    if side == 'right':
        return word[:-1]
    # Derive predecessor directly from target: no production subset choices.
    return tuple(max(0,v-1) for v in word[1:])
