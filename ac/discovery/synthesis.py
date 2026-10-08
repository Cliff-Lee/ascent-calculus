from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from itertools import product
from typing import Iterable

from ac.algebra.transforms import Compose, Identity, Transformation
from ac.core.word import ChainWord
from ac.logic.predicates import WordPredicate


class FailureKind(str, Enum):
    UNDEFINED = "undefined"
    OUTSIDE_TARGET = "outside_target"
    COLLISION = "collision"
    NOT_SURJECTIVE = "not_surjective"


@dataclass(frozen=True)
class SynthesisFailure:
    kind: FailureKind
    n: int
    source: ChainWord | None = None
    output: ChainWord | None = None
    detail: str = ""
    other_source: ChainWord | None = None


@dataclass(frozen=True)
class CandidateDiagnostics:
    """Probe-degree diagnostics for ranking imperfect transformation candidates."""

    n: int
    source_count: int
    target_count: int
    defined_count: int
    target_member_count: int
    unique_output_count: int
    modified_defect: int
    target_pattern_avoid_count: int | None = None

    @property
    def defined_fraction(self) -> float:
        return self.defined_count / self.source_count if self.source_count else 1.0

    @property
    def target_fraction(self) -> float:
        return self.target_member_count / self.source_count if self.source_count else 1.0

    @property
    def injectivity_fraction(self) -> float:
        return self.unique_output_count / self.defined_count if self.defined_count else 0.0

    @property
    def mean_modified_defect(self) -> float:
        return self.modified_defect / self.defined_count if self.defined_count else float("inf")

    @property
    def target_pattern_fraction(self) -> float | None:
        if self.target_pattern_avoid_count is None:
            return None
        return self.target_pattern_avoid_count / self.defined_count if self.defined_count else 0.0


@dataclass(frozen=True)
class FiniteMapDiagnostics:
    n: int
    source_count: int
    target_count: int
    undefined_sources: tuple[ChainWord, ...]
    outside_target: tuple[tuple[ChainWord, ChainWord], ...]
    collisions: tuple[tuple[ChainWord, tuple[ChainWord, ...]], ...]
    missing_targets: tuple[ChainWord, ...]

    @property
    def injective(self) -> bool:
        return not self.collisions and not self.undefined_sources

    @property
    def into_target(self) -> bool:
        return not self.outside_target and not self.undefined_sources

    @property
    def surjective(self) -> bool:
        return not self.missing_targets and self.into_target

    @property
    def bijective(self) -> bool:
        return self.injective and self.surjective


def analyze_finite_map(
    transform: Transformation,
    source: WordPredicate,
    target: WordPredicate,
    *,
    universe,
    n: int,
    target_universe=None,
    degree_shift: int = 0,
) -> FiniteMapDiagnostics:
    """Return the complete finite map defect from degree n to n+degree_shift."""

    words = tuple(universe(n))
    src = tuple(x for x in words if source.holds(x))
    target_degree = n + degree_shift
    if target_degree < 0:
        raise ValueError("target degree cannot be negative")
    target_words = tuple((target_universe or universe)(target_degree))
    tgt = tuple(x for x in target_words if target.holds(x))
    target_by_key = {_word_key(x): x for x in tgt}
    undefined: list[ChainWord] = []
    outside: list[tuple[ChainWord, ChainWord]] = []
    preimages: dict[tuple[tuple[int, ...], int], list[ChainWord]] = {}
    output_word: dict[tuple[tuple[int, ...], int], ChainWord] = {}
    for x in src:
        if not transform.defined_on(x):
            undefined.append(x)
            continue
        y = transform.apply(x).output
        key = _word_key(y)
        output_word[key] = y
        preimages.setdefault(key, []).append(x)
        if key not in target_by_key:
            outside.append((x, y))
    collisions = tuple(
        (output_word[key], tuple(pre))
        for key, pre in sorted(preimages.items())
        if len(pre) > 1
    )
    image_target_keys = set(preimages) & set(target_by_key)
    missing = tuple(target_by_key[key] for key in sorted(set(target_by_key) - image_target_keys))
    return FiniteMapDiagnostics(
        n=n,
        source_count=len(src),
        target_count=len(tgt),
        undefined_sources=tuple(undefined),
        outside_target=tuple(outside),
        collisions=collisions,
        missing_targets=missing,
    )


@dataclass(frozen=True)
class CandidateEvaluation:
    transform: Transformation
    cost: int
    verified_through: int
    failure: SynthesisFailure | None
    diagnostics: CandidateDiagnostics | None = None
    finite_map_fingerprint: str | None = None

    @property
    def exact(self) -> bool:
        return self.failure is None


@dataclass(frozen=True)
class SynthesisReport:
    candidates_tested: int
    normalized_candidates: int
    exact: tuple[CandidateEvaluation, ...]
    ranked: tuple[CandidateEvaluation, ...]


def transformation_cost(transform: Transformation) -> int:
    if isinstance(transform, Compose):
        return sum(transformation_cost(part) for part in transform.parts)
    return int(getattr(transform, "search_cost", 1))


def _word_key(word: ChainWord) -> tuple[tuple[int, ...], int]:
    return word.values, word.height


def _candidate_key(transform: Transformation) -> tuple[str, str]:
    nf = transform.normal_form()
    return type(nf).__name__, repr(nf)


def enumerate_transform_programs(
    atoms: Iterable[Transformation],
    *,
    max_cost: int,
    seed: Transformation | None = None,
    max_steps: int | None = None,
) -> tuple[Transformation, ...]:
    """Enumerate normalized transformation programs up to a weighted cost.

    Search is intentionally over the AC algebra, not arbitrary Python programs.
    ``seed`` is useful for targeted searches such as ``Reverse >> repair``.
    Equivalent programs eliminated by the current normalizer are emitted once.
    """

    atoms = tuple(atoms)
    seed = Identity() if seed is None else seed.normal_form()
    seed_cost = transformation_cost(seed)
    if seed_cost > max_cost:
        return ()

    seen: dict[tuple[str, str], Transformation] = {_candidate_key(seed): seed}
    frontier: list[tuple[Transformation, int, int]] = [(seed, seed_cost, 0)]
    out: list[Transformation] = [seed]

    while frontier:
        current, current_cost, steps = frontier.pop(0)
        if max_steps is not None and steps >= max_steps:
            continue
        for atom in atoms:
            cost = current_cost + transformation_cost(atom)
            if cost > max_cost:
                continue
            candidate = (current >> atom).normal_form()
            key = _candidate_key(candidate)
            if key in seen:
                continue
            seen[key] = candidate
            out.append(candidate)
            frontier.append((candidate, cost, steps + 1))

    out.sort(key=lambda t: (transformation_cost(t), repr(t)))
    return tuple(out)


def evaluate_bijection_candidate(
    transform: Transformation,
    source: WordPredicate,
    target: WordPredicate,
    *,
    universe,
    through: int,
    start: int = 1,
    target_universe=None,
    degree_shift: int = 0,
) -> CandidateEvaluation:
    """Test whether a candidate is a bijection from degree n to n+shift."""

    verified = start - 1
    failure: SynthesisFailure | None = None
    for n in range(start, through + 1):
        target_degree = n + degree_shift
        if target_degree < 0:
            raise ValueError("target degree cannot be negative")
        words = list(universe(n))
        target_words = list((target_universe or universe)(target_degree))
        src = [x for x in words if source.holds(x)]
        tgt = [x for x in target_words if target.holds(x)]
        tgt_keys = {_word_key(x) for x in tgt}
        outputs: list[ChainWord] = []
        for x in src:
            if not transform.defined_on(x):
                failure = SynthesisFailure(FailureKind.UNDEFINED, n, source=x)
                return CandidateEvaluation(transform, transformation_cost(transform), verified, failure)
            y = transform.apply(x).output
            if not target.holds(y):
                failure = SynthesisFailure(
                    FailureKind.OUTSIDE_TARGET,
                    n,
                    source=x,
                    output=y,
                )
                return CandidateEvaluation(transform, transformation_cost(transform), verified, failure)
            outputs.append(y)

        output_keys = [_word_key(y) for y in outputs]
        seen = {}
        for source_word, output_word, key in zip(src, outputs, output_keys):
            if key in seen:
                first_source = seen[key]
                failure = SynthesisFailure(
                    FailureKind.COLLISION, n, source=source_word, output=output_word,
                    detail=f"also image of {first_source.values}",
                    other_source=first_source,
                )
                return CandidateEvaluation(transform, transformation_cost(transform), verified, failure)
            seen[key] = source_word
        if set(output_keys) != tgt_keys:
            failure = SynthesisFailure(
                FailureKind.NOT_SURJECTIVE,
                n,
                detail=f"image={len(set(output_keys))}, target={len(tgt_keys)}",
            )
            return CandidateEvaluation(transform, transformation_cost(transform), verified, failure)
        verified = n

    return CandidateEvaluation(transform, transformation_cost(transform), verified, None)


def diagnose_candidate(
    transform: Transformation,
    source: WordPredicate,
    target: WordPredicate,
    *,
    universe,
    n: int,
    target_pattern: WordPredicate | None = None,
) -> CandidateDiagnostics:
    """Measure why an imperfect candidate fails at one probe degree.

    ``modified_defect`` is the total symmetric-difference size between First and
    literature Asctop in defined outputs.  It is zero exactly on the modified
    structural condition (Cayley-ness is still checked by ``target`` separately).
    """

    words = list(universe(n))
    src = [x for x in words if source.holds(x)]
    tgt = [x for x in words if target.holds(x)]
    outputs: list[ChainWord] = []
    target_members = 0
    defect = 0
    pattern_hits = 0 if target_pattern is not None else None

    for x in src:
        if not transform.defined_on(x):
            continue
        y = transform.apply(x).output
        outputs.append(y)
        if target.holds(y):
            target_members += 1
        defect += len(y.first_positions ^ y.ascent_tops)
        if target_pattern is not None and target_pattern.holds(y):
            assert pattern_hits is not None
            pattern_hits += 1

    return CandidateDiagnostics(
        n=n,
        source_count=len(src),
        target_count=len(tgt),
        defined_count=len(outputs),
        target_member_count=target_members,
        unique_output_count=len({_word_key(y) for y in outputs}),
        modified_defect=defect,
        target_pattern_avoid_count=pattern_hits,
    )


def _rank_key(ev: CandidateEvaluation):
    d = ev.diagnostics
    # Higher verified degree and target/defined/injective fractions are better;
    # lower structural defect and program cost are better.
    if d is None:
        return (-ev.verified_through, ev.cost, repr(ev.transform))
    return (
        -ev.verified_through,
        -d.target_fraction,
        -d.defined_fraction,
        -d.injectivity_fraction,
        d.mean_modified_defect,
        ev.cost,
        repr(ev.transform),
    )


def _precompute_degree_classes(source, target, universe, *, start: int, through: int, target_universe=None, degree_shift: int = 0):
    degrees = {}
    for n in range(start, through + 1):
        target_degree = n + degree_shift
        if target_degree < 0:
            raise ValueError("target degree cannot be negative")
        words = tuple(universe(n))
        target_words = tuple((target_universe or universe)(target_degree))
        src = tuple(x for x in words if source.holds(x))
        tgt = tuple(x for x in target_words if target.holds(x))
        degrees[n] = (src, tgt, frozenset(_word_key(x) for x in tgt))
    return degrees


def _evaluate_precomputed(transform, degrees, *, start: int, through: int) -> CandidateEvaluation:
    verified = start - 1
    for n in range(start, through + 1):
        src, tgt, tgt_keys = degrees[n]
        output_keys = []
        seen = {}
        for x in src:
            if not transform.defined_on(x):
                return CandidateEvaluation(
                    transform, transformation_cost(transform), verified,
                    SynthesisFailure(FailureKind.UNDEFINED, n, source=x),
                )
            y = transform.apply(x).output
            key = _word_key(y)
            if key not in tgt_keys:
                return CandidateEvaluation(
                    transform, transformation_cost(transform), verified,
                    SynthesisFailure(FailureKind.OUTSIDE_TARGET, n, source=x, output=y),
                )
            if key in seen:
                first_source = seen[key]
                return CandidateEvaluation(
                    transform, transformation_cost(transform), verified,
                    SynthesisFailure(
                        FailureKind.COLLISION, n, source=x, output=y,
                        detail=f"also image of {first_source.values}",
                        other_source=first_source,
                    ),
                )
            seen[key] = x
            output_keys.append(key)
        if set(output_keys) != tgt_keys:
            return CandidateEvaluation(
                transform, transformation_cost(transform), verified,
                SynthesisFailure(
                    FailureKind.NOT_SURJECTIVE, n,
                    detail=f"image={len(set(output_keys))}, target={len(tgt_keys)}",
                ),
            )
        verified = n
    return CandidateEvaluation(transform, transformation_cost(transform), verified, None)


def _diagnose_precomputed(transform, source_words, target_words, target_keys, *, n: int, target_pattern=None):
    outputs = []
    target_members = 0
    defect = 0
    pattern_hits = 0 if target_pattern is not None else None
    for x in source_words:
        if not transform.defined_on(x):
            continue
        y = transform.apply(x).output
        outputs.append(y)
        if _word_key(y) in target_keys:
            target_members += 1
        defect += len(y.first_positions ^ y.ascent_tops)
        if target_pattern is not None and target_pattern.holds(y):
            assert pattern_hits is not None
            pattern_hits += 1
    return CandidateDiagnostics(
        n=n,
        source_count=len(source_words),
        target_count=len(target_words),
        defined_count=len(outputs),
        target_member_count=target_members,
        unique_output_count=len({_word_key(y) for y in outputs}),
        modified_defect=defect,
        target_pattern_avoid_count=pattern_hits,
    )


def synthesize_bijections(
    source: WordPredicate,
    target: WordPredicate,
    *,
    universe,
    target_universe=None,
    degree_shift: int = 0,
    atoms: Iterable[Transformation],
    max_cost: int,
    through: int,
    seed: Transformation | None = None,
    max_steps: int | None = None,
    probe_n: int | None = None,
    target_pattern: WordPredicate | None = None,
    keep: int = 20,
    start: int = 1,
) -> SynthesisReport:
    """Bounded synthesis of low-complexity AC transformation programs.

    Source/target classes are materialized once per degree and shared by every
    candidate.  This makes bounded algebra search practical while preserving the
    reference semantics used by standalone candidate evaluation.
    """

    programs = enumerate_transform_programs(
        atoms,
        max_cost=max_cost,
        seed=seed,
        max_steps=max_steps,
    )
    target_universe = target_universe or universe
    degrees = _precompute_degree_classes(
        source,
        target,
        universe,
        start=start,
        through=through,
        target_universe=target_universe,
        degree_shift=degree_shift,
    )
    if probe_n is not None and probe_n not in degrees:
        target_n = probe_n + degree_shift
        if target_n < 0:
            raise ValueError("probe degree and shift produce a negative target degree")
        words = tuple(universe(probe_n))
        target_words = tuple(target_universe(target_n))
        src = tuple(x for x in words if source.holds(x))
        tgt = tuple(x for x in target_words if target.holds(x))
        probe_data = (src, tgt, frozenset(_word_key(x) for x in tgt))
    elif probe_n is not None:
        probe_data = degrees[probe_n]
    else:
        probe_data = None

    evaluated: list[CandidateEvaluation] = []
    exact: list[CandidateEvaluation] = []
    for program in programs:
        sig = program.signature
        if sig.delta_length != degree_shift:
            continue
        ev = _evaluate_precomputed(program, degrees, start=start, through=through)
        if probe_data is not None:
            src, tgt, tgt_keys = probe_data
            diag = _diagnose_precomputed(
                program, src, tgt, tgt_keys,
                n=probe_n, target_pattern=target_pattern,
            )
            ev = CandidateEvaluation(ev.transform, ev.cost, ev.verified_through, ev.failure, diag)
        evaluated.append(ev)
        if ev.exact:
            exact.append(ev)

    evaluated.sort(key=_rank_key)
    exact.sort(key=lambda ev: (ev.cost, repr(ev.transform)))
    return SynthesisReport(
        candidates_tested=len(programs),
        normalized_candidates=len(evaluated),
        exact=tuple(exact),
        ranked=tuple(evaluated[:keep]),
    )
