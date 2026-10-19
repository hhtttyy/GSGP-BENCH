from __future__ import annotations

import json
import unittest
from pathlib import Path

import jsonschema

REPO = Path(__file__).resolve().parents[2]
SCHEMA = REPO / "benchmark" / "schema" / "result.v1.json"
RUN_RECORD = REPO / "benchmark" / "runs" / "gblup-sim500-mcp-v1" / "result.json"
DIRECT_RECORD = REPO / "benchmark" / "runs" / "gblup-sim500-v1" / "result.json"
SITE_RECORD = REPO / "site" / "data" / "results" / "gblup-sim500.json"
IFAM_STUB_RECORD = REPO / "benchmark" / "runs" / "ifam-stub-sim500-v1" / "result.json"
IFAM_STUB_SITE = REPO / "site" / "data" / "results" / "ifam-stub-sim500.json"
CERTIFICATION = REPO / "benchmark" / "algorithms" / "gblup" / "certification.json"


class GblupEvidenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
        self.record = json.loads(RUN_RECORD.read_text(encoding="utf-8"))

    def test_schema(self) -> None:
        jsonschema.validate(self.record, self.schema)

    def test_public_record_is_aggregate_only(self) -> None:
        self.assertNotIn("predictions", self.record)
        self.assertEqual(self.record["evidence"]["level"], "exploratory")
        self.assertFalse(self.record["evidence"]["certified"])
        self.assertTrue(self.record["evidence"]["single_split"])
        self.assertEqual(self.record["site"]["status"], "exploratory")

    def test_record_was_produced_through_mcp(self) -> None:
        self.assertEqual(self.record["mcp"]["transport"], "stdio")
        self.assertIn("gblup_fit", self.record["mcp"]["tools"])
        self.assertIn("via MCP", self.record["algorithm"]["implementation"])

    def test_site_copy_matches_evidence_record(self) -> None:
        self.assertEqual(
            json.loads(SITE_RECORD.read_text(encoding="utf-8")),
            self.record,
        )

    def test_mcp_matches_direct_baseline(self) -> None:
        direct = json.loads(DIRECT_RECORD.read_text(encoding="utf-8"))
        for key in ("pearson_r", "r2", "prediction_bias_slope"):
            self.assertAlmostEqual(self.record["metrics"][key], direct["metrics"][key], places=6)

    def test_metrics_are_present_and_finite(self) -> None:
        metrics = self.record["metrics"]
        self.assertGreater(metrics["pearson_r"], 0.0)
        self.assertGreater(metrics["r2"], 0.0)
        self.assertIsNone(metrics["auc"])

    def test_mcp_certification_is_simple_and_package_scoped(self) -> None:
        certification = json.loads(CERTIFICATION.read_text(encoding="utf-8"))
        self.assertEqual(certification["status"], "certified")
        self.assertTrue(certification["certified"])
        self.assertFalse(certification["hosted"])
        self.assertEqual(certification["scope"], "central-package-test")
        self.assertIn("not any benchmark result", " ".join(certification["boundaries"]).lower())

    def test_ifam_stub_is_labeled_and_not_scientific(self) -> None:
        record = json.loads(IFAM_STUB_RECORD.read_text(encoding="utf-8"))
        jsonschema.validate(record, self.schema)
        self.assertEqual(record["evidence"]["level"], "stub")
        self.assertFalse(record["evidence"]["certified"])
        self.assertEqual(record["mcp"]["server"], "ifam")
        self.assertEqual(json.loads(IFAM_STUB_SITE.read_text(encoding="utf-8")), record)
        self.assertNotIn("predictions", record)


if __name__ == "__main__":
    unittest.main()
