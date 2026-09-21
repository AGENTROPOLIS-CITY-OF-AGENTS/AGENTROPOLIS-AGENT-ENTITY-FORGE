"""54-T governance / security review gate.

Every production promotion path must pass 54-T governance/security review.
FORGE cannot bypass it. 54-T may APPROVE, DENY, RESTRICT, or ESCALATE. 54-T
does NOT execute transactions.

Required path:
  Proof Graph -> BE -> FORGE -> 54-T -> production eligibility
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Optional

from .forge_decision import PromotionDecision

# 54-T review outcomes.
REVIEW_OUTCOMES = frozenset({"APPROVE", "DENY", "RESTRICT", "ESCALATE"})

# 54-T review version.
REVIEW_VERSION = "54t-v1"


class GateError(Exception):
    """54-T gate failed (fail closed)."""


@dataclass
class GovernanceReview:
    review_id: str
    agent_entity_ref: str
    capability: str
    forge_decision_ref: str
    outcome: str
    reviewer_ref: str
    policy_version: str
    timestamp: str
    digest: str
    notes: list[str] = None  # type: ignore[assignment]

    def to_dict(self) -> dict[str, Any]:
        return {
            "review_id": self.review_id,
            "agent_entity_ref": self.agent_entity_ref,
            "capability": self.capability,
            "forge_decision_ref": self.forge_decision_ref,
            "outcome": self.outcome,
            "reviewer_ref": self.reviewer_ref,
            "policy_version": self.policy_version,
            "timestamp": self.timestamp,
            "digest": self.digest,
            "notes": list(self.notes or []),
        }


def _sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _require(value: Any, field: str) -> None:
    if value is None or (isinstance(value, str) and value.strip() == ""):
        raise GateError(f"missing or empty {field}")


def _validate_timestamp(value: str, field: str) -> None:
    _require(value, field)
    if not (value.endswith("Z") or value.endswith("+00:00") or value.endswith("+0000")):
        raise GateError(f"{field} must carry an explicit timezone")


def review(
    decision: PromotionDecision,
    *,
    reviewer_ref: str,
    policy_version: str,
    now: str,
    outcome: Optional[str] = None,
    notes: Optional[list[str]] = None,
) -> GovernanceReview:
    """Run the 54-T governance/security review on a FORGE decision.

    Default outcome is ESCALATE (fail closed): a promotion is not approved
    unless an explicit reviewer APPROVEs it. 54-T never executes transactions.
    """
    _require(reviewer_ref, "reviewer_ref")
    _require(policy_version, "policy_version")
    _validate_timestamp(now, "now")

    # Fail closed: only an explicit APPROVE advances production eligibility.
    if outcome is None:
        outcome = "ESCALATE"
    if outcome not in REVIEW_OUTCOMES:
        raise GateError(f"unknown 54-T outcome: {outcome}")

    review_id = f"54T-{decision.agent_entity_ref}-{decision.capability}"
    result = GovernanceReview(
        review_id=review_id,
        agent_entity_ref=decision.agent_entity_ref,
        capability=decision.capability,
        forge_decision_ref=decision.decision_id,
        outcome=outcome,
        reviewer_ref=reviewer_ref,
        policy_version=policy_version,
        timestamp=now,
        digest="",
        notes=list(notes or []),
    )
    result.digest = _sha256_hex(
        json.dumps(
            {
                "review_id": result.review_id,
                "agent_entity_ref": result.agent_entity_ref,
                "capability": result.capability,
                "forge_decision_ref": result.forge_decision_ref,
                "outcome": result.outcome,
                "reviewer_ref": result.reviewer_ref,
                "policy_version": result.policy_version,
                "timestamp": result.timestamp,
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    )
    return result
