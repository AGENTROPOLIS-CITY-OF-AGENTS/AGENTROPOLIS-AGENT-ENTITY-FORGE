"""AGENT-ENTITY Forge Proof Graph.

The Proof Graph is evidence infrastructure. It is NOT a reputation score and no
proof object grants authority by itself. Evidence is append-only: corrections
use supersedes / revocation / replacement proof, never a rewrite of history.

Core invariants:
- PROOF != AUTHORITY
- Evidence may support a governed promotion decision; it must NEVER directly
  mutate authority.
- Provenance is preserved; history is never silently overwritten.
- Contradictory evidence coexists; BE evaluates current validity.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Optional

# Canonical proof classes (logical classes, not one contract per class).
PROOF_CLASSES = frozenset(
    {
        "ProofOfIdentity",
        "ProofOfControl",
        "ProofOfMandate",
        "ProofOfAuthority",
        "ProofOfCapability",
        "ProofOfCompetence",
        "ProofOfWorkReceipt",
        "ProofOfOutcome",
        "ProofOfReputation",
        "ProofOfCompliance",
        "ProofOfProvenance",
        "ProofOfSimulation",
        "ProofOfDelegation",
        "ProofOfContinuity",
        "ProofOfEvolution",
        "ProofOfService",
        "ProofOfSLA",
        "ProofOfFiscalDiscipline",
        "ProofOfExecution",
        "ProofOfSettlement",
        "ProofOfTransfer",
    }
)

# Node statuses. Historical proofs remain auditable.
NODE_STATUSES = frozenset({"ACTIVE", "EXPIRED", "SUPERSEDED", "REVOKED", "DISPUTED"})

# Core relationships.
RELATIONSHIPS = frozenset(
    {
        "ISSUED_BY",
        "VERIFIES",
        "DERIVED_FROM",
        "SUPERSEDES",
        "REVOKES",
        "SUPPORTS",
        "CONTRADICTS",
        "EVALUATED_BY",
        "CERTIFIED_BY",
        "GOVERNED_BY",
        "SETTLED_BY",
    }
)

# Forbidden claims that must never appear in evidence (no credentials, no
# execution/settlement fabrication).
FORBIDDEN_CLAIMS = frozenset(
    {
        "privateKey",
        "seedPhrase",
        "mnemonic",
        "walletSecret",
        "apiSecret",
        "providerSecret",
        "rawSigner",
        "txHash",
        "transactionHash",
        "settlementHash",
        "settlementReceipt",
        "signedTransaction",
    }
)

# Proof classes that are execution/settlement claims. AQUADUCT verification
# evidence must never be ingested as these.
EXECUTION_SETTLEMENT_CLASSES = frozenset({"ProofOfExecution", "ProofOfSettlement"})


class ProofGraphError(Exception):
    """Base error for the Proof Graph."""


class ProofGraphValidationError(ProofGraphError):
    """A proof node failed validation (fail closed)."""


class ProofGraphConflictError(ProofGraphError):
    """A proof node conflicts with existing graph state."""


@dataclass
class ProofNode:
    """A single evidence node in the graph."""

    proof_id: str
    proof_type: str
    subject_ref: str
    source_ref: str
    verifier_ref: str
    timestamp: str
    digest: str
    schema_version: str
    evidence_refs: list[str] = field(default_factory=list)
    status: str = "ACTIVE"
    expiry: Optional[str] = None
    supersedes: Optional[str] = None
    revocation_ref: Optional[str] = None
    provenance: dict[str, Any] = field(default_factory=dict)
    grants_authority: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "proof_id": self.proof_id,
            "proof_type": self.proof_type,
            "subject_ref": self.subject_ref,
            "source_ref": self.source_ref,
            "verifier_ref": self.verifier_ref,
            "timestamp": self.timestamp,
            "digest": self.digest,
            "schema_version": self.schema_version,
            "evidence_refs": list(self.evidence_refs),
            "status": self.status,
            "expiry": self.expiry,
            "supersedes": self.supersedes,
            "revocation_ref": self.revocation_ref,
            "provenance": dict(self.provenance),
            "grants_authority": self.grants_authority,
        }


def _sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def compute_node_digest(node: ProofNode) -> str:
    """Deterministic digest over the immutable evidence fields.

    The digest binds the evidence content (not status, which is a graph-state
    view). Recomputing must be stable across ingestion.
    """
    canonical = json.dumps(
        {
            "proof_id": node.proof_id,
            "proof_type": node.proof_type,
            "subject_ref": node.subject_ref,
            "source_ref": node.source_ref,
            "verifier_ref": node.verifier_ref,
            "timestamp": node.timestamp,
            "schema_version": node.schema_version,
            "evidence_refs": sorted(node.evidence_refs),
            "expiry": node.expiry,
            "supersedes": node.supersedes,
            "provenance": node.provenance,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return _sha256_hex(canonical.encode("utf-8"))


def _require_non_empty(value: Any, field_name: str) -> None:
    if value is None or (isinstance(value, str) and value.strip() == ""):
        raise ProofGraphValidationError(f"missing or empty {field_name}")


def _validate_timestamp(value: str, field_name: str) -> None:
    _require_non_empty(value, field_name)
    # Require an explicit UTC-relative timezone designator.
    if not (value.endswith("Z") or value.endswith("+00:00") or value.endswith("+0000")):
        raise ProofGraphValidationError(f"{field_name} must carry an explicit timezone")


def validate_node(node: ProofNode) -> None:
    """Validate a proof node. Fail closed on any malformed field."""
    _require_non_empty(node.proof_id, "proof_id")
    _require_non_empty(node.proof_type, "proof_type")
    _require_non_empty(node.subject_ref, "subject_ref")
    _require_non_empty(node.source_ref, "source_ref")
    _require_non_empty(node.verifier_ref, "verifier_ref")
    _validate_timestamp(node.timestamp, "timestamp")
    if node.expiry is not None:
        _validate_timestamp(node.expiry, "expiry")
    if node.status not in NODE_STATUSES:
        raise ProofGraphValidationError(f"unknown status: {node.status}")
    if node.grants_authority:
        raise ProofGraphValidationError("proof nodes never grant authority")
    if not node.digest or len(node.digest) != 64:
        raise ProofGraphValidationError("digest must be a 64-char hex string")
    # Forbidden claims must never appear in evidence.
    for claim in FORBIDDEN_CLAIMS:
        if claim in json.dumps(node.to_dict()):
            raise ProofGraphValidationError(f"forbidden claim present: {claim}")


class ProofGraph:
    """Append-only evidence graph with provenance, status, and relationships."""

    def __init__(self) -> None:
        self._nodes: dict[str, ProofNode] = {}
        self._relationships: list[tuple[str, str, str]] = []  # (subject, rel, object)

    def nodes(self) -> list[ProofNode]:
        return list(self._nodes.values())

    def get(self, proof_id: str) -> Optional[ProofNode]:
        return self._nodes.get(proof_id)

    def relationships(self) -> list[tuple[str, str, str]]:
        return list(self._relationships)

    def add_relationship(self, subject: str, rel: str, obj: str) -> None:
        if rel not in RELATIONSHIPS:
            raise ProofGraphValidationError(f"unknown relationship: {rel}")
        if subject not in self._nodes:
            raise ProofGraphValidationError(f"relationship subject not in graph: {subject}")
        if obj not in self._nodes:
            raise ProofGraphValidationError(f"relationship object not in graph: {obj}")
        self._relationships.append((subject, rel, obj))

    def ingest(self, node: ProofNode) -> ProofNode:
        """Ingest a proof node. Idempotent: same proof_id + same digest is a no-op.

        A different digest for an existing proof_id is a conflict (fail closed).
        """
        validate_node(node)
        existing = self._nodes.get(node.proof_id)
        if existing is not None:
            if existing.digest == node.digest:
                return existing  # idempotent replay
            raise ProofGraphConflictError(
                f"proof_id {node.proof_id} already exists with a different digest"
            )
        self._nodes[node.proof_id] = node
        return node

    def supersede(self, old_id: str, new_id: str) -> None:
        """Mark old proof SUPERSEDED by new proof. History is preserved."""
        old = self._nodes.get(old_id)
        new = self._nodes.get(new_id)
        if old is None or new is None:
            raise ProofGraphValidationError("supersede requires both proofs in graph")
        if old.status == "REVOKED":
            raise ProofGraphConflictError("cannot supersede a revoked proof")
        old.status = "SUPERSEDED"
        old.supersedes = new_id
        self.add_relationship(old_id, "SUPERSEDES", new_id)

    def revoke(self, proof_id: str, reason: str, revoked_by: str) -> None:
        """Revoke a proof. First-class revocation path; history preserved."""
        node = self._nodes.get(proof_id)
        if node is None:
            raise ProofGraphValidationError(f"proof not in graph: {proof_id}")
        _require_non_empty(reason, "reason")
        _require_non_empty(revoked_by, "revoked_by")
        node.status = "REVOKED"
        node.revocation_ref = f"REVOKE:{revoked_by}:{reason}"
        # Revocation is a first-class relationship.
        revoke_node = ProofNode(
            proof_id=f"REVOKE-{proof_id}",
            proof_type="RevocationReceipt",
            subject_ref=node.subject_ref,
            source_ref=revoked_by,
            verifier_ref=revoked_by,
            timestamp=node.timestamp,
            digest=_sha256_hex(f"REVOKE:{proof_id}:{revoked_by}:{reason}".encode()),
            schema_version="v1",
            evidence_refs=[proof_id],
            status="ACTIVE",
            provenance={"reason": reason, "revoked_by": revoked_by},
        )
        self._nodes[revoke_node.proof_id] = revoke_node
        self.add_relationship(revoke_node.proof_id, "REVOKES", proof_id)

    def mark_disputed(self, proof_id: str) -> None:
        node = self._nodes.get(proof_id)
        if node is None:
            raise ProofGraphValidationError(f"proof not in graph: {proof_id}")
        if node.status == "REVOKED":
            raise ProofGraphConflictError("cannot dispute a revoked proof")
        node.status = "DISPUTED"

    def expire(self, proof_id: str) -> None:
        node = self._nodes.get(proof_id)
        if node is None:
            raise ProofGraphValidationError(f"proof not in graph: {proof_id}")
        if node.status == "REVOKED":
            raise ProofGraphConflictError("cannot expire a revoked proof")
        node.status = "EXPIRED"

    def active_proofs(self, subject_ref: str, proof_type: Optional[str] = None) -> list[ProofNode]:
        """Current (ACTIVE) proofs for a subject, optionally filtered by class."""
        out = []
        for node in self._nodes.values():
            if node.subject_ref != subject_ref or node.status != "ACTIVE":
                continue
            if proof_type is not None and node.proof_type != proof_type:
                continue
            out.append(node)
        return out

    def contradictions_for(self, subject_ref: str) -> list[ProofNode]:
        """Proofs that are DISPUTED or REVOKED for a subject (contradiction surface)."""
        return [
            n
            for n in self._nodes.values()
            if n.subject_ref == subject_ref and n.status in ("DISPUTED", "REVOKED")
        ]
