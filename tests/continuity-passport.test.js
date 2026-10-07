import test from 'node:test';
import assert from 'node:assert/strict';

import { ContinuityPassportService } from '../src/continuity-passport-service.js';
import { MemoryPassportStore } from '../src/memory-passport-store.js';

function fixture() {
  const proofVerifier = {
    verifyIdentity: async ({ proofRef }) => proofRef === 'proof:identity:ok',
    verifyControl: async ({ proofRef }) => proofRef === 'proof:control:ok',
    verifyContinuity: async ({ proofRef }) => proofRef === 'proof:continuity:ok',
  };
  const service = new ContinuityPassportService({
    store: new MemoryPassportStore(),
    proofVerifier,
    clock: () => new Date('2026-10-06T20:00:00.000Z'),
    passportIdFactory: () => 'passport:axiom:001',
  });
  return { service };
}

const registration = {
  agent_entity_id: 'agt:axiom',
  agent_did: 'did:agentropolis:axiom',
  controller_ref: 'human:neuro',
  identity_proof_ref: 'proof:identity:ok',
  control_proof_ref: 'proof:control:ok',
};

test('registers one persistent passport for an existing AGENT-ENTITY', async () => {
  const { service } = fixture();
  const first = await service.registerExistingEntity(registration);
  const second = await service.registerExistingEntity(registration);

  assert.equal(first.passport_id, 'passport:axiom:001');
  assert.equal(second.passport_id, first.passport_id);
  assert.equal(first.runtime_bindings.length, 0);
});

test('invalid identity proof fails closed', async () => {
  const { service } = fixture();
  await assert.rejects(
    () =>
      service.registerExistingEntity({
        ...registration,
        identity_proof_ref: 'proof:identity:bad',
      }),
    /FORGE_IDENTITY_PROOF_INVALID/,
  );
});

test('attaches a new runtime binding only after continuity proof', async () => {
  const { service } = fixture();
  await service.registerExistingEntity(registration);

  const passport = await service.attachRuntimeBinding('agt:axiom', {
    runtime_binding_id: 'binding:hermes:01',
    runtime_id: 'hermes:local:01',
    credential_ref: 'credential:hermes:01',
    continuity_proof_ref: 'proof:continuity:ok',
    capability_policy_ref: 'capability-policy:hermes:01',
  });

  assert.equal(passport.runtime_bindings.length, 1);
  assert.equal(passport.runtime_bindings[0].state, 'active');
  assert.equal(passport.runtime_bindings[0].capability_policy_ref, 'capability-policy:hermes:01');
});

test('runtime binding does not carry an authority grant field', async () => {
  const { service } = fixture();
  await service.registerExistingEntity(registration);
  const passport = await service.attachRuntimeBinding('agt:axiom', {
    runtime_binding_id: 'binding:codex:01',
    runtime_id: 'codex:01',
    credential_ref: 'credential:codex:01',
    continuity_proof_ref: 'proof:continuity:ok',
  });

  const binding = passport.runtime_bindings[0];
  assert.equal('authority' in binding, false);
  assert.equal('permissions' in binding, false);
  assert.equal('capabilities' in binding, false);
});

test('revokes one runtime binding without revoking the AGENT-ENTITY', async () => {
  const { service } = fixture();
  await service.registerExistingEntity(registration);
  await service.attachRuntimeBinding('agt:axiom', {
    runtime_binding_id: 'binding:hermes:01',
    runtime_id: 'hermes:local:01',
    credential_ref: 'credential:hermes:01',
    continuity_proof_ref: 'proof:continuity:ok',
  });

  const passport = await service.revokeRuntimeBinding('agt:axiom', 'binding:hermes:01');
  assert.equal(passport.status, 'active');
  assert.equal(passport.runtime_bindings[0].state, 'revoked');
});
