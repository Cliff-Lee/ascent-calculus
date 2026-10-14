"""Offline PP07 conversion, recursive derivation and adversarial audit."""
import json
from pathlib import Path
import subprocess
from ac.research_conversion_audit import reference_demo

root=Path(__file__).resolve().parents[1]
report=reference_demo()
report['checkout_commit']=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()
report['checkout_has_changes']=bool(subprocess.check_output(['git','status','--porcelain'],cwd=root,text=True).strip())
print(json.dumps(report,indent=2,sort_keys=True))
