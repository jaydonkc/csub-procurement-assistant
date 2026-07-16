# CSUB Procurement Assistant Frontend

The standalone React/Vite interface for the public CSUB Procurement Assistant.

Production: `https://d3s79ehfkh7xjx.cloudfront.net`

## Backend connection

The default build connects directly to the production API Gateway backend:

- Chat: `https://w0vfga8dil.execute-api.us-west-2.amazonaws.com/prod/v1/chat`

Copy `.env.example` to `.env.local` to override the backend for another environment. `VITE_API_BASE_URL` is preferred; `VITE_API_URL` can override the chat route directly.

## Branding

The header uses the official CSUB Bakersfield logo asset with padded desktop and mobile spacing. It does not show demo or backend-status badges.

## Run locally

```bash
npm install
npm run dev
```

Then open `http://127.0.0.1:5173`.

## Verify

```bash
npm run lint
npm run build
```

## Deploy to AWS

The production frontend is hosted from a private S3 bucket through CloudFront. From the repository root, run:

```bash
AWS_PROFILE=summercamp AWS_REGION=us-west-2 ./scripts/deploy_frontend.sh
```

The script verifies the AWS account, validates the CloudFormation template, runs frontend checks, builds with the production API URL, uploads cache-safe assets, invalidates CloudFront, and smoke-tests the public HTTPS page. Override `VITE_API_BASE_URL` only when intentionally targeting a different backend.

The current API is public/no-auth guidance only. The interface changes its suggested questions for faculty/staff, vendors/suppliers, and support staff, then sends the selected guidance role, the current question, and at most six recent conversation items. It displays only the answer and cited source cards returned by the backend. Role selection changes guidance context only and does not authorize internal content.

Each role keeps its own in-memory conversation, draft, and open source while the page remains loaded. Switching roles opens that role's session, and switching back restores it. After a conversation starts, the role bar provides a **New chat** action that clears only the selected role's messages, draft, and open source.

When the assistant cannot safely complete public guidance or a request requires human support, it directs the user to `bwholgemuth1@csub.edu`.

The MVP product direction now allows an authenticated read-only status surface for requester and vendor progress questions. That authenticated surface must use a campus-approved identity provider and backend authorization before showing requisition, supplier, invoice, purchase-order, or payment status. The current frontend does not implement that sign-in flow yet.
