"""Bounded subprocess benchmark runner with local, version-bound checkpoints."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import tempfile
import time

from ac.research_benchmarks import ROOT, DATA, canonical, digest, load_catalog, run_case


def implementation_fingerprint():
    paths = sorted((ROOT/'ac').rglob('*.py'))
    paths += [ROOT/'docs/research/pp03'/name for name in
              ('source_reviews_v1.json','reference_corpus_v1.json')]
    paths += [DATA/name for name in ('source_reviews_v1.json','benchmarks_v1.json')]
    return digest({str(p.relative_to(ROOT)): sha256(p.read_bytes()).hexdigest() for p in paths})


def read_json(path):
    from ac.research_math import decode
    if path.is_symlink():
        raise ValueError('Checkpoint symlinks are not supported')
    with path.open('rb') as stream:
        raw = stream.read(30_001)
    return decode(raw.decode())


def atomic_json(path, value):
    if path.is_symlink():
        raise ValueError('Checkpoint symlinks are not supported')
    fd, temporary = tempfile.mkstemp(dir=path.parent, prefix='.benchmark-')
    try:
        with os.fdopen(fd,'w') as stream:
            stream.write(canonical(value)+'\n')
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary,path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def execute_cell(benchmark_id, degree, timeout):
    started = time.monotonic()
    env = os.environ.copy()
    env['PYTHONPATH'] = str(ROOT)
    env['PYTHONDONTWRITEBYTECODE'] = '1'
    try:
        proc = subprocess.run(
            [sys.executable,'-m','ac.research_benchmark_runner','--worker',benchmark_id,str(degree)],
            cwd=ROOT, env=env, text=True, capture_output=True, timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return {'benchmark_id': benchmark_id, 'degree': degree,
                'status': 'budget_exhausted', 'proof_status': 'not_proved',
                'wall_seconds': time.monotonic()-started}
    if proc.returncode:
        return {'benchmark_id': benchmark_id, 'degree': degree,
                'status': 'execution_error', 'proof_status': 'not_proved',
                'diagnostic': proc.stderr[-2000:], 'wall_seconds': time.monotonic()-started}
    result = json.loads(proc.stdout)
    if result['benchmark_id'] != benchmark_id or result['degree'] != degree:
        raise ValueError('Worker returned the wrong case')
    result['wall_seconds'] = time.monotonic()-started
    return result


def run_suite(profile='quick', workers=1, checkpoint=None):
    """Quick is default; deep has explicit bounds, at most two child processes.

    Each completed degree is atomic. Interrupted workers are rerun on resume;
    failed attempts are retained. Checkpoint checksums detect accidental edits,
    not adversarial forgery and not mathematical proof validity.
    """
    if profile not in ('quick','deep') or type(workers) is not int or not 1 <= workers <= 2:
        raise ValueError('Use quick/deep and one or two workers')
    catalog = load_catalog()
    fingerprint = implementation_fingerprint()
    manifest = {'schema_version': 1, 'profile': profile,
                'implementation_sha256': fingerprint,
                'catalog_sha256': digest(catalog),
                'python': platform.python_version(), 'platform': platform.system(),
                'seed': None, 'randomness': 'none'}
    folder = Path(checkpoint) if checkpoint is not None else None
    if folder is not None:
        if folder.is_symlink():
            raise ValueError('Checkpoint symlinks are not supported')
        folder.mkdir(parents=True, exist_ok=True)
        path = folder/'manifest.json'
        if path.exists():
            if read_json(path) != manifest:
                raise ValueError('Stale or incompatible checkpoint; use a new directory')
        else:
            # Refuse to adopt arbitrary user files or abandoned partial state.
            if any(folder.iterdir()):
                raise ValueError('New checkpoint directory must be empty')
            atomic_json(path,manifest)

    tasks = [(r,n) for r in catalog['records'] for n in r[profile+'_degrees']]

    def one(task):
        record, degree = task
        key = {'benchmark_id': record['id'], 'degree': degree}
        path = folder/(record['id']+'-'+str(degree)+'.json') if folder else None
        attempts = []
        if path is not None and path.exists():
            saved = read_json(path)
            if set(saved) != {'key','manifest_sha256','attempts','sha256'}:
                raise ValueError('Invalid checkpoint schema')
            body = {k:v for k,v in saved.items() if k != 'sha256'}
            if (digest(body) != saved['sha256'] or saved['key'] != key or
                    saved['manifest_sha256'] != digest(manifest)):
                raise ValueError('Checkpoint identity/checksum mismatch')
            attempts = saved['attempts']
            if type(attempts) is not list or not attempts or len(attempts) > 10:
                raise ValueError('Invalid checkpoint attempts')
            for result in attempts:
                if (not isinstance(result,dict) or result.get('benchmark_id') != key['benchmark_id'] or
                        result.get('degree') != degree or result.get('proof_status') != 'not_proved'):
                    raise ValueError('Invalid checkpoint result identity')
            last = attempts[-1]
            if last['status'] == 'finite_verified':
                if (last.get('catalog_sha256') != manifest['catalog_sha256'] or
                        not last.get('checks') or not all(v is True for v in last['checks'].values())):
                    raise ValueError('Invalid successful checkpoint evidence')
                return last, True
            if len(attempts) == 10:
                raise ValueError('Attempt limit reached; preserve this checkpoint and use a new directory')
        result = execute_cell(record['id'], degree, record['runtime_seconds'][profile])
        if path is not None:
            attempts.append(result)
            body = {'key': key, 'manifest_sha256': digest(manifest), 'attempts': attempts}
            atomic_json(path,{**body,'sha256':digest(body)})
        return result, False

    # Threads only supervise isolated child processes; mathematics runs in them.
    with ThreadPoolExecutor(max_workers=workers) as pool:
        completed = list(pool.map(one,tasks))
    if implementation_fingerprint() != fingerprint:
        raise ValueError('Source changed during execution; results require a fresh run')
    results = [r for r,_ in completed]
    return {'schema_version': 1, 'manifest': manifest, 'workers': workers,
            'resumed_cases': sum(resumed for _,resumed in completed),
            'results': results, 'complete': all(r['status']=='finite_verified' for r in results),
            'proof_status': 'not_proved'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile', choices=('quick','deep'), default='quick')
    parser.add_argument('--workers', type=int, choices=(1,2), default=1)
    parser.add_argument('--checkpoint', type=Path)
    parser.add_argument('--worker', nargs=2, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.worker:
        print(canonical(run_case(args.worker[0],int(args.worker[1]))))
        return
    result = run_suite(args.profile,args.workers,args.checkpoint)
    print(json.dumps(result,indent=2,sort_keys=True))
    if not result['complete']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
