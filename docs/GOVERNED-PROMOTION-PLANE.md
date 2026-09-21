# Governed Promotion Plane (Proof Graph → BE → FORGE → 54-T)

Status: implemented reference plane

This is the middle intelligence layer of the canonical corridor:

```text
AQUADUCT
  -> Proof Graph
  -> BE evaluation
  -> AGENT-ENTITY FORGE
  -> 54-T governance/security review
  -> PAYRAIL
```

## Core principle

```text
PROOF != AUTHORITY
SCORE != AUTHORITY
REPUTATION != AUTHORITY
CAPABILITY != AUTHORITY
TEST PASS != PRODUCTION AUTHORITY
CAPABILITY GROWTH != AUTHORITY GROWTH
```

Evidence may support a governed promotion decision. Evidence must NEVER
directly mutate authority.

## Modules

- `forge/proof_graph.py` — append-only evidence graph (node model, statuses,
  supersede/revoke/dispute, relationships, provenance).
- `forge/aqueduct_ingest.py` — AQUADUCT verification evidence ingestion
  (verifies schema, digest, binding, verifier, timestamp, expiry,
  execution=false, settled=false; never maps to execution/settlement).
- `forge/be.py` — BE evaluation layer producing an explainable
  `EvaluationReceipt` (QUALIFIED / NOT_QUALIFIED / NEEDS_REVIEW).
- `forge/forge_decision.py` — FORGE `PromotionDecision`
  (PROMOTE / RESTRICT / REVOKE / RETAIN / REQUIRE_RETEST / ESCALATE).
- `forge/gate_54t.py` — 54-T governance/security review
  (APPROVE / DENY / RESTRICT / ESCALATE; default ESCALATE, fail closed).
- `forge/erc8004.py` — ERC-8004 external adapter (evidence only, never authority).
- `forge/reputation.py` — reputation views derived from signed evidence.

## BE evaluation

BE consumes Proof Graph evidence and produces an `EvaluationReceipt` with:

- `agent_entity_ref`, `requested_capability`, `requested_authority_change`
- `proof_refs`, `policy_refs`, `evaluation_version`, `evaluator_ref`
- `confidence`, `evidence_completeness`
- `contradictions`, `expired_evidence`, `missing_evidence`
- `risk_tier`, `recommendation`, `timestamp`, `digest`

Recommendation: QUALIFIED / NOT_QUALIFIED / NEEDS_REVIEW.

BE recommendation is NOT authority. BE cannot directly increase budget, signing
authority, asset/counterparty scope, delegation depth, transaction ceiling, or
production access.

## FORGE decision

FORGE consumes the BE `EvaluationReceipt` + Proof Graph references + current
state and produces a `PromotionDecision`. A capability promotion explicitly
defines what changes (capability, old tier, requested tier, approved tier). It
does NOT implicitly change budget, wallet authority, signing authority, asset
permissions, or counterparty permissions.

## 54-T gate

Every production promotion path must pass 54-T governance/security review.
FORGE cannot bypass it. 54-T may APPROVE / DENY / RESTRICT / ESCALATE. 54-T
does NOT execute transactions. Default outcome is ESCALATE (fail closed).

## Authority promotion receipt

If an authority change is eventually approved, a distinct
`AuthorityPromotionReceipt` is emitted through the governed authority process.
Never hide authority growth inside a capability receipt. No self-approval.

## Revocation

Revocation is a first-class path. Triggers include revoked/expired proof, new
contradictory evidence, policy change, security incident, runtime compromise,
model change, adapter change, failed recertification, 54-T finding, or human
revocation. FORGE supports RESTRICT / REVOKE / REQUIRE_RETEST.

## Temporal validity

Proofs carry `issued_at` / `valid_from` / `expires_at` / `revoked_at` /
`superseded_at` semantics. BE does not treat expired proof as current evidence.

## Mission Control

Outputs are designed so Mission Control can visualize the AGENT-ENTITY nucleus,
proof rings, BE evaluation state, FORGE certification state, 54-T governance
state, current authority envelope, revocations, expired evidence, and
contradictions, with drill-down from proof -> receipt -> verifier -> source ->
policy -> decision -> governance -> authority effect.

## Security

Default deny. Fail closed on unknown schema, unknown proof type where policy
requires a known type, invalid digest, missing subject, missing issuer/verifier,
malformed timestamps, expired/revoked required proof, and unresolved mandatory
contradiction. No credentials, private keys, seed phrases, provider secrets, or
unrestricted tool handles in evidence.

## Replay / idempotence

Same immutable proof does not create duplicate authority effects. Ingestion is
idempotent (same proof_id + same digest is a no-op). Repeated BE evaluation is
traceable to the same evidence set, policy version, and evaluator version.
