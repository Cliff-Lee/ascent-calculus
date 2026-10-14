"""Exact weighted counts, grammar ambiguity and counter soundness controls."""
from dataclasses import replace
from itertools import product
import json
import pytest

from ac.research_languages import Automaton, Terminal, Transition, Grammar, Production, Symbol, equation_coefficients
import ac.research_language_benchmarks as bench


@pytest.fixture(scope='module')
def demo():return bench.reference_demo()


def test_regular_weighted_automaton_roundtrip_and_exact_counts(demo):
    machine=bench.tile_automaton()
    assert Automaton.from_json(machine.to_json())==machine
    assert machine.kind=='finite_dfa' and machine.state_space=='finite_control_states'
    assert machine.counts(6)==(0,1,2,3,5,8,13)
    assert machine.accepts(('two',)) and not machine.accepts(())
    assert equation_coefficients(machine.equations(),6)['I']==machine.counts(6)
    assert all(r['passed'] for r in demo['regular']['rows'])
    assert demo['regular']['derived_rational_gf']=='(t+t^2)/(1-t-t^2)'


def test_counter_is_unbounded_and_not_a_finite_state_rational_export():
    counter,grammar=bench.motzkin_models()
    assert Automaton.from_json(counter.to_json())==counter
    assert 'unbounded' in counter.state_space
    assert counter.accepts(('U','U','D','D'))
    assert not counter.accepts(('D','U')) and not counter.accepts(('U',))
    with pytest.raises(ValueError,match='unbounded'):counter.equations()
    with pytest.raises(ValueError,match='counter update'):replace(counter,kind='finite_dfa')
    assert counter.counts(6)==(1,1,2,4,9,21,51)
    assert Grammar.from_json(grammar.to_json())==grammar


def test_complete_path_sets_and_grammar_coefficients(demo):
    counter,grammar=bench.motzkin_models()
    levels=grammar.levels(6)
    for n in range(7):
        independent=set(bench.independent_motzkin_paths(n))
        assert set(levels[n])==independent
        assert len(levels[n])==len(independent)
        assert all(counter.accepts(w) for w in independent)
    assert equation_coefficients(grammar.equations(),6)['M']==(1,1,2,4,9,21,51)
    assert demo['counter_grammar']['audit']['status']=='finite_verified'
    assert all(r['counts_match'] and r['same_complete_ascent_members'] for r in demo['counter_grammar']['class_bridge'])
    assert demo['counter_grammar']['empty_convention']=={'grammar_paths_degree_zero':1,'ordinary_engine_degree_zero':0,'comparison_starts_at_degree':1,'ordinary_gf_relation':'A(t)=F_M(t)-1'}
    assert grammar.equations()['gf_class_for_intended_objects']=='not_certified'


def test_saved_negative_controls_and_initial_conditions(demo):
    ambiguity,discarded=demo['negative_controls']
    assert ambiguity['audit']['status']=='refuted'
    first=ambiguity['audit']['first_tested_failure']
    assert first['degree']==0 and first['derivation_count']==2
    assert first['checks']['grammar_complete_objects']
    assert not first['checks']['unambiguous_at_degree']
    assert discarded['audit']['first_tested_failure']['degree']==1
    assert not discarded['audit']['first_tested_failure']['checks']['machine_complete_objects']
    wrong=replace(bench.tile_automaton(),accepting=('I','A'))
    assert wrong.counts(0)==(1,) # wrong empty-word convention exposed
    assert wrong.counts(6)[1:]==bench.tile_automaton().counts(6)[1:]


def test_grammar_omitted_branch_refuted():
    machine,grammar=bench.motzkin_models()
    incomplete=replace(grammar,productions=grammar.productions[:2])
    failed=bench.check_motzkin(machine,incomplete,3)
    assert failed['first_tested_failure']['degree']==2
    assert failed['first_tested_failure']['missing_path']==('U','D')


def test_path_oracle_independent_of_grammar_and_machine(monkeypatch):
    def forbidden(*_):raise AssertionError('Oracle reused production')
    monkeypatch.setattr(Grammar,'levels',forbidden)
    monkeypatch.setattr(Automaton,'accepts',forbidden)
    monkeypatch.setattr(Automaton,'counts',forbidden)
    assert len(list(bench.independent_motzkin_paths(6)))==51


def test_terminal_weights_are_size_not_word_length():
    machine=bench.tile_automaton()
    assert machine.counts(2)==(0,1,2)
    assert machine.accepts(('one','one')) and machine.accepts(('two',))
    wrong=replace(machine,alphabet=(Terminal('one',1),Terminal('two',1)))
    assert wrong.counts(2)==(0,2,4)


def test_determinism_zero_size_cycles_and_dangling_symbols():
    machine=bench.tile_automaton()
    with pytest.raises(ValueError):replace(machine,transitions=machine.transitions+(machine.transitions[0],))
    with pytest.raises(ValueError):Terminal('empty',0)
    with pytest.raises(ValueError):Terminal('boolean',True)
    with pytest.raises(ValueError):replace(machine,transitions=(Transition('I','one','missing'),))
    _,grammar=bench.motzkin_models()
    with pytest.raises(ValueError,match='Zero-degree'):replace(grammar,productions=(Production('cycle','M',(Symbol('nonterminal','M'),)),))
    with pytest.raises(ValueError):replace(grammar,productions=(Production('unknown','M',(Symbol('terminal','X'),)),))
    with pytest.raises(ValueError):Symbol('eval','danger')


def test_closed_schemas_and_equation_guards():
    machine=bench.tile_automaton()
    raw=json.loads(machine.to_json());raw['proof_status']='PROVED'
    with pytest.raises(ValueError):Automaton.from_json(json.dumps(raw))
    with pytest.raises(ValueError):Automaton.from_json('{"states":[],"states":[]}')
    _,grammar=bench.motzkin_models()
    raw=json.loads(grammar.to_json());raw['productions'][0]['python']='print(1)'
    with pytest.raises(ValueError):Grammar.from_json(json.dumps(raw))
    equation=grammar.equations();equation['equations'][0]['terms'][1]['t_power']=0
    with pytest.raises(ValueError,match='Zero-degree'):equation_coefficients(equation,4)
    with pytest.raises(ValueError):machine.accepts(('unknown',))


@pytest.mark.parametrize('degree',(-1,9,True))
def test_automaton_and_coefficient_budgets(degree):
    machine=bench.tile_automaton()
    with pytest.raises(ValueError):machine.counts(degree)
    with pytest.raises(ValueError):equation_coefficients(machine.equations(),degree)


@pytest.mark.parametrize('degree',(-1,7,True))
def test_grammar_and_benchmark_preflight(degree,monkeypatch):
    _,grammar=bench.motzkin_models()
    with pytest.raises(ValueError):grammar.levels(degree)
    def forbidden(*_):raise AssertionError('Generation before preflight')
    monkeypatch.setattr(Grammar,'levels',forbidden)
    with pytest.raises(ValueError):bench.check_motzkin(bench.motzkin_models()[0],grammar,degree)


def test_source_changed_requires_reaudit(monkeypatch):
    monkeypatch.setattr(bench,'REVIEW_SHA256','0'*64)
    with pytest.raises(ValueError,match='re-audit'):bench.reference_demo()
