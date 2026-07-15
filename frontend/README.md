# CSUB Procurement Assistant Frontend

The standalone React/Vite interface for the public CSUB Procurement Assistant.

## Backend connection

The default build connects directly to the production API Gateway backend:

- Chat: `https://w0vfga8dil.execute-api.us-west-2.amazonaws.com/prod/v1/chat`
- Health: `https://w0vfga8dil.execute-api.us-west-2.amazonaws.com/prod/v1/health`

Copy `.env.example` to `.env.local` to override the backend for another environment. `VITE_API_BASE_URL` is preferred; `VITE_API_URL` and `VITE_HEALTH_URL` can override individual routes.

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

The API is public/no-auth guidance only. The interface sends the selected guidance role, the current question, and at most six recent conversation items. It displays only the answer and cited source cards returned by the backend.
