"""Deterministic, read-only AGENT-ENTITY evidence projection. No authority writes."""
from collections import defaultdict
from decimal import Decimal
from hashlib import sha256
import json

DIMENSIONS = ("reputation", "work", "knowledge", "relationships", "continuity", "ethics")
WEIGHTS = {"reputation": 25, "work": 25, "knowledge": 20, "relationships": 10, "continuity": 10, "ethics": 10}
STAGES = ("Genesis", "Apprentice", "Contributor", "Specialist", "Steward", "Legacy")
REQUIRED = ("event_id", "entity_id", "occurred_at", "event_type", "domain", "claim", "evidence_refs", "evidence_hashes", "issuer_id", "verifier_id", "verification_status", "confidence", "mandate_ref", "policy_version", "appeal_status", "created_at")
TYPES = {"task_completed", "skill_verified", "collaboration_reviewed", "incident_confirmed", "correction_accepted", "credential_awarded", "credential_revoked", "lineage_checkpoint"}
class InvalidEvidence(ValueError):
    pass

def project(events, entity_id, domain, policy_version="v0.1"):
    """Project evidence counts and illustrative weighted dimensions, never capability grants."""
    ordered = sorted(events, key=lambda e: (e.get("occurred_at", ""), e.get("event_id", "")))
    seen_ids, seen_evidence = set(), set()
    accepted, rejected = [], []
    counts = defaultdict(int)
    revoked = set()
    for e in ordered:
        missing = [key for key in REQUIRED if key not in e]
        if missing:
            rejected.append((e.get("event_id"), "missing_fields"))
            continue
        if e["event_id"] in seen_ids:
            rejected.append((e["event_id"], "duplicate_event"))
            continue
        seen_ids.add(e["event_id"])
        if e["entity_id"] != entity_id or e["domain"] != domain or e["policy_version"] != policy_version:
            continue
        if e["event_type"] not in TYPES or e["verification_status"] != "verified" or e["appeal_status"] not in ("none", "resolved"):
            rejected.append((e["event_id"], "unverified_or_disputed"))
            continue
        if e["issuer_id"] == e["verifier_id"] or not e["verifier_id"]:
            rejected.append((e["event_id"], "self_verification"))
            continue
        if not e["evidence_refs"] or not e["evidence_hashes"] or len(e["evidence_refs"]) != len(e["evidence_hashes"]):
            rejected.append((e["event_id"], "invalid_evidence"))
            continue
        if not all(isinstance(h, str) and len(h) == 64 and all(c in "0123456789abcdef" for c in h) for h in e["evidence_hashes"]):
            rejected.append((e["event_id"], "invalid_hash"))
            continue
        if any(h in seen_evidence for h in e["evidence_hashes"]):
            rejected.append((e["event_id"], "duplicate_evidence"))
            continue
        try:
            confidence = Decimal(str(e["confidence"]))
            if not confidence.is_finite() or not 0 <= confidence <= 1:
                raise ValueError
        except (ValueError, TypeError, ArithmeticError):
            rejected.append((e["event_id"], "invalid_confidence"))
            continue
        seen_evidence.update(e["evidence_hashes"])
        accepted.append(e["event_id"])
        counts[e["event_type"]] += 1
        if e["event_type"] == "credential_revoked":
            revoked.add(e["claim"])
    result = {"entity_id": entity_id, "domain": domain, "policy_version": policy_version,
              "accepted_event_ids": accepted, "rejected_events": rejected,
              "proof_counts": dict(sorted(counts.items())), "revoked_claims": sorted(revoked),
              "stage": "UNASSESSED", "authority_changed": False,
              "consciousness_status": "undetermined", "soul_status": "philosophically_open"}
    result["projection_sha256"] = sha256(json.dumps(result, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return result
