# Feature Specification: AI Purchasing and Procurement Assistant

## Product Definition

The solution is a standalone, role-aware RAG chatbot and guided procurement assistant for CSUB requesters, vendors, and internal support stakeholders. It helps users determine the correct purchasing path in CSUBUY/P2P, understand required approvals and supplier steps, find the right forms, and navigate procurement guidance without reading long PDFs or watching full training videos.

The MVP is a guidance layer only. It does not submit requisitions, modify ServiceNow, write to CFS, approve purchases, or replace Procurement staff.

## Primary Users

- Faculty and staff who initiate purchases.
- Infrequent requesters who do not know where to start.
- Department staff supporting purchasing workflows.
- Vendors and suppliers who need registration, purchase order, invoice, payment, and onboarding guidance.
- Procurement, AP, Supplier Management, ITS, and Solutions Consulting as support and escalation stakeholders.

## MVP Feature Set

### F1. Plain-Language Procurement Chat

Priority: Must have

User need:
Requesters need to ask procurement questions naturally instead of searching policy pages, PDFs, or videos.

Example queries:
- "How do I buy software?"
- "How do I add a new vendor?"
- "How do I get access to CSUBUY?"
- "How do student workers get access?"
- "How do I process an invoice?"
- "What approval do I need for a $7,500 purchase?"

Behavior:
- Accept free-text questions.
- Identify the likely procurement topic.
- Retrieve relevant CSUB and CSU-wide source material.
- Produce a concise answer in plain language.
- Include next steps, forms, approvals, and source citations when available.
- Ask a clarifying question when the answer depends on missing information.

Output:
- Short answer.
- Step-by-step guidance.
- Required forms or systems.
- Relevant office or escalation path.
- Citations to source documents.

Acceptance criteria:
- Given a common procurement question, the assistant returns an actionable answer in under 10 seconds.
- Every policy-based answer includes at least one citation.
- The assistant does not answer from unsupported policy assumptions when no source is found.

### F1A. Role Selection And Role-Aware Guidance

Priority: Must have

User need:
Requesters, vendors, and internal staff need different language, source exposure, and escalation paths.

Roles:
- Requester: CSUB faculty, staff, department admin, or student worker support context.
- Vendor: supplier or vendor trying to register, understand purchase orders, submit invoices, or resolve payment questions.
- Internal staff: Procurement, Accounts Payable, Supplier Management, ITS, Solutions Consulting, or approver support.

Behavior:
- Let the user identify their role at the start or infer role from the question.
- Use role-specific wording and escalation paths.
- Avoid exposing internal-only documents to vendors unless approved.
- Keep requester, vendor, and internal process flows separate enough to extend independently.

Output:
- Role-aware answer.
- Role-specific next steps.
- Role-specific escalation target.
- Citations appropriate for that role.

Acceptance criteria:
- A vendor registration question receives vendor-facing guidance, not requester-facing internal purchasing instructions.
- A requester buying question receives purchase path and checklist guidance.
- Internal-only or restricted sources are not exposed to vendors unless marked safe.

### F2. Source-Grounded RAG Retrieval

Priority: Must have

User need:
Procurement answers must be trustworthy and traceable.

Data sources:
- CSUB procurement policies.
- CSU-wide procurement/P2P documentation.
- DOA levels.
- Commodity code references.
- Supplier registration resources.
- Contract guidance.
- Approved-software list.
- P2P ServiceNow requester guide.
- Training video transcripts.
- Screenshots or walkthrough images.

Behavior:
- Index approved source documents.
- Retrieve relevant chunks for each query.
- Rank CSUB-specific material above CSU-wide material when both apply.
- Return document title, section/page, URL, and date/version when available.
- Detect missing or low-confidence retrieval.

Output:
- Answer grounded in retrieved text.
- Citation list.
- Confidence or source coverage signal for internal use.

Acceptance criteria:
- Each answer shows the source document used.
- CSUB-specific documents are preferred over CSU-wide documents for campus-specific procedures.
- If sources conflict, the assistant surfaces the conflict and recommends contacting the responsible office.

### F3. Guided Procurement Pathfinder

Priority: Must have / standout feature

User need:
Many users do not know what question to ask. They need the assistant to guide them through the decision.

Trigger:
- User asks broad questions like "How do I buy this?", "I need to purchase equipment", or "Where do I start?"

Required intake questions:
- What are you buying?
- Estimated dollar amount?
- Is it software, hardware, cloud, data, or other technology?
- Is the supplier already registered?
- Do you know whether a contract already exists?
- Is this a reimbursement, invoice, requisition, or new purchase?
- Is the requester faculty, staff, student worker, or department admin?

Behavior:
- Ask only the minimum necessary clarifying questions.
- Build a recommended path from the answers.
- Identify purchase method, approval needs, supplier steps, forms, and technology review needs.
- Explain why each requirement applies with citations.

Output:
- Recommended purchasing path.
- Missing information.
- Required approvals.
- Required forms.
- Supplier/contract steps.
- Technology review flag.
- Next action.

Acceptance criteria:
- For a realistic purchase scenario, the assistant produces a checklist and path recommendation.
- The assistant does not require users to know procurement terminology before using it.
- If the user lacks key information, the assistant identifies exactly what is missing.

### F4. Dynamic Pre-Submission Checklist

Priority: Must have / standout feature

User need:
Requesters need to know what they need before submitting a requisition so they avoid rework.

Inputs:
- Purchase description.
- Estimated amount.
- Supplier status.
- Technology/software flag.
- Contract status if known.
- Invoice/requisition/new purchase context.

Behavior:
- Generate a purchase-specific checklist.
- Separate required items from optional/unknown items.
- Mark items that require human confirmation.
- Cite the rule or guide behind each checklist item.

Output example:
- Purchase method: P2P requisition.
- DOA approval: required at X threshold.
- Supplier: registration needed.
- Contract: check existing contract before proceeding.
- Technology review: required if software/cloud/data involved.
- Forms: list required forms.
- Next step: submit through P2P ServiceNow requester flow.

Acceptance criteria:
- Checklist is specific to the user's described purchase.
- Checklist includes citations for each policy-driven requirement.
- Checklist clearly flags unknowns and blockers.

### F5. FAQ And Common Questions Page

Priority: Should have

User need:
Users need fast access to common answers without typing full questions.

Content sources:
- Top Procurement questions.
- High-frequency chatbot queries.
- Known rework/rejection causes.
- Access, vendor registration, invoices, approvals, software purchases, payment questions, and forms.

Behavior:
- Display common question categories.
- Let users click a question to open a sourced answer.
- Keep FAQ entries backed by the same RAG source system.
- Allow admins to promote recurring chatbot questions into FAQ entries.

Output:
- Category list.
- Common questions.
- Cited answers.
- Links to related guided workflows.

Acceptance criteria:
- FAQ answers use the same citation standard as chatbot answers.
- FAQ content can be updated without code changes.
- FAQ does not become the only experience; it supports the guided assistant.

### F6. Video Transcript And Timestamp Support

Priority: Should have / demo differentiator

User need:
Users do not want to watch a full training video to find one answer.

Data sources:
- YouTube training videos.
- Raw MP4s if available.
- Video transcripts.
- Manually or automatically generated timestamps.

Behavior:
- Ingest video transcripts.
- Retrieve transcript segments relevant to a question.
- Answer in summary form.
- Link to the exact YouTube timestamp when available.

Output:
- Summarized answer.
- Training video title.
- Timestamp link.
- Transcript citation.

Acceptance criteria:
- For a question covered in a training video, the assistant can link to the relevant time range.
- The user can answer their question without watching the full video.

### F7. Screenshot And Visual Reference Support

Priority: Should have

User need:
Some users need visual confirmation of where to click or what screen to use.

Data sources:
- Screenshots in PDFs/manuals.
- Screenshots from training videos.
- P2P/ServiceNow walkthrough images.

Behavior:
- Attach relevant screenshots to answers when the next step depends on UI location.
- Show image captions and source citations.
- Avoid showing stale screenshots unless source date/version is known.

Output:
- Text guidance.
- Relevant screenshot or visual.
- Source document/video reference.

Acceptance criteria:
- Answers about where to find something in P2P/ServiceNow can include a visual reference.
- Visuals include source metadata.

### F8. Escalation Routing

Priority: Must have

User need:
When the assistant cannot safely answer, the user still needs to know who to contact.

Escalation targets:
- Procurement and Contracts.
- Accounts Payable.
- Supplier Management.
- ITS.
- Solutions Consulting.
- Department approver.

Behavior:
- Detect unsupported, ambiguous, conflicting, or high-risk questions.
- Explain what the assistant can and cannot determine.
- Route the user to the right office.
- Include the reason for escalation.

Output:
- Escalation recommendation.
- Reason.
- Information the user should gather before contacting the office.

Acceptance criteria:
- The assistant does not invent answers for missing policy.
- Conflicting source material triggers an escalation message.
- Technology/software uncertainty routes to ITS or Solutions Consulting.

### F9. Requisition Status Guidance

Priority: Should have for MVP; could become must have if live status is required

User need:
Requesters want to understand where a requisition stands without emailing Procurement.

MVP behavior:
- Explain how to check requisition status in P2P/ServiceNow.
- Explain common status meanings if source material exists.
- Identify common blockers and where to follow up.

Post-MVP behavior:
- Read-only integration with ServiceNow/P2P to retrieve live status.
- Summarize current state, pending approver, missing information, and likely next action.

Output:
- Instructions for checking status.
- Meaning of status terms.
- Suggested next action.

Acceptance criteria:
- MVP does not claim live requisition status unless integration exists.
- Status guidance is grounded in source documentation.

### F9A. Vendor Onboarding And Invoice Guidance

Priority: Must have if vendors are in first-version scope

User need:
Vendors need clear guidance on supplier registration, purchase orders, invoices, payment questions, and who to contact when onboarding stalls.

Inputs:
- Vendor status: new supplier, existing supplier, invited to register, invoice issue, payment question, or purchase order question.
- Known identifiers if available: purchase order number, invoice number, supplier name, or requester contact.

Behavior:
- Explain supplier registration steps using approved sources.
- Explain where invoice or payment questions should go.
- Distinguish vendor-facing guidance from requester/internal guidance.
- Route unresolved supplier setup issues to Supplier Management.
- Route invoice/payment issues to Accounts Payable when appropriate.
- Avoid exposing internal procurement-only materials to vendors unless approved.

Output:
- Vendor-facing step-by-step guidance.
- Required information or documents.
- Responsible office.
- Source citations.
- Escalation path.

Acceptance criteria:
- A new vendor can understand what to do next without reading internal procurement documentation.
- Vendor invoice questions route to AP or the correct source-backed process.
- The assistant does not expose restricted internal guidance to vendors.

### F10. Admin Knowledge Base Management

Priority: Should have

User need:
Procurement and ITS need to keep sources accurate without engineering support for every document change.

Admin users:
- Procurement content owner.
- ITS support/admin.
- Project maintainer.

Behavior:
- Upload or sync source documents.
- Tag source by campus, owner, topic, document type, date, and priority.
- Mark source as active, outdated, draft, or retired.
- Rebuild index after approved updates.
- View documents used in recent answers.

Output:
- Source inventory.
- Index status.
- Last updated date.
- Source priority rules.

Acceptance criteria:
- Admin can add or retire a document without changing application code.
- The system tracks source metadata.
- Retired documents are not used in new answers.

### F11. Duplicate And Conflict Handling

Priority: Should have

User need:
CSU-wide and CSUB-specific documents may overlap or conflict. The assistant must avoid mixing them incorrectly.

Behavior:
- Identify similar or duplicate source documents.
- Prioritize CSUB-specific content over CSU-wide content for campus procedures.
- Surface conflicts when the answer differs across sources.
- Store source priority rules.

Output:
- Deduplication warning for admins.
- Conflict warning in answers when relevant.
- Recommended source precedence.

Acceptance criteria:
- If two sources give different procedures, the assistant does not silently choose one without explanation.
- Admins can inspect which sources conflict.

### F12. Analytics And Gap Dashboard

Priority: Could have / strong post-MVP feature

User need:
Procurement needs to understand where users are stuck and which documentation gaps cause repeated questions.

Metrics:
- Top user questions.
- Unanswered questions.
- Escalation rate.
- Source coverage gaps.
- FAQ click rate.
- Helpful/not helpful ratings.
- Common purchase categories.
- Repeated missing information.

Behavior:
- Log anonymized query categories.
- Track answer success signals.
- Show topics where sources are missing or low-confidence.
- Recommend new FAQ entries or documentation updates.

Output:
- Admin dashboard.
- Weekly question summary.
- Missing-source report.
- Common confusion areas.

Acceptance criteria:
- Admin can see the top recurring questions.
- Admin can identify questions the assistant could not answer.
- Dashboard does not expose unnecessary personal or sensitive data.

## Explicit Non-Features For MVP

- No requisition submission.
- No purchase approval.
- No write-back to ServiceNow.
- No write-back to CFS.
- No supplier registration submission.
- No final legal/procurement determination without source support.
- No replacement for Procurement, AP, ITS, Supplier Management, or Solutions Consulting.
- No campus-agnostic CSU answer when CSUB-specific guidance exists.

## Data Model Requirements

Each source document should include:
- Source ID.
- Title.
- Campus scope: CSUB, CSU-wide, or other.
- Owner office.
- Topic tags.
- Document type: PDF, web page, transcript, image, spreadsheet, guide.
- URL or file path.
- Date published.
- Date ingested.
- Version if available.
- Active/retired status.
- Priority level.
- Access level.

Each answer should store:
- User query.
- Detected topic.
- Clarifying questions asked.
- Retrieved source IDs.
- Generated answer.
- Citations shown.
- Escalation target if any.
- Helpful/not helpful feedback if provided.

## Recommended Demo Scenarios

### Demo 1: New Vendor

User asks:
"I need to buy something from a vendor that is not in the system. What do I do?"

Expected assistant behavior:
- Explain supplier registration steps.
- Identify who handles supplier management.
- List requester next actions.
- Cite supplier registration source.
- Offer checklist.

### Demo 2: Software Purchase

User asks:
"My department wants to buy a new software subscription for $5,000. Where do I start?"

Expected assistant behavior:
- Ask whether supplier exists and whether contract exists if needed.
- Flag technology/software review.
- Identify likely purchase path.
- Mention approved-software list.
- Cite technology review and procurement sources.
- Generate checklist.

### Demo 3: Student Worker Access

User asks:
"Can a student worker get access to CSUBUY?"

Expected assistant behavior:
- Use CSUB-specific source if available.
- Explain access process.
- Escalate if campus-specific access rules are missing.
- Avoid giving generic CSU guidance as final if CSUB rules differ.

### Demo 4: Invoice Processing

User asks:
"How do I process an invoice?"

Expected assistant behavior:
- Determine whether invoice relates to existing PO/requisition if needed.
- Provide steps.
- Route AP-specific questions to Accounts Payable.
- Cite P2P/ServiceNow guide.

### Demo 5: Training Video Timestamp

User asks:
"Where in the training does it explain how to check requisition status?"

Expected assistant behavior:
- Retrieve transcript segment.
- Summarize instructions.
- Link directly to the relevant YouTube timestamp.

## Priority Summary

Must have:
- Plain-language procurement chat.
- Role selection and role-aware guidance.
- Source-grounded RAG retrieval.
- Guided procurement pathfinder.
- Dynamic pre-submission checklist.
- Escalation routing.
- Vendor onboarding and invoice guidance, if vendors remain in first-version scope.

Should have:
- FAQ/common questions page.
- Video transcript and timestamp support.
- Screenshot and visual reference support.
- Requisition status guidance.
- Admin knowledge base management.
- Duplicate and conflict handling.

Could have:
- Analytics and gap dashboard.
- Live read-only requisition status integration.
- Contract/supplier lookup integration.
- Role-aware answers.
- CSU-wide reusable version with campus overlays.

## Success Criteria

The prototype should be considered successful if it can:
- Answer common requester questions with citations.
- Guide a user from an unclear purchase need to a concrete purchasing checklist.
- Correctly distinguish CSUB-specific guidance from CSU-wide material.
- Avoid unsupported answers and escalate ambiguous cases.
- Summarize relevant training content without requiring full video viewing.
- Demonstrate reduced need for repetitive Procurement hand-holding.
