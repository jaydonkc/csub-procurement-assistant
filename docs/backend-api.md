# Backend API

Status: live and verified July 15, 2026.

## Endpoints

Base URL: `https://w0vfga8dil.execute-api.us-west-2.amazonaws.com/prod`

- `GET /v1/health` returns the service status, immutable Lambda version, and request ID without calling Bedrock.
- `POST /v1/chat` accepts a bounded public guidance request and returns an answer, optional cited public source cards, an optional structured status card, and a request ID.
- `OPTIONS` is enabled for both routes. The current public MVP allows all browser origins; replace `AllowedOrigin=*` with the approved frontend origin during frontend integration.

## Chat Request

```json
{
  "message": "Where do I review voucher pay status and what does it show?",
  "role": "requester",
  "history": []
}
```

The API requires `message` and `role`. The message is limited to 4,000 characters. Role must be `requester`, `vendor`, or `internal_staff`. Optional history is limited to six `user` or `assistant` items of no more than 2,000 characters each. Unknown fields and invalid schemas are rejected before Lambda runs.

## Chat Response

```json
{
  "answer": "Source-grounded guidance with [S1] citations.",
  "sources": [
    {
      "id": "S1",
      "path": "Invoicing and Vouchers/Voucher Pay Status.pdf",
      "kind": "document",
      "timestamp": null,
      "source_url": "https://short-lived-private-source-url",
      "media_expires_in": 900
    }
  ],
  "request_id": "example-request-id"
}
```

Conversation, clarification, out-of-scope, safety, and capability routes can return a successful response with an empty `sources` array. The pre-retrieval router is used only after deterministic gates; it defaults to retrieval when its output is invalid, unavailable, or uncertain. Substantive procurement answers still require grounded citations.

### Synthetic status response

The `codex/demo-status-panel` development branch recognizes one exact synthetic identifier before retrieval or model execution. The four demo identifiers are `DEMO-REQ-1001`, `DEMO-PO-2001`, `DEMO-INV-3001`, and `DEMO-VCH-4002`. A successful lookup uses the normal response plus `status_card`:

```json
{
  "answer": "I found the invoice DEMO-INV-3001.",
  "sources": [],
  "status_card": {
    "record_id": "DEMO-INV-3001",
    "record_type": "Invoice",
    "title": "Equipment delivery invoice",
    "status": "In Accounts Payable review",
    "current_stage": 2,
    "stages": ["Invoice received", "AP review", "Payment scheduled", "Paid"],
    "fields": [{"label": "Invoice total", "value": "$2,480.00"}],
    "next_step": "Accounts Payable completes its review before the payment can be scheduled.",
    "last_updated": "July 16, 2026 at 11:40 AM"
  },
  "request_id": "example-request-id"
}
```

Unknown or multiple demo identifiers fail closed without retrieval. Mutation requests remain blocked. Ordinary record numbers still return the no-live-access boundary. This optional response field is implemented on the development branch and is not part of the currently frozen Lambda version `18` until a later deployment is explicitly approved.

The rendered experience uses the `DEMO-*` record identifier as its only demo marker. User-facing answer text, status headings, field values, and badges do not add separate demo or synthetic labels.

Public cited documents can include `source_url`; cited training videos can include both `source_url` and `media_url` plus a transcript `timestamp`. These are private S3 presigned links with `media_expires_in=900`, not permanent public URLs. Invalid input returns `400`, unknown routes return `404`, throttled traffic returns `429`, oversized traffic returns `413`, and unexpected backend failures return a generic `500` without internal error details.

## Production Controls

- API Gateway schema validation, CORS, compression, per-stage throttling, detailed metrics, and X-Ray.
- WAF source-IP rate limiting and 64,000-byte body enforcement.
- Direct Lambda URLs use IAM authentication and are not public fallbacks.
- Access logs exclude request bodies, chat content, source IPs, and user agents.
- Lambda application logs contain request IDs, route outcomes, grounding status, and source counts—not questions or answers.
- No chat, question, or feedback database exists until CSUB approves a retention policy.
- Synthetic status records are a four-record Python provider with no names, account credentials, sensitive PII, or live-system connection.

## Deployment

`infra/backend.yaml` defines the production API, WAF, logging, metrics, alarms, alert topic, dashboard, API invocation permission, and X-Ray permission. `scripts/deploy_backend.sh` verifies account `335010339891`, reconciles the bounded source-link policies, vendors the pinned Lambda SDK, runs the policy/API tests, updates the stack, verifies both grounded and no-retrieval `$LATEST` responses, publishes an immutable version, moves the alias, and rolls back if post-alias health, grounded-answer, or conditional-retrieval checks fail. Code hashes and revision IDs prevent a concurrent deployment from silently replacing the tested code.

The deployment script defaults to AWS profile `summercamp` and region `us-west-2`. Optional environment variables include `ALLOWED_ORIGIN`, `WAF_RATE_LIMIT`, and `ALERT_EMAIL`. Supplying `ALERT_EMAIL` creates an email subscription that still requires recipient confirmation.
