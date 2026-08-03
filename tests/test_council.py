import sys
import asyncio
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from salescout.council import ACCOUNT_SCENARIOS, CouncilRequest, Decision, decide, execute
from mcp_server import server


class RevenueCouncilTests(unittest.TestCase):
    def test_ten_accounts_produce_grounded_draft_only_records(self):
        self.assertEqual(10, len(ACCOUNT_SCENARIOS))
        for scenario in ACCOUNT_SCENARIOS:
            record = execute(CouncilRequest(scenario=scenario, idempotency_key=f"golden-{scenario}-0001"))
            evidence_ids = {item.evidence_id for item in record.evidence}
            for claim in record.outputs["strategy"]["grounded_claims"]:
                self.assertTrue(set(claim["evidence_ids"]) <= evidence_ids)
            for draft in record.outputs["drafts"]:
                self.assertTrue(set(draft["grounded_claim_ids"]) <= evidence_ids)
                self.assertEqual("draft_only", draft["send_status"])
            self.assertEqual(0, record.outputs["emails_sent"])
            self.assertEqual(0, record.outputs["crm_writes"])

    def test_low_fit_account_is_not_recommended(self):
        record = execute(CouncilRequest(scenario="low_fit", idempotency_key="low-fit-test-0001"))
        self.assertFalse(record.outputs["analysis"]["qualified"])
        self.assertIn("Do not pursue", record.outputs["strategy"]["recommended_angle"])

    def test_approval_remains_manual(self):
        record = execute(CouncilRequest(scenario="saas_growth", idempotency_key="approval-test-0001"))
        updated = decide(record.run_id, Decision(decision="approve", actor="Account owner", reason="Evidence reviewed"))
        self.assertEqual("approved_for_manual_use", updated.status)
        self.assertEqual(0, updated.outputs["emails_sent"])
        self.assertEqual(0, updated.outputs["crm_writes"])

    def test_mcp_exposes_only_read_only_tools(self):
        tools = asyncio.run(server.list_tools())
        self.assertEqual({"get_capabilities", "analyze_account", "read_run"}, {tool.name for tool in tools})
        self.assertNotIn("send_email", {tool.name for tool in tools})
        self.assertNotIn("write_crm", {tool.name for tool in tools})


if __name__ == "__main__":
    unittest.main()
