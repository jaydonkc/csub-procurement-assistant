# Backend API

Status: live and verified July 15, 2026.

## Endpoints

Base URL: `https://w0vfga8dil.execute-api.us-west-2.amazonaws.com/prod`

- `GET /v1/health` returns the service status, immutable Lambda version, and request ID without calling Bedrock.
- `POST /v1/chat` accepts a bounded public guidance request and returns an answer, cited public source cards, and request ID.
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
      "timestamp": null
    }
  ],
  "request_id": "example-request-id"
}
```

Safety or capability routes can return a successful guidance response with an empty `sources` array. Invalid input returns `400`, unknown routes return `404`, throttled traffic returns `429`, oversized traffic returns `413`, and unexpected backend failures return a generic `500` without internal error details.

## Production Controls

- API Gateway schema validation, CORS, compression, per-stage throttling, detailed metrics, and X-Ray.
- WAF source-IP rate limiting and 64,000-byte body enforcement.
- Direct Lambda URLs use IAM authentication and are not public fallbacks.
- Access logs exclude request bodies, chat content, source IPs, and user agents.
- Lambda application logs contain request IDs, route outcomes, grounding status, and source counts—not questions or answers.
- No chat, question, or feedback database exists until CSUB approves a retention policy.

## Deployment

`infra/backend.yaml` defines the production API, WAF, logging, metrics, alarms, alert topic, dashboard, API invocation permission, and X-Ray permission. `scripts/deploy_backend.sh` vendors the pinned Lambda SDK, runs the policy/API tests, updates the stack, verifies a grounded `$LATEST` response, publishes an immutable version, moves the alias, and rolls back if post-alias health or grounded API checks fail.

The deployment script defaults to AWS profile `summercamp` and region `us-west-2`. Optional environment variables include `ALLOWED_ORIGIN`, `WAF_RATE_LIMIT`, and `ALERT_EMAIL`. Supplying `ALERT_EMAIL` creates an email subscription that still requires recipient confirmation.
