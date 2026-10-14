"""Offline source-pack acceptance demo using an explicit path and disposable DB."""
import argparse
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from ac.research_library import Catalogue, ingest_pack

if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive',type=Path)
    parser.add_argument('--expected-sha256',required=True)
    args=parser.parse_args()
    with TemporaryDirectory(prefix='ac-pp-ri-') as folder:
        db=Path(folder)/'registry.sqlite3'
        first=ingest_pack(args.archive,db,expected_sha256=args.expected_sha256)
        repeat=ingest_pack(args.archive,db,expected_sha256=args.expected_sha256)
        catalogue=Catalogue(db)
        print(json.dumps({'first':first,'repeat':repeat,'record_count':len(catalogue.search()),
                          'priorities':{p:len(catalogue.search(priority=p)) for p in ('P0','P1','P2')},
                          'bijection_methods':catalogue.search(method='bijection',priority='P0'),
                          'inversion_family':catalogue.search(family='inversion_sequences',limit=3),
                          'metadata':catalogue.metadata(first['pack_sha256'])},indent=2,ensure_ascii=False))
