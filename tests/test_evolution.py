import hashlib
import unittest
from evolution.engine import project

def event(i, kind="task_completed", **changes):
    e = dict(event_id=str(i), entity_id="AE-1", occurred_at="2026-10-31T00:00:00Z",
             event_type=kind, domain="research", claim="proof", evidence_refs=["receipt:"+str(i)],
             evidence_hashes=[hashlib.sha256(str(i).encode()).hexdigest()],
             issuer_id="issuer", verifier_id="auditor", verification_status="verified",
             confidence="0.9", mandate_ref="M-1", policy_version="v0.1",
             appeal_status="none", created_at="2026-10-31T00:00:00Z")
    e.update(changes)
    return e

class EvolutionTests(unittest.TestCase):
    def test_verified(self):
        self.assertEqual(len(project([event(1)], "AE-1", "research")["accepted_event_ids"]), 1)
    def test_unverified(self):
        self.assertEqual(len(project([event(1, verification_status="pending")], "AE-1", "research")["accepted_event_ids"]), 0)
    def test_duplicate_event(self):
        self.assertEqual(len(project([event(1), event(1)], "AE-1", "research")["accepted_event_ids"]), 1)
    def test_duplicate_evidence(self):
        a = event(1)
        b = event(2, evidence_hashes=a["evidence_hashes"])
        self.assertEqual(len(project([a,b], "AE-1", "research")["accepted_event_ids"]), 1)
    def test_self_verification(self):
        self.assertEqual(len(project([event(1, verifier_id="issuer")], "AE-1", "research")["accepted_event_ids"]), 0)
    def test_disputed(self):
        self.assertEqual(len(project([event(1, appeal_status="pending")], "AE-1", "research")["accepted_event_ids"]), 0)
    def test_wrong_domain(self):
        self.assertEqual(len(project([event(1)], "AE-1", "finance")["accepted_event_ids"]), 0)
    def test_no_authority(self):
        self.assertFalse(project([event(1)], "AE-1", "research")["authority_changed"])
    def test_determinism(self):
        a,b=event(1),event(2)
        self.assertEqual(project([a,b],"AE-1","research"),project([b,a],"AE-1","research"))
    def test_revocation(self):
        self.assertEqual(project([event(1,"credential_revoked",claim="credential:X")],"AE-1","research")["revoked_claims"],["credential:X"])
    def test_no_soul_inference(self):
        self.assertEqual(project([event(1)],"AE-1","research")["consciousness_status"],"undetermined")

if __name__ == "__main__":
    unittest.main()
