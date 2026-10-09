# AM-Next N5: generated typed transformation search

N5 adds a finite, inspectable grammar for constructing transformation
programs. Its inputs are the exact source and target class specifications,
their degree offsets, a grammar version, and explicit selector, operation,
cost, depth, candidate, expansion, retained-class-object, universe-enumeration,
and total map-evaluation bounds.

## Generated vocabulary

The grammar combines the current calculus with definitions that distinguish
ascent-sequence positions:

- reversal, complement, level compression, standardization, hat and inverse-hat;
- prefix lifts and inverse lifts at positions within a configured bound;
- left-to-right and right-to-left lift sweeps, with either lift direction, over
  first/last occurrences, ascent and descent roles, run boundaries, and bounded
  Boolean combinations of those selectors;
- selector-defined restrictions;
- insertion of an existing value and insertion of a new maximum at selected
  source cuts.

Compositions are generated from these atoms and normalized with the existing
transformation algebra. Atoms have weighted costs. Programs with a known length
effect different from the requested degree shift are discarded before finite
evaluation. Unknown effects remain eligible and are checked on every tested
object. Selector kinds prevent position selectors from being used as cut
selectors.

The grammar is intentionally not described as complete. It is a bounded search
language over documented operations, selectors, and parameter ranges. A
researcher can reconstruct each run from the canonical transformation-search
specification and its grammar version. Increasing the bounds enlarges a search;
it does not establish that all mathematically sensible maps have been tried.

## Finite map checks

The registered `search-transformations` worker precomputes each finite source
and target class, generates normalized programs, and checks definedness, target
membership, collisions, and coverage at each requested degree. It records the
first finite failure for near misses and ranks exact finite matches by cost.
The worker checkpoints candidate progress and results in the same durable job
store as the other research questions.

Class preparation and map applications have separate checked budgets. The
worker fails with an explicit limit message instead of silently dropping part
of a class or exhausting memory. The effective candidate budget is reduced
when the requested map-evaluation budget cannot cover every candidate over
the whole source window.

An exact candidate means it passed every degree in the supplied window. It is
not a proof of a theorem. The stored result lists proof obligations: universal
definedness, target membership, injectivity and surjectivity (or a proved
inverse), and the scope of the generated grammar.

## Python submission

The N10 desktop workflow is not yet connected. Until then a run can be queued
through the public Python API:

```python
from ac.discovery.jobs import ResearchJobStore
from ac.discovery.specification import ClassSpec, DegreeWindow, PatternRuleSpec
from ac.discovery.transformation_search import TransformationSearchSpec
from ac.discovery.worker import PersistentWorker

source = ClassSpec("modified", (PatternRuleSpec.build("avoid", "2122"),))
target = ClassSpec("modified", (PatternRuleSpec.build("avoid", "2212"),))
question = TransformationSearchSpec(source, target, DegreeWindow(1, 7))
store = ResearchJobStore("research.sqlite3")
job = store.create_job(question, handler="search-transformations")
worker = PersistentWorker("research.sqlite3")
worker.start()
```

The worker is a persistent process. Applications should retain its handle and
stop it with `worker.stop()` during orderly shutdown. Job state remains in
SQLite after the process exits.

## N5 gate

The gate checks strict specification round-trips, fresh-maximum insertion
semantics and occurrence identity, generated selector sweeps, durable job
serialization, and a real spawned worker finding the identity map on a finite
ordinary class window. Larger blind rediscovery benchmarks and adversarial
validation remain scheduled for N12.
