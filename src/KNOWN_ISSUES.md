# AgentPay Guard — Known Issues & TODOs

Honest status board. Everything verified working is in `src/README.md`; this file lists
what's broken, unverified, or deliberately out of scope. Last updated: after the
live-MCP + real-checkout milestone.

---

## 🔴 Confirmed bugs (fix these first)

### 1. Stale approvals accumulate in `/guard/pending`
- **Where:** `src/backend/app/api/routes_guard.py` → `pending()`
- **What:** `USER_APPROVAL` requests that are never decided stay in the pending queue
  forever. During testing the queue grew to 11 stale items, and the Android LiveSync /
  Claude purchase flows have to filter around them.
- **Fix:** expire pending requests after the 5-minute authorization window
  (`request.timestamp + 300s < now` → mark `EXPIRED`, drop from pending), or add a
  cleanup sweep on each `payment-request`.

### 2. Android build not verified
- **Where:** `src/android/` (whole module)
- **What:** No Android SDK/Gradle in the build environment, so the Kotlin sources have
  **never compiled**. Several errors were found and fixed by hand (missing imports in
  `DecisionEngine.kt` / `GuardDecisionCard.kt`, `when`-subject mismatch in
  `ActivityScreen.kt`, `NotificationCompat.Action` mismatch, event-loop-blocking fixed
  on web only), but more may surface on first build.
- **Known leftovers (warnings, not errors):** unused `borderColor` val in
  `GuardDecisionCard.kt`, unused `TimeUnit` import in `PolicyEngine.kt`, unused
  `APPROVAL_LATENCY_MS` in `GuardRepository.kt`, unused `context` param in
  `GuardGraph.api()`.
- **Fix:** open in Android Studio → build → fix whatever surfaces. Expect 1–3 rounds.

### 3. Web TypeScript never compiled
- **Where:** `src/web/` (whole app)
- **What:** No Node.js in the build environment, so `tsc --noEmit` / `next build` has
  never run. The recent live-store rewrite touched 11 files; shapes were verified
  against the running API, but type errors are possible (e.g. recharts `Tooltip`
  formatter typings, `AbortSignal.timeout` DOM lib level).
- **Fix:** `cd src/web && npm install && npx tsc --noEmit` and fix fallout.

### 4. Live Razorpay payments stay `processing` until checkout completes
- **Where:** backend `finalize_payment`, MCP `purchase`
- **What:** With test keys the order is real, but capture only happens after the user
  completes Razorpay Checkout. If the user pays but closes the tab before the JS
  `handler` fires, the payment stays `authorized` — nothing captures it.
- **Fix:** configure a Razorpay webhook (`/guard/webhooks/razorpay` exists, needs
  `RAZORPAY_WEBHOOK_SECRET` + the ngrok URL set in the Razorpay dashboard) and capture
  `payment.authorized` events server-side.

---

## 🟠 Architecture gaps (real, accepted for hackathon)

### 5. No authentication anywhere
- Backend agent endpoints accept any `X-Agent-Key` (never validated). MCP server has an
  optional `GUARD_MCP_TOKEN` but it's unset by default, and Claude connectors won't send
  it anyway. The checkout confirm endpoint is unauthenticated.
- **Fix for production:** real agent identity (key pair per agent, signed requests), OAuth
  on the MCP server, auth token on the callback.

### 6. Android LiveSync only works while the app is open
- **Where:** `src/android/.../sync/LiveSync.kt`
- **What:** 4-second polling runs only while `MainActivity` is alive. App closed → no
  notifications. WorkManager's minimum periodic interval is 15 min, too slow.
- **Fix:** FCM push (needs a Firebase project), or a foreground service with a persistent
  notification.

### 7. Web dashboard polls; doesn't use the WebSocket
- **Where:** `src/web/lib/store.tsx` vs backend `/ws/events`
- **What:** 3-second polling works but the backend already broadcasts events the
  dashboard ignores.
- **Fix:** subscribe to `ws://{apiBase}/ws/events` and refresh on event + 30s fallback.

### 8. Physical Android phone can't reach `localhost:8000`
- **What:** `GuardGraph.backendBaseUrl` defaults to `http://10.0.2.2:8000` (emulator
  only). On a real phone you must edit `GuardGraph.kt` to your PC's LAN IP, and the
  backend must listen on `0.0.0.0` (it does).
- **Fix:** expose the backend through the same ngrok tunnel (add a route) or a second
  tunnel, and make the base URL a settings field instead of a constant.

### 9. `usesCleartextTraffic="true"` in the Android manifest
- **What:** required for plain-HTTP dev traffic, but a production no-no.
- **Fix:** network security config allowing cleartext only for the dev host, or TLS
  everywhere.

### 10. Intent data is write-only
- **What:** agents can create intents (`POST /agent/intent`) and requests reference
  `intentId`, but there's no `GET /intents`, so the web audit page can only show the
  intent ID, not the goal text.
- **Fix:** add `GET /intents` + include goal in `/audit/{id}` response.

---

## 🟡 Minor / quality

### 11. ML anomaly model is weak
- `src/ml` — risk model F1 ≈ 0.98, but IsolationForest anomaly precision ≈ 0.33 on the
  synthetic set. Features don't capture burst context well. Honest number, reported in
  `evaluation/metrics.json`. Needs better features (windowed velocity, merchant novelty
  score) before any real claim.

### 12. Backend state is a single JSON file
- `state.py` — fine for demo, loses everything on corruption, no concurrency story beyond
  a thread lock. Swap to SQLite/Postgres for anything real.

### 13. Simulation numbers differ between web and backend
- Both simulate 10k requests but distributions/timestamps were tuned separately
  (`src/web` version removed, backend `/simulate` is canonical now). The web Simulation
  page uses the backend — the old TS simulator was deleted, so this is resolved, but the
  backend distribution (per_day=8, 62% legit) should be revisited for realism.

### 14. `GuardGraph.api()` rebuilds Retrofit per call
- `src/android/.../GuardGraph.kt` — no client caching. Harmless at demo scale, lazy
  otherwise.

### 15. ngrok URL is ephemeral
- Free tunnel = new URL every restart → Claude connector, `GUARD_PUBLIC_URL`, and the
  checkout links all break. Use a reserved domain (ngrok free now offers 1 static domain)
  or Cloudflare Tunnel.

### 16. Razorpay secret was exposed in chat
- Rotate `RAZORPAY_KEY_SECRET` in the Razorpay dashboard before any demo you record or
  share. Keys live in `src/backend/.env` (gitignored ✓).

---

## ✅ Verified working (for contrast)

- Backend smoke test: 9/9 scenarios (approval → auth → capture, replay block, over-limit,
  splitting/circumvention, category block, simulation, audit chain)
- MCP remote server over ngrok: initialize / tools/list / search / purchase / block
- Claude web → real purchase → real Razorpay order (`order_TTiKcf8lSquwog`,
  `order_TTirzhmMBPWWGI`)
- Checkout page renders through the tunnel with real order + test key
- Reject path returns "user declined" to the agent
- LiveSync: backend request → phone notification → decision → backend (verified via API)
