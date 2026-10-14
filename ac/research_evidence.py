"""Offline provenance snapshots. Validation checks links/status eligibility, not truth.

No source retrieval, code execution or automatic theorem promotion occurs here.
"""
from dataclasses import asdict, dataclass, fields
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import tempfile
from .research_library import CatalogueError, canonical, text, url

STATUSES = {'CATALOGUED','SOURCE_LOCATED','FULL_TEXT_INSPECTED','CLAIM_EXTRACTED',
            'CLAIM_VERIFIED','NEEDS_REVIEW','INACCESSIBLE'}
PROOF_STATUSES = {'NOT_ASSERTED','PROPOSED','PROOF_ATTEMPT','PROVED_EXTERNAL'}
MAX_BYTES = 1_000_000


@dataclass(frozen=True)
class Source:
    id: str
    url: str
    version: str
    medium: str
    inspection_status: str
    retrieved_on: str
    inspection_scope: str
    rights_note: str
    content_sha256: str | None


@dataclass(frozen=True)
class Work:
    id: str
    lead_id: str
    pack_sha256: str
    title: str
    authors: tuple[str, ...]
    year: int


@dataclass(frozen=True)
class SourceLocation:
    id: str
    source_id: str
    label: str


@dataclass(frozen=True)
class Citation:
    id: str
    work_id: str
    location_id: str


@dataclass(frozen=True)
class Evidence:
    id: str
    source_id: str
    inspection_status: str
    review_note: str


@dataclass(frozen=True)
class Claim:
    id: str
    statement: str
    assumptions: tuple[str, ...]
    family: str
    indexing: str
    pattern_semantics: str
    proof_status: str
    citation_ids: tuple[str, ...]
    evidence_ids: tuple[str, ...]


@dataclass(frozen=True)
class Definition(Claim):
    pass


@dataclass(frozen=True)
class Theorem(Claim):
    pass


@dataclass(frozen=True)
class Algorithm(Claim):
    pass


TYPES = {c.__name__:c for c in (Source,Work,SourceLocation,Citation,Evidence,Claim,Definition,Theorem,Algorithm)}
TUPLES = {'authors','assumptions','citation_ids','evidence_ids'}
CARD_FIELDS = {'work_id','source_ids','problem_family','assumptions','construction','input_type',
               'output_type','complexity','proof_mechanism','implementation_idea','adaptation_risks','blockers'}


class ReviewBundle:
    def __init__(self, entities, cards):
        self._raw = canonical({'schema_version':1,
                              'entities':[{'kind':type(e).__name__,'data':asdict(e)} for e in entities],
                              'method_cards':cards})
        self._validate()

    def _validate(self):
        obj=json.loads(self._raw)
        if len(self._raw.encode())>MAX_BYTES or len(obj['entities'])>1000 or len(obj['method_cards'])>100:
            raise CatalogueError('Review snapshot budget exceeded')
        items={}
        for item in obj['entities']:
            kind,data=item['kind'],item['data']
            if kind not in TYPES or set(data)!={f.name for f in fields(TYPES[kind])}:
                raise CatalogueError('Unsupported entity schema')
            for k,v in data.items():
                if k in TUPLES:
                    if type(v) is not list or len(v)>100 or any(type(x) is not str or not x.strip() for x in v):
                        raise CatalogueError('Expected bounded string array')
                elif k=='year':
                    if type(v) is not int or not 1900<=v<=2100:raise CatalogueError('Invalid publication year')
                elif k=='content_sha256' and v is None:continue
                else:text(v)
            if not re.fullmatch('[A-Za-z0-9_.-]{1,100}',data['id']) or data['id'] in items:
                raise CatalogueError('Invalid/duplicate entity ID')
            items[data['id']]=(kind,data)
            if kind=='Source':
                url(data['url'])
                if data['inspection_status'] not in STATUSES:raise CatalogueError('Unknown source status')
                import datetime
                datetime.date.fromisoformat(data['retrieved_on'])
                if data['content_sha256'] is not None and not re.fullmatch('[0-9a-f]{64}',data['content_sha256']):
                    raise CatalogueError('Invalid content digest')
            if kind=='Work' and (not re.fullmatch('[0-9a-f]{64}',data['pack_sha256']) or not re.fullmatch('PP-[0-9]{3}',data['lead_id'])):
                raise CatalogueError('Invalid immutable lead reference')
        def resolve(key,kind):
            if key not in items or items[key][0]!=kind:raise CatalogueError('Dangling or wrong-type reference')
            return items[key][1]
        for kind,data in items.values():
            if kind=='SourceLocation':resolve(data['source_id'],'Source')
            elif kind=='Citation':
                resolve(data['work_id'],'Work');resolve(data['location_id'],'SourceLocation')
            elif kind=='Evidence':
                resolve(data['source_id'],'Source')
                if data['inspection_status'] not in STATUSES:raise CatalogueError('Unknown evidence status')
            elif kind in ('Claim','Definition','Theorem','Algorithm'):
                if data['proof_status'] not in PROOF_STATUSES:raise CatalogueError('Unsupported proof status; no kernel backend in PP02')
                if not data['citation_ids'] or not data['evidence_ids']:raise CatalogueError('Uncited statement')
                cites=[resolve(c,'Citation') for c in data['citation_ids']]
                sources={resolve(resolve(c['location_id'],'SourceLocation')['source_id'],'Source')['id'] for c in cites}
                evidence=[resolve(e,'Evidence') for e in data['evidence_ids']]
                if {e['source_id'] for e in evidence} != sources:raise CatalogueError('Evidence does not support cited sources')
                if len({c['work_id'] for c in cites})!=1:raise CatalogueError('Statement needs one unambiguous work')
                if data['proof_status']=='PROVED_EXTERNAL':
                    if (not data['assumptions'] or any(e['inspection_status']!='CLAIM_VERIFIED' for e in evidence)
                            or any(resolve(s,'Source')['medium']!='full_paper' or resolve(s,'Source')['inspection_status']!='FULL_TEXT_INSPECTED' for s in sources)):
                        raise CatalogueError('External proof requires inspected full-paper statement/hypotheses, not abstract metadata')
        seen=set()
        for card in obj['method_cards']:
            if type(card) is not dict or set(card)!=CARD_FIELDS:raise CatalogueError('Invalid method-card fields')
            resolve(card['work_id'],'Work')
            if card['work_id'] in seen:raise CatalogueError('Duplicate method card')
            seen.add(card['work_id'])
            if type(card['source_ids']) is not list or not card['source_ids']:raise CatalogueError('Method source required')
            for s in card['source_ids']:
                resolve(s,'Source')
                if not any(kind=='Citation' and data['work_id']==card['work_id'] and resolve(data['location_id'],'SourceLocation')['source_id']==s for kind,data in items.values()):
                    raise CatalogueError('Method source is not cited by this work')
            for k in CARD_FIELDS-{'source_ids'}:text(card[k])

    def to_json(self):return self._raw

    @property
    def fingerprint(self):return sha256(self._raw.encode()).hexdigest()

    def entities(self,kind=None):
        return [TYPES[e['kind']](**{k:tuple(v) if k in TUPLES else v for k,v in e['data'].items()})
                for e in json.loads(self._raw)['entities'] if kind is None or kind==e['kind']]

    def method_cards(self,work_id=None):
        return [c for c in json.loads(self._raw)['method_cards'] if work_id is None or c['work_id']==work_id]

    def check_catalogue(self,catalogue):
        for work in self.entities('Work'):
            if not catalogue.search(pack=work.pack_sha256,record_id=work.lead_id):
                raise CatalogueError('Work lead/pack not found in catalogue')
        return True

    @classmethod
    def from_json(cls,raw):
        if type(raw) is not str or len(raw.encode())>MAX_BYTES:raise CatalogueError('Review JSON budget exceeded')
        def unique(pairs):
            out={}
            for k,v in pairs:
                if k in out:raise CatalogueError('Duplicate review JSON key')
                out[k]=v
            return out
        try:obj=json.loads(raw,object_pairs_hook=unique)
        except (ValueError,RecursionError) as exc:raise CatalogueError('Invalid review JSON') from exc
        if type(obj) is not dict or set(obj)!={'schema_version','entities','method_cards'} or type(obj['schema_version']) is not int or obj['schema_version']!=1:
            raise CatalogueError('Unsupported review snapshot')
        if type(obj['entities']) is not list or type(obj['method_cards']) is not list:raise CatalogueError('Expected review arrays')
        entities=[]
        for e in obj['entities']:
            if type(e) is not dict or set(e)!={'kind','data'} or type(e['kind']) is not str or e['kind'] not in TYPES or type(e['data']) is not dict:
                raise CatalogueError('Unsupported entity')
            if set(e['data'])!={f.name for f in fields(TYPES[e['kind']])}:raise CatalogueError('Unknown entity fields')
            entities.append(TYPES[e['kind']](**{k:tuple(v) if k in TUPLES and type(v) is list else v for k,v in e['data'].items()}))
        return cls(entities,obj['method_cards'])


def load_review(path):
    with Path(path).open('rb') as f:raw=f.read(MAX_BYTES+1)
    if len(raw)>MAX_BYTES:raise CatalogueError('Review snapshot too large')
    return ReviewBundle.from_json(raw.decode('utf-8'))


def save_review(path,bundle):
    if type(bundle) is not ReviewBundle:raise CatalogueError('Validated review bundle required')
    target=Path(path)
    fd,temp=tempfile.mkstemp(dir=target.parent,prefix='.pp-review-')
    try:
        with os.fdopen(fd,'wb') as f:
            f.write(bundle.to_json().encode());f.flush();os.fsync(f.fileno())
        os.link(temp,target) # exclusive publication; never overwrite existing evidence
    finally:os.unlink(temp)
