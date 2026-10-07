from __future__ import annotations

from collections import Counter
from dataclasses import asdict
from typing import Callable

from ac.core.word import ChainWord
from ac.classes.theories import is_ascent_sequence, is_modified, is_revised
from ac.generate.universes import modified_via_hat
from ac.discovery.fibre_geometry import fibre_gaps, contains_repeated_sandwich
from ac.discovery.local_repair import (
    ExtremeGapSwap,
    GapSwapRepair,
    canonical_defect_rotation,
    modified_defect,
    repair_modified_defects,
    rotate_interval,
)
from ac.discovery.proof_extraction import (
    fibre_orientation,
    orientation_profile,
    extreme_gap_proof_trace_2122_to_2212,
    defect_value_potential,
    certify_defect_rotation,
    defect_admissibility,
    repair_heavy_crossing_values,
)
from ac.transform.basic import reverse


DEFINITIONS = {
    "First": "The first occurrence of this value in the whole word.",
    "AscTop": "Position 1 by convention, or a position whose immediately preceding value is smaller.",
    "AscBottom": "Position 1 by convention, or the left endpoint of an adjacent rise.",
    "DefectFirst": "A first occurrence that is not currently an ascent top (First \\ AscTop).",
    "DefectTop": "An ascent top that is not a first occurrence (AscTop \\ First).",
    "RunStart": "Position 1, or a position not entered by an ascent.",
    "Orientation": "For a repeated value, records whether lower-valued material occurs only in its first gap, only in its last gap, both, or neither.",
    "Potential": "Proof-oriented defect potential: sum (n+1)^(height-value) over false-first defects.",
    "HeavyCrossing": "A multiplicity >=3 fibre meeting both blocks of a canonical repair. It obstructs the original one-pass repair proof; the alternating repair handles observed cases, while its general termination and preservation remain open.",
}


def parse_word(spec: str | list[int] | tuple[int, ...]) -> ChainWord:
    if isinstance(spec, (list, tuple)):
        vals = tuple(int(v) for v in spec)
    else:
        text = str(spec).strip()
        if not text:
            raise ValueError("word is empty")
        if any(ch in text for ch in " ,;"):
            vals = tuple(int(v) for v in text.replace(",", " ").replace(";", " ").split())
        else:
            if not text.isdigit() or "0" in text:
                raise ValueError("compact words must use positive single-digit values")
            vals = tuple(int(ch) for ch in text)
    return ChainWord(vals)


def _orientation_rows(word: ChainWord):
    rows = []
    for value in range(1, word.height + 1):
        fibre = word.fibre(value)
        if not fibre:
            continue
        gaps = []
        for g in fibre_gaps(word, value):
            gaps.append({
                "gap": g.gap_index,
                "left_position": g.left_position,
                "right_position": g.right_position,
                "positions": list(range(g.left_position + 1, g.right_position)),
                "lower_positions": list(g.lower_positions),
            })
        rows.append({
            "value": value,
            "fibre": list(fibre),
            "multiplicity": len(fibre),
            "orientation": fibre_orientation(word, value).value,
            "gaps": gaps,
        })
    return rows


def _position_rows(word: ChainWord):
    defect = modified_defect(word)
    rows = []
    for pos in range(1, len(word) + 1):
        value = word.at(pos)
        fibre = word.fibre(value)
        first = pos in word.first_positions
        top = pos in word.ascent_tops
        prev_value = word.at(pos - 1) if pos > 1 else None
        next_value = word.at(pos + 1) if pos < len(word) else None
        reasons = []
        if first:
            reasons.append(f"First: no earlier {value}; fibre positions are {list(fibre)}.")
        else:
            reasons.append(f"Not First: {value} already occurs at position {fibre[0]}.")
        if pos == 1:
            reasons.append("AscTop: position 1 is included by the literature convention.")
        elif prev_value < value:
            reasons.append(f"AscTop: {prev_value} < {value} across edge {pos-1}->{pos}.")
        else:
            reasons.append(f"Not AscTop: {prev_value} is not < {value} across edge {pos-1}->{pos}.")
        if pos in defect.first_not_top:
            reasons.append("Defect: this position is First but not AscTop.")
        if pos in defect.top_not_first:
            reasons.append("Defect: this position is AscTop but not First.")
        rows.append({
            "position": pos,
            "position_id": word.position_id(pos),
            "value": value,
            "occurrence_rank": word.occurrence_rank(pos),
            "first": first,
            "last": pos in word.last_positions,
            "asc_top": top,
            "asc_bottom": pos in word.ascent_bottoms,
            "run_start": pos in word.run_starts,
            "run_end": pos in word.run_ends,
            "defect_first_not_top": pos in defect.first_not_top,
            "defect_top_not_first": pos in defect.top_not_first,
            "previous_value": prev_value,
            "next_value": next_value,
            "reasons": reasons,
        })
    return rows


def inspect_word(word: ChainWord | str | list[int] | tuple[int, ...]):
    if not isinstance(word, ChainWord):
        word = parse_word(word)
    defect = modified_defect(word)
    return {
        "word": str(word),
        "values": list(word.values),
        "height": word.height,
        "length": len(word),
        "is_cayley": word.is_cayley,
        "is_ascent_sequence": is_ascent_sequence(word),
        "is_modified": is_modified(word),
        "is_revised": is_revised(word),
        "avoids_2122": not contains_repeated_sandwich(word, 1, 2),
        "avoids_2212": not contains_repeated_sandwich(word, 2, 1),
        "first_positions": sorted(word.first_positions),
        "ascent_tops": sorted(word.ascent_tops),
        "ascent_bottoms": sorted(word.ascent_bottoms),
        "run_starts": sorted(word.run_starts),
        "defect": {
            "first_not_top": list(defect.first_not_top),
            "top_not_first": list(defect.top_not_first),
            "size": defect.size,
        },
        "potential": defect_value_potential(word),
        "positions": _position_rows(word),
        "fibres": _orientation_rows(word),
        "orientation_profile": [o.value for o in orientation_profile(word)],
        "definitions": DEFINITIONS,
    }


def _state_summary(word: ChainWord):
    d = modified_defect(word)
    return {
        "inspection": inspect_word(word),
        "defect_admissibility": asdict(defect_admissibility(word)),
    }


def trace_gap_swap_repair(word: ChainWord | str, *, left_repeats: int = 2, right_repeats: int = 1):
    if not isinstance(word, ChainWord):
        word = parse_word(word)

    proof_gap = None
    if (left_repeats, right_repeats) == (2, 1):
        t = extreme_gap_proof_trace_2122_to_2212(word)
        proof_gap = {
            "source_right_oriented": t.source_right_oriented,
            "output_left_oriented": t.output_left_oriented,
            "strictly_increasing_pivots": t.strictly_increasing_pivots,
            "pattern_target_clean": t.pattern_target_clean,
            "steps": [
                {
                    "pivot": s.pivot,
                    "before": str(s.before),
                    "after": str(s.after),
                    "pivot_before": s.pivot_before.value,
                    "pivot_after": s.pivot_after.value,
                    "lower_projection_preserved": s.lower_projection_preserved,
                    "lower_orientations_preserved": s.lower_orientations_preserved,
                    "orientation_closed": s.orientation_closed,
                    "smaller_target_clean": s.smaller_target_clean,
                }
                for s in t.steps
            ],
        }

    swapped = ExtremeGapSwap(left_repeats, right_repeats).apply(word).output
    repair = repair_modified_defects(swapped)
    steps = []
    for idx, rule in enumerate(repair.rotations):
        before = repair.states[idx]
        after = repair.states[idx + 1]
        f, q, v, s = rule.pair.first_position, rule.pair.top_position, rule.pair.value, rule.start
        cert = certify_defect_rotation(before, rule)
        A = list(before.values[s - 1:f - 1])
        B = list(before.values[f - 1:q - 1])
        steps.append({
            "index": idx + 1,
            "before": _state_summary(before),
            "after": _state_summary(after),
            "pair": {"f": f, "q": q, "value": v},
            "interval": {"start": s, "end": rule.end, "left_amount": rule.left_amount},
            "block_a": A,
            "block_b": B,
            "before_ids": list(before.position_ids),
            "after_ids": list(after.position_ids),
            "potential_before": defect_value_potential(before),
            "potential_after": defect_value_potential(after),
            "heavy_crossing_values": list(repair_heavy_crossing_values(before, rule)),
            "certificate": asdict(cert),
        })

    return {
        "source": _state_summary(word),
        "parameters": {"left_repeats": left_repeats, "right_repeats": right_repeats},
        "gap_swap": {
            "output": _state_summary(swapped),
            "proof_trace": proof_gap,
        },
        "repair": {
            "terminated": repair.terminated,
            "reason": repair.reason,
            "steps": steps,
            "output": _state_summary(repair.output) if repair.output is not None else None,
        },
    }


def research_status():
    return {
        "overall": {
            "label": "open",
            "title": "Alternating gap-swap repair bijection",
            "detail": "The frozen alternating construction is verified through n=11. Its all-degree bijection proof remains open.",
        },
        "claims": [
            {
                "id": "orientation-2122",
                "label": "proved",
                "title": "2122 avoidance = right-oriented fibres",
                "detail": "The repeated-sandwich fibre-gap characterization is established in the proof extraction layer.",
            },
            {
                "id": "orientation-2212",
                "label": "proved",
                "title": "2212 avoidance = left-oriented fibres",
                "detail": "The repeated-sandwich fibre-gap characterization is established in the proof extraction layer.",
            },
            {
                "id": "local-repair",
                "label": "proved",
                "title": "One canonical repair exchanges ascent-top identity q -> f",
                "detail": "A local boundary calculation proves the ascent-top exchange and characterizes first-occurrence changes.",
            },
            {
                "id": "finite-bijection",
                "label": "verified",
                "verified_through": 10,
                "title": "One-pass GapSwapRepair maps M(2122) to M(2212)",
                "detail": "The original one-pass construction is verified through n=10, but it is not the current candidate: its degree-11 failure is recorded below.",
            },
            {
                "id": "reachable-fibre-shielding",
                "label": "counterexample",
                "title": "One-pass no-heavy-crossing claim fails at n=11",
                "detail": "For the old one-pass rule, the first canonical repair has value 4 (multiplicity 3) in both A and B. Source 12321443542 reaches terminal state 12143544232 with pair (f,q,v)=(5,10,3), A=[4], B=[3,5,4,4,2]. This refutes that proof route, not the alternating candidate.",
                "witness": "12321443542",
            },
            {
                "id": "generic-repair-warning",
                "label": "counterexample",
                "title": "Local admissibility alone does not guarantee safe repeated repair",
                "detail": "14323312 -> 13243312 is locally valid, but the next repair has heavy value 3 crossing both blocks. Reachability/provenance matters.",
                "witness": "14323312",
            },
            {
                "id": "n11-audit",
                "priority": 0,
                "label": "verified",
                "verified_through": 11,
                "title": "Alternating construction is bijective through degree 11",
                "detail": "Exhaustive check: 1,248,595 sources map to 1,248,595 distinct targets. All terminate in the modified 2212-avoiding class; no cycles, stalls, unpaired defects, target failures, collisions, or missing targets. Finite evidence only.",
            },
            {
                "id": "alternating-repair-taxonomy",
                "priority": 1,
                "label": "open",
                "title": "Alternating repair termination and state taxonomy",
                "detail": "The current proof campaign must explain which defect types M-repair and O-repair can create, and prove that alternation terminates and preserves the target class. This is the next open proof obligation.",
            },
            {
                "id": "bijection-candidate-n11",
                "label": "counterexample",
                "title": "The original one-pass repair fails at degree 11",
                "detail": "This is a counterexample to the old GapSwapRepair(2,1) rule, not the alternating candidate. The frozen M/O alternating algorithm was independently checked through degree 11.",
                "witness": "12321443542",
            },
            {
                "id": "alternating-traces-n11",
                "label": "verified",
                "verified_through": 11,
                "title": "Rare degree-11 traces exercise the new branch",
                "detail": "The three longest observed traces are M→O→M for 12321443542, M→M→M for 12324215432, and M→O→M for 12324431542. Only two degree-11 words use the orientation-repair branch.",
            },
        ],
    }


def interface_contract():
    return {
        "tasks": [
            "Inspect a sequence and explain structural roles position-by-position.",
            "Apply ExtremeGapSwap and inspect each pivot step.",
            "Step through CanonicalRepair with stable occurrence IDs and proof-oriented invariants.",
            "Compose a bounded count or class comparison from a family, pattern rules, range, and optional refinement.",
            "Reproduce an experiment from its serialized specification and inspect its finite result table.",
        ],
        "result_labels": {
            "proved": "General statement supported by a recorded mathematical argument in the current proof layer.",
            "verified": "Finite computation only; always displayed with the maximum completed degree.",
            "open": "Not established. This includes incomplete runs and current proof obligations.",
            "counterexample": "A stated general claim is false; a concrete witness is available.",
        },
        "rule": "The interface renders engine results; combinatorial definitions and transformations are not reimplemented in the browser.",
    }


# --------------------------- bounded-check registry ---------------------------

def _source_m2122(x: ChainWord) -> bool:
    return is_modified(x) and not contains_repeated_sandwich(x, 1, 2)


def _source_m2212(x: ChainWord) -> bool:
    return is_modified(x) and not contains_repeated_sandwich(x, 2, 1)


def _source_modified(x: ChainWord) -> bool:
    return is_modified(x)


CLASS_REGISTRY: dict[str, tuple[str, Callable[[ChainWord], bool]]] = {
    "m2122": ("Modified & Avoid(2122)", _source_m2122),
    "m2212": ("Modified & Avoid(2212)", _source_m2212),
    "modified": ("Modified", _source_modified),
}


def _identity(x: ChainWord) -> ChainWord:
    return x


def _reverse(x: ChainWord) -> ChainWord:
    return reverse(x).output


TRANSFORM_REGISTRY: dict[str, tuple[str, Callable[[ChainWord], ChainWord]]] = {
    "identity": ("Identity", _identity),
    "reverse": ("Reverse", _reverse),
    "gap21": ("ExtremeGapSwap(2,1)", lambda x: ExtremeGapSwap(2, 1).apply(x).output),
    "repair21": ("GapSwapRepair(2,1)", lambda x: GapSwapRepair(2, 1).apply(x).output),
    "gap12": ("ExtremeGapSwap(1,2)", lambda x: ExtremeGapSwap(1, 2).apply(x).output),
    "repair12": ("GapSwapRepair(1,2)", lambda x: GapSwapRepair(1, 2).apply(x).output),
}


def bounded_check(source: str, target: str, transform: str, max_n: int = 8):
    if source not in CLASS_REGISTRY or target not in CLASS_REGISTRY:
        raise ValueError("unknown class")
    if transform not in TRANSFORM_REGISTRY:
        raise ValueError("unknown transformation")
    if not (1 <= max_n <= 10):
        raise ValueError("prototype bounded checks support 1 <= n <= 10")
    source_name, source_pred = CLASS_REGISTRY[source]
    target_name, target_pred = CLASS_REGISTRY[target]
    transform_name, transform_fn = TRANSFORM_REGISTRY[transform]

    rows = []
    first_failure = None
    all_ok = True
    for n in range(1, max_n + 1):
        universe = list(modified_via_hat(n))
        src = [x for x in universe if source_pred(x)]
        target_count = sum(1 for x in universe if target_pred(x))
        outputs: dict[tuple[int, ...], str] = {}
        outside = 0
        exceptions = 0
        collision = 0
        for x in src:
            try:
                y = transform_fn(x)
            except Exception as exc:  # prototype diagnostic boundary
                exceptions += 1
                if first_failure is None:
                    first_failure = {"n": n, "source": str(x), "kind": "undefined", "detail": str(exc)}
                continue
            if not target_pred(y):
                outside += 1
                if first_failure is None:
                    first_failure = {
                        "n": n,
                        "source": str(x),
                        "output": str(y),
                        "kind": "outside target",
                        "output_inspection": inspect_word(y),
                    }
            key = y.values
            if key in outputs:
                collision += 1
                if first_failure is None:
                    first_failure = {
                        "n": n,
                        "source": str(x),
                        "other_source": outputs[key],
                        "output": str(y),
                        "kind": "collision",
                    }
            else:
                outputs[key] = str(x)
        surjective = len(outputs) == target_count
        ok = not outside and not exceptions and not collision and len(src) == target_count == len(outputs)
        all_ok = all_ok and ok
        if not surjective and first_failure is None:
            first_failure = {"n": n, "kind": "not surjective", "detail": f"{len(outputs)} unique images vs {target_count} targets"}
        rows.append({
            "n": n,
            "source_count": len(src),
            "target_count": target_count,
            "unique_images": len(outputs),
            "outside_target": outside,
            "exceptions": exceptions,
            "collisions": collision,
            "surjective": surjective,
            "bijection_at_n": ok,
        })
        if not ok:
            break
    if all_ok and rows and rows[-1]["n"] == max_n:
        label = "verified"
        title = f"Verified through n={max_n}"
    else:
        label = "counterexample"
        title = "Counterexample found"
    return {
        "label": label,
        "title": title,
        "source": source_name,
        "target": target_name,
        "transformation": transform_name,
        "requested_max_n": max_n,
        "completed_through": rows[-1]["n"] if rows else 0,
        "rows": rows,
        "first_failure": first_failure,
        "finite_only": True,
        "notice": "A bounded check is finite evidence, never a proof of the general statement.",
    }
