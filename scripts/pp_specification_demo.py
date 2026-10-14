"""Offline PP05 constructor search; run from the public checkout with PYTHONPATH=."""
import json
import subprocess
from pathlib import Path
from ac.research_specifications import search_fibonacci_specifications

root=Path(__file__).resolve().parents[1]
result=search_fibonacci_specifications()
result['checkout_commit']=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()
result['checkout_has_changes']=bool(subprocess.check_output(['git','status','--porcelain'],cwd=root,text=True).strip())
print(json.dumps(result,indent=2,sort_keys=True))
