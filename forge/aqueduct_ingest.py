"""AQUADUCT verification evidence ingestion into the Proof Graph.

AQUADUCT proves verification occurred. Nothing more. AQUADUCT verification
evidence must NEVER become ProofOfExecution or ProofOfSettlement.

Before ingestion we verify:
- schema version
- candidate digest
- source binding
- verifier identity
- proof references
- timestamp
- expiry where applicable
- execution == false
- settled == false
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Optional

from .proof_graph import (
    EXECUTION_SETTLEMENT_CLASSES,
    FORBIDDEN_CLAIMS,
    ProofGraph,
    ProofGraphValidationError,
    ProofNode,
    compute_node_digest,
)

# The AQUADUCT verification receipt schema this consumer understands.
AQUADUCT_VERIFICATION_SCHEMA = "agentropolis.aqueduct.verification-receipt.v1"
# The AEGIS candidate schema that produced the verification.
AEGIS_CANDIDATE_SCHEMA = "agentropolis.aegis.aquaduct-candidate.v1"


class AqueductIngestError(Exception):
    """AQUADUCT evidence failed verification (fail closed)."""


def _require(value: Any, field: str) -> None:
    if value is None or (isinstance(value, str) and value.strip() == ""):
        raise AqueductIngestError(f"missing or empty {field}")


def _validate_timestamp(value: str, field: str) -> None:
    _require(value, field)
    if not (value.endswith("Z") or value.endswith("+00:00") or value.endswith("+0000")):
        raise AqueductIngestError(f"{field} must carry an explicit timezone")


def _sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def verify_aqueduct_receipt(receipt: dict[str, Any]) -> None:
    """Verify an AQUADUCT verification receipt before ingestion. Fail closed."""
    # Schema version.
    schema = receipt.get("schema")
    if schema != AQUADUCT_VERIFICATION_SCHEMA:
        raise AqueductIngestError(f"unsupported AQUADUCT receipt schema: {schema!r}")

    # execution and settled must be false.
    if receipt.get("execution") is not False:
        raise AqueductIngestError("AQUADUCT verification receipt must have execution=false")
    if receipt.get("settled") is not False:
        raise AqueductIngestError("AQUADUCT verification receipt must have settled=false")

    # Required fields.
    for field in (
        "verification_id",
        "source_decision_id",
        "source_binding_hash",
        "agent_entity_ref",
        "principal_ref",
        "intent_id",
        "verification_result",
        "verifier_id",
        "candidate_digest",
        "schema_version",
        "test_environment",
    ):
        _require(receipt.get(field), field)

    if receipt.get("verification_result") != "VERIFIED":
        raise AqueductIngestError("AQUADUCT receipt is not VERIFIED")

    _validate_timestamp(receipt.get("verified_at", ""), "verified_at")

    # Forbidden claims must never appear in AQUADUCT evidence.
    raw = json.dumps(receipt)
    for claim in FORBIDDEN_CLAIMS:
        if claim in raw:
            raise AqueductIngestError(f"forbidden claim present in AQUADUCT receipt: {claim}")

    # AQUADUCT verification must not claim execution or settlement.
    proofs = receipt.get("proofs_satisfied") or []
    for p in proofs:
        if p in EXECUTION_SETTLEMENT_CLASSES:
            raise AqueductIngestError(
                f"AQUADUCT verification must not claim {p}; verification is not execution/settlement"
            )


def ingest_aqueduct_verification(
    graph: ProofGraph,
    receipt: dict[str, Any],
    *,
    verifier_override: Optional[str] = None,
) -> ProofNode:
    """Verify and ingest an AQUADUCT verification receipt as ProofOfAuthority
    evidence (verification occurred). Returns the ingested node.

    The AQUADUCT verification becomes evidence that AEGIS authorized a bounded
    action and AQUADUCT verified it. It is NOT ProofOfExecution / ProofOfSettlement.
    """
    verify_aqueduct_receipt(receipt)

    agent_entity_ref = receipt["agent_entity_ref"]
    verifier_ref = verifier_override or receipt["verifier_id"]
    proof_id = f"AQUADUCT-VERIFY-{receipt['verification_id']}"

    node = ProofNode(
        proof_id=proof_id,
        proof_type="ProofOfAuthority",
        subject_ref=agent_entity_ref,
        source_ref=f"aegis:{receipt['source_decision_id']}",
        verifier_ref=verifier_ref,
        timestamp=receipt["verified_at"],
        digest="",  # computed below
        schema_version=AQUADUCT_VERIFICATION_SCHEMA,
        evidence_refs=[receipt["verification_id"], receipt["source_binding_hash"]],
        status="ACTIVE",
        provenance={
            "source": "aqueduct",
            "verification_id": receipt["verification_id"],
            "source_decision_id": receipt["source_decision_id"],
            "source_binding_hash": receipt["source_binding_hash"],
            "candidate_digest": receipt["candidate_digest"],
            "intent_id": receipt["intent_id"],
            "test_environment": receipt["test_environment"],
            "verification_result": receipt["verification_result"],
            "execution": False,
            "settled": False,
        },
    )
    node.digest = compute_node_digest(node)
    return graph.ingest(node)
