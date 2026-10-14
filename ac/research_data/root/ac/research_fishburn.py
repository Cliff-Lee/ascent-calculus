"""Small reference implementation of the Fishburn-tree in-order transport.

Tree nodes are immutable (left, positive label, right) triples; None is empty.
No synthesis or changes to existing word transformations are performed here.
"""
from ac.research_math import integer


def inorder(tree):
    if tree is None:
        return ()
    left, label, right = tree
    return inorder(left) + (label,) + inorder(right)


def max_tree(word):
    """Leftmost-maximum recursive construction, Section 2 of Fishburn trees."""
    if type(word) is not tuple or len(word) > 6:
        raise ValueError('Bounded positive endofunction tuple required')
    for v in word:
        integer(v, 1, len(word))

    def build(values):
        if not values:
            return None
        index = values.index(max(values))
        return (build(values[:index]), values[index], build(values[index+1:]))
    return build(word)


def tree_statistics(tree):
    """Statistics from node topology and in-order identity, not word ascents."""
    nodes = []

    def visit(node):
        if node is None:
            return
        left, label, right = node
        visit(left)
        nodes.append((label, left is not None))
        visit(right)
    visit(tree)
    seen = set()
    first, tops = [], []
    for i, (label, has_left) in enumerate(nodes, 1):
        if label not in seen:
            first.append(i)
        seen.add(label)
        if i == 1 or has_left:
            tops.append(i)
    return {'first_positions': first, 'ascent_top_positions': tops,
            'maximum': max(seen, default=0)}


def fishburn_coefficients(max_degree):
    """Truncated sum of products prod_{k=1}^m (1-(1-t)^k)."""
    from math import comb
    integer(max_degree, 0, 100)
    total = [1] + [0]*max_degree
    term = total.copy()
    for k in range(1, max_degree+1):
        factor = [0] + [(-1)**(j+1)*comb(k,j) for j in range(1,k+1)]
        term = [sum(term[i-j]*factor[j] for j in range(1,min(i,k)+1))
                for i in range(max_degree+1)]
        total = [a+b for a,b in zip(total,term)]
    return tuple(total)
