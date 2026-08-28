# Alon AI dashboard

This Next.js App Router frontend renders the private Alon AI foundation
dashboard and reports live API/database readiness through the generated FastAPI
contract. It contains no production outreach controls or fake business data.

Use Node.js 24. From `frontend/`:

```sh
npm ci
npm run api:generate
npm run lint
npm run typecheck
npm test -- --run
npm run build
npm run dev
```

The application source is under `src/app/`. `NEXT_PUBLIC_API_BASE_URL`
defaults to `http://localhost:8000`; only browser-safe configuration belongs in
variables with the `NEXT_PUBLIC_` prefix. Generated changes to `openapi.json`
and `src/lib/api/schema.d.ts` must be reviewed together.
