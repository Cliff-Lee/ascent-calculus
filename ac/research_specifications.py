"""Small independent recursive-specification interface and finite search.

Constructors operate on words, never on finite matching tables. Published
count identities are reference checks; a synthesized specification has its
own outstanding universal obligations.
"""
from dataclasses import asdict, dataclass
from hashlib import sha256
from itertools import product
import json
from pathlib import Path

from ac.research_math import ClassPresentation, decode, fields, integer, engine_words
from ac.research_math_oracle import reference_words
from ac.research_references import load_references

ANCHORS = ('append', 'prepend', 'before_first_max', 'after_first_max')
ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class InsertionRule:
    id: str
    anchor: str
    copies: int
    minimum_parent_degree: int

    def __post_init__(self):
        if type(self.id) is not str or not self.id or len(self.id) > 100:
            raise ValueError('Bounded rule ID required')
        if self.anchor not in ANCHORS:
            raise ValueError('Unknown insertion primitive')
        integer(self.copies, 1, 3)
        integer(self.minimum_parent_degree, 1, 4)

    def construct(self, parent):
        if type(parent) is not tuple or not self.minimum_parent_degree <= len(parent) <= 6-self.copies:
            raise ValueError('Parent outside constructor degree precondition')
        for value in parent:
            integer(value, 0, 10000)
        index = {'append': len(parent), 'prepend': 0,
                 'before_first_max': parent.index(max(parent)),
                 'after_first_max': parent.index(max(parent))+1}[self.anchor]
        new = max(parent)+1
        return parent[:index] + (new,)*self.copies + parent[index:]

    def decompose(self, word):
        """Return a parent only when multiplicity and exact reconstruction agree."""
        if type(word) is not tuple or len(word)>6:
            raise ValueError('Bounded word tuple required')
        for value in word:
            integer(value,0,10000)
        if not word or word.count(max(word)) != self.copies:
            return None
        parent = tuple(v for v in word if v != max(word))
        if len(parent) < self.minimum_parent_degree:
            return None
        return parent if self.construct(parent) == word else None


@dataclass(frozen=True)
class RecursiveSpecification:
    class_spec: ClassPresentation
    atoms: tuple[tuple[int, ...], ...]
    rules: tuple[InsertionRule, ...]
    citation_ids: tuple[str, ...]
    review_sha256: str
    source_theorem_id: str
    schema_version: int = 1

    def __post_init__(self):
        if type(self.schema_version) is not int or self.schema_version != 1:
            raise ValueError('Unknown specification schema')
        if type(self.class_spec) is not ClassPresentation or self.class_spec.value_base != 0 or self.class_spec.degree_offset != 0:
            raise ValueError('This interpreter requires a zero-based, unshifted class')
        if type(self.atoms) is not tuple or not self.atoms or len(self.atoms) > 20:
            raise ValueError('Bounded nonempty atom tuple required')
        if any(type(w) is not tuple or not 1 <= len(w) <= 3 or not self.class_spec.holds(w) for w in self.atoms):
            raise ValueError('Atoms must belong to the declared class')
        if len(set(self.atoms)) != len(self.atoms):
            raise ValueError('Duplicate atoms')
        if type(self.rules) is not tuple or not 1 <= len(self.rules) <= 8 or any(type(r) is not InsertionRule for r in self.rules):
            raise ValueError('Bounded typed rule tuple required')
        if len({r.id for r in self.rules}) != len(self.rules):
            raise ValueError('Duplicate rule IDs')
        if (type(self.citation_ids) is not tuple or not self.citation_ids or
                any(type(c) is not str or not c or len(c)>100 for c in self.citation_ids)):
            raise ValueError('Explicit citations required')
        if type(self.source_theorem_id) is not str or not self.source_theorem_id or len(self.source_theorem_id)>100:
            raise ValueError('Source theorem reference required')
        import re
        if type(self.review_sha256) is not str or not re.fullmatch('[0-9a-f]{64}',self.review_sha256):
            raise ValueError('Review fingerprint required')

    def to_json(self):
        return json.dumps(asdict(self),sort_keys=True,separators=(',',':'))

    @classmethod
    def from_json(cls, raw):
        obj = decode(raw)
        fields(obj, ('class_spec','atoms','rules','citation_ids','review_sha256','source_theorem_id','schema_version'))
        for key in ('atoms','rules','citation_ids'):
            if type(obj[key]) is not list:
                raise ValueError('Specification arrays required')
        if any(type(w) is not list for w in obj['atoms']):
            raise ValueError('Atom arrays required')
        rules = []
        for r in obj['rules']:
            fields(r, ('id','anchor','copies','minimum_parent_degree'))
            rules.append(InsertionRule(**r))
        return cls(ClassPresentation.from_dict(obj['class_spec']),
                   tuple(tuple(w) for w in obj['atoms']),tuple(rules),
                   tuple(obj['citation_ids']),obj['review_sha256'],
                   obj['source_theorem_id'],obj['schema_version'])

    def equation(self):
        """Exact grammar-count equation, conditional on disjointness/coverage."""
        atoms = '+'.join(f't^{len(w)}' for w in self.atoms)
        terms = [f't^{r.copies}*A_ge_{r.minimum_parent_degree}(t)' for r in self.rules]
        return 'A(t) = ' + ' + '.join([atoms]+terms)

    def describe(self):
        return {'class': json.loads(self.class_spec.to_json()), 'atoms': self.atoms,
                'rules': [{'id': r.id, 'precondition': f'parent in class, length >= {r.minimum_parent_degree}',
                           'constructor': f'insert {r.copies} copies of max(parent)+1 at {r.anchor}',
                           'decomposition': f'remove all maxima; require exactly {r.copies} and exact reconstruction',
                           'size_shift': r.copies} for r in self.rules],
                'equation': self.equation(), 'proof_status': 'unproved'}

    def levels(self, maximum_degree):
        integer(maximum_degree, 1, 6)
        levels = {0: []}
        for n in range(1, maximum_degree+1):
            current = [w for w in self.atoms if len(w)==n]
            for rule in self.rules:
                parent_degree = n-rule.copies
                if parent_degree >= rule.minimum_parent_degree:
                    current += [rule.construct(w) for w in levels[parent_degree]]
            if len(current) > 10000:
                raise ValueError('Specification object budget exceeded')
            # Preserve duplicates and invalid outputs for independent audit.
            levels[n] = current
        return levels

    def counts(self, maximum_degree):
        """Counts derivations, not necessarily distinct mathematical objects."""
        integer(maximum_degree, 1, 6)
        counts = [0]*(maximum_degree+1)
        for n in range(1,maximum_degree+1):
            counts[n] = sum(len(w)==n for w in self.atoms)
            for rule in self.rules:
                if n-rule.copies >= rule.minimum_parent_degree:
                    counts[n] += counts[n-rule.copies]
        return tuple(counts)


def replay(spec, degrees):
    """Audit objects with an independent oracle and every inverse obligation."""
    if type(spec) is not RecursiveSpecification or type(degrees) is not tuple or not degrees:
        raise ValueError('Typed specification and degree tuple required')
    if any(type(n) is not int or not 1<=n<=6 for n in degrees) or tuple(sorted(set(degrees))) != degrees:
        raise ValueError('Unique increasing degrees 1..6 required')
    generated = spec.levels(max(degrees))
    derivation_counts = spec.counts(max(degrees))
    rows = []
    first_failure = None
    for n in degrees:
        oracle = set(reference_words(spec.class_spec,n))
        engine = set(engine_words(spec.class_spec,n))
        candidates = generated[n]
        produced = set(candidates)
        failures = {}
        if oracle != engine:
            failures['engine_oracle_disagreement'] = True
        if produced-oracle:
            failures['invalid_output'] = min(produced-oracle)
        if oracle-produced:
            failures['missing_object'] = min(oracle-produced)
        if len(candidates) != len(produced):
            failures['overlap_or_duplicate'] = len(candidates)-len(produced)
        for word in sorted(oracle):
            branches = [('atom',word)] if word in spec.atoms else []
            for rule in spec.rules:
                parent = rule.decompose(word)
                if parent is not None:
                    if parent not in set(reference_words(spec.class_spec,len(parent))):
                        failures.setdefault('parent_membership', {'word':word,'parent':parent,'rule':rule.id})
                    branches.append((rule.id,parent))
            if len(branches) != 1:
                failures.setdefault('decomposition_partition',{'word':word,'branch_count':len(branches)})
        for rule in spec.rules:
            m = n-rule.copies
            if m >= rule.minimum_parent_degree:
                for parent in reference_words(spec.class_spec,m):
                    image = rule.construct(parent)
                    if image not in oracle or rule.decompose(image) != parent:
                        failures.setdefault('constructor_inverse',{'rule':rule.id,'parent':parent,'image':image})
        row = {'degree':n,'oracle_count':len(oracle),'engine_count':len(engine),
               'derivation_count':derivation_counts[n],'generated_count':len(candidates),
               'distinct_generated_count':len(produced),'failures':failures}
        if failures and first_failure is None:
            first_failure = row
        rows.append(row)
    disagreement = any('engine_oracle_disagreement' in row['failures'] for row in rows)
    return {'schema_version':1,'status':'validation_disagreement' if disagreement else 'refuted' if first_failure else 'finite_verified',
            'tested_degrees':list(degrees),'first_tested_failure':first_failure,'rows':rows,
            'proof_status':'unproved','specification_sha256':sha256(spec.to_json().encode()).hexdigest()}


def obligation_ledger(spec, evidence):
    if evidence.get('specification_sha256') != sha256(spec.to_json().encode()).hexdigest():
        raise ValueError('Evidence refers to another specification')
    statements = {
        'structure': 'Any structural hypotheses used to justify this decomposition hold throughout the source class.',
        'closure': 'Each constructor sends every eligible parent to a source-class member.',
        'coverage': 'Every non-atomic source member belongs to a recursive branch.',
        'disjointness': 'Atoms and branches are pairwise disjoint with no constructor collisions.',
        'inverse': 'Removing maxima and constructing are mutual inverses in both directions.',
        'termination': 'All recursive children have strictly smaller nonnegative degree.',
        'equation': 'The derivation-count equation equals the class counting equation at all degrees.',
    }
    return [{'id':key,'statement':statement,'status':'unproved',
             'finite_check_status': 'not_tested' if key=='structure' else evidence['status'],
             'finite_degrees': [] if key=='structure' else evidence['tested_degrees'],
             'dependencies':[] if key in ('structure','termination') else ['structure','termination'],
             'citation_ids':list(spec.citation_ids)} for key,statement in statements.items()]


def search_fibonacci_specifications(training=(3,4), holdout=(5,6)):
    """Exhaustive small constructor grammar, not unrestricted invention.

    One-copy and two-copy rules vary independently over four insertion sites.
    The reviewed benchmark motivates the multiplicity partition; it is not
    hidden from this search or a blind rediscovery benchmark.
    """
    if training != (3,4) or holdout != (5,6):
        raise ValueError('Use the audited disjoint training/holdout design')
    statement = next(s for s in load_references(
        ROOT/'docs/research/pp03/reference_corpus_v1.json',
        ROOT/'docs/research/pp03/source_reviews_v1.json') if s.id=='PP129-P6')
    atoms = tuple(w for n in (1,2) for w in engine_words(statement.class_spec,n))
    trials = []
    survivors = []
    for one, two in product(ANCHORS,repeat=2):
        candidate = RecursiveSpecification(statement.class_spec,atoms,
            (InsertionRule('one-max',one,1,2),InsertionRule('two-max',two,2,1)),
            (statement.class_spec.citation_id,),statement.review_sha256,statement.source_theorem_id)
        evidence = replay(candidate,training)
        trial = {'specification':json.loads(candidate.to_json()),'anchors':[one,two],'specification_sha256':evidence['specification_sha256'],
                 'training_status':evidence['status'], 'first_training_failure':evidence['first_tested_failure']}
        if evidence['status']=='finite_verified':
            held = replay(candidate,holdout)
            trial['holdout'] = held
            if held['status']=='finite_verified':
                full = replay(candidate,tuple(range(1,7)))
                survivors.append({'specification':json.loads(candidate.to_json()),
                                  'description':candidate.describe(),'evidence':full,
                                  'obligations':obligation_ledger(candidate,full)})
        trials.append(trial)
    return {'schema_version':1,'benchmark_id':'PP129-P6',
            'design':{'training':list(training),'holdout':list(holdout),'seed':None,
                      'grammar':list(ANCHORS),'candidate_count':16,'blind_discovery':False},
            'trials':trials,'survivors':survivors,'proof_status':'unproved',
            'implementation_sha256':sha256(Path(__file__).read_bytes()).hexdigest()}
