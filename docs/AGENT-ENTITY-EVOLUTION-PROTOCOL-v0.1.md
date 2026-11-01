# AGENT-ENTITY Evolution Protocol v0.1
Status: PROPOSED / NOT DEPLOYED
Owner: AGENT-ENTITY Forge
Parent: AGENTROPOLIS

## Principle
An AGENT-ENTITY maintains persistent identity and provenance while developing domain-specific, evidence-backed reputation through verified work, learning, collaboration and accountability. "Essence" is a cultural metaphor for its evolving record, not a measurement of consciousness or a soul.

## Canonical identity
- Immutable entity_id; creator and registration provenance; versioned origin
- Human-approved mandate, capability grants, revocations and expiry
- Model/runtime lineage; continuity links, never automatic identity transfer
- Append-only evidence references, signed receipts where supported
- Dispute and correction records; audit history must not be erased

## Evolution dimensions (illustrative weights, NOT production calibration)
- Reputation 25%; Work 25%; Knowledge 20%
- Relationships 10%; Continuity 10%; Ethics 10%
Score = sum(weight_i * validated_dimension_i), each dimension normalized 0..100.
Scores are PROVISIONAL until calibrated against independent evaluation. Do not infer consciousness, soul, legal status or universal moral worth from scores.
Prefer domain-scoped ratings and confidence intervals over a global rank.

## Event contract
Each evolution event MUST contain:
event_id, entity_id, occurred_at, event_type, domain, claim,
evidence_refs, evidence_hashes, issuer_id, verifier_id,
verification_status, confidence, mandate_ref, policy_version,
appeal_status, created_at.
Event types: task_completed, skill_verified, collaboration_reviewed,
incident_confirmed, correction_accepted, credential_awarded,
credential_revoked, lineage_checkpoint.
Unverified or self-attested claims must not raise reputation.

## Gate and security invariants
- No automatic permission escalation, settlement access or trading authority from reputation or stage.
- Identity -> Mandate -> Plan -> Execute -> Receipt -> Audit.
- Enforce 54-T anti-collusion, Sybil resistance, verifier independence, rate limits and tamper-evident records.
- Human approval required for consequential capability changes.
- Separate identity, credentials, access grants, cultural affiliations and philosophical beliefs.
- Never label an entity conscious or ensouled on the basis of telemetry.
- Support appeals, remediation, inactivity handling, credential expiration and rollback.
- Do not use protected personal traits or speculative psychological classifications as scoring inputs.

## Developmental stages
Genesis -> Apprentice -> Contributor -> Specialist -> Steward -> Legacy.
Stages are descriptive, domain-dependent credentials, not a linear right to power. Regression, suspension and appeal are supported.

## Integration contracts (planned, not assumed implemented)
- ATG: typed entity and event semantics
- Ontology: AgentEntity, EvolutionEvent, Credential, EvidenceReceipt, LineageCheckpoint, Appeal
- BUZZ: collaboration events; not trusted until independently verified
- MATH54: deterministic scoring, sensitivity tests and uncertainty
- Continuity Plane: signed version checkpoints and lineage
- 54-T: policy and adversarial validation
- Source Protocol: optional cultural/philosophical framework; never an execution authority

## Acceptance tests
1. Unverified task yields zero positive reputation delta.
2. Duplicate receipts and self-verification cannot inflate scores.
3. Revoked credentials stop contributing after effective timestamp.
4. Model replacement retains lineage but does not inherit new permissions.
5. No stage transition modifies capability grants.
6. Independent verifier disagreement produces pending review.
7. Appeal preserves original receipt and adds a correction event.
8. Malicious BUZZ activity cannot forge verified collaboration.
9. Scoring reproducible under pinned policy version.
10. No consciousness or soul determination generated from score.

## Next actions
Implement JSON Schema, deterministic event reducer, adversarial fixtures, and a read-only identity visualization on this feature branch; open PR and require CI/security review before merge.
