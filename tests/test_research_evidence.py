from copy import deepcopy
import json
from pathlib import Path
import pytest
from ac.research_evidence import load_review,save_review,ReviewBundle
from ac.research_library import CatalogueError,Catalogue,ingest_pack

CARDS=Path(__file__).resolve().parents[1]/'docs/research/pp02/source_cards_v1.json'


def raw():return json.loads(CARDS.read_text())


def change(kind,key,value):
    obj=raw()
    next(e for e in obj['entities'] if e['kind']==kind)['data'][key]=value
    return obj


def test_all_entity_types_roundtrip_and_cards_detached():
    bundle=load_review(CARDS)
    assert len(bundle.method_cards())==11
    assert {type(e).__name__ for e in bundle.entities()}=={'Work','Source','Citation','SourceLocation','Evidence','Claim','Definition','Theorem','Algorithm'}
    assert ReviewBundle.from_json(bundle.to_json()).to_json()==bundle.to_json()
    cards=bundle.method_cards();cards[0]['assumptions']='mutated'
    assert bundle.method_cards()[0]['assumptions']!='mutated'
    assert len(bundle.entities('Theorem'))==3
    assert all(t.proof_status=='PROVED_EXTERNAL' for t in bundle.entities('Theorem'))


@pytest.mark.parametrize('kind,key,value',[
 ('Citation','location_id','missing'),('Citation','work_id','missing'),
 ('SourceLocation','source_id','W-PP-129'),('Evidence','source_id','missing'),
 ('Theorem','citation_ids',[]),('Theorem','evidence_ids',[]),
 ('Theorem','evidence_ids',['E-PP-031']),('Theorem','assumptions',[]),
 ('Theorem','proof_status','formal_kernel_checked'),('Theorem','proof_status','VERIFIED_TO_11'),
 ('Source','inspection_status','PROVED'),('Source','content_sha256','abc'),
 ('Work','year',True),('Work','pack_sha256','missing'),('Work','authors','not a tuple'),
 ('Source','url','file:///etc/passwd'),
])
def test_invalid_links_types_statuses_and_missing_hypotheses(kind,key,value):
    with pytest.raises(ValueError):ReviewBundle.from_json(json.dumps(change(kind,key,value)))


def test_abstract_cannot_be_external_proof():
    obj=raw();next(e for e in obj['entities'] if e['kind']=='Source')['data']['medium']='extended_abstract'
    with pytest.raises(CatalogueError,match='External proof'):ReviewBundle.from_json(json.dumps(obj))


def test_duplicate_unknown_fields_and_schema_version_refused():
    for mutate in (lambda o:o['entities'].append(o['entities'][0]),
                   lambda o:o['entities'][0]['data'].update(trusted=True),
                   lambda o:o.update(schema_version=True),
                   lambda o:o['method_cards'][0].update(guaranteed_proof=True),
                   lambda o:o['method_cards'][0].update(source_ids=['S-PP-031'])):
        obj=raw();mutate(obj)
        with pytest.raises(ValueError):ReviewBundle.from_json(json.dumps(obj))
    with pytest.raises(CatalogueError):ReviewBundle.from_json(CARDS.read_text().replace('"schema_version": 1','"schema_version": 1,"schema_version": 1'))


def test_atomic_exclusive_snapshot_and_bounded_read(tmp_path):
    bundle=load_review(CARDS);p=tmp_path/'review.json'
    save_review(p,bundle);assert load_review(p).fingerprint==bundle.fingerprint
    before=p.read_bytes()
    with pytest.raises(FileExistsError):save_review(p,bundle)
    assert p.read_bytes()==before
    large=tmp_path/'large';large.write_bytes(b' '*1_000_001)
    with pytest.raises(CatalogueError):load_review(large)


def test_blockers_and_licences_not_fabricated():
    bundle=load_review(CARDS)
    assert bundle.method_cards('W-PP-094')[0]['construction']=='Not extracted'
    assert any(s.inspection_status=='INACCESSIBLE' for s in bundle.entities('Source'))
    licences=[s for s in bundle.entities('Source') if s.medium=='licence']
    assert len(licences)==2 and all(s.content_sha256 and s.rights_note=='BSD-3-Clause' for s in licences)
    assert all('No' in c['complexity'] or c['complexity']=='Not extracted' or 'not independently audited' in c['complexity'] for c in bundle.method_cards())


def test_load_does_not_retrieve_or_execute_sources(monkeypatch):
    import socket,subprocess
    def forbidden(*args,**kwargs):raise AssertionError('Unexpected side effect')
    monkeypatch.setattr(socket,'socket',forbidden)
    monkeypatch.setattr(subprocess,'run',forbidden)
    assert load_review(CARDS).method_cards()


def test_catalogue_link_check_refuses_missing_or_wrong_pack():
    class Missing:
        def search(self,**kwargs):return []
    with pytest.raises(CatalogueError,match='lead/pack'):load_review(CARDS).check_catalogue(Missing())


def test_extra_citation_needs_its_own_evidence():
    obj=raw();next(e for e in obj['entities'] if e['kind']=='Theorem')['data']['citation_ids'].append('C-PP-129')
    # First theorem already cites PP-129; add a genuinely different source.
    next(e for e in obj['entities'] if e['kind']=='Theorem')['data']['citation_ids'].append('C-PP-031')
    with pytest.raises(CatalogueError):ReviewBundle.from_json(json.dumps(obj))
