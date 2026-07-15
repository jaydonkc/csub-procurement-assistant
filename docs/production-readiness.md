# Agent Production Readiness

Status: backend and production agent behavior verified July 15, 2026. The remaining launch work is frontend integration, an approved domain, and governance choices that cannot be inferred from the technical implementation.

## Frozen Runtime

- Lambda: `csub-pa-mvp-chat-test`
- Alias: `production`
- Version: `4`
- API base URL: `https://w0vfga8dil.execute-api.us-west-2.amazonaws.com/prod`
- Chat: `POST /v1/chat`
- Health: `GET /v1/health`
- Rollback versions: `2`, then `1`
- Knowledge Base: `3MMHDI5IDU`
- Generation: US Anthropic Claude Sonnet 4.6
- Validation: US Anthropic Claude Haiku 4.5

API Gateway invokes only the immutable `production` alias. The `$LATEST` and alias Lambda Function URLs remain available for authenticated operator diagnostics but use `AuthType=AWS_IAM`; anonymous callers receive `403` and cannot bypass the protected API.

## Production Ingress And Operations

- Regional REST API `w0vfga8dil` with JSON-schema request validation and versioned routes.
- API Gateway throttling at 5 requests per second with a burst of 10.
- Regional WAF with a 64,000-byte body limit and 300-requests-per-five-minutes source-IP rate rule.
- CORS and consistent JSON gateway errors for the future standalone frontend.
- X-Ray on API Gateway and Lambda.
- Privacy-safe API access logs, application logs, and blocked-request WAF logs retained for 30 days.
- CloudWatch dashboard `csub-pa-production` and six alarms wired to `csub-pa-prod-alerts`.
- No raw question, chat history, or feedback database.
- CloudFormation stack `csub-pa-production-backend` and rollback-safe deployment script `scripts/deploy_backend.sh`.

## Request Pipeline

1. Validate and bound the request body, role, message, and recent history.
2. Apply deterministic capability, access, prompt-injection, PII, and out-of-scope gates.
3. Ask a guided clarification when required purchase context is missing.
4. Retrieve only public candidates and exclude internal metadata and known internal/admin paths.
5. Use source-verified templates for high-frequency guided workflows or grounded model generation for other questions.
6. Normalize citations, reject unknown citation IDs, verify citation coverage, and audit entailment, numeric operators, and source scope.
7. Attempt one constrained correction; fail closed if the answer remains unsupported.
8. Return only cited public source cards and privacy-preserving request metadata.

The agent cannot submit, approve, edit, withdraw, reject, or look up transactions. Self-reported roles affect wording only and never authorize restricted content.

## Acceptance Results

Final post-deployment run through API Gateway and WAF:

- Raw retrieval: 34/36 exact expected-source hits, 93.1% mean term coverage, 0 internal leaks, 3/3 timestamp checks, 1.783-second p95.
- Guided end to end: 13/13 HTTP successes, 13/13 expected-source hits, 13/13 valid citation sets, 0 internal leaks, 0 duplicate source cards, 3/3 timestamp checks, 9.215-second p95.
- Boundary and adversarial behavior: 8/8 passed.
- Local policy/API suite: 58/58 passed.

The raw retrieval evaluation still records exact-source misses for supplier search and Marketplace end-user training, plus partial term coverage for the forms scenario. These are not hidden: the guided product suite passes because query routing, public-source enforcement, clarification, and source-verified workflows are part of the product being evaluated.

## Remaining External Decisions

- Connect the final standalone frontend to `POST /v1/chat` and put it behind its approved domain/CDN.
- Supply and confirm an alert recipient for the already-provisioned SNS topic.
- Approve retention and analytics rules before storing user questions or feedback.
- Physically separate restricted content or add authentication before enabling any internal workflow.
- Assign content-governance ownership before automating the custom-connector synchronization process.
