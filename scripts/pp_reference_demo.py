"""Offline PP03 references: run with PYTHONPATH=. python scripts/pp_reference_demo.py."""
import json
from pathlib import Path
import platform
import subprocess
from ac.research_math import evaluate
from ac.research_references import load_references

root = Path(__file__).resolve().parents[1]
folder = root / 'docs/research/pp03'
references = load_references(folder/'reference_corpus_v1.json', folder/'source_reviews_v1.json')
print(json.dumps({
    'schema_version': 1,
    'python_version': platform.python_version(),
    'checkout_commit': subprocess.check_output(['git','rev-parse','HEAD'], cwd=root, text=True).strip(),
    'checkout_has_changes': bool(subprocess.check_output(['git','status','--porcelain'], cwd=root, text=True).strip()),
    'scope': 'Complete finite degrees 1..6; no proof certification',
    'results': [evaluate(statement, tuple(range(1,7))) for statement in references],
}, indent=2, sort_keys=True))
