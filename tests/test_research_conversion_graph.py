"""Public transport and recursive-map obligations, with deliberate failures."""
from dataclasses import replace
from itertools import product
import json
import pytest

from ac.research_conversion_graph import Endpoint, ConversionGraph, PatternCorrespondence
from ac.research_conversion_audit import load_reference_graph, audit_conversion, independent_tree_contains
from ac.research_recursive_bijections import (
    to_tiles, from_tiles, tile_levels, independent_tiles, reference_specification, derivation,
)
from ac.research_math import engine_words, SourcePattern
from ac.research_fishburn import max_tree


@pytest.fixture
def graph():return load_reference_graph()


def test_graph_roundtrip_and_typed_compositions(graph):
    assert ConversionGraph.from_json(graph.to_json())==graph
    for word in ((1,),(1,1),(1,2,1,3)):
        assert graph.apply_path(('modified-to-tree','tree-to-modified'),word)==word
    assert graph.apply_path(('fibonacci-to-tiles','tiles-to-fibonacci'),(0,1,2,2,1))==(0,1,2,2,1)
    with pytest.raises(ValueError,match='Incompatible'):
        graph.apply_path(('modified-to-tree','tiles-to-fibonacci'),(1,))
    with pytest.raises(ValueError,match='domain'):
        graph.apply_path(('modified-to-tree',),(0,))


@pytest.mark.parametrize('edge',('modified-to-tree','tree-to-modified','fibonacci-to-tiles','tiles-to-fibonacci'))
def test_independent_full_conversion_audits(graph,edge):
    result=audit_conversion(graph,edge,(1,2,3,4,5,6))
    assert result['status']=='finite_verified'
    assert all(all(row['checks'].values()) for row in result['rows'])
    assert result['proof_status']=='unproved'
    assert result['overrides_applied'] is False


def test_parallel_specifications_and_two_compositions():
    spec=reference_specification()
    levels=tile_levels(6)
    for n in range(1,7):
        source=list(engine_words(spec.class_spec,n))
        target=list(independent_tiles(n))
        assert len(source)==len(target)==spec.counts(6)[n]
        assert set(levels[n])==set(target)
        images=[to_tiles(w) for w in source]
        assert len(images)==len(set(images)) and set(images)==set(target)
        for w in source:
            assert from_tiles(to_tiles(w))==w
            assert to_tiles(w).count(2)==len(w)-len(set(w))
        for tiles in target:
            assert to_tiles(from_tiles(tiles))==tiles
    worked=derivation((0,1,2,2,1))
    assert worked['target']==(1,2,2)
    assert [step['tile_size'] for step in worked['steps']]==[2,2]
    assert worked['proof_status']=='unproved'


def test_maps_do_not_use_target_oracle_or_matching_table(monkeypatch):
    import ac.research_recursive_bijections as module
    def forbidden(*_):raise AssertionError('Map enumerated target sets')
    monkeypatch.setattr(module,'independent_tiles',forbidden)
    monkeypatch.setattr(module,'tile_levels',forbidden)
    monkeypatch.setattr(module,'engine_words',forbidden,raising=False)
    assert to_tiles((0,1,2,2,1))==(1,2,2)
    assert from_tiles((1,2,2))==(0,1,2,2,1)


def test_inorder_pattern_correspondence_all_small_rank_patterns(graph):
    source=next(n for n in graph.endpoints if n.id=='modified')
    for size in range(1,4):
        for values in product(range(1,size+1),repeat=size):
            if set(values)!=set(range(1,max(values)+1)):continue
            p=SourcePattern(values,1,(),'test')
            for word in engine_words(source.word_class,4):
                from ac.core.word import ChainWord
                assert p.compile().contains(ChainWord(word))==independent_tree_contains(max_tree(word),p)


def test_shortest_inverse_and_collision_failures(graph):
    faulty=audit_conversion(graph,'fibonacci-to-tiles',(1,2,3),inverse_override=lambda _: (0,))
    assert faulty['status']=='refuted' and faulty['overrides_applied']
    assert faulty['first_tested_failure']['degree']==2
    assert not faulty['first_tested_failure']['checks']['left_composition']
    assert not faulty['first_tested_failure']['checks']['right_composition']
    collision=audit_conversion(graph,'fibonacci-to-tiles',(1,2,3),forward_override=lambda w:(1,)*len(w))
    assert collision['first_tested_failure']['degree']==2
    checks=collision['first_tested_failure']['checks']
    assert not checks['injectivity'] and not checks['surjectivity'] and not checks['statistics']
    assert collision['first_tested_failure']['transport']['failures']['collision']


def test_statistic_claim_failure_is_separate_from_bijection(graph):
    edge=graph.edges[2]
    altered=replace(edge,statistic_links=(('distinct_count','size'),))
    candidate=replace(graph,edges=tuple(altered if e.id==edge.id else e for e in graph.edges))
    report=audit_conversion(candidate,edge.id,(1,2,3))
    assert report['status']=='refuted'
    failed=report['first_tested_failure']
    assert failed['degree']==2 and failed['checks']['injectivity'] and failed['checks']['surjectivity']
    assert failed['checks']['left_composition'] and not failed['checks']['statistics']


def test_unknown_patterns_statistics_and_family_contracts(graph):
    with pytest.raises(ValueError):PatternCorrespondence(SourcePattern((1,),1,(),'x'),SourcePattern((1,1),1,(),'x'),'inorder_classical')
    with pytest.raises(ValueError):replace(graph.edges[0],degree_shift=1)
    with pytest.raises(ValueError):replace(graph.edges[0],proof_status='formal_kernel_checked')
    with pytest.raises(ValueError):replace(graph.edges[0],inverse_requirement='matching_table')
    with pytest.raises(ValueError):replace(graph,edges=(replace(graph.edges[0],inverse_edge='missing'),)+graph.edges[1:])
    with pytest.raises(ValueError):replace(graph,endpoints=(replace(graph.endpoints[0],word_class=replace(graph.endpoints[0].word_class,family='revised')),)+graph.endpoints[1:])
    bad=replace(graph.edges[0],statistic_links=(('invented','maximum'),))
    with pytest.raises(ValueError):replace(graph,edges=(bad,)+graph.edges[1:])
    with pytest.raises(ValueError):replace(graph,endpoints=graph.endpoints+(graph.endpoints[0],))


def test_closed_schemas_tree_guards_and_bad_inputs(graph):
    data=json.loads(graph.to_json());data['edges'][0]['eval']='print(1)'
    with pytest.raises(ValueError):ConversionGraph.from_json(json.dumps(data))
    with pytest.raises(ValueError):ConversionGraph.from_json('{"edges":[],"edges":[]}')
    tree=graph.endpoints[1]
    assert not tree.holds(((None,1,None),1,None)) # not strictly decreasing left
    assert not tree.holds((None,2,None)) # nonregular alphabet
    assert not tree.holds(None) # declared nonempty scope
    with pytest.raises(ValueError):from_tiles(())
    with pytest.raises(ValueError):from_tiles((True,))
    with pytest.raises(ValueError):from_tiles((3,))
    with pytest.raises(ValueError):to_tiles((0,0,0))
    with pytest.raises(ValueError):to_tiles((0,)*7)


@pytest.mark.parametrize('degrees',((),(0,),(7,),(True,),(2,1),(1,1)))
def test_audit_budget_preflight(graph,degrees,monkeypatch):
    import ac.research_conversion_audit as module
    def forbidden(*_):raise AssertionError('Enumeration before budget validation')
    monkeypatch.setattr(module,'endpoint_members',forbidden)
    with pytest.raises(ValueError):audit_conversion(graph,'fibonacci-to-tiles',degrees)


def test_reference_graph_reaudit_required(monkeypatch):
    import ac.research_conversion_audit as module
    monkeypatch.setattr(module,'GRAPH_SHA256','0'*64)
    with pytest.raises(ValueError,match='re-audit'):module.load_reference_graph()


def test_backend_disagreement_not_a_mathematical_refutation(graph,monkeypatch):
    import ac.research_conversion_audit as module
    monkeypatch.setattr(module,'engine_words',lambda *_:iter(()))
    result=audit_conversion(graph,'fibonacci-to-tiles',(1,2))
    assert result['status']=='validation_disagreement'
    assert result['first_tested_failure']['degree']==1
