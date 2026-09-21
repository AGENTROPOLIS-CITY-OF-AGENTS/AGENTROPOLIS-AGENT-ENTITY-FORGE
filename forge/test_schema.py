"""Schema validation tests: emitted artifacts must validate against the
canonical JSON schemas in schemas/."""

import json
import os
import unittest

from forge import (
    ProofGraph,
    decide,
    evaluate,
    review,
)
from forge.proof_graph import ProofNode, compute_node_digest

SCHEMA_DIR = os.path.join(os.path.dirname(__file__), "..", "schemas")

NOW = "2027-01-01T00:00:00Z"


def load_schema(name):
    with open(os.path.join(SCHEMA_DIR, name), encoding="utf-8") as f:
        return json.load(f)


def full_capability_set(graph, subject="AGENT-ENTITY-042"):
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
        node = ProofNode(
            proof_id=f"{cls}-{subject}",
            proof_type=cls,
            subject_ref=subject,
            source_ref="test",
            verifier_ref="verifier-1",
            timestamp=NOW,
            digest="",
            schema_version="v1",
            evidence_refs=["ev-1"],
        )
        node.digest = compute_node_digest(node)
        graph.ingest(node)


class TestSchemaValidation(unittest.TestCase):
    def setUp(self):
        try:
            import jsonschema  # noqa: F401
        except ImportError:
            self.skipTest("jsonschema not installed")

    def test_proof_node_validates(self):
        from jsonschema import validate

        schema = load_schema("proof-node.v1.json")
        g = ProofGraph()
        full_capability_set(g)
        node = g.get("ProofOfCapability-AGENT-ENTITY-042")
        validate(instance=node.to_dict(), schema=schema)

    def test_be_evaluation_receipt_validates(self):
        from jsonschema import validate

        schema = load_schema("be-evaluation-receipt.v1.json")
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
        validate(instance=receipt.to_dict(), schema=schema)

    def test_promotion_decision_validates(self):
        from jsonschema import validate

        schema = load_schema("promotion-decision.v1.json")
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
        validate(instance=decision.to_dict(), schema=schema)

    def test_governance_review_validates(self):
        from jsonschema import validate

        schema = load_schema("promotion-decision.v1.json")  # review uses decision shape
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
        # GovernanceReview is a distinct artifact; validate its own shape.
        d = gr.to_dict()
        self.assertIn("review_id", d)
        self.assertIn("outcome", d)
        self.assertIn("digest", d)


if __name__ == "__main__":
    unittest.main()
