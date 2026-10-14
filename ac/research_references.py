"""Explicitly audited PP03 bindings; a citation alone does not bind mathematics.

Editing either snapshot requires a new source/semantics audit, not status reuse.
"""
from hashlib import sha256
import json
from pathlib import Path
from ac.research_math import EnumerationStatement,decode,fields
from ac.research_evidence import load_review

AUDITED_REVIEW_SHA256='36e63f88850937d64cd44844a7887a0b66fb7524e845e00270bae5b4233cbb99'
AUDITED_CORPUS_SHA256='732b4642b6a6fad048c6c75cd329b361cb4e5e43045d88137d75c9e534517bf1'


def load_references(corpus_path,review_path):
    with Path(corpus_path).open('rb') as f:raw=f.read(30001)
    if len(raw)>30000:raise ValueError('Reference corpus exceeds budget')
    obj=decode(raw.decode());fields(obj,('schema_version','statements'))
    if type(obj['schema_version']) is not int or obj['schema_version']!=1 or type(obj['statements']) is not list:raise ValueError('Unsupported reference corpus')
    digest=sha256(json.dumps(obj,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    review=load_review(review_path)
    if digest!=AUDITED_CORPUS_SHA256 or review.fingerprint!=AUDITED_REVIEW_SHA256:raise ValueError('Source/mathematical binding changed; explicit re-audit required')
    refs=tuple(EnumerationStatement.from_json(json.dumps(s)) for s in obj['statements'])
    theorems={t.id:t for t in review.entities('Theorem')}
    for s in refs:
        if s.review_sha256!=review.fingerprint or s.source_theorem_id not in theorems or theorems[s.source_theorem_id].proof_status!='PROVED_EXTERNAL':raise ValueError('Unreviewed external reference')
        cited=set(theorems[s.source_theorem_id].citation_ids)
        if s.class_spec.citation_id not in cited or any(p.citation_id not in cited for p in s.class_spec.avoid+s.class_spec.contain):raise ValueError('Class restrictions have unbound citations')
    return refs
