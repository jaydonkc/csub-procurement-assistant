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
- No requisition submission.
- No purchase approval.
- No write-back into ServiceNow.
- No write-back into CFS.
- No supplier registration submission.
- No unsupported policy advice without source grounding.

## Expected Architecture Direction

The project is expected to use AWS for a significant part of the implementation. Final AWS service choices are still open.

Likely implementation areas:
- Document storage and ingestion.
- Retrieval index / vector search.
- Chat and orchestration API.
- Authentication and authorization.
- Logging, analytics, and feedback.
- Admin tools for source management.
- Static or server-rendered web frontend.

The repository should keep the product architecture modular enough to support:
- A standalone full-page web assistant first.
- An embeddable widget later if CSUB wants to place it inside existing procurement pages.
- Separate role flows for requesters, vendors, and internal staff.
- Future read-only integrations with ServiceNow, P2P, supplier, contract, or approved-software systems.

## Documentation

- [Discovery notes](docs/discovery-notes.md)
- [Feature specification](docs/feature-spec.md)
- [Open questions](docs/open-questions.md)

## MVP Differentiators

- Guided procurement pathfinder instead of only open-ended chat.
- Dynamic pre-submission checklist for requesters.
- Vendor onboarding and invoice guidance.
- Source-cited answers with CSUB-specific priority over generic CSU material.
- Video transcript and timestamp support when training videos are available.
- Screenshot or walkthrough references where UI context matters.
- Escalation routing when sources are missing, conflicting, or require human judgment.

