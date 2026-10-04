"""Regenerate examples/signed-proof-set.v1.json.

The HMAC key below is a TEST FIXTURE ONLY. It is not a secret and grants nothing.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from forge.proofs import HmacSha256Verifier, canonical_json  # noqa: E402

TEST_VERIFIER_REF = "verifier:aquaduct:test-fixture"
TEST_FIXTURE_KEY = b"TEST-FIXTURE-KEY-NOT-A-SECRET-DO-NOT-USE-IN-PRODUCTION"
AGENT = "agententity:example:atlas-0001"
OUT = Path(__file__).resolve().parent / "signed-proof-set.v1.json"

CLASSES = ("ProofOfCapability", "ProofOfQuote", "ProofOfExecution", "ProofOfSettlement", "ProofOfFiscalDiscipline")


def build() -> dict:
    verifier = HmacSha256Verifier({TEST_VERIFIER_REF: TEST_FIXTURE_KEY})
    proofs = []
    for i, cls in enumerate(CLASSES, start=1):
        envelope = {
            "proof_id": f"proof:example:{i:04d}",
            "proof_class": cls,
            "agent_entity_ref": AGENT,
            "intent_ref": "intent:example:0001",
            "mandate_ref": "mandate:example:0001",
            "execution_envelope_ref": "envelope:example:0001",
            "evidence_refs": [f"aquaduct:receipt:arc-testnet-5042002:{i:04d}"],
            "verifier_ref": TEST_VERIFIER_REF,
            "policy_version_ref": "aegis:policy:v1",
            "security_attestation_ref": f"54t:attestation:{i:04d}",
            "created_at": "2026-09-18T00:00:00Z",
            "status": "VERIFIED",
            "grants_authority": False,
        }
        proofs.append({"envelope": envelope, "signature": verifier.sign(canonical_json(envelope), TEST_VERIFIER_REF)})
    return {
        "_comment": "TEST FIXTURE. Signatures are HMAC-SHA256 with the public test key in generate_signed_proof_set.py. Evidence only; grants no authority.",
        "verifier_ref": TEST_VERIFIER_REF,
        "test_fixture_key_utf8": TEST_FIXTURE_KEY.decode(),
        "proofs": proofs,
    }


if __name__ == "__main__":
    OUT.write_text(json.dumps(build(), indent=2) + "\n")
    print(OUT)
