# AgentPay Guard — Known Issues & TODOs

Status board. Updated after the "remove hardcoded data" + issue-fixing pass.
Fixed items stay listed with their resolution for reference.

---

## ✅ Fixed this pass

### 1. Stale approvals accumulated in `/guard/pending` — FIXED
- `pending()` now auto-expires `USER_APPROVAL` requests older than 5 minutes:
  marks them resolved (`action: "expire"`), appends an
  "Approval window elapsed" audit event, and broadcasts `approvals_expired`.
- Verified live: backdated request disappeared from pending after the sweep.

### 2. Android compiler warnings — CLEANED
- Removed unused `borderColor` (`GuardDecisionCard.kt`), `TimeUnit` import
  (`PolicyEngine.kt`), `APPROVAL_LATENCY_MS` (`GuardRepository.kt`).
- Full compile still unverified — see open item below.

### 4. Uncaptured payments when the checkout tab closes — FIXED (needs config to arm)
- `POST /guard/webhooks/razorpay` now handles `payment.authorized`:
  verifies → **captures server-side** → updates payment + audit + WS broadcast.
- Signature check enforced when `RAZORPAY_WEBHOOK_SECRET` is set.
- **To arm:** add the webhook in the Razorpay dashboard pointing at
  `https://<your-tunnel>/guard/webhooks/razorpay` with the same secret.
- Verified: bad signature → HTTP 400.

### 6. No notifications when the app is closed — MITIGATED
- `SyncWorker` (15-min WorkManager) now also pulls `/guard/pending` and raises
  approval notifications, not just audit sync.
- Fast path remains `LiveSync` (4s polling while app is open). True push still
  needs FCM — open item below.

### 7. Web dashboard ignored the WebSocket — FIXED
- `lib/store.tsx` subscribes to `ws://{apiBase}/ws/events`, debounced refresh
  (1/sec), auto-reconnect every 5s, polling relaxed to a 15s fallback.

### 8. Physical phone couldn't reach the backend — FIXED
- Backend URL is now a **Settings field** in the app (persisted via
  SharedPreferences, Retrofit client invalidated on change).
- Emulator default `http://10.0.2.2:8000`; physical phone → PC's LAN IP.

### 9. Blanket cleartext traffic — SCOPED
- Replaced `usesCleartextTraffic` with `network_security_config.xml`:
  cleartext only for `10.0.2.2` / `localhost` / `127.0.0.1`. LAN IPs must be
  added to the XML for physical-phone testing. Everything else HTTPS-only.

### 10. Intent data write-only — FIXED
- `GET /intents` added; `/audit/{id}` now returns the full `intent` object.
- Web audit page shows the real intent goal text when available.

### 11. Weak ML anomaly model — IMPROVED
- Added burst-context features: `night_hour`, `velocity_x_amount`,
  `novelty_pressure` (unknown merchant × unfamiliar category × night).
- Anomaly model: precision **0.33 → 0.52**, recall **0.28 → 0.62**.
- Risk model unchanged at F1 0.98. Circumvention tests all pass.

### 14. Retrofit client rebuilt per call — FIXED
- `GuardGraph.api()` now caches the client and invalidates only when the
  backend URL changes (`setBackendBaseUrl`).

---

## 🔴 Still open

### A. Android full compile unverified
- No SDK in this environment. Sources were hand-checked (imports, API usage)
  but `gradlew assembleDebug` has never run. Expect a round of small fixes.

### B. Web TypeScript compile unverified
- No Node here. `tsc --noEmit` has never run against the live-store rewrite.
- Run: `cd src/web && npm install && npx tsc --noEmit`.

### C. Authentication (production)
- Agent endpoints trust a registered `agentId` (unknown agents get 401) but
  there's no cryptographic identity. Checkout confirm is unauthenticated.
- Production: per-agent key pairs + signed requests, OAuth on MCP.

### D. State is a single JSON file
- `state.py` — fine for demo. Swap to SQLite/Postgres for durability.

### E. ngrok URL is ephemeral
- Reserve a static ngrok domain or use Cloudflare Tunnel; then update the
  Claude connector + checkout links once.

### F. Rotate the Razorpay key secret
- It appeared in chat during setup. Rotate in the Razorpay dashboard before
  recording/sharing any demo. `.env` is gitignored.

### G. True push notifications (FCM)
- The 15-min WorkManager sweep is best-effort. Real-time when the app is
  closed requires a Firebase project + FCM.

---

## ✅ Verified working

- Backend smoke test: approval → auth → capture, single-use replay block,
  over-limit, splitting/circumvention, category block, simulation, audit chain
- MCP served **from the backend itself** (`:8000/mcp`) — one tunnel for API +
  MCP + checkout pages; Claude connector validated against the live URL
- Claude web → real purchase → real Razorpay orders
  (`order_TTiKcf8lSquwog`, `order_TTirzhmMBPWWGI`, `order_TTtR5iMhXTFP6n`)
- Razorpay Checkout page renders through the tunnel with real order + key
- Reject path returns "user declined" to the agent; expired approvals resolve
  themselves
- LiveSync: backend request → phone notification → decision → backend
- Web + Android are fully live-data driven — no seed/demo data anywhere
