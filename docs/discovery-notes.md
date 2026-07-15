# Discovery Notes: AI Purchasing and Procurement Assistant

Sources reviewed:
- `/Users/jaydon/Downloads/DiscoveryCall-Transcript.vtt`
- `/Users/jaydon/Downloads/SubmissionForm.pdf`
- `/Users/jaydon/Downloads/DiscoveryCall.mp4` was present, but the transcript covered the relevant discovery segment.
- `/Users/jaydon/Downloads/challenge_overview.md`

## Challenge Submission Metadata

- Challenge: AI Purchasing and Procurement Assistant.
- University: California State University, Bakersfield.
- Sponsor: Chris Diniz, Associate Vice President and Chief Information Officer.
- Sponsor email: cdiniz@csub.edu.
- Sample or synthetic data available: yes. The submission defines data broadly, including website content, PDFs, Excel files, databases, and other resources needed to solve the problem.
- Challenge context: CSU Summer AI Camp 2026, a five-day Learn by Doing hackathon in San Luis Obispo, California, with final team pitches.
- Review context: proposals are reviewed by DXHub staff from Cal Poly and AWS.
- Case study permission: with customer approval, DxHub may post short open-source case studies for selected challenges.

## Executive Summary

CSUB wants a requester-facing AI assistant that helps faculty and staff navigate CSUBUY/P2P purchasing without needing to know where every policy, guide, approval matrix, vendor step, or training video lives. The strongest customer need is not transaction automation. It is plain-language, source-grounded procedural guidance: "How do I buy this?", "Which path applies?", "What approval is needed?", "How do I process an invoice?", "How do I get a vendor or student worker into the system?", and "Where does my requisition stand?"

The assistant should reduce repeated procurement questions, lower rejected or reworked requisitions, shorten purchase cycle time, and give requesters confidence that they are following the correct CSUB-specific process. The solution should be a guidance layer grounded in campus and CSU-wide procurement materials. The initial version can include authenticated read-only status visibility if CSUB provides identity, authorization, and source-system access, but it should not write back into ServiceNow or CFS.

## Customer And Stakeholder Map

Primary sponsor:
- Chris Diniz, Associate Vice President and Chief Information Officer, California State University, Bakersfield.

Primary end users:
- Faculty and staff across CSUB divisions who initiate purchases.
- Infrequent buyers who do not know where to start.
- Requesters using CSUBUY/P2P and the P2P ServiceNow portal.

Intermediary and operational stakeholders:
- Procurement and Contracts.
- Accounts Payable.
- Department approvers.
- Supplier management.
- CSUB ITS.
- Potentially CSU-wide procurement/process owners because P2P is a CSU-wide system and standard.

Secondary users implied by the call:
- Student workers or departments requesting student worker access.
- Technology purchasers who may need Solutions Consulting review.
- Buyers who need to understand vendor onboarding, invoices, commodity codes, existing contracts, or delegation-of-authority thresholds.
- Vendors and suppliers who need registration, purchase order, invoice, payment, or onboarding guidance.
- Internal procurement/process users if the product later expands beyond the requester-facing flow.

## Problem Statement

CSUB purchasing requires users to understand multiple process decisions before submitting or following a requisition:
- Which purchase method applies.
- Which delegation-of-authority approval level applies for the amount.
- Which commodity codes are correct.
- Whether a supplier must register.
- Whether an existing contract already applies.
- Whether a technology purchase requires Solutions Consulting review.
- How to use CSUBUY/P2P and the P2P ServiceNow portal.
- How to process invoices.
- How to get access to the system, including access for student workers.

The problem is not lack of documentation. The customer repeatedly emphasized that there is a lot of documentation, training, PDFs, videos, and process material. The problem is that users do not know how to consume it quickly, how to find the relevant portion, or how to translate it into the next step for their specific situation.

The current tooling is constrained by CSU-mandated systems: CSUBUY/P2P is a Chancellor's Office standard, requisitions are handled through the P2P ServiceNow portal, and CFS remains part of the broader environment. The solution should guide users through those systems rather than replacing them.

## Direct Customer Evidence

Important customer statements from the call:
- CSU recently brought in the P2P system, and it created confusion and questions for people operating it.
- There are "tons and tons" of instructional materials, but consuming the information is overwhelming.
- Simple questions such as how to get access to the system can slow people down.
- Desired experience: a knowledgeable assistant users can ask how to get access, how student workers get access, how to process an invoice, or how to get a new vendor into the system.
- The expected answer format is summarized guidance, not forcing the user to watch a full video from the beginning.
- Screenshots and visuals are useful because some users need to see where something is in the system.
- Videos are available and were confirmed to be on YouTube; raw source access may also be possible.
- Campus-specific documents matter because CSUB may handle certain processes differently from another CSU campus.

Important statements from the submission form:
- Infrequent buyers do not know where to start.
- Current friction causes delays, rejected or reworked requisitions, off-contract spend, and repeated "how do I buy this" questions to Procurement.
- The desired assistant should be grounded in CSUB procurement policy, methods, DOA levels, supplier and contract information, and approved-software information.
- The assistant should explain the right method, approvals, supplier steps, forms, and where a requisition stands.
- Initial implementation should be a chatbot grounded in documents, returning citations, on the campus AWS environment.
- It should be guidance-only, not a write-back into ServiceNow or CFS.

## Key Customer Needs

### 1. Fast answers to procedural "how do I" questions

Users need an assistant that can answer common purchasing questions directly:
- How do I get access to CSUBUY/P2P?
- How do student workers get access?
- How do I process an invoice?
- How do I get a new vendor into the system?
- How do I buy a specific good or service?
- What form or portal do I use?
- What step comes next?

Success means the user leaves with a concrete next action, not just a link dump.

### 2. Plain-language decision guidance

Requesters need help choosing the correct procurement path. The assistant should translate policy into an understandable decision flow:
- Purchase method.
- Approval path.
- DOA threshold.
- Commodity code.
- Contract availability.
- Supplier registration requirement.
- Technology or software review requirement.

The assistant should ask clarifying questions when the answer depends on amount, purchase type, existing supplier status, technology/software category, or contract availability.

### 3. CSUB-specific answers, not generic CSU guidance

The knowledge base must distinguish between:
- CSU-wide P2P documentation.
- CSUB campus-specific policies and process variations.
- Potential duplicate or conflicting documents.

The customer explicitly noted that student access or other process details may differ by campus. A correct answer for another campus may be wrong for CSUB.

### 4. Reduced cognitive load from long training materials

Users need summarized answers from videos, PDFs, guides, and web pages. They should not have to watch a long video or search a manual to find one relevant step.

The assistant should support:
- Summaries from videos.
- Links to the exact source.
- Ideally timestamped video links when an answer comes from a walkthrough.
- Screenshots or visual references when the user's next action depends on a UI location.

### 5. Trust through citations and source grounding

Because procurement answers affect compliance, approvals, and spend, users need to know why the assistant gave an answer. Every important answer should include:
- Source citation.
- Policy or guide title.
- Date/version when available.
- Relevant excerpt or section reference.
- Clear distinction between policy-backed guidance and unresolved/needs-human-review cases.

### 6. Better requisition status visibility

The formal submission asks for requesters to understand where a requisition stands without emailing Procurement. This may require integration or data access beyond static documents.

For MVP, this should be scoped carefully:
- If live status access is not available, the assistant can explain how to check status in ServiceNow/P2P.
- If read-only status integration is available for the MVP, authenticated users can see their own requisition status and likely blockers.
- The assistant should never expose one requester's requisition status to another requester.

### 7. Procurement workload reduction

Procurement and related teams need fewer repetitive questions. The assistant should deflect high-volume, low-complexity questions while routing edge cases to the right human team.

High-value deflection categories:
- Access requests.
- Invoice processing.
- Vendor onboarding.
- Choosing purchase method.
- Required forms.
- DOA threshold lookup.
- Technology review pre-check.
- Finding existing contract/supplier information.

## Functional Requirements

Core assistant behavior:
- Answer requester questions in plain language.
- Ask clarifying questions when needed.
- Ground answers in approved source material.
- Return citations with every substantive answer.
- Prioritize CSUB-specific material over CSU-wide material when there is overlap.
- Summarize long videos and PDFs into actionable steps.
- Provide source links and, where possible, timestamped video links.
- Include screenshots or visual references when useful.
- Identify when a case requires Procurement, AP, Supplier Management, ITS, or Solutions Consulting.
- Avoid giving unsupported policy interpretation when sources are missing or conflicting.

Knowledge base ingestion:
- CSUB procurement policies.
- CSU-wide P2P documentation.
- P2P ServiceNow requester guide.
- DOA levels.
- Commodity code references.
- Supplier registration resources.
- Contract information.
- Approved-software list.
- Technology purchase / Solutions Consulting review guidance.
- Training videos, ideally YouTube links or raw MP4s.
- Screenshots from manuals and video walkthroughs.
- Common how-to questions and recurring Procurement support topics.

Administrative functions:
- Document upload or repository sync workflow.
- Duplicate document detection or source prioritization.
- Source metadata tracking: campus, document type, owner, date, version, URL.
- Content review workflow for Procurement/ITS to approve or retire sources.
- Analytics for unanswered questions and high-volume topics.

## Non-Functional Requirements

Accuracy:
- Answers must be grounded in vetted sources.
- Source conflicts should be surfaced rather than hidden.
- CSUB-specific guidance should take precedence over generic CSU material.

Usability:
- Requesters should receive concise next steps.
- The assistant should avoid overwhelming users with entire policy pages.
- Answers should be readable by infrequent buyers with no procurement background.

Governance:
- Human owner should approve the source set.
- Sensitive or outdated materials need a retirement/update process.
- The assistant should remain guidance-first for MVP, with any status visibility limited to authenticated read-only access.

Security and access:
- MVP uses a hybrid access model: public/no-auth guidance plus optional authenticated read-only status lookup.
- Only documents approved for no-auth exposure should be indexed in the public corpus.
- Role selection is self-reported for public guidance and should shape language, not grant access to restricted content.
- Internal-only, restricted, user-specific, supplier-specific, invoice-specific, and payment-specific data must stay out of public retrieval.
- Authenticated status lookup requires an approved identity provider, backend authorization, audit logging, and read-only source-system access.
- For MVP, avoid write-back to ServiceNow, P2P, or CFS.

Deployment:
- Submission form suggests campus AWS environment.
- The solution should be designed so CSUB ITS can operate or support it.

## Data And Source Notes

Available or likely available:
- Public documentation.
- CSUB documents.
- CSU-wide documents.
- PDFs.
- Videos.
- YouTube-hosted training videos.
- Screenshots in manuals.
- Raw data may be obtainable through Chris Diniz or CSU contacts.

Data issues to handle:
- Duplicative CSU-wide and CSUB-specific materials.
- Possible campus-specific differences.
- Videos may need transcripts, timestamps, and screenshot extraction.
- Some sources may be outdated or superseded.
- Supplier, contract, approved software, and requisition status data may live in separate systems and may not be document-only.

## MVP Recommendation

Build a retrieval-augmented procurement guidance assistant focused on CSUB requester questions.

MVP scope:
- Public/no-auth web assistant for general procurement guidance.
- Authenticated read-only status surface for requester and vendor progress questions if approved identity and source-system integration are available.
- Static-source chatbot over vetted CSUB and CSU procurement materials.
- Strong source citations.
- CSUB-over-CSU source prioritization.
- How-to answers for access, invoices, vendor registration, purchase method, DOA, forms, and technology review.
- Video transcript ingestion with timestamp citation where available.
- Screenshot/reference support for guides or videos where visuals clarify the next step.
- No write-back to ServiceNow or CFS.
- No unauthenticated personalized requisition, supplier, invoice, purchase-order, or payment lookup.
- No cross-user or cross-vendor status visibility.
- Authenticated status lookup is read-only and limited to records the user is authorized to view.

MVP user flow:
1. User asks a procurement question in plain language.
2. Assistant identifies the purchase/process category.
3. Assistant asks any needed clarifying questions, such as amount, item type, supplier status, software/technology flag, or existing contract.
4. Assistant returns a short answer with steps, required approvals/forms, and citations.
5. Assistant escalates to the right office when policy is ambiguous, missing, or source material says human review is required.

## Post-MVP Opportunities

Potential enhancements:
- Contract and supplier search integration.
- Approved-software lookup integration.
- Guided intake form that pre-checks purchase method, approvals, supplier status, and technology review.
- Analytics dashboard for Procurement showing top questions, deflection rate, unresolved topics, and stale-source gaps.
- Human-in-the-loop answer review for low-confidence answers.
- Role-aware guidance for faculty, staff, approvers, procurement staff, and student workers.
- CSU-wide reusable version with campus-specific overlays.

## Key Risks

Source conflict risk:
- CSU-wide and CSUB-specific documents may disagree or duplicate each other. The assistant needs source priority rules.

Policy/compliance risk:
- Incorrect procurement guidance can cause rework, delays, off-contract spend, or compliance issues. The system must cite sources and avoid overconfident unsupported answers.

Scope creep risk:
- "Where does my requisition stand?" implies live or near-live system data if the product promises an actual answer. MVP should distinguish public procedural guidance from authenticated read-only transaction status and avoid any write-back behavior.

Data freshness risk:
- Procurement policies, DOA levels, approved software, and supplier/contract information may change. The solution needs a source update process.

Video grounding risk:
- Summarizing videos is useful, but answers may need exact timestamps or screenshots to be trusted and usable.

User trust risk:
- If the chatbot gives generic or non-CSUB-specific answers, users may abandon it and continue emailing Procurement.

## Open Questions

Source access:
- What exact repository will hold the CSUB-specific documents?
- Which documents are public, internal, or restricted?
- Who owns document approval and update cadence?
- Are YouTube training videos public, unlisted, or internal?
- Can raw videos, transcripts, and screenshots be used in the knowledge base?

Policy hierarchy:
- When CSU-wide and CSUB-specific guidance conflict, what is the precedence?
- Are there official source-of-truth documents for DOA, commodity codes, supplier registration, approved software, and technology review?

System integration:
- Which status promises are required for the camp prototype: public "how to check status" guidance, authenticated requester lookup, authenticated vendor/supplier lookup, or all three?
- Is ServiceNow/P2P API access available?
- Is CFS access needed or explicitly out of scope?
- Is supplier/contract data available as documents, spreadsheets, database exports, or live systems?

Users and access:
- Who can use the assistant: only CSUB employees, all CSU users, student workers, or public users?
- Should answers change based on user role or department?
- Are student worker access rules sensitive or role-dependent?
- Which identity provider and authorization rules should control requester, vendor, and internal status access?

Success measurement:
- What is the current baseline for requisition cycle time?
- What percentage of requisitions are rejected or reworked today?
- How many Procurement guidance requests arrive per week/month?
- What is the current supplier registration turnaround time?
- How will requester satisfaction be measured?

## Suggested Success Metrics

From the submission form:
- Requisition cycle time.
- Rejected or reworked requisition rate.
- Share of on-contract spend.
- Supplier registration time.
- Volume of purchasing guidance requests.
- Requester satisfaction.

Additional useful metrics:
- Answer helpfulness rating.
- Percentage of answers with accepted citations.
- Number of questions resolved without human escalation.
- Top unresolved topics.
- Source coverage gaps.
- Time from policy update to assistant knowledge refresh.
- Percentage of queries requiring clarifying questions.

## Product Positioning

Best concise framing:

An AI procurement guide for CSUB requesters that turns CSUBUY/P2P policies, guides, videos, and campus-specific rules into cited, step-by-step purchasing guidance.

What it is:
- A requester-facing guidance assistant.
- A source-grounded search and explanation layer.
- An authenticated read-only status surface if CSUB approves identity and source-system access.
- A way to reduce repetitive procurement questions.
- A decision-support tool for the correct purchasing path.

What it is not for MVP:
- A transaction engine.
- A replacement for Procurement.
- A write-back integration into ServiceNow or CFS.
- A public lookup tool for personalized requisition, supplier, invoice, purchase-order, or payment records.
- A generic CSU chatbot that ignores campus-specific rules.

## Initial Build Plan

1. Collect source materials.
   - CSUB procurement PDFs and web pages.
   - CSU-wide P2P docs.
   - P2P ServiceNow requester guide.
   - DOA matrix.
   - Supplier registration resources.
   - Approved software list.
   - Technology review/Solutions Consulting guidance.
   - YouTube training video links and transcripts.

2. Normalize and tag sources.
   - Tag by campus, source owner, document type, date, policy area, and priority.
   - Mark CSUB-specific sources as higher priority than CSU-wide defaults.
   - Detect duplicate or overlapping documents.

3. Build retrieval and answer policy.
   - Require citations.
   - Prefer CSUB-specific sources.
   - Ask clarifying questions when amount, category, supplier status, or technology status is missing.
   - Escalate when sources conflict or are missing.

4. Implement high-value workflows.
   - Access to P2P.
   - Student worker access.
   - Invoice processing.
   - New vendor onboarding.
   - Authenticated read-only requisition/vendor status lookup if approved source-system access is available.
   - Purchase method selection.
   - DOA approval guidance.
   - Technology/software purchase review.

5. Add video support.
   - Ingest transcripts.
   - Preserve timestamps.
   - Link to the relevant YouTube timestamp.
   - Capture or reference screenshots when the user needs visual guidance.

6. Test with real requester questions.
   - Use Procurement's most common incoming questions.
   - Verify each answer with Procurement/ITS.
   - Track gaps, missing sources, and ambiguous rules.

## Questions To Ask Chris / CSUB Next

- Can you provide the CSUB-specific document repository and confirm which files are authoritative?
- Can you provide YouTube links or raw files for the P2P training videos?
- Who should approve source priority when CSUB and CSU-wide documents overlap?
- Which authenticated status lookup, if any, should the prototype support for requesters and vendors?
- Can we get examples of the top 20 repeated "how do I buy this" questions Procurement receives?
- Can we get sample rejected/reworked requisition scenarios to test whether the assistant prevents common mistakes?
- Is there a current approved-software list and technology review checklist we can ingest?
- Are supplier registration and contract lookup available as static exports for MVP?
- What identity provider and authorization rules should protect personalized requester/vendor status?
- What AWS environment constraints or services should the team assume?
