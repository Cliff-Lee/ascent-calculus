"""Offline metadata ingestion; conference annotations never become proof claims."""
from __future__ import annotations
import argparse
from hashlib import sha256
import io
import json
from pathlib import Path
from datetime import datetime, timezone
import csv
import re
import sqlite3
import stat
import unicodedata
from urllib.parse import urlsplit
import zipfile

JSON_MEMBER = 'permutation_patterns_ascent_research_catalogue_expanded.json'
AUDIT_MEMBER = 'permutation_patterns_ascent_calculus_audit_expanded.md'
MAX_ARCHIVE = 2_000_000
MAX_MEMBER = 1_000_000
APP_ID = 0x50504C42
VERSION = 1
FIELDS = {'id', 'year', 'source_type', 'authors', 'title', 'priority', 'proposed_module', 'relevance', 'url', 'evidence_note'}
TOP_FIELDS = {'created', 'topic', 'scope_note', 'priority_legend', 'records', 'audit_revision', 'sources_checked'}
FAMILIES = {'ascent_sequences': ('ascent',), 'inversion_sequences': ('inversion',),
            'words': ('word', 'cayley', 'multipermutation'), 'permutations': ('permutation',),
            'trees': ('tree', 'forest'), 'paths': ('dyck', 'motzkin', 'path'),
            'posets_matrices': ('poset', 'matrix', 'matrices', 'interval order'),
            'partitions': ('partition', 'restricted growth')}


class CatalogueError(ValueError):
    pass


def canonical(obj):
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)


def folded(text):
    return ''.join(c for c in unicodedata.normalize('NFKD', text.casefold()) if not unicodedata.combining(c))


def text(value, limit=4000):
    if type(value) is not str or not value.strip() or len(value) > limit or any(ord(c) < 32 for c in value):
        raise CatalogueError('Invalid bounded metadata text')


def url(value):
    text(value)
    try:
        parsed = urlsplit(value)
    except ValueError as exc:
        raise CatalogueError('Invalid URL locator') from exc
    if parsed.scheme not in ('https', 'http') or not parsed.hostname or parsed.username or parsed.password:
        raise CatalogueError('Only noncredentialed HTTP(S) literature locators allowed')


def validate_catalogue(raw):
    def unique(pairs):
        out = {}
        for k, v in pairs:
            if k in out:
                raise CatalogueError('Duplicate JSON key')
            out[k] = v
        return out
    def bad(value):
        raise CatalogueError('Nonfinite JSON number')
    try:
        obj = json.loads(raw, object_pairs_hook=unique, parse_constant=bad)
    except (UnicodeError, ValueError, RecursionError) as exc:
        raise CatalogueError('Invalid catalogue JSON') from exc
    if type(obj) is not dict or set(obj) != TOP_FIELDS:
        raise CatalogueError('Unsupported catalogue envelope')
    for field in ('created', 'topic', 'scope_note', 'audit_revision'):
        text(obj[field])
    import datetime
    try:
        datetime.date.fromisoformat(obj['created'])
    except ValueError as exc:
        raise CatalogueError('Invalid creation date') from exc
    legend = obj['priority_legend']
    if type(legend) is not dict or set(legend) != {'P0', 'P1', 'P2'}:
        raise CatalogueError('Invalid priority legend')
    for value in legend.values():
        text(value)
    sources = obj['sources_checked']
    if type(sources) is not list or len(sources) > 100:
        raise CatalogueError('Invalid source locators')
    for value in sources:
        url(value)
    records = obj['records']
    if type(records) is not list or len(records) != 140:
        raise CatalogueError('This import contract requires exactly 140 records')
    seen = set()
    for r in records:
        if type(r) is not dict or set(r) != FIELDS:
            raise CatalogueError('Unknown or missing record fields')
        for k in FIELDS - {'year'}:
            text(r[k])
        if not re.fullmatch(r'PP-[0-9]{3}', r['id']) or r['id'] in seen:
            raise CatalogueError('Invalid or duplicate record ID')
        seen.add(r['id'])
        if type(r['year']) is not int or not 1900 <= r['year'] <= 2100:
            raise CatalogueError('Invalid association year')
        if r['priority'] not in legend:
            raise CatalogueError('Invalid priority')
        url(r['url'])
    return obj


def read_pack(path):
    """Bounded reads, exact member allowlist, no extraction or link following."""
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise CatalogueError('Select a regular archive, not a symlink')
    with path.open('rb') as f:
        raw = f.read(MAX_ARCHIVE+1)
    if len(raw) > MAX_ARCHIVE:
        raise CatalogueError('Archive exceeds size budget')
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            entries = z.infolist()
            if len(entries) != 2 or {i.filename for i in entries} != {JSON_MEMBER, AUDIT_MEMBER}:
                raise CatalogueError('Archive member allowlist violation')
            contents = {}
            for i in entries:
                mode = i.external_attr >> 16
                if (i.flag_bits & 1 or stat.S_ISLNK(mode) or i.is_dir()
                        or (stat.S_IFMT(mode) not in (0, stat.S_IFREG))
                        or i.compress_type not in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED)
                        or i.file_size > MAX_MEMBER or i.file_size > max(i.compress_size, 1)*200):
                    raise CatalogueError('Unsafe or oversized ZIP member')
                with z.open(i) as f:
                    value = f.read(MAX_MEMBER+1)
                if len(value) > MAX_MEMBER:
                    raise CatalogueError('Expanded member exceeds size budget')
                value.decode('utf-8')
                contents[i.filename] = value
    except (zipfile.BadZipFile, UnicodeError, RuntimeError, NotImplementedError) as exc:
        raise CatalogueError('Invalid archive') from exc
    obj = validate_catalogue(contents[JSON_MEMBER])
    return sha256(raw).hexdigest(), raw, contents, obj


def family_tags(record):
    value = folded(' '.join(record[k] for k in ('title', 'proposed_module', 'relevance')))
    return sorted(k for k, terms in FAMILIES.items() if any(term in value for term in terms))


def _connect(path, *, create=False):
    path = Path(path)
    if path.is_symlink() or (path.exists() and not path.is_file()):
        raise CatalogueError('Database must be a regular file')
    connection = sqlite3.connect(path.resolve().as_uri()+('?mode=rwc' if create else '?mode=ro'), uri=True)
    try:
        connection.execute('BEGIN IMMEDIATE' if create else 'BEGIN')
        app = connection.execute('PRAGMA application_id').fetchone()[0]
        version = connection.execute('PRAGMA user_version').fetchone()[0]
        tables = {r[0] for r in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if not tables and app == version == 0 and create:
            connection.execute('CREATE TABLE packs (sha TEXT PRIMARY KEY, archive BLOB NOT NULL, catalogue BLOB NOT NULL, audit BLOB NOT NULL, imported_at TEXT NOT NULL)')
            connection.execute('CREATE TABLE records (pack TEXT NOT NULL REFERENCES packs(sha), id TEXT NOT NULL, original TEXT NOT NULL, PRIMARY KEY(pack,id))')
            connection.execute(f'PRAGMA application_id={APP_ID}')
            connection.execute(f'PRAGMA user_version={VERSION}')
        elif app != APP_ID or version != VERSION or tables != {'packs', 'records'}:
            raise CatalogueError('Foreign or unsupported database; never migrate jobs/literature stores')
        return connection
    except BaseException:
        connection.close()
        raise


def ingest_pack(archive, database, *, expected_sha256=None):
    pack, raw, members, obj = read_pack(archive)  # validate before opening a database
    if expected_sha256 is not None and (not isinstance(expected_sha256,str) or not re.fullmatch('[0-9a-f]{64}',expected_sha256) or expected_sha256 != pack):
        raise CatalogueError('Archive SHA-256 does not match supplied manifest')
    conn = _connect(database, create=True)
    try:
        existing = conn.execute('SELECT archive,catalogue,audit FROM packs WHERE sha=?', (pack,)).fetchone()
        if existing is not None:
            expected = (raw, members[JSON_MEMBER], members[AUDIT_MEMBER])
            cached = dict(conn.execute('SELECT id,original FROM records WHERE pack=?', (pack,)))
            if existing != expected or cached != {r['id']: canonical(r) for r in obj['records']}:
                raise CatalogueError('Stored pack or records changed; explicit audit required')
            status = 'already_ingested'
        else:
            conn.execute('INSERT INTO packs VALUES (?,?,?,?,?)', (pack, raw, members[JSON_MEMBER], members[AUDIT_MEMBER], datetime.now(timezone.utc).isoformat()))
            conn.executemany('INSERT INTO records VALUES (?,?,?)', ((pack, r['id'], canonical(r)) for r in obj['records']))
            status = 'ingested'
        imported_at = conn.execute('SELECT imported_at FROM packs WHERE sha=?', (pack,)).fetchone()[0]
        conn.commit()
        return {'status': status, 'pack_sha256': pack, 'catalogue_sha256': sha256(members[JSON_MEMBER]).hexdigest(),
                'audit_sha256': sha256(members[AUDIT_MEMBER]).hexdigest(), 'record_count': len(obj['records']),
                'schema_version': VERSION, 'imported_at': imported_at, 'evidence_status': 'imported_annotation_unverified'}
    finally:
        conn.close()


class Catalogue:
    """Read-only, detached results. Search filters AND together; text is literal."""
    def __init__(self, database):
        self.database = Path(database)
        conn = _connect(self.database)
        conn.close()

    def packs(self):
        conn = _connect(self.database)
        try:
            return [r[0] for r in conn.execute('SELECT sha FROM packs ORDER BY sha')]
        finally:
            conn.close()

    def source(self, pack):
        conn = _connect(self.database)
        try:
            row = conn.execute('SELECT archive,catalogue,audit FROM packs WHERE sha=?', (pack,)).fetchone()
            if row is None:
                raise CatalogueError('Unknown pack')
            return dict(zip(('archive', 'catalogue', 'audit'), row))
        finally:
            conn.close()

    def metadata(self, pack):
        obj = json.loads(self.source(pack)['catalogue'])
        return {k: v for k, v in obj.items() if k != 'records'}

    def export(self, *, format='json', **filters):
        rows = self.search(**filters)
        if format == 'json':
            return json.dumps(rows, ensure_ascii=False, sort_keys=True, indent=2)+'\n'
        if format != 'csv':
            raise CatalogueError('Export format must be json or csv')
        output = io.StringIO(newline='')
        columns = sorted(FIELDS)+['pack_sha256','verification_status','proof_status']
        writer = csv.DictWriter(output, fieldnames=columns, lineterminator='\n')
        writer.writeheader()
        for row in rows:
            values = {**row['original'], 'pack_sha256':row['provenance']['pack_sha256'],
                      'verification_status':row['verification_status'], 'proof_status':row['proof_status']}
            # CSV is a view, not the lossless source. Neutralize spreadsheet formula
            # prefixes; JSON/source() preserve all exact original values.
            values = {k: "'"+v if isinstance(v,str) and v.startswith(('=','+','-','@')) else v for k,v in values.items()}
            writer.writerow(values)
        return output.getvalue()

    def search(self, *, method=None, family=None, relevance=None, author=None, year=None,
               priority=None, query=None, pack=None, record_id=None, source_type=None,
               verification_status=None, limit=200):
        if type(limit) is not int or not 1 <= limit <= 1000:
            raise CatalogueError('Limit must be 1..1000')
        for value in (method, relevance, author, query, record_id, pack, source_type):
            if value is not None:
                text(value)
        if year is not None and (type(year) is not int or not 1900 <= year <= 2100):
            raise CatalogueError('Invalid year')
        if priority is not None and priority not in ('P0','P1','P2'):
            raise CatalogueError('Invalid priority')
        if verification_status is not None and verification_status != 'CATALOGUED':
            raise CatalogueError('Only CATALOGUED metadata is available in PP-RI-01')
        if family is not None and family not in FAMILIES:
            raise CatalogueError('Unknown family tag')
        conn = _connect(self.database)
        try:
            rows = conn.execute('SELECT pack,original FROM records ORDER BY pack,id').fetchall()
        finally:
            conn.close()
        results = []
        for source, original in rows:
            r = json.loads(original)
            tags = family_tags(r)
            if (pack is not None and pack != source or record_id is not None and record_id != r['id']
                    or year is not None and year != r['year'] or priority is not None and priority != r['priority']
                    or family is not None and family not in tags):
                continue
            if any(term is not None and folded(term) not in folded(r[field])
                   for term, field in ((method,'proposed_module'),(relevance,'relevance'),(author,'authors'),(source_type,'source_type'))):
                continue
            if query is not None and folded(query) not in folded(' '.join(str(v) for v in r.values())):
                continue
            results.append({'original': r, 'provenance': {'pack_sha256': source, 'record_sha256': sha256(canonical(r).encode()).hexdigest(),
                           'source_member': JSON_MEMBER, 'record_id': r['id']},
                           'index': {'method': r['proposed_module'], 'families': tags, 'version': 'pp-keyword-v1', 'status': 'heuristic_metadata_index'},
                           'verification_status': 'CATALOGUED', 'evidence_status': 'imported_annotation_unverified', 'proof_status': 'not_assessed'})
            if len(results) == limit:
                break
        return results


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database', required=True, type=Path)
    subs = parser.add_subparsers(dest='action', required=True)
    ingestion = subs.add_parser('ingest')
    ingestion.add_argument('archive', type=Path)
    ingestion.add_argument('--expected-sha256')
    search = subs.add_parser('search')
    for key in ('method','family','relevance','author','priority','query','pack','record-id','source-type','verification-status'):
        search.add_argument('--'+key)
    search.add_argument('--format', choices=('json','csv'), default='json')
    search.add_argument('--year', type=int)
    search.add_argument('--limit', type=int, default=200)
    args = vars(parser.parse_args(argv))
    database, action = args.pop('database'), args.pop('action')
    try:
        result = ingest_pack(args['archive'], database, expected_sha256=args['expected_sha256']) if action == 'ingest' else Catalogue(database).export(**args)
    except (CatalogueError, OSError, sqlite3.Error) as exc:
        parser.exit(2, str(exc)+'\n')
    print(json.dumps(result, ensure_ascii=False, indent=2) if action == 'ingest' else result, end='\n' if action == 'ingest' else '')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
