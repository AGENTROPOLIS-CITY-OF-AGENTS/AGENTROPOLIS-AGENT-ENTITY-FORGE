"""Append-only Proof Graph.

Records are never mutated; disputes and revocations append new status records.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Callable, Iterable, Mapping

from .proofs import Verifier, verify_signed_proof

VERIFIED, DISPUTED, REVOKED, EXPIRED, FAILED = "VERIFIED", "DISPUTED", "REVOKED", "EXPIRED", "FAILED"


class DuplicateProof(ValueError):
    pass


class UnknownProof(KeyError):
    pass


@dataclass(frozen=True)
class ProofRecord:
    proof_id: str
    proof_class: str
    agent_entity_ref: str
    status: str
    security_bound: bool
    envelope: Mapping
    signature: str | None
    recorded_at: datetime
    reason: str | None = None
    grants_authority: bool = field(default=False, init=False)


@dataclass(frozen=True)
class ProofEvent:
    kind: str
    record: ProofRecord


def _parse_ts(value: str) -> datetime:
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


class ProofGraph:
    def __init__(self, verifier: Verifier, *, ttl: timedelta | None = None,
                 clock: Callable[[], datetime] | None = None):
        self._verifier = verifier
        self._ttl = ttl
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._records: list[ProofRecord] = []
        self._subscribers: list[Callable[[ProofEvent], None]] = []

    def subscribe(self, callback: Callable[[ProofEvent], None]) -> None:
        self._subscribers.append(callback)

    def _emit(self, kind: str, record: ProofRecord) -> None:
        self._records.append(record)
        for cb in list(self._subscribers):
            cb(ProofEvent(kind, record))

    def add_proof(self, envelope: Mapping, signature: str | None) -> ProofRecord:
        verified = verify_signed_proof(envelope, signature, self._verifier)
        if any(r.proof_id == envelope["proof_id"] for r in self._records):
            raise DuplicateProof(envelope["proof_id"])
        status = envelope["status"]
        now = self._clock()
        if status == VERIFIED and self._ttl is not None and _parse_ts(envelope["created_at"]) + self._ttl < now:
            status = EXPIRED
        record = ProofRecord(
            proof_id=envelope["proof_id"],
            proof_class=envelope["proof_class"],
            agent_entity_ref=envelope["agent_entity_ref"],
            status=status,
            security_bound=verified["security_bound"],
            envelope=verified["envelope"],
            signature=signature,
            recorded_at=now,
        )
        self._emit("added", record)
        return record

    def history(self, proof_id: str) -> list[ProofRecord]:
        return [r for r in self._records if r.proof_id == proof_id]

    def current(self, proof_id: str) -> ProofRecord:
        hist = self.history(proof_id)
        if not hist:
            raise UnknownProof(proof_id)
        return hist[-1]

    def _append_status(self, proof_id: str, status: str, reason: str) -> ProofRecord:
        if not reason:
            raise ValueError("reason is required")
        prev = self.current(proof_id)
        record = ProofRecord(
            proof_id=prev.proof_id,
            proof_class=prev.proof_class,
            agent_entity_ref=prev.agent_entity_ref,
            status=status,
            security_bound=prev.security_bound,
            envelope=prev.envelope,
            signature=prev.signature,
            recorded_at=self._clock(),
            reason=reason,
        )
        self._emit(status.lower(), record)
        return record

    def dispute(self, proof_id: str, reason: str) -> ProofRecord:
        return self._append_status(proof_id, DISPUTED, reason)

    def revoke(self, proof_id: str, reason: str) -> ProofRecord:
        return self._append_status(proof_id, REVOKED, reason)

    def _latest_by_id(self, agent_entity_ref: str) -> dict[str, ProofRecord]:
        latest: dict[str, ProofRecord] = {}
        for r in self._records:
            if r.agent_entity_ref == agent_entity_ref:
                latest[r.proof_id] = r
        return latest

    def proofs_for(self, agent_entity_ref: str, proof_class: str | None = None,
                   status: str | None = None) -> list[ProofRecord]:
        return [
            r for r in self._latest_by_id(agent_entity_ref).values()
            if (proof_class is None or r.proof_class == proof_class)
            and (status is None or r.status == status)
        ]

    def missing_classes(self, agent_entity_ref: str, required_classes: Iterable[str],
                        require_security_bound: bool = True) -> list[str]:
        have = {
            r.proof_class for r in self.proofs_for(agent_entity_ref, status=VERIFIED)
            if r.security_bound or not require_security_bound
        }
        return [c for c in required_classes if c not in have]

    def has_verified_set(self, agent_entity_ref: str, required_classes: Iterable[str],
                         require_security_bound: bool = True) -> bool:
        return not self.missing_classes(agent_entity_ref, required_classes, require_security_bound)

    def __len__(self) -> int:
        return len(self._records)
