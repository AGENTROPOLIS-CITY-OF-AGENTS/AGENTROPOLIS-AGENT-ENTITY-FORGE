-- AGENTROPOLIS AGENT-ENTITY Continuity Passport durable store v1
-- SQLite-family / Cloudflare D1 compatible.

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS continuity_passports (
  passport_id TEXT PRIMARY KEY,
  agent_entity_id TEXT NOT NULL UNIQUE,
  agent_did TEXT NOT NULL UNIQUE,
  controller_ref TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('active','restricted','suspended','revoked','recovery')),
  proof_refs_json TEXT NOT NULL DEFAULT '[]',
  memory_refs_json TEXT NOT NULL DEFAULT '[]',
  reputation_view_refs_json TEXT NOT NULL DEFAULT '[]',
  proof_graph_head TEXT,
  issued_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS runtime_bindings (
  runtime_binding_id TEXT PRIMARY KEY,
  passport_id TEXT NOT NULL,
  agent_entity_id TEXT NOT NULL,
  runtime_id TEXT NOT NULL,
  harness_profile_id TEXT,
  credential_ref TEXT NOT NULL,
  dock_session_ref TEXT,
  capability_policy_ref TEXT,
  state TEXT NOT NULL CHECK (state IN ('active','suspended','revoked','expired')),
  issued_at TEXT NOT NULL,
  expires_at TEXT,
  FOREIGN KEY (passport_id) REFERENCES continuity_passports(passport_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_runtime_bindings_passport
  ON runtime_bindings(passport_id);

CREATE INDEX IF NOT EXISTS idx_runtime_bindings_agent_entity
  ON runtime_bindings(agent_entity_id);

CREATE INDEX IF NOT EXISTS idx_runtime_bindings_state
  ON runtime_bindings(state);
