# Response acceptance tests

The response suite keeps test data separate from runner logic:

- `response_scenarios.json` contains prompts, roles, history, severity, tags, and expected behavior.
- `response_scenarios.schema.json` documents the JSON contract for editors and CI validation.
- `scripts/run_response_evals.py` calls the public `/v1/chat` endpoint and evaluates the response.

The runner checks more than keyword presence. It validates the suite contract before making requests, then checks HTTP and response shape, required and prohibited answer content, regexes, source paths, citation resolution, source URLs, video timestamps, duplicate source cards, and case-insensitive internal-source leakage.

## Validate without calling the API

```bash
.venv/bin/python scripts/run_response_evals.py --dry-run
```

## Run the complete production suite

```bash
.venv/bin/python scripts/run_response_evals.py \
  --jobs 4 \
  --output outputs/response-evals/production.json
```

The command exits nonzero when any scenario fails. Use `--allow-failures` only when collecting a diagnostic baseline.

## Run focused scenarios

```bash
# All invoice scenarios
.venv/bin/python scripts/run_response_evals.py --tag invoice

# Safety and authorization boundaries
.venv/bin/python scripts/run_response_evals.py --tag boundary

# One regression
.venv/bin/python scripts/run_response_evals.py \
  --case invoice_requirements_partial_answer
```

Multiple `--case` and `--tag` flags are supported. Case IDs restrict the selected IDs; tags then keep cases matching at least one requested tag.

## Test another environment

```bash
CSUB_EVAL_BASE_URL=http://127.0.0.1:8000 \
  .venv/bin/python scripts/run_response_evals.py --tag grounded
```

The base URL should end before `/v1/chat`. It can also be supplied with `--base-url`.

## Add a scenario

Each case contains:

- `id`, `description`, `severity`, and `tags` for reporting and filtering;
- `request.message`, `request.role`, and optional conversation `history`;
- `expect.answer` assertions for required, alternative, prohibited, or regex content;
- `expect.sources` assertions for counts, paths, citations, URLs, and timestamps.

Use `contains_all` for essential wording, `contains_any` for acceptable alternatives, and `contains_any_groups` when every conceptual requirement has several acceptable phrasings. Prefer intent-level assertions over exact full-answer snapshots so harmless wording changes do not make the suite brittle.

Global defaults always check that citation IDs resolve to returned source cards and that internal/admin source paths do not leak into public responses.
