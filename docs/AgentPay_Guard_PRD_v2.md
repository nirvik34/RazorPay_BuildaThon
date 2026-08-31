# AgentPay Guard — Product Requirements Document

**Version:** 2.0  
**Status:** Final hackathon PRD  
**Primary product:** Local-first Android app  
**Secondary product:** Web control plane  
**Core integrations:** AI shopping agents, Razorpay  
**AI ecosystems:** ChatGPT, Claude, Gemini  
**Core thesis:** Let AI agents shop autonomously while keeping the user in control of every consequential payment.

---

# 1. Executive Summary

AgentPay Guard is a **local-first Android consent and authorization gateway for autonomous AI shopping agents**.

The intended future flow is already becoming real: an AI assistant can search the web, compare products, choose a merchant, prepare checkout, and invoke payment infrastructure. Razorpay has publicly demonstrated agentic payment experiences across ChatGPT, Gemini and Claude and supports UPI Reserve Pay, where users can pre-authorize a spending boundary and agents can transact within it. Razorpay also provides AI-ready MCP/API infrastructure. citeturn0search2turn0search7turn0search9

AgentPay Guard does **not** replace the AI agent and does **not** replace Razorpay.

It sits between them:

```text
USER
  │
  │ "Find headphones under ₹15,000"
  ▼
CHATGPT / CLAUDE / GEMINI
  │
  │ Search → Compare → Select → Checkout
  │
  │ Payment request
  ▼
┌─────────────────────────────────────────────┐
│              AGENTPAY GUARD                 │
│                                             │
│ Agent identity                              │
│ User intent                                 │
│ Authority / spending policy                 │
│ Merchant + transaction context              │
│ Risk / behavioural analysis                 │
│ Circumvention detection                     │
│ Human approval                              │
│ Local audit                                 │
└──────────────────┬──────────────────────────┘
                   │
             ACCEPT / BLOCK
                   │
                   ▼
                RAZORPAY
                   │
                   ▼
             PAYMENT / ORDER
```

The core user experience is simple:

> **Whenever an AI agent reaches a shopping/payment action, AgentPay Guard gives the user a clear, contextual decision point.**

If the user accepts, a scoped authorization is issued and the transaction proceeds through Razorpay.

If the user rejects, the payment is blocked, the rejection reason is stored, and the agent receives a structured denial.

The Android phone is the **local trust anchor**. The cloud and web dashboard are optional management and synchronization layers, not mandatory components for every authorization decision.

---

# 2. Research Basis

## 2.1 Agentic payments are already moving into production

Razorpay describes UPI Reserve Pay as a model where a user authorizes a spending capacity once and a merchant/agent can debit within that approved boundary. Razorpay explicitly positions this as infrastructure for agentic commerce. citeturn0search2turn0search3

Razorpay also states that its agentic payment demonstrations include ChatGPT, Gemini and Claude, with users able to authorize agents within predefined spending limits. citeturn0search7turn0search9

Therefore:

**Not novel enough:**
```text
AI → find product → Razorpay → pay
```

**Product opportunity:**
```text
AI → financial action → independent user consent boundary → Razorpay
```

## 2.2 Why a separate consent layer matters

An agent may receive a broad instruction:

> "Buy me a monitor under ₹20,000."

Between that instruction and payment, the agent can make many decisions:

- which product
- which merchant
- whether to add accessories
- whether to substitute a product
- whether to retry
- whether to follow instructions embedded in a webpage
- whether to split purchases
- whether to choose a new merchant

A spending limit alone does not express all of these constraints.

AgentPay Guard therefore evaluates the **specific action**, not merely whether the agent has some general permission to spend.

---

# 3. Problem Statement

AI agents are gaining the ability to act on behalf of users in commerce.

Traditional payment authorization is largely centered on:

> "Is this payment authenticated?"

Autonomous agents create a different question:

> "Is this exact financial action still within the authority and intent the user delegated to this agent?"

AgentPay Guard addresses:

1. **Over-authority** — agent exceeds configured financial boundaries.
2. **Intent drift** — transaction no longer matches the user's request.
3. **Merchant risk** — agent selects an unfamiliar or disallowed merchant.
4. **Category violations** — agent buys something outside allowed categories.
5. **Transaction splitting** — multiple individually valid payments circumvent an aggregate limit.
6. **Behavioural anomalies** — an agent suddenly behaves very differently from its baseline.
7. **Prompt/web manipulation** — external content causes the agent to request an unrelated purchase.
8. **Unauthorized retry** — an agent attempts a previously rejected action again.
9. **Lack of explainability** — user cannot later determine why a payment was allowed or rejected.

---

# 4. Product Vision

> **Make autonomous AI shopping safe enough to delegate without surrendering financial control.**

### Product principle

**The AI can discover and propose. AgentPay Guard evaluates and obtains consent. Razorpay executes.**

The LLM is not the final financial authority.

---

# 5. Product Surfaces

## 5.1 Android App — Primary Product

The Android app is the user's trusted financial control device.

It handles:

- payment/action notifications
- accept/reject
- local policy enforcement
- agent identity
- local spending state
- risk state
- freeze/revoke
- local audit history
- offline/local authorization decisions

The app must work without the laptop or web dashboard.

## 5.2 Web Dashboard — Secondary Control Plane

The web app handles:

- agent management
- detailed policy configuration
- analytics
- simulation
- audit/replay
- model evaluation
- synchronized history
- advanced settings

It must not be required for each transaction.

## 5.3 Cloud Backend

The backend handles:

- synchronization
- backup
- multi-device state
- analytics
- web APIs
- optional notification infrastructure
- Razorpay integration
- agent connector services

The backend must not be the single point of authorization failure.

---

# 6. Core User Journey

## Example: legitimate purchase

User tells Claude:

> "Find me noise-cancelling headphones under ₹15,000."

Claude searches the web and selects:

```text
Sony WH-1000XM5
Amazon
₹14,499
```

Claude sends a structured payment request.

AgentPay Guard evaluates it.

The phone displays:

```text
🟠 ACTION REQUIRED

Claude Shopping Agent

Sony WH-1000XM5
Amazon
₹14,499

User intent:
"Headphones under ₹15,000"

Checks:
✓ Within budget
✓ Allowed category
✓ Agent authorized

Risk:
LOW

[ REJECT ]     [ ACCEPT ]
```

### If user accepts

```text
🟢 APPROVED

Claude is authorized to complete
this purchase.

₹14,499
Amazon
Sony WH-1000XM5
```

A scoped authorization is created and the guarded payment tool can proceed to Razorpay.

### If user rejects

```text
🔴 REJECTED

Sony WH-1000XM5
₹14,499

Reason:
User rejected transaction.

Authorization denied.
Decision stored.
```

The agent receives a structured denial and cannot silently execute the payment.

---

# 7. Notification UX

Notifications are the most important mobile interaction.

Every notification should answer:

- **Who?** Agent identity
- **What?** Product/action
- **Where?** Merchant
- **How much?** Amount
- **Why?** Flag reason/context
- **What can I do?** Accept / Reject

Example:

```text
┌───────────────────────────────────┐
│ 🟠 AI PURCHASE REQUEST            │
│                                   │
│ Claude Shopping Agent             │
│                                   │
│ Sony WH-1000XM5                   │
│ Amazon                            │
│ ₹14,499                           │
│                                   │
│ Intent                             │
│ Headphones under ₹15,000          │
│                                   │
│ ✓ Budget valid                    │
│ ✓ Category allowed                │
│ ⚠ New merchant                    │
│                                   │
│ [ REJECT ]       [ ACCEPT ]       │
└───────────────────────────────────┘
```

### Visual status system

**Green border:** approved

**Red border:** rejected or blocked

**Amber border:** waiting for user action

**Neutral:** informational event

Do not use red for every warning. Red means a negative security/authorization outcome.

---

# 8. Android Activity Feed

The user should have a permanent local timeline.

```text
TODAY

┌───────────────────────────────┐
│ 🟢 APPROVED                  │
│ Claude → Amazon              │
│ Sony WH-1000XM5              │
│ ₹14,499                      │
│ User approved                │
└───────────────────────────────┘

┌───────────────────────────────┐
│ 🔴 REJECTED                  │
│ Gemini → Unknown Merchant    │
│ ₹28,900                      │
│ Exceeded ₹20K limit          │
└───────────────────────────────┘

┌───────────────────────────────┐
│ 🔴 BLOCKED                   │
│ ChatGPT → Gift Card          │
│ ₹5,000                       │
│ Category disabled            │
└───────────────────────────────┘
```

Every event has:

- agent
- merchant
- product
- amount
- timestamp
- decision
- reason
- payment outcome

---

# 9. Local-First Requirement

This is a hard requirement.

The phone must be capable of performing **core authorization and hard-policy decisions without the web dashboard or cloud backend**.

### Local data

Store locally:

- agent identity
- policies
- current spending counters
- pending approvals
- recent transactions
- risk state
- decision records
- agent freeze state

### Cloud data

Synchronize:

- audit backup
- analytics
- historical records
- multi-device state
- simulation results

### Architecture

```text
                 ANDROID
                    │
       ┌────────────┴────────────┐
       │                         │
LOCAL DECISION              LOCAL AUDIT
       │                         │
       └────────────┬────────────┘
                    │
              Sync when online
                    │
                    ▼
              CLOUD BACKEND
                    │
                    ▼
              WEB DASHBOARD
```

If the internet/cloud is temporarily unavailable:

```text
Agent request
      ↓
Local Guard
      ↓
Local policy
      ↓
Local decision
      ↓
Notification
```

The actual online payment still requires network connectivity to the merchant/payment infrastructure. Local-first means **authorization is not cloud-dependent**.

---

# 10. Agent Integration

The prototype should not claim to modify or intercept the internal implementation of consumer ChatGPT, Claude or Gemini.

Instead, use a controlled agent/tool interface:

```text
ChatGPT / Claude / Gemini
          │
          ▼
   Guarded payment tool
          │
          ▼
    AgentPay Guard
          │
          ▼
      Authorization
          │
          ▼
       Razorpay
```

For the hackathon, build a deterministic shopping-agent simulator that behaves like a real external agent.

The simulator allows reliable demonstration of:

- normal purchase
- over-limit purchase
- intent mismatch
- new merchant
- transaction splitting
- compromised-agent behaviour

---

# 11. Agent Identity

Every agent must have an explicit identity.

```text
Agent:
Claude Shopping Agent

Agent ID:
agent_7F91

Owner:
User-001

Status:
ACTIVE

Authority:
₹10,000 / transaction
₹30,000 / day
```

For the stronger implementation, the agent identity is associated with a cryptographic key.

The Guard verifies that a request came from a registered agent rather than trusting an arbitrary string such as `"claude"`.

---

# 12. Authority Model

Users configure what an agent is allowed to do.

Example:

```yaml
agent: shopping-agent

per_transaction_limit: 10000
daily_limit: 30000

allowed_categories:
  - electronics
  - groceries
  - office_supplies

blocked_categories:
  - gambling
  - cryptocurrency
  - gift_cards

approval_required:
  - new_merchant
  - international
  - amount_above_10000
```

Authority must be enforced locally.

Hard constraints cannot be overridden by an LLM or risk model.

---

# 13. Intent Model

Natural language may be converted into structured intent.

Example:

> "Find me a good monitor under ₹20,000."

Structured intent:

```json
{
  "category": "electronics",
  "item_type": "monitor",
  "maximum_budget": 20000,
  "currency": "INR"
}
```

The LLM may perform interpretation.

The authorization engine operates on the resulting structured constraints.

---

# 14. Intent Verification

The system compares:

```text
USER INTENT
     ↓
AGENT SELECTION
     ↓
TRANSACTION
```

Example:

```text
Intent:
"Buy office equipment under ₹5,000"

Agent transaction:
Gaming headset
₹4,700
```

Result:

```text
INTENT MISMATCH
Category incompatible

→ BLOCK / HUMAN APPROVAL
```

This protects against an agent making a technically affordable but semantically unauthorized purchase.

---

# 15. Decision Engine

The decision engine is deterministic.

Simplified hierarchy:

```text
IF agent revoked
    → BLOCK

IF agent frozen
    → BLOCK

IF category prohibited
    → BLOCK

IF merchant prohibited
    → BLOCK

IF amount > hard transaction limit
    → BLOCK

IF cumulative exposure > hard daily limit
    → BLOCK

IF severe intent mismatch
    → BLOCK

IF circumvention detected
    → BLOCK

IF new merchant requires approval
    → HUMAN APPROVAL

IF risk is high and policy requires review
    → HUMAN APPROVAL

OTHERWISE
    → USER APPROVAL / ALLOW
```

The key principle:

> **Models can recommend. Policies constrain. The decision engine authorizes.**

---

# 16. Risk Engine

The risk engine provides contextual risk.

### Transaction features

- amount
- category
- merchant
- currency
- timestamp
- payment method
- transaction frequency

### Agent features

- historical amount distribution
- transaction velocity
- merchant familiarity
- category familiarity
- previous rejections
- previous blocks
- current trust state

### Context

- user intent
- session
- merchant novelty
- cumulative exposure

Output:

```text
risk_score: 0–100

LOW
MEDIUM
HIGH
CRITICAL
```

A low risk score cannot override a hard policy violation.

---

# 17. Behavioural Anomaly Detection

The system maintains a baseline per agent.

Example:

```text
NORMAL

Transactions/day: 5–8
Typical amount: ₹1K–₹8K
Typical categories:
electronics / groceries

Typical hours:
08:00–20:00
```

Observed:

```text
21 transactions
₹92,000
8 minutes
new merchants
00:14
```

Result:

```text
CRITICAL ANOMALY

Recommended:
FREEZE AGENT
```

The behaviour model can initially use:

- Isolation Forest
- rolling statistical baselines
- velocity thresholds

---

# 18. Transaction-Splitting Detection

This is one of the core technical demonstrations.

Policy:

```text
Per transaction: ₹10,000
```

Agent attempts:

```text
₹9,800
₹9,700
₹9,900
```

A naive system approves all three.

AgentPay Guard evaluates the sequence:

- same agent
- same session
- same merchant
- same category
- short time interval
- similar amounts
- aggregate exposure

Result:

```text
CIRCUMVENTION DETECTED

Aggregate:
₹29,400

Circumvention score:
96/100

Decision:
BLOCK
```

This feature is intentionally algorithmic rather than LLM-based.

---

# 19. Agent Freeze

The Android app provides:

```text
Agent:
Claude Shopping Agent

Status:
ACTIVE

[ FREEZE AGENT ]
```

After freezing:

```text
Any new request
       ↓
Local Guard
       ↓
AGENT_FROZEN
       ↓
BLOCK
```

The freeze must work without the cloud.

---

# 20. Approval Lifecycle

```text
REQUESTED
    ↓
EVALUATING
    │
    ├───────────────┐
    ▼               ▼
AUTO-BLOCK       USER REQUIRED
                    │
              ┌─────┴─────┐
              ▼           ▼
           ACCEPT       REJECT
              │           │
              ▼           ▼
         AUTHORIZED     BLOCKED
              │
              ▼
           RAZORPAY
              │
         ┌────┴────┐
         ▼         ▼
      SUCCESS    FAILURE
         │         │
         └────┬────┘
              ▼
          AUDIT LOG
```

---

# 21. Scoped Authorization

When the user accepts a transaction, create a scoped authorization.

Example:

```json
{
  "authorization_id": "auth_981",
  "agent_id": "claude-shopping-01",
  "merchant": "amazon",
  "amount": 14499,
  "currency": "INR",
  "intent_id": "intent_183",
  "expires_at": "2026-08-24T20:48:00+05:30",
  "status": "AUTHORIZED"
}
```

Authorization should be:

- scoped to the request
- short-lived
- non-reusable where appropriate
- tied to merchant/amount/intent
- invalid after expiration
- recorded in the audit log

A rejected request must not create an executable authorization.

---

# 22. Razorpay Integration

Razorpay remains the payment execution layer.

Potential components:

- Razorpay MCP
- Razorpay APIs
- Orders
- Payments
- Webhooks
- UPI Reserve Pay where appropriate

Razorpay documents UPI Reserve Pay as a mechanism where funds can be reserved within a user-approved amount and debited as the service/product is delivered. citeturn0search3

AgentPay Guard should not recreate that rail.

Its role is:

```text
Agent
 ↓
Guarded authorization
 ↓
Razorpay
 ↓
Payment
```

---

# 23. Data Flow

```text
                       USER
                        │
                        │ goal
                        ▼
                ┌───────────────┐
                │ AI AGENT      │
                │ ChatGPT       │
                │ Claude        │
                │ Gemini        │
                └───────┬───────┘
                        │
                  search / choose
                        │
                 payment request
                        │
                        ▼
          ┌─────────────────────────────┐
          │       ANDROID GUARD         │
          │                             │
          │ Agent Identity              │
          │      ↓                      │
          │ Intent Verification         │
          │      ↓                      │
          │ Authority / Policy          │
          │      ↓                      │
          │ Risk Model                  │
          │      ↓                      │
          │ Behaviour Model             │
          │      ↓                      │
          │ Circumvention Detector      │
          │      ↓                      │
          │ Decision Engine             │
          └─────────────┬───────────────┘
                        │
                  ┌─────┼──────┐
                  ▼     ▼      ▼
                ALLOW  ASK    BLOCK
                        │
                        ▼
                     USER
                  ACCEPT/REJECT
                        │
                        ▼
                  AUTHORIZATION
                        │
                        ▼
                    RAZORPAY
                        │
                        ▼
                 PAYMENT / ORDER
                        │
                        ▼
                     WEBHOOK
                        │
                        ▼
                  LOCAL AUDIT
                        │
                 sync when online
                        │
                        ▼
                  CLOUD BACKEND
                        │
                        ▼
                  WEB DASHBOARD
```

---

# 24. Android Architecture

```text
┌─────────────────────────────────────────┐
│              ANDROID APP                │
│                                         │
│  Jetpack Compose UI                     │
│          │                              │
│          ▼                              │
│  Application / ViewModels               │
│          │                              │
│          ▼                              │
│  LOCAL GUARD RUNTIME                    │
│  ├── Authority                          │
│  ├── Policy                             │
│  ├── Intent                             │
│  ├── Risk                               │
│  ├── Circumvention                      │
│  └── Decision                           │
│          │                              │
│          ▼                              │
│  Room / SQLite                          │
│  ├── Agents                             │
│  ├── Policies                           │
│  ├── Approvals                          │
│  ├── Transactions                       │
│  └── Audit                              │
│          │                              │
│          ▼                              │
│  Android Keystore                       │
└─────────────────────────────────────────┘
```

---

# 25. Android Technology Stack

- **Kotlin**
- **Jetpack Compose**
- **Room + SQLite**
- **Android Keystore**
- **WorkManager**
- **Kotlin Coroutines**
- **Kotlin Serialization**
- **Retrofit / OkHttp**
- **BiometricPrompt**
- **ONNX Runtime for Android** if ML inference is deployed locally

Why Kotlin instead of React Native:

The mobile app is not just a UI. It is the local trust anchor and must own secure storage, local decision state, cryptographic identity, background work and offline behaviour. Kotlin gives direct Android-native control.

---

# 26. Web Technology Stack

- Next.js
- TypeScript
- Tailwind CSS
- shadcn/ui
- Recharts

Web responsibilities:

- agent management
- policy management
- analytics
- simulation
- audit/replay
- synchronized history

---

# 27. Backend Technology Stack

- Python
- FastAPI
- PostgreSQL
- Redis

Backend responsibilities:

- synchronization
- authentication
- web APIs
- analytics
- audit backup
- multi-device state
- Razorpay integration
- optional agent gateway

---

# 28. ML Stack

- Python
- pandas
- NumPy
- scikit-learn
- XGBoost
- ONNX

Suggested models:

### Model 1 — Behaviour anomaly

Isolation Forest or statistical baseline.

### Model 2 — Transaction risk

XGBoost.

### Model 3 — Circumvention

Deterministic sequence/velocity/aggregate analysis initially.

Do not use an LLM as the final payment-risk classifier.

---

# 29. LLM Role

The LLM is useful for:

```text
Natural language
      ↓
Intent extraction
      ↓
Structured constraints
```

Example:

> "Get me a decent monitor under 20k, nothing fancy."

Structured:

```json
{
  "category": "monitor",
  "maximum_budget": 20000,
  "quality_preference": "standard"
}
```

The LLM must **not** be responsible for:

```text
"Is this payment safe?"
```

and then directly authorizing it.

The project must remain useful even if the LLM provider changes.

---

# 30. Web Dashboard

## Dashboard

Show:

- active agents
- pending approvals
- approved payments
- blocked payments
- current spending
- risk events

## Agents

```text
Claude Shopping Agent
ACTIVE
Trust: 94

Today:
6 transactions
₹18,420

₹10K transaction limit
₹30K daily limit
```

## Policies

Configure:

- limits
- categories
- merchants
- approval rules
- time windows

## Simulation

Test policy changes against synthetic/historical requests.

## Audit

Replay:

```text
Intent
 ↓
Agent request
 ↓
Policy
 ↓
Risk
 ↓
Decision
 ↓
User action
 ↓
Payment
 ↓
Outcome
```

---

# 31. Local Data Model

## Agent

```text
agent_id
owner_id
name
status
public_key
policy_id
trust_score
risk_state
created_at
```

## Policy

```text
policy_id
version
transaction_limit
daily_limit
monthly_limit
allowed_categories
blocked_categories
allowed_merchants
blocked_merchants
approval_rules
```

## Intent

```text
intent_id
agent_id
goal
category
budget
constraints
created_at
expires_at
```

## Transaction Request

```text
request_id
agent_id
intent_id
merchant
amount
currency
category
session_id
timestamp
```

## Decision

```text
decision_id
request_id
decision
risk_score
intent_score
circumvention_score
reason_codes
policy_version
timestamp
```

## Audit Event

```text
event_id
decision_id
event_type
actor
timestamp
payload
```

---

# 32. Audit and Replay

Every financial request creates an audit record.

Example:

```text
20:42:01
User intent received

20:42:12
Claude requested ₹14,499

20:42:12
Authority checked

20:42:12
Policy passed

20:42:12
Risk = LOW

20:42:13
User notified

20:42:25
User ACCEPTED

20:42:25
Authorization issued

20:42:31
Razorpay payment initiated

20:42:34
Payment captured
```

The user can replay the complete decision chain.

This is the product's **financial flight recorder**.

---

# 33. Security Principles

## Least privilege

Agents receive only required authority.

## Explicit delegation

Every agent has an owner and policy.

## Hard constraints

No LLM/model can override hard limits.

## Local enforcement

Core policies work without cloud.

## Human escalation

Ambiguous transactions require user action.

## Immediate freeze

User can freeze an agent from the phone.

## Scoped authorization

Approval applies to a specific request, not an unrestricted payment credential.

## Auditability

Every decision has reason codes, policy version and timestamp.

---

# 34. Threat Scenarios

## A. Over-limit

```text
Limit: ₹20K
Request: ₹42K
→ BLOCK
```

## B. Transaction splitting

```text
₹9.8K + ₹9.7K + ₹9.9K
→ CIRCUMVENTION
→ BLOCK
```

## C. Intent mismatch

```text
Intent: Monitor
Request: Gift card
→ BLOCK
```

## D. New merchant

```text
Amount valid
Category valid
Merchant unknown
→ USER APPROVAL
```

## E. Compromised behaviour

```text
Normal: 5 transactions/day
Observed: 20 in 10 minutes
→ ANOMALY
→ FREEZE
```

## F. Rejected retry

```text
User rejects request
→ authorization denied
→ agent informed
→ same request cannot silently execute
```

---

# 35. MVP

The MVP should not attempt to solve every type of financial action.

Focus on:

> **AI shopping → payment request → Android notification → user decision → Razorpay test payment → audit.**

### Required MVP components

1. Android app
2. Local policy engine
3. Agent identity
4. Payment request protocol
5. Notification system
6. Accept/reject
7. Scoped authorization
8. Razorpay test integration
9. Local activity/audit
10. Transaction splitting detector
11. Intent mismatch detector
12. Agent freeze
13. Web dashboard
14. Shopping-agent simulator

---

# 36. Agent Simulator

For the hackathon, implement a deterministic shopping-agent simulator.

```text
shopping_agent/
├── search_catalog()
├── compare_products()
├── select_product()
├── create_checkout()
└── request_payment()
```

Modes:

```text
NORMAL
OVER_LIMIT
INTENT_MISMATCH
TRANSACTION_SPLITTING
NEW_MERCHANT
COMPROMISED
```

This makes the demo deterministic and repeatable.

---

# 37. Judge Demo

Do not begin with a dashboard.

Begin with the actual problem.

### Scene 1 — legitimate purchase

```text
Claude
→ Sony headphones
→ ₹14,499
→ Android notification
→ ACCEPT
→ Razorpay
→ order complete
→ GREEN record
```

### Scene 2 — dangerous purchase

```text
Claude
→ MacBook
→ ₹42,000
→ limit = ₹20,000
→ RED flag
→ REJECT
→ payment blocked
→ reason stored
```

### Scene 3 — circumvention

```text
Agent:
₹9,800
₹9,700
₹9,900

Each transaction < ₹10K

Guard:
Aggregate pattern detected
→ BLOCK
```

### Scene 4 — intent manipulation

```text
User:
"Buy a monitor"

Agent:
Gift card ₹10,000

Guard:
Intent mismatch
→ BLOCK
```

### Scene 5 — compromised agent

```text
Normal:
5 transactions/day

Sudden:
20 transactions / 10 min

Android:
🚨 CRITICAL ANOMALY

[ FREEZE AGENT ]

→ local freeze
```

This sequence demonstrates the product in minutes.

---

# 38. Success Metrics

Use a reproducible synthetic dataset.

Example test structure:

```text
10,000 requests

Legitimate
Over-limit
Intent mismatch
New merchant
Circumvention
Behaviour anomaly
Compromised-agent cases
```

Measure:

- authorization accuracy
- circumvention detection rate
- false-positive rate
- intent mismatch detection
- anomaly detection
- local decision latency
- offline policy coverage
- successful Razorpay execution after approval

Do not invent final metrics. Generate them from the implementation.

---

# 39. Acceptance Criteria

### Android

- [ ] App works independently of web dashboard.
- [ ] Policies persist locally.
- [ ] Agent identity persists locally.
- [ ] Payment request creates notification.
- [ ] User can accept.
- [ ] User can reject.
- [ ] Rejection reason is stored.
- [ ] Green/red status records are visually distinct.
- [ ] User can freeze an agent.
- [ ] Hard policy checks work offline.
- [ ] Local audit exists.
- [ ] Android Keystore protects keys.

### Agent

- [ ] Agent can send a structured payment request.
- [ ] Agent identity is verified.
- [ ] Agent receives ALLOW/BLOCK/APPROVAL result.
- [ ] Agent cannot execute without authorization.
- [ ] Rejected request cannot silently retry.

### Razorpay

- [ ] Approved test transaction can reach Razorpay.
- [ ] Payment status can be received.
- [ ] Webhook updates local/cloud state.
- [ ] Transaction is linked to authorization ID.

### ML

- [ ] Synthetic dataset exists.
- [ ] Behaviour anomaly model is evaluated.
- [ ] Risk model is evaluated.
- [ ] Circumvention detector has dedicated tests.

### Web

- [ ] Agents visible.
- [ ] Policies configurable.
- [ ] Transactions visible.
- [ ] Audit replay works.
- [ ] Simulation works.

---

# 40. Repository Structure

```text
agentpay-guard/
│
├── apps/
│   ├── android/
│   │   ├── app/
│   │   ├── core/
│   │   │   ├── authority/
│   │   │   ├── policy/
│   │   │   ├── decision/
│   │   │   ├── intent/
│   │   │   ├── risk/
│   │   │   └── circumvention/
│   │   ├── data/
│   │   │   ├── local/
│   │   │   ├── remote/
│   │   │   └── repository/
│   │   ├── security/
│   │   │   └── keystore/
│   │   ├── notifications/
│   │   └── ui/
│   │       ├── home/
│   │       ├── approvals/
│   │       ├── activity/
│   │       ├── agents/
│   │       └── settings/
│   │
│   └── web/
│       ├── app/
│       │   ├── dashboard/
│       │   ├── agents/
│       │   ├── policies/
│       │   ├── transactions/
│       │   ├── simulation/
│       │   ├── audit/
│       │   └── settings/
│       ├── components/
│       └── lib/
│
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── services/
│   │   ├── sync/
│   │   ├── audit/
│   │   └── integrations/
│   │       └── razorpay/
│   └── requirements.txt
│
├── agent/
│   ├── protocol/
│   ├── tools/
│   └── simulator/
│       ├── normal.py
│       ├── over_limit.py
│       ├── intent_mismatch.py
│       ├── splitting.py
│       └── compromised.py
│
├── ml/
│   ├── data/
│   ├── features/
│   ├── training/
│   ├── models/
│   └── evaluation/
│
├── tests/
│   ├── android/
│   ├── backend/
│   ├── agent/
│   ├── security/
│   └── e2e/
│
├── docs/
│   ├── PRD.md
│   ├── architecture.md
│   ├── threat-model.md
│   └── demo-script.md
│
├── docker-compose.yml
├── .env.example
└── README.md
```

---

# 41. What Is Explicitly NOT Being Built

Do not turn the project into:

- another shopping marketplace
- another generic AI chatbot
- a dashboard that only predicts transaction risk
- an LLM that decides whether payments are safe
- a payment gateway
- a replacement for Razorpay
- a cloud-only authorization service
- an app that requires the laptop to remain connected
- an attempt to secretly intercept consumer ChatGPT/Claude/Gemini traffic

The product must remain:

> **A local-first user-consent and authorization boundary for agentic commerce.**

---

# 42. Differentiation

Razorpay already enables agentic payments and pre-authorized payment capacity. citeturn0search2turn0search7turn0search9

AgentPay Guard does not claim to replace that.

The differentiation is:

| Existing agentic flow | AgentPay Guard |
|---|---|
| Agent can transact within a spending boundary | User can inspect each consequential action |
| Payment infrastructure | Independent consent layer |
| Pre-authorized capacity | Transaction-level contextual approval |
| Payment execution | Authorization + audit |
| Agent-centric | User/device-centric |
| Cloud/payment infrastructure | Local-first trusted device |
| Payment outcome | Decision + reason + outcome |

---

# 43. Final Product Definition

AgentPay Guard is:

> **A local-first Android consent gateway that sits between autonomous AI shopping agents and payment execution. It gives users contextual notifications whenever an agent attempts a consequential purchase, allows them to accept or reject the action, records the decision and reason, and only releases a scoped authorization to the payment layer after approval.**

The architecture is:

```text
AI Agent
   ↓
AgentPay Guard on Android
   ├── Identity
   ├── Intent
   ├── Authority
   ├── Policy
   ├── Risk
   ├── Behaviour
   ├── Circumvention
   ├── Human Consent
   └── Audit
   ↓
Razorpay
   ↓
Payment / Order
```

---

# 44. Final Hackathon Pitch

> **AI agents are moving from answering questions to shopping and paying for us. Razorpay is already building the payment rails for this future. But when an AI can move money, a spending limit alone isn't enough.**
>
> **AgentPay Guard is a local-first Android consent layer between AI agents and payment execution. When ChatGPT, Claude or Gemini reaches a shopping or payment action, AgentPay Guard shows the user exactly what the agent wants to buy, from whom, for how much, what the original intent was, and why the transaction is being flagged. The user can accept or reject it instantly.**
>
> **If accepted, AgentPay Guard issues a scoped authorization and the transaction proceeds through Razorpay. If rejected, it is blocked, the reason is stored, and the agent cannot silently retry. Behind the simple experience is local policy enforcement, intent verification, behavioural anomaly detection and transaction-circumvention detection.**
>
> **The cloud dashboard is for management and analytics. The phone remains the trust anchor.**
>
> **We are not building another AI that can pay. We are building the consent boundary that lets AI pay without taking control of the user's money.**

---

# 45. North-Star Metric

The north-star metric is:

> **How much autonomous shopping can a user safely delegate while retaining meaningful control over financial actions?**

The product should maximize:

- autonomous completion
- user convenience
- payment success
- useful automation

while minimizing:

- unauthorized spending
- policy violations
- circumvention
- unexplained actions
- unnecessary approval prompts

---

# 46. One-Sentence Product Definition

> **AgentPay Guard lets ChatGPT, Claude and Gemini shop autonomously while keeping every consequential payment behind a local, contextual and user-controlled financial consent layer.**
