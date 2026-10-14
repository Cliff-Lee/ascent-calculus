"""Specification obligations tested as objects, independently of coefficients."""
from dataclasses import replace
import json
import pytest

from ac.research_math import ClassPresentation
from ac.research_math_oracle import reference_words
from ac.research_specifications import (
    InsertionRule, RecursiveSpecification, search_fibonacci_specifications,
    replay, obligation_ledger,
)


@pytest.fixture(scope='module')
def search():
    return search_fibonacci_specifications()


@pytest.fixture
def spec(search):
    return RecursiveSpecification.from_json(json.dumps(search['survivors'][0]['specification']))


def test_search_design_failures_and_holdout(search):
    assert search['design']['candidate_count']==len(search['trials'])==16
    assert search['design']['training']==[3,4]
    assert search['design']['holdout']==[5,6]
    assert search['design']['blind_discovery'] is False
    assert len(search['survivors'])==1
    assert sum(t['training_status']=='refuted' for t in search['trials'])==15
    assert all(t['first_training_failure'] for t in search['trials'] if t['training_status']=='refuted')
    surviving=next(t for t in search['trials'] if t['training_status']=='finite_verified')
    assert surviving['anchors']==['after_first_max','after_first_max']
    assert surviving['holdout']['tested_degrees']==[5,6]
    assert search['proof_status']=='unproved'


def test_roundtrip_reconstruction_and_independent_complete_sets(spec):
    assert RecursiveSpecification.from_json(spec.to_json())==spec
    assert spec.counts(6)==(0,1,2,3,5,8,13)
    levels=spec.levels(6)
    for n in range(1,7):
        assert len(levels[n])==len(set(levels[n]))
        assert set(levels[n])==set(reference_words(spec.class_spec,n))
        for word in levels[n]:
            if word in spec.atoms:
                continue
            branches=[(r,r.decompose(word)) for r in spec.rules if r.decompose(word) is not None]
            assert len(branches)==1
            rule,parent=branches[0]
            assert rule.construct(parent)==word
            assert len(parent)<len(word)
    assert replay(spec,(1,2,3,4,5,6))['status']=='finite_verified'


def test_readable_equations_and_unproved_obligations(spec):
    description=spec.describe()
    assert 'A_ge_2(t)' in description['equation']
    assert description['rules'][0]['size_shift']==1
    evidence=replay(spec,(3,4))
    ledger=obligation_ledger(spec,evidence)
    assert len(ledger)==7
    assert all(row['status']=='unproved' for row in ledger)
    structure=next(r for r in ledger if r['id']=='structure')
    assert structure['finite_check_status']=='not_tested'
    assert structure['finite_degrees']==[]
    with pytest.raises(ValueError): obligation_ledger(replace(spec,atoms=spec.atoms[:1]),evidence)


def test_equal_counts_do_not_authorize_specification(spec):
    bad_rules=tuple(replace(r,anchor='prepend') for r in spec.rules)
    bad=replace(spec,rules=bad_rules)
    assert bad.counts(6)==spec.counts(6)
    evidence=replay(bad,(3,4,5,6))
    assert evidence['status']=='refuted'
    assert 'invalid_output' in evidence['first_tested_failure']['failures']
    assert 'missing_object' in evidence['first_tested_failure']['failures']


def test_partition_collision_missing_atoms_and_inverse_guards(spec):
    duplicate=replace(spec,rules=spec.rules+(replace(spec.rules[0],id='duplicate-rule'),))
    result=replay(duplicate,(3,4))
    assert 'overlap_or_duplicate' in result['first_tested_failure']['failures']
    assert 'decomposition_partition' in result['first_tested_failure']['failures']
    missing=replace(spec,atoms=((0,),))
    assert 'missing_object' in replay(missing,(1,2,3))['first_tested_failure']['failures']
    rule=spec.rules[1]
    assert rule.decompose((0,1,0,1)) is None
    assert rule.decompose((0,1,1))==(0,)
    assert rule.construct((0,))==(0,1,1)


def test_finite_checker_detects_engine_oracle_disagreement(spec,monkeypatch):
    import ac.research_specifications as module
    monkeypatch.setattr(module,'engine_words',lambda *_:iter(()))
    assert replay(spec,(3,))['status']=='validation_disagreement'


@pytest.mark.parametrize('change', [dict(anchor='eval'),dict(copies=0),dict(copies=True),dict(minimum_parent_degree=0)])
def test_bad_rules(change):
    with pytest.raises(ValueError): replace(InsertionRule('r','append',1,1),**change)


@pytest.mark.parametrize('degrees', [(),(0,),(7,),(True,),(2,1),(1,1)])
def test_degree_preflight(spec,degrees,monkeypatch):
    def forbidden(*_): raise AssertionError('Enumeration before preflight')
    monkeypatch.setattr(RecursiveSpecification,'levels',forbidden)
    with pytest.raises(ValueError): replay(spec,degrees)


def test_closed_schema_family_and_serialization_guards(spec):
    data=json.loads(spec.to_json());data['proof_status']='formal_kernel_checked'
    with pytest.raises(ValueError): RecursiveSpecification.from_json(json.dumps(data))
    with pytest.raises(ValueError): RecursiveSpecification.from_json('{"rules":[],"rules":[]}')
    with pytest.raises(ValueError): replace(spec,class_spec=replace(spec.class_spec,value_base=1,avoid=(),contain=()))
    with pytest.raises(ValueError): replace(spec,class_spec=replace(spec.class_spec,degree_offset=1))
    with pytest.raises(ValueError): replace(spec,atoms=((1,),))
    with pytest.raises(ValueError): replace(spec,atoms=spec.atoms+(spec.atoms[0],))
    with pytest.raises(ValueError): spec.rules[0].construct(())
    with pytest.raises(ValueError): spec.rules[0].construct((0,)*6)
    with pytest.raises(ValueError): spec.rules[0].decompose([0,1])


def test_reusable_constructor_on_a_different_ordinary_class(spec):
    ordinary=ClassPresentation('ordinary',0,(),(),0,'example')
    other=replace(spec,class_spec=ordinary)
    result=replay(other,(3,4))
    assert result['status']=='refuted'
    assert result['first_tested_failure']['failures']['missing_object']
    # Meaningful constructions are replayed against the new class, not looked up.
    assert other.rules[0].construct((0,0))==(0,1,0)
