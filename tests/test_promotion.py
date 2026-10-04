import unittest
from datetime import timedelta

from helpers import AGENT, NOW, REQUIRED, add_required_set, envelope, load_json, make_verifier, sign
from jsonschema import Draft202012Validator, FormatChecker

from forge.proof_graph import ProofGraph
from forge.promotion import (
    CertificationState as S,
    ExternalApprovalRequired,
    InsufficientEvidence,
    InvalidTransition,
    PromotionCorridor,
)

STATE_SCHEMA = load_json("schemas/certification-state.v1.json")
STATE_VALIDATOR = Draft202012Validator(STATE_SCHEMA, format_checker=FormatChecker())


class PromotionCorridorTests(unittest.TestCase):
    def setUp(self):
        self.graph = ProofGraph(make_verifier(), ttl=timedelta(days=30), clock=lambda: NOW)
        self.corridor = PromotionCorridor(self.graph, clock=lambda: NOW)

    def certified(self, security=True):
        add_required_set(self.graph, security=security)
        self.corridor.nominate(AGENT)
        self.corridor.certify(AGENT)
        return self.corridor

    def test_nominate(self):
        self.assertEqual(self.corridor.state(AGENT), S.UNCERTIFIED)
        self.corridor.nominate(AGENT)
        self.assertEqual(self.corridor.state(AGENT), S.CANDIDATE)
        with self.assertRaises(InvalidTransition):
            self.corridor.nominate(AGENT)

    def test_certify_requires_full_verified_set(self):
        self.corridor.nominate(AGENT)
        with self.assertRaises(InsufficientEvidence) as ctx:
            self.corridor.certify(AGENT)
        self.assertEqual(ctx.exception.missing, list(REQUIRED))
        add_required_set(self.graph)
        self.corridor.certify(AGENT)
        self.assertEqual(self.corridor.state(AGENT), S.CERTIFIED)

    def test_certify_requires_candidate(self):
        add_required_set(self.graph)
        with self.assertRaises(InvalidTransition):
            self.corridor.certify(AGENT)

    def test_test_pass_evidence_without_security_attestation_is_insufficient(self):
        add_required_set(self.graph, security=False)
        self.corridor.nominate(AGENT)
        with self.assertRaises(InsufficientEvidence) as ctx:
            self.corridor.certify(AGENT)
        self.assertEqual(ctx.exception.missing, list(REQUIRED))
        self.assertEqual(self.corridor.state(AGENT), S.CANDIDATE)

    def test_certification_does_not_self_promote(self):
        self.certified()
        with self.assertRaises(InvalidTransition):
            self.corridor.certify(AGENT)
        for cls in ("ProofOfContainment", "ProofOfSLA", "ProofOfOutcome"):
            env = envelope(cls)
            self.graph.add_proof(env, sign(env))
        self.assertEqual(self.corridor.state(AGENT), S.CERTIFIED)
        with self.assertRaises(ExternalApprovalRequired):
            self.corridor.approve_production(AGENT)
        with self.assertRaises(ExternalApprovalRequired):
            self.corridor.approve_production(AGENT, aegis_decision_ref="", human_approval_ref="   ")
        self.assertEqual(self.corridor.state(AGENT), S.CERTIFIED)

    def test_production_requires_external_approval_ref(self):
        self.certified()
        self.corridor.approve_production(AGENT, aegis_decision_ref="aegis:decision:0001")
        self.assertEqual(self.corridor.state(AGENT), S.PRODUCTION_APPROVED)
        self.assertEqual(self.corridor.status(AGENT)["history"][-1]["aegis_decision_ref"], "aegis:decision:0001")

    def test_production_requires_certified_state(self):
        self.corridor.nominate(AGENT)
        with self.assertRaises(InvalidTransition):
            self.corridor.approve_production(AGENT, human_approval_ref="human:approval:0001")

    def test_reputation_is_not_authority(self):
        self.certified()
        for i in range(50):
            env = envelope("ProofOfOutcome", proof_id=f"proof:outcome:{i}")
            self.graph.add_proof(env, sign(env))
        status = self.corridor.status(AGENT)
        self.assertEqual(status["state"], S.CERTIFIED.value)
        self.assertIs(status["reputation_is_authority"], False)
        self.assertIs(status["grants_authority"], False)

    def test_settlement_proof_does_not_mutate_agent_entity_state(self):
        for before in (S.UNCERTIFIED, S.CANDIDATE):
            agent = f"agententity:test:{before.value.lower()}"
            if before == S.CANDIDATE:
                self.corridor.nominate(agent)
            snapshot = self.corridor.status(agent)
            env = envelope("ProofOfSettlement", agent=agent, proof_id=f"proof:settle:{agent}")
            self.graph.add_proof(env, sign(env))
            self.assertEqual(self.corridor.status(agent), snapshot)
        self.certified()
        snapshot = self.corridor.status(AGENT)
        env = envelope("ProofOfSettlement", proof_id="proof:settle:extra")
        self.graph.add_proof(env, sign(env))
        self.assertEqual(self.corridor.status(AGENT), snapshot)
        self.assertEqual(len(self.graph.proofs_for(AGENT, proof_class="ProofOfSettlement")), 2)

    def test_restrict_and_revoke_transitions(self):
        self.certified()
        self.corridor.restrict(AGENT, "policy change")
        self.assertEqual(self.corridor.state(AGENT), S.RESTRICTED)
        with self.assertRaises(InvalidTransition):
            self.corridor.restrict(AGENT, "again")
        self.corridor.revoke(AGENT, "mandate withdrawn")
        self.assertEqual(self.corridor.state(AGENT), S.REVOKED)
        with self.assertRaises(InvalidTransition):
            self.corridor.revoke(AGENT, "again")
        self.corridor.revoke("agententity:test:fresh", "never trusted")
        self.assertEqual(self.corridor.state("agententity:test:fresh"), S.REVOKED)

    def test_revoked_proof_restricts(self):
        self.certified()
        self.corridor.approve_production(AGENT, human_approval_ref="human:approval:0001")
        self.graph.revoke(f"proof:ProofOfExecution:{AGENT}", "receipt forged")
        self.assertEqual(self.corridor.state(AGENT), S.RESTRICTED)
        self.assertIn("receipt forged", self.corridor.status(AGENT)["history"][-1]["reason"])

    def test_disputed_proof_restricts(self):
        self.certified()
        self.graph.dispute(f"proof:ProofOfQuote:{AGENT}", "quote mismatch")
        self.assertEqual(self.corridor.state(AGENT), S.RESTRICTED)

    def test_disputed_non_required_proof_does_not_restrict(self):
        self.certified()
        env = envelope("ProofOfOutcome")
        self.graph.add_proof(env, sign(env))
        self.graph.dispute(env["proof_id"], "late")
        self.assertEqual(self.corridor.state(AGENT), S.CERTIFIED)

    def test_status_validates_against_schema(self):
        self.certified()
        self.corridor.approve_production(AGENT, aegis_decision_ref="aegis:decision:0001")
        self.corridor.restrict(AGENT, "re-cert")
        status = self.corridor.status(AGENT)
        STATE_VALIDATOR.validate(status)
        self.assertEqual([h["to_state"] for h in status["history"]],
                         ["CANDIDATE", "CERTIFIED", "PRODUCTION_APPROVED", "RESTRICTED"])
        STATE_VALIDATOR.validate(self.corridor.status("agententity:test:unknown"))


class CertificationStateSchemaTests(unittest.TestCase):
    def base(self):
        return {"agent_entity_ref": "a", "state": "CERTIFIED", "history": [],
                "grants_authority": False, "reputation_is_authority": False}

    def test_grants_authority_true_rejected(self):
        self.assertFalse(STATE_VALIDATOR.is_valid(dict(self.base(), grants_authority=True)))

    def test_unknown_state_rejected(self):
        self.assertFalse(STATE_VALIDATOR.is_valid(dict(self.base(), state="LIVE")))

    def test_additional_properties_rejected(self):
        self.assertFalse(STATE_VALIDATOR.is_valid(dict(self.base(), wallet_power="raw")))

    def test_production_history_entry_needs_approval_ref(self):
        entry = {"from_state": "CERTIFIED", "to_state": "PRODUCTION_APPROVED", "at": "2026-09-18T00:00:00Z"}
        self.assertFalse(STATE_VALIDATOR.is_valid(dict(self.base(), history=[entry])))
        self.assertTrue(STATE_VALIDATOR.is_valid(dict(self.base(), history=[dict(entry, human_approval_ref="h:1")])))


if __name__ == "__main__":
    unittest.main()
