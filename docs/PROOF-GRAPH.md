# AGENT-ENTITY Forge Proof Graph

The Proof Graph is evidence infrastructure. It is not a single reputation score and no proof object grants authority by itself.

## Proof families

Identity and control:
- ProofOfIdentity
- ProofOfControl
- ProofOfMandate
- ProofOfAuthority

Capability and work:
- ProofOfCapability
- ProofOfWork
- ProofOfOutcome
- ProofOfCompetence
- ProofOfRefusal
- ProofOfSLA

Economic:
- ProofOfQuote
- ProofOfPriceProtection
- ProofOfFeeQuote
- ProofOfFeeAuthorization
- ProofOfFeeCollection
- ProofOfRoute
- ProofOfExecution
- ProofOfPartialExecution
- ProofOfBalanceChange
- ProofOfSettlement
- ProofOfTransfer
- ProofOfNetAmount
- ProofOfFiscalDiscipline

Security:
- ProofOfContainment
- ProofOfCapabilityScope
- ProofOfSignerBoundary
- ProofOfSecretIsolation
- ProofOfIntentIntegrity
- ProofOfQuoteIntegrity
- ProofOfIdempotency
- ProofOfRecovery
- ProofOfAdapterIntegrity
- ProofOfDependencyIntegrity
- ProofOfEgressPolicy

Lifecycle:
- ProofOfProvenance
- ProofOfContinuity
- ProofOfDelegation
- ProofOfCompliance
- EvolutionReceipt
- AuthorityPromotionReceipt
- RestrictionReceipt
- RevocationReceipt

## Reputation

Reputation is a derived view over signed evidence. It MUST preserve source, verifier, policy/version context, disputes, reversals, refusals, outcomes and time.

REPUTATION != AUTHORITY.

## Promotion

Forge may consume evidence and determine certification state, but production authority requires the principal/AEGIS approval path.
