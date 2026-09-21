"""AGENT-ENTITY Forge governed promotion plane.

Proof Graph -> BE evaluation -> FORGE decision -> 54-T gate.

Evidence is not authority. Capability growth != authority growth.
TEST PASS != PRODUCTION AUTHORITY.
"""

from .proof_graph import (
    EXECUTION_SETTLEMENT_CLASSES,
    FORBIDDEN_CLAIMS,
    NODE_STATUSES,
    PROOF_CLASSES,
    RELATIONSHIPS,
    ProofGraph,
    ProofGraphConflictError,
    ProofGraphError,
    ProofGraphValidationError,
    ProofNode,
    compute_node_digest,
)
from .aqueduct_ingest import (
    AEGIS_CANDIDATE_SCHEMA,
    AQUADUCT_VERIFICATION_SCHEMA,
    AqueductIngestError,
    ingest_aqueduct_verification,
    verify_aqueduct_receipt,
)
from .be import (
    CAPABILITY_PROOF_CLASSES,
    EVALUATION_VERSION,
    RECOMMENDATIONS,
    BEError,
    EvaluationReceipt,
    evaluate,
)
from .forge_decision import (
    DECISIONS,
    FORGE_DECISION_VERSION,
    ForgeError,
    PromotionDecision,
    decide,
)
from .gate_54t import (
    REVIEW_OUTCOMES,
    REVIEW_VERSION,
    GateError,
    GovernanceReview,
    review,
)
from .erc8004 import (
    ERC8004_PROOF_MAP,
    ERC8004_REGISTRIES,
    ERC8004Error,
    ingest_erc8004,
)
from .reputation import (
    DIMENSIONS,
    ReputationError,
    ReputationView,
    compute_view,
)

__all__ = [
    "EXECUTION_SETTLEMENT_CLASSES",
    "FORBIDDEN_CLAIMS",
    "NODE_STATUSES",
    "PROOF_CLASSES",
    "RELATIONSHIPS",
    "ProofGraph",
    "ProofGraphConflictError",
    "ProofGraphError",
    "ProofGraphValidationError",
    "ProofNode",
    "compute_node_digest",
    "AEGIS_CANDIDATE_SCHEMA",
    "AQUADUCT_VERIFICATION_SCHEMA",
    "AqueductIngestError",
    "ingest_aqueduct_verification",
    "verify_aqueduct_receipt",
    "CAPABILITY_PROOF_CLASSES",
    "EVALUATION_VERSION",
    "RECOMMENDATIONS",
    "BEError",
    "EvaluationReceipt",
    "evaluate",
    "DECISIONS",
    "FORGE_DECISION_VERSION",
    "ForgeError",
    "PromotionDecision",
    "decide",
    "REVIEW_OUTCOMES",
    "REVIEW_VERSION",
    "GateError",
    "GovernanceReview",
    "review",
    "ERC8004_PROOF_MAP",
    "ERC8004_REGISTRIES",
    "ERC8004Error",
    "ingest_erc8004",
    "DIMENSIONS",
    "ReputationError",
    "ReputationView",
    "compute_view",
]
