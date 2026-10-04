import unittest
from datetime import timedelta

from helpers import AGENT, NOW, REQUIRED, add_required_set, envelope, make_verifier, sign

from forge.proof_graph import DuplicateProof, ProofGraph, UnknownProof
from forge.proofs import SignatureError


class ProofGraphTests(unittest.TestCase):
    def setUp(self):
        self.graph = ProofGraph(make_verifier(), ttl=timedelta(days=30), clock=lambda: NOW)

    def test_unsigned_proof_rejected(self):
        env = envelope("ProofOfCapability")
        with self.assertRaises(SignatureError):
            self.graph.add_proof(env, None)
        with self.assertRaises(SignatureError):
            self.graph.add_proof(env, "deadbeef")
        self.assertEqual(len(self.graph), 0)

    def test_duplicate_proof_id_rejected(self):
        env = envelope("ProofOfCapability")
        self.graph.add_proof(env, sign(env))
        with self.assertRaises(DuplicateProof):
            self.graph.add_proof(env, sign(env))

    def test_stale_verified_proof_stored_as_expired(self):
        env = envelope("ProofOfCapability", created_at="2026-01-01T00:00:00Z")
        record = self.graph.add_proof(env, sign(env))
        self.assertEqual(record.status, "EXPIRED")
        self.assertFalse(self.graph.has_verified_set(AGENT, ["ProofOfCapability"]))

    def test_fresh_verified_proof_stays_verified(self):
        env = envelope("ProofOfCapability")
        self.assertEqual(self.graph.add_proof(env, sign(env)).status, "VERIFIED")

    def test_proofs_for_filters(self):
        add_required_set(self.graph)
        other = envelope("ProofOfQuote", agent="agententity:test:other")
        self.graph.add_proof(other, sign(other))
        self.assertEqual(len(self.graph.proofs_for(AGENT)), 5)
        self.assertEqual(len(self.graph.proofs_for(AGENT, proof_class="ProofOfQuote")), 1)
        self.assertEqual(len(self.graph.proofs_for(AGENT, status="REVOKED")), 0)

    def test_has_verified_set(self):
        add_required_set(self.graph)
        self.assertTrue(self.graph.has_verified_set(AGENT, REQUIRED))
        self.assertFalse(self.graph.has_verified_set(AGENT, REQUIRED + ("ProofOfContainment",)))

    def test_pass_evidence_without_security_attestation_is_insufficient(self):
        add_required_set(self.graph, security=False)
        self.assertFalse(self.graph.has_verified_set(AGENT, REQUIRED, require_security_bound=True))
        self.assertTrue(self.graph.has_verified_set(AGENT, REQUIRED, require_security_bound=False))

    def test_dispute_and_revoke_append_history(self):
        env = envelope("ProofOfCapability")
        first = self.graph.add_proof(env, sign(env))
        disputed = self.graph.dispute(env["proof_id"], "receipt mismatch")
        revoked = self.graph.revoke(env["proof_id"], "verifier compromised")
        self.assertEqual([r.status for r in self.graph.history(env["proof_id"])], ["VERIFIED", "DISPUTED", "REVOKED"])
        self.assertEqual(first.status, "VERIFIED")
        self.assertEqual(disputed.reason, "receipt mismatch")
        self.assertEqual(self.graph.current(env["proof_id"]), revoked)
        self.assertFalse(self.graph.has_verified_set(AGENT, ["ProofOfCapability"]))

    def test_records_are_immutable(self):
        env = envelope("ProofOfCapability")
        record = self.graph.add_proof(env, sign(env))
        with self.assertRaises(AttributeError):
            record.status = "REVOKED"
        self.assertIs(record.grants_authority, False)

    def test_status_change_requires_reason(self):
        env = envelope("ProofOfCapability")
        self.graph.add_proof(env, sign(env))
        with self.assertRaises(ValueError):
            self.graph.revoke(env["proof_id"], "")

    def test_unknown_proof(self):
        with self.assertRaises(UnknownProof):
            self.graph.dispute("proof:nope", "x")

    def test_events_emitted(self):
        events = []
        self.graph.subscribe(events.append)
        env = envelope("ProofOfCapability")
        self.graph.add_proof(env, sign(env))
        self.graph.dispute(env["proof_id"], "r")
        self.assertEqual([e.kind for e in events], ["added", "disputed"])


if __name__ == "__main__":
    unittest.main()
