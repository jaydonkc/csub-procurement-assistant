"""Source-verified responses for narrow, high-frequency workflows."""

from __future__ import annotations

import re
from typing import Any

from backend.config import ESCALATION_CONTACT, ESCALATION_EMAIL
from backend.grounding import context_for_citations


def timestamp_for_phrase(context: str, source_id: str, phrase: str) -> str | None:
    for chunk in re.split(r"\n\n(?=\[S\d+\]\s)", context):
        if (
            not chunk.startswith(f"[{source_id}] ")
            or phrase.casefold() not in chunk.casefold()
        ):
            continue
        match = re.search(
            r"\d{2}:\d{2}:\d{2}\.\d{3}\s+-->\s+\d{2}:\d{2}:\d{2}\.\d{3}",
            chunk,
        )
        if match:
            return match.group(0)
    return None


def guided_template_answer(
    message: str,
    context: str,
    sources: list[dict[str, Any]],
    *,
    resolved_query: str = "",
) -> tuple[str, list[dict[str, Any]]] | None:
    """Return source-verified copy for a narrow, high-frequency workflow."""
    lowered = f"{message}\n{resolved_query}".casefold()

    invoice_information_question = "invoice" in lowered and any(
        phrase in lowered
        for phrase in (
            "what information",
            "what should i include",
            "what should be on",
            "what do i include",
            "what needs to be",
            "what is required",
            "information should",
            "invoice requirements",
            "invoice need",
            "required on an invoice",
            "include with an invoice",
            "include on an invoice",
        )
    )
    if invoice_information_question:
        guide_source = next(
            (
                item
                for item in sources
                if item["path"].endswith(
                    "Getting Started/AComprehensiveGuide05_20_25.pdf"
                )
            ),
            None,
        )
        guide_verified = False
        guide_submission_verified = False
        if guide_source is not None:
            guide_excerpt = context_for_citations(
                context, {guide_source["id"]}
            ).casefold()
            required_terms = (
                "invoice",
                "itemized",
                "process payment",
            )
            guide_verified = all(
                term in guide_excerpt for term in required_terms
            ) and any(
                term in guide_excerpt for term in ("match amount", "match the amount")
            )
            guide_submission_verified = "csubuy p2p" in guide_excerpt and any(
                email in guide_excerpt
                for email in (
                    "accounts_payable@csub.edu",
                    "accounts payable@csub.edu",
                )
            )

        voucher_source = next(
            (
                item
                for item in sources
                if item["path"].endswith("Invoicing and Vouchers/Sales.pdf")
            ),
            None,
        )
        voucher_verified = False
        if voucher_source is not None:
            voucher_excerpt = context_for_citations(
                context, {voucher_source["id"]}
            ).casefold()
            voucher_terms = (
                "supplier invoice date",
                "supplier invoice number",
                "supplier name",
            )
            voucher_verified = all(term in voucher_excerpt for term in voucher_terms)

        if guide_verified:
            source_id = guide_source["id"]
            answer = f"""The CSUB guide provides a useful baseline, but it does not label it as an exhaustive vendor-facing field checklist [{source_id}]. Based on the documented guidance:

1. Make the invoice **itemized** and include the information CSUB needs to process payment [{source_id}].
2. Ensure the invoice amount matches the related **Purchase Order (PO)** or **Direct Pay (DP)** amount [{source_id}]."""
            if guide_submission_verified:
                answer += f"""
3. Upload the invoice through **CSUBUY P2P** when possible; if the supplier cannot upload it, email it to **accounts_payable@csub.edu** [{source_id}]."""
            cited_sources = [guide_source]
        elif voucher_verified:
            voucher_id = voucher_source["id"]
            answer = (
                "The available CSUBUY excerpt supports three invoice identifiers used during voucher entry: "
                f"**Supplier Name, Supplier Invoice Date, and Supplier Invoice Number** [{voucher_id}]. "
                "Because the excerpt describes internal voucher entry rather than a complete vendor-facing invoice standard, "
                f"treat those fields as a supported partial answer, not an exhaustive checklist [{voucher_id}]."
            )
            cited_sources = [voucher_source]
        else:
            answer = ""
            cited_sources = []

        if voucher_verified and guide_verified:
            voucher_id = voucher_source["id"]
            answer += (
                "\n\nCSUBUY's voucher-entry screen also records **Supplier Name, Supplier Invoice Date, "
                f"and Supplier Invoice Number** [{voucher_id}]. Those fields are documented for voucher entry, "
                f"not presented as a complete vendor invoice standard [{voucher_id}]."
            )
            cited_sources.append(voucher_source)

        if cited_sources:
            answer += (
                "\n\nThe public sources do not document a complete vendor-facing field checklist. "
                f"For any additional required fields, contact **{ESCALATION_EMAIL}**."
            )
            return answer, cited_sources

    supplier_invitation_question = (
        any(term in lowered for term in ("supplier", "vendor"))
        and any(term in lowered for term in ("invitation", "invite"))
        and any(
            term in lowered
            for term in (
                "did not receive",
                "didn't receive",
                "never received",
                "not received",
                "missing invitation",
                "re-invite",
                "reinvite",
            )
        )
    )
    if supplier_invitation_question:
        source = next(
            (
                item
                for item in sources
                if item["path"].endswith(
                    "Suppliers/Supplier Did Not Receive Invitation.pdf"
                )
            ),
            None,
        )
        if source:
            excerpt = context_for_citations(
                context, {source["id"]}
            ).casefold()
            required_terms = (
                "invited email address",
                "supplier search",
                "view history",
                "re-invite request",
                "new supplier request",
                "noreply@jaggaer.com",
                "junk/spam",
                "email filters",
                "whitelist",
            )
            if all(term in excerpt for term in required_terms):
                source_id = source["id"]
                answer = f"""When a supplier does not receive the registration invitation, first verify which email address was invited [{source_id}].

1. Find the supplier profile with supplier search, open **View History**, and review the invited email address [{source_id}].
2. If the address is correct, submit a **Re-Invite Request** and ask the supplier to look for **noreply@jaggaer.com** in their inbox and junk/spam folder [{source_id}].
3. If the address is incorrect, submit a **New Supplier Request** [{source_id}].
4. If the invitation still does not arrive, the supplier should ask their IT team to check email filters and whitelist the **jaggaer.com** domain [{source_id}].

For additional help, contact **{ESCALATION_EMAIL}**."""
                return answer, [source]

    amazon_access_question = "amazon" in lowered and any(
        term in lowered
        for term in ("access", "account", "punchout", "start shopping")
    )
    if amazon_access_question:
        source = next(
            (
                item
                for item in sources
                if item["path"].endswith(
                    "Shopping and Requistions/Amazon Accounts and Access.pdf"
                )
            ),
            None,
        )
        if source:
            excerpt = context_for_citations(
                context, {source["id"]}
            ).casefold()
            required_terms = (
                "amazon business",
                "csubuy user profile",
                "email addresses can only be used one time",
                "check any/all your amazon accounts",
                "amazon business tile",
            )
            if all(term in excerpt for term in required_terms):
                source_id = source["id"]
                answer = f"""Amazon Business access through CSUBUY depends on how the email address in your CSUBUY user profile is already used with Amazon [{source_id}].

1. Amazon email addresses can be used only once, so sign in directly to any existing Amazon accounts and check the email before punching out from CSUBUY [{source_id}].
2. If the email is already in CSU's Amazon Business account, select the **Amazon Business** tile in CSUBUY [{source_id}]."""
                if all(
                    term in excerpt
                    for term in (
                        "new email",
                        "registration wizard",
                        "complete the registration process",
                        'click "start shopping"',
                    )
                ):
                    answer += f"""
3. If the email is new to Amazon, complete the registration wizard and select **Start Shopping** [{source_id}]."""
                answer += f"""

For an email tied to another account state, use the matching documented scenario in the guide [{source_id}]."""
                return answer, [source]

    supplier_registration_returned_question = (
        any(term in lowered for term in ("supplier", "vendor"))
        and "registration" in lowered
        and any(term in lowered for term in ("returned", "return", "correction"))
    )
    if supplier_registration_returned_question:
        source = next(
            (
                item
                for item in sources
                if item["path"].endswith(
                    "Suppliers/Supplier Registration Returned.pdf"
                )
            ),
            None,
        )
        if source:
            excerpt = context_for_citations(context, {source["id"]}).casefold()
            required_terms = (
                "supplier maintenance",
                "returns a registration for correction",
                "admin on the profile",
                "noreply@jaggaer.com",
                "returned for correction for the following reason",
                "resources",
                "corrections in your supplier profile",
            )
            if all(term in excerpt for term in required_terms):
                source_id = source["id"]
                answer = f"""A returned supplier registration means the systemwide Supplier Maintenance (SM) Team identified a correction that is needed [{source_id}].

1. The admin on the supplier profile receives a return email from **noreply@jaggaer.com** that states the specific correction reason [{source_id}].
2. Follow the resources named in that email, make the correction it describes, and update the supplier profile as directed [{source_id}].

The guide's W-9 correction is an example, so use the reason in the actual return email rather than assuming every returned registration has the same issue [{source_id}]."""
                return answer, [source]

    po_change_request_question = "change request" in lowered and any(
        term in lowered for term in ("purchase order", "cfs", "current po", "po status")
    )
    if po_change_request_question:
        source = next(
            (
                item
                for item in sources
                if item["path"].endswith(
                    "Shopping and Requistions/Submitting a Change Request.pdf"
                )
            ),
            None,
        )
        if source:
            excerpt = context_for_citations(context, {source["id"]}).casefold()
            precheck_verified = all(
                term in excerpt
                for term in (
                    "review the current status",
                    "vouchers",
                    "payments",
                    "receipts",
                )
            )
            status_verified = all(
                term in excerpt
                for term in (
                    "history tab",
                    "summary panel",
                    "sent to cfs",
                    "completed",
                )
            )
            if precheck_verified or status_verified:
                source_id = source["id"]
                parts = []
                if precheck_verified:
                    parts.append(
                        "Before creating the purchase-order change request, review the current PO status. "
                        f"Existing vouchers, payments, or receipts can mean a change is not possible and may require coordination with Procurement [{source_id}]."
                    )
                if status_verified:
                    parts.append(
                        "To check the change request afterward, open the PO's **History** tab and expand the **Summary** panel; "
                        f"that is where the guide says to verify whether it was sent to **CFS** and completed [{source_id}]."
                    )
                if not (precheck_verified and status_verified):
                    parts.append(ESCALATION_CONTACT)
                return "\n\n".join(parts), [source]

    if "profile" in lowered and any(
        term in lowered for term in ("update", "change", "edit")
    ):
        source = next(
            (
                item
                for item in sources
                if item["path"].endswith("Getting Started/User Profile Update.mp4")
            ),
            None,
        )
        if source:
            excerpt = context_for_citations(context, {source["id"]}).casefold()
            navigation_verified = all(
                term in excerpt for term in ("view my profile", "sidebar", "preferences")
            )
            preferences_verified = all(
                term in excerpt
                for term in (
                    "notifications",
                    "override radio button",
                    "save changes",
                    "default addresses",
                )
            )
            if navigation_verified or preferences_verified:
                source_id = source["id"]
                answer_parts = []
                if navigation_verified:
                    answer_parts.append(
                        f"Open the user menu in the upper-right corner of CSUBUY and select **View My Profile** [{source_id}]. "
                        f"Use the profile sidebar to choose the preference category you want to update [{source_id}]."
                    )
                if preferences_verified:
                    answer_parts.append(
                        f"The User Profile Update training also shows how to customize notification preferences with the override option, save the changes, and update **Default Addresses** for punchout requests [{source_id}]."
                    )
                timestamp = timestamp_for_phrase(
                    context, source_id, "view my profile"
                ) or source.get("timestamp")
                cited_source = dict(source)
                if timestamp:
                    answer_parts.append(
                        f"The retrieved profile-training segment is **{timestamp}** [{source_id}]."
                    )
                    cited_source["timestamp"] = timestamp
                return "\n\n".join(answer_parts), [cited_source]

    if "default" in lowered and "address" in lowered:
        source = next(
            (
                item
                for item in sources
                if item["path"].endswith(
                    "Getting Started/Setting Default Addresses.pdf"
                )
            ),
            None,
        )
        if source:
            excerpt = context_for_citations(context, {source["id"]}).casefold()
            required_terms = (
                "default addresses",
                "ship to",
                "select addresses for profile",
                "address template",
            )
            if all(term in excerpt for term in required_terms):
                source_id = source["id"]
                answer = f"""To set your default shipping address in CSUBUY:

1. Open your profile and select **Default Addresses** [{source_id}].
2. Open the **Ship To** tab and choose **Select Addresses for Profile** [{source_id}].
3. Use **Select Address Template** to choose the address you want as the default [{source_id}].

The retrieved public excerpt does not provide a complete Bill To setup sequence. {ESCALATION_CONTACT}"""
                return answer, [source]

    if "support ticket" in lowered:
        source = next(
            (
                item
                for item in sources
                if item["path"].endswith(
                    "Search, Data Exports, Reports, & Support Tickets/Submit Support Ticket (QRG_Optimize_Requester).pdf"
                )
            ),
            None,
        )
        if source:
            excerpt = context_for_citations(context, {source["id"]}).casefold()
            required_terms = (
                "optimize",
                "category",
                "subcategory",
                "short description",
                "description",
                "submit",
            )
            if all(term in excerpt for term in required_terms):
                source_id = source["id"]
                answer = f"""Submit a CSUBUY support ticket through the **OPTIMIZE** support portal using the **CSUBUY Ticket** form [{source_id}].

1. Select the appropriate **Category** and **Subcategory** [{source_id}].
2. Enter a **Short Description** for the issue [{source_id}].
3. Add a detailed **Description** and any useful attachment [{source_id}].
4. Select **Submit**, or save the ticket as a draft if it is not ready [{source_id}].

The public excerpt does not include the OPTIMIZE portal URL. {ESCALATION_CONTACT}"""
                return answer, [source]

    if any(
        term in lowered
        for term in ("new supplier", "request a supplier", "cannot find a supplier")
    ):
        source = next(
            (
                item
                for item in sources
                if item["path"].endswith("Suppliers/Requesting a New Supplier.pdf")
            ),
            None,
        )
        if source:
            excerpt = context_for_citations(context, {source["id"]}).casefold()
            required_terms = (
                "search",
                "request new supplier",
                "supplier name",
                "submit",
                "requester contact",
                "review and complete",
            )
            if all(term in excerpt for term in required_terms):
                source_id = source["id"]
                answer = f"""Search for the supplier first so you do not create a duplicate profile [{source_id}]. If no full supplier profile exists, follow this path:

1. From the CSUBUY homepage, select **Request New Supplier** [{source_id}].
2. Enter the supplier name and select **Submit** [{source_id}].
3. Complete the form's **Questions** and **Requester Contact Information** sections [{source_id}].
4. Use **Review and Complete** to finish the request form [{source_id}].

If the supplier appears in search results or you are unsure which profile/status applies, stop before creating a duplicate. {ESCALATION_CONTACT}"""
                return answer, [source]

    if "fiscal year" in lowered and "accounting date" in lowered:
        source = next(
            (
                item
                for item in sources
                if item["path"].endswith(
                    "Fiscal Year End/Fiscal Year End Process - End User.pdf"
                )
            ),
            None,
        )
        if source:
            excerpt = context_for_citations(context, {source["id"]}).casefold()
            required_terms = (
                "accounting date",
                "current fiscal year",
                "new fiscal year",
                "july 1",
            )
            if all(term in excerpt for term in required_terms):
                source_id = source["id"]
                answer = f"""During fiscal year end, edit the requisition's **PO Information** and set the **Accounting Date** for the fiscal year in which the purchase belongs [{source_id}].

1. For a current-fiscal-year requisition submitted in May or June, use the applicable current May/June date [{source_id}].
2. For a new-fiscal-year requisition, use July 1 or a later date in the new fiscal year [{source_id}].
3. Save the PO Information before submitting the requisition [{source_id}].

If the correct fiscal year is uncertain, do not guess. {ESCALATION_CONTACT}"""
                return answer, [source]

    if "voucher" in lowered and "status" in lowered:
        source = next(
            (
                item
                for item in sources
                if item["path"].endswith(
                    "Invoicing and Vouchers/Voucher Pay Status.pdf"
                )
            ),
            None,
        )
        if source:
            excerpt = context_for_citations(context, {source["id"]}).casefold()
            required_terms = ("orders", "search", "vouchers", "pay status")
            if all(term in excerpt for term in required_terms):
                source_id = source["id"]
                answer = f"In CSUBUY, navigate to **Orders > Search > Vouchers**; the **Pay Status** column shows the voucher's current status [{source_id}]."
                if "payment information" in excerpt:
                    answer += f" Open a voucher and review the **Payment Information** section for Pay Status and additional payment-process details [{source_id}]."
                answer += " This is general guidance only; I cannot view a live voucher or payment record."
                return answer, [source]

    if "receipt" in lowered:
        source = next(
            (
                item
                for item in sources
                if item["path"].endswith("Receiving/Creating a Receipt.mp4")
            ),
            None,
        )
        if source:
            excerpt = context_for_citations(context, {source["id"]}).casefold()
            required_terms = (
                "purchase orders",
                "create receipt",
                "create quantity receipt",
                "packing",
                "tracking",
                "complete",
            )
            if all(term in excerpt for term in required_terms):
                source_id = source["id"]
                answer = f"""To create a receipt for delivered goods in CSUBUY:

1. Open **Orders > Purchase Orders** and locate the purchase order [{source_id}].
2. Open **Document Actions** and select **Create Receipt** [{source_id}].
3. Uncheck any purchase-order line that should not be included in this receipt [{source_id}].
4. Select **Create Quantity Receipt** [{source_id}].
5. Enter the receipt name, receipt date, packing-slip number, and tracking information [{source_id}].
6. Confirm the purchase-order lines are accurate, then select **Complete** [{source_id}].
7. Confirm that CSUBUY displays the success message [{source_id}]."""
                return answer, [source]
    return None
