"""FORGE promotion decision layer.

FORGE consumes BE EvaluationReceipt + Proof Graph references + current state and
produces a separate PromotionDecision. A PromotionDecision is NOT execution and
NOT an authority grant. Authority changes require their own governed
AuthorityPromotionReceipt path (never hidden inside a capability receipt).

Decisions: PROMOTE, RESTRICT, REVOKE, RETAIN, REQUIRE_RETEST, ESCALATE.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Optional

from .be import EvaluationReceipt
from .proof_graph import ProofGraph

DECISIONS = frozenset({"PROMOTE", "RESTRICT", "REVOKE", "RETAIN", "REQUIRE_RETEST", "ESCALATE"})

# FORGE decision version.
FORGE_DECISION_VERSION = "forge-v1"


class ForgeError(Exception):
    """FORGE decision failed (fail closed)."""


@dataclass
class PromotionDecision:
    decision_id: str
    agent_entity_ref: str
    capability: str
    old_tier: str
    requested_tier: str
    approved_tier: Optional[str]
    decision: str
    be_evaluation_ref: str
    proof_refs: list[str]
    policy_version: str
    risk_tier: str
    timestamp: str
    digest: str
    grants_authority: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision_id": self.decision_id,
            "agent_entity_ref": self.agent_entity_ref,
            "capability": self.capability,
            "old_tier": self.old_tier,
            "requested_tier": self.requested_tier,
            "approved_tier": self.approved_tier,
            "decision": self.decision,
            "be_evaluation_ref": self.be_evaluation_ref,
            "proof_refs": list(self.proof_refs),
            "policy_version": self.policy_version,
            "risk_tier": self.risk_tier,
            "timestamp": self.timestamp,
            "digest": self.digest,
            "grants_authority": self.grants_authority,
        }


def _sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _require(value: Any, field: str) -> None:
    if value is None or (isinstance(value, str) and value.strip() == ""):
        raise ForgeError(f"missing or empty {field}")


def _validate_timestamp(value: str, field: str) -> None:
    _require(value, field)
    if not (value.endswith("Z") or value.endswith("+00:00") or value.endswith("+0000")):
        raise ForgeError(f"{field} must carry an explicit timezone")


def decide(
    graph: ProofGraph,
    evaluation: EvaluationReceipt,
    *,
    capability: str,
    old_tier: str,
    requested_tier: str,
    policy_version: str,
    now: str,
    decision_id: Optional[str] = None,
) -> PromotionDecision:
    """Produce a FORGE PromotionDecision from a BE evaluation.

    FORGE never grants authority. A PROMOTE decision here only advances a
    capability tier; authority changes require the separate
    AuthorityPromotionReceipt path through AEGIS + 54-T + human approval.
    """
    _require(capability, "capability")
    _require(old_tier, "old_tier")
    _require(requested_tier, "requested_tier")
    _require(policy_version, "policy_version")
    _validate_timestamp(now, "now")

    # FORGE consumes BE evaluation; it does not replace it.
    if evaluation.recommendation not in ("QUALIFIED", "NEEDS_REVIEW", "NOT_QUALIFIED"):
        raise ForgeError("BE evaluation has an invalid recommendation")

    # Decision logic (fail closed; never auto-promote on weak evidence).
    if evaluation.recommendation == "NOT_QUALIFIED":
        decision = "RETAIN"
        approved_tier = old_tier
    elif evaluation.recommendation == "NEEDS_REVIEW":
        decision = "REQUIRE_RETEST"
        approved_tier = None
    elif evaluation.recommendation == "QUALIFIED":
        # A qualified capability may advance a tier, but never beyond the
        # requested tier and never implicitly granting authority.
        decision = "PROMOTE"
        approved_tier = requested_tier
    else:
        decision = "ESCALATE"
        approved_tier = None

    decision_id = decision_id or f"FORGE-{evaluation.agent_entity_ref}-{capability}"
    result = PromotionDecision(
        decision_id=decision_id,
        agent_entity_ref=evaluation.agent_entity_ref,
        capability=capability,
        old_tier=old_tier,
        requested_tier=requested_tier,
        approved_tier=approved_tier,
        decision=decision,
        be_evaluation_ref=evaluation.evaluation_id,
        proof_refs=list(evaluation.proof_refs),
        policy_version=policy_version,
        risk_tier=evaluation.risk_tier,
        timestamp=now,
        digest="",
    )
    result.digest = _sha256_hex(
        json.dumps(
            {
                "decision_id": result.decision_id,
                "agent_entity_ref": result.agent_entity_ref,
                "capability": result.capability,
                "old_tier": result.old_tier,
                "requested_tier": result.requested_tier,
                "approved_tier": result.approved_tier,
                "decision": result.decision,
                "be_evaluation_ref": result.be_evaluation_ref,
                "policy_version": result.policy_version,
                "risk_tier": result.risk_tier,
                "timestamp": result.timestamp,
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    )
    return result
