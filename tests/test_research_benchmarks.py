"""Permanent PP04 positive, adversarial, execution and resume benchmarks."""
from itertools import product
import json
from math import factorial
import os
import shutil
import subprocess

import pytest
import ac.research_benchmarks as bench
import ac.research_benchmark_runner as runner
from ac.research_inversions import InversionClass, testart_coefficients as reference_coefficients
from ac.research_fishburn import max_tree, inorder, tree_statistics, fishburn_coefficients
from ac.research_math import SourcePattern
from ac.research_benchmark_oracles import inversion_201_210, fishburn_trees

CASES = [(r['id'],n) for r in bench.load_catalog()['records'] for n in r['quick_degrees']]


@pytest.mark.parametrize('case,degree', CASES)
def test_quick_published_benchmarks(case,degree):
    result = bench.run_case(case,degree)
    assert result['status'] == 'finite_verified'
    assert result['proof_status'] == 'not_proved'
    assert all(result['checks'].values())
    assert result['citation_ids'] and result['source_theorem_id']


def test_distinct_source_verified_families():
    records = bench.load_catalog()['records']
    assert {r['family'] for r in records} == {
        'ordinary_pair_avoidance', 'inversion_sequences', 'fishburn_tree_transport'}
    assert all(r['runtime_seconds']['quick'] <= 10 for r in records)
    assert all(max(r['quick_degrees']) < max(r['deep_degrees']) < 11 for r in records)


def test_false_recurrence_fit_and_off_by_one():
    # n! agrees through degree four, but its tempting recurrence is false here.
    counts = reference_coefficients(7)
    assert counts[:5] == tuple(factorial(n) for n in range(5))
    assert counts[5] == len(list(inversion_201_210(5))) == 116 != factorial(5)
    assert counts[1] != len(list(inversion_201_210(2)))
    assert fishburn_coefficients(6) == (1,1,2,5,15,53,217)


def test_inversion_equality_and_family_semantics():
    avoid_equal = InversionClass((SourcePattern((0,0),0,(),'test'),))
    assert list(avoid_equal.words(2)) == [(0,1)]
    # Valid inversion words need not be Cayley or ascent sequences.
    assert (0,0,2) in set(InversionClass(()).words(3))
    assert (0,0,2,1,1) in set(inversion_201_210(5))
    assert (0,0,0,3) in set(InversionClass(()).words(4))
    with pytest.raises(ValueError):
        InversionClass((SourcePattern((1,),1,(),'wrong-base'),))
    with pytest.raises(ValueError):
        InversionClass((SourcePattern((0,1),0,(1,),'vincular'),))


def test_complete_oracle_and_inverse_on_all_small_endofunctions():
    for n in range(5):
        for word in product(range(1,n+1),repeat=n):
            assert inorder(max_tree(word)) == word
    trees = list(fishburn_trees(3))
    assert len(trees) == len(set(trees)) == 5
    for tree in trees:
        assert max_tree(inorder(tree)) == tree
    # Repeated maxima must split at the leftmost copy, not the rightmost.
    assert max_tree((1,1)) == (None,1,(None,1,None))
    with pytest.raises(ValueError): max_tree((0,))


def test_independent_oracles_do_not_call_production(monkeypatch):
    def forbidden(*_): raise AssertionError('Oracle reused production logic')
    monkeypatch.setattr(InversionClass,'words',forbidden)
    monkeypatch.setattr(SourcePattern,'compile',forbidden)
    import ac.research_fishburn as trees
    monkeypatch.setattr(trees,'max_tree',forbidden)
    monkeypatch.setattr(trees,'inorder',forbidden)
    monkeypatch.setattr(trees,'tree_statistics',forbidden)
    assert len(list(inversion_201_210(5))) == 116
    assert len(list(fishburn_trees(4))) == 15


def test_incomplete_equal_count_and_duplicate_generators():
    assert not bench.compare_members([(1,)],[(2,)])['same_complete_members']
    result = bench.compare_members([(1,),(1,)],[(1,)])
    assert not result['same_complete_members'] and result['production_duplicates']==1
    missing = bench.compare_members([],[(1,)])
    assert missing['oracle_only'] == (1,)


def test_inverse_statistic_collision_and_membership_failures():
    words = [(1,1),(1,2)]
    trees = [max_tree(w) for w in words]
    good = bench.check_transport(words,trees,max_tree,inorder,bench.word_statistics,tree_statistics)
    assert good['passed']
    bad_inverse = bench.check_transport(words,trees,max_tree,lambda _: (1,1),bench.word_statistics,tree_statistics)
    assert {'left_inverse','right_inverse'} <= set(bad_inverse['failures'])
    bad_stat = bench.check_transport(words,trees,max_tree,inorder,lambda _: 99,tree_statistics)
    assert 'statistic' in bad_stat['failures']
    constant = bench.check_transport(words,trees,lambda _: trees[0],inorder,bench.word_statistics,tree_statistics)
    assert {'collision','surjectivity'} <= set(constant['failures'])
    wrong_target = bench.check_transport(words,trees,lambda _: None,inorder,bench.word_statistics,tree_statistics)
    assert 'target_membership' in wrong_target['failures']


@pytest.mark.parametrize('case,degree', [('unknown',1),('fishburn-inorder',7),('testart-201-210',True),('PP129-P5',0)])
def test_budgets_and_scope(case,degree):
    with pytest.raises(ValueError): bench.run_case(case,degree)


def test_reference_corruption_rejected(tmp_path):
    for name in ('benchmarks_v1.json','source_reviews_v1.json'):
        shutil.copy(bench.DATA/name,tmp_path/name)
    path = tmp_path/'benchmarks_v1.json'
    data = json.loads(path.read_text())
    data['records'][0]['degree_offset'] = 1
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError,match='re-audit'): bench.load_catalog(tmp_path)


def test_quick_subprocess_execution():
    result = runner.run_suite()
    assert result['complete'] and len(result['results'])==21
    assert result['resumed_cases']==0 and result['proof_status']=='not_proved'


def test_checkpoint_resume_interruption_and_corruption(tmp_path,monkeypatch):
    calls = []
    def interrupted(case,n,timeout):
        calls.append((case,n))
        if len(calls)>3: raise RuntimeError('Simulated interruption')
        return bench.run_case(case,n)
    monkeypatch.setattr(runner,'execute_cell',interrupted)
    with pytest.raises(RuntimeError): runner.run_suite(checkpoint=tmp_path)
    monkeypatch.setattr(runner,'execute_cell',lambda case,n,timeout: bench.run_case(case,n))
    resumed = runner.run_suite(checkpoint=tmp_path)
    assert resumed['complete'] and resumed['resumed_cases']==3
    def forbidden(*_): raise AssertionError('Successful checkpoint recomputed')
    monkeypatch.setattr(runner,'execute_cell',forbidden)
    assert runner.run_suite(workers=2,checkpoint=tmp_path)['resumed_cases']==21
    path = tmp_path/'PP129-P5-1.json'
    data=json.loads(path.read_text()); data['attempts'][0]['status']='refuted'
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError,match='checksum'): runner.run_suite(checkpoint=tmp_path)


def test_timeout_kills_worker_and_is_not_passed(monkeypatch,tmp_path):
    def timeout(*args,**kwargs): raise subprocess.TimeoutExpired(args[0],kwargs['timeout'])
    monkeypatch.setattr(subprocess,'run',timeout)
    failed = runner.run_suite(checkpoint=tmp_path)
    assert not failed['complete']
    assert all(r['status']=='budget_exhausted' for r in failed['results'])
    monkeypatch.setattr(runner,'execute_cell',lambda case,n,timeout: bench.run_case(case,n))
    assert runner.run_suite(checkpoint=tmp_path)['complete']
    data=json.loads((tmp_path/'PP129-P5-1.json').read_text())
    assert len(data['attempts'])==2
    assert data['attempts'][0]['status']=='budget_exhausted'


def test_stale_profile_and_source_checkpoints(tmp_path,monkeypatch):
    monkeypatch.setattr(runner,'execute_cell',lambda case,n,timeout: bench.run_case(case,n))
    runner.run_suite(checkpoint=tmp_path)
    with pytest.raises(ValueError,match='Stale'): runner.run_suite(profile='deep',checkpoint=tmp_path)
    monkeypatch.setattr(runner,'implementation_fingerprint',lambda: 'changed')
    with pytest.raises(ValueError,match='Stale'): runner.run_suite(checkpoint=tmp_path)


@pytest.mark.skipif(os.environ.get('PP_RI_DEEP') != '1', reason='Explicit opt-in deep benchmark')
def test_deep_published_benchmarks():
    result = runner.run_suite('deep',workers=2)
    assert result['complete'] and len(result['results'])==32


def test_real_subprocess_deadline():
    result = runner.execute_cell('fishburn-inorder',6,0.001)
    assert result['status']=='budget_exhausted'
    assert result['proof_status']=='not_proved'
