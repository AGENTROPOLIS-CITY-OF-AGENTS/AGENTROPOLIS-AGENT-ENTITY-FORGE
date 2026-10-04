"""Certification lifecycle state owned by Forge.

Certification is derived from evidence. Production approval requires an
external AEGIS or human approval reference. Nothing here grants authority.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Callable, Sequence

from .proof_graph import DISPUTED, REVOKED, ProofEvent, ProofGraph

DEFAULT_REQUIRED_PROOF_CLASSES = (
    "ProofOfCapability",
    "ProofOfQuote",
    "ProofOfExecution",
    "ProofOfSettlement",
    "ProofOfFiscalDiscipline",
)


class CertificationState(str, Enum):
    UNCERTIFIED = "UNCERTIFIED"
    CANDIDATE = "CANDIDATE"
    CERTIFIED = "CERTIFIED"
    PRODUCTION_APPROVED = "PRODUCTION_APPROVED"
    RESTRICTED = "RESTRICTED"
    REVOKED = "REVOKED"


class InvalidTransition(ValueError):
    pass


class InsufficientEvidence(ValueError):
    def __init__(self, missing: Sequence[str]):
        self.missing = list(missing)
        super().__init__(f"missing verified, security-bound proofs: {', '.join(self.missing)}")


class ExternalApprovalRequired(ValueError):
    pass


@dataclass(frozen=True)
class Transition:
    from_state: CertificationState
    to_state: CertificationState
    at: datetime
    reason: str | None = None
    aegis_decision_ref: str | None = None
    human_approval_ref: str | None = None


class PromotionCorridor:
    def __init__(self, graph: ProofGraph,
                 required_proof_classes: Sequence[str] = DEFAULT_REQUIRED_PROOF_CLASSES,
                 clock: Callable[[], datetime] | None = None):
        self._graph = graph
        self._required = tuple(required_proof_classes)
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._history: dict[str, list[Transition]] = {}
        graph.subscribe(self._on_proof_event)

    @property
    def required_proof_classes(self) -> tuple[str, ...]:
        return self._required

    def state(self, agent_entity_ref: str) -> CertificationState:
        hist = self._history.get(agent_entity_ref)
        return hist[-1].to_state if hist else CertificationState.UNCERTIFIED

    def _transition(self, ref: str, allowed: Sequence[CertificationState], to: CertificationState, **meta) -> Transition:
        current = self.state(ref)
        if current not in allowed:
            raise InvalidTransition(f"{ref}: cannot move {current.value} -> {to.value}")
        t = Transition(current, to, self._clock(), **meta)
        self._history.setdefault(ref, []).append(t)
        return t

    def nominate(self, agent_entity_ref: str) -> Transition:
        return self._transition(agent_entity_ref, [CertificationState.UNCERTIFIED], CertificationState.CANDIDATE)

    def certify(self, agent_entity_ref: str) -> Transition:
        if self.state(agent_entity_ref) != CertificationState.CANDIDATE:
            raise InvalidTransition(f"{agent_entity_ref}: certify requires CANDIDATE")
        missing = self._graph.missing_classes(agent_entity_ref, self._required, require_security_bound=True)
        if missing:
            raise InsufficientEvidence(missing)
        return self._transition(agent_entity_ref, [CertificationState.CANDIDATE], CertificationState.CERTIFIED)

    def approve_production(self, agent_entity_ref: str, *, aegis_decision_ref: str | None = None,
                           human_approval_ref: str | None = None) -> Transition:
        refs = [r for r in (aegis_decision_ref, human_approval_ref) if isinstance(r, str) and r.strip()]
        if not refs:
            raise ExternalApprovalRequired(
                "PRODUCTION_APPROVED requires an AEGIS decision ref or human approval ref; certification alone is not authority"
            )
        return self._transition(
            agent_entity_ref, [CertificationState.CERTIFIED], CertificationState.PRODUCTION_APPROVED,
            aegis_decision_ref=aegis_decision_ref or None, human_approval_ref=human_approval_ref or None,
        )

    def restrict(self, agent_entity_ref: str, reason: str) -> Transition:
        if not reason:
            raise ValueError("reason is required")
        return self._transition(
            agent_entity_ref, [CertificationState.CERTIFIED, CertificationState.PRODUCTION_APPROVED],
            CertificationState.RESTRICTED, reason=reason,
        )

    def revoke(self, agent_entity_ref: str, reason: str) -> Transition:
        if not reason:
            raise ValueError("reason is required")
        current = self.state(agent_entity_ref)
        if current == CertificationState.REVOKED:
            raise InvalidTransition(f"{agent_entity_ref}: already REVOKED")
        return self._transition(agent_entity_ref, [current], CertificationState.REVOKED, reason=reason)

    def _on_proof_event(self, event: ProofEvent) -> None:
        record = event.record
        if record.status not in (DISPUTED, REVOKED) or record.proof_class not in self._required:
            return
        if self.state(record.agent_entity_ref) in (CertificationState.CERTIFIED, CertificationState.PRODUCTION_APPROVED):
            self.restrict(record.agent_entity_ref, f"proof {record.proof_id} {record.status}: {record.reason}")

    def status(self, agent_entity_ref: str) -> dict:
        return {
            "agent_entity_ref": agent_entity_ref,
            "state": self.state(agent_entity_ref).value,
            "history": [
                {
                    "from_state": t.from_state.value,
                    "to_state": t.to_state.value,
                    "at": t.at.isoformat(),
                    "reason": t.reason,
                    "aegis_decision_ref": t.aegis_decision_ref,
                    "human_approval_ref": t.human_approval_ref,
                }
                for t in self._history.get(agent_entity_ref, [])
            ],
            "grants_authority": False,
            "reputation_is_authority": False,
        }
