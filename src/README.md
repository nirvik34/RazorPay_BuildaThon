# AgentPay Guard

> A local-first consent and authorization boundary for agentic commerce.
> AI agents discover and propose. AgentPay Guard evaluates and obtains consent. Razorpay executes.

## What this is

AgentPay Guard sits between autonomous AI shopping agents (ChatGPT / Claude / Gemini) and
payment execution. Whenever an agent reaches a payment action, the user gets a contextual
decision point: who wants to buy what, from whom, for how much, against which intent, and why
the Guard flagged it. Accept → a scoped, single-use, 5-minute authorization is issued and the
payment proceeds through Razorpay. Reject → the transaction is blocked, the reason stored, the
agent cannot silently retry.

The phone (Android app) is the trust anchor. The web dashboard is management/analytics only.

```
AI AGENT ──payment request──▶ GUARD (identity → intent → policy → risk → circumvention)
                                   │
                          ALLOW / USER_APPROVAL / BLOCK
                                   │
                        accept ──▶ scoped authorization ──▶ RAZORPAY ──▶ audit
```

## Layout

| Folder | What it is | Stack |
|---|---|---|
| `web/` | Control plane: dashboard, approvals queue, agents, policies, risk console, simulation, audit replay | Next.js 14 · TypeScript · Tailwind · Recharts |
| `backend/` | API surface: `/agent/payment-request`, approvals, scoped authorizations, Razorpay orders, webhooks, WS events, sync | FastAPI · pydantic v2 |
| `android/` | Local trust anchor: local decision engine, Room storage, Android Keystore signing, approval notifications with quick actions, offline-first | Kotlin · Compose · Room |
| `agent/` | Deterministic shopping-agent simulator with attack modes (stdlib-only Python) | Python |
| `ml/` | Synthetic dataset generator, risk model (GradientBoosting), anomaly model (IsolationForest), evaluation incl. circumvention detector tests | pandas · scikit-learn |

Shared spec: [`SPEC.md`](./SPEC.md) — data contract, decision-engine hierarchy, design tokens,
canonical demo story. The identical engine logic exists in TypeScript (`web/lib/engine.ts`),
Python (`backend/app/engine.py`) and Kotlin (`android/.../core/decision/DecisionEngine.kt`).

## Run it

### 1. Backend (port 8000)

```bash
cd src/backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
# health: curl localhost:8000/health   → {"status":"ok","mode":"razorpay-simulated",...}
```

Razorpay runs in simulated mode until `RAZORPAY_KEY_ID` / `RAZORPAY_KEY_SECRET` are set in
`.env` (copy `.env.example`). With keys present, approved authorizations create real test-mode
Orders and capture payments; webhooks verify signatures when `RAZORPAY_WEBHOOK_SECRET` is set.

End-to-end smoke test (no server needed):

```bash
python tests/smoke_test.py
```

Covers: legitimate purchase → approval → authorization → payment → single-use replay rejection,
over-limit block, splitting/circumvention detection, category block, policy simulation, audit chain.

### 2. Web dashboard (port 3000)

```bash
cd src/web
npm install
npm run dev
```

Fully usable standalone (local-first store seeded with the canonical demo story). If the backend
is running, Settings → Test Connection shows ONLINE; demo triggers and audit stay local by design.

### 3. Agent simulator (against the backend)

```bash
cd src/agent
python run_demo.py --mode all          # or: normal | over_limit | splitting | intent_mismatch | new_merchant | compromised
python run_demo.py --api http://localhost:8000 --mode splitting
```

Runs the PRD judge-demo scenes end-to-end against the live Guard.

### 4. Android

Open `src/android/` in Android Studio (Koala+), let Gradle sync, run on an emulator/device.
Use **Settings & Demo** inside the app to fire Normal / Over-limit / Splitting / Intent-mismatch /
Compromised-burst requests through the local engine. Approval notifications carry ACCEPT/REJECT
quick actions; freezing an agent blocks all further requests locally, offline included.
Optional backend URL defaults to `http://10.0.2.2:8000` for emulator sync.

### 5. ML

```bash
cd src/ml
pip install -r requirements.txt
python data/generate_dataset.py                 # 10k labeled synthetic requests
python training/train_risk_model.py             # blocked-vs-legit classifier
python training/train_anomaly_model.py          # IsolationForest behaviour baseline
python evaluation/evaluate.py                   # metrics + circumvention detector unit tests
```

## Demo script (judge flow)

1. **Legitimate purchase** — Claude buys Sony WH-1000XM5 ₹14,499 within a ₹15K intent → approval card → ACCEPT → Razorpay order captured → green audit record.
2. **Over-limit** — Gemini tries MacBook ₹42,000 vs ₹20,000 limit → hard BLOCK, no prompt, reason stored.
3. **Splitting** — ₹9,800 + ₹9,700 + ₹9,900 same session → each under limit, but the Guard correlates the sequence → third request BLOCKED as CIRCUMVENTION_DETECTED (aggregate ₹29,400).
4. **Intent mismatch** — intent says "monitor", agent buys a gift card → BLOCK before any prompt.
5. **Compromised agent** — 10-request burst raises velocity signals → CRITICAL ANOMALY on Risk page → FREEZE AGENT → next request dies with AGENT_FROZEN.

Every scene lands in the audit timeline (`/audit/<request_id>`): request received → authenticated →
policy evaluated → risk assessed → notified/decided → authorization → payment captured.

## Design language

Guard Blue `#2563EB` for infrastructure/actions · navy sidebar as the security boundary ·
green = approved only · red = rejected/blocked only · amber = action required · purple = AI intent.
Amounts are the focal point of every approval. See `SPEC.md` §3 and `docs/design.txt`.
