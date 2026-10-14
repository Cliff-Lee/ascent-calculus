"""Typed finite generating-tree exploration and published reference replay."""

from ac.research_resources import research_root, source_bytes
from collections import Counter
from dataclasses import asdict, dataclass
from hashlib import sha256
from itertools import combinations, product
import json
from pathlib import Path

from ac.core.word import ChainWord
from ac.research_inversions import InversionClass, testart_coefficients
from ac.research_math import SourcePattern, decode, fields, integer
from ac.research_growth_oracle import words as oracle_words, parent as oracle_parent

REVIEW_SHA256 = '894c82f11fcadfe4658c28c3c23802aab249b18083b60ba253d6d269563746cc'

FEATURES = ('leading_zeros','nonleading_zero_flag','zero_count','published_s',
            'last','maximum','ascents','repeat_count','run_count','first_count')


@dataclass(frozen=True)
class GrowthStrategy:
    class_spec: InversionClass
    side: str

    def __post_init__(self):
        if type(self.class_spec) is not InversionClass or self.side not in ('left','right'):
            raise ValueError('Typed inversion class and left/right strategy required')

    def to_json(self):
        return json.dumps({'schema_version':1,'side':self.side,'patterns':[asdict(p) for p in self.class_spec.avoid]},sort_keys=True,separators=(',',':'))

    @classmethod
    def from_json(cls, raw):
        obj=decode(raw);fields(obj,('schema_version','side','patterns'))
        if type(obj['schema_version']) is not int or obj['schema_version']!=1 or type(obj['patterns']) is not list:
            raise ValueError('Unsupported strategy schema')
        return cls(InversionClass(tuple(SourcePattern.from_dict(p) for p in obj['patterns'])),obj['side'])

    def holds(self, word):
        if type(word) is not tuple or len(word)>7:
            raise ValueError('Bounded inversion tuple required')
        for i,v in enumerate(word):
            integer(v,0,i)
        positive = ChainWord(tuple(v+1 for v in word))
        return not any(p.compile().contains(positive) for p in self.class_spec.avoid)

    def children(self, word):
        if len(word)>6 or not self.holds(word):
            raise ValueError('Parent outside membership/degree budget')
        if self.side == 'right':
            candidates = (word+(v,) for v in range(len(word)+1))
        else:
            zeros = [i for i,v in enumerate(word) if v==0]
            candidates = ((0,)+tuple(v+1 if v>0 or (v==0 and chosen[zeros.index(i)]) else 0
                           for i,v in enumerate(word))
                          for chosen in product((False,True),repeat=len(zeros)))
        return tuple(child for child in candidates if self.holds(child))


@dataclass(frozen=True)
class LabelSchema:
    features: tuple[str, ...]

    def __post_init__(self):
        if (type(self.features) is not tuple or len(self.features)>4 or
                any(type(f) is not str or f not in FEATURES for f in self.features) or
                len(set(self.features))!=len(self.features)):
            raise ValueError('Unique supported statistic features required')

    def state(self, word):
        if type(word) is not tuple or len(word)>7:
            raise ValueError('Bounded inversion tuple required')
        for i,v in enumerate(word):
            integer(v,0,i)
        leading=0
        for v in word:
            if v != 0: break
            leading+=1
        zeros=word.count(0)
        values={'leading_zeros':leading,'nonleading_zero_flag':int(zeros>leading),
                'zero_count':zeros,'published_s':leading+int(zeros>leading),
                'last':word[-1] if word else -1,'maximum':max(word,default=-1),
                'ascents':sum(a<b for a,b in zip(word,word[1:])),
                'repeat_count':len(word)-len(set(word)),
                'run_count':int(bool(word))+sum(a!=b for a,b in zip(word,word[1:])),
                'first_count':len(set(word))}
        return tuple(values[f] for f in self.features)

    def to_json(self):
        return json.dumps(asdict(self),sort_keys=True,separators=(',',':'))

    @classmethod
    def from_json(cls, raw):
        obj=decode(raw);fields(obj,('features',))
        if type(obj['features']) is not list: raise ValueError('Feature array required')
        return cls(tuple(obj['features']))


def explore(strategy, through):
    """Build edges from ALL independent parents, and test reachable coverage."""
    if type(strategy) is not GrowthStrategy:
        raise ValueError('Typed growth strategy required')
    integer(through,1,7)
    patterns=tuple(p.values for p in strategy.class_spec.avoid)
    levels={n:tuple(oracle_words(patterns,n)) for n in range(through+1)}
    edges={}
    reachable={()}
    rows=[]
    for n in range(through):
        target=set(levels[n+1]); source=set(levels[n])
        actual=[];expected=[];orphans=[]
        for word in levels[n]:
            edges[word]=strategy.children(word)
            actual += [(word,c) for c in edges[word]]
        for child in levels[n+1]:
            parent=oracle_parent(child,strategy.side)
            if parent not in source:
                orphans.append({'child':child,'parent':parent})
            else:
                expected.append((parent,child))
        actual_set=set(actual); expected_set=set(expected)
        reachable={child for p in reachable for child in edges[p]}
        missing=target-reachable
        row={'parent_degree':n,'source_count':len(source),'target_count':len(target),
             'reachable_count':len(reachable),'edge_count':len(actual),
             'duplicate_edges':len(actual)-len(actual_set),
             'edges_agree':actual_set==expected_set,
             'missing_reachable':min(missing) if missing else None,
             'orphan':orphans[0] if orphans else None,
             'unexpected_edge':min(actual_set-expected_set) if actual_set-expected_set else None,
             'omitted_edge':min(expected_set-actual_set) if expected_set-actual_set else None}
        rows.append(row)
    passed=all(r['edges_agree'] and r['duplicate_edges']==0 and
               r['missing_reachable'] is None and r['orphan'] is None for r in rows)
    return {'strategy':strategy,'through':through,'levels':levels,'edges':edges,
            'audit':{'side':strategy.side,'through':through,'rows':rows,
                     'status':'finite_verified' if passed else 'refuted','proof_status':'unproved'}}


def infer_labels(exploration, schema, parent_degrees):
    """A label must determine child-state multiplicities, including across sizes.

    The witness minimizes the maximum parent degree, then deterministic visit
    order. Frontier leaves are never treated as having zero children.
    """
    if type(schema) is not LabelSchema or type(parent_degrees) is not tuple or not parent_degrees:
        raise ValueError('Typed label schema and parent degrees required')
    if (any(type(n) is not int or not 0<=n<exploration['through'] for n in parent_degrees) or
            tuple(sorted(set(parent_degrees)))!=parent_degrees):
        raise ValueError('Unique increasing expanded parent degrees required')
    observed={}; examples={}; failure=None
    for degree in parent_degrees:
        for word in sorted(exploration['levels'][degree]):
            state=schema.state(word)
            signature=tuple(sorted(Counter(schema.state(c) for c in exploration['edges'][word]).items()))
            if state in observed and observed[state]!=signature and failure is None:
                previous=examples[state]
                failure={'maximum_parent_degree':max(len(word),len(previous)),
                         'shared_state':state,'word_a':previous,'word_b':word,
                         'children_a':exploration['edges'][previous],
                         'children_b':exploration['edges'][word],
                         'signature_a':observed[state],'signature_b':signature}
            observed.setdefault(state,signature);examples.setdefault(state,word)
    return {'schema_version':1,'label':json.loads(schema.to_json()),
            'parent_degrees':list(parent_degrees),'status':'refuted' if failure else 'finite_verified',
            'shortest_tested_witness':failure,'proof_status':'unproved',
            'table':[{'state':state,'children':signature,'example_parent':examples[state]}
                     for state,signature in sorted(observed.items())]}


def table_counts(inference, root_state, through):
    """Finite table replay refuses an unexpanded state or refuted label."""
    integer(through,0,7)
    if inference.get('status')!='finite_verified' or inference.get('proof_status')!='unproved':
        raise ValueError('Consistent finite inference required; no PROVED transitions accepted')
    if type(root_state) is not tuple or any(type(x) is not int for x in root_state):
        raise ValueError('Exact root state tuple required')
    rows={}
    for row in inference['table']:
        state=tuple(row['state'])
        if state in rows or any(type(v) is not int for v in state):
            raise ValueError('Duplicate or noninteger state')
        targets=[]
        for child,multiplicity in row['children']:
            child=tuple(child)
            if len(child)!=len(state) or any(type(v) is not int for v in child) or child in targets:
                raise ValueError('Duplicate or malformed child state')
            targets.append(child)
        rows[state]=row['children']
    population=Counter({root_state:1});counts=[1]
    for _ in range(through):
        following=Counter()
        for state,number in population.items():
            if state not in rows:
                raise ValueError('Unexpanded state; extrapolation refused')
            for child,multiplicity in rows[state]:
                if type(multiplicity) is not int or multiplicity<1:
                    raise ValueError('Positive exact transition multiplicity required')
                following[tuple(child)]+=number*multiplicity
        population=following;counts.append(sum(population.values()))
    return tuple(counts)


def published_transitions(state):
    """Inspected Testart Lemma 4 formula; external source, no kernel check."""
    integer(state,0,100)
    result=Counter({i:1 for i in range(1,state+2)})
    for i in range(1,state):
        result[i+1]+=2**(state-i)-1
    return result


def reference_demo(through=6):
    integer(through,5,7)
    from ac.research_evidence import load_review
    review=load_review(research_root()/'docs/research/pp06/source_reviews_v1.json')
    if review.fingerprint!=REVIEW_SHA256:
        raise ValueError('Published tree source binding changed; re-audit required')
    spec=InversionClass(tuple(SourcePattern(p,0,(),'C-PP06-tree') for p in ((2,0,1),(2,1,0))))
    candidates=[LabelSchema(())]
    fields_to_try=('leading_zeros','nonleading_zero_flag','zero_count','published_s','last','ascents')
    for width in (1,2):
        candidates += [LabelSchema(fs) for fs in combinations(fields_to_try,width)]
    sides={}
    for side in ('left','right'):
        exploration=explore(GrowthStrategy(spec,side),through)
        trials=[];survivors=[]
        for schema in candidates:
            training=infer_labels(exploration,schema,(0,1,2,3))
            trial={'label':list(schema.features),'training':training}
            if training['status']=='finite_verified':
                full=infer_labels(exploration,schema,tuple(range(through)))
                trial['training_plus_holdout']=full
                if full['status']=='finite_verified':
                    survivors.append((schema,full))
            trials.append(trial)
        minimal=[{'label':list(schema.features),'observed_states':len(full['table'])}
                 for schema,full in survivors if not any(set(other.features)<set(schema.features) for other,_ in survivors)]
        sides[side]={'tree_audit':exploration['audit'],'label_trials':trials,
                     'minimal_labels_within_grammar':minimal}
        if side=='left':
            schema=LabelSchema(('published_s',))
            full=infer_labels(exploration,schema,tuple(range(through)))
            formula_matches=all(dict((tuple(c)[0],m) for c,m in row['children'])==published_transitions(row['state'][0])
                                for row in full['table'])
            counts=table_counts(full,schema.state(()),through)
            sides[side]['published_replay']={'inference':full,'formula_matches_observed_states':formula_matches,
                                            'counts':counts,'generating_function_counts':testart_coefficients(through),
                                            'counts_match':counts==testart_coefficients(through),
                                            'recurrence_candidate':'a[n+1,j] = sum_s a[n,s]*m(s,j), a[0,0]=1; m from the observed table',
                                            'unproved_obligations':['Label sufficiency at every degree','All-length tree closure/coverage','Formula correspondence to exact implemented definitions'],
                                            'proof_status':'unproved'}
    return {'schema_version':1,'benchmark_id':'testart-201-210','through':through,
            'search_design':{'training_parent_degrees':[0,1,2,3],'holdout_parent_degrees':list(range(4,through)),
                             'feature_grammar':list(fields_to_try),'max_width':2,'seed':None,'blind_discovery':False},
            'sides':sides,'strategy':json.loads(GrowthStrategy(spec,'left').to_json()),
            'review_sha256':review.fingerprint,'source_theorem_id':'T-PP06-L4',
            'citation_ids':['C-PP06-tree'],'proof_status':'unproved',
            'implementation_sha256':sha256(source_bytes('research_generating_trees.py')).hexdigest(),
            'oracle_sha256':sha256(source_bytes('research_growth_oracle.py')).hexdigest()}
