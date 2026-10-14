"""Offline PP02 inspection report. Optional lead-link check is read-only."""
import argparse
import json
from pathlib import Path
from ac.research_evidence import load_review
from ac.research_library import Catalogue

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--snapshot',type=Path,default=Path(__file__).resolve().parents[1]/'docs/research/pp02/source_cards_v1.json')
    parser.add_argument('--database',type=Path)
    parser.add_argument('--work-id',help='Print the requested method card instead of the summary')
    args=parser.parse_args()
    bundle=load_review(args.snapshot)
    if args.database:bundle.check_catalogue(Catalogue(args.database))
    if args.work_id:
        print(json.dumps(bundle.method_cards(args.work_id),indent=2));raise SystemExit(0)
    print(json.dumps({'snapshot_sha256':bundle.fingerprint,'method_cards':len(bundle.method_cards()),
                      'source_statuses':{s.id:s.inspection_status for s in bundle.entities('Source')},
                      'statements':[{ 'id':t.id,'status':t.proof_status,'statement':t.statement } for t in bundle.entities() if hasattr(t,'proof_status')],
                      'interpretation':'PROVED_EXTERNAL is source-inspected, not independently checked; validation is structural, not a mathematical verifier.'},indent=2))
