"""Independent object oracles: no engine imports or production constructors."""
from itertools import combinations, product


def inversion_201_210(length):
    if type(length) is not int or not 0 <= length <= 7:
        raise ValueError('Inversion oracle budget is 0..7')
    for word in product(*(range(i) for i in range(1, length+1))):
        if not any(word[i] > word[j] and word[i] > word[k] and word[j] != word[k]
                   for i,j,k in combinations(range(length),3)):
            yield word


def fishburn_trees(length):
    """Enumerate decreasing labelled shapes, then test tree-node conditions.

    This does not construct a tree from a word, use a word-family recognizer,
    or compare adjacent word entries to find ascent tops.
    """
    if type(length) is not int or not 0 <= length <= 6:
        raise ValueError('Fishburn oracle budget is 0..6')

    def trees(size, bound):
        if size == 0:
            yield None
            return
        for root in range(1, bound+1):
            for left_size in range(size):
                for left in trees(left_size, root-1):
                    for right in trees(size-1-left_size, root):
                        yield (left, root, right)

    def nodes(tree, address=()):
        if tree is None:
            return
        left, label, right = tree
        yield from nodes(left, address+(0,))
        yield address, label, left is not None
        yield from nodes(right, address+(1,))

    for tree in trees(length, length):
        visited = list(nodes(tree))
        labels = {v for _,v,_ in visited}
        if labels != set(range(1, max(labels,default=0)+1)):
            continue
        first = {}
        for address,label,_ in visited:
            first.setdefault(label,address)
        tops = {address for address,_,has_left in visited if has_left}
        if visited:
            tops.add(visited[0][0])
        if tops == set(first.values()):
            yield tree
