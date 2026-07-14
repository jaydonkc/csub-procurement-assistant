# Open Questions

## Product Scope

- Should the first prototype include both free-form chat and guided pathfinder flows?
- Which workflows are mandatory for the first demo: requester buying path, vendor onboarding, invoice help, access help, or technology/software review?
- Should requisition status be limited to "how to check status" guidance, or should live read-only status lookup be pursued later?
- Should the assistant present itself as a standalone CSUB Procurement Assistant, or should it be related to Rowdy only by integration/linking?

## Users And Roles

- Which user roles should appear in the first screen: requester, vendor, internal staff, or all three?
- Are vendors allowed to access the same assistant as CSUB employees?
- Should answers change based on authentication, role, department, or campus affiliation?
- Are student worker access rules safe to expose to all users, or only authenticated CSUB users?

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

- Which AWS account or campus environment will host the prototype?
- Are there preferred AWS services for retrieval, chat orchestration, authentication, storage, logging, or deployment?
- Are Bedrock, OpenSearch, S3, Lambda, ECS, App Runner, or Cognito approved for this project?
- Are there data retention or logging restrictions for user questions?
- Will the prototype need SSO or can it start unauthenticated for demo purposes?

## Evaluation

- What are the top 20 Procurement questions currently received by email or ticket?
- What are the most common causes of rejected or reworked requisitions?
- What vendor onboarding questions happen most often?
- What invoice or payment questions do vendors ask most often?
- What baseline metrics exist for cycle time, rework rate, on-contract spend, supplier registration time, and requester satisfaction?

