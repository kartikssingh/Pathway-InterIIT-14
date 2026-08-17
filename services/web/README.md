# FraudGuard Console

The operator-facing web console: KYC records, transaction monitoring, alert
review and superadmin dashboards. Next.js 16 (App Router), React 19, Tailwind 4,
shadcn/ui.

```
services/web/
├── src/
│   ├── app/           routes (App Router)
│   ├── components/    shared components; `ui/` is shadcn
│   ├── hooks/         data hooks, one module per domain
│   ├── lib/
│   │   ├── api/       the API client, split by domain
│   │   ├── format.ts  currency, dates, risk bands
│   │   └── transformers.ts  API shapes → component shapes
│   └── data/          static fixtures
└── public/
```

---

## Quick start

```bash
cd services/web
pnpm install                 # or npm install
cp .env.example .env.local   # point NEXT_PUBLIC_API_BASE_URL at the API
pnpm dev                     # http://localhost:3000
```

The API must be running (`services/api`, port 8001 by default) or the console
shows its "server unavailable" screen.

```bash
pnpm check      # typecheck + lint
pnpm build      # production build
```

---

## The API layer

`@/lib/api` is a directory, not a file. Existing imports are unchanged.

```ts
import { userApi, alertApi, ApiError } from "@/lib/api";
import { formatCurrency, getRiskCategory } from "@/lib/format";
```

| Module | Covers |
| --- | --- |
| `client.ts` | fetch wrapper: auth header, retries, timeouts, error parsing, session |
| `types.ts` | request/response types mirroring the API schemas |
| `users.ts` · `transactions.ts` · `dashboard.ts` · `alerts.ts` | domain endpoints |
| `risk-history.ts` | toxicity history and sanction matches |
| `auth.ts` | login/logout and the browser session |
| `superadmin.ts` | audit logs, metrics, health checks, system alerts |

Failures throw an `ApiError`, so a component can branch on the cause instead of
matching on a message string:

```ts
try {
  await userApi.suspendUser(id, reason);
} catch (error) {
  if (error instanceof ApiError && error.isForbidden) showPermissionNotice();
  else toast(describeError(error));
}
```

`error.userMessage` is always safe to show to an operator.

---

## Data hooks

`@/hooks/useApi` is also a barrel; the hooks live in `useUsers.ts`,
`useTransactions.ts`, `useDashboard.ts`, `useAlerts.ts`, `useRiskHistory.ts` and
`useSuperadmin.ts`, all built on `useApiState`.

```ts
const { users, loading, error, refetch } = useUsers({ limit: 50 });
```

---

## Conventions

* **Risk scores are 0-1 everywhere** — in the database, over the wire and in
  state. Convert to a percentage only at render time, with `formatRiskScore`.
* **Never format inline.** `formatCurrency`, `formatDate`, `formatRelativeTime`
  and `getRiskColor` all live in `@/lib/format` and all handle `null`.
* **Wrap risky panels** in `<ErrorBoundary label="...">` so one failure does not
  blank the page.
* **Environment variables** are read once, in `lib/api/client.ts`. Nothing else
  should reach for `process.env`.

---

## What changed in the refactor

* `lib/api.ts` (1,710 lines) and `hooks/useApi.ts` (1,497 lines) are split into
  focused modules behind barrels, so no import in the app had to change.
* The fetch helper was rebuilt: it no longer `console.log`s every response body
  (customer PII was going to the browser console in production), and it gained
  timeouts, abort support, retries on network/5xx, parsing of both the new and
  old API error shapes, and an automatic sign-out on 401 — an expired token used
  to leave every panel failing with no explanation.
* The 12-line `URLSearchParams` block that had been pasted into ~30 functions is
  one `buildQuery` helper; several copies were missing the `undefined` guard and
  were sending the literal string `"undefined"` to the API.
* The health check probed `/` and treated 404 and 405 as healthy, so the console
  showed green whenever *anything* was listening on the port. It now calls
  `/health/live`. Its config object was also rebuilt every render, which
  recreated the polling interval each time.
* `useApiState` used to clear `data` on failure, blanking a populated table on a
  transient error, and set state after unmount. Both fixed.
* Added an error boundary, real page metadata (the tab still said "Create Next
  App"), security headers, a strict production build, and `.env.example`.
* Removed three stale `.backup` files that were being kept next to the modules
  they duplicated.
