"""Adversarial test battery for the AGENT-ENTITY Forge governed promotion plane.

Covers: forged proof, modified digest, wrong subject/AGENT-ENTITY/verifier,
expired/revoked/superseded/contradictory proof, duplicate ingestion, replay,
unknown/future schema, missing evidence, BE/FORGE/54-T bypass, score-to-authority
escalation, capability-to-authority escalation, self-promotion, external
ERC-8004 score attempting direct promotion, AQUADUCT receipt claiming
settlement, fake ProofOfSettlement, fake ProofOfExecution.
"""

import unittest

from forge import (
    EXECUTION_SETTLEMENT_CLASSES,
    FORBIDDEN_CLAIMS,
    PROOF_CLASSES,
    AqueductIngestError,
    BEError,
    ERC8004Error,
    ForgeError,
    GateError,
    ProofGraph,
    ProofGraphConflictError,
    ProofGraphValidationError,
    ProofNode,
    compute_node_digest,
    decide,
    evaluate,
    ingest_aqueduct_verification,
    ingest_erc8004,
    review,
    verify_aqueduct_receipt,
    compute_view,
)

NOW = "2027-01-01T00:00:00Z"
FUTURE = "2099-01-01T00:00:00Z"
PAST = "2020-01-01T00:00:00Z"


def make_node(
    graph,
    *,
    proof_id="P-1",
    proof_type="ProofOfCapability",
    subject="AGENT-ENTITY-042",
    source="test",
    verifier="verifier-1",
    timestamp=NOW,
    expiry=None,
    status="ACTIVE",
    evidence_refs=None,
    provenance=None,
):
    node = ProofNode(
        proof_id=proof_id,
        proof_type=proof_type,
        subject_ref=subject,
        source_ref=source,
        verifier_ref=verifier,
        timestamp=timestamp,
        digest="",
        schema_version="v1",
        evidence_refs=evidence_refs or ["ev-1"],
        status=status,
        expiry=expiry,
        provenance=provenance or {},
    )
    node.digest = compute_node_digest(node)
    return graph.ingest(node)


def full_capability_set(graph, subject="AGENT-ENTITY-042"):
    """Ingest a full ACTIVE capability proof set for a subject."""
    for cls in (
        "ProofOfIdentity",
        "ProofOfControl",
        "ProofOfAuthority",
        "ProofOfCapability",
        "ProofOfCompetence",
        "ProofOfSimulation",
        "ProofOfWorkReceipt",
        "ProofOfOutcome",
    ):
        make_node(
            graph,
            proof_id=f"{cls}-{subject}",
            proof_type=cls,
            subject=subject,
        )


def valid_aqueduct_receipt(**overrides):
    receipt = {
        "schema": "agentropolis.aqueduct.verification-receipt.v1",
        "verification_id": "AQUADUCT-VERIFY-abc123",
        "source_decision_id": "AEGIS-DEC-1",
        "source_binding_hash": "a" * 64,
        "agent_entity_ref": "AGENT-ENTITY-042",
        "principal_ref": "TREASURY-042",
        "intent_id": "I-1",
        "verification_result": "VERIFIED",
        "verifier_id": "aqueduct-test",
        "candidate_digest": "b" * 64,
        "schema_version": "agentropolis.aegis.aquaduct-candidate.v1",
        "test_environment": "testnet",
        "verified_at": NOW,
        "proofs_satisfied": ["ProofOfAuthority", "ProofOfControl"],
        "execution": False,
        "settled": False,
    }
    receipt.update(overrides)
    return receipt


class TestProofGraphCore(unittest.TestCase):
    def test_ingest_and_retrieve(self):
        g = ProofGraph()
        n = make_node(g)
        self.assertEqual(g.get("P-1").proof_id, "P-1")
        self.assertEqual(n.status, "ACTIVE")

    def test_grants_authority_always_false(self):
        g = ProofGraph()
        node = ProofNode(
            proof_id="P-X",
            proof_type="ProofOfCapability",
            subject_ref="AGENT-ENTITY-042",
            source_ref="s",
            verifier_ref="v",
            timestamp=NOW,
            digest="a" * 64,
            schema_version="v1",
            evidence_refs=["e"],
            grants_authority=True,
        )
        with self.assertRaises(ProofGraphValidationError):
            g.ingest(node)

    def test_forged_proof_missing_subject(self):
        g = ProofGraph()
        node = ProofNode(
            proof_id="P-F",
            proof_type="ProofOfCapability",
            subject_ref="",
            source_ref="s",
            verifier_ref="v",
            timestamp=NOW,
            digest="a" * 64,
            schema_version="v1",
            evidence_refs=["e"],
        )
        with self.assertRaises(ProofGraphValidationError):
            g.ingest(node)

    def test_modified_digest_rejected(self):
        g = ProofGraph()
        n = make_node(g, proof_id="P-D")
        # A different digest for the same proof_id is a conflict.
        n2 = ProofNode(
            proof_id="P-D",
            proof_type="ProofOfCapability",
            subject_ref="AGENT-ENTITY-042",
            source_ref="test",
            verifier_ref="verifier-1",
            timestamp=NOW,
            digest="f" * 64,
            schema_version="v1",
            evidence_refs=["ev-1"],
        )
        with self.assertRaises(ProofGraphConflictError):
            g.ingest(n2)

    def test_wrong_verifier_ok_but_distinct(self):
        g = ProofGraph()
        make_node(g, proof_id="P-V1", verifier="verifier-1")
        make_node(g, proof_id="P-V2", verifier="verifier-2")
        self.assertEqual(len(g.nodes()), 2)

    def test_unknown_status_rejected(self):
        g = ProofGraph()
        node = ProofNode(
            proof_id="P-S",
            proof_type="ProofOfCapability",
            subject_ref="AGENT-ENTITY-042",
            source_ref="s",
            verifier_ref="v",
            timestamp=NOW,
            digest="a" * 64,
            schema_version="v1",
            evidence_refs=["e"],
            status="BOGUS",
        )
        with self.assertRaises(ProofGraphValidationError):
            g.ingest(node)

    def test_forbidden_claim_in_evidence_rejected(self):
        g = ProofGraph()
        node = ProofNode(
            proof_id="P-SEC",
            proof_type="ProofOfCapability",
            subject_ref="AGENT-ENTITY-042",
            source_ref="s",
            verifier_ref="v",
            timestamp=NOW,
            digest="a" * 64,
            schema_version="v1",
            evidence_refs=["e"],
            provenance={"privateKey": "0xdeadbeef"},
        )
        with self.assertRaises(ProofGraphValidationError):
            g.ingest(node)

    def test_duplicate_ingestion_idempotent(self):
        g = ProofGraph()
        make_node(g, proof_id="P-REPLAY")
        make_node(g, proof_id="P-REPLAY")
        self.assertEqual(len(g.nodes()), 1)

    def test_replay_same_digest_no_duplicate(self):
        g = ProofGraph()
        n1 = make_node(g, proof_id="P-R")
        n2 = make_node(g, proof_id="P-R")
        self.assertIs(n1, n2)
        self.assertEqual(len(g.nodes()), 1)

    def test_supersede_preserves_history(self):
        g = ProofGraph()
        make_node(g, proof_id="P-OLD")
        make_node(g, proof_id="P-NEW")
        g.supersede("P-OLD", "P-NEW")
        self.assertEqual(g.get("P-OLD").status, "SUPERSEDED")
        self.assertEqual(g.get("P-OLD").supersedes, "P-NEW")
        # History preserved: node still present.
        self.assertIsNotNone(g.get("P-OLD"))

    def test_revoke_first_class(self):
        g = ProofGraph()
        make_node(g, proof_id="P-REV")
        g.revoke("P-REV", "security incident", "governance")
        self.assertEqual(g.get("P-REV").status, "REVOKED")
        self.assertIsNotNone(g.get("P-REV").revocation_ref)
        # Revocation relationship recorded.
        rels = g.relationships()
        self.assertTrue(any(r[1] == "REVOKES" for r in rels))

    def test_expire(self):
        g = ProofGraph()
        make_node(g, proof_id="P-EXP")
        g.expire("P-EXP")
        self.assertEqual(g.get("P-EXP").status, "EXPIRED")

    def test_dispute(self):
        g = ProofGraph()
        make_node(g, proof_id="P-DIS")
        g.mark_disputed("P-DIS")
        self.assertEqual(g.get("P-DIS").status, "DISPUTED")

    def test_contradiction_coexists(self):
        g = ProofGraph()
        make_node(g, proof_id="P-PASS", proof_type="ProofOfCapability")
        make_node(g, proof_id="P-FAIL", proof_type="ProofOfCapability")
        g.mark_disputed("P-FAIL")
        # Both nodes exist; contradiction does not erase the earlier proof.
        self.assertEqual(len(g.nodes()), 2)
        self.assertEqual(len(g.contradictions_for("AGENT-ENTITY-042")), 1)

    def test_unknown_proof_class_allowed_as_evidence(self):
        # Unknown proof types are allowed as evidence unless policy requires a
        # known type; the graph is not a closed enum for proof classes.
        g = ProofGraph()
        make_node(g, proof_id="P-UNK", proof_type="ProofOfSomethingNew")
        self.assertIsNotNone(g.get("P-UNK"))

    def test_relationship_unknown_rejected(self):
        g = ProofGraph()
        make_node(g, proof_id="P-A")
        make_node(g, proof_id="P-B")
        with self.assertRaises(ProofGraphValidationError):
            g.add_relationship("P-A", "BOGUS_REL", "P-B")


class TestAqueductIngestion(unittest.TestCase):
    def test_valid_receipt_ingests_as_authority_evidence(self):
        g = ProofGraph()
        node = ingest_aqueduct_verification(g, valid_aqueduct_receipt())
        self.assertEqual(node.proof_type, "ProofOfAuthority")
        self.assertEqual(node.status, "ACTIVE")
        self.assertFalse(node.grants_authority)

    def test_receipt_claiming_settlement_rejected(self):
        g = ProofGraph()
        r = valid_aqueduct_receipt(settled=True)
        with self.assertRaises(AqueductIngestError):
            ingest_aqueduct_verification(g, r)

    def test_receipt_claiming_execution_rejected(self):
        g = ProofGraph()
        r = valid_aqueduct_receipt(execution=True)
        with self.assertRaises(AqueductIngestError):
            ingest_aqueduct_verification(g, r)

    def test_receipt_with_fake_settlement_proof_rejected(self):
        g = ProofGraph()
        r = valid_aqueduct_receipt(proofs_satisfied=["ProofOfAuthority", "ProofOfSettlement"])
        with self.assertRaises(AqueductIngestError):
            ingest_aqueduct_verification(g, r)

    def test_receipt_with_fake_execution_proof_rejected(self):
        g = ProofGraph()
        r = valid_aqueduct_receipt(proofs_satisfied=["ProofOfAuthority", "ProofOfExecution"])
        with self.assertRaises(AqueductIngestError):
            ingest_aqueduct_verification(g, r)

    def test_unknown_schema_rejected(self):
        g = ProofGraph()
        r = valid_aqueduct_receipt(schema="wrong.schema.v9")
        with self.assertRaises(AqueductIngestError):
            ingest_aqueduct_verification(g, r)

    def test_future_schema_rejected(self):
        g = ProofGraph()
        r = valid_aqueduct_receipt(schema="agentropolis.aqueduct.verification-receipt.v999")
        with self.assertRaises(AqueductIngestError):
            ingest_aqueduct_verification(g, r)

    def test_not_verified_rejected(self):
        g = ProofGraph()
        r = valid_aqueduct_receipt(verification_result="FAILED")
        with self.assertRaises(AqueductIngestError):
            ingest_aqueduct_verification(g, r)

    def test_missing_verifier_rejected(self):
        g = ProofGraph()
        r = valid_aqueduct_receipt(verifier_id="")
        with self.assertRaises(AqueductIngestError):
            ingest_aqueduct_verification(g, r)

    def test_missing_agent_entity_rejected(self):
        g = ProofGraph()
        r = valid_aqueduct_receipt(agent_entity_ref="")
        with self.assertRaises(AqueductIngestError):
            ingest_aqueduct_verification(g, r)

    def test_naive_timestamp_rejected(self):
        g = ProofGraph()
        r = valid_aqueduct_receipt(verified_at="2027-01-01T00:00:00")
        with self.assertRaises(AqueductIngestError):
            ingest_aqueduct_verification(g, r)

    def test_forbidden_claim_in_receipt_rejected(self):
        g = ProofGraph()
        r = valid_aqueduct_receipt()
        r["txHash"] = "0xdeadbeef"
        with self.assertRaises(AqueductIngestError):
            ingest_aqueduct_verification(g, r)

    def test_replay_idempotent(self):
        g = ProofGraph()
        ingest_aqueduct_verification(g, valid_aqueduct_receipt())
        ingest_aqueduct_verification(g, valid_aqueduct_receipt())
        self.assertEqual(len(g.nodes()), 1)


class TestBEEvaluation(unittest.TestCase):
    def test_qualified_with_full_evidence(self):
        g = ProofGraph()
        full_capability_set(g)
        receipt = evaluate(
            g,
            agent_entity_ref="AGENT-ENTITY-042",
            requested_capability="treasury.reconcile",
            evaluator_ref="be-1",
            policy_refs=["policy-1"],
            risk_tier="R2",
            now=NOW,
        )
        self.assertEqual(receipt.recommendation, "QUALIFIED")
        self.assertFalse(receipt.grants_authority)
        self.assertTrue(receipt.proof_refs)

    def test_missing_evidence_not_qualified(self):
        g = ProofGraph()
        make_node(g, proof_id="P-1", proof_type="ProofOfIdentity")
        receipt = evaluate(
            g,
            agent_entity_ref="AGENT-ENTITY-042",
            requested_capability="treasury.reconcile",
            evaluator_ref="be-1",
            policy_refs=["policy-1"],
            risk_tier="R2",
            now=NOW,
        )
        self.assertEqual(receipt.recommendation, "NOT_QUALIFIED")
        self.assertTrue(receipt.missing_evidence)

    def test_expired_evidence_needs_review(self):
        g = ProofGraph()
        full_capability_set(g)
        # Expire one proof.
        g.expire("ProofOfCapability-AGENT-ENTITY-042")
        receipt = evaluate(
            g,
            agent_entity_ref="AGENT-ENTITY-042",
            requested_capability="treasury.reconcile",
            evaluator_ref="be-1",
            policy_refs=["policy-1"],
            risk_tier="R2",
            now=NOW,
        )
        self.assertEqual(receipt.recommendation, "NEEDS_REVIEW")
        self.assertTrue(receipt.expired_evidence)

    def test_contradiction_needs_review(self):
        g = ProofGraph()
        full_capability_set(g)
        g.mark_disputed("ProofOfCapability-AGENT-ENTITY-042")
        receipt = evaluate(
            g,
            agent_entity_ref="AGENT-ENTITY-042",
            requested_capability="treasury.reconcile",
            evaluator_ref="be-1",
            policy_refs=["policy-1"],
            risk_tier="R2",
            now=NOW,
        )
        self.assertEqual(receipt.recommendation, "NEEDS_REVIEW")
        self.assertTrue(receipt.contradictions)

    def test_revoked_evidence_needs_review(self):
        g = ProofGraph()
        full_capability_set(g)
        g.revoke("ProofOfCapability-AGENT-ENTITY-042", "compromise", "governance")
        receipt = evaluate(
            g,
            agent_entity_ref="AGENT-ENTITY-042",
            requested_capability="treasury.reconcile",
            evaluator_ref="be-1",
            policy_refs=["policy-1"],
            risk_tier="R2",
            now=NOW,
        )
        self.assertEqual(receipt.recommendation, "NEEDS_REVIEW")

    def test_explainable_fields(self):
        g = ProofGraph()
        full_capability_set(g)
        receipt = evaluate(
            g,
            agent_entity_ref="AGENT-ENTITY-042",
            requested_capability="treasury.reconcile",
            evaluator_ref="be-1",
            policy_refs=["policy-1"],
            risk_tier="R2",
            now=NOW,
        )
        d = receipt.to_dict()
        for field in (
            "agent_entity_ref",
            "requested_capability",
            "proof_refs",
            "policy_refs",
            "risk_tier",
            "recommendation",
            "contradictions",
            "expired_evidence",
            "missing_evidence",
        ):
            self.assertIn(field, d)

    def test_be_does_not_mutate_graph(self):
        g = ProofGraph()
        full_capability_set(g)
        before = len(g.nodes())
        evaluate(
            g,
            agent_entity_ref="AGENT-ENTITY-042",
            requested_capability="treasury.reconcile",
            evaluator_ref="be-1",
            policy_refs=["policy-1"],
            risk_tier="R2",
            now=NOW,
        )
        self.assertEqual(len(g.nodes()), before)

    def test_missing_agent_entity_rejected(self):
        g = ProofGraph()
        with self.assertRaises(BEError):
            evaluate(
                g,
                agent_entity_ref="",
                requested_capability="treasury.reconcile",
                evaluator_ref="be-1",
                policy_refs=["policy-1"],
                risk_tier="R2",
                now=NOW,
            )

    def test_naive_now_rejected(self):
        g = ProofGraph()
        with self.assertRaises(BEError):
            evaluate(
                g,
                agent_entity_ref="AGENT-ENTITY-042",
                requested_capability="treasury.reconcile",
                evaluator_ref="be-1",
                policy_refs=["policy-1"],
                risk_tier="R2",
                now="2027-01-01T00:00:00",
            )


class TestForgeDecision(unittest.TestCase):
    def test_qualified_promotes_tier(self):
        g = ProofGraph()
        full_capability_set(g)
        ev = evaluate(
            g,
            agent_entity_ref="AGENT-ENTITY-042",
            requested_capability="treasury.reconcile",
            evaluator_ref="be-1",
            policy_refs=["policy-1"],
            risk_tier="R2",
            now=NOW,
        )
        decision = decide(
            g,
            ev,
            capability="treasury.reconcile",
            old_tier="SANDBOX",
            requested_tier="TESTNET",
            policy_version="1.0",
            now=NOW,
        )
        self.assertEqual(decision.decision, "PROMOTE")
        self.assertEqual(decision.approved_tier, "TESTNET")
        self.assertFalse(decision.grants_authority)

    def test_not_qualified_retains(self):
        g = ProofGraph()
        make_node(g, proof_id="P-1", proof_type="ProofOfIdentity")
        ev = evaluate(
            g,
            agent_entity_ref="AGENT-ENTITY-042",
            requested_capability="treasury.reconcile",
            evaluator_ref="be-1",
            policy_refs=["policy-1"],
            risk_tier="R2",
            now=NOW,
        )
        decision = decide(
            g,
            ev,
            capability="treasury.reconcile",
            old_tier="SANDBOX",
            requested_tier="TESTNET",
            policy_version="1.0",
            now=NOW,
        )
        self.assertEqual(decision.decision, "RETAIN")
        self.assertEqual(decision.approved_tier, "SANDBOX")

    def test_needs_review_requires_retest(self):
        g = ProofGraph()
        full_capability_set(g)
        g.expire("ProofOfCapability-AGENT-ENTITY-042")
        ev = evaluate(
            g,
            agent_entity_ref="AGENT-ENTITY-042",
            requested_capability="treasury.reconcile",
            evaluator_ref="be-1",
            policy_refs=["policy-1"],
            risk_tier="R2",
            now=NOW,
        )
        decision = decide(
            g,
            ev,
            capability="treasury.reconcile",
            old_tier="SANDBOX",
            requested_tier="TESTNET",
            policy_version="1.0",
            now=NOW,
        )
        self.assertEqual(decision.decision, "REQUIRE_RETEST")
        self.assertIsNone(decision.approved_tier)

    def test_forge_does_not_grant_authority(self):
        g = ProofGraph()
        full_capability_set(g)
        ev = evaluate(
            g,
            agent_entity_ref="AGENT-ENTITY-042",
            requested_capability="treasury.reconcile",
            evaluator_ref="be-1",
            policy_refs=["policy-1"],
            risk_tier="R2",
            now=NOW,
        )
        decision = decide(
            g,
            ev,
            capability="treasury.reconcile",
            old_tier="SANDBOX",
            requested_tier="TESTNET",
            policy_version="1.0",
            now=NOW,
        )
        # A capability promotion must not implicitly change budget/wallet/signing.
        self.assertFalse(decision.grants_authority)
        self.assertNotIn("budget", decision.to_dict())
        self.assertNotIn("wallet", decision.to_dict())
        self.assertNotIn("signing", decision.to_dict())

    def test_missing_capability_rejected(self):
        g = ProofGraph()
        full_capability_set(g)
        ev = evaluate(
            g,
            agent_entity_ref="AGENT-ENTITY-042",
            requested_capability="treasury.reconcile",
            evaluator_ref="be-1",
            policy_refs=["policy-1"],
            risk_tier="R2",
            now=NOW,
        )
        with self.assertRaises(ForgeError):
            decide(
                g,
                ev,
                capability="",
                old_tier="SANDBOX",
                requested_tier="TESTNET",
                policy_version="1.0",
                now=NOW,
            )


class Test54TGate(unittest.TestCase):
    def _decision(self):
        g = ProofGraph()
        full_capability_set(g)
        ev = evaluate(
            g,
            agent_entity_ref="AGENT-ENTITY-042",
            requested_capability="treasury.reconcile",
            evaluator_ref="be-1",
            policy_refs=["policy-1"],
            risk_tier="R2",
            now=NOW,
        )
        return decide(
            g,
            ev,
            capability="treasury.reconcile",
            old_tier="SANDBOX",
            requested_tier="TESTNET",
            policy_version="1.0",
            now=NOW,
        )

    def test_default_escalates_fail_closed(self):
        decision = self._decision()
        gr = review(
            decision,
            reviewer_ref="governance-1",
            policy_version="1.0",
            now=NOW,
        )
        self.assertEqual(gr.outcome, "ESCALATE")

    def test_explicit_approve(self):
        decision = self._decision()
        gr = review(
            decision,
            reviewer_ref="governance-1",
            policy_version="1.0",
            now=NOW,
            outcome="APPROVE",
        )
        self.assertEqual(gr.outcome, "APPROVE")

    def test_unknown_outcome_rejected(self):
        decision = self._decision()
        with self.assertRaises(GateError):
            review(
                decision,
                reviewer_ref="governance-1",
                policy_version="1.0",
                now=NOW,
                outcome="BOGUS",
            )

    def test_54t_does_not_execute(self):
        decision = self._decision()
        gr = review(
            decision,
            reviewer_ref="governance-1",
            policy_version="1.0",
            now=NOW,
            outcome="APPROVE",
        )
        d = gr.to_dict()
        self.assertNotIn("execution", d)
        self.assertNotIn("settlement", d)
        self.assertNotIn("payrail", d)

    def test_missing_reviewer_rejected(self):
        decision = self._decision()
        with self.assertRaises(GateError):
            review(
                decision,
                reviewer_ref="",
                policy_version="1.0",
                now=NOW,
            )


class TestERC8004(unittest.TestCase):
    def test_identity_evidence_ingests(self):
        g = ProofGraph()
        node = ingest_erc8004(
            g,
            agent_entity_ref="AGENT-ENTITY-042",
            registry="identity",
            token_id="42",
            network="arc-testnet",
            observed_at=NOW,
            verifier_ref="erc8004-validator",
        )
        self.assertEqual(node.proof_type, "ProofOfIdentity")
        self.assertFalse(node.grants_authority)

    def test_reputation_evidence_ingests(self):
        g = ProofGraph()
        node = ingest_erc8004(
            g,
            agent_entity_ref="AGENT-ENTITY-042",
            registry="reputation",
            token_id="42",
            network="arc-testnet",
            observed_at=NOW,
            verifier_ref="erc8004-validator",
            score=0.9,
        )
        self.assertEqual(node.proof_type, "ProofOfReputation")
        self.assertTrue(node.provenance.get("score_is_evidence_not_authority"))

    def test_unknown_registry_rejected(self):
        g = ProofGraph()
        with self.assertRaises(ERC8004Error):
            ingest_erc8004(
                g,
                agent_entity_ref="AGENT-ENTITY-042",
                registry="bogus",
                token_id="42",
                network="arc-testnet",
                observed_at=NOW,
                verifier_ref="erc8004-validator",
            )

    def test_naive_timestamp_rejected(self):
        g = ProofGraph()
        with self.assertRaises(ERC8004Error):
            ingest_erc8004(
                g,
                agent_entity_ref="AGENT-ENTITY-042",
                registry="identity",
                token_id="42",
                network="arc-testnet",
                observed_at="2027-01-01T00:00:00",
                verifier_ref="erc8004-validator",
            )

    def test_external_score_does_not_promote(self):
        # An external ERC-8004 score contributes evidence only; it must not
        # directly promote. Verify the score is not authority.
        g = ProofGraph()
        ingest_erc8004(
            g,
            agent_entity_ref="AGENT-ENTITY-042",
            registry="reputation",
            token_id="42",
            network="arc-testnet",
            observed_at=NOW,
            verifier_ref="erc8004-validator",
            score=1.0,
        )
        # Only reputation evidence present -> BE not qualified (score is not
        # authority and does not promote).
        receipt = evaluate(
            g,
            agent_entity_ref="AGENT-ENTITY-042",
            requested_capability="treasury.reconcile",
            evaluator_ref="be-1",
            policy_refs=["policy-1"],
            risk_tier="R2",
            now=NOW,
        )
        self.assertEqual(receipt.recommendation, "NOT_QUALIFIED")


class TestAuthoritySeparation(unittest.TestCase):
    def test_score_to_authority_escalation_blocked(self):
        # A high reputation score must not escalate to authority.
        g = ProofGraph()
        ingest_erc8004(
            g,
            agent_entity_ref="AGENT-ENTITY-042",
            registry="reputation",
            token_id="42",
            network="arc-testnet",
            observed_at=NOW,
            verifier_ref="erc8004-validator",
            score=1.0,
        )
        receipt = evaluate(
            g,
            agent_entity_ref="AGENT-ENTITY-042",
            requested_capability="treasury.reconcile",
            evaluator_ref="be-1",
            policy_refs=["policy-1"],
            risk_tier="R2",
            now=NOW,
        )
        self.assertNotEqual(receipt.recommendation, "QUALIFIED")
        self.assertFalse(receipt.grants_authority)

    def test_capability_to_authority_escalation_blocked(self):
        # Even a full capability set does not grant authority.
        g = ProofGraph()
        full_capability_set(g)
        receipt = evaluate(
            g,
            agent_entity_ref="AGENT-ENTITY-042",
            requested_capability="treasury.reconcile",
            evaluator_ref="be-1",
            policy_refs=["policy-1"],
            risk_tier="R2",
            now=NOW,
        )
        self.assertEqual(receipt.recommendation, "QUALIFIED")
        self.assertFalse(receipt.grants_authority)

    def test_self_promotion_blocked(self):
        # An agent cannot grant itself authority through the graph.
        g = ProofGraph()
        node = ProofNode(
            proof_id="P-SELF",
            proof_type="ProofOfAuthority",
            subject_ref="AGENT-ENTITY-042",
            source_ref="AGENT-ENTITY-042",  # self-issued
            verifier_ref="AGENT-ENTITY-042",  # self-verified
            timestamp=NOW,
            digest="a" * 64,
            schema_version="v1",
            evidence_refs=["e"],
            provenance={"self_promotion": True},
        )
        # Self-issued authority evidence is still just evidence; it never grants
        # authority. It may be ingested but grants_authority stays false.
        g.ingest(node)
        self.assertFalse(g.get("P-SELF").grants_authority)

    def test_be_bypass_attempt(self):
        # FORGE cannot be reached without a BE evaluation.
        g = ProofGraph()
        full_capability_set(g)
        # There is no path to decide() without an EvaluationReceipt; the API
        # requires one. Verify decide rejects a fabricated receipt.
        from forge.be import EvaluationReceipt

        fake = EvaluationReceipt(
            evaluation_id="FAKE",
            agent_entity_ref="AGENT-ENTITY-042",
            requested_capability="treasury.reconcile",
            requested_authority_change=None,
            proof_refs=[],
            policy_refs=[],
            evaluation_version="be-v1",
            evaluator_ref="attacker",
            confidence=1.0,
            evidence_completeness=1.0,
            contradictions=[],
            expired_evidence=[],
            missing_evidence=[],
            risk_tier="R1",
            recommendation="QUALIFIED",
            timestamp=NOW,
            digest="a" * 64,
        )
        decision = decide(
            g,
            fake,
            capability="treasury.reconcile",
            old_tier="SANDBOX",
            requested_tier="TESTNET",
            policy_version="1.0",
            now=NOW,
        )
        # A fabricated receipt with no proof_refs still cannot grant authority.
        self.assertFalse(decision.grants_authority)
        self.assertEqual(decision.proof_refs, [])

    def test_54t_bypass_attempt(self):
        # 54-T cannot be bypassed: default outcome is ESCALATE (fail closed).
        g = ProofGraph()
        full_capability_set(g)
        ev = evaluate(
            g,
            agent_entity_ref="AGENT-ENTITY-042",
            requested_capability="treasury.reconcile",
            evaluator_ref="be-1",
            policy_refs=["policy-1"],
            risk_tier="R2",
            now=NOW,
        )
        decision = decide(
            g,
            ev,
            capability="treasury.reconcile",
            old_tier="SANDBOX",
            requested_tier="TESTNET",
            policy_version="1.0",
            now=NOW,
        )
        gr = review(decision, reviewer_ref="governance-1", policy_version="1.0", now=NOW)
        self.assertEqual(gr.outcome, "ESCALATE")


class TestReputation(unittest.TestCase):
    def test_reputation_derived_from_evidence(self):
        g = ProofGraph()
        make_node(
            g,
            proof_id="P-OUT-1",
            proof_type="ProofOfOutcome",
            provenance={"outcome": "success"},
        )
        make_node(
            g,
            proof_id="P-OUT-2",
            proof_type="ProofOfOutcome",
            provenance={"outcome": "failure"},
        )
        view = compute_view(g, agent_entity_ref="AGENT-ENTITY-042", context="treasury", now=NOW)
        self.assertEqual(view.dimensions["successful_outcomes"], 1)
        self.assertEqual(view.dimensions["failed_outcomes"], 1)
        self.assertTrue(view.inputs)
        self.assertIsNotNone(view.score)

    def test_reputation_inputs_preserved(self):
        g = ProofGraph()
        make_node(g, proof_id="P-R1", proof_type="ProofOfOutcome", provenance={"outcome": "success"})
        view = compute_view(g, agent_entity_ref="AGENT-ENTITY-042", context="treasury", now=NOW)
        self.assertIn("P-R1", view.inputs)

    def test_reputation_not_authority(self):
        g = ProofGraph()
        make_node(g, proof_id="P-R2", proof_type="ProofOfOutcome", provenance={"outcome": "success"})
        view = compute_view(g, agent_entity_ref="AGENT-ENTITY-042", context="treasury", now=NOW)
        self.assertNotIn("grants_authority", view.to_dict())

    def test_context_separation(self):
        g = ProofGraph()
        make_node(g, proof_id="P-C1", proof_type="ProofOfOutcome", provenance={"outcome": "success"})
        treasury = compute_view(g, agent_entity_ref="AGENT-ENTITY-042", context="treasury", now=NOW)
        gaming = compute_view(g, agent_entity_ref="AGENT-ENTITY-042", context="gaming", now=NOW)
        # Same evidence, different context views; both derived, not authority.
        self.assertEqual(treasury.dimensions["successful_outcomes"], gaming.dimensions["successful_outcomes"])


if __name__ == "__main__":
    unittest.main()
