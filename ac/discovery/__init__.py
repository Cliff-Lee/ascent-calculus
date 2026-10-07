from ac.discovery.profiles import ProfileComparison, profile, compare_profile, BUILTIN_STATS
from ac.discovery.classes import ClassComparisonRow, ClassComparison, compare_classes
from ac.discovery.claims import ClaimStatus, ClaimRecord, ClaimRegistry, claim_from_verification
from ac.discovery.laws import (
    MinedLaw,
    mine_selector_laws,
    selector_complexity,
    generate_selector_expressions,
    mine_selector_expression_laws, SelectorEquivalenceClass,
    mine_selector_equivalence_classes,
)
from ac.discovery.fibre_geometry import (
    SpanRelation,
    FibreGap,
    RepeatedSandwichWitness,
    fibre_gaps,
    lower_gap_profile,
    reflect_gap_profile,
    higher_gap_profile,
    repeated_sandwich_pattern,
    repeated_sandwich_witness,
    contains_repeated_sandwich,
    fibre_span_relation,
    fibre_span_profile,
)
from ac.discovery.hypotheses import (
    HypothesisCandidate,
    HypothesisDiscovery,
    mine_minimal_hypotheses,
    ThresholdDiscovery,
    discover_monotone_threshold,
)
from ac.discovery.schemas import SchemaInstance, SchemaReport, verify_parameterized_schema
from ac.discovery.discriminate import StatisticDiscrimination, rank_discriminating_statistics

__all__ = [name for name in globals() if not name.startswith("_")]

from ac.discovery.synthesis import (
    FailureKind, SynthesisFailure, CandidateDiagnostics, FiniteMapDiagnostics, CandidateEvaluation,
    SynthesisReport, transformation_cost, enumerate_transform_programs,
    evaluate_bijection_candidate, diagnose_candidate, analyze_finite_map, synthesize_bijections,
)

from ac.discovery.repairs import (
    pack_internal_occurrences, repeated_sandwich_offending_values,
    FibreGapPackT, FibreGapPack,
)
from .local_repair import (
    rotate_interval, move_interval, swap_intervals, swap_fibre_gaps,
    RepeatedSandwichOccurrence, repeated_sandwich_witnesses,
    RepeatedSandwichLower, RepeatedSandwichValues,
    RotateT, SwapFibreGapsT, ExtremeGapSwapT,
    Rotate, SwapFibreGaps, ExtremeGapSwap,
)
from .local_repair import (
    ModifiedDefect, modified_defect, DefectPair, defect_pairs,
    DefectRotation, canonical_defect_rotation, DefectRepairTrace,
    defect_measure, repair_modified_defects, GapSwapRepairT, GapSwapRepair,
)
from .growth import modified_parent, modified_children, grow_modified_level
from .proof_extraction import (
    ExtremeOrientation, lower_gap_indices, fibre_orientation,
    is_extreme_oriented, right_oriented, left_oriented,
    threshold_projection, maximum_extreme_normal_form,
    ExtremeGapProofStep, ExtremeGapProofTrace,
    extreme_gap_proof_trace_2122_to_2212,
)
__all__ = [name for name in globals() if not name.startswith("_")]
from .proof_extraction import DefectRotationCertificate, certify_defect_rotation, defect_value_potential
__all__ = [name for name in globals() if not name.startswith("_")]
from .proof_extraction import DefectAdmissibility, defect_admissibility
__all__ = [name for name in globals() if not name.startswith("_")]
from .proof_extraction import orientation_profile, repair_heavy_crossing_values, repair_preserves_orientation_profile
__all__ = [name for name in globals() if not name.startswith("_")]
