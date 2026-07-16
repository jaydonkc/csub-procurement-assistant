# Agent Production Readiness

Status: the public frontend, backend, and production agent behavior were verified end to end on July 16, 2026. The production UI includes identifier-only `DEMO-*` status records; authenticated requester/vendor status workflows are not implemented. A CSUB-approved custom domain and governance choices remain external decisions.

## Frozen Runtime

- Lambda: `csub-pa-mvp-chat-test`
- Alias: `production`
- Version: `22`
- API base URL: `https://w0vfga8dil.execute-api.us-west-2.amazonaws.com/prod`
- Chat: `POST /v1/chat`
- Health: `GET /v1/health`
- Immediate rollback version: `21`; version `22` adds deterministic source-verified routing and response templates for high-value guided workflows, improves supported partial answers, and retains the version `21` `DEMO-*` status provider, role-aware conversations, grounded guidance, and expiring source links
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

## Production Frontend

- Public URL: `https://d3s79ehfkh7xjx.cloudfront.net`
- CloudFront distribution: `E1J3M2Y5JS6LMM`, status `Deployed`
- Private S3 origin with public access fully blocked and CloudFront origin access control
- HTTPS redirect, HTTP/2 and HTTP/3, compressed delivery, security headers, and cache-safe asset metadata
- CloudFormation stack `csub-pa-production-frontend` and deployment script `scripts/deploy_frontend.sh`
- Live page, asset caching, CORS preflight, backend health, and a cited guided-chat response verified after deployment

## Request Pipeline

1. Validate and bound the request body, role, message, and recent history.
2. Apply deterministic capability, access, prompt-injection, and PII gates.
3. Resolve exact `DEMO-*` identifiers through the deterministic status provider and return a structured status card without calling retrieval or a model.
4. Apply narrow deterministic retrieval routes for high-confidence guided workflows, then route remaining turns as conversation, clarification, out of scope, or retrieval; default to retrieval on invalid, unavailable, or uncertain router output.
5. Return bounded natural language with no sources for non-retrieval turns; deterministic capability escalations direct users to `bwholgemuth1@csub.edu`.
6. For retrieval turns, retrieve only public candidates and exclude internal metadata and known internal/admin paths.
7. Use source-verified templates for high-frequency guided workflows or grounded model generation for other questions.
8. Normalize citations, reject unknown citation IDs, verify citation coverage, and audit entailment, numeric operators, and source scope.
9. Attempt one constrained correction; fail closed if the answer remains unsupported and provide the configured escalation contact.
10. Return only cited public source cards, optional structured demo status, optional 15-minute private source links, and privacy-preserving request metadata.

The frozen public agent cannot submit, approve, edit, withdraw, reject, or look up live transactions. It can return only the four packaged `DEMO-*` records through the deterministic status path. Self-reported roles affect wording and suggested questions only and never authorize restricted content. Public escalation responses direct users to `bwholgemuth1@csub.edu`. Any requester/vendor live status lookup added to the MVP must use authenticated read-only integration and backend authorization before returning personalized records.

Production version `21` introduced the packaged status path, which recognizes only records with explicit `DEMO-*` identifiers, and version `22` retains that boundary. The identifier is the sole user-visible demo marker; answer text, panel labels, and field values otherwise use the production-shaped presentation. It is a demo of the future response shape, not authenticated status access and not a connection to CSUBUY. A real provider should sit behind a read-only tool boundary with identity and record-level authorization enforced independently of model output.

The version `22` deployment passed 109/109 focused runtime tests. The combined pre-merge backend suite passed 129/129 tests, including structured status responses, no-model/no-retrieval demo lookup, deterministic guided routing, unknown-ID failure, mutation blocking, and preservation of the ordinary no-live-access boundary.

## Pydantic AI Development Refactor

The development implementation reorganizes the backend without changing the product boundary:

- Pydantic models validate chat requests, recent history, response source cards, and the grounding verdict.
- Pydantic AI uses Bedrock Converse for typed Haiku retrieval routing, Sonnet answer generation, and a structured Haiku grounding audit.
- An output validator checks citation syntax and source IDs, runs the grounding audit, and permits one constrained model retry before failing closed.
- Request classification, guided clarification, Knowledge Base retrieval, public-source filtering, source caps, source-verified workflow templates, and S3 URL signing remain deterministic application code.
- Retrieval is performed before model execution and is not exposed as a model-optional tool.

This Pydantic path is deployed to the frozen `production` alias. Its deployment-time runtime suite passes 109/109 focused tests, including retrieval routing, valid-audit, retry-exhaustion, structured-audit-rejection, verdict-consistency, cited-source filtering, escalation routing, structured status routing, and handler fallback coverage. The 37-scenario response acceptance suite should be rerun through the protected production API before any future alias move.

## Acceptance Results

Final post-deployment run through API Gateway and WAF:

- Comprehensive response acceptance: 37/37 passed, including 14/14 blocker, 17/17 high-severity, and 6/6 medium-severity scenarios, with 13.603-second p95 end-to-end latency.
- Raw retrieval: 34/36 exact expected-source hits, 93.1% mean term coverage, 0 internal leaks, 3/3 timestamp checks, 1.783-second p95.
- Earlier guided end to end: 13/13 HTTP successes, 13/13 expected-source hits, 13/13 valid citation sets, 0 internal leaks, 0 duplicate source cards, 3/3 timestamp checks, 9.215-second p95.
- Boundary and adversarial behavior: 8/8 passed.
- Conditional retrieval/source-link live check: 9/9 routing scenarios passed; `hi` returned no sources in both the API and deployed UI; cited PDF and video links returned the correct content types.
- Current deployment-time runtime suite: 109/109 passed; combined pre-merge backend suite: 129/129 passed.
- Production status-panel smoke check: `DEMO-INV-3001` returned the structured four-stage record through API Gateway and rendered automatically in CloudFront with no extra demo/synthetic labels; an ordinary invoice number still returned the no-live-access boundary.

The raw retrieval evaluation still records exact-source misses for supplier search and Marketplace end-user training, plus partial term coverage for the forms scenario. These are not hidden: the guided product suite passes because query routing, public-source enforcement, clarification, and source-verified workflows are part of the product being evaluated.

## Remaining External Decisions

- Decide whether to replace the working CloudFront domain with a CSUB-approved custom domain and ACM certificate.
- Supply and confirm an alert recipient for the already-provisioned SNS topic.
- Approve retention and analytics rules before storing user questions or feedback.
- Physically separate restricted content or add authentication and authorization before enabling any personalized requester, vendor, or internal workflow.
- Assign content-governance ownership before automating the custom-connector synchronization process.
