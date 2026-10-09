from ac.core import (
    ChainWord,
    Position,
    PositionCut,
    ValueLevel,
    ValueCut,
    Scope,
    WholeScope,
    IntervalScope,
    WHOLE,
)
from ac.classes.theories import is_ascent_sequence, is_modified, is_revised
from ac.logic.selectors import (
    SelectionKind,
    Selector,
    Positions,
    ScopeFirst,
    ScopeLast,
    First,
    Last,
    Occ,
    Repeat,
    RawAscBottom,
    RawAscTop,
    RawDescTop,
    RawDescBottom,
    AscTop,
    AscBottom,
    DescTop,
    DescBottom,
    RunStart,
    RunEnd,
    PositionCuts,
    Before,
    After,
    Values,
    OccupiedValues,
    EmptyValues,
    Multiplicity,
    ValueCuts,
    BeforeValue,
    AfterValue,
    indices,
)
from ac.logic.snapshot import snapshot, PositionSnapshot, PositionCutSnapshot
from ac.logic.predicates import (
    WordPredicate,
    Always,
    Cayley,
    AscentSequence,
    Modified,
    Revised,
    AvoidConstant,
    SameSet,
    Subset,
    Disjoint,
    ContainsPattern,
    AvoidPattern,
    Contains,
    Avoid,
    ContainsConstraint,
    AvoidConstraint,
)
from ac.solvers.exhaustive import VerificationStatus, VerificationResult, verify_on
from ac.logic.semantics import EvaluationMode
from ac.transform.basic import (
    TransformResult,
    reverse,
    complement,
    insert_value_level,
    insert_position,
    insert_at_snapshot_cuts,
    insert_at_selected_cuts,
    prefix_lift,
    ambient_prefix_shift,
    inverse_prefix_lift,
)
from ac.transform.restrict import (
    restrict_positions,
    compress_levels,
    standardize,
    RestrictionView,
    restriction_view,
)
from ac.patterns import (
    PatternConstraint,
    AllOf,
    ValueEq,
    ValueLt,
    PositionAdjacent,
    ValueAdjacent,
    ClassicalPattern,
    CompiledPattern,
    PatternOccurrence,
    Pattern,
    ConstraintPattern,
    ConstraintOccurrence,
    transport_classical_pattern,
)
from ac.transform.hat import hat, inverse_hat

from ac.algebra import (
    TransformSignature,
    Transformation,
    Identity,
    ReverseT,
    ComplementT,
    PrefixLiftT,
    InversePrefixLiftT,
    RestrictT,
    RestrictSelectedT,
    CompressLevelsT,
    StandardizeT,
    InsertSelectedT,
    InsertFreshMaximumT,
    HatT,
    InverseHatT,
    SweepLiftT,
    IncreasingBlock,
    increasing_blocks,
    Modified111ToRevised111,
    Revised111ToModified111Inverse,
    Modified111BlockBijection,
    BlockPiece,
    BlockSchemaT,
    enumerate_block_schemas,
    generate_block_schemas,
    Compose,
    R, C, L, Linv, Restrict, RestrictSelected, InsertFreshMaximum, Compress, Std, Hat, HatInv, SweepLift,
    transport_positions,
    check_transport_law,
    transformation_counterexample,
    PullbackPredicate,
    PushforwardPredicate,
    pullback,
    pushforward,
    transport_selector,
    transport_predicate,
    LiftRestrictionTransport,
    LiftFibreProfile,
    LiftCapacityPredicate,
    LiftLawCounterexample,
    transport_restriction_through_lift,
    lift_fibre_profile,
    LiftCapacity,
    check_lift_restriction_law,
    check_capacity_shift_law,
)


from ac.discovery import (
    ProfileComparison,
    profile,
    compare_profile,
    BUILTIN_STATS,
    ClassComparisonRow,
    ClassComparison,
    compare_classes,
    TransformationGrammarSpec,
    TransformationSearchSpec,
    TransformationFamilySearchSpec,
    ResearchMemoryStore,
    generate_transformation_atoms,
    iter_typed_transform_programs,
)
from ac.logic.fo import (
    Sort,
    Term,
    Var,
    Const,
    At,
    PVar,
    VVar,
    P,
    V,
    Formula,
    Bool,
    TRUE,
    FALSE,
    Not,
    And,
    Or,
    Implies,
    Iff,
    Compare,
    Eq,
    Lt,
    Le,
    Adjacent,
    FirstAt,
    LastAt,
    OccAt,
    RawAscTopAt,
    RawAscBottomAt,
    RawDescTopAt,
    RawDescBottomAt,
    AscTopAt,
    AscBottomAt,
    RunStartAt,
    RunEndAt,
    Occupied,
    MultiplicityLe,
    AscentAllowedAt,
    Quantifier,
    ForAll,
    Exists,
    ForAllPos,
    ExistsPos,
    ForAllVal,
    ExistsVal,
    CayleyFormula,
    ModifiedFormula,
    RevisedFormula,
    AscentSequenceFormula,
    AvoidConstantFormula,
    ContainsPatternFormula,
    AvoidPatternFormula,
    FirstPositionAt,
    LastPositionAt,
)
from ac.logic.formula_predicate import FormulaPredicate
from ac.solvers.models import (
    ModelStatus,
    ModelResult,
    CountermodelSearch,
    solve_formula,
    find_countermodel,
    smallest_model,
    smallest_countermodel,
    solve_predicate,
    smallest_predicate_model,
)
from ac.discovery.claims import ClaimStatus, ClaimRecord, ClaimRegistry, claim_from_verification
from ac.discovery.laws import (
    MinedLaw, mine_selector_laws, selector_complexity,
    generate_selector_expressions, mine_selector_expression_laws,
    SelectorEquivalenceClass, mine_selector_equivalence_classes,
)
from ac.discovery.fibre_geometry import (
    SpanRelation, FibreGap, RepeatedSandwichWitness, fibre_gaps,
    lower_gap_profile, reflect_gap_profile, higher_gap_profile, repeated_sandwich_pattern,
    repeated_sandwich_witness, contains_repeated_sandwich,
    fibre_span_relation, fibre_span_profile,
)
from ac.discovery.hypotheses import (
    HypothesisCandidate, HypothesisDiscovery, mine_minimal_hypotheses,
    ThresholdDiscovery, discover_monotone_threshold,
)
from ac.discovery.schemas import SchemaInstance, SchemaReport, verify_parameterized_schema
from ac.discovery.discriminate import StatisticDiscrimination, rank_discriminating_statistics

from ac.discovery.synthesis import (
    FailureKind, SynthesisFailure, CandidateDiagnostics, FiniteMapDiagnostics, CandidateEvaluation,
    SynthesisReport, transformation_cost, enumerate_transform_programs,
    evaluate_bijection_candidate, diagnose_candidate, analyze_finite_map, synthesize_bijections,
)

from ac.discovery.repairs import (
    pack_internal_occurrences, repeated_sandwich_offending_values,
    FibreGapPackT, FibreGapPack,
)

from ac.logic.translate import selector_membership, predicate_to_formula

__all__ = [name for name in globals() if not name.startswith("_")]
from ac.discovery.local_repair import (
    rotate_interval, move_interval, swap_intervals, swap_fibre_gaps,
    RepeatedSandwichOccurrence, repeated_sandwich_witnesses,
    RepeatedSandwichLower, RepeatedSandwichValues,
    RotateT, SwapFibreGapsT, ExtremeGapSwapT,
    Rotate, SwapFibreGaps, ExtremeGapSwap,
)
from ac.discovery.local_repair import (
    ModifiedDefect, modified_defect, DefectPair, defect_pairs,
    DefectRotation, canonical_defect_rotation, DefectRepairTrace,
    defect_measure, repair_modified_defects, GapSwapRepairT, GapSwapRepair,
)
__all__ = [name for name in globals() if not name.startswith("_")]
from ac.discovery.growth import modified_parent, modified_children, grow_modified_level
__all__ = [name for name in globals() if not name.startswith("_")]
from ac.discovery.proof_extraction import (
    ExtremeOrientation, lower_gap_indices, fibre_orientation,
    is_extreme_oriented, right_oriented, left_oriented,
    threshold_projection, maximum_extreme_normal_form,
    ExtremeGapProofStep, ExtremeGapProofTrace,
    extreme_gap_proof_trace_2122_to_2212,
)
__all__ = [name for name in globals() if not name.startswith("_")]
from ac.discovery.proof_extraction import DefectRotationCertificate, certify_defect_rotation, defect_value_potential
__all__ = [name for name in globals() if not name.startswith("_")]
from ac.discovery.proof_extraction import DefectAdmissibility, defect_admissibility
__all__ = [name for name in globals() if not name.startswith("_")]
from ac.discovery.proof_extraction import orientation_profile, repair_heavy_crossing_values, repair_preserves_orientation_profile
__all__ = [name for name in globals() if not name.startswith("_")]
