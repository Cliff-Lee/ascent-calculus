"""Published-result benchmarks. Computation never promotes a proof status."""

from ac.research_resources import research_root, source_bytes
from hashlib import sha256
import json
from pathlib import Path

from ac.research_evidence import load_review
from ac.research_math import ClassPresentation, SourcePattern, engine_words, evaluate
from ac.research_references import load_references
from ac.research_inversions import InversionClass, testart_coefficients
from ac.research_fishburn import max_tree, inorder, tree_statistics, fishburn_coefficients
from ac.research_benchmark_oracles import inversion_201_210, fishburn_trees
from ac.research_math_oracle import reference_words

ROOT = research_root()
DATA = ROOT / 'docs/research/pp04'
REVIEW_SHA256 = '611cc5ba90c35b5cf80c3444351e92e98ea6238b420d30fe8bff5a53f75dbe91'
CATALOG_SHA256 = '0d628e4c15db87e43a9be8ab98a5f7186f138a59977064b6d320068915844c66'
MAX_MEMBERS = 10_000


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def digest(value):
    return sha256(canonical(value).encode()).hexdigest()


def load_catalog(folder=DATA):
    """A versioned audit boundary, not a user-extensible executable registry."""
    from ac.research_math import decode
    with (Path(folder) / 'benchmarks_v1.json').open('rb') as stream:
        raw = stream.read(30_001)
    catalog = decode(raw.decode())
    review = load_review(Path(folder) / 'source_reviews_v1.json')
    if digest(catalog) != CATALOG_SHA256 or review.fingerprint != REVIEW_SHA256:
        raise ValueError('Benchmark/source binding changed; re-audit required')
    if catalog['review_sha256'] != review.fingerprint:
        raise ValueError('Mismatched source snapshot')
    theorems = {t.id: t for t in review.entities('Theorem')}
    for record in catalog['records']:
        theorem = theorems[record['source_theorem_id']]
        if theorem.proof_status != 'PROVED_EXTERNAL' or tuple(record['citation_ids']) != theorem.citation_ids:
            raise ValueError('Unreviewed benchmark binding')
    return catalog


def bounded_members(iterable):
    values = []
    for value in iterable:
        if len(values) == MAX_MEMBERS:
            raise ValueError('Retained object budget exceeded')
        values.append(value)
    return values


def compare_members(production, oracle):
    """Counts alone cannot detect omitted/replaced objects or duplicates."""
    a, b = bounded_members(production), bounded_members(oracle)
    left, right = set(a), set(b)
    return {
        'same_complete_members': left == right and len(a) == len(left) and len(b) == len(right),
        'production_count': len(a), 'oracle_count': len(b),
        'production_duplicates': len(a)-len(left), 'oracle_duplicates': len(b)-len(right),
        'production_only': min(left-right, key=canonical) if left-right else None,
        'oracle_only': min(right-left, key=canonical) if right-left else None,
    }


def check_transport(source, target, forward, inverse, source_stat, target_stat):
    """Finite obligations with witnesses; no finite table is a construction."""
    source, target = bounded_members(source), bounded_members(target)
    source_set, target_set = set(source), set(target)
    seen = {}
    failures = {}
    if len(source_set) != len(source) or len(target_set) != len(target):
        failures['duplicate_generation'] = True
    for word in source:
        try:
            image = forward(word)
            if image not in target_set:
                failures.setdefault('target_membership', {'source': word, 'image': image})
            if image in seen:
                failures.setdefault('collision', {'source': word, 'other': seen[image]})
            seen[image] = word
            if inverse(image) != word:
                failures.setdefault('left_inverse', {'source': word, 'image': image})
            if source_stat(word) != target_stat(image):
                failures.setdefault('statistic', {'source': word, 'image': image})
        except (ValueError, TypeError, IndexError) as exc:
            failures.setdefault('construction_error', {'source': word, 'error': str(exc)})
    missing = target_set - set(seen)
    if missing:
        failures['surjectivity'] = min(missing, key=canonical)
    for obj in target:
        try:
            preimage = inverse(obj)
            if preimage not in source_set or forward(preimage) != obj:
                failures.setdefault('right_inverse', obj)
        except (ValueError, TypeError, IndexError) as exc:
            failures.setdefault('inverse_error', str(exc))
    return {'passed': not failures, 'failures': failures,
            'source_count': len(source), 'target_count': len(target)}


def word_statistics(word):
    # Direct word statistics compared with structural tree-node statistics.
    return {'first_positions': [i for i,v in enumerate(word,1) if v not in word[:i-1]],
            'ascent_top_positions': [i for i,v in enumerate(word,1) if i == 1 or word[i-2] < v],
            'maximum': max(word, default=0)}


def run_case(benchmark_id, degree):
    catalog = load_catalog()
    records = {r['id']: r for r in catalog['records']}
    if benchmark_id not in records:
        raise ValueError('Unknown benchmark')
    record = records[benchmark_id]
    if type(degree) is not int or degree not in record['deep_degrees']:
        raise ValueError('Degree outside audited finite budget')
    expected = record['expected_counts'][degree-record['start_degree']]
    if record['family'] == 'ordinary_pair_avoidance':
        references = load_references(ROOT/'docs/research/pp03/reference_corpus_v1.json',
                                     ROOT/'docs/research/pp03/source_reviews_v1.json')
        statement = next(s for s in references if s.id == benchmark_id)
        evidence = evaluate(statement, (degree,))
        row = evidence['rows'][0]
        checks = {'members': row['same_complete_members'],
                  'enumeration': row['engine_count'] == expected == row['expected']}
        details = row
        status = evidence['status']
    elif record['family'] == 'inversion_sequences':
        spec = InversionClass(tuple(SourcePattern(tuple(p),0,(),record['citation_ids'][0])
                                    for p in record['forbidden']))
        production = list(spec.words(degree))
        details = compare_members(production, inversion_201_210(degree))
        checks = {'members': details['same_complete_members'],
                  'enumeration': details['production_count'] == expected == testart_coefficients(degree)[degree]}
        status = ('validation_disagreement' if not checks['members'] else
                  'finite_verified' if checks['enumeration'] else 'refuted')
        details['worked_word'] = production[len(production)//2]
    else:
        spec = ClassPresentation('modified',1,(),(),0,record['citation_ids'][0])
        words = list(engine_words(spec,degree))
        oracle_trees = list(fishburn_trees(degree))
        agreement = compare_members(words, reference_words(spec,degree))
        transport = check_transport(words,oracle_trees,max_tree,inorder,word_statistics,tree_statistics)
        checks = {'members': agreement['same_complete_members'],
                  'enumeration': len(words) == len(oracle_trees) == expected == fishburn_coefficients(degree)[degree],
                  'transport_and_statistics': transport['passed']}
        status = ('validation_disagreement' if not checks['members'] else
                  'finite_verified' if all(checks.values()) else 'refuted')
        sample = words[len(words)//2]
        details = {'member_agreement': agreement, 'transport': transport,
                   'worked_word': sample, 'worked_tree': max_tree(sample),
                   'worked_statistics': word_statistics(sample)}
    return {'schema_version': 1, 'benchmark_id': benchmark_id, 'degree': degree,
            'family': record['family'], 'status': status, 'proof_status': 'not_proved',
            'expected_count': expected, 'checks': checks, 'details': details,
            'citation_ids': record['citation_ids'], 'source_theorem_id': record['source_theorem_id'],
            'review_sha256': REVIEW_SHA256, 'catalog_sha256': CATALOG_SHA256}
