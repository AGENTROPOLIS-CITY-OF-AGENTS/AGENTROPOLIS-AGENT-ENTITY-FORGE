function parseArray(value) {
  if (!value) return [];
  const parsed = JSON.parse(value);
  return Array.isArray(parsed) ? parsed : [];
}

function rowToBinding(row) {
  return {
    runtime_binding_id: row.runtime_binding_id,
    runtime_id: row.runtime_id,
    harness_profile_id: row.harness_profile_id,
    credential_ref: row.credential_ref,
    dock_session_ref: row.dock_session_ref,
    capability_policy_ref: row.capability_policy_ref,
    state: row.state,
    issued_at: row.issued_at,
    expires_at: row.expires_at,
  };
}

export class D1PassportStore {
  constructor(db) {
    if (!db || typeof db.prepare !== 'function') {
      throw new Error('FORGE_DATABASE_REQUIRED');
    }
    this.db = db;
  }

  async #bindingsFor(passportId) {
    const result = await this.db
      .prepare('SELECT * FROM runtime_bindings WHERE passport_id = ?1 ORDER BY issued_at ASC')
      .bind(passportId)
      .all();
    return (result?.results ?? []).map(rowToBinding);
  }

  async #rowToPassport(row) {
    if (!row) return null;
    return {
      passport_id: row.passport_id,
      agent_entity_id: row.agent_entity_id,
      agent_did: row.agent_did,
      controller_ref: row.controller_ref,
      status: row.status,
      proof_refs: parseArray(row.proof_refs_json),
      memory_refs: parseArray(row.memory_refs_json),
      reputation_view_refs: parseArray(row.reputation_view_refs_json),
      runtime_bindings: await this.#bindingsFor(row.passport_id),
      proof_graph_head: row.proof_graph_head,
      issued_at: row.issued_at,
      updated_at: row.updated_at,
    };
  }

  async getByPassportId(passportId) {
    const row = await this.db
      .prepare('SELECT * FROM continuity_passports WHERE passport_id = ?1 LIMIT 1')
      .bind(passportId)
      .first();
    return await this.#rowToPassport(row);
  }

  async getByAgentEntityId(agentEntityId) {
    const row = await this.db
      .prepare('SELECT * FROM continuity_passports WHERE agent_entity_id = ?1 LIMIT 1')
      .bind(agentEntityId)
      .first();
    return await this.#rowToPassport(row);
  }

  async getBindingOwner(runtimeBindingId) {
    const row = await this.db
      .prepare('SELECT agent_entity_id FROM runtime_bindings WHERE runtime_binding_id = ?1 LIMIT 1')
      .bind(runtimeBindingId)
      .first();
    return row?.agent_entity_id ?? null;
  }

  async create(passport) {
    await this.db
      .prepare(
        `INSERT INTO continuity_passports (
          passport_id,agent_entity_id,agent_did,controller_ref,status,
          proof_refs_json,memory_refs_json,reputation_view_refs_json,
          proof_graph_head,issued_at,updated_at
        ) VALUES (?1,?2,?3,?4,?5,?6,?7,?8,?9,?10,?11)`,
      )
      .bind(
        passport.passport_id,
        passport.agent_entity_id,
        passport.agent_did,
        passport.controller_ref,
        passport.status,
        JSON.stringify(passport.proof_refs ?? []),
        JSON.stringify(passport.memory_refs ?? []),
        JSON.stringify(passport.reputation_view_refs ?? []),
        passport.proof_graph_head ?? null,
        passport.issued_at,
        passport.updated_at,
      )
      .run();

    return this.getByPassportId(passport.passport_id);
  }

  async update(passport) {
    await this.db
      .prepare(
        `UPDATE continuity_passports SET
          status=?2,proof_refs_json=?3,memory_refs_json=?4,
          reputation_view_refs_json=?5,proof_graph_head=?6,updated_at=?7
        WHERE passport_id=?1`,
      )
      .bind(
        passport.passport_id,
        passport.status,
        JSON.stringify(passport.proof_refs ?? []),
        JSON.stringify(passport.memory_refs ?? []),
        JSON.stringify(passport.reputation_view_refs ?? []),
        passport.proof_graph_head ?? null,
        passport.updated_at,
      )
      .run();

    for (const binding of passport.runtime_bindings ?? []) {
      await this.db
        .prepare(
          `INSERT INTO runtime_bindings (
            runtime_binding_id,passport_id,agent_entity_id,runtime_id,harness_profile_id,
            credential_ref,dock_session_ref,capability_policy_ref,state,issued_at,expires_at
          ) VALUES (?1,?2,?3,?4,?5,?6,?7,?8,?9,?10,?11)
          ON CONFLICT(runtime_binding_id) DO UPDATE SET
            harness_profile_id=excluded.harness_profile_id,
            dock_session_ref=excluded.dock_session_ref,
            capability_policy_ref=excluded.capability_policy_ref,
            state=excluded.state,
            expires_at=excluded.expires_at`,
        )
        .bind(
          binding.runtime_binding_id,
          passport.passport_id,
          passport.agent_entity_id,
          binding.runtime_id,
          binding.harness_profile_id ?? null,
          binding.credential_ref,
          binding.dock_session_ref ?? null,
          binding.capability_policy_ref ?? null,
          binding.state,
          binding.issued_at,
          binding.expires_at ?? null,
        )
        .run();
    }

    return this.getByPassportId(passport.passport_id);
  }
}
