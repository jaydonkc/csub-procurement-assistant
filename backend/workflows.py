"""Source-verified responses for narrow, high-frequency workflows."""

from __future__ import annotations

import re
from typing import Any

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
) -> tuple[str, list[dict[str, Any]]] | None:
    """Return source-verified copy for a narrow, high-frequency workflow."""
    lowered = message.casefold()

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
            required_terms = ("view my profile", "sidebar", "preferences")
            if all(term in excerpt for term in required_terms):
                source_id = source["id"]
                answer = (
                    f"Open the user menu in the upper-right corner of CSUBUY and select **View My Profile** [{source_id}]. "
                    f"Use the profile sidebar to choose the preference category you want to update [{source_id}]."
                )
                timestamp = timestamp_for_phrase(
                    context, source_id, "view my profile"
                ) or source.get("timestamp")
                cited_source = dict(source)
                if timestamp:
                    answer += f" The retrieved training segment is **{timestamp}** [{source_id}]."
                    cited_source["timestamp"] = timestamp
                return answer, [cited_source]

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

The retrieved public excerpt does not provide a complete Bill To setup sequence, so contact the responsible CSUB support office if the billing-address tab does not provide enough guidance."""
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

The public excerpt does not include the OPTIMIZE portal URL; contact CSUB Procurement or IT support if you need the entry link."""
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

If the supplier appears in search results or you are unsure which profile/status applies, stop before creating a duplicate and contact the Campus Supplier Administrator."""
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

If the correct fiscal year is uncertain, confirm the date with the campus Procurement team before submission."""
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
