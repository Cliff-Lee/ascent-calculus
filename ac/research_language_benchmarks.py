"""PP08 source-grounded regular and counter/grammar reference audits."""
from hashlib import sha256
from itertools import product
import json
from pathlib import Path

from ac.research_languages import Automaton, Terminal, Transition, Grammar, Production, Symbol, equation_coefficients
from ac.research_math import ClassPresentation, SourcePattern, engine_words
from ac.research_math_oracle import reference_words
from ac.research_recursive_bijections import independent_tiles, reference_specification
from ac.research_evidence import load_review

ROOT=Path(__file__).resolve().parents[1]
REVIEW_SHA256='69d94bb9978313a12e5fff4e9375498346b8ac04416c60ce43d28bda93a40db3'


def tile_automaton():
    return Automaton(('I','A'),(Terminal('one',1),Terminal('two',2)),
        tuple(Transition(s,t,'A') for s in ('I','A') for t in ('one','two')),'I',('A',))


def motzkin_models():
    alphabet=tuple(Terminal(name,1) for name in ('H','U','D'))
    machine=Automaton(('Q',),alphabet,
        (Transition('Q','H','Q',0),Transition('Q','U','Q',1),Transition('Q','D','Q',-1)),
        'Q',('Q',),'one_counter')
    t=lambda name:Symbol('terminal',name)
    m=Symbol('nonterminal','M')
    grammar=Grammar(('M',),alphabet,
        (Production('empty','M',()),Production('horizontal','M',(t('H'),m)),
         Production('arch','M',(t('U'),m,t('D'),m))),'M')
    return machine,grammar


def independent_motzkin_paths(degree):
    """Full-product path oracle, using prefix balance without grammar/machine."""
    from ac.research_math import integer
    integer(degree,0,6)
    for tokens in product(('H','U','D'),repeat=degree):
        if tokens.count('U')!=tokens.count('D'):continue
        if all(prefix.count('U')>=prefix.count('D') for prefix in (tokens[:i] for i in range(1,len(tokens)+1))):
            yield tokens


def check_motzkin(machine,grammar,through=6):
    from ac.research_math import integer
    integer(through,1,6)
    levels=grammar.levels(through)
    coefficients=equation_coefficients(grammar.equations(),through)[grammar.start]
    counter_counts=machine.counts(through)
    rows=[];first=None
    for n in range(through+1):
        expected=set(independent_motzkin_paths(n)); actual=levels[n]
        accepted={tokens for tokens in product(('H','U','D'),repeat=n) if machine.accepts(tokens)}
        checks={'grammar_complete_objects':set(actual)==expected,
                'unambiguous_at_degree':len(actual)==len(set(actual)),
                'machine_complete_objects':accepted==expected,
                'coefficients':len(expected)==coefficients[n]==counter_counts[n]}
        row={'degree':n,'oracle_count':len(expected),'derivation_count':len(actual),
             'counter_count':counter_counts[n],'equation_coefficient':coefficients[n],
             'checks':checks,'missing_path':min(expected-set(actual)) if expected-set(actual) else None,
             'extra_path':min(set(actual)-expected) if set(actual)-expected else None}
        if not all(checks.values()) and first is None:first=row
        rows.append(row)
    return {'status':'refuted' if first else 'finite_verified','rows':rows,
            'first_tested_failure':first,'proof_status':'unproved'}


def human_equations(export):
    """Render validated data with a namespace distinct from the size variable t."""
    rows=[]
    for row in export['equations']:
        terms=[str(row['constant'])] if row.get('constant') else []
        for term in row['terms']:
            factors=[]
            if term['coefficient']!=1:factors.append(str(term['coefficient']))
            if term['t_power']:factors.append('t' if term['t_power']==1 else 't^'+str(term['t_power']))
            factors += ['F_'+name for name in term['variables']]
            terms.append('*'.join(factors) if factors else '1')
        rows.append('F_'+row['variable']+' = '+(' + '.join(terms) if terms else '0'))
    return rows


def reference_demo():
    review=load_review(ROOT/'docs/research/pp08/source_reviews_v1.json')
    if review.fingerprint!=REVIEW_SHA256:raise ValueError('Language reference source changed; explicit re-audit required')
    tiles=tile_automaton();counter,grammar=motzkin_models()
    tile_counts=tiles.counts(6);tile_equations=tiles.equations()
    exported=equation_coefficients(tile_equations,6)['I']
    tile_rows=[]
    for n in range(1,7):
        objects=list(independent_tiles(n))
        accepted=[]
        for length in range(1,n+1):
            for word in product(('one','two'),repeat=length):
                if sum(1 if x=='one' else 2 for x in word)==n and tiles.accepts(word):accepted.append(word)
        source=set(reference_words(reference_specification().class_spec,n))
        tile_rows.append({'degree':n,'machine_count':tile_counts[n],'equation_count':exported[n],
                          'independent_tile_count':len(objects),'independent_ascent_count':len(source),
                          'passed':tile_counts[n]==exported[n]==len(objects)==len(source) and
                                   {tuple(1 if x=='one' else 2 for x in w) for w in accepted}==set(objects)})
    path_audit=check_motzkin(counter,grammar)
    ordinary=ClassPresentation('ordinary',0,tuple(SourcePattern(p,0,(),'C-PP08-Motzkin') for p in ((0,0,0),(1,0,1))),(),0,'C-PP08-Motzkin')
    bridge=[]
    for n in range(1,7):
        a=set(engine_words(ordinary,n));b=set(reference_words(ordinary,n))
        paths=path_audit['rows'][n]['oracle_count']
        bridge.append({'degree':n,'engine_count':len(a),'independent_ascent_count':len(b),'path_count':paths,
                       'same_complete_ascent_members':a==b,'counts_match':len(a)==len(b)==paths})
    ambiguous=Grammar(grammar.nonterminals,grammar.alphabet,grammar.productions+(Production('duplicate_empty','M',()),),grammar.start)
    wrong_finite=Automaton(counter.states,counter.alphabet,
        tuple(Transition(e.source,e.terminal,e.target) for e in counter.transitions),counter.start,counter.accepting)
    negatives=[{'name':'duplicated_empty_production','audit':check_motzkin(counter,ambiguous,3)},
               {'name':'counter_discarded_changes_language','audit':check_motzkin(wrong_finite,grammar,3)}]
    return {'schema_version':1,'source_review_sha256':review.fingerprint,
            'regular':{'automaton':json.loads(tiles.to_json()),'state_space':tiles.state_space,
                       'citation_ids':['C-PP-129-6'],'source_review_sha256':reference_specification().review_sha256,
                       'equations':tile_equations,'human_equations':human_equations(tile_equations),
                       'derived_rational_gf':'(t+t^2)/(1-t-t^2)',
                       'derivation':['F_I=(t+t^2)*F_A','F_A=1+(t+t^2)*F_A','F_A=1/(1-t-t^2)','F_I=(t+t^2)/(1-t-t^2)'],
                       'constant_coefficient':tile_counts[0],'rows':tile_rows,'proof_status':'unproved'},
            'counter_grammar':{'automaton':json.loads(counter.to_json()),'state_space':counter.state_space,
                               'grammar':json.loads(grammar.to_json()),'equations':grammar.equations(),
                               'human_equations':human_equations(grammar.equations()),'audit':path_audit,
                               'class_bridge':bridge,'citation_ids':['C-PP08-Motzkin'],
                               'empty_convention':{'grammar_paths_degree_zero':1,'ordinary_engine_degree_zero':0,
                                                   'comparison_starts_at_degree':1,'ordinary_gf_relation':'A(t)=F_M(t)-1'},
                               'derivation':['M = epsilon | H M | U M D M','F_M=1+t*F_M+t^2*F_M^2','F_M(0)=1',
                                             'A=F_M-1 counts nonempty source degrees'],
                               'logical_obligations':['All-length completeness and unambiguity of the path grammar',
                                    'Exact correspondence with the source recurrence and hypotheses',
                                    'No sequence-to-path bijection is claimed from count agreement alone',
                                    'Correct selected formal-series initial branch'], 'proof_status':'unproved'},
            'negative_controls':negatives,'symbolic_backend':{'implementation':'exact integer coefficient convolution and typed equation exporter',
                'third_party_solver':'not integrated; SymPy absent and unnecessary for this bounded benchmark'},
            'proof_status':'unproved','implementation_sha256':sha256(Path(__file__).read_bytes()).hexdigest(),
            'language_interface_sha256':sha256(Path(__file__).with_name('research_languages.py').read_bytes()).hexdigest()}
