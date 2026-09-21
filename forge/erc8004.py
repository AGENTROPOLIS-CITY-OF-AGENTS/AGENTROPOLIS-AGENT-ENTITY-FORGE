"""ERC-8004 external adapter.

Maps ERC-8004 identity / reputation / validation evidence into the Proof Graph
as evidence. ERC-8004 does NOT replace AGENT-ENTITY. External score/validation:

- MAY contribute evidence
- MUST NOT grant authority
- MUST NOT automatically promote
- MUST NOT override AEGIS
- MUST NOT bypass BE
- MUST NOT bypass FORGE
- MUST NOT bypass 54-T
"""

from __future__ import annotations

from typing import Any, Optional

from .proof_graph import (
    FORBIDDEN_CLAIMS,
    ProofGraph,
    ProofGraphValidationError,
    ProofNode,
    compute_node_digest,
)

# ERC-8004 registry types.
ERC8004_REGISTRIES = frozenset({"identity", "reputation", "validation"})

# ERC-8004 evidence maps to these proof classes only (never authority).
ERC8004_PROOF_MAP = {
    "identity": "ProofOfIdentity",
    "reputation": "ProofOfReputation",
    "validation": "ProofOfCapability",
}


class ERC8004Error(Exception):
    """ERC-8004 evidence failed validation (fail closed)."""


def _require(value: Any, field: str) -> None:
    if value is None or (isinstance(value, str) and value.strip() == ""):
        raise ERC8004Error(f"missing or empty {field}")


def _validate_timestamp(value: str, field: str) -> None:
    _require(value, field)
    if not (value.endswith("Z") or value.endswith("+00:00") or value.endswith("+0000")):
        raise ERC8004Error(f"{field} must carry an explicit timezone")


def ingest_erc8004(
    graph: ProofGraph,
    *,
    agent_entity_ref: str,
    registry: str,
    token_id: str,
    network: str,
    observed_at: str,
    verifier_ref: str,
    metadata_uri: Optional[str] = None,
    owner_address: Optional[str] = None,
    score: Optional[Any] = None,
) -> ProofNode:
    """Ingest an ERC-8004 external attestation as evidence.

    The external score/validation contributes evidence only. It never grants
    authority and never auto-promotes.
    """
    _require(agent_entity_ref, "agent_entity_ref")
    _require(registry, "registry")
    _require(token_id, "token_id")
    _require(network, "network")
    _require(verifier_ref, "verifier_ref")
    _validate_timestamp(observed_at, "observed_at")

    if registry not in ERC8004_REGISTRIES:
        raise ERC8004Error(f"unknown ERC-8004 registry: {registry}")

    proof_type = ERC8004_PROOF_MAP[registry]
    proof_id = f"ERC8004-{registry}-{token_id}"

    provenance: dict[str, Any] = {
        "external_identity_type": "erc-8004",
        "registry": registry,
        "network": network,
        "token_id": token_id,
        "observed_at": observed_at,
        "verifier_ref": verifier_ref,
    }
    if metadata_uri is not None:
        provenance["metadata_uri"] = metadata_uri
    if owner_address is not None:
        provenance["owner_address"] = owner_address
    if score is not None:
        # A score is evidence input, never authority. Preserve its inputs.
        provenance["external_score"] = score
        provenance["score_is_evidence_not_authority"] = True

    node = ProofNode(
        proof_id=proof_id,
        proof_type=proof_type,
        subject_ref=agent_entity_ref,
        source_ref=f"erc-8004:{registry}:{network}",
        verifier_ref=verifier_ref,
        timestamp=observed_at,
        digest="",
        schema_version="erc-8004-v1",
        evidence_refs=[f"{registry}:{token_id}"],
        status="ACTIVE",
        provenance=provenance,
    )
    node.digest = compute_node_digest(node)
    return graph.ingest(node)
