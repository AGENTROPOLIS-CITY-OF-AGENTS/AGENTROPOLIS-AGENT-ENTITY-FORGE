function clone(value) {
  return value == null ? value : structuredClone(value);
}

export class MemoryPassportStore {
  #byPassport = new Map();
  #byEntity = new Map();
  #bindingOwners = new Map();

  getByPassportId(passportId) {
    return clone(this.#byPassport.get(passportId) ?? null);
  }

  getByAgentEntityId(agentEntityId) {
    const passportId = this.#byEntity.get(agentEntityId);
    return passportId ? this.getByPassportId(passportId) : null;
  }

  create(passport) {
    if (this.#byPassport.has(passport.passport_id)) {
      throw new Error('FORGE_PASSPORT_ID_CONFLICT');
    }
    if (this.#byEntity.has(passport.agent_entity_id)) {
      throw new Error('FORGE_AGENT_ENTITY_ALREADY_REGISTERED');
    }
    this.#byPassport.set(passport.passport_id, clone(passport));
    this.#byEntity.set(passport.agent_entity_id, passport.passport_id);
    return this.getByPassportId(passport.passport_id);
  }

  update(passport) {
    if (!this.#byPassport.has(passport.passport_id)) {
      throw new Error('FORGE_PASSPORT_NOT_FOUND');
    }

    for (const binding of passport.runtime_bindings ?? []) {
      const owner = this.#bindingOwners.get(binding.runtime_binding_id);
      if (owner && owner !== passport.agent_entity_id) {
        throw new Error('FORGE_RUNTIME_BINDING_CONFLICT');
      }
      this.#bindingOwners.set(binding.runtime_binding_id, passport.agent_entity_id);
    }

    this.#byPassport.set(passport.passport_id, clone(passport));
    this.#byEntity.set(passport.agent_entity_id, passport.passport_id);
    return this.getByPassportId(passport.passport_id);
  }

  getBindingOwner(runtimeBindingId) {
    return this.#bindingOwners.get(runtimeBindingId) ?? null;
  }
}
