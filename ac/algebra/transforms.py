from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from ac.core.word import ChainWord
from ac.logic.selectors import PositionCutSelector, PositionSelector
from ac.transform.basic import (
    TransformResult,
    complement,
    insert_at_selected_cuts,
    inverse_prefix_lift,
    prefix_lift,
    reverse,
)
from ac.transform.restrict import restrict_positions, compress_levels, standardize
from ac.transform.hat import hat, inverse_hat


@dataclass(frozen=True)
class TransformSignature:
    """Coarse transformation metadata used for pruning/search."""

    delta_length: int | None = 0
    delta_height: int | None = 0
    preserves_occurrence_ids: bool = True
    partial: bool = False


class Transformation:
    """Typed symbolic transformation expression."""

    signature = TransformSignature()
    search_cost = 1

    def apply(self, word: ChainWord) -> TransformResult:
        raise NotImplementedError

    def defined_on(self, word: ChainWord) -> bool:
        try:
            self.apply(word)
            return True
        except (ValueError, IndexError):
            return False

    def __rshift__(self, other: "Transformation") -> "Transformation":
        if not isinstance(other, Transformation):
            raise TypeError("transformation composition requires another Transformation")
        return Compose((self, other)).normal_form()

    def normal_form(self) -> "Transformation":
        return self

    def inverse(self) -> "Transformation":
        """Return a symbolic inverse when AC knows an exact partial inverse.

        Transformations such as restriction and standardization are deliberately
        not assigned a fake inverse here: their inverse is relational and will
        belong to the later correspondence layer.
        """
        raise TypeError(f"{type(self).__name__} has no functional inverse in the current calculus")


@dataclass(frozen=True)
class Identity(Transformation):
    search_cost = 0
    def apply(self, word: ChainWord) -> TransformResult:
        return TransformResult(
            word,
            position_map=tuple(range(1, len(word) + 1)),
            value_map=tuple(range(1, word.height + 1)),
        )

    def inverse(self) -> Transformation:
        return self


@dataclass(frozen=True)
class ReverseT(Transformation):
    def apply(self, word: ChainWord) -> TransformResult:
        return reverse(word)

    def inverse(self) -> Transformation:
        return self


@dataclass(frozen=True)
class ComplementT(Transformation):
    def apply(self, word: ChainWord) -> TransformResult:
        return complement(word)

    def inverse(self) -> Transformation:
        return self


@dataclass(frozen=True)
class PrefixLiftT(Transformation):
    position: int
    signature = TransformSignature(delta_length=0, delta_height=None, partial=True)

    def apply(self, word: ChainWord) -> TransformResult:
        return prefix_lift(word, self.position)

    def inverse(self) -> Transformation:
        return InversePrefixLiftT(self.position)


@dataclass(frozen=True)
class InversePrefixLiftT(Transformation):
    position: int
    signature = TransformSignature(delta_length=0, delta_height=None, partial=True)

    def apply(self, word: ChainWord) -> TransformResult:
        return inverse_prefix_lift(word, self.position)

    def inverse(self) -> Transformation:
        return PrefixLiftT(self.position)


@dataclass(frozen=True)
class RestrictT(Transformation):
    positions: tuple[int, ...]
    signature = TransformSignature(delta_length=None, delta_height=0, partial=True)

    def __init__(self, positions):
        object.__setattr__(self, "positions", tuple(int(i) for i in positions))

    def apply(self, word: ChainWord) -> TransformResult:
        return restrict_positions(word, self.positions)


@dataclass(frozen=True)
class RestrictSelectedT(Transformation):
    selector: PositionSelector
    signature = TransformSignature(delta_length=None, delta_height=0, partial=False)

    def apply(self, word: ChainWord) -> TransformResult:
        positions = sorted(int(p) for p in self.selector.evaluate(word))
        return restrict_positions(word, positions)


@dataclass(frozen=True)
class CompressLevelsT(Transformation):
    signature = TransformSignature(delta_length=0, delta_height=None, partial=False)

    def apply(self, word: ChainWord) -> TransformResult:
        return compress_levels(word)


@dataclass(frozen=True)
class StandardizeT(Transformation):
    signature = TransformSignature(delta_length=0, delta_height=None, partial=False)

    def apply(self, word: ChainWord) -> TransformResult:
        return standardize(word)


@dataclass(frozen=True)
class InsertSelectedT(Transformation):
    selector: PositionCutSelector
    value: int
    signature = TransformSignature(delta_length=None, delta_height=0, partial=True)

    def apply(self, word: ChainWord) -> TransformResult:
        return insert_at_selected_cuts(word, self.selector, self.value)


@dataclass(frozen=True)
class HatT(Transformation):
    """Classical hat sweep, exposed as a symbolic search generator."""

    signature = TransformSignature(delta_length=0, delta_height=None, partial=False)
    search_cost = 2

    def apply(self, word: ChainWord) -> TransformResult:
        return _result_from_final(word, hat(word))

    def inverse(self) -> Transformation:
        return InverseHatT()


@dataclass(frozen=True)
class InverseHatT(Transformation):
    """Partial inverse-hat transformation."""

    signature = TransformSignature(delta_length=0, delta_height=None, partial=True)
    search_cost = 2

    def apply(self, word: ChainWord) -> TransformResult:
        return _result_from_final(word, inverse_hat(word))

    def inverse(self) -> Transformation:
        return HatT()


@dataclass(frozen=True)
class SweepLiftT(Transformation):
    """Snapshot-selected sequential prefix-lift sweep.

    The selector is evaluated once on the input word.  Because lifts do not
    change positions, the resulting positional schedule remains meaningful.
    This gives synthesis access to the generic event-driven operation behind
    hat-like maps without hard-coding a new named bijection for every event set.
    """

    selector: PositionSelector
    inverse_lift: bool = False
    direction: str = "ltr"
    signature = TransformSignature(delta_length=0, delta_height=None, partial=True)
    search_cost = 2

    def __post_init__(self) -> None:
        if self.direction not in {"ltr", "rtl"}:
            raise ValueError("direction must be 'ltr' or 'rtl'")

    def apply(self, word: ChainWord) -> TransformResult:
        positions = sorted(
            (int(p) for p in self.selector.evaluate(word)),
            reverse=self.direction == "rtl",
        )
        y = word
        for position in positions:
            if self.inverse_lift:
                y = inverse_prefix_lift(y, position).output
            else:
                y = prefix_lift(y, position).output
        return _result_from_final(word, y)


def _result_from_final(source: ChainWord, output: ChainWord) -> TransformResult:
    output_by_id = {pid: i for i, pid in enumerate(output.position_ids, start=1)}
    pmap = tuple(output_by_id.get(pid) for pid in source.position_ids)
    source_ids = set(source.position_ids)
    created_ids = tuple(pid for pid in output.position_ids if pid not in source_ids)
    created_positions = tuple(output_by_id[pid] for pid in created_ids)
    return TransformResult(
        output,
        position_map=pmap,
        value_map=None,
        created_positions=created_positions,
        created_position_ids=created_ids,
    )


@dataclass(frozen=True)
class Compose(Transformation):
    """Left-to-right transformation composition.

    ``Compose((A,B)).apply(x)`` means ``B(A(x))``.  This agrees with the DSL
    spelling ``A >> B`` / pipeline reading.
    """

    parts: tuple[Transformation, ...]

    def __init__(self, parts: Iterable[Transformation]):
        object.__setattr__(self, "parts", tuple(parts))

    @property
    def signature(self) -> TransformSignature:
        dn: int | None = 0
        dh: int | None = 0
        partial = False
        ids = True
        for part in self.parts:
            sig = part.signature
            partial = partial or sig.partial
            ids = ids and sig.preserves_occurrence_ids
            if dn is not None and sig.delta_length is not None:
                dn += sig.delta_length
            else:
                dn = None
            if dh is not None and sig.delta_height is not None:
                dh += sig.delta_height
            else:
                dh = None
        return TransformSignature(dn, dh, ids, partial)

    def apply(self, word: ChainWord) -> TransformResult:
        y = word
        for part in self.parts:
            y = part.apply(y).output
        return _result_from_final(word, y)

    def normal_form(self) -> Transformation:
        # Flatten nested compositions and remove identities first.
        flat: list[Transformation] = []
        for part in self.parts:
            p = part.normal_form()
            if isinstance(p, Identity):
                continue
            if isinstance(p, Compose):
                flat.extend(p.parts)
            else:
                flat.append(p)

        # Canonicalize each maximal run in the Klein-four subgroup <R,C>.
        out: list[Transformation] = []
        r_parity = c_parity = 0

        def flush_symmetry() -> None:
            nonlocal r_parity, c_parity
            if r_parity:
                out.append(ReverseT())
            if c_parity:
                out.append(ComplementT())
            r_parity = c_parity = 0

        for part in flat:
            if isinstance(part, ReverseT):
                r_parity ^= 1
            elif isinstance(part, ComplementT):
                c_parity ^= 1
            else:
                flush_symmetry()
                out.append(part)
        flush_symmetry()

        if not out:
            return Identity()
        if len(out) == 1:
            return out[0]
        return Compose(tuple(out))

    def inverse(self) -> Transformation:
        return Compose(tuple(part.inverse() for part in reversed(self.parts))).normal_form()


# Notebook-friendly constructors.
def R() -> ReverseT:
    return ReverseT()


def C() -> ComplementT:
    return ComplementT()


def L(position: int) -> PrefixLiftT:
    return PrefixLiftT(position)


def Linv(position: int) -> InversePrefixLiftT:
    return InversePrefixLiftT(position)


def Restrict(positions) -> RestrictT:
    return RestrictT(positions)


def RestrictSelected(selector: PositionSelector) -> RestrictSelectedT:
    return RestrictSelectedT(selector)


def Compress() -> CompressLevelsT:
    return CompressLevelsT()


def Std() -> StandardizeT:
    return StandardizeT()


def Hat() -> HatT:
    return HatT()


def HatInv() -> InverseHatT:
    return InverseHatT()


def SweepLift(selector: PositionSelector, *, inverse: bool = False, direction: str = "ltr") -> SweepLiftT:
    return SweepLiftT(selector, inverse_lift=inverse, direction=direction)
