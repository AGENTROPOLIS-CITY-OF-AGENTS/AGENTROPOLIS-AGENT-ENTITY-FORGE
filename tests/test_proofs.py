import unittest

from helpers import VERIFIER_REF, envelope, load_json, make_verifier, sign

from forge.proofs import (
    HmacSha256Verifier,
    ProofValidationError,
    SignatureError,
    canonical_json,
    validate_proof_envelope,
    verify_signed_proof,
)


class ProofEnvelopeValidationTests(unittest.TestCase):
    def test_valid_envelope_passes(self):
        self.assertIsNotNone(validate_proof_envelope(envelope("ProofOfCapability")))

    def test_unknown_proof_class_rejected(self):
        with self.assertRaises(ProofValidationError):
            validate_proof_envelope(envelope("ProofOfSettlment"))

    def test_invalid_status_rejected(self):
        with self.assertRaises(ProofValidationError):
            validate_proof_envelope(envelope("ProofOfCapability", status="APPROVED"))

    def test_malformed_date_time_rejected(self):
        with self.assertRaises(ProofValidationError):
            validate_proof_envelope(envelope("ProofOfCapability", created_at="not-a-date"))

    def test_grants_authority_true_rejected(self):
        with self.assertRaises(ProofValidationError):
            validate_proof_envelope(envelope("ProofOfCapability", grants_authority=True))

    def test_additional_properties_rejected(self):
        with self.assertRaises(ProofValidationError):
            validate_proof_envelope(envelope("ProofOfCapability", authority_level="max"))

    def test_verified_proof_requires_policy_version(self):
        with self.assertRaises(ProofValidationError):
            validate_proof_envelope(envelope("ProofOfCapability", policy_version_ref=None))
        validate_proof_envelope(envelope("ProofOfCapability", status="FAILED", policy_version_ref=None))

    def test_empty_evidence_refs_rejected(self):
        with self.assertRaises(ProofValidationError):
            validate_proof_envelope(envelope("ProofOfCapability", evidence_refs=[]))


class CanonicalJsonTests(unittest.TestCase):
    def test_sorted_and_compact(self):
        self.assertEqual(canonical_json({"b": 1, "a": [1, {"z": 0, "y": None}]}), b'{"a":[1,{"y":null,"z":0}],"b":1}')

    def test_key_order_independent(self):
        self.assertEqual(canonical_json({"a": 1, "b": 2}), canonical_json({"b": 2, "a": 1}))


class SignedProofTests(unittest.TestCase):
    def setUp(self):
        self.verifier = make_verifier()
        self.env = envelope("ProofOfCapability")

    def test_valid_signature_accepted(self):
        result = verify_signed_proof(self.env, sign(self.env), self.verifier)
        self.assertTrue(result["security_bound"])
        self.assertEqual(result["envelope"], self.env)

    def test_unsigned_proof_rejected(self):
        for sig in (None, ""):
            with self.assertRaises(SignatureError):
                verify_signed_proof(self.env, sig, self.verifier)

    def test_tampered_envelope_rejected(self):
        sig = sign(self.env)
        tampered = dict(self.env, agent_entity_ref="agententity:test:attacker")
        with self.assertRaises(SignatureError):
            verify_signed_proof(tampered, sig, self.verifier)

    def test_unknown_verifier_ref_rejected(self):
        env = envelope("ProofOfCapability", verifier_ref="verifier:unknown")
        with self.assertRaises(SignatureError):
            verify_signed_proof(env, sign(self.env), self.verifier)

    def test_wrong_key_rejected(self):
        other = HmacSha256Verifier({VERIFIER_REF: b"different-test-key"})
        with self.assertRaises(SignatureError):
            verify_signed_proof(self.env, sign(self.env), other)

    def test_missing_security_attestation_flagged_not_rejected(self):
        env = envelope("ProofOfCapability", security=False)
        result = verify_signed_proof(env, sign(env), self.verifier)
        self.assertFalse(result["security_bound"])

    def test_verifier_does_not_expose_keys(self):
        self.assertFalse(hasattr(self.verifier, "keys"))
        self.assertNotIn("_keys", vars(HmacSha256Verifier))


class ExampleFixtureTests(unittest.TestCase):
    def test_example_signed_proof_set_verifies(self):
        fixture = load_json("examples/signed-proof-set.v1.json")
        verifier = HmacSha256Verifier({fixture["verifier_ref"]: fixture["test_fixture_key_utf8"].encode()})
        self.assertEqual(len(fixture["proofs"]), 5)
        for item in fixture["proofs"]:
            result = verify_signed_proof(item["envelope"], item["signature"], verifier)
            self.assertTrue(result["security_bound"])
            self.assertIs(item["envelope"]["grants_authority"], False)


if __name__ == "__main__":
    unittest.main()
