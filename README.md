# CSUB Procurement Assistant

A standalone, role-aware guided procurement assistant for California State University, Bakersfield.

The product helps CSUB requesters, vendors, and internal procurement stakeholders navigate CSUBUY/P2P, supplier onboarding, invoice questions, purchasing approvals, contract checks, commodity code guidance, technology review, and related procurement workflows.

This repository currently contains discovery notes and product specifications only. Implementation will be added after the product scope, source access, AWS architecture, and prototype boundaries are confirmed.

## Product Positioning

This is not just an FAQ chatbot. The intended product is a guided procurement assistant that combines RAG with structured intake flows.

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

The MVP AWS baseline is now established in account `335010339891`, region `us-west-2`. Amazon S3 is the source of truth for approved content, and an Amazon Bedrock managed Knowledge Base provides retrieval and citations. Application hosting and orchestration services remain intentionally unselected because the application itself has not been implemented.

Live status as of July 14, 2026: the Knowledge Base is active and the old 16-document corpus has been replaced with all 80 real source files from `CSUBuyP2P`. All 63 PDF/DOCX files are text-indexed. All 17 MP4 files are stored in S3, and their 17 timestamped VTT transcripts are indexed and retrieval-tested. Because campus organization policy blocks the native S3 paths required here, the current baseline uses a managed custom connector and an explicit operator synchronization step.

The current Knowledge Base intentionally includes internal/admin and sensitive-PII-access guidance from the supplied collection. Those sources carry `access_scope=internal` metadata, but the connector does not enforce ACLs. A public/no-auth application must enforce source filtering or use a separate restricted corpus before launch.

See [AWS architecture](docs/aws-architecture.md) for the live resource inventory, ingestion boundary, and deferred decisions.

Likely implementation areas:
- Document storage and ingestion.
- Retrieval index / vector search.
- Chat and orchestration API.
- Source access-level tagging.
- Logging, analytics, and feedback.
- Admin tools for source management.
- Static or server-rendered web frontend.

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
- [Open questions](docs/open-questions.md)

## MVP Differentiators

- Guided procurement pathfinder instead of only open-ended chat.
- Dynamic pre-submission checklist for requesters.
- Vendor onboarding and invoice guidance.
- Source-cited answers with CSUB-specific priority over generic CSU material.
- Video transcript and timestamp support when training videos are available.
- Screenshot or walkthrough references where UI context matters.
- Escalation routing when sources are missing, conflicting, or require human judgment.
