# Durable Continuity Passport Storage

The Continuity Passport service supports an async store contract. The in-memory adapter exists for tests only.

Production deployments may use the included SQLite-family / Cloudflare D1 schema and adapter, or another approved durable database implementation.

Persistence rules:

- AGENT-ENTITY identity and Agent DID are unique
- runtime binding identifiers are globally unique
- runtime bindings remain subordinate to a passport
- credential fields are references only
- raw private keys and bearer credentials are prohibited
- revocation must survive process restarts and replica changes
- database access is least-privilege
- backup/recovery must preserve revocation and proof lineage
- database state does not itself grant authority

Capability authority is still evaluated outside Forge by the canonical policy/capability corridor.
