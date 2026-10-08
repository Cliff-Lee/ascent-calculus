"""Versioned mathematical specification for reproducible AC searches.

The specification describes the finite mathematical question only.  Execution
budgets, worker state, and machine-specific performance limits belong to the
runtime record, not to the class definitions or degree offsets.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import cached_property
from hashlib import sha256
import json
from typing import Literal

from ac.discovery.statistics import STATISTICS
from ac.logic.predicates import AscentSequence, Modified, Revised, WordPredicate
from ac.patterns.classical import ClassicalPattern


SPEC_FORMAT = "ascent-machine-search-spec"
SPEC_VERSION = 1
SEMANTICS_VERSION = "ac-positive-cayley-v1"
FAMILIES = ("ordinary", "modified", "revised")
GOALS = ("enumerate", "count_equivalence", "profile_equivalence", "bijection_search")
RULE_MODES = ("avoid", "contain")


def _strict_int(value, name: str) -> int:
    if type(value) is not int:
        raise ValueError(f"{name} must be an integer (booleans and decimal values are not accepted)")
    return value


@dataclass(frozen=True, order=True)
class PatternRuleSpec:
    """Classical Cayley pattern requirement with conjunctive semantics."""

    mode: Literal["avoid", "contain"]
    pattern: tuple[int, ...]

    def __post_init__(self) -> None:
        if self.mode not in RULE_MODES:
            raise ValueError("pattern mode must be 'avoid' or 'contain'")
        if not isinstance(self.pattern, tuple) or not self.pattern:
            raise ValueError("pattern must be a nonempty tuple of positive integers")
        if any(type(value) is not int for value in self.pattern):
            raise ValueError("pattern entries must be integers; booleans and decimal values are not accepted")
        try:
            canonical = ClassicalPattern(self.pattern).values
        except (TypeError, ValueError) as exc:
            raise ValueError(f"invalid classical Cayley pattern: {exc}") from exc
        object.__setattr__(self, "pattern", canonical)

    @classmethod
    def build(cls, mode: str, pattern) -> "PatternRuleSpec":
        """Convenience constructor for a tuple, list, or compact pattern string."""
        if isinstance(pattern, str):
            parsed = ClassicalPattern(pattern).values
        else:
            parsed = tuple(pattern)
        return cls(mode, parsed)

    def to_dict(self) -> dict:
        return {"mode": self.mode, "pattern": list(self.pattern)}

    @classmethod
    def from_dict(cls, raw: dict) -> "PatternRuleSpec":
        if not isinstance(raw, dict):
            raise ValueError("each pattern rule must be an object")
        if set(raw) != {"mode", "pattern"}:
            raise ValueError("pattern rule fields must be exactly 'mode' and 'pattern'")
        pattern = raw["pattern"]
        if not isinstance(pattern, list):
            raise ValueError("serialized pattern must be an array of integers")
        return cls(raw["mode"], tuple(pattern))


@dataclass(frozen=True)
class _PatternRulePredicate(WordPredicate):
    rule: PatternRuleSpec

    @cached_property
    def _compiled(self):
        return ClassicalPattern(self.rule.pattern).compile()

    def holds(self, word) -> bool:
        found = self._compiled.contains(word)
        return found if self.rule.mode == "contain" else not found


@dataclass(frozen=True)
class ClassSpec:
    """An ordinary, modified, or revised class with conjunctive pattern rules."""

    family: Literal["ordinary", "modified", "revised"]
    rules: tuple[PatternRuleSpec, ...] = ()

    def __post_init__(self) -> None:
        if self.family not in FAMILIES:
            raise ValueError("family must be ordinary, modified, or revised")
        if not isinstance(self.rules, tuple) or any(not isinstance(rule, PatternRuleSpec) for rule in self.rules):
            raise ValueError("rules must be a tuple of PatternRuleSpec objects")
        # Rule order and duplicate copies do not alter a conjunction.  Normalize
        # them once so fingerprints do not depend on palette/drop order.
        normalized = tuple(sorted(set(self.rules), key=lambda rule: (rule.mode, rule.pattern)))
        object.__setattr__(self, "rules", normalized)

    @classmethod
    def build(cls, family: str, rules=()) -> "ClassSpec":
        built = tuple(
            rule if isinstance(rule, PatternRuleSpec) else PatternRuleSpec.build(rule["mode"], rule["pattern"])
            for rule in rules
        )
        return cls(family, built)

    def to_dict(self) -> dict:
        return {"family": self.family, "rules": [rule.to_dict() for rule in self.rules]}

    @classmethod
    def from_dict(cls, raw: dict) -> "ClassSpec":
        if not isinstance(raw, dict):
            raise ValueError("class specification must be an object")
        if set(raw) != {"family", "rules"}:
            raise ValueError("class fields must be exactly 'family' and 'rules'")
        if not isinstance(raw["rules"], list):
            raise ValueError("class rules must be an array")
        return cls(raw["family"], tuple(PatternRuleSpec.from_dict(rule) for rule in raw["rules"]))

    def predicate(self) -> WordPredicate:
        base = {
            "ordinary": AscentSequence,
            "modified": Modified,
            "revised": Revised,
        }[self.family]()
        result = base
        for rule in self.rules:
            result = result & _PatternRulePredicate(rule)
        return result

    def describe(self) -> str:
        family_name = {"ordinary": "ordinary", "modified": "modified", "revised": "revised"}[self.family]
        if not self.rules:
            return f"{family_name} ascent sequences"
        clauses = [f"{rule.mode} {ClassicalPattern(rule.pattern)}" for rule in self.rules]
        return f"{family_name} ascent sequences satisfying " + " and ".join(clauses)


@dataclass(frozen=True)
class DegreeWindow:
    """Inclusive range of base degrees n."""

    start: int
    stop: int

    def __post_init__(self) -> None:
        start = _strict_int(self.start, "degree-window start")
        stop = _strict_int(self.stop, "degree-window stop")
        if start < 1 or stop < start:
            raise ValueError("degree window must satisfy 1 <= start <= stop")

    def to_dict(self) -> dict:
        return {"start": self.start, "stop": self.stop}

    @classmethod
    def from_dict(cls, raw: dict) -> "DegreeWindow":
        if not isinstance(raw, dict) or set(raw) != {"start", "stop"}:
            raise ValueError("degree window must contain exactly 'start' and 'stop'")
        return cls(raw["start"], raw["stop"])


@dataclass(frozen=True)
class SearchSpec:
    """Exact, versioned question submitted to a finite search or worker.

    Offsets are relative to the same base degree n: the source is tested at
    ``n + source_offset`` and the target at ``n + target_offset``.  An offset
    changes degree only; it does not shift pattern values or statistics.
    """

    goal: Literal["enumerate", "count_equivalence", "profile_equivalence", "bijection_search"]
    source: ClassSpec
    degrees: DegreeWindow
    target: ClassSpec | None = None
    source_offset: int = 0
    target_offset: int = 0
    statistic: str | None = None

    def __post_init__(self) -> None:
        if self.goal not in GOALS:
            raise ValueError(f"goal must be one of: {', '.join(GOALS)}")
        if not isinstance(self.source, ClassSpec):
            raise ValueError("source must be a ClassSpec")
        if not isinstance(self.degrees, DegreeWindow):
            raise ValueError("degrees must be a DegreeWindow")
        source_offset = _strict_int(self.source_offset, "source degree offset")
        target_offset = _strict_int(self.target_offset, "target degree offset")
        needs_target = self.goal != "enumerate"
        if needs_target and not isinstance(self.target, ClassSpec):
            raise ValueError(f"goal '{self.goal}' requires a target class")
        if not needs_target and self.target is not None:
            raise ValueError("enumeration has one class and cannot specify a target")
        if self.goal == "enumerate" and target_offset != 0:
            raise ValueError("target offset is only meaningful when a target class is present")
        if self.goal == "profile_equivalence":
            if not isinstance(self.statistic, str) or self.statistic not in STATISTICS or self.statistic == "none":
                raise ValueError("profile equivalence requires a supported non-count statistic")
        elif self.statistic is not None and (
            not isinstance(self.statistic, str) or self.statistic not in STATISTICS
        ):
            raise ValueError("statistic must be a supported AC statistic identifier")
        if self.source_offset + self.degrees.start < 1:
            raise ValueError("source offset makes the first requested object degree less than 1")
        if self.target is not None and self.target_offset + self.degrees.start < 1:
            raise ValueError("target offset makes the first requested object degree less than 1")

    @property
    def degree_shift(self) -> int:
        """Target degree minus source degree for every base degree n."""
        if self.target is None:
            raise ValueError("single-class enumeration has no target degree shift")
        return self.target_offset - self.source_offset

    @property
    def is_count_only(self) -> bool:
        return self.goal == "count_equivalence" and self.statistic in (None, "none")

    def degrees_for(self, base_degree: int) -> tuple[int, int | None]:
        if type(base_degree) is not int or not self.degrees.start <= base_degree <= self.degrees.stop:
            raise ValueError("base degree lies outside the specified inclusive window")
        source_degree = base_degree + self.source_offset
        target_degree = None if self.target is None else base_degree + self.target_offset
        return source_degree, target_degree

    def to_dict(self) -> dict:
        return {
            "format": SPEC_FORMAT,
            "version": SPEC_VERSION,
            "semantics": SEMANTICS_VERSION,
            "goal": self.goal,
            "source": self.source.to_dict(),
            "target": None if self.target is None else self.target.to_dict(),
            "degrees": self.degrees.to_dict(),
            "source_offset": self.source_offset,
            "target_offset": self.target_offset,
            "statistic": self.statistic,
        }

    def canonical_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, sort_keys=True, separators=(",", ":"))

    @property
    def fingerprint(self) -> str:
        return sha256(self.canonical_json().encode("utf-8")).hexdigest()

    def describe(self) -> str:
        start, stop = self.degrees.start, self.degrees.stop
        source_degree = f"n{self.source_offset:+d}" if self.source_offset else "n"
        summary = f"For n={start}…{stop}, {self.source.describe()} at degree {source_degree}"
        if self.target is None:
            return summary + "."
        target_degree = f"n{self.target_offset:+d}" if self.target_offset else "n"
        if self.goal == "count_equivalence":
            verb = "compare counts with"
            if self.statistic not in (None, "none"):
                verb = f"compare counts and {STATISTICS[self.statistic].lower()} profiles with"
        elif self.goal == "profile_equivalence":
            verb = f"compare {STATISTICS[self.statistic].lower()} profiles with"
        else:
            verb = "search for a finite bijection to"
        return f"{summary}; {verb} {self.target.describe()} at degree {target_degree}."

    @classmethod
    def from_dict(cls, raw: dict) -> "SearchSpec":
        expected = {
            "format", "version", "semantics", "goal", "source", "target", "degrees",
            "source_offset", "target_offset", "statistic",
        }
        if not isinstance(raw, dict) or set(raw) != expected:
            raise ValueError("search specification fields do not match the version-1 schema")
        if raw["format"] != SPEC_FORMAT or type(raw["version"]) is not int or raw["version"] != SPEC_VERSION:
            raise ValueError("unsupported search specification format or version")
        if raw["semantics"] != SEMANTICS_VERSION:
            raise ValueError("search specification uses an unknown ascent-sequence semantics version")
        target = None if raw["target"] is None else ClassSpec.from_dict(raw["target"])
        return cls(
            raw["goal"],
            ClassSpec.from_dict(raw["source"]),
            DegreeWindow.from_dict(raw["degrees"]),
            target,
            raw["source_offset"],
            raw["target_offset"],
            raw["statistic"],
        )

    @classmethod
    def from_json(cls, payload: str) -> "SearchSpec":
        try:
            raw = json.loads(payload)
        except (TypeError, json.JSONDecodeError) as exc:
            raise ValueError(f"invalid search specification JSON: {exc}") from exc
        return cls.from_dict(raw)
