"""Shared offline library, citation and bounded method-explorer contracts.

No Tk import, provider calls, user-state migration or proof promotion occurs.
"""
from pathlib import Path
from ac.research_resources import research_root

METHODS={
 'counts':{'title':'Pair-avoidance benchmark','lead':'PP-129','stage':'PP04','capability':'Exact complete-class counts and independent oracle','degrees':[1,2,3,4]},
 'specification':{'title':'Recursive specification','lead':'PP-129','stage':'PP05','capability':'Constructors, inverse replay and proof obligations','degrees':[1,2,3,4,5,6]},
 'tree':{'title':'Generating-tree labels','lead':'PP-066','stage':'PP06','capability':'Left/right edges, state labels and counterexamples','degrees':[0,1,2,3,4,5]},
 'transport':{'title':'Fishburn representation','lead':'PP-047','stage':'PP07','capability':'Forward/inverse tree encoding and statistics','degrees':[1,2,3,4]},
 'bijection':{'title':'Recursive bijection to tilings','lead':'PP-129','stage':'PP07','capability':'Two compositions, coverage and statistic checks','degrees':[1,2,3,4]},
 'language':{'title':'Language and grammar equations','lead':'PP-129','stage':'PP08','capability':'Regular/counter separation and exact coefficients','degrees':[0,1,2,3,4,5,6]},
}
STATUS_HELP={
 'KNOWN_PUBLISHED':'A publication/source locator is known; mathematical verification is separate.',
 'CONJECTURED':'A proposed construction or claim still has universal obligations.',
 'VERIFIED_TO_N':'Finite coverage only; exact tested degrees and implementations are shown.',
 'PROOF_ATTEMPT':'A proof attempt has open obligations.',
 'PROVED_EXTERNAL':'An external statement and displayed argument were inspected; no kernel check implied.',
 'FORMAL_KERNEL_CHECKED':'Requires a precise theorem, dependency/axiom audit and recorded verifier artifact.',
 'INDEPENDENT_FINITE_CHECK':'Separately implemented finite objects/checks agree; this is not a proof.',
}


def database_path():
    from ac.gui.research_state import state_path
    return state_path().parent/'pp-research-library.sqlite'


def reviewed_library():
    from ac.research_evidence import load_review
    bundles={name:load_review(research_root()/'docs/research'/name/'source_reviews_v1.json') for name in ('pp03','pp04','pp06','pp08')}
    return bundles


def library_search(query='',author='',year=None,priority=None,method='',family='',relevance='',database=None):
    if any(type(x) is not str or len(x)>200 for x in (query,author,method,family,relevance)):
        raise ValueError('Search text must be at most 200 characters')
    if year is not None and (type(year) is not int or not 1900<=year<=2100):raise ValueError('Year must be 1900..2100')
    if priority not in (None,'P0','P1','P2'):raise ValueError('Choose P0, P1 or P2')
    bundles=reviewed_library();base=bundles['pp03']
    work_by_lead={w.lead_id:w for w in base.entities('Work')}
    db=Path(database) if database is not None else database_path()
    if db.exists():
        from ac.research_library import Catalogue
        items=Catalogue(db).search(query=query or None,author=author or None,year=year,priority=priority,
                                   method=method or None,family=family or None,relevance=relevance or None,limit=200)
        records=[r['original'] for r in items]
    else:
        # Reviewed works remain usable before a local pack is explicitly imported.
        records=[{'id':w.lead_id,'title':w.title,'authors':', '.join(w.authors),'year':w.year,'priority':'P0','proposed_module':base.method_cards(w.id)[0]['implementation_idea'] if base.method_cards(w.id) else '', 'relevance':'Reviewed reference source','source_type':'reviewed_work'} for w in work_by_lead.values()]
        terms=(query,author,method,family,relevance)
        selected=[]
        for record in records:
            searchable=(str(record),record['authors'],record['proposed_module'],str(record),record['relevance'])
            if all(not term or term.casefold() in value.casefold() for term,value in zip(terms,searchable)) and (year is None or record['year']==year) and (priority is None or record['priority']==priority):selected.append(record)
        records=selected
    rows=[]
    for r in records:
        reviewed=r['id'] in work_by_lead
        rows.append({'id':r['id'],'title':r['title'],'authors':r['authors'],'year':r['year'],'priority':r['priority'],
                     'status_flags':['KNOWN_PUBLISHED','SOURCE_REVIEW_AVAILABLE'] if reviewed else ['CATALOGUED_UNVERIFIED'],
                     'methods':[key for key,value in METHODS.items() if value['lead']==r['id']]})
    return {'records':rows,'pack_loaded':db.exists(),'available_count':len(rows),'status_help':STATUS_HELP,
            'notice':'Import a conference pack to search all 140 annotations. Reviewed works and reference methods are available offline.' if not db.exists() else 'Imported annotations are literature leads; source reviews and finite evidence remain separate.'}


def work_detail(lead_id,database=None):
    if type(lead_id) is not str:raise ValueError('Work ID required')
    row=next((r for r in library_search(database=database)['records'] if r['id']==lead_id),None)
    if row is None:raise ValueError('Work not found in this local library')
    reviews=[];cards=[]
    for stage,bundle in reviewed_library().items():
        work=next((w for w in bundle.entities('Work') if w.lead_id==lead_id),None)
        if work is None:continue
        sources={s.id:s for s in bundle.entities('Source')};locations={s.id:s for s in bundle.entities('SourceLocation')}
        for cite in bundle.entities('Citation'):
            if cite.work_id!=work.id:continue
            loc=locations[cite.location_id];source=sources[loc.source_id]
            claims=[{'statement':c.statement,'assumptions':list(c.assumptions),'proof_status':c.proof_status,'indexing':c.indexing} for kind in ('Theorem','Claim','Definition','Algorithm') for c in bundle.entities(kind) if cite.id in c.citation_ids]
            reviews.append({'citation_id':cite.id,'url':source.url,'location':loc.label,'source_version':source.version,
                            'inspection_status':source.inspection_status,'claims':claims,'review_stage':stage,'review_sha256':bundle.fingerprint})
        cards += [{**c,'review_stage':stage} for c in bundle.method_cards(work.id)]
    db=Path(database) if database is not None else database_path()
    annotation=None
    if db.exists():
        from ac.research_library import Catalogue
        annotation=Catalogue(db).search(record_id=lead_id,limit=1)[0]['original']
        if not reviews:
            reviews.append({'citation_id':'CATALOGUE-'+lead_id,'url':annotation['url'],'location':'Annotated literature lead; exact theorem not reviewed',
                            'source_version':'Imported conference pack','inspection_status':'CATALOGUED_UNVERIFIED','claims':[],
                            'review_stage':'pp01','review_sha256':None})
    return {**row,'annotation':annotation,'citations':reviews,'method_cards':cards,
            'capabilities':[{**METHODS[k],'id':k} for k in row['methods']],
            'formal_proof_status':'No independently checked formal artifact is attached to these reference runs.'}


def import_library(archive,database=None):
    from ac.research_library import ingest_pack
    db=Path(database) if database is not None else database_path()
    db.parent.mkdir(parents=True,exist_ok=True)
    return ingest_pack(archive,db)


def inspect_reference_word(word,value_base):
    if type(word) is not list or not word or len(word)>6 or value_base not in (0,1) or type(value_base) is not int:
        raise ValueError('A nonempty bounded source word and explicit value base are required')
    if any(type(v) is not int or v<value_base for v in word):raise ValueError('Invalid source word')
    positive=[v+1-value_base for v in word]
    return {'source_word':word,'source_value_base':value_base,'positive_engine_word':positive,
            'conversion':'add 1 to each source value' if value_base==0 else 'identity',
            'inspector_input':' '.join(map(str,positive))}


def detail_text(detail):
    lines=[detail['title'],f"{detail['authors']} · {detail['year']} · {detail['id']} · {detail['priority']}",
           'Publication/source flags: '+', '.join(detail['status_flags']),detail['formal_proof_status'],'', 'Exact citations and source reviews:']
    for c in detail['citations']:
        lines += [f"{c['review_stage']} / {c['citation_id']} · {c['inspection_status']}",c['location'],c['url'],f"Version: {c['source_version']}"]
        for claim in c['claims']:
            lines += [f"Source claim status: {claim['proof_status']}",claim['statement'],'Hypotheses: '+'; '.join(claim['assumptions']),'Indexing: '+claim['indexing']]
        lines.append('')
    lines += ['Mapped software capabilities:']+[c['title']+' — '+c['capability'] for c in detail['capabilities']]
    lines += ['','Method cards:']
    for card in detail['method_cards']:
        lines += [card['problem_family'],'Method: '+card['construction'],'Proof mechanism: '+card['proof_mechanism'],'Adaptation risks: '+card['adaptation_risks'],'Blockers: '+card['blockers']]
    return '\n'.join(lines)


def result_text(result):
    import json
    return '\n'.join([result['title'],'Finite validation: '+result['finite_validation_status'],
        'Status flags: '+', '.join(result['status_flags']),'Complete tested degrees: '+str(result['tested_degrees']),
        'Source work: '+result['source_work'],'Formal proof: '+result['proof_status'],
        'Universal implementation: '+result['universal_implementation_status'],result['notice'],
        '\nGenerated structure / derivation:',json.dumps(result['generated_structure'],indent=2),
        '\nIndependent mathematical evidence:',json.dumps(result['evidence'],indent=2),
        '\nCounterexamples / failed attempts:',json.dumps(result['counterexamples'],indent=2),
        '\nRemaining obligations:',json.dumps(result['obligations'],indent=2)])
