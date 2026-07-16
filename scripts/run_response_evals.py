#!/usr/bin/env python3
"""Run JSON-defined response acceptance tests against the public chat API."""

from __future__ import annotations

import argparse
import json
import os
import re
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

try:
    import certifi
except ImportError:  # fall back to the interpreter's configured CA store
    certifi = None


ROOT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_SUITE = ROOT_DIR / "evals" / "response_scenarios.json"
VALID_ROLES = {"requester", "vendor", "internal_staff"}
VALID_SEVERITIES = {"blocker", "high", "medium", "low"}
CITATION_PATTERN = re.compile(r"\[(S\d+)\]")
SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where() if certifi else None)


class SuiteValidationError(ValueError):
    """Raised when a JSON suite does not match the supported contract."""


def _require_type(value: Any, expected: type, location: str) -> None:
    if not isinstance(value, expected) or (expected is int and isinstance(value, bool)):
        raise SuiteValidationError(
            f"{location} must be {expected.__name__}, got {type(value).__name__}."
        )


def _reject_unknown_keys(value: dict[str, Any], allowed: set[str], location: str) -> None:
    unknown = sorted(set(value) - allowed)
    if unknown:
        raise SuiteValidationError(
            f"{location} contains unsupported fields: {', '.join(unknown)}."
        )


def _validate_string_list(
    value: Any, location: str, *, unique: bool = False
) -> None:
    _require_type(value, list, location)
    if not all(isinstance(item, str) and item.strip() for item in value):
        raise SuiteValidationError(f"{location} must contain only non-empty strings.")
    if unique and len(value) != len(set(value)):
        raise SuiteValidationError(f"{location} must not contain duplicates.")


def _validate_nonnegative_int(value: Any, location: str) -> None:
    _require_type(value, int, location)
    if value < 0:
        raise SuiteValidationError(f"{location} must be nonnegative.")


def _validate_regex_list(value: Any, location: str) -> None:
    _validate_string_list(value, location)
    for index, pattern in enumerate(value):
        try:
            re.compile(pattern)
        except re.error as exc:
            raise SuiteValidationError(
                f"{location}[{index}] is not a valid regular expression: {exc}."
            ) from exc


def validate_suite(suite: dict[str, Any]) -> None:
    """Validate the subset of the JSON schema required by the runner."""
    _require_type(suite, dict, "suite")
    _reject_unknown_keys(
        suite,
        {
            "$schema",
            "schema_version",
            "name",
            "description",
            "default_base_url",
            "defaults",
            "cases",
        },
        "suite",
    )
    if suite.get("schema_version") != 1:
        raise SuiteValidationError("schema_version must be 1.")
    _require_type(suite.get("name"), str, "name")
    if not suite["name"].strip():
        raise SuiteValidationError("name must be a non-empty string.")
    if "description" in suite:
        _require_type(suite["description"], str, "description")
    base_url = suite.get("default_base_url")
    _require_type(base_url, str, "default_base_url")
    parsed_base_url = urllib.parse.urlsplit(base_url)
    if parsed_base_url.scheme not in {"http", "https"} or not parsed_base_url.netloc:
        raise SuiteValidationError("default_base_url must be an absolute HTTP(S) URL.")
    defaults = suite.get("defaults", {})
    _require_type(defaults, dict, "defaults")
    _reject_unknown_keys(
        defaults,
        {
            "citations_must_resolve",
            "forbid_duplicate_source_ids",
            "forbid_duplicate_source_paths",
            "forbid_internal_sources",
            "forbidden_source_path_prefixes",
            "forbidden_source_paths",
        },
        "defaults",
    )
    for key in (
        "citations_must_resolve",
        "forbid_duplicate_source_ids",
        "forbid_duplicate_source_paths",
        "forbid_internal_sources",
    ):
        if key in defaults and not isinstance(defaults[key], bool):
            raise SuiteValidationError(f"defaults.{key} must be bool.")
    for key in ("forbidden_source_path_prefixes", "forbidden_source_paths"):
        if key in defaults:
            _validate_string_list(defaults[key], f"defaults.{key}", unique=True)

    cases = suite.get("cases")
    _require_type(cases, list, "cases")
    if not cases:
        raise SuiteValidationError("cases must not be empty.")

    seen_ids: set[str] = set()
    for index, case in enumerate(cases):
        location = f"cases[{index}]"
        _require_type(case, dict, location)
        _reject_unknown_keys(
            case,
            {"id", "description", "severity", "tags", "enabled", "request", "expect"},
            location,
        )
        case_id = case.get("id")
        if not isinstance(case_id, str) or not case_id.strip():
            raise SuiteValidationError(f"{location}.id must be a non-empty string.")
        if case_id in seen_ids:
            raise SuiteValidationError(f"Duplicate case id: {case_id}.")
        seen_ids.add(case_id)
        if case.get("severity") not in VALID_SEVERITIES:
            raise SuiteValidationError(
                f"{location}.severity must be one of {sorted(VALID_SEVERITIES)}."
            )
        description = case.get("description")
        if not isinstance(description, str) or not description.strip():
            raise SuiteValidationError(f"{location}.description must be a non-empty string.")
        _validate_string_list(case.get("tags"), f"{location}.tags", unique=True)
        if not case["tags"]:
            raise SuiteValidationError(f"{location}.tags must not be empty.")
        if "enabled" in case and not isinstance(case["enabled"], bool):
            raise SuiteValidationError(f"{location}.enabled must be bool.")

        request = case.get("request")
        _require_type(request, dict, f"{location}.request")
        _reject_unknown_keys(request, {"message", "role", "history"}, f"{location}.request")
        if not isinstance(request.get("message"), str) or not request["message"].strip():
            raise SuiteValidationError(
                f"{location}.request.message must be a non-empty string."
            )
        if len(request["message"]) > 4_000:
            raise SuiteValidationError(f"{location}.request.message exceeds 4000 characters.")
        if request.get("role") not in VALID_ROLES:
            raise SuiteValidationError(
                f"{location}.request.role must be one of {sorted(VALID_ROLES)}."
            )
        history = request.get("history", [])
        _require_type(history, list, f"{location}.request.history")
        if len(history) > 6:
            raise SuiteValidationError(f"{location}.request.history exceeds 6 items.")
        for history_index, item in enumerate(history):
            if (
                not isinstance(item, dict)
                or set(item) != {"role", "text"}
                or item.get("role") not in {"user", "assistant"}
                or not isinstance(item.get("text"), str)
                or not item["text"].strip()
            ):
                raise SuiteValidationError(
                    f"{location}.request.history[{history_index}] is invalid."
                )

        expect = case.get("expect")
        _require_type(expect, dict, f"{location}.expect")
        _reject_unknown_keys(
            expect,
            {"http_status", "max_latency_seconds", "answer", "sources"},
            f"{location}.expect",
        )
        if "http_status" in expect:
            _validate_nonnegative_int(expect["http_status"], f"{location}.expect.http_status")
            if not 100 <= expect["http_status"] <= 599:
                raise SuiteValidationError(f"{location}.expect.http_status must be 100-599.")
        if "max_latency_seconds" in expect:
            value = expect["max_latency_seconds"]
            if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
                raise SuiteValidationError(
                    f"{location}.expect.max_latency_seconds must be positive."
                )
        for section in ("answer", "sources"):
            if section in expect:
                _require_type(expect[section], dict, f"{location}.expect.{section}")
        answer_expect = expect.get("answer", {})
        _reject_unknown_keys(
            answer_expect,
            {
                "min_chars",
                "max_chars",
                "contains_all",
                "contains_any",
                "contains_any_groups",
                "not_contains",
                "regex_all",
                "regex_any",
                "not_regex",
                "question_mark",
            },
            f"{location}.expect.answer",
        )
        for key in ("min_chars", "max_chars"):
            if key in answer_expect:
                _validate_nonnegative_int(
                    answer_expect[key], f"{location}.expect.answer.{key}"
                )
        if "max_chars" in answer_expect and answer_expect["max_chars"] < 1:
            raise SuiteValidationError(f"{location}.expect.answer.max_chars must be positive.")
        if (
            "min_chars" in answer_expect
            and "max_chars" in answer_expect
            and answer_expect["min_chars"] > answer_expect["max_chars"]
        ):
            raise SuiteValidationError(
                f"{location}.expect.answer.min_chars cannot exceed max_chars."
            )
        if "question_mark" in answer_expect and not isinstance(
            answer_expect["question_mark"], bool
        ):
            raise SuiteValidationError(
                f"{location}.expect.answer.question_mark must be bool."
            )
        for key in (
            "contains_all",
            "contains_any",
            "not_contains",
        ):
            if key in answer_expect:
                _validate_string_list(
                    answer_expect[key], f"{location}.expect.answer.{key}"
                )
        for key in ("regex_all", "regex_any", "not_regex"):
            if key in answer_expect:
                _validate_regex_list(
                    answer_expect[key], f"{location}.expect.answer.{key}"
                )
        groups = answer_expect.get("contains_any_groups", [])
        _require_type(groups, list, f"{location}.expect.answer.contains_any_groups")
        for group_index, group in enumerate(
            groups
        ):
            _validate_string_list(
                group,
                f"{location}.expect.answer.contains_any_groups[{group_index}]",
            )
            if not group:
                raise SuiteValidationError(
                    f"{location}.expect.answer.contains_any_groups[{group_index}] must not be empty."
                )
        source_expect = expect.get("sources", {})
        _reject_unknown_keys(
            source_expect,
            {
                "min_count",
                "max_count",
                "path_contains_all",
                "path_contains_any",
                "path_not_contains",
                "citations_required",
                "timestamps_required",
                "source_urls_required",
            },
            f"{location}.expect.sources",
        )
        for key in ("min_count", "max_count"):
            if key in source_expect:
                _validate_nonnegative_int(
                    source_expect[key], f"{location}.expect.sources.{key}"
                )
        if (
            "min_count" in source_expect
            and "max_count" in source_expect
            and source_expect["min_count"] > source_expect["max_count"]
        ):
            raise SuiteValidationError(
                f"{location}.expect.sources.min_count cannot exceed max_count."
            )
        for key in (
            "citations_required",
            "timestamps_required",
            "source_urls_required",
        ):
            if key in source_expect and not isinstance(source_expect[key], bool):
                raise SuiteValidationError(f"{location}.expect.sources.{key} must be bool.")
        for key in ("path_contains_all", "path_contains_any", "path_not_contains"):
            if key in source_expect:
                _validate_string_list(
                    source_expect[key], f"{location}.expect.sources.{key}"
                )


def load_suite(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as source:
        suite = json.load(source)
    validate_suite(suite)
    return suite


def _check(
    checks: list[dict[str, Any]],
    name: str,
    passed: bool,
    *,
    expected: Any = None,
    actual: Any = None,
) -> None:
    check: dict[str, Any] = {"name": name, "passed": bool(passed)}
    if expected is not None:
        check["expected"] = expected
    if actual is not None:
        check["actual"] = actual
    checks.append(check)


def _redact_url_query(value: Any) -> Any:
    if not isinstance(value, str) or not value:
        return value
    parsed = urllib.parse.urlsplit(value)
    if not parsed.scheme or not parsed.netloc:
        return value
    return urllib.parse.urlunsplit(
        (parsed.scheme, parsed.netloc, parsed.path, "", "")
    )


def _report_sources(sources: list[dict[str, Any]]) -> list[dict[str, Any]]:
    sanitized = []
    for source in sources:
        item = dict(source)
        for key in ("source_url", "media_url"):
            if key in item:
                item[key] = _redact_url_query(item[key])
        sanitized.append(item)
    return sanitized


def evaluate_case(
    case: dict[str, Any],
    *,
    status: int,
    payload: dict[str, Any],
    latency_seconds: float,
    defaults: dict[str, Any],
) -> dict[str, Any]:
    """Evaluate one HTTP response without making a network request."""
    checks: list[dict[str, Any]] = []
    expect = case["expect"]
    expected_status = int(expect.get("http_status", 200))
    _check(
        checks,
        "http_status",
        status == expected_status,
        expected=expected_status,
        actual=status,
    )

    answer = payload.get("answer")
    sources = payload.get("sources")
    request_id = payload.get("request_id")
    response_shape_ok = (
        isinstance(answer, str)
        and isinstance(sources, list)
        and all(
            isinstance(item, dict)
            and isinstance(item.get("id"), str)
            and bool(item["id"].strip())
            and isinstance(item.get("path"), str)
            and bool(item["path"].strip())
            for item in sources
        )
        and isinstance(request_id, str)
        and bool(request_id.strip())
    )
    _check(checks, "response_shape", response_shape_ok)
    answer = answer if isinstance(answer, str) else ""
    sources = sources if isinstance(sources, list) else []
    lowered = answer.casefold()

    answer_expect = expect.get("answer", {})
    min_chars = int(answer_expect.get("min_chars", 1))
    _check(
        checks,
        "answer_min_chars",
        len(answer.strip()) >= min_chars,
        expected=min_chars,
        actual=len(answer.strip()),
    )
    if "max_chars" in answer_expect:
        max_chars = int(answer_expect["max_chars"])
        _check(
            checks,
            "answer_max_chars",
            len(answer) <= max_chars,
            expected=max_chars,
            actual=len(answer),
        )
    for term in answer_expect.get("contains_all", []):
        _check(
            checks,
            f"answer_contains:{term}",
            term.casefold() in lowered,
            expected=term,
        )
    contains_any = answer_expect.get("contains_any", [])
    if contains_any:
        _check(
            checks,
            "answer_contains_any",
            any(term.casefold() in lowered for term in contains_any),
            expected=contains_any,
        )
    for index, group in enumerate(answer_expect.get("contains_any_groups", [])):
        _check(
            checks,
            f"answer_contains_any_group:{index}",
            any(term.casefold() in lowered for term in group),
            expected=group,
        )
    for term in answer_expect.get("not_contains", []):
        _check(
            checks,
            f"answer_excludes:{term}",
            term.casefold() not in lowered,
            expected=f"not {term}",
        )
    for pattern in answer_expect.get("regex_all", []):
        _check(
            checks,
            f"answer_regex:{pattern}",
            re.search(pattern, answer, re.IGNORECASE | re.MULTILINE) is not None,
            expected=pattern,
        )
    regex_any = answer_expect.get("regex_any", [])
    if regex_any:
        _check(
            checks,
            "answer_regex_any",
            any(
                re.search(pattern, answer, re.IGNORECASE | re.MULTILINE)
                for pattern in regex_any
            ),
            expected=regex_any,
        )
    for pattern in answer_expect.get("not_regex", []):
        _check(
            checks,
            f"answer_excludes_regex:{pattern}",
            re.search(pattern, answer, re.IGNORECASE | re.MULTILINE) is None,
            expected=f"not {pattern}",
        )
    if "question_mark" in answer_expect:
        expected_question = bool(answer_expect["question_mark"])
        _check(
            checks,
            "answer_question_mark",
            ("?" in answer) == expected_question,
            expected=expected_question,
            actual="?" in answer,
        )

    paths = [str(source.get("path", "")) for source in sources]
    source_ids = [str(source.get("id", "")) for source in sources]
    source_expect = expect.get("sources", {})
    min_count = int(source_expect.get("min_count", 0))
    _check(
        checks,
        "source_min_count",
        len(sources) >= min_count,
        expected=min_count,
        actual=len(sources),
    )
    if "max_count" in source_expect:
        max_count = int(source_expect["max_count"])
        _check(
            checks,
            "source_max_count",
            len(sources) <= max_count,
            expected=max_count,
            actual=len(sources),
        )
    for fragment in source_expect.get("path_contains_all", []):
        _check(
            checks,
            f"source_path_contains:{fragment}",
            any(fragment.casefold() in path.casefold() for path in paths),
            expected=fragment,
            actual=paths,
        )
    path_contains_any = source_expect.get("path_contains_any", [])
    if path_contains_any:
        _check(
            checks,
            "source_path_contains_any",
            any(
                fragment.casefold() in path.casefold()
                for fragment in path_contains_any
                for path in paths
            ),
            expected=path_contains_any,
            actual=paths,
        )
    for fragment in source_expect.get("path_not_contains", []):
        _check(
            checks,
            f"source_path_excludes:{fragment}",
            not any(fragment.casefold() in path.casefold() for path in paths),
            expected=f"not {fragment}",
            actual=paths,
        )

    citations = set(CITATION_PATTERN.findall(answer))
    available_ids = {source_id for source_id in source_ids if source_id}
    citations_required = bool(source_expect.get("citations_required", False))
    if citations_required:
        _check(checks, "citations_present", bool(citations))
    if defaults.get("citations_must_resolve", True):
        _check(
            checks,
            "citations_resolve",
            citations.issubset(available_ids),
            expected=sorted(available_ids),
            actual=sorted(citations),
        )
    if source_expect.get("timestamps_required"):
        _check(
            checks,
            "source_timestamp_present",
            any(source.get("timestamp") for source in sources),
        )
    if source_expect.get("source_urls_required"):
        _check(
            checks,
            "source_urls_present",
            bool(sources) and all(source.get("source_url") for source in sources),
        )

    if defaults.get("forbid_duplicate_source_ids", True):
        _check(
            checks,
            "no_duplicate_source_ids",
            len(source_ids) == len(set(source_ids)),
            actual=source_ids,
        )
    if defaults.get("forbid_duplicate_source_paths", True):
        _check(
            checks,
            "no_duplicate_source_paths",
            len(paths) == len(set(paths)),
            actual=paths,
        )
    if defaults.get("forbid_internal_sources", True):
        forbidden_prefixes = tuple(
            prefix.casefold()
            for prefix in defaults.get("forbidden_source_path_prefixes", [])
        )
        forbidden_paths = {
            path.casefold() for path in defaults.get("forbidden_source_paths", [])
        }
        leaked = [
            path
            for path in paths
            if path.casefold() in forbidden_paths
            or path.casefold().startswith(forbidden_prefixes)
        ]
        _check(checks, "no_internal_source_leaks", not leaked, actual=leaked)

    if "max_latency_seconds" in expect:
        max_latency = float(expect["max_latency_seconds"])
        _check(
            checks,
            "max_latency_seconds",
            latency_seconds <= max_latency,
            expected=max_latency,
            actual=round(latency_seconds, 3),
        )

    failures = [check for check in checks if not check["passed"]]
    return {
        "id": case["id"],
        "severity": case["severity"],
        "tags": case["tags"],
        "passed": not failures,
        "latency_seconds": round(latency_seconds, 3),
        "checks": checks,
        "failures": failures,
        "response": {
            "status": status,
            "answer": answer,
            "sources": _report_sources(sources),
            "request_id": request_id,
        },
    }


def post_chat(endpoint: str, request_payload: dict[str, Any], timeout: float) -> tuple[int, dict[str, Any]]:
    body = json.dumps(request_payload).encode("utf-8")
    request = urllib.request.Request(
        endpoint,
        data=body,
        headers={"content-type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(
            request, timeout=timeout, context=SSL_CONTEXT
        ) as response:
            status = response.status
            raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        status = exc.code
        raw = exc.read().decode("utf-8")
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        payload = {"answer": "", "sources": [], "request_id": "", "raw_body": raw}
    return status, payload


def get_health(base_url: str, timeout: float) -> tuple[int, dict[str, Any]]:
    endpoint = f"{base_url.rstrip('/')}/v1/health"
    request = urllib.request.Request(endpoint, method="GET")
    try:
        with urllib.request.urlopen(
            request, timeout=timeout, context=SSL_CONTEXT
        ) as response:
            status = response.status
            raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        status = exc.code
        raw = exc.read().decode("utf-8")
    try:
        return status, json.loads(raw)
    except json.JSONDecodeError:
        return status, {"raw_body": raw}


def run_case(
    case: dict[str, Any],
    *,
    endpoint: str,
    timeout: float,
    defaults: dict[str, Any],
) -> dict[str, Any]:
    started = time.monotonic()
    try:
        status, payload = post_chat(endpoint, case["request"], timeout)
        return evaluate_case(
            case,
            status=status,
            payload=payload,
            latency_seconds=time.monotonic() - started,
            defaults=defaults,
        )
    except Exception as exc:  # network failures should become test failures
        latency = time.monotonic() - started
        return {
            "id": case["id"],
            "severity": case["severity"],
            "tags": case["tags"],
            "passed": False,
            "latency_seconds": round(latency, 3),
            "checks": [],
            "failures": [
                {
                    "name": "request_error",
                    "passed": False,
                    "actual": f"{type(exc).__name__}: {exc}",
                }
            ],
            "response": {"status": None, "answer": "", "sources": []},
        }


def select_cases(
    cases: list[dict[str, Any]],
    *,
    case_ids: set[str],
    tags: set[str],
) -> list[dict[str, Any]]:
    selected = []
    for case in cases:
        if case.get("enabled", True) is False:
            continue
        if case_ids and case["id"] not in case_ids:
            continue
        if tags and not tags.intersection(case["tags"]):
            continue
        selected.append(case)
    return selected


def summarize(results: list[dict[str, Any]]) -> dict[str, Any]:
    passed = sum(result["passed"] for result in results)
    by_severity: dict[str, dict[str, int]] = {}
    for severity in VALID_SEVERITIES:
        matching = [result for result in results if result["severity"] == severity]
        if matching:
            by_severity[severity] = {
                "total": len(matching),
                "passed": sum(result["passed"] for result in matching),
                "failed": sum(not result["passed"] for result in matching),
            }
    latencies = sorted(result["latency_seconds"] for result in results)
    p95_index = max(0, int(len(latencies) * 0.95 + 0.999) - 1) if latencies else 0
    return {
        "total": len(results),
        "passed": passed,
        "failed": len(results) - passed,
        "pass_rate": round(passed / len(results), 4) if results else 0.0,
        "by_severity": by_severity,
        "p95_latency_seconds": latencies[p95_index] if latencies else None,
    }


def print_report(report: dict[str, Any]) -> None:
    summary = report["summary"]
    version = report.get("target_health", {}).get("version", "unknown")
    print(
        f"Response evals (version {version}): {summary['passed']}/{summary['total']} passed "
        f"({summary['pass_rate']:.1%}); p95={summary['p95_latency_seconds']}s"
    )
    for result in report["results"]:
        marker = "PASS" if result["passed"] else "FAIL"
        print(
            f"{marker:4}  {result['id']:<36} "
            f"{result['latency_seconds']:>6.2f}s  {result['severity']}"
        )
        if not result["passed"]:
            for failure in result["failures"]:
                actual = failure.get("actual")
                suffix = f" (actual: {actual})" if actual is not None else ""
                print(f"      - {failure['name']}{suffix}")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--suite", type=Path, default=DEFAULT_SUITE)
    parser.add_argument("--base-url", default=os.getenv("CSUB_EVAL_BASE_URL", ""))
    parser.add_argument("--case", action="append", default=[], dest="case_ids")
    parser.add_argument("--tag", action="append", default=[])
    parser.add_argument("--jobs", type=int, default=4)
    parser.add_argument("--timeout", type=float, default=35.0)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--allow-failures",
        action="store_true",
        help="Return exit code 0 even when response assertions fail.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    suite = load_suite(args.suite)
    cases = select_cases(
        suite["cases"], case_ids=set(args.case_ids), tags=set(args.tag)
    )
    if not cases:
        print("No enabled scenarios matched the supplied filters.", file=sys.stderr)
        return 2
    if args.dry_run:
        counts = Counter(tag for case in cases for tag in case["tags"])
        print(
            json.dumps(
                {
                    "suite": suite["name"],
                    "selected_cases": len(cases),
                    "tags": dict(sorted(counts.items())),
                },
                indent=2,
            )
        )
        return 0

    base_url = args.base_url or suite.get("default_base_url", "")
    if not base_url:
        print("Provide --base-url or set default_base_url in the suite.", file=sys.stderr)
        return 2
    base_url = base_url.rstrip("/")
    endpoint = f"{base_url}/v1/chat"
    try:
        health_status, health = get_health(base_url, args.timeout)
    except Exception as exc:
        print(f"Health preflight failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    if health_status != 200 or health.get("status") != "ok":
        print(
            f"Health preflight failed: HTTP {health_status}: {json.dumps(health)}",
            file=sys.stderr,
        )
        return 2
    results_by_id: dict[str, dict[str, Any]] = {}
    with ThreadPoolExecutor(max_workers=max(1, args.jobs)) as executor:
        futures = {
            executor.submit(
                run_case,
                case,
                endpoint=endpoint,
                timeout=args.timeout,
                defaults=suite.get("defaults", {}),
            ): case["id"]
            for case in cases
        }
        for future in as_completed(futures):
            results_by_id[futures[future]] = future.result()
    results = [results_by_id[case["id"]] for case in cases]
    report = {
        "suite": suite["name"],
        "schema_version": suite["schema_version"],
        "endpoint": endpoint,
        "target_health": health,
        "generated_at": datetime.now(UTC).isoformat(),
        "summary": summarize(results),
        "results": results,
    }
    print_report(report)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(f"Wrote JSON report to {args.output}")
    if report["summary"]["failed"] and not args.allow_failures:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
