# Alon AI operator desk

The Next.js App Router frontend provides a private, desktop-oriented operator
shell. Login and operator data pass through same-origin route handlers. Server
rendering verifies the signed session before requesting status or activity, and
private responses use `no-store` caching. Activity comes from the server-owned
projection; the browser listens for read-only events and polls if the stream is
unavailable.

Use Node.js 24. From `frontend/`:

```sh
npm ci
npm run api:generate
npm run lint
npm run typecheck
npm test -- --run
npm run build
npm run test:visual
npm run dev
```

`test:visual` builds the app, runs a fixed local API stub, and compares headless
Chrome screenshots of `/login` and the authenticated shell at 1280×800 with
the baselines in `tests/visual/`. It fails if more than 0.5% of pixels differ
substantially or the mean channel difference exceeds 1.5. Set `CHROME_BIN` if
Chrome is installed outside the default macOS path. To intentionally refresh
the baselines after reviewing a visual change, run
`UPDATE_VISUAL_BASELINES=1 npm run test:visual`.

Set `API_BASE_URL` to the backend's server-reachable origin (default
`http://localhost:8000`). The backend must set `ALON_AI_FRONTEND_ORIGIN` to the
browser-visible frontend origin (default `http://localhost:3000`); login and
logout forward that origin for the backend's exact-Origin check.

`NEXT_PUBLIC_API_BASE_URL` remains for the older readiness client, which is not
used by the private shell. The generated `openapi.json` and
`src/lib/api/schema.d.ts` must be reviewed together after backend changes.
