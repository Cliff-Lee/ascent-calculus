"""Small data-only weighted automata and productive grammar interfaces.

Finite weighted DFAs give linear/rational equation systems. A counter's domain
is unbounded even when its control states and every finite experiment are small.
Grammar equations are candidates for object counts until unambiguity is audited.
"""
from collections import Counter
from dataclasses import asdict, dataclass
from functools import lru_cache
from itertools import product
import json
import re
from ac.research_math import decode, fields, integer


def identifier(value):
    if type(value) is not str or not re.fullmatch('[A-Za-z][A-Za-z0-9_]{0,29}',value):
        raise ValueError('Bounded symbolic identifier required')


@dataclass(frozen=True)
class Terminal:
    name: str
    weight: int

    def __post_init__(self):
        identifier(self.name);integer(self.weight,1,3)


@dataclass(frozen=True)
class Transition:
    source: str
    terminal: str
    target: str
    counter_delta: int=0

    def __post_init__(self):
        for x in (self.source,self.terminal,self.target):identifier(x)
        integer(self.counter_delta,-1,1)


@dataclass(frozen=True)
class Automaton:
    states: tuple[str,...]
    alphabet: tuple[Terminal,...]
    transitions: tuple[Transition,...]
    start: str
    accepting: tuple[str,...]
    kind: str='finite_dfa'
    schema_version: int=1

    def __post_init__(self):
        if type(self.schema_version) is not int or self.schema_version!=1 or self.kind not in ('finite_dfa','one_counter'):
            raise ValueError('Explicit finite_dfa or one_counter model required')
        if type(self.states) is not tuple or not 1<=len(self.states)<=4 or len(set(self.states))!=len(self.states):
            raise ValueError('Unique bounded control-state tuple required')
        for state in self.states:identifier(state)
        if type(self.alphabet) is not tuple or not 1<=len(self.alphabet)<=3 or any(type(a) is not Terminal for a in self.alphabet):
            raise ValueError('Typed bounded alphabet required')
        names={a.name for a in self.alphabet}
        if len(names)!=len(self.alphabet):raise ValueError('Duplicate alphabet symbol')
        if self.start not in self.states or type(self.accepting) is not tuple or len(set(self.accepting))!=len(self.accepting) or not set(self.accepting)<=set(self.states):
            raise ValueError('Invalid initial/final states')
        if type(self.transitions) is not tuple or len(self.transitions)>12 or any(type(t) is not Transition for t in self.transitions):
            raise ValueError('Typed bounded transitions required')
        keys=set()
        for t in self.transitions:
            if t.source not in self.states or t.target not in self.states or t.terminal not in names or (t.source,t.terminal) in keys:
                raise ValueError('Unknown or nondeterministic transition')
            if self.kind=='finite_dfa' and t.counter_delta!=0:
                raise ValueError('A counter update cannot be declared finite-state')
            keys.add((t.source,t.terminal))

    @property
    def state_space(self):
        return 'finite_control_states' if self.kind=='finite_dfa' else 'control_states_times_unbounded_nonnegative_counter'

    def accepts(self,tokens):
        if type(tokens) is not tuple or len(tokens)>8:raise ValueError('Bounded terminal tuple required')
        weights={a.name:a.weight for a in self.alphabet}
        if any(type(x) is not str or x not in weights for x in tokens):raise ValueError('Unknown input symbol')
        if sum(weights[x] for x in tokens)>8:raise ValueError('Input degree budget exceeded')
        transitions={(t.source,t.terminal):t for t in self.transitions}
        state=self.start;counter=0
        for token in tokens:
            edge=transitions.get((state,token))
            if edge is None:return False
            state=edge.target;counter+=edge.counter_delta
            if counter<0:return False
        return state in self.accepting and counter==0

    def counts(self,through):
        integer(through,0,8)
        weights={a.name:a.weight for a in self.alphabet}
        outgoing={s:[t for t in self.transitions if t.source==s] for s in self.states}
        populations=[Counter() for _ in range(through+1)]
        populations[0][(self.start,0)]=1
        for n in range(through+1):
            for (state,counter),number in populations[n].items():
                for edge in outgoing[state]:
                    target_degree=n+weights[edge.terminal];height=counter+edge.counter_delta
                    if target_degree<=through and height>=0:
                        populations[target_degree][(edge.target,height)]+=number
        return tuple(sum(number for (state,counter),number in p.items() if state in self.accepting and counter==0) for p in populations)

    def equations(self):
        if self.kind!='finite_dfa':
            raise ValueError('Finite-state rational exporter cannot discard an unbounded counter')
        weights={a.name:a.weight for a in self.alphabet}
        return {'schema_version':1,'classification':'finite_weighted_linear_system',
                'gf_class_for_machine':'rational','root':self.start,'size_semantics':'sum_of_terminal_weights',
                'equations':[{'variable':state,'constant':int(state in self.accepting),
                              'terms':[{'coefficient':1,'t_power':weights[e.terminal],'variables':[e.target]}
                                       for e in self.transitions if e.source==state]} for state in self.states],
                'logical_obligations':['Machine recognizes intended class completely','Correct terminal weights and initial/final states'],
                'proof_status':'unproved'}

    def to_json(self):return json.dumps(asdict(self),sort_keys=True,separators=(',',':'))

    @classmethod
    def from_json(cls,raw):
        obj=decode(raw);fields(obj,('states','alphabet','transitions','start','accepting','kind','schema_version'))
        for key in ('states','alphabet','transitions','accepting'):
            if type(obj[key]) is not list:raise ValueError('Automaton arrays required')
        for a in obj['alphabet']:fields(a,('name','weight'))
        for t in obj['transitions']:fields(t,('source','terminal','target','counter_delta'))
        return cls(tuple(obj['states']),tuple(Terminal(**a) for a in obj['alphabet']),tuple(Transition(**t) for t in obj['transitions']),obj['start'],tuple(obj['accepting']),obj['kind'],obj['schema_version'])


@dataclass(frozen=True)
class Symbol:
    kind: str
    name: str

    def __post_init__(self):
        identifier(self.name)
        if self.kind not in ('terminal','nonterminal'):raise ValueError('Tagged grammar symbol required')


@dataclass(frozen=True)
class Production:
    id: str
    lhs: str
    rhs: tuple[Symbol,...]

    def __post_init__(self):
        identifier(self.id);identifier(self.lhs)
        if type(self.rhs) is not tuple or len(self.rhs)>6 or any(type(s) is not Symbol for s in self.rhs):
            raise ValueError('Bounded tagged right-hand side required')


@dataclass(frozen=True)
class Grammar:
    nonterminals: tuple[str,...]
    alphabet: tuple[Terminal,...]
    productions: tuple[Production,...]
    start: str
    schema_version: int=1

    def __post_init__(self):
        if type(self.schema_version) is not int or self.schema_version!=1:raise ValueError('Unknown grammar schema')
        if type(self.nonterminals) is not tuple or not 1<=len(self.nonterminals)<=4 or len(set(self.nonterminals))!=len(self.nonterminals):
            raise ValueError('Unique bounded nonterminal tuple required')
        for name in self.nonterminals:identifier(name)
        if self.start not in self.nonterminals:raise ValueError('Unknown start nonterminal')
        if type(self.alphabet) is not tuple or not 1<=len(self.alphabet)<=3 or any(type(a) is not Terminal for a in self.alphabet):raise ValueError('Typed alphabet required')
        names={a.name for a in self.alphabet}
        if len(names)!=len(self.alphabet):raise ValueError('Duplicate terminal')
        if type(self.productions) is not tuple or not 1<=len(self.productions)<=8 or any(type(p) is not Production for p in self.productions):raise ValueError('Typed productions required')
        if len({p.id for p in self.productions})!=len(self.productions):raise ValueError('Duplicate production ID')
        for p in self.productions:
            if p.lhs not in self.nonterminals:raise ValueError('Unknown production parent')
            for s in p.rhs:
                if s.name not in (names if s.kind=='terminal' else self.nonterminals):raise ValueError('Dangling grammar symbol')
            if p.rhs and not any(s.kind=='terminal' for s in p.rhs):
                raise ValueError('Zero-degree recursive/unit productions unsupported')

    def equations(self):
        weights={a.name:a.weight for a in self.alphabet}
        return {'schema_version':1,'classification':'polynomial_derivation_system',
                'gf_class_for_intended_objects':'not_certified','root':self.start,
                'equations':[{'variable':name,'terms':[{'coefficient':1,
                    't_power':sum(weights[s.name] for s in p.rhs if s.kind=='terminal'),
                    'variables':[s.name for s in p.rhs if s.kind=='nonterminal']}
                    for p in self.productions if p.lhs==name]} for name in self.nonterminals],
                'logical_obligations':['Complete encoding of intended objects','Unambiguous production partition',
                    'Correct degree and empty-object convention','Intended generating function is the selected formal-series branch'],
                'proof_status':'unproved'}

    def levels(self,through):
        integer(through,0,6)
        weights={a.name:a.weight for a in self.alphabet}
        @lru_cache(maxsize=None)
        def derive(name,n):
            outputs=[]
            for p in self.productions:
                if p.lhs!=name:continue
                terminal_degree=sum(weights[s.name] for s in p.rhs if s.kind=='terminal')
                remaining=n-terminal_degree
                if remaining<0:continue
                children=[s for s in p.rhs if s.kind=='nonterminal']
                for sizes in product(range(remaining+1),repeat=len(children)):
                    if sum(sizes)!=remaining:continue
                    populations=[derive(s.name,size) for s,size in zip(children,sizes)]
                    for selected in product(*populations):
                        pieces=[];i=0
                        for s in p.rhs:
                            if s.kind=='terminal':pieces.append(s.name)
                            else:pieces.extend(selected[i]);i+=1
                        outputs.append(tuple(pieces))
                        if len(outputs)>10000:raise ValueError('Derivation budget exceeded')
            return tuple(outputs)
        return {n:derive(self.start,n) for n in range(through+1)}

    def to_json(self):return json.dumps(asdict(self),sort_keys=True,separators=(',',':'))

    @classmethod
    def from_json(cls,raw):
        obj=decode(raw);fields(obj,('nonterminals','alphabet','productions','start','schema_version'))
        for key in ('nonterminals','alphabet','productions'):
            if type(obj[key]) is not list:raise ValueError('Grammar arrays required')
        for a in obj['alphabet']:fields(a,('name','weight'))
        productions=[]
        for p in obj['productions']:
            fields(p,('id','lhs','rhs'))
            if type(p['rhs']) is not list:raise ValueError('Production array required')
            for s in p['rhs']:fields(s,('kind','name'))
            productions.append(Production(p['id'],p['lhs'],tuple(Symbol(**s) for s in p['rhs'])))
        return cls(tuple(obj['nonterminals']),tuple(Terminal(**a) for a in obj['alphabet']),tuple(productions),obj['start'],obj['schema_version'])


def equation_coefficients(equations,through):
    """Evaluate exported positive-degree polynomial systems using exact integers.

    This evaluates derivation equations, not an algebraicity proof for a class.
    """
    integer(through,0,8)
    rows=equations['equations'];names=[r['variable'] for r in rows]
    if len(set(names))!=len(names) or not 1<=len(names)<=4:raise ValueError('Unique bounded equation variables required')
    coefficients={name:[0]*(through+1) for name in names}
    for row in rows:
        for term in row['terms']:
            integer(term['coefficient'],1,10);integer(term['t_power'],0,18)
            if type(term['variables']) is not list or len(term['variables'])>6 or any(v not in names for v in term['variables']):raise ValueError('Unknown equation variable')
            if term['variables'] and term['t_power']==0:raise ValueError('Zero-degree recursive equation unsupported')
    for n in range(through+1):
        for row in rows:
            value=row.get('constant',0) if n==0 else 0
            integer(row.get('constant',0),0,10)
            for term in row['terms']:
                remaining=n-term['t_power']
                if remaining<0:continue
                convolution=[1]+[0]*remaining
                for variable in term['variables']:
                    convolution=[sum(convolution[i-j]*coefficients[variable][j] for j in range(i+1)) for i in range(remaining+1)]
                value+=term['coefficient']*convolution[remaining]
            coefficients[row['variable']][n]=value
    return {name:tuple(values) for name,values in coefficients.items()}
