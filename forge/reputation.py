"""Reputation views derived from signed evidence.

Reputation is a derived view over signed evidence. It is NEVER stored as an
unexplained mutable number. If a score exists, its inputs are preserved.

Different contexts compute different reputation views (treasury reputation !=
coding reputation != gaming reputation). REPUTATION != AUTHORITY.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from .proof_graph import ProofGraph, ProofNode

# Reputation dimensions (evidence-derived).
DIMENSIONS = frozenset(
    {
        "successful_outcomes",
        "failed_outcomes",
        "sla_adherence",
        "policy_violations",
        "revocations",
        "disputes",
        "financial_discipline",
        "capability_recency",
        "verifier_diversity",
        "provenance_quality",
    }
)


class ReputationError(Exception):
    """Reputation computation failed (fail closed)."""


@dataclass
class ReputationView:
    agent_entity_ref: str
    context: str
    dimensions: dict[str, Any]
    inputs: list[str]  # proof_ids that fed this view
    score: Optional[float]  # derived, with inputs preserved

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent_entity_ref": self.agent_entity_ref,
            "context": self.context,
            "dimensions": dict(self.dimensions),
            "inputs": list(self.inputs),
            "score": self.score,
        }


def _require(value: Any, field: str) -> None:
    if value is None or (isinstance(value, str) and value.strip() == ""):
        raise ReputationError(f"missing or empty {field}")


def compute_view(
    graph: ProofGraph,
    *,
    agent_entity_ref: str,
    context: str,
    now: str,
) -> ReputationView:
    """Compute a reputation view for a context from signed evidence.

    The score is derived and its inputs (proof_ids) are always preserved. The
    score is evidence, not authority.
    """
    _require(agent_entity_ref, "agent_entity_ref")
    _require(context, "context")

    active = graph.active_proofs(agent_entity_ref)
    inputs: list[str] = []
    dimensions: dict[str, Any] = {}

    successful = 0
    failed = 0
    sla = 0
    violations = 0
    revocations = 0
    disputes = 0
    fiscal = 0
    verifiers: set[str] = set()

    for node in active:
        inputs.append(node.proof_id)
        verifiers.add(node.verifier_ref)
        if node.proof_type == "ProofOfOutcome":
            outcome = node.provenance.get("outcome")
            if outcome == "success":
                successful += 1
            elif outcome == "failure":
                failed += 1
        elif node.proof_type == "ProofOfSLA":
            sla += 1
        elif node.proof_type == "ProofOfFiscalDiscipline":
            fiscal += 1
        elif node.proof_type == "ProofOfCompliance":
            if node.provenance.get("violation"):
                violations += 1

    # Contradiction surface (disputes / revocations) feeds the view.
    for node in graph.contradictions_for(agent_entity_ref):
        if node.status == "REVOKED":
            revocations += 1
        elif node.status == "DISPUTED":
            disputes += 1

    dimensions = {
        "successful_outcomes": successful,
        "failed_outcomes": failed,
        "sla_adherence": sla,
        "policy_violations": violations,
        "revocations": revocations,
        "disputes": disputes,
        "financial_discipline": fiscal,
        "capability_recency": len(active),
        "verifier_diversity": len(verifiers),
        "provenance_quality": len(inputs),
    }

    # Derived score with inputs preserved. Never an unexplained number.
    score = None
    if inputs:
        base = successful - failed - violations - revocations - disputes
        score = max(0.0, float(base) / max(1, len(inputs)))

    return ReputationView(
        agent_entity_ref=agent_entity_ref,
        context=context,
        dimensions=dimensions,
        inputs=sorted(set(inputs)),
        score=score,
    )
