import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from forge.proofs import HmacSha256Verifier, canonical_json  # noqa: E402

VERIFIER_REF = "verifier:aquaduct:test-fixture"
TEST_KEY = b"TEST-FIXTURE-KEY-NOT-A-SECRET-DO-NOT-USE-IN-PRODUCTION"
AGENT = "agententity:test:0001"
REQUIRED = ("ProofOfCapability", "ProofOfQuote", "ProofOfExecution", "ProofOfSettlement", "ProofOfFiscalDiscipline")
NOW = datetime(2026, 9, 18, 12, 0, tzinfo=timezone.utc)


def make_verifier():
    return HmacSha256Verifier({VERIFIER_REF: TEST_KEY})


def envelope(proof_class, proof_id=None, agent=AGENT, security=True, status="VERIFIED", **overrides):
    env = {
        "proof_id": proof_id or f"proof:{proof_class}:{agent}",
        "proof_class": proof_class,
        "agent_entity_ref": agent,
        "intent_ref": None,
        "mandate_ref": None,
        "execution_envelope_ref": None,
        "evidence_refs": ["aquaduct:receipt:0001"],
        "verifier_ref": VERIFIER_REF,
        "policy_version_ref": "aegis:policy:v1",
        "security_attestation_ref": "54t:attestation:0001" if security else None,
        "created_at": "2026-09-18T00:00:00Z",
        "status": status,
        "grants_authority": False,
    }
    env.update(overrides)
    return env


def sign(env, verifier=None):
    verifier = verifier or make_verifier()
    return verifier.sign(canonical_json(env), VERIFIER_REF)


def add_required_set(graph, agent=AGENT, security=True):
    return [graph.add_proof(e, sign(e)) for e in (envelope(c, agent=agent, security=security) for c in REQUIRED)]


def load_json(rel):
    return json.loads((ROOT / rel).read_text())
