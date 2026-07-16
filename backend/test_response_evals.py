import copy
import unittest

from scripts import run_response_evals as evals


class ResponseEvalSuiteTests(unittest.TestCase):
    def setUp(self):
        self.defaults = {
            "citations_must_resolve": True,
            "forbid_duplicate_source_ids": True,
            "forbid_duplicate_source_paths": True,
            "forbid_internal_sources": True,
            "forbidden_source_path_prefixes": ["Approvals/", "Admin/"],
            "forbidden_source_paths": ["internal.pdf"],
        }
        self.case = {
            "id": "invoice",
            "description": "test",
            "severity": "blocker",
            "tags": ["grounded"],
            "request": {
                "message": "What belongs on an invoice?",
                "role": "vendor",
            },
            "expect": {
                "http_status": 200,
                "answer": {
                    "min_chars": 10,
                    "contains_all": ["itemized"],
                    "contains_any_groups": [["not exhaustive", "not complete"]],
                    "not_contains": ["taxes charged"],
                },
                "sources": {
                    "min_count": 1,
                    "path_contains_all": ["guide.pdf"],
                    "citations_required": True,
                    "source_urls_required": True,
                },
            },
        }
        self.payload = {
            "answer": "Use an itemized invoice; this is not exhaustive [S1].",
            "sources": [
                {
                    "id": "S1",
                    "path": "Getting Started/guide.pdf",
                    "source_url": "https://sources.example/guide?token=temporary",
                }
            ],
            "request_id": "request-1",
        }

    def evaluate(self, case=None, payload=None):
        return evals.evaluate_case(
            case or self.case,
            status=200,
            payload=payload or self.payload,
            latency_seconds=0.25,
            defaults=self.defaults,
        )

    def test_repository_json_suite_is_valid(self):
        suite = evals.load_suite(evals.DEFAULT_SUITE)
        self.assertGreaterEqual(len(suite["cases"]), 30)
        self.assertEqual(
            len({case["id"] for case in suite["cases"]}), len(suite["cases"])
        )

    def test_grounded_response_passes_all_assertions(self):
        result = self.evaluate()
        self.assertTrue(result["passed"])
        self.assertEqual(result["failures"], [])
        self.assertEqual(
            result["response"]["sources"][0]["source_url"],
            "https://sources.example/guide",
        )

    def test_unresolved_citation_fails(self):
        payload = copy.deepcopy(self.payload)
        payload["answer"] = "Use an itemized invoice; this is not exhaustive [S99]."
        result = self.evaluate(payload=payload)
        failure_names = {failure["name"] for failure in result["failures"]}
        self.assertIn("citations_resolve", failure_names)

    def test_internal_source_path_fails(self):
        payload = copy.deepcopy(self.payload)
        payload["sources"][0]["path"] = "approvals/internal.pdf"
        result = self.evaluate(payload=payload)
        failure_names = {failure["name"] for failure in result["failures"]}
        self.assertIn("no_internal_source_leaks", failure_names)

    def test_prohibited_claim_fails(self):
        payload = copy.deepcopy(self.payload)
        payload["answer"] = (
            "Use an itemized invoice; this is not exhaustive and must list taxes charged [S1]."
        )
        result = self.evaluate(payload=payload)
        failure_names = {failure["name"] for failure in result["failures"]}
        self.assertIn("answer_excludes:taxes charged", failure_names)

    def test_duplicate_case_ids_are_rejected(self):
        suite = {
            "schema_version": 1,
            "name": "duplicate",
            "default_base_url": "https://example.test",
            "defaults": {},
            "cases": [self.case, copy.deepcopy(self.case)],
        }
        with self.assertRaisesRegex(evals.SuiteValidationError, "Duplicate case id"):
            evals.validate_suite(suite)

    def test_invalid_regex_is_rejected_before_requests_run(self):
        case = copy.deepcopy(self.case)
        case["expect"]["answer"]["regex_all"] = ["("]
        suite = {
            "schema_version": 1,
            "name": "invalid-regex",
            "default_base_url": "https://example.test",
            "defaults": {},
            "cases": [case],
        }
        with self.assertRaisesRegex(evals.SuiteValidationError, "valid regular expression"):
            evals.validate_suite(suite)

    def test_unknown_expectation_field_is_rejected(self):
        case = copy.deepcopy(self.case)
        case["expect"]["sources"]["typo_count"] = 1
        suite = {
            "schema_version": 1,
            "name": "unknown-field",
            "default_base_url": "https://example.test",
            "defaults": {},
            "cases": [case],
        }
        with self.assertRaisesRegex(evals.SuiteValidationError, "unsupported fields"):
            evals.validate_suite(suite)

    def test_case_and_tag_filters_can_be_combined(self):
        second = copy.deepcopy(self.case)
        second["id"] = "second"
        second["tags"] = ["boundary"]
        selected = evals.select_cases(
            [self.case, second], case_ids={"invoice", "second"}, tags={"grounded"}
        )
        self.assertEqual([case["id"] for case in selected], ["invoice"])


if __name__ == "__main__":
    unittest.main()
