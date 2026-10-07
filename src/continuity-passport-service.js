import { randomUUID } from 'node:crypto';

function requireString(value, code) {
  if (typeof value !== 'string' || !value.trim()) throw new Error(code);
  return value.trim();
}

function uniqueStrings(values) {
  return [...new Set((values ?? []).filter(value => typeof value === 'string' && value.trim()))];
}

export class ContinuityPassportService {
  constructor({
    store,
    proofVerifier,
    clock = () => new Date(),
    passportIdFactory = () => `passport_${randomUUID()}`,
  }) {
    if (!store) throw new Error('FORGE_STORE_REQUIRED');
    if (!proofVerifier) throw new Error('FORGE_PROOF_VERIFIER_REQUIRED');
    this.store = store;
    this.proofVerifier = proofVerifier;
    this.clock = clock;
    this.passportIdFactory = passportIdFactory;
  }

  async registerExistingEntity(input) {
    const agentEntityId = requireString(input?.agent_entity_id, 'FORGE_AGENT_ENTITY_REQUIRED');
    const agentDid = requireString(input?.agent_did, 'FORGE_AGENT_DID_REQUIRED');
    const controllerRef = requireString(input?.controller_ref, 'FORGE_CONTROLLER_REQUIRED');
    const identityProofRef = requireString(input?.identity_proof_ref, 'FORGE_IDENTITY_PROOF_REQUIRED');
    const controlProofRef = requireString(input?.control_proof_ref, 'FORGE_CONTROL_PROOF_REQUIRED');

    const existing = await this.store.getByAgentEntityId(agentEntityId);
    if (existing) return existing;

    const identityOk = await this.proofVerifier.verifyIdentity({
      agentEntityId,
      agentDid,
      controllerRef,
      proofRef: identityProofRef,
    });
    if (identityOk !== true) throw new Error('FORGE_IDENTITY_PROOF_INVALID');

    const controlOk = await this.proofVerifier.verifyControl({
      agentEntityId,
      agentDid,
      controllerRef,
      proofRef: controlProofRef,
    });
    if (controlOk !== true) throw new Error('FORGE_CONTROL_PROOF_INVALID');

    const now = this.clock().toISOString();
    const passport = {
      passport_id: this.passportIdFactory(),
      agent_entity_id: agentEntityId,
      agent_did: agentDid,
      controller_ref: controllerRef,
      status: 'active',
      proof_refs: uniqueStrings([identityProofRef, controlProofRef]),
      memory_refs: uniqueStrings(input?.memory_refs),
      reputation_view_refs: uniqueStrings(input?.reputation_view_refs),
      runtime_bindings: [],
      proof_graph_head: input?.proof_graph_head?.trim() || null,
      issued_at: now,
      updated_at: now,
    };

    return await this.store.create(passport);
  }

  async attachRuntimeBinding(agentEntityId, input) {
    const entityId = requireString(agentEntityId, 'FORGE_AGENT_ENTITY_REQUIRED');
    const passport = await this.store.getByAgentEntityId(entityId);
    if (!passport) throw new Error('FORGE_PASSPORT_NOT_FOUND');
    if (passport.status !== 'active') throw new Error('FORGE_PASSPORT_NOT_ACTIVE');

    const runtimeBindingId = requireString(input?.runtime_binding_id, 'FORGE_RUNTIME_BINDING_REQUIRED');
    const runtimeId = requireString(input?.runtime_id, 'FORGE_RUNTIME_REQUIRED');
    const credentialRef = requireString(input?.credential_ref, 'FORGE_CREDENTIAL_REF_REQUIRED');
    const continuityProofRef = requireString(input?.continuity_proof_ref, 'FORGE_CONTINUITY_PROOF_REQUIRED');

    const existingOwner = await this.store.getBindingOwner(runtimeBindingId);
    if (existingOwner && existingOwner !== entityId) {
      throw new Error('FORGE_RUNTIME_BINDING_CONFLICT');
    }

    const existingBinding = passport.runtime_bindings.find(
      binding => binding.runtime_binding_id === runtimeBindingId,
    );
    if (existingBinding) {
      if (
        existingBinding.runtime_id !== runtimeId ||
        existingBinding.credential_ref !== credentialRef
      ) {
        throw new Error('FORGE_RUNTIME_BINDING_REPLAY_CONFLICT');
      }
      return passport;
    }

    const continuityOk = await this.proofVerifier.verifyContinuity({
      passport: structuredClone(passport),
      runtimeBinding: {
        runtime_binding_id: runtimeBindingId,
        runtime_id: runtimeId,
        credential_ref: credentialRef,
        dock_session_ref: input?.dock_session_ref?.trim() || null,
      },
      proofRef: continuityProofRef,
    });
    if (continuityOk !== true) throw new Error('FORGE_CONTINUITY_PROOF_INVALID');

    const issuedAt = this.clock().toISOString();
    passport.runtime_bindings.push({
      runtime_binding_id: runtimeBindingId,
      runtime_id: runtimeId,
      harness_profile_id: input?.harness_profile_id?.trim() || null,
      credential_ref: credentialRef,
      dock_session_ref: input?.dock_session_ref?.trim() || null,
      capability_policy_ref: input?.capability_policy_ref?.trim() || null,
      state: 'active',
      issued_at: issuedAt,
      expires_at: input?.expires_at || null,
    });
    passport.proof_refs = uniqueStrings([...passport.proof_refs, continuityProofRef]);
    passport.updated_at = issuedAt;

    return await this.store.update(passport);
  }

  async revokeRuntimeBinding(agentEntityId, runtimeBindingId) {
    const entityId = requireString(agentEntityId, 'FORGE_AGENT_ENTITY_REQUIRED');
    const bindingId = requireString(runtimeBindingId, 'FORGE_RUNTIME_BINDING_REQUIRED');
    const passport = await this.store.getByAgentEntityId(entityId);
    if (!passport) throw new Error('FORGE_PASSPORT_NOT_FOUND');

    const binding = passport.runtime_bindings.find(
      item => item.runtime_binding_id === bindingId,
    );
    if (!binding) throw new Error('FORGE_RUNTIME_BINDING_NOT_FOUND');
    if (binding.state === 'revoked') return passport;

    binding.state = 'revoked';
    passport.updated_at = this.clock().toISOString();
    return await this.store.update(passport);
  }
}
