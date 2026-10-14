"""PP03 semantic and adversarial checks independent of source proof status."""
from dataclasses import replace
from itertools import product
import json
from pathlib import Path
import pytest
import ac.research_math as math
from ac.research_math import ClassPresentation, SourcePattern, MapContract, CountFormula, EnumerationStatement
from ac.research_math_oracle import reference_words
from ac.research_references import load_references

ROOT = Path(__file__).resolve().parents[1] / 'docs/research/pp03'

def refs():
    return load_references(ROOT/'reference_corpus_v1.json', ROOT/'source_reviews_v1.json')

def spec(family='ordinary', base=0):
    return ClassPresentation(family, base, (), (), 0, 'test-definition')

@pytest.mark.parametrize('family', math.FAMILIES)
@pytest.mark.parametrize('base', (0, 1))
def test_families_roundtrip_and_independent_members(family, base):
    s = spec(family, base)
    assert ClassPresentation.from_json(s.to_json()) == s
    assert s.includes_empty == (family != 'ordinary')
    for n in range(5):
        assert set(math.engine_words(s, n)) == set(reference_words(s, n))
    assert s.holds(()) == s.includes_empty

@pytest.mark.parametrize('base', (0, 1))
@pytest.mark.parametrize('restriction', ('avoid', 'contain'))
def test_every_small_rank_pattern_and_adjacency(base, restriction):
    for size in range(1, 4):
        for values in product(range(base, base+size), repeat=size):
            if set(values) != set(range(base, max(values)+1)):
                continue
            for adjacency in ((), tuple(range(1, size))):
                p = SourcePattern(values, base, adjacency, 'test-pattern')
                for family in math.FAMILIES:
                    s = replace(spec(family, base), **{restriction: (p,)})
                    assert ClassPresentation.from_json(s.to_json()) == s
                    assert set(math.engine_words(s, 4)) == set(reference_words(s, 4))

@pytest.mark.parametrize('change', [dict(family='inversion'), dict(value_base=True), dict(degree_offset=True), dict(definition_version='unknown'), dict(avoid=[]), dict(avoid=(SourcePattern((1,),1,(),'x'),))])
def test_bad_class_contracts(change):
    with pytest.raises(ValueError): replace(spec(), **change)

@pytest.mark.parametrize('values,base,adj', [((0,2),0,()), ((0,False),0,()), ((0,1),0,(0,)), ((0,1),0,(2,)), ((0,1),0,(1,1)), ((),0,())])
def test_bad_patterns(values, base, adj):
    with pytest.raises(ValueError): SourcePattern(values,base,adj,'x')

def test_json_closed_schema():
    raw = spec().to_json()
    for bad in ('{"family":"ordinary","family":"revised"}', raw[:-1]+',"proof_status":"formal_kernel_checked"}', raw.replace('0', 'NaN', 1)):
        with pytest.raises(ValueError): ClassPresentation.from_json(bad)

def test_typed_existing_maps():
    contract = MapContract('hat', spec(), spec('modified',1), 'inverse_hat')
    assert MapContract.from_json(contract.to_json()) == contract
    for n in range(1,5):
        outputs = {contract.apply(w) for w in math.engine_words(contract.domain,n)}
        assert outputs == set(reference_words(contract.codomain,n))
        for w in math.engine_words(contract.domain,n):
            assert contract.inverse().apply(contract.apply(w)) == w
    for change in (dict(codomain=spec('revised')), dict(inverse_primitive='hat'), dict(degree_shift=1), dict(minimum_length=0), dict(codomain=replace(spec('modified'),degree_offset=1))):
        with pytest.raises(ValueError): replace(contract,**change)
    with pytest.raises(ValueError): contract.apply(())
    restricted = replace(contract,codomain=replace(spec('modified'),avoid=(SourcePattern((0,),0,(),'x'),)))
    with pytest.raises(ValueError, match='codomain'): restricted.apply((0,))

def test_cited_reference_fixtures():
    for s in refs():
        assert EnumerationStatement.from_json(s.to_json()) == s
        result = math.evaluate(s,tuple(range(1,7)))
        assert result['status'] == 'finite_verified'
        assert result['proof_status'] == 'not_proved'
        assert result['statement']['class_spec']['citation_id']
        assert all(r['same_complete_members'] for r in result['rows'])

def test_refutations_and_backend_disagreement(monkeypatch):
    s = refs()[0]
    assert math.evaluate(replace(s,formula=CountFormula('linear',(1,1))),(1,2))['status']=='refuted'
    shifted = replace(s,class_spec=replace(s.class_spec,degree_offset=1))
    assert math.evaluate(shifted,(1,2))['status']=='refuted'
    monkeypatch.setattr(math,'engine_words',lambda *_: iter(()))
    result = math.evaluate(s,(1,2))
    assert result['status']=='validation_disagreement'
    assert result['first_tested_failure']['oracle_only']==[0]

@pytest.mark.parametrize('degrees', [(), (0,), (7,), (True,), (2,1), (1,1), (1,7)])
def test_budget_preflight(monkeypatch,degrees):
    def forbidden(*_): raise AssertionError('Enumeration before validation')
    monkeypatch.setattr(math,'engine_words',forbidden)
    with pytest.raises(ValueError): math.evaluate(refs()[0],degrees)

def test_oracle_does_not_use_engine(monkeypatch):
    import ac.generate.universes as generators
    import ac.classes.theories as predicates
    def forbidden(*_): raise AssertionError('Oracle called engine')
    monkeypatch.setattr(generators,'ascent_sequences',forbidden)
    monkeypatch.setattr(predicates,'is_ascent_sequence',forbidden)
    monkeypatch.setattr(ClassPresentation,'holds',forbidden)
    monkeypatch.setattr(SourcePattern,'compile',forbidden)
    assert len(list(reference_words(refs()[0].class_spec,4)))==4

@pytest.mark.parametrize('field,value', [('family','revised'),('degree_offset',1),('citation_id','other')])
def test_citations_cannot_authorize_changed_math(tmp_path,field,value):
    data=json.loads((ROOT/'reference_corpus_v1.json').read_text())
    data['statements'][0]['class_spec'][field]=value
    target=tmp_path/'changed.json'; target.write_text(json.dumps(data))
    with pytest.raises(ValueError,match='re-audit'): load_references(target,ROOT/'source_reviews_v1.json')

def test_review_tampering(tmp_path):
    raw=(ROOT/'source_reviews_v1.json').read_text()
    target=tmp_path/'changed.json'; target.write_text(raw.replace('Baxter','Changed'))
    with pytest.raises(ValueError): load_references(ROOT/'reference_corpus_v1.json',target)
