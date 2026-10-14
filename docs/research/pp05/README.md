# PP-RI-05 recursive specification interface

The first class adapter uses the PP04 `PP129-P6` ordinary class, avoiding zero-based classical patterns 000 and 001. Its definition and source binding come from PP03; [Baxter–Pudwell Proposition 6 and its proof](https://arxiv.org/html/1406.4100v2) motivate removing one or two maxima. This is guided reconstruction of a known mechanism, not a novelty or blind-discovery claim.

## Working example

From the public checkout, using the existing environment:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python scripts/pp_specification_demo.py
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python -m pytest -o addopts='' -q tests/test_research_specifications.py
```

```python
import json
from ac.research_specifications import search_fibonacci_specifications, RecursiveSpecification, replay
search = search_fibonacci_specifications()
spec = RecursiveSpecification.from_json(json.dumps(search['survivors'][0]['specification']))
assert spec.rules[0].construct((0, 1, 0)) == (0, 1, 2, 0)
assert spec.rules[0].decompose((0, 1, 2, 0)) == (0, 1, 0)
assert replay(spec, (1, 2, 3, 4, 5, 6))['status'] == 'finite_verified'
```

The grammar independently varies insertion sites for one-copy and two-copy constructors: append, prepend, before or after the first maximum. Sixteen candidates are tested on degrees 3–4; surviving candidates are tested on separately enumerated degrees 5–6. One survives: insert the new maximum immediately after the first old maximum. All failed candidates retain serialized configurations and first tested counterexamples. Holdout objects use a separate enumeration implementation, but the published benchmark guided grammar design and was not withheld.

Atoms are `(0,)`, `(0,0)` and `(0,1)`. One-copy branches require parent length at least two; two-copy branches require at least one. Decomposition removes all maximum entries, checks multiplicity and requires exact reconstruction. The interpreter preserves invalid outputs and duplicate derivations for audit, rather than silently filtering them into the target class. It never uses a finite target matching table.

The grammar yields the conditional equation

```text
A(t) = t + 2*t^2 + t*(A(t)-t) + t^2*A(t).
```

If the universal obligations hold, this simplifies to `(1-t-t^2)A(t)=t+t^2`, with coefficients `a_0=0`, `a_1=1`, `a_2=2` and `a_n=a_{n-1}+a_{n-2}` for n>=3. Degree zero is excluded by the existing ordinary universe. The counting interpreter counts derivations; those counts become class counts only after disjointness, closure and coverage are justified.

Independent replay checks full source member sets, constructor outputs, parent membership, unique branch assignment, absence of duplicate generation and both reconstruction directions. A deliberately wrong prepend constructor has identical derivation counts but fails those object checks. The survivor's serialized specification, human-readable description, finite evidence and seven universal obligations are in `evidence/search.json`.

All universal obligations remain `unproved`. The structural-hypothesis obligation is explicitly `not_tested`; the finite replay does not establish that every length has the structural form used in the source's explanation. Published enumeration proof status does not automatically transfer to a newly synthesized specification. `finite_verified`, `refuted` and `validation_disagreement` describe finite replay, not theorem certification.

## Architecture and upstream decision

The [upstream README](https://github.com/PermutaTriangle/comb_spec_searcher/blob/826a16cc6b40b48eac1c334c777e2cc3da30740d/README.rst) documents class identity/serialization, strategy packs, forward/backward maps and automatic specification search. We inspected it, the licence and build metadata at that exact commit. [PyPI metadata](https://pypi.org/project/comb-spec-searcher/4.3.0/) reports release 4.3.0 and Python >=3.10. Release dependency versions differ from develop, including psutil, requests and typing-extensions. The project supports Python >=3.11 and this run uses 3.14.7; metadata alone does not establish runtime compatibility.

We chose an independently authored bounded rule interface. This keeps default installation dependency-free while establishing the class/constructor/reconstructor boundaries a later optional adapter would need. No upstream package is installed, imported or vendored. An upstream integration will require separate runtime tests before an optional extra is added. The BSD-3-Clause licence was read in full: redistribution requires notices and disclaimer retention and prohibits endorsement without permission. No redistribution of upstream implementation occurs here. Exact local inspection hashes and decision are in `upstream_audit.json`.

`ClassPresentation` remains the mathematical class contract. New `InsertionRule` and `RecursiveSpecification` types have closed, bounded serialization; there are no executable expressions or dynamic class imports. Generic word constructors can be replayed against other classes, where coverage may fail. This prototype supports zero-based, unshifted classes, nonempty atoms, positive degree reduction, at most eight rules and interpreter degrees at most six. Citation metadata documents provenance; generic serialization does not certify a source/theorem binding or establish truth.

Advanced invention, strategy learning and unpublished research remain in the private architecture. PP06 generating-tree discovery and PP12 cumulative discovery are not implemented here. Current search is a finite constructor grammar, not a general-purpose specification finder or a `comb_spec_searcher` API compatibility layer.
