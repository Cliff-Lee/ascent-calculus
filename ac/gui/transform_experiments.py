"""Bounded, class-wide experiments for established AC transformations."""

from __future__ import annotations

from time import perf_counter

from ac.classes.theories import is_ascent_sequence, is_modified, is_revised
from ac.core.word import ChainWord
from ac.transform import (
    complement,
    hat,
    inverse_hat,
    inverse_prefix_lift,
    insert_position,
    prefix_lift,
    reverse,
    restrict_positions,
)

from .experiments import (
    FAMILY_GENERATORS,
    FAMILY_LIMITS,
    STATISTICS,
    _cancel_requested,
    _emit_progress,
    _matches,
    _statistic,
    parse_experiment,
)


TRANSFORM_LIMIT = 10
TRANSFORMS = {
    "reverse": reverse,
    "complement": complement,
    "hat": hat,
    "inverse_hat": inverse_hat,
    "prefix_lift": prefix_lift,
    "inverse_prefix_lift": inverse_prefix_lift,
    "insert_position": insert_position,
    "delete_position": restrict_positions,
}
INVERSES = {
    "reverse": "reverse",
    "complement": "complement",
    "hat": "inverse_hat",
    "inverse_hat": "hat",
    "prefix_lift": "inverse_prefix_lift",
    "inverse_prefix_lift": "prefix_lift",
    "insert_position": "delete_position",
    "delete_position": "insert_position",
}
PARAMETERIZED_TRANSFORMS = {"prefix_lift", "inverse_prefix_lift", "insert_position", "delete_position"}
LENGTH_OFFSETS = {"insert_position": 1, "delete_position": -1}
FAMILY_PREDICATES = {
    "ordinary": is_ascent_sequence,
    "modified": is_modified,
    "revised": is_revised,
}


def _key(word: ChainWord) -> tuple[tuple[int, ...], int]:
    """Mathematical word identity, excluding provenance IDs."""
    return tuple(word.values), word.height


def _parse(raw: dict):
    if not isinstance(raw, dict):
        raise ValueError("Transformation experiment must be an object")
    name = raw.get("transformation")
    if name not in TRANSFORMS:
        raise ValueError("Choose reverse, complement, hat, inverse hat, prefix lift, or inverse prefix lift")
    parameter = None
    if name in PARAMETERIZED_TRANSFORMS:
        raw_parameter = raw.get("parameter")
        if isinstance(raw_parameter, bool) or (
            isinstance(raw_parameter, float) and not raw_parameter.is_integer()
        ):
            raise ValueError("Transformation parameter must be a whole number")
        try:
            parameter = int(raw_parameter)
        except (TypeError, ValueError) as exc:
            raise ValueError("Enter a whole-number position or cut for this transformation") from exc
        minimum = 0 if name == "insert_position" else 1
        if parameter < minimum:
            if name == "insert_position":
                message = "Insertion cut must be nonnegative"
            elif name in {"prefix_lift", "inverse_prefix_lift"}:
                message = "Pivot position must be a positive integer"
            else:
                message = "Deleted position must be positive"
            raise ValueError(message)
    elif raw.get("parameter") not in (None, ""):
        raise ValueError("This transformation does not use a position or cut")
    value = None
    if name in {"insert_position", "delete_position"}:
        raw_value = raw.get("value")
        if isinstance(raw_value, bool) or (isinstance(raw_value, float) and not raw_value.is_integer()):
            raise ValueError("Value level must be a whole number")
        try:
            value = int(raw_value)
        except (TypeError, ValueError) as exc:
            raise ValueError("Enter the value level to insert or expect at the deleted position") from exc
        if value < 1:
            raise ValueError("Value level must be positive")
    try:
        start, stop = int(raw.get("start", 1)), int(raw.get("stop", 8))
    except (TypeError, ValueError) as exc:
        raise ValueError("Degrees must be whole numbers") from exc
    if not 1 <= start <= stop <= TRANSFORM_LIMIT:
        raise ValueError(f"Transformation checks are currently bounded to degrees 1–{TRANSFORM_LIMIT}")
    statistic = raw.get("statistic", "none")
    if statistic not in STATISTICS:
        raise ValueError("Choose a supported statistic to test, or select overall count")
    # Reuse the same validated family/restriction language as class comparisons.
    target_offset = LENGTH_OFFSETS.get(name, 0)
    source_raw = dict(raw.get("source", {}))
    target_raw = dict(raw.get("target", {}))
    if int(source_raw.get("degree_offset", 0)) != 0:
        raise ValueError("Transformation source degree shift must be zero in this workbench")
    declared_target_offset = int(target_raw.get("degree_offset", target_offset))
    if declared_target_offset != target_offset:
        raise ValueError(f"{name.replace('_', ' ')} maps source degree n to target degree n{target_offset:+d}")
    target_raw["degree_offset"] = target_offset
    common = parse_experiment({
        "question": "compare",
        "start": start,
        "stop": stop,
        "statistic": statistic,
        "left": source_raw,
        "right": target_raw,
    })
    return name, common, statistic, parameter, value


def _apply(name, word, parameter, value):
    if name in {"prefix_lift", "inverse_prefix_lift"}:
        return TRANSFORMS[name](word, parameter)
    if name == "insert_position":
        return insert_position(word, parameter, value)
    if name == "delete_position":
        if parameter > len(word):
            raise IndexError(parameter)
        positions = tuple(i for i in range(1, len(word) + 1) if i != parameter)
        return restrict_positions(word, positions)
    return TRANSFORMS[name](word)


def _apply_inverse(name, word, parameter, value):
    if name == "insert_position":
        # insert_position inserts after `cut`, so the created entry is cut+1.
        return _apply("delete_position", word, parameter + 1, value)
    if name == "delete_position":
        # Recovery is possible only when the deleted entry had the selected value.
        return insert_position(word, parameter - 1, value)
    return _apply(INVERSES[name], word, parameter, value)


def run_transform_experiment(raw: dict, *, progress=None, cancel_event=None) -> dict:
    """Apply one existing transformation to a bounded source class and audit it."""
    name, spec, statistic, parameter, value = _parse(raw)
    inverse_name = INVERSES.get(name)
    started = perf_counter()
    rows = []
    cancelled = False
    total_degrees = spec.stop - spec.start + 1
    current_n = spec.start
    total_tested = 0
    _emit_progress(progress, phase="starting", degree=current_n, completed_degrees=0,
                   total_degrees=total_degrees, degree_tested=0, total_tested=0)
    for n in range(spec.start, spec.stop + 1):
        current_n = n
        _emit_progress(progress, phase="degree", degree=n, completed_degrees=len(rows),
                       total_degrees=total_degrees, degree_tested=0, total_tested=total_tested)
        if _cancel_requested(cancel_event):
            cancelled = True
            break
        source_count = valid_outputs = target_hits = collisions = inverse_successes = 0
        statistic_preserved = statistic_failures = 0
        images: set[tuple[tuple[int, ...], int]] = set()
        target_keys: set[tuple[tuple[int, ...], int]] = set()
        target_order: list[tuple[tuple[int, ...], int]] = []
        first_invalid = first_target_failure = first_collision = first_inverse_failure = first_statistic_failure = None
        target_predicate = FAMILY_PREDICATES[spec.right.family]
        source_degree = n + spec.left.degree_offset
        target_degree = n + spec.right.degree_offset
        universe_scanned = 0
        for source in FAMILY_GENERATORS[spec.left.family](source_degree):
            universe_scanned += 1
            if universe_scanned == 1 or universe_scanned % 256 == 0:
                _emit_progress(progress, phase="source", degree=n, completed_degrees=len(rows),
                               total_degrees=total_degrees, degree_tested=universe_scanned,
                               total_tested=total_tested + universe_scanned)
                if _cancel_requested(cancel_event):
                    cancelled = True
                    break
            if not _matches(source, spec.left.rules):
                continue
            source_count += 1
            try:
                output = _apply(name, source, parameter, value)
                if not isinstance(output, ChainWord):
                    output = output.output
            except Exception as exc:  # partial transformations report their exact failed inputs
                if first_invalid is None:
                    first_invalid = {"source": list(source.values), "reason": f"{type(exc).__name__}: {exc}"}
                continue
            output_key = _key(output)
            output_is_cayley = output.is_cayley
            if output_is_cayley:
                valid_outputs += 1
            elif first_invalid is None:
                first_invalid = {"source": list(source.values), "output": list(output.values), "reason": "output is not a Cayley word"}

            if output_key in images:
                collisions += 1
                if first_collision is None:
                    first_collision = {"source": list(source.values), "output": list(output.values)}
            else:
                images.add(output_key)

            lands_in_target = (
                output_is_cayley
                and len(output) == target_degree
                and target_predicate(output)
                and _matches(output, spec.right.rules)
            )
            if lands_in_target:
                target_hits += 1
            elif first_target_failure is None:
                first_target_failure = {"source": list(source.values), "output": list(output.values)}

            if statistic != "none":
                if _statistic(source, statistic) == _statistic(output, statistic):
                    statistic_preserved += 1
                else:
                    statistic_failures += 1
                    if first_statistic_failure is None:
                        first_statistic_failure = {
                            "source": list(source.values),
                            "output": list(output.values),
                            "source_value": _json_value(_statistic(source, statistic)),
                            "output_value": _json_value(_statistic(output, statistic)),
                        }

            if inverse_name is not None:
                try:
                    recovered = _apply_inverse(name, output, parameter, value)
                    if not isinstance(recovered, ChainWord):
                        recovered = recovered.output
                    if _key(recovered) == _key(source):
                        inverse_successes += 1
                    elif first_inverse_failure is None:
                        first_inverse_failure = {"source": list(source.values), "output": list(output.values), "recovered": list(recovered.values)}
                except Exception as exc:
                    if first_inverse_failure is None:
                        first_inverse_failure = {"source": list(source.values), "output": list(output.values), "reason": f"{type(exc).__name__}: {exc}"}

        if cancelled:
            break

        target_count = 0
        target_scanned = 0
        for target in FAMILY_GENERATORS[spec.right.family](target_degree):
            target_scanned += 1
            if target_scanned == 1 or target_scanned % 256 == 0:
                _emit_progress(progress, phase="target", degree=n, completed_degrees=len(rows),
                               total_degrees=total_degrees,
                               degree_tested=universe_scanned + target_scanned,
                               total_tested=total_tested + universe_scanned + target_scanned)
                if _cancel_requested(cancel_event):
                    cancelled = True
                    break
            if _matches(target, spec.right.rules):
                target_count += 1
                target_key = _key(target)
                target_keys.add(target_key)
                target_order.append(target_key)
        if cancelled:
            break
        target_coverage = sum(key in images for key in target_keys)
        missing_key = next((key for key in target_order if key not in images), None)
        missing_target = list(missing_key[0]) if missing_key is not None else None
        rows.append({
            "n": n,
            "source_degree": source_degree,
            "target_degree": target_degree,
            "source_count": source_count,
            "cayley_outputs": valid_outputs,
            "target_hits": target_hits,
            "distinct_images": len(images),
            "collisions": collisions,
            "target_count": target_count,
            "target_coverage": target_coverage,
            "missing_targets": target_count - target_coverage,
            "all_sources_land_in_target": target_hits == source_count,
            "injective": collisions == 0 and len(images) == source_count,
            "surjective": target_coverage == target_count,
            "inverse_successes": inverse_successes if inverse_name is not None else None,
            "statistic_preserved": statistic_preserved if statistic != "none" else None,
            "statistic_failures": statistic_failures if statistic != "none" else None,
            "first_invalid": first_invalid,
            "first_target_failure": first_target_failure,
            "first_collision": first_collision,
            "first_missing_target": missing_target,
            "first_inverse_failure": first_inverse_failure,
            "first_statistic_failure": first_statistic_failure,
        })
        total_tested += universe_scanned + target_scanned
        _emit_progress(progress, phase="degree_complete", degree=n, completed_degrees=len(rows),
                       total_degrees=total_degrees, degree_tested=0, total_tested=total_tested)
    result = {
        "transformation": name,
        "parameter": parameter,
        "value": value,
        "inverse": inverse_name,
        "statistic": statistic,
        "statistic_label": STATISTICS[statistic],
        "rows": rows,
        "runtime_seconds": round(perf_counter() - started, 3),
        "finite_only": True,
        "notice": f"Finite class-wide test through degree {spec.stop}; no all-degree theorem is asserted.",
        "specification": {
            "transformation": name,
            "parameter": parameter,
            "value": value,
            "start": spec.start,
            "stop": spec.stop,
            "statistic": statistic,
            "source": _serial_side(spec.left),
            "target": _serial_side(spec.right),
        },
    }
    has_counterexample = any(
        not row["all_sources_land_in_target"]
        or not row["injective"]
        or not row["surjective"]
        or (row["inverse_successes"] is not None and row["inverse_successes"] != row["source_count"])
        or (row["statistic_failures"] is not None and row["statistic_failures"] > 0)
        for row in rows
    )
    result["evidence"] = {
        "schema": "ac.finite-result.v1",
        "status": "incomplete" if cancelled else ("counterexample" if has_counterexample else "verified"),
        "finite_only": True,
        "completed_degrees": [row["n"] for row in rows],
        "requested_degrees": {"start": spec.start, "stop": spec.stop},
        "complete": not cancelled,
        "cancelled_at_degree": current_n if cancelled else None,
        "objects_tested": total_tested,
    }
    _emit_progress(progress, phase="cancelled" if cancelled else "complete", degree=current_n,
                   completed_degrees=len(rows), total_degrees=total_degrees,
                   degree_tested=0, total_tested=total_tested)
    return result


def _json_value(value):
    return list(value) if isinstance(value, tuple) else value


def _serial_side(side):
    return {
        "family": side.family,
        "degree_offset": side.degree_offset,
        "rules": [{"mode": rule.mode, "pattern": list(rule.pattern.values)} for rule in side.rules],
    }
