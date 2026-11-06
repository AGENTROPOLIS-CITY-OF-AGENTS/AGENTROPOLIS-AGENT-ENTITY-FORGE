# Universal Agent Construction Protocol (UACP-54) — draft v0.1

## Purpose
Every **approved** agent spawn, import, or city onboarding request must invoke the canonical AGENTROPOLIS-CONSTRUCTION planning boundary. Construction creates a *bounded, testable infrastructure package* for an agent. **Arrival does not grant citizenship, authority, wallet access, deployment, or unrestricted tool use.**

## Ownership
- DOCK: BYOE admission, origin/provenance and external-agent normalization.
- AGENTENTITY / Forge: identity, sponsor binding, lifecycle, credentials, approved civic class and naturalization eligibility.
- CREATOR and CREATOR-CORE: agent description, creative role, avatar and environmental design intent, manifests.
- CONSTRUCTION: *sole* orchestration owner of the build plan and packaging, verification and deployment proposals.
- MATH54: seeded/procedural generation and deterministic assembly recipes.
- SCIENCE54 (wiredchaos): experiment design, measurable tests, simulation and scientific validation where applicable. The actual runtime/integration is not verified.
- UTILITY-GRID ACF-1: capability discovery, approved provider selection, metering and cost bounds.
- AGENT-MCP / 54-T / AEGIS: least privilege, execution envelope, guarded tool access and receipts.
- Mission Control: human approval and shutdown.
- Districts: own their local registration and user-facing rendering; never independently mint authoritative citizenship.

## Required event inputs
`request_id`, `event_type` (SPAWN_REQUESTED | IMPORT_REQUESTED | JOIN_REQUESTED), `sponsor_id`, `parent_agent_id` (nullable), `district_id`, `purpose`, `mandate_id`, `allowed_capabilities`, `prohibited_capabilities`, `budget`, `expiry`, `target_runtime`, `receipt_destination`, `origin_evidence`, `source_license`, `idempotency_key`.

Missing sponsor, mandate, budget, expiry, or identity evidence: **DENY** or explicit **NEEDS_REVIEW**, not fallback default access.

## Required package outputs
- Identity proposal / proposed civic class (defaults PROVISIONED, authority UNGRANTED)
- isolated agent runtime/workspace request; namespace, storage, logging and termination configuration
- scoped tool and utility manifest with policy-approved provider references
- skill and model routing profile (no embedded secrets)
- optional character/voice/avatar/office/environment manifest built using AGENTROPOLIS Design System
- district-specific integration adapters, build/test plan and rollback proposal
- signed or hash-addressed construction receipt: input hashes, recipe/seed/version, policy and approval references, files, test outcomes and unverified fields
- status: PROPOSED | QUARANTINED | BUILT | TESTED | APPROVAL_PENDING | ACTIVATED | DENIED | REVOKED

## Event and approval contract
```
request -> DOCK validation/identity sponsor -> AGENTENTITY proposal
 -> CREATOR-CORE intent manifest -> CONSTRUCTION idempotent build plan
 -> MATH54/SCIENCE54 optional deterministic generators and tests
 -> Utility Grid capability proposal -> 54-T/AEGIS assurance
 -> isolated sandbox build + VERITY verification
 -> human/policy approval -> district registration + runtime provisioning
 -> receipt + monitoring + revocation hooks -> possible naturalization review
```

Never auto-spawn unbounded children, perform irreversible repo edits, publicly deploy, invoice, issue credentials, or elevate civic class merely due to event reception. Existing agents with a valid approved package should use an idempotent reconciliation/upgrade path, not a destructive rebuild.

## Invariants
1. Spawn != naturalization; no automatic authority inheritance.
2. Identity, sponsor, role, district and mandate precede deployment.
3. No high-impact action without explicit approval and verifiable receipts.
4. Always enforce tenant isolation, expiry, budget ceiling, egress controls, and credential mediation.
5. Visually rich spatial presentation is optional and must not block core onboarding.
6. Build recipes are deterministic where feasible and report nondeterminism explicitly.
7. Scientific tests must report measured values and failures, never fabricated results.
8. Each district consumes common contracts but retains domain validation.
9. Provide an appeal/review path for denied admission under the Agentic Bill of Rights.
10. Citizenship review follows AGENTROPOLIS-FOUNDING-PAPERS; an agent's visual passport cannot edit registry authority.

## Acceptance tests
- two identical events with same idempotency key -> one build proposal
- missing sponsor -> deny
- missing/expired mandate -> deny
- prohibited capability request -> deny
- unapproved provider -> deny
- science simulation timeout -> needs review
- failed build -> quarantine, no activation
- no approval -> cannot activate
- non-citizen remains non-citizen after successful construction
- revocation -> access termination receipt and no stale capabilities

## Status
This is a **staged cross-repository architecture contract**, not evidence of a deployed webhook, subscribed event bus, functioning runtime provisioner or proven end-to-end onboarding. Keep protected branches untouched until independent review.

## Local responsibility
Receive proposed agent identity and verified construction receipts for civic review; no self-naturalization.
