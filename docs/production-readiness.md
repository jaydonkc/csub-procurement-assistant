# Agent Production Readiness

Status: production agent behavior verified July 14, 2026. This status covers the guidance agent and its AWS runtime. It does not claim that custom campus web hosting, WAF, analytics, or authenticated internal workflows are complete.

## Frozen Runtime

- Lambda: `csub-pa-mvp-chat-test`
- Alias: `production`
- Version: `2`
- Production URL: `https://etwxpbmxee2s6vniis3sgez5m40vorpg.lambda-url.us-west-2.on.aws/`
- Rollback: version `1`
- Knowledge Base: `3MMHDI5IDU`
- Generation: US Anthropic Claude Sonnet 4.6
- Validation: US Anthropic Claude Haiku 4.5

The mutable `$LATEST` URL is retained for pre-release testing. Production clients should use the alias URL so later development cannot silently change deployed behavior.

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

Final post-deployment run:

- Raw retrieval: 34/36 exact expected-source hits, 93.1% mean term coverage, 0 internal leaks, 3/3 timestamp checks, 1.311-second p95.
- Guided end to end: 13/13 HTTP successes, 13/13 expected-source hits, 13/13 valid citation sets, 0 internal leaks, 0 duplicate source cards, 3/3 timestamp checks, 8.193-second p95.
- Boundary and adversarial behavior: 8/8 passed.
- Local policy suite: 53/53 passed.

The raw retrieval evaluation still records exact-source misses for supplier search and Marketplace end-user training, plus partial term coverage for the forms scenario. These are not hidden: the guided product suite passes because query routing, public-source enforcement, clarification, and source-verified workflows are part of the product being evaluated.

## Remaining Launch Work

- Put the final standalone frontend behind an approved domain/CDN and connect it to the production alias.
- Add WAF/rate limiting and an abuse-response policy for broad public launch.
- Approve retention and analytics rules before storing user questions or feedback.
- Physically separate restricted content or add authentication before enabling any internal workflow.
- Add infrastructure-as-code and an automated, governed source-synchronization pipeline.
