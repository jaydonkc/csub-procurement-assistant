# AWS Architecture: MVP Baseline

Status: AWS content, retrieval, production agent behavior, public API protection, operations plumbing, and the public frontend are provisioned and verified as of July 15, 2026. A CSUB-approved custom domain remains optional launch work.

## Scope

- AWS account: `335010339891`
- Region: `us-west-2`
- AWS CLI profile: `summercamp`
- Access model: AWS IAM Identity Center / SSO session; no raw or long-lived access keys
- Product direction: public, no-auth procurement guidance

Public/no-auth describes the current user experience. It does not make the S3 bucket or Bedrock resources public. The current Knowledge Base contains mixed-scope material, including internal/admin guidance, so the Lambda agent enforces metadata, path, intent, and response-level controls before returning public guidance.

## Live Resources

### Source bucket

- Bucket: `csub-pa-mvp-source-335010339891-us-west-2`
- Purpose: canonical source storage for procurement documents and timestamped transcripts
- Region: `us-west-2`
- Public access: blocked
- Object ownership: bucket-owner enforced
- Default encryption: SSE-S3
- Versioning: enabled
- Lifecycle: noncurrent versions expire after 90 days; incomplete multipart uploads abort after 7 days
- Transport: bucket policy denies non-TLS requests

The Bedrock source boundary is `approved/`. The separate bucket `dxhub-camp-2026-csub-purchasing-procurement` contains project instructions and is not a retrieval source. It was not modified during this setup.

Current layout:

- `approved/documents/` - 63 PDF/DOCX sources, preserving the `CSUBuyP2P` folder hierarchy
- `approved/transcripts/` - 17 timestamped VTT transcripts retained as the transcript source of truth
- `approved/transcript-segments/` - 300 derived, overlapping timestamped text segments used for video retrieval
- `media/videos/` - 17 original MP4 sources; stored but not indexed directly
- `transcription-output/raw/` - Amazon Transcribe job outputs retained for traceability
- `incoming/` - future staging area; never directly indexed
- `retired/` - future superseded content; never directly indexed

The canonical corpus was replaced with all 80 real source files in the local `CSUBuyP2P` collection: 63 documents and 17 videos. The macOS `.DS_Store` artifact was excluded. The local collection is ignored by Git and is not part of the repository.

The earlier 16-document corpus imported from `customer-dataaisummercamp` was deleted. Future source changes should be managed in `csub-pa-mvp-source-335010339891-us-west-2`.

### Retrieval

- Knowledge Base: `csub-pa-mvp-kb-chunked`
- Knowledge Base ID: `3MMHDI5IDU`
- Type: Amazon Bedrock managed Knowledge Base
- Embeddings: Amazon Titan Text Embeddings V2, 1,024 dimensions
- Service role: `AmazonBedrockExecutionRoleForKnowledgeBase_csub_pa_mvp`
- Procedural data source: `csub-pa-mvp-procedural-450` (`NT1NI8NZVE`) - Smart Parsing, fixed 450-token maximum, 15% overlap
- Long-form data source: `csub-pa-mvp-longform-600` (`N1UU0ZTSUI`) - Smart Parsing, fixed 600-token maximum, 15% overlap
- Transcript data source: `csub-pa-mvp-transcript-segments` (`RHK7NA8GPY`) - pre-segmented atomic text with no additional Bedrock chunking

The managed Knowledge Base was selected because it keeps S3 as the source of truth while Bedrock manages vector storage, indexing, and retrieval. A selectable embedding model is required because the service-managed embedding configuration does not permit a custom chunking configuration. The account's organization policy explicitly denies S3 Vectors and prevents Bedrock service roles from listing S3 buckets. Therefore, sources are synchronized through Bedrock's supported custom connector using the authenticated `summercamp` operator session instead of a native S3 crawler. A native S3 crawler should not be assumed available unless the campus organization policy changes.

The Bedrock role can invoke Titan Text Embeddings V2 and has `s3:GetObject` only for `approved/documents/*` and `approved/transcript-segments/*` in the canonical source bucket. It has no bucket-list permission, no direct access to the canonical VTTs under `approved/transcripts/`, no access to `media/videos/`, and no access to the DXHub instruction bucket.

The previous default-chunked Knowledge Base `KZWZQVCCJW` and data source `UEPVWR8BSS` were retired after the replacement passed retrieval and end-to-end tests. No canonical S3 source objects were removed during that retirement.

### Agent runtime

- Lambda function: `csub-pa-mvp-chat-test`
- Production alias: `production` -> immutable version `10`
- Production API: `https://w0vfga8dil.execute-api.us-west-2.amazonaws.com/prod`
- API routes: `POST /v1/chat` and `GET /v1/health`
- Legacy Lambda URLs: retained with `AuthType=AWS_IAM`; no anonymous bypass
- Immediate predecessors: version `9` retains document/video source links without conditional retrieval; version `8` retains conditional retrieval and video playback
- Runtime: Python 3.13 on ARM64, 256 MB memory, 30-second timeout
- Generation model: US Anthropic Claude Sonnet 4.6 inference profile
- Retrieval router and grounding validator: US Anthropic Claude Haiku 4.5 inference profile
- Public access: API Gateway REST API with `AuthorizationType=NONE`, protected by WAF and throttling
- Execution role: `AmazonBedrockExecutionRoleForLambda_csub_pa_mvp_chat_test`
- Logs: Lambda, API Gateway, and blocked-request WAF logs retained for 30 days
- Repository source: `backend/lambda_function.py`
- Policy tests: `backend/test_lambda_function.py`

The function supports a versioned JSON chat contract and health endpoint. It retrieves up to 12 candidates, keeps at most two chunks from any source, and passes at most eight excerpts into generation. Managed reranking is disabled because it is unavailable with a custom embedding model. Returned public document and video sources can include private presigned links that expire after 15 minutes; videos retain the retrieved transcript timestamp.

The development branch now keeps `backend/lambda_function.py` as a thin AWS adapter and uses pinned Pydantic AI `2.10.0` for Bedrock model orchestration. The refactor is not deployed to the immutable `production` alias until the full acceptance suite passes against a newly published version.

Requests first pass through deterministic gates that block submit/approve/edit actions, personalized live lookups, PII-access requests, internal/admin procedures, and prompt-injection attempts. If a gate does not decide the turn, Haiku returns a structured `conversation`, `clarification`, `out_of_scope`, or `retrieve` decision. Only `retrieve` calls the Knowledge Base; contextual follow-ups can be rewritten into standalone search queries. Non-retrieval replies are bounded to prevent unsupported facts, and malformed, unavailable, or uncertain router output defaults to retrieval. Ambiguous software and purchase requests still receive guided intake questions. High-frequency workflows use source-verified response templates; remaining answers use Sonnet generation, sentence/line citation checks, Haiku entailment validation, and one constrained repair attempt before failing closed.

The execution role can call `bedrock:Retrieve` on `3MMHDI5IDU`, invoke the production Sonnet and Haiku inference profiles, invoke Nova Lite for the oldest rollback version, write this function's CloudWatch logs, and publish X-Ray telemetry. For cited-source links it has `s3:GetObject` on `approved/documents/*` and an exact allowlist of 11 public training-video objects; it has no bucket-list permission, no access to the DXHub instruction bucket, and no procurement-system write permissions. The application signs only sources that already passed the public metadata and path filters.

### API protection and observability

- CloudFormation stack: `csub-pa-production-backend`
- Regional REST API: `w0vfga8dil`, stage `prod`
- Request validation: Draft 4 JSON schema for message, role, and bounded history
- Stage throttling: 5 requests/second, burst 10
- Regional WAF: body size over 64,000 bytes returns `413`; more than 300 requests per source IP in five minutes returns `429`
- Access logging: route, status, latency, response length, integration status, and request ID only; request/response data tracing is disabled
- WAF logging: blocked requests only; sampled requests disabled
- Tracing: API Gateway and Lambda X-Ray enabled
- Dashboard: `csub-pa-production`
- Alert topic: `csub-pa-prod-alerts`; no subscriber is configured because no recipient was approved
- Alarms: Lambda errors, throttles, p95 duration, API 5xx, API 4xx spike, and caught application failures
- Infrastructure: `infra/backend.yaml`; deployment: `scripts/deploy_backend.sh`

Amazon Bedrock Agents were evaluated but are not used. The Agent runtime injects a vector-search configuration that is incompatible with this managed Knowledge Base, which requires `managedSearchConfiguration`. The temporary Agent, alias, and Agent execution role were removed after this was verified.

### Frontend hosting

- Public URL: `https://d3s79ehfkh7xjx.cloudfront.net`
- CloudFormation stack: `csub-pa-production-frontend`
- CloudFront distribution: `E1J3M2Y5JS6LMM`
- Private origin bucket: `csub-pa-production-frontend-335010339891-us-west-2`
- Public bucket access: fully blocked; CloudFront uses signed origin access control
- Transport: HTTPS redirect with HTTP/2 and HTTP/3 enabled
- Browser controls: CSP, HSTS, frame denial, content-type protection, referrer policy, and permissions policy
- Caching: hashed assets are immutable for one year; `index.html` is not cached and deployments invalidate CloudFront
- Infrastructure: `infra/frontend.yaml`; deployment: `scripts/deploy_frontend.sh`

The deployment script verifies account `335010339891`, validates the template, runs lint and build checks, injects the production API URL, uploads the build, invalidates CloudFront, and smoke-tests both the page and backend health endpoint. No raw AWS keys or public S3 website endpoint are used.

## Current Verification Status

Last verified July 15, 2026:

- Knowledge Base status: `ACTIVE`
- All three data source statuses: `AVAILABLE`
- Canonical source corpus: 63 documents and 17 original videos
- Video processing: 17 Amazon Transcribe jobs `COMPLETED`, 0 failed
- Retrieval representations: 47 procedural documents, 16 long-form documents, and 300 timestamped segments covering all 17 VTT transcripts
- Document state: all 63 report `TEXT_INDEXED` or `INDEXED` when checked directly and are text-searchable
- Transcript state: all 300 derived segments report `INDEXED`
- A 12-scenario guided retrieval comparison covered supplier onboarding, invitations, receiving, requisition search, default addresses, change requests, support tickets, payment terms, punchout shopping, fiscal year end, voucher status, and supplier status.
- The replacement returned an expected source in 12/12 scenarios versus 11/12, improved mean expected-source rank from 2.33 to 1.25, improved procedural-term coverage from 88.9% to 94.5%, reduced duplicate context chunks from 54 to 31, and returned useful timestamps in 5/5 video-oriented scenarios versus 2/5.
- Both configurations returned zero `access_scope=internal` sources under the public-test filter.
- API health identifies immutable Lambda version `10`; both direct Lambda URLs reject anonymous requests with `403`.
- The CloudFront distribution reports `Deployed`, the public page returns `200`, and the S3 policy status reports `IsPublic: false` with all four public-access blocks enabled.
- The deployed page returns the configured CSP, HSTS, frame, content-type, referrer, and permissions headers; versioned assets return the one-year immutable cache policy while `index.html` returns `no-cache,no-store,must-revalidate`.
- Browser preflight from the CloudFront origin returns `204`, and a post-deployment guided voucher-status request returned a cited public source through the production API.
- The final 36-scenario raw-retrieval suite returned 34/36 exact expected-source hits, 93.1% mean procedural-term coverage, 0 internal-source leaks, 3/3 timestamp passes, and 1.783-second p95 retrieval latency.
- The final 13-scenario guided end-to-end suite through API Gateway and WAF returned 13/13 HTTP successes, 13/13 expected-source hits, 13/13 valid citation sets, 0 internal-source leaks, 0 duplicate source cards, 3/3 timestamp passes, and 9.215-second p95 latency.
- All 8 boundary cases passed: PII refusal, live lookup, submit action, approve action, prompt injection, unrelated topic, ambiguous software clarification, and self-reported internal-role access.
- Post-version-10 conditional-routing checks passed nine live cases: four conversational/clarification/out-of-scope turns returned no sources, substantive procurement and contextual follow-up turns retrieved, and a direct transaction action remained blocked before retrieval.
- A deployed-browser `hi` check returned the natural greeting with no source section. Cited PDF and MP4 URLs both returned HTTP `206` with `application/pdf` and `video/mp4`, respectively.
- The raw retrieval exceptions remain visible for evaluation: supplier-search and Marketplace end-user exact-source misses, plus partial heuristic term coverage for the forms scenario. Guided end-to-end behavior passed because routing and source-verified workflows are evaluated as the product surface.

Some documents may report `TEXT_INDEXED` while optional image extraction continues; text retrieval is already available in that state. Deletion tombstones from the earlier imported corpus belonged only to the retired Knowledge Base. For example, `approved/documents/VPAT_2.5_Nov2023.pdf` remains intentionally absent from both S3 and the `CSUBuyP2P` collection.

## Content And Access Boundary

- The current Knowledge Base covers every real file from `CSUBuyP2P` by explicit project direction: documents are indexed directly and videos are represented by their complete timestamped transcript content.
- This includes supplier material labeled internal, campus-admin guidance, and the sensitive-PII access guide.
- Internal/admin/PII-related sources are tagged with `access_scope=internal` metadata where identified. This includes the admin collection, approval collection, combined CSUB Buy files, campus-administrator marketplace training, the internal supplier FAQ, and explicit PII-access guidance.
- The custom connector has ACL enforcement disabled. Metadata tags do not prevent retrieval by themselves.
- The public function filters `access_scope=internal`, explicitly excludes admin and approval paths as defense in depth, refuses PII-access requests before retrieval, and treats self-reported roles as wording context only.
- Production should still separate internal sources into a restricted Knowledge Base or add authenticated authorization rather than relying only on application filters.
- Synchronize only objects under `approved/` through the custom connector.
- Keep raw videos under `media/videos/`, outside the indexed prefixes.
- Convert videos into timestamped VTT transcripts before placing them under `approved/transcripts/`.
- Treat requester, vendor, and internal-staff roles as guidance context, not authorization.
- Do not add personalized supplier, invoice, payment, requester, or transaction records to this Knowledge Base.

## Source Synchronization

The custom connector does not automatically crawl S3. Until a different ingestion path is approved, source updates should follow this operating sequence:

1. Place candidate material under `incoming/`.
2. Review it for authority, currency, duplication, access scope, and intended audience.
3. Promote approved documents into `approved/documents/`; store original videos under `media/videos/` and promote their timestamped VTT output into `approved/transcripts/`.
4. Submit documents of five pages or fewer to the procedural data source and longer manuals/decks to the long-form data source. Treat the collection-level `CSUB Buy` overview as long-form.
5. Segment each approved VTT into sentence-aligned windows of no more than 90 seconds or approximately 300 words, retaining about 10 seconds of overlap and explicit start/end timestamps. Store the derived text under `approved/transcript-segments/` and submit each segment to the atomic transcript data source.
6. Use an authenticated `summercamp` session for direct ingestion. The Bedrock role reads only approved document and derived-segment prefixes.
7. Confirm `TEXT_INDEXED` or `INDEXED` status, then run a guided retrieval-and-citation check before relying on the source.
8. When retiring or replacing content, update the canonical S3 corpus, derived transcript segments, and the corresponding custom-connector document state.

The owner of this approval and synchronization process is still an open governance decision. Event-driven or scheduled synchronization remains deferred.

## Deferred Beyond The Deployed MVP

- Optional CSUB-approved custom domain and ACM certificate for CloudFront
- Alert topic recipient confirmation
- Production analytics and feedback storage
- Authentication for any future restricted or personalized workflows
- Physical separation of internal content into a restricted Knowledge Base
- Automated video transcription and ingestion pipeline; the current 17-video batch was operator-run
- Scheduled or event-driven Knowledge Base synchronization

No AWS Budgets or Cost Anomaly Detection resources are part of this baseline.
