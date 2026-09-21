# Arc ERC-8004 Proof Adapter

Status: Arc testnet reference adapter

## Purpose

Map ERC-8004 identity, reputation and validation evidence into the AGENT-ENTITY Forge Proof Graph without replacing AGENTENTITY.

AGENTENTITY remains the canonical persistent entity protocol. ERC-8004 is an external onchain adapter.

## Arc testnet reference contracts

Current Arc documentation identifies the following ERC-8004 contracts on Arc Testnet:

- IdentityRegistry: `0x8004A818BFB912233c491871b3d84c89A494BD9e`
- ReputationRegistry: `0x8004B663056A597Dffe9eCcC1965A193B7388713`
- ValidationRegistry: `0x8004Cb1BF31DAf7788923b405b754f57acEB4272`

These addresses are testnet-scoped and MUST be re-verified against current official Arc documentation before use.

## Identity mapping

```text
AGENTENTITY
   -> external identity binding
   -> ERC-8004 agent token id
   -> metadata URI
   -> owner / controller evidence
```

An ERC-8004 identity token is not the whole Agent Entity. The Forge may bind it as:

- external_identity_type: erc-8004
- network
- registry
- token_id
- metadata_uri
- owner_address
- observed_at
- verification_receipt

This can contribute to `ProofOfIdentity` and `ProofOfControl`.

## Reputation mapping

The Arc quickstart records reputation through an external validator and notes that an agent owner cannot record reputation for its own agent.

AGENTROPOLIS preserves that anti-self-dealing boundary.

ERC-8004 reputation events are external attestations and may contribute to the Proof Graph, but:

```text
ERC-8004 SCORE != CANONICAL AGENT REPUTATION
```

The Forge derives reputation views from signed evidence such as:
- completed work
- verified outcomes
- correct refusals
- reversals / disputes
- SLA performance
- policy violations
- independent feedback
- verifier provenance

A single numeric score never grants authority.

## Validation mapping

ERC-8004 validation uses a request / response flow between the agent owner and a validator.

A validation response may contribute to:
- ProofOfCapability
- ProofOfCompliance

These are the canonical proof classes defined in `docs/PROOF-GRAPH.md`. The
adapter maps ERC-8004 validation evidence to existing canonical classes; it does
not introduce non-canonical proof types.

The response proves only the configured validation claim under the identified validator and request commitment.

It MUST NOT be described as broad legal or regulatory compliance unless the underlying verifier, scope and policy actually establish that claim.

## Forge use

```text
ERC-8004 evidence
      ↓
AQUADUCT verification
      ↓
normalized proof receipts
      ↓
Proof Graph
      ↓
BE evaluation
      ↓
Forge certification decision
      ↓
54-T governance / security review
      ↓
AEGIS / human approval if authority changes
```

## Promotion invariant

```text
IDENTITY TOKEN != AUTHORITY
REPUTATION SCORE != AUTHORITY
VALIDATION PASS != AUTHORITY
```

No ERC-8004 event may silently increase spending limits, signing power, tool access, production environment access or delegation depth.

## Wallet boundary

Arc documentation demonstrates both Circle developer-controlled wallets and self-managed Viem wallets.

AGENTROPOLIS policy remains:
- no raw private keys in agent memory;
- no raw private keys in ATG messages;
- no raw private keys in FISCALITH payloads;
- Circle entity secrets remain server-side;
- production wallet authority remains capability-scoped and revocable.
