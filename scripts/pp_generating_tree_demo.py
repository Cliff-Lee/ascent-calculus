"""Offline published left/right tree and state-label audit."""
import argparse
import json
from pathlib import Path
import subprocess
from ac.research_generating_trees import reference_demo

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--through',type=int,choices=(5,6,7),default=6)
args=parser.parse_args()
root=Path(__file__).resolve().parents[1]
result=reference_demo(args.through)
result['checkout_commit']=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()
result['checkout_has_changes']=bool(subprocess.check_output(['git','status','--porcelain'],cwd=root,text=True).strip())
print(json.dumps(result,sort_keys=True,indent=2))
