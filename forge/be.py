"""BE evaluation layer.

BE is the evaluator. It consumes Proof Graph evidence and produces an
explainable EvaluationReceipt. BE recommendation is NOT authority: it cannot
directly increase budget, signing authority, asset/counterparty scope,
delegation depth, transaction ceiling, or production access.

Every recommendation is explainable: which capability, which AGENT-ENTITY,
which proofs, who issued them, which expired, contradictions, policy version,
risk tier, and why.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Optional

from .proof_graph import ProofGraph, ProofNode

# Recommendation enum.
RECOMMENDATIONS = frozenset({"QUALIFIED", "NOT_QUALIFIED", "NEEDS_REVIEW"})

# Evaluation version (bump when evaluation semantics change).
EVALUATION_VERSION = "be-v1"

# Proof classes that count toward capability qualification.
CAPABILITY_PROOF_CLASSES = frozenset(
    {
        "ProofOfCapability",
        "ProofOfCompetence",
        "ProofOfSimulation",
        "ProofOfWorkReceipt",
        "ProofOfOutcome",
        "ProofOfAuthority",
        "ProofOfControl",
        "ProofOfIdentity",
    }
)


class BEError(Exception):
    """BE evaluation failed (fail closed)."""


@dataclass
class EvaluationReceipt:
    evaluation_id: str
    agent_entity_ref: str
    requested_capability: str
    requested_authority_change: Optional[str]
    proof_refs: list[str]
    policy_refs: list[str]
    evaluation_version: str
    evaluator_ref: str
    confidence: float
    evidence_completeness: float
    contradictions: list[str]
    expired_evidence: list[str]
    missing_evidence: list[str]
    risk_tier: str
    recommendation: str
    timestamp: str
    digest: str
    grants_authority: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "evaluation_id": self.evaluation_id,
            "agent_entity_ref": self.agent_entity_ref,
            "requested_capability": self.requested_capability,
            "requested_authority_change": self.requested_authority_change,
            "proof_refs": list(self.proof_refs),
            "policy_refs": list(self.policy_refs),
            "evaluation_version": self.evaluation_version,
            "evaluator_ref": self.evaluator_ref,
            "confidence": self.confidence,
            "evidence_completeness": self.evidence_completeness,
            "contradictions": list(self.contradictions),
            "expired_evidence": list(self.expired_evidence),
            "missing_evidence": list(self.missing_evidence),
            "risk_tier": self.risk_tier,
            "recommendation": self.recommendation,
            "timestamp": self.timestamp,
            "digest": self.digest,
            "grants_authority": self.grants_authority,
        }


def _sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _require(value: Any, field: str) -> None:
    if value is None or (isinstance(value, str) and value.strip() == ""):
        raise BEError(f"missing or empty {field}")


def _validate_timestamp(value: str, field: str) -> None:
    _require(value, field)
    if not (value.endswith("Z") or value.endswith("+00:00") or value.endswith("+0000")):
        raise BEError(f"{field} must carry an explicit timezone")


def _is_expired(node: ProofNode, now: str) -> bool:
    if node.expiry is None:
        return False
    # Lexicographic comparison works for ISO-8601 UTC with same format.
    return node.expiry < now


def evaluate(
    graph: ProofGraph,
    *,
    agent_entity_ref: str,
    requested_capability: str,
    evaluator_ref: str,
    policy_refs: list[str],
    risk_tier: str,
    now: str,
    requested_authority_change: Optional[str] = None,
    required_proof_classes: Optional[list[str]] = None,
) -> EvaluationReceipt:
    """Evaluate Proof Graph evidence for a capability. Explainable and fail-closed.

    BE recommendation is NOT authority. This function never mutates the graph
    and never grants authority.
    """
    _require(agent_entity_ref, "agent_entity_ref")
    _require(requested_capability, "requested_capability")
    _require(evaluator_ref, "evaluator_ref")
    _require(risk_tier, "risk_tier")
    _validate_timestamp(now, "now")

    required = required_proof_classes or sorted(CAPABILITY_PROOF_CLASSES)

    # Gather current (ACTIVE) proofs for the subject.
    active = graph.active_proofs(agent_entity_ref)
    active_by_type: dict[str, list[ProofNode]] = {}
    for node in active:
        active_by_type.setdefault(node.proof_type, []).append(node)

    # All proofs for the subject (including non-ACTIVE) to detect expired /
    # revoked / disputed evidence that should not be treated as merely missing.
    all_nodes = [n for n in graph.nodes() if n.subject_ref == agent_entity_ref]
    all_by_type: dict[str, list[ProofNode]] = {}
    for node in all_nodes:
        all_by_type.setdefault(node.proof_type, []).append(node)

    proof_refs: list[str] = []
    missing_evidence: list[str] = []
    expired_evidence: list[str] = []
    contradictions: list[str] = []

    # Contradiction surface: disputed/revoked proofs for the subject.
    for node in graph.contradictions_for(agent_entity_ref):
        contradictions.append(f"{node.proof_id}:{node.status}")

    # Evaluate required proof classes.
    for cls in required:
        nodes = active_by_type.get(cls, [])
        if not nodes:
            # If the class exists but is non-ACTIVE, classify it precisely.
            all_for_cls = all_by_type.get(cls, [])
            if all_for_cls:
                for node in all_for_cls:
                    if node.status == "EXPIRED":
                        expired_evidence.append(node.proof_id)
                    elif node.status in ("REVOKED", "DISPUTED"):
                        contradictions.append(f"{node.proof_id}:{node.status}")
                    else:
                        missing_evidence.append(cls)
            else:
                missing_evidence.append(cls)
            continue
        for node in nodes:
            proof_refs.append(node.proof_id)
            if _is_expired(node, now):
                expired_evidence.append(node.proof_id)

    # Evidence completeness: fraction of required classes present (ACTIVE).
    present = sum(1 for cls in required if active_by_type.get(cls))
    completeness = present / len(required) if required else 0.0

    # Confidence: penalized by missing evidence, expired evidence, contradictions.
    penalty = 0.0
    if missing_evidence:
        penalty += 0.25 * len(missing_evidence)
    if expired_evidence:
        penalty += 0.15 * len(expired_evidence)
    if contradictions:
        penalty += 0.2 * len(contradictions)
    confidence = max(0.0, min(1.0, completeness - penalty))

    # Recommendation (fail closed; never auto-promote).
    # - Missing evidence -> NOT_QUALIFIED (insufficient evidence to qualify).
    # - Expired / contradictory evidence -> NEEDS_REVIEW (stale or conflicting,
    #   requires human/governance judgment).
    # - Full, current, uncontradicted evidence -> QUALIFIED.
    if expired_evidence or contradictions:
        recommendation = "NEEDS_REVIEW"
    elif missing_evidence:
        recommendation = "NOT_QUALIFIED"
    elif completeness >= 1.0 and confidence >= 0.6:
        recommendation = "QUALIFIED"
    else:
        recommendation = "NOT_QUALIFIED"

    evaluation_id = f"BE-{agent_entity_ref}-{requested_capability}"
    receipt = EvaluationReceipt(
        evaluation_id=evaluation_id,
        agent_entity_ref=agent_entity_ref,
        requested_capability=requested_capability,
        requested_authority_change=requested_authority_change,
        proof_refs=sorted(set(proof_refs)),
        policy_refs=list(policy_refs),
        evaluation_version=EVALUATION_VERSION,
        evaluator_ref=evaluator_ref,
        confidence=round(confidence, 4),
        evidence_completeness=round(completeness, 4),
        contradictions=sorted(set(contradictions)),
        expired_evidence=sorted(set(expired_evidence)),
        missing_evidence=sorted(set(missing_evidence)),
        risk_tier=risk_tier,
        recommendation=recommendation,
        timestamp=now,
        digest="",
    )
    receipt.digest = _sha256_hex(
        json.dumps(
            {
                "evaluation_id": receipt.evaluation_id,
                "agent_entity_ref": receipt.agent_entity_ref,
                "requested_capability": receipt.requested_capability,
                "proof_refs": sorted(receipt.proof_refs),
                "policy_refs": sorted(receipt.policy_refs),
                "evaluation_version": receipt.evaluation_version,
                "recommendation": receipt.recommendation,
                "risk_tier": receipt.risk_tier,
                "timestamp": receipt.timestamp,
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    )
    return receipt
