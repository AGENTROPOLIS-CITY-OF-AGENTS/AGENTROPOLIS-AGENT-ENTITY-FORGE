# AGENT-ENTITY Capability Leases and Revocation

Status: CANONICAL DIRECTION  
Date: 2026-09-18

AGENT-ENTITY persists identity, provenance, lineage, rights, and history. Privileged execution authority is represented through bounded capability leases rather than ambient access.

## Capability lease

```ts
export type CapabilityLease = {
  leaseId: string;
  actorEntityId: string;
  grantorEntityId: string;
  action: string;
  resource: string;
  scope?: string[];
  issuedAt: string;
  expiresAt: string;
  maxOperations?: number;
  delegationDepth: number;
  maxDelegationDepth: number;
  economicLimit?: {
    asset: string;
    amount: string;
  };
  requiredApprovals?: string[];
  prohibitedActions?: string[];
  parentLeaseId?: string;
  receiptRequired: boolean;
  revokedAt?: string;
  revocationReason?: string;
};
```

## Invariants

1. Identity persists; authority expires.
2. Child scope cannot exceed parent scope.
3. Child expiry cannot exceed parent expiry.
4. Child economic limit cannot exceed remaining parent limit.
5. Child delegation depth cannot exceed parent allowance.
6. Parent revocation invalidates descendants.
7. Connector sessions are references, not authority.
8. Wallet possession is not authority.
9. Model intelligence is not authority.
10. Context transfer is not authority transfer.

## Authority lineage

Every privileged action should be able to reconstruct:

```text
HUMAN / ORGANIZATION
 -> AGENT-ENTITY
 -> ROOT MANDATE
 -> CAPABILITY LEASE
 -> OPTIONAL CHILD LEASE
 -> EXECUTION
 -> RECEIPT
```

## Economic authority

Economic leases may bind:

- allowed asset;
- maximum amount;
- maximum total fees;
- approved counterparties;
- eligible rails;
- expiry;
- transaction count;
- required approvals.

PAYRAIL may select Arc or another eligible rail only inside those bounds.

## Representation independence

The same AGENT-ENTITY may appear as a bot, software agent, TCG card, spatial avatar, robot, service, or future representation. Authority must not silently expand when representation changes.
