# CSUB Procurement Assistant

A standalone, role-aware guided procurement assistant for California State University, Bakersfield.

The product helps CSUB requesters, vendors, and internal procurement stakeholders navigate CSUBUY/P2P, supplier onboarding, invoice questions, purchasing approvals, contract checks, commodity code guidance, technology review, and related procurement workflows.

This repository contains the product documentation, deployed React frontend, AWS Lambda agent source, infrastructure templates, and policy/grounding test suite. The production frontend calls the versioned Lambda handler in `backend/lambda_function.py` through API Gateway.

## Backend Architecture

The development backend uses Pydantic AI `2.10.0` as a thin orchestration layer over Amazon Bedrock Converse. Pydantic models validate the public chat contract, a Sonnet agent generates source-cited answers, and Haiku agents return typed retrieval-routing and grounding decisions. The answer agent gets one validation-driven retry before the request fails closed.

The Lambda applies deterministic capability and access gates first. Pydantic AI then runs the typed pre-retrieval router; only the `retrieve` route calls the filtered Bedrock Knowledge Base. Retrieval, public-source filtering, source caps, source-verified workflow templates, and source signing remain deterministic application code.

Backend modules:

- `backend/lambda_function.py` - Lambda/API adapter and request orchestration.
- `backend/models.py` - typed request, response, source-card, and grounding contracts.
- `backend/policy.py` - deterministic public-access and capability gates.
- `backend/retrieval.py` - Bedrock Knowledge Base query construction, filtering, and source caps.
- `backend/router.py` - deterministic fallback and reply-safety checks around typed routing.
- `backend/workflows.py` - source-verified responses for frequent procurement workflows.
- `backend/grounding.py` - citation normalization and deterministic grounding checks.
- `backend/pydantic_agent.py` - Pydantic AI routing, generation, structured auditing, and one-retry/fail-closed behavior.
- `backend/source_access.py` - internal-source exclusion and short-lived S3 source links.

The Pydantic AI refactor is development code and has not replaced the frozen Lambda `production` alias. It must pass the live retrieval and guided end-to-end acceptance suites before a new immutable Lambda version is published.

## Product Positioning

The intended product is a guided procurement assistant that combines RAG with structured intake flows.

Core behavior:
- Answer procurement questions in plain language.
- Ask clarifying questions when the correct path depends on purchase amount, supplier status, contract status, technology/software category, requester role, or invoice context.
- Retrieve answers from approved CSUB and CSU procurement sources.
- Cite the policy, guide, webpage, video transcript, or source document behind each answer.
- Generate role-specific checklists for requesters, vendors, and internal support teams.
- Route ambiguous or high-risk situations to Procurement, Accounts Payable, Supplier Management, ITS, or Solutions Consulting.

## Initial Scope

The first version should support:
- CSUB faculty and staff requesters buying goods, services, software, equipment, or subscriptions.
- Vendors and suppliers trying to understand registration, onboarding, invoice, purchase order, and payment-related steps.
- Internal support stakeholders who need consistent routing and source-backed guidance.

The initial version should be guidance-only:
- No authentication or user accounts.
- No requisition submission.
- No purchase approval.
- No write-back into ServiceNow.
- No write-back into CFS.
- No supplier registration submission.
- No personalized requisition, supplier, invoice, or payment lookup.
- No unsupported policy advice without source grounding.
- No restricted/internal-only sources unless they are explicitly approved for no-auth public use.

## AWS Architecture Baseline

The MVP AWS baseline is established in account `335010339891`, region `us-west-2`. Amazon S3 is the source of truth for approved content, an Amazon Bedrock managed Knowledge Base provides retrieval, and a versioned Lambda runtime provides the public guidance agent.

Live status as of July 14, 2026: the source-aware Knowledge Base is active and covers all 80 real source files from `CSUBuyP2P`. All 63 PDF/DOCX files are text-indexed through separate 450-token procedural and 600-token long-form data sources. All 17 MP4 files are stored in S3, and their complete VTT content is represented by 300 atomic, timestamped retrieval segments of no more than 90 seconds. The original VTT files remain the transcript source of truth. Because campus organization policy blocks the native S3 paths required here, the baseline uses managed custom connectors and an explicit operator synchronization step.

The chunked retrieval configuration passed a 12-scenario guided procurement comparison against the previous default chunker: 12/12 expected-source hits, better procedural coverage and source ranking, fewer duplicate context chunks after a two-chunks-per-source cap, useful timestamps for all five video-oriented questions, and no internal-source results under the public filter. The AWS test chatbot now uses this configuration.

The production agent behavior is frozen as Lambda version `2` behind the `production` alias. It uses Claude Sonnet 4.6 for grounded generation and Claude Haiku 4.5 for citation auditing. Deterministic pre-model gates block transaction actions, live lookups, internal/admin procedures, PII-access guidance, prompt injection, and explicit out-of-scope topics. Source-verified guided templates cover frequent workflows, while other answers must pass citation syntax, public-source, numeric-boundary, source-scope, and entailment checks or fail closed.

The final acceptance run passed 13/13 guided end-to-end scenarios with the expected source and valid citations, 8/8 adversarial/capability boundaries, 3/3 video timestamp checks, zero internal-source leaks, zero duplicate source cards, and 8.193-second p95 end-to-end latency. The broader raw-retrieval suite retained 34/36 exact-source hits and 93.1% mean term coverage; guided routing is evaluated separately because the product is not a generic similarity-search chatbot.

The current Knowledge Base intentionally includes internal/admin and sensitive-PII-access guidance from the supplied collection. Those sources carry `access_scope=internal` metadata, but the connector does not enforce ACLs. A public/no-auth application must enforce source filtering or use a separate restricted corpus before launch.

Test the frozen agent at [CSUB Procurement Assistant — production alias](https://etwxpbmxee2s6vniis3sgez5m40vorpg.lambda-url.us-west-2.on.aws/). The mutable `$LATEST` test URL remains available for future pre-release checks but is not the production target.

See [AWS architecture](docs/aws-architecture.md) for the live resource inventory, ingestion boundary, and deferred decisions.

Production-hosting areas still open:
- Custom domain, CDN, WAF, and public-endpoint abuse controls.
- Integration of the standalone frontend with the frozen production alias.
- Analytics and feedback storage with an approved question-retention policy.
- Admin tools and automated synchronization for future source changes.
- Authentication and corpus separation for any future restricted workflow.
- Infrastructure-as-code for repeatable environment provisioning.

MVP access model:
- Public/no-auth web assistant.
- Only sources approved for no-auth exposure should be returned to public users.
- Role selection is self-reported and used for guidance style, not authorization.

The repository should keep the product architecture modular enough to support:
- A standalone full-page web assistant first.
- An embeddable widget later if CSUB wants to place it inside existing procurement pages.
- Separate role flows for requesters, vendors, and internal staff.
- Future read-only integrations with ServiceNow, P2P, supplier, contract, or approved-software systems.

## Documentation

- [Discovery notes](docs/discovery-notes.md)
- [Feature specification](docs/feature-spec.md)
- [AWS architecture](docs/aws-architecture.md)
- [Production readiness](docs/production-readiness.md)
- [Open questions](docs/open-questions.md)

## Local Verification

```bash
uv venv .venv
uv pip install --python .venv/bin/python -r requirements.txt
.venv/bin/python -m unittest discover -s backend -p 'test_*.py'
ruff check backend
npm --prefix frontend run lint
npm --prefix frontend run build
```

Build Lambda dependencies for its Linux ARM64 runtime; do not deploy packages copied from the local macOS virtual environment.

## MVP Differentiators

- Guided procurement pathfinder instead of only open-ended chat.
- Dynamic pre-submission checklist for requesters.
- Vendor onboarding and invoice guidance.
- Source-cited answers with CSUB-specific priority over generic CSU material.
- Video transcript and timestamp support when training videos are available.
- Screenshot or walkthrough references where UI context matters.
- Escalation routing when sources are missing, conflicting, or require human judgment.
