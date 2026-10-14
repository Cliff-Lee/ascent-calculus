"""PP09 shared user journey, isolated jobs, status discipline and resource audit."""
from hashlib import sha256
import json
from pathlib import Path
import time
import pytest

from ac.gui.research_library_model import library_search,work_detail,import_library,inspect_reference_word,detail_text,result_text,STATUS_HELP,METHODS
from ac.gui.research_jobs import run_method,ReferenceJobs
from ac.gui.research_http import dispatch
from ac.research_resources import research_root,source_bytes

ROOT=Path(__file__).resolve().parents[1]


def test_offline_reviewed_library_and_citation_capability_journey(tmp_path):
    db=tmp_path/'absent.sqlite'
    result=library_search(database=db)
    assert len(result['records'])==11 and not result['pack_loaded'] and not db.exists()
    work=work_detail('PP-129',database=db)
    assert any(c['citation_id']=='C-PP-129-6' and 'arxiv.org' in c['url'] for c in work['citations'])
    assert 'bijection' in work['methods']
    assert 'PROVED_EXTERNAL' in detail_text(work)
    assert 'No independently checked formal artifact' in detail_text(work)
    assert {'KNOWN_PUBLISHED','CONJECTURED','VERIFIED_TO_N','PROOF_ATTEMPT','PROVED_EXTERNAL','FORMAL_KERNEL_CHECKED'}<=set(STATUS_HELP)


def test_pack_search_idempotence_and_unreviewed_not_promoted(tmp_path):
    pack=ROOT/'.local-imports/pp-ri/source-pack.zip'
    if not pack.exists():pytest.skip('Actual supplied pack is a local opt-in fixture')
    db=tmp_path/'registry.sqlite'
    first=import_library(pack,db);second=import_library(pack,db)
    assert second['status']=='already_ingested'
    records=library_search(database=db)['records']
    assert len(records)==140
    reviewed=library_search(author='Baxter',database=db)['records']
    assert any(r['id']=='PP-129' for r in reviewed)
    unknown=next(r for r in records if r['status_flags']==['CATALOGUED_UNVERIFIED'])
    detail=work_detail(unknown['id'],database=db)
    assert detail['annotation']['id']==unknown['id'] and detail['citations'][0]['inspection_status']=='CATALOGUED_UNVERIFIED'
    assert not detail['citations'][0]['claims']
    assert first['status']!='already_ingested'


@pytest.mark.parametrize('method',tuple(METHODS))
def test_reference_methods_return_actual_bounded_evidence(method):
    result=run_method(method)
    assert result['finite_validation_status']=='finite_verified'
    assert 'VERIFIED_TO_N' in result['status_flags'] and 'INDEPENDENT_FINITE_CHECK' in result['status_flags']
    assert result['tested_degrees']==METHODS[method]['degrees']
    assert result['proof_status']=='not_formally_checked' and result['universal_implementation_status']=='unproved'
    assert 'FORMAL_KERNEL_CHECKED' not in result['status_flags']
    assert len(result['provenance']['method_source_sha256'])==64
    text=result_text(result)
    assert 'Complete tested degrees' in text and 'Remaining obligations' in text


def test_failed_math_is_not_displayed_verified(monkeypatch):
    import ac.research_benchmarks as benchmark
    monkeypatch.setattr(benchmark,'run_case',lambda *_:{'status':'refuted'})
    result=run_method('counts')
    assert result['finite_validation_status']=='validation_failed'
    assert 'VERIFIED_TO_N' not in result['status_flags']
    assert 'INDEPENDENT_FINITE_CHECK' not in result['status_flags']


def test_counterexamples_and_explicit_inspector_translation():
    result=run_method('bijection')
    assert result['counterexamples'][0]['first_tested_failure']['degree']==2
    item=result['inspectable_objects'][0]
    translated=inspect_reference_word(item['word'],item['value_base'])
    assert translated['source_word']==[0,0]
    assert translated['positive_engine_word']==[1,1] and translated['inspector_input']=='1 1'
    assert inspect_reference_word([1,2],1)['positive_engine_word']==[1,2]
    with pytest.raises(ValueError):inspect_reference_word([0,True],0)
    with pytest.raises(ValueError):inspect_reference_word([0],True)


def test_spawned_reference_jobs_complete_and_cancel_responsively():
    manager=ReferenceJobs()
    try:
        key=manager.start('counts');deadline=time.monotonic()+15
        while manager.poll(key)['status']=='running' and time.monotonic()<deadline:time.sleep(.02)
        assert manager.poll(key)['status']=='completed'
        detached=manager.poll(key);detached['result']['proof_status']='fabricated'
        assert manager.poll(key)['result']['proof_status']=='not_formally_checked'
        key=manager.start('tree');started=time.monotonic();cancelled=manager.cancel(key)
        assert cancelled['status']=='cancelled' and not manager.jobs[key]['process'].is_alive()
        assert time.monotonic()-started<3
        assert manager.poll(key)['result'] is None
        with pytest.raises(ValueError):manager.start('arbitrary-code')
    finally:manager.close()


def test_single_active_job_and_unknown_job_controls():
    manager=ReferenceJobs()
    try:
        key=manager.start('language')
        with pytest.raises(ValueError):manager.start('counts')
        manager.cancel(key)
        with pytest.raises(ValueError):manager.poll('unknown')
        with pytest.raises(ValueError):manager.cancel('unknown')
    finally:manager.close()


def test_resource_payload_exact_and_small():
    payload=ROOT/'ac/research_data'
    manifest=json.loads((payload/'manifest.json').read_text())
    assert manifest['total_bytes']<400000
    for name,record in manifest['files'].items():
        original=(ROOT/name).read_bytes();packaged=(payload/'root'/name).read_bytes()
        assert original==packaged and sha256(packaged).hexdigest()==record['sha256']
        assert '..' not in name and 'private' not in name
    assert any(name.startswith('ac/gui/research_jobs') for name in manifest['files'])


def test_resource_fallback_preserves_exact_sources(monkeypatch,tmp_path):
    import ac.research_resources as resources
    monkeypatch.setattr(resources,'__file__',str(tmp_path/'ac/research_resources.py'))
    assert resources.research_root()==ROOT/'ac/research_data/root'
    assert resources.source_bytes('research_math.py')==(ROOT/'ac/research_math.py').read_bytes()
    assert resources.source_bytes('gui/research_jobs.py')==(ROOT/'ac/gui/research_jobs.py').read_bytes()


def test_query_http_and_schema_errors_are_understandable(tmp_path,monkeypatch):
    monkeypatch.setenv('ASCENT_ENGINE_DATA_DIR',str(tmp_path))
    assert dispatch('library',{'author':'Baxter'})['records']
    assert dispatch('work',{'id':'PP-129'})['display_text']
    with pytest.raises(ValueError):dispatch('start',{'method':'unknown'})
    with pytest.raises(ValueError):dispatch('library',{'database':'arbitrary.sqlite'})
    with pytest.raises(ValueError):library_search(year=True,database=tmp_path/'none')
    with pytest.raises(ValueError):library_search(query='x'*201,database=tmp_path/'none')
    with pytest.raises(ValueError):dispatch('import',{'archive_base64':'bad!notbase64'})


def test_native_browser_navigation_and_safe_text_rendering():
    html=(ROOT/'ac/gui/static/index.html').read_text();js=(ROOT/'ac/gui/static/research.js').read_text()
    assert 'aria-controls="panel-research"' in html and 'id="research-inspector-context"' in html
    assert 'textContent' in js and 'innerHTML' not in js
    desktop=(ROOT/'ac/gui/desktop.py').read_text()
    assert 'self.research_view = None' in desktop and 'multiprocessing.freeze_support()' in desktop
