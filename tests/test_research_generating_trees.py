"""Published-tree replay, coarse-state refutation and independent edge audits."""
from collections import Counter
from dataclasses import replace
import json
import pytest

import ac.research_generating_trees as trees
from ac.research_inversions import InversionClass
from ac.research_math import SourcePattern
from ac.research_growth_oracle import words, parent


def strategy(side='left',patterns=((2,0,1),(2,1,0))):
    return trees.GrowthStrategy(InversionClass(tuple(SourcePattern(p,0,(),'test') for p in patterns)),side)


@pytest.fixture(scope='module')
def demo():
    return trees.reference_demo(6)


@pytest.mark.parametrize('side',('left','right'))
def test_typed_strategy_roundtrip_and_independent_edges(side):
    s=strategy(side)
    assert trees.GrowthStrategy.from_json(s.to_json())==s
    explored=trees.explore(s,6)
    assert explored['audit']['status']=='finite_verified'
    for n in range(6):
        targets=tuple(words(((2,0,1),(2,1,0)),n+1))
        for word in explored['levels'][n]:
            expected={c for c in targets if parent(c,side)==word}
            assert set(s.children(word))==expected
        row=explored['audit']['rows'][n]
        assert row['duplicate_edges']==0
        assert row['reachable_count']==row['target_count']


def test_published_rule_reconstructed_and_counted(demo):
    replay=demo['sides']['left']['published_replay']
    assert replay['formula_matches_observed_states']
    assert replay['counts_match']
    assert replay['counts']==(1,1,2,6,24,116,632)
    assert replay['proof_status']=='unproved'
    assert len(replay['unproved_obligations'])==3
    assert demo['citation_ids'] and demo['review_sha256']
    table=replay['inference']
    # State 3 has label 1 once, label 2 four times, label 3 twice, label 4 once.
    row=next(r for r in table['table'] if r['state']==(3,))
    assert dict(row['children'])=={(1,):1,(2,):4,(3,):2,(4,):1}
    assert sum(trees.published_transitions(3).values())==8


def test_false_labels_minimal_witnesses_and_holdout(demo):
    left=demo['sides']['left']
    assert ['published_s'] in [r['label'] for r in left['minimal_labels_within_grammar']]
    assert ['leading_zeros','published_s'] not in [r['label'] for r in left['minimal_labels_within_grammar']]
    zeros=next(t for t in left['label_trials'] if t['label']==['zero_count'])
    assert zeros['training']['status']=='finite_verified'
    assert zeros['training_plus_holdout']['status']=='refuted'
    witness=zeros['training_plus_holdout']['shortest_tested_witness']
    assert witness['maximum_parent_degree']==4
    assert witness['word_a']==(0,0,0) and witness['word_b']==(0,1,0,0)
    s=trees.LabelSchema(('zero_count',));growth=strategy()
    assert s.state(witness['word_a'])==s.state(witness['word_b'])
    assert Counter(s.state(c) for c in growth.children(witness['word_a'])) != Counter(s.state(c) for c in growth.children(witness['word_b']))
    assert demo['sides']['right']['minimal_labels_within_grammar']==[]


def test_frontier_and_false_proof_transitions_refused(demo):
    full=demo['sides']['left']['published_replay']['inference']
    with pytest.raises(ValueError,match='Unexpanded'):
        trees.table_counts(full,(0,),7)
    bad={**full,'proof_status':'PROVED'}
    with pytest.raises(ValueError,match='PROVED'): trees.table_counts(bad,(0,),4)
    refuted=demo['sides']['left']['label_trials'][0]['training']
    with pytest.raises(ValueError): trees.table_counts(refuted,(),3)


def test_duplicate_child_state_and_zero_multiplicity_rejected(demo):
    full=json.loads(json.dumps(demo['sides']['left']['published_replay']['inference']))
    full['table'][0]['children'] += full['table'][0]['children']
    with pytest.raises(ValueError,match='Duplicate'): trees.table_counts(full,(0,),1)
    full=json.loads(json.dumps(demo['sides']['left']['published_replay']['inference']))
    full['table'][0]['children'][0][1]=0
    with pytest.raises(ValueError,match='multiplicity'): trees.table_counts(full,(0,),1)


def test_left_avoidance_subtree_can_be_disconnected():
    # Testart Section 2: valid child 0021 has forbidden parent 010.
    result=trees.explore(strategy('left',((0,1,0),)),4)
    assert result['audit']['status']=='refuted'
    assert parent((0,0,2,1),'left')==(0,1,0)
    assert (0,0,2,1) in set(words(((0,1,0),),4))
    assert (0,1,0) not in set(words(((0,1,0),),3))
    assert result['audit']['rows'][3]['orphan'] is not None
    assert result['audit']['rows'][3]['missing_reachable'] is not None


def test_incomplete_production_edge_checker_detects_loss(monkeypatch):
    original=trees.GrowthStrategy.children
    monkeypatch.setattr(trees.GrowthStrategy,'children',lambda self,w:original(self,w)[:-1])
    result=trees.explore(strategy(),3)
    assert result['audit']['status']=='refuted'
    assert result['audit']['rows'][0]['omitted_edge'] is not None


def test_oracle_uses_no_production_engine(monkeypatch):
    def forbidden(*_): raise AssertionError('Oracle called production')
    monkeypatch.setattr(InversionClass,'words',forbidden)
    monkeypatch.setattr(SourcePattern,'compile',forbidden)
    monkeypatch.setattr(trees.GrowthStrategy,'children',forbidden)
    assert len(list(words(((2,0,1),(2,1,0)),5)))==116
    assert parent((0,1,0),'left')==(0,0)


@pytest.mark.parametrize('features',[('untrusted',),('last','last'),['last']])
def test_bad_labels(features):
    with pytest.raises(ValueError): trees.LabelSchema(features)


def test_closed_serialization_and_wrong_family():
    label=trees.LabelSchema(('leading_zeros','nonleading_zero_flag'))
    assert trees.LabelSchema.from_json(label.to_json())==label
    with pytest.raises(ValueError): trees.LabelSchema.from_json('{"features":[],"features":[]}')
    with pytest.raises(ValueError): trees.GrowthStrategy.from_json('{"schema_version":1,"side":"left","patterns":[],"proof":"PROVED"}')
    with pytest.raises(ValueError): trees.GrowthStrategy('modified','left')
    with pytest.raises(ValueError): replace(strategy(),side='hat')
    with pytest.raises(ValueError): strategy().children((0,)*7)
    with pytest.raises(ValueError): strategy().children((0,2))


@pytest.mark.parametrize('through',(0,8,True))
def test_budget_preflight(through,monkeypatch):
    def forbidden(*_): raise AssertionError('Oracle before budget validation')
    monkeypatch.setattr(trees,'oracle_words',forbidden)
    with pytest.raises(ValueError): trees.explore(strategy(),through)


def test_inference_parent_degree_guards():
    exploration=trees.explore(strategy(),3)
    for degrees in ((),(3,),(True,),(1,0),(0,0)):
        with pytest.raises(ValueError): trees.infer_labels(exploration,trees.LabelSchema(()),degrees)


def test_source_binding_changed_refused(monkeypatch):
    monkeypatch.setattr(trees,'REVIEW_SHA256','0'*64)
    with pytest.raises(ValueError,match='re-audit'): trees.reference_demo(5)
