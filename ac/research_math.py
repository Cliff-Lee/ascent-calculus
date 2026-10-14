"""Source-indexed presentations of existing families; exact bounded evaluation.

Production definitions/generators remain in ac.classes/ac.generate. The oracle
is deliberately separate and bounded. No finite result becomes a proof.
"""
from ac.research_resources import source_bytes
from dataclasses import dataclass,asdict
from hashlib import sha256
import json
from pathlib import Path
from math import comb

DEFINITION_VERSION='ac-positive-families-v1'
FAMILIES=('ordinary','modified','revised')


def integer(value,low,high):
    if type(value) is not int or not low<=value<=high:raise ValueError(f'Expected integer {low}..{high}')


def citation(value):
    if type(value) is not str or not 1<=len(value)<=100:raise ValueError('Explicit source citation required')


def decode(raw):
    if type(raw) is not str or len(raw.encode())>30000:raise ValueError('Bounded JSON required')
    def unique(pairs):
        out={}
        for k,v in pairs:
            if k in out:raise ValueError('Duplicate JSON key')
            out[k]=v
        return out
    def bad(v):raise ValueError('Nonfinite JSON')
    return json.loads(raw,object_pairs_hook=unique,parse_constant=bad)


def fields(obj,names):
    if type(obj) is not dict or set(obj)!=set(names):raise ValueError('Missing/unknown schema fields')


@dataclass(frozen=True)
class SourcePattern:
    values: tuple[int,...]
    value_base: int
    adjacent_positions: tuple[int,...]
    citation_id: str

    def __post_init__(self):
        integer(self.value_base,0,1);citation(self.citation_id)
        if type(self.values) is not tuple or not 1<=len(self.values)<=8:raise ValueError('Bounded pattern tuple required')
        for v in self.values:integer(v,self.value_base,self.value_base+7)
        if set(self.values)!=set(range(self.value_base,max(self.values)+1)):raise ValueError('Explicit rank-normalized pattern required')
        if type(self.adjacent_positions) is not tuple or tuple(sorted(set(self.adjacent_positions)))!=self.adjacent_positions:
            raise ValueError('Unique increasing adjacent-position constraints required')
        for i in self.adjacent_positions:integer(i,1,len(self.values)-1)

    def compile(self):
        from ac.patterns.classical import ClassicalPattern
        from ac.patterns.general import ConstraintPattern
        from ac.patterns.constraints import AllOf,PositionAdjacent
        classical=ClassicalPattern(tuple(v+1-self.value_base for v in self.values)).compile()
        if not self.adjacent_positions:return classical
        return ConstraintPattern(len(self.values),AllOf((classical.constraint,)+tuple(PositionAdjacent(i,i+1) for i in self.adjacent_positions)))

    @classmethod
    def from_dict(cls,obj):
        fields(obj,('values','value_base','adjacent_positions','citation_id'))
        if type(obj['values']) is not list or type(obj['adjacent_positions']) is not list:raise ValueError('Pattern arrays required')
        return cls(tuple(obj['values']),obj['value_base'],tuple(obj['adjacent_positions']),obj['citation_id'])


@dataclass(frozen=True)
class ClassPresentation:
    family: str
    value_base: int
    avoid: tuple[SourcePattern,...]
    contain: tuple[SourcePattern,...]
    degree_offset: int
    citation_id: str
    definition_version: str=DEFINITION_VERSION

    def __post_init__(self):
        if self.family not in FAMILIES:raise ValueError('Unsupported family; an audited family adapter is required')
        integer(self.value_base,0,1);integer(self.degree_offset,-20,20);citation(self.citation_id)
        if self.definition_version!=DEFINITION_VERSION:raise ValueError('Unknown definition version')
        for ps in (self.avoid,self.contain):
            if type(ps) is not tuple or len(ps)>12 or any(type(p) is not SourcePattern for p in ps):raise ValueError('Typed bounded patterns required')
            if any(p.value_base!=self.value_base for p in ps):raise ValueError('Pattern and word source conventions disagree')

    @property
    def includes_empty(self):return self.family!='ordinary'

    def holds(self,source_word):
        from ac.core.word import ChainWord
        from ac.logic.predicates import AscentSequence,Modified,Revised
        if type(source_word) is not tuple:raise ValueError('Source word tuple required')
        for v in source_word:integer(v,self.value_base,10000)
        word=ChainWord(tuple(v+1-self.value_base for v in source_word))
        family=dict(zip(FAMILIES,(AscentSequence,Modified,Revised)))[self.family]()
        return family.holds(word) and not any(p.compile().contains(word) for p in self.avoid) and all(p.compile().contains(word) for p in self.contain)

    def to_json(self):return json.dumps(asdict(self),sort_keys=True,separators=(',',':'))

    @property
    def fingerprint(self):return sha256(self.to_json().encode()).hexdigest()

    @classmethod
    def from_dict(cls,obj):
        fields(obj,('family','value_base','avoid','contain','degree_offset','citation_id','definition_version'))
        if type(obj['avoid']) is not list or type(obj['contain']) is not list:raise ValueError('Pattern arrays required')
        return cls(obj['family'],obj['value_base'],tuple(map(SourcePattern.from_dict,obj['avoid'])),tuple(map(SourcePattern.from_dict,obj['contain'])),obj['degree_offset'],obj['citation_id'],obj['definition_version'])

    @classmethod
    def from_json(cls,raw):return cls.from_dict(decode(raw))


def engine_words(spec,length):
    integer(length,0,6)
    from ac.generate.universes import ascent_sequences,modified_sequences,revised_sequences
    generator=dict(zip(FAMILIES,(ascent_sequences,modified_sequences,revised_sequences)))[spec.family]
    for word in generator(length):
        source=tuple(v-1+spec.value_base for v in word.values)
        if spec.holds(source):yield source


@dataclass(frozen=True)
class MapContract:
    """Domain/codomain wrapper for existing maps, not a new bijection claim."""
    primitive: str
    domain: ClassPresentation
    codomain: ClassPresentation
    inverse_primitive: str
    degree_shift: int=0
    minimum_length: int=1

    def __post_init__(self):
        if type(self.domain) is not ClassPresentation or type(self.codomain) is not ClassPresentation:raise ValueError('Typed map classes required')
        pairs={'hat':('ordinary','modified','inverse_hat'),'inverse_hat':('modified','ordinary','hat')}
        if self.primitive not in pairs or (self.domain.family,self.codomain.family,self.inverse_primitive)!=pairs[self.primitive]:raise ValueError('Map family/inverse contract is incompatible with existing primitive')
        if type(self.degree_shift) is not int or self.degree_shift!=0:raise ValueError('Existing hat maps are length preserving')
        integer(self.minimum_length,1,100)
        if self.domain.degree_offset!=self.codomain.degree_offset:raise ValueError('Degree offsets do not commute with this map')

    def apply(self,source):
        from ac.algebra.transforms import HatT,InverseHatT
        from ac.core.word import ChainWord
        if len(source)<self.minimum_length:raise ValueError('Word outside declared nonempty map scope')
        if not self.domain.holds(source):raise ValueError('Word outside declared map domain')
        engine=ChainWord(tuple(v+1-self.domain.value_base for v in source))
        result={'hat':HatT,'inverse_hat':InverseHatT}[self.primitive]().apply(engine).output
        output=tuple(v-1+self.codomain.value_base for v in result.values)
        if not self.codomain.holds(output):raise ValueError('Map output violates declared codomain restrictions')
        return output

    def inverse(self):return MapContract(self.inverse_primitive,self.codomain,self.domain,self.primitive,minimum_length=self.minimum_length)
    def to_json(self):return json.dumps(asdict(self),sort_keys=True,separators=(',',':'))
    @classmethod
    def from_json(cls,raw):
        obj=decode(raw);fields(obj,('primitive','domain','codomain','inverse_primitive','degree_shift','minimum_length'))
        return cls(obj['primitive'],ClassPresentation.from_dict(obj['domain']),ClassPresentation.from_dict(obj['codomain']),obj['inverse_primitive'],obj['degree_shift'],obj['minimum_length'])


@dataclass(frozen=True)
class CountFormula:
    kind: str
    parameters: tuple[int,...]

    def __post_init__(self):
        arity={'linear':2,'fibonacci_shift':1,'binomial_plus_constant':2}
        if self.kind not in arity or type(self.parameters) is not tuple or len(self.parameters)!=arity[self.kind]:raise ValueError('Unsupported exact count expression')
        for p in self.parameters:integer(p,0,100)
        if self.kind=='binomial_plus_constant' and self.parameters[0]<1:raise ValueError('Positive binomial order required')

    def evaluate(self,n):
        integer(n,0,100)
        a=self.parameters[0]
        if self.kind=='linear':return a*n+self.parameters[1]
        if self.kind=='binomial_plus_constant':return comb(n,a)+self.parameters[1]
        left,right=0,1
        for _ in range(n+a):left,right=right,left+right
        return left


@dataclass(frozen=True)
class EnumerationStatement:
    id: str
    class_spec: ClassPresentation
    formula: CountFormula
    minimum_degree: int
    maximum_degree: int | None
    source_theorem_id: str
    review_sha256: str

    def __post_init__(self):
        if type(self.class_spec) is not ClassPresentation or type(self.formula) is not CountFormula:raise ValueError('Typed enumeration statement required')
        citation(self.id);citation(self.source_theorem_id)
        integer(self.minimum_degree,0,100)
        if self.maximum_degree is not None:integer(self.maximum_degree,self.minimum_degree,100)
        if self.minimum_degree+self.class_spec.degree_offset<0:raise ValueError('Scope includes negative lengths')
        import re
        if type(self.review_sha256) is not str or not re.fullmatch('[0-9a-f]{64}',self.review_sha256):raise ValueError('Explicit review fingerprint required')

    def to_json(self):return json.dumps(asdict(self),sort_keys=True,separators=(',',':'))
    @classmethod
    def from_json(cls,raw):
        obj=decode(raw);fields(obj,('id','class_spec','formula','minimum_degree','maximum_degree','source_theorem_id','review_sha256'))
        f=obj['formula'];fields(f,('kind','parameters'))
        if type(f['parameters']) is not list:raise ValueError('Parameter array required')
        return cls(obj['id'],ClassPresentation.from_dict(obj['class_spec']),CountFormula(f['kind'],tuple(f['parameters'])),obj['minimum_degree'],obj['maximum_degree'],obj['source_theorem_id'],obj['review_sha256'])


def evaluate(statement,degrees):
    """Compare complete member sets, not just counts, using two implementations."""
    from ac.research_math_oracle import reference_words
    if type(statement) is not EnumerationStatement or type(degrees) is not tuple or not degrees or tuple(sorted(set(degrees)))!=degrees:raise ValueError('Typed statement and ordered degree tuple required')
    for n in degrees:
        integer(n,statement.minimum_degree,statement.maximum_degree if statement.maximum_degree is not None else 100)
        integer(n+statement.class_spec.degree_offset,0,6)
    rows=[];failure=None
    for n in degrees:
        length=n+statement.class_spec.degree_offset
        production=list(engine_words(statement.class_spec,length));reference=list(reference_words(statement.class_spec,length))
        a,b=set(production),set(reference);expected=statement.formula.evaluate(n)
        equal=a==b and len(production)==len(a) and len(reference)==len(b)
        matches=equal and len(a)==expected
        row={'degree':n,'word_length':length,'engine_count':len(a),'oracle_count':len(b),'expected':expected,'same_complete_members':equal,'formula_matches':matches,'engine_only':list(min(a-b)) if a-b else None,'oracle_only':list(min(b-a)) if b-a else None}
        rows.append(row)
        if not matches and failure is None:failure=row
    return {'schema_version':1,'statement':json.loads(statement.to_json()),'complete_degrees':list(degrees),'status':'validation_disagreement' if any(not r['same_complete_members'] for r in rows) else 'refuted' if failure else 'finite_verified','first_tested_failure':failure,'rows':rows,'proof_status':'not_proved','provenance':{'engine_adapter_sha256':sha256(source_bytes('research_math.py')).hexdigest(),'engine_source_sha256':{name:sha256(source_bytes(name)).hexdigest() for name in ('classes/theories.py','generate/universes.py','patterns/classical.py','patterns/constraints.py','patterns/general.py','logic/predicates.py')},'oracle_sha256':sha256(source_bytes('research_math_oracle.py')).hexdigest(),'independence':'separate family predicates, enumeration and pattern matching; shared typed inputs and expected expression'}}
