"""Prepare a small, allowlisted public reference payload for wheel/native builds."""
from hashlib import sha256
import json
from pathlib import Path
import shutil

ROOT=Path(__file__).resolve().parents[1]
TARGET=ROOT/'ac/research_data'
SNAPSHOTS={
 'pp03':('source_reviews_v1.json','reference_corpus_v1.json'),
 'pp04':('source_reviews_v1.json','benchmarks_v1.json'),
 'pp06':('source_reviews_v1.json',),
 'pp07':('graph_v1.json',),
 'pp08':('source_reviews_v1.json',),
}
SOURCES=('classes/theories.py','generate/universes.py','patterns/classical.py','patterns/constraints.py','patterns/general.py','logic/predicates.py')


def prepare():
    TARGET.mkdir(exist_ok=True)
    (TARGET/'__init__.py').write_text('"""Public reference data and exact source records; no private artifacts."""\n')
    selected=[ROOT/'docs/research'/stage/name for stage,names in SNAPSHOTS.items() for name in names]
    selected += list((ROOT/'ac').glob('research_*.py'))
    selected += [ROOT/'ac'/name for name in SOURCES]
    selected += [ROOT/'ac/gui'/name for name in ('research_jobs.py','research_library_model.py','research_panel.py','research_http.py','research_smoke.py')]
    manifest={}
    for path in sorted(selected):
        relative=path.relative_to(ROOT);out=TARGET/'root'/relative
        out.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(path,out)
        manifest[str(relative)]={'sha256':sha256(path.read_bytes()).hexdigest(),'bytes':path.stat().st_size}
    (TARGET/'manifest.json').write_text(json.dumps({'schema_version':1,'files':manifest,'total_bytes':sum(v['bytes'] for v in manifest.values())},indent=2,sort_keys=True)+'\n')
    return manifest


if __name__=='__main__':
    print(f'Prepared {len(prepare())} public reference/source records.')
