"""Reference parallel-specification experiment for the PP05 Fibonacci class.

One/two maximum copies correspond recursively to a final tile of size one/two.
Only the three structural base objects are paired explicitly. No target-set
enumeration or matching table is consulted by either map.
"""

from ac.research_resources import research_root, source_bytes
from functools import lru_cache
from itertools import product
from pathlib import Path

from ac.research_math import integer
from ac.research_references import load_references
from ac.research_specifications import InsertionRule, RecursiveSpecification


@lru_cache(maxsize=1)
def reference_specification():
    root=research_root()/'docs/research/pp03'
    statement=next(s for s in load_references(root/'reference_corpus_v1.json',root/'source_reviews_v1.json') if s.id=='PP129-P6')
    return RecursiveSpecification(statement.class_spec,((0,),(0,0),(0,1)),
        (InsertionRule('one-max','after_first_max',1,2),InsertionRule('two-max','after_first_max',2,1)),
        (statement.class_spec.citation_id,),statement.review_sha256,statement.source_theorem_id)


def tile_member(tiles):
    return (type(tiles) is tuple and bool(tiles) and len(tiles)<=6 and
            all(type(v) is int and v in (1,2) for v in tiles) and 1<=sum(tiles)<=6)


def to_tiles(word):
    spec=reference_specification()
    if type(word) is not tuple or not 1<=len(word)<=6 or not spec.class_spec.holds(word):
        raise ValueError('Word outside the declared Fibonacci class/scope')
    bases={(0,):(1,), (0,0):(2,), (0,1):(1,1)}
    if word in bases:
        return bases[word]
    decompositions=[(rule,rule.decompose(word)) for rule in spec.rules]
    eligible=[(rule,parent) for rule,parent in decompositions if parent is not None]
    if len(eligible)!=1:
        raise ValueError('Recursive source branch is missing or ambiguous')
    rule,parent=eligible[0]
    return to_tiles(parent)+(rule.copies,)


def from_tiles(tiles):
    if not tile_member(tiles):
        raise ValueError('Nonempty one/two tile word of total size 1..6 required')
    bases={(1,):(0,), (2,):(0,0), (1,1):(0,1)}
    if tiles in bases:
        return bases[tiles]
    parent=from_tiles(tiles[:-1])
    rule=next(r for r in reference_specification().rules if r.copies==tiles[-1])
    return rule.construct(parent)


def tile_levels(through):
    """Target specification interpreter, separate from the inverse map."""
    integer(through,1,6)
    levels={0:[]}
    for n in range(1,through+1):
        current=[t for t in ((1,),(2,),(1,1)) if sum(t)==n]
        if n>=3:
            current += [t+(1,) for t in levels[n-1]]
            current += [t+(2,) for t in levels[n-2]]
        levels[n]=current
    return levels


def independent_tiles(size):
    """Full binary-product oracle; no recursive production or source map."""
    integer(size,1,6)
    for length in range(1,size+1):
        for tiles in product((1,2),repeat=length):
            if sum(tiles)==size:
                yield tiles


def derivation(word):
    tiles=to_tiles(word)
    rows=[]
    current=word
    while len(current)>2:
        rule,parent=next((r,r.decompose(current)) for r in reference_specification().rules if r.decompose(current) is not None)
        rows.append({'source':current,'source_parent':parent,'source_degree':len(current),
                     'branch':rule.id,'tile_size':rule.copies,'target':to_tiles(current)})
        current=parent
    return {'source':word,'target':tiles,'base_source':current,'base_target':to_tiles(current),
            'steps':rows,'reverse_composition':from_tiles(tiles),
            'parallel_equations':{'source':'A=t+2t^2+t(A-t)+t^2*A',
                                  'target':'T=t+2t^2+t(T-t)+t^2*T'},
            'proof_status':'unproved'}
