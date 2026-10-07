# AGENT-ENTITY Continuity Passport

Status: PROPOSED CANONICAL FORGE CONTRACT

The Continuity Passport is the portable, evidence-backed continuity record for a persistent AGENT-ENTITY across replaceable runtimes.

It is not a private key, wallet, prompt dump, unrestricted memory export, or blanket authorization token.

## Core rule

```text
THE AGENT-ENTITY PERSISTS.
RUNTIMES ARE REPLACEABLE.
RUNTIME CREDENTIALS ARE SCOPED.
AUTHORITY MUST BE RE-EVALUATED PER BINDING.
```

## Passport responsibilities

A Continuity Passport links:

- canonical AGENT-ENTITY identifier
- Agent DID / verification method references
- controller relationships
- ProofOfIdentity
- ProofOfControl
- ProofOfContinuity
- lineage/provenance
- continuity-safe memory references
- verified skill/capability evidence
- runtime bindings
- restriction/revocation state
- proof-graph head / evidence references

It MUST NOT embed raw secrets.

## Runtime-binding rule

A runtime binding proves that a particular runtime instance is permitted to represent the same persistent AGENT-ENTITY for a bounded period and purpose.

A binding does not inherit all permissions from another runtime.

```text
SAME AGENT-ENTITY
  !=
SAME RUNTIME
  !=
SAME CREDENTIAL
  !=
SAME CAPABILITY SET
  !=
SAME AUTHORITY
```

## Promotion and recovery

Forge may certify continuity when the required identity, control and provenance evidence is valid. Recovery or replacement of a lost runtime credential SHOULD issue a new binding and produce a recovery/revocation receipt for the old one.

Forge certification is evidence. Production authority still requires the principal/AEGIS approval path.

## Required proof chain

For an existing entity attaching a new runtime:

```text
ProofOfIdentity
  + ProofOfControl
  + ProofOfContinuity
  + runtime provenance
  -> Continuity Passport update
  -> runtime binding
  -> policy/capability evaluation
```

## Duplicate-entity prevention

When a valid continuity proof resolves to an existing AGENT-ENTITY, Forge MUST update that entity's passport or binding set rather than minting a second identity record.

## Relationship to Dock

Dock handles arrival and attachment. Forge handles persistent entity proof and lifecycle state.

```text
DOCK -> resolve claim -> FORGE / identity proof -> runtime binding -> AEGIS / Capability Grid
```
