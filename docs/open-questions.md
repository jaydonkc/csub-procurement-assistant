# Open Questions

## Product Scope

- Should the first prototype include both free-form chat and guided pathfinder flows?
- Which workflows are mandatory for the first demo: requester buying path, vendor onboarding, invoice help, access help, or technology/software review?
- Should requisition status be limited to "how to check status" guidance, or should live read-only status lookup be pursued later?
- Should the assistant present itself as a standalone CSUB Procurement Assistant, or should it be related to Rowdy only by integration/linking?

## Users And Roles

- Which user roles should appear in the first screen: requester, vendor, internal staff, or all three?
- Are vendors allowed to access the same assistant as CSUB employees?
- Should answers change based on self-reported role, department, or campus affiliation?
- Are student worker access rules safe to expose in a no-auth public assistant?

## Source Access

- Which CSUB procurement documents are authoritative?
- Which CSU-wide P2P documents should be indexed?
- When CSUB and CSU-wide guidance differ, which source wins?
- Are training videos public, unlisted, or internal?
- Are transcripts already available for the training videos?
- Can screenshots from manuals or videos be used in assistant answers?

## Governance

- Who approves documents before they enter the knowledge base?
- Who owns source updates after the prototype?
- How often do DOA levels, supplier registration steps, approved software lists, and procurement policies change?
- Which documents should never be cited or exposed to vendors?
- What is the escalation policy when sources are missing or conflicting?

## AWS And Implementation

- Resolved: the prototype uses AWS account `335010339891` in `us-west-2`, accessed through CLI profile `summercamp`.
- Resolved for content and retrieval: private Amazon S3 source storage plus an Amazon Bedrock managed Knowledge Base.
- Resolved for the current account policy: S3 Vectors and the native Bedrock S3 crawler path are unavailable, so approved objects are submitted through a managed custom connector using an authenticated `summercamp` operator session.
- Resolved for the current corpus: all 80 real files from `CSUBuyP2P` are in canonical S3 storage; 63 documents are text-indexed through source-aware fixed-size chunking and all 17 videos are covered by 300 indexed timestamped segments derived from the canonical VTT transcripts.
- Resolved for replacement status: the 16 `NOT_FOUND` identifiers were deletion tombstones in the retired Knowledge Base, not failed replacement uploads; they are not part of the active chunked index.
- Resolved for the production agent runtime: Lambda version `2` is frozen behind the `production` alias, with Sonnet 4.6 generation, Haiku 4.5 citation validation, and version `1` retained for rollback.
- Resolved for the public boundary: deterministic gates block system actions, live lookups, internal/admin procedures, PII access, prompt injection, and explicit out-of-scope topics; self-reported role is not authorization.
- Resolved for guided evaluation: 13/13 end-to-end scenarios, 8/8 boundary cases, and 3/3 video timestamp checks passed with no internal-source leakage and 8.193-second p95 end-to-end latency.
- Still open for campus production hosting: frontend integration, custom domain/CDN, WAF and rate limiting, analytics, feedback storage, and infrastructure-as-code.
- Should internal/admin sources move to a separate restricted Knowledge Base before production launch?
- Who owns approving and synchronizing future S3 source changes into the custom connector?
- Are there data retention or logging restrictions for user questions?
- Which source types are approved for no-auth public exposure?
- What authentication model would be required in a future phase for restricted sources or personalized status lookup?

## Evaluation

- What are the top 20 Procurement questions currently received by email or ticket?
- What are the most common causes of rejected or reworked requisitions?
- What vendor onboarding questions happen most often?
- What invoice or payment questions do vendors ask most often?
- What baseline metrics exist for cycle time, rework rate, on-contract spend, supplier registration time, and requester satisfaction?
