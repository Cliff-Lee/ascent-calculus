"""Small local HTTP dispatch shared with the native library/method explorer."""
from ac.gui.research_library_model import library_search,work_detail,inspect_reference_word,import_library,detail_text,result_text
from ac.gui.research_jobs import jobs


def dispatch(path,body):
    if type(body) is not dict:raise ValueError('Research request must be an object')
    if path=='library':
        allowed={'query','author','year','priority','method','family','relevance'}
        if not set(body)<=allowed:raise ValueError('Unknown search field')
        return library_search(**body)
    schemas={'work':{'id'},'start':{'method'},'job':{'id'},'cancel':{'id'},'inspect':{'word','value_base'},'import':{'archive_base64'}}
    if path not in schemas or set(body)!=schemas[path]:raise ValueError('Unknown research request/schema')
    if path=='work':
        detail=work_detail(body['id']);return {**detail,'display_text':detail_text(detail)}
    if path=='start':return {'id':jobs().start(body['method'])}
    if path=='job':
        state=jobs().poll(body['id'])
        if state['status']=='completed':state['display_text']=result_text(state['result'])
        return state
    if path=='cancel':return jobs().cancel(body['id'])
    if path=='inspect':return inspect_reference_word(body['word'],body['value_base'])
    import base64
    import os
    import tempfile
    text=body['archive_base64']
    if type(text) is not str or len(text)>2_700_000:raise ValueError('Research ZIP exceeds upload budget')
    data=base64.b64decode(text,validate=True)
    if len(data)>2_000_000:raise ValueError('Research ZIP exceeds upload budget')
    fd,name=tempfile.mkstemp(suffix='.zip')
    try:
        with os.fdopen(fd,'wb') as f:f.write(data)
        return import_library(name)
    finally:os.unlink(name)
