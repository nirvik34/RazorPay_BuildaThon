# AgentPay Guard — Shared Build Spec

Single source of truth for all components (web, backend, android, agent, ml).
Product: local-first consent/authorization layer between AI shopping agents (ChatGPT/Claude/Gemini) and Razorpay payments.
Flow: AI agent sends PaymentRequest → Guard evaluates (identity → intent → policy/limits → risk → circumvention) → ALLOW | USER_APPROVAL | BLOCK → user accepts/rejects → scoped Authorization (5-min expiry) → Razorpay executes → audit.

---

## 1. Shared Data Contract

IDs: `req_xxxxxx`, `auth_xxxxxx`, `intent_xxx`, `evt_xxx`.

```
AgentStatus:   ACTIVE | FROZEN | REVOKED
RiskLevel:     LOW (<25) | MEDIUM (<50) | HIGH (<75) | CRITICAL (>=75)
DecisionType:  ALLOW | USER_APPROVAL | BLOCK
Category:      electronics | groceries | office_supplies | gift_cards | gambling | cryptocurrency | fashion | travel
PaymentOutcome CAPTURED | PROCESSING | FAILED | DENIED | NOT_ATTEMPTED
```

```ts
ApprovalRules { newMerchant: bool; international: bool; amountAbove: number; highRisk: bool }

Policy {
  policyId: string; version: number;
  transactionLimit: number; dailyLimit: number; monthlyLimit: number;
  allowedCategories: Category[]; blockedCategories: Category[];
  blockedMerchants: string[];              // lowercase slugs; [] = none blocked
  approvalRules: ApprovalRules;
}

Agent {
  agentId: string; name: string; ownerId: string;
  status: AgentStatus; trustScore: number;      // 0-100
  riskState: NORMAL | ELEVATED | CRITICAL;
  policyId: string; createdAt: ISO;
}

Intent {
  intentId: string; agentId: string; goal: string;
  category: Category; budget: number; currency: "INR";
  createdAt: ISO; expiresAt: ISO;
}

PaymentRequest {
  requestId: string; agentId: string; intentId: string|null;
  merchant: string;            // lowercase slug e.g. "amazon"
  product: string; amount: number; currency: "INR"; category: Category;
  sessionId: string; timestamp: ISO;
}

ReasonCode { code: string; label: string; severity: ok|warn|block }
GuardDecision {
  requestId: string; decision: DecisionType; reasonCodes: ReasonCode[];
  riskScore: number; intentScore: number; circumventionScore: number;
  policyVersion: number; authorizationId: string|null; timestamp: ISO;
}

Authorization {
  authorizationId: string; requestId: string; agentId: string;
  merchant: string; product: string; amount: number; currency: "INR";
  intentId: string|null; expiresAt: ISO;         // issuedAt + 300s
  status: AUTHORIZED | USED | EXPIRED;
}

TransactionRecord { request; decision; outcome: PaymentOutcome; decidedBy: user|policy; userActionAt?: ISO; authorization?: Authorization }
AuditEvent  { eventId; requestId; at: ISO; label: string; detail?: string }
AnomalyEvent {
  anomalyId; agentId; type: CRITICAL_ANOMALY;
  observedTxns; observedMinutes; observedAmount;
  baselineTxnsPerDayMin; baselineTxnsPerDayMax;
  signals: string[]; recommendation: FREEZE_AGENT;
  createdAt: ISO; dismissed: bool;
}
```

---

## 2. Decision Engine (identical logic in TS/Python/Kotlin)

`evaluateRequest(request, agent, policy, history, intents, now)` — deterministic, exact order:

1. `agent.status == REVOKED` → BLOCK `AGENT_REVOKED`
2. `agent.status == FROZEN` → BLOCK `AGENT_FROZEN`
3. `category in policy.blockedCategories` → BLOCK `CATEGORY_BLOCKED`
4. `merchant in policy.blockedMerchants` → BLOCK `MERCHANT_BLOCKED`
5. `amount > policy.transactionLimit` → BLOCK `LIMIT_TRANSACTION_EXCEEDED`
6. `todayApprovedSpend(history, agentId) + amount > policy.dailyLimit` → BLOCK `LIMIT_DAILY_EXCEEDED`
7. severe intent mismatch (below) → BLOCK `INTENT_MISMATCH`
8. circumvention detected (`score >= 80`) → BLOCK `CIRCUMVENTION_DETECTED`
9. merchant unknown AND `approvalRules.newMerchant` → USER_APPROVAL warn `NEW_MERCHANT`
10. `amount >= approvalRules.amountAbove` → USER_APPROVAL `AMOUNT_REQUIRES_APPROVAL`
11. risk level HIGH|CRITICAL AND `approvalRules.highRisk` → USER_APPROVAL `HIGH_RISK`
12. else → ALLOW

Always also emit ok/warn context reasons: `AGENT_AUTHORIZED(ok)`, `CATEGORY_ALLOWED(ok)`, `BUDGET_VALID(warn if over intent budget but not severe)`, etc.

**Known merchants** = distinct merchants with any non-BLOCK decision in history.

**Intent scoring**: find Intent by request.intentId. None → intentScore 50 neutral.
- category mismatch → SEVERE, intentScore 15
- amount > budget*1.5 → SEVERE
- amount > budget*1.1 → WARN, intentScore 55
- else MATCH, intentScore 95

**Risk heuristic** (0–100): base 0
+22 unknown merchant
+ min(20, round(amount / transactionLimit * 20))
+12 if hour <8 or >=21
+15 velocity: >=3 requests same agent within last 10 min (any state)
+12 category never previously used by this agent in history
+14 agent has any BLOCK today
Clamp [0,100]. signals[] = human-readable strings for every added factor.

**Circumvention detector**: prior = history where same agentId AND same sessionId AND decision != BLOCK AND timestamp within last 5 minutes of current request AND (amount within ±15% of any prior amount OR same merchant && category).
If prior.count >= 2 AND aggregate(incl current) >= 0.9 * transactionLimit → detected=true, score=min(100, 55+15*prior.count). Else score = prior.count>0 ? min(60, prior.count*20) : 0. aggregateAmount = sum incl current.

**Authorization on accept**: id auth_<hex>, expiresAt now+300s, status AUTHORIZED. Reject → DENIED, no authorization object.

---

## 3. Design System (Web)

Colors:
bg #F7F9FC · foreground #101828 · brand #2563EB · brandDark #1D4ED8 · muted #667085 · border #E4E7EC · card #FFFFFF · navy #0B1220 · navyLight #111C2E ·
success #12B76A bg #ECFDF3 border #A6F4C5 text #067647 · danger #F04438 bg #FEF3F2 border #FECDCA text #B42318 · warning #F79009 bg #FFFAEB border #FEDF89 text #B54708 · info #2E90FA bg #EFF8FF border #B2DDFF text #175CD3 · purple #7F56D9 bg #F4F3FF.

Typography: Inter sans; JetBrains Mono for IDs, amounts metadata, timestamps. Headings -0.02em tracking, weight 650. Body 14px.

Layout: 8px spacing scale. Sidebar 240px navy (#0B1220), white text, active item bg rgba(59,130,246,0.14) + left indicator #3B82F6, lucide line icons, logo block shield + "AGENTPAY / GUARD". Page padding desktop 32px.

Semantic rules (hard):
- green ONLY approved/success
- red ONLY rejected/blocked/frozen/critical security outcomes (never warnings)
- amber = action required / pending
- blue = informational/sync
- purple = AI-generated context (user intent quotes)
- Amounts are the visual focal point of approval cards; large mono numerals
- Status pills: APPROVED #ECFDF3/#067647 · PENDING #FFFAEB/#B54708 · BLOCKED #FEF3F2/#B42318 · ACTIVE #EFF8FF/#175CD3 · FROZEN #FEF3F2/#B42318
- Cards: white, 1px #E4E7EC, radius 10px, shadow low `0 1px 2px rgba(16,24,40,0.04)`; medium `0 4px 12px rgba(16,24,40,0.08)`; high `0 12px 32px rgba(16,24,40,0.12)`
- Security states use 4px LEFT border on cards (green/red/amber), background stays white
- No gradients, no glassmorphism, no neon cyberpunk, no giant robot illustrations
- Voice: short factual copy. "Policy checks passed. User approval required." / "Authorization denied. No payment was attempted." Never "Oops!" or exclamation marks.

Signature component **Guard Decision Card**:
amber 4px left border when ACTION REQUIRED; header pill "ACTION REQUIRED" (amber); agent name; product; merchant; LARGE mono amount; divider; purple-tinted "USER INTENT" quote block; GUARD CHECKS list (✓ ok / ⚠ warn); RISK row + linear RiskScale (LOW MEDIUM HIGH CRITICAL ●———● style, value below); footer buttons REJECT (danger solid) + ACCEPT (success solid), equal visual weight, never a tiny text link.

Linear RiskScale component: horizontal LOW→CRITICAL segments with marker at score.

---

## 4. Canonical Seed Story (use identical names/values across stacks)

Policy `pol_default` v3: transactionLimit 20000, dailyLimit 75000, monthlyLimit 200000,
allowed [electronics, groceries, office_supplies], blocked [gift_cards, gambling, cryptocurrency],
blockedMerchants [], approvalRules { newMerchant true, international true, amountAbove 10000, highRisk true }.

Agents:
- claude-shopping-01 "Claude Shopping Agent" ACTIVE trust 94 NORMAL
- gemini-shopping-02 "Gemini Shopping Agent" ACTIVE trust 81 NORMAL
- gpt-assistant-03 "ChatGPT Assistant" ACTIVE trust 88 NORMAL

Intent intent_183 (claude): goal "Find me noise-cancelling headphones under ₹15,000." category electronics budget 15000.

Transactions today (times IST):
| requestId    | time  | agent  | merchant  | product                     | amount | category        | result |
|--------------|-------|--------|-----------|-----------------------------|--------|-----------------|--------|
| req_a1c3f9   | 20:42 | claude | amazon    | Sony WH-1000XM5             | 14499  | electronics     | accepted by user → auth_981 USED → payment CAPTURED. riskScore 18 LOW, intentScore 95. Audit timeline: Intent created 20:42:01 → Payment request received 20:42:12 → Agent authenticated 20:42:12 → Policy evaluated 20:42:12 → Risk: LOW 20:42:12 → User notified 20:42:13 → User approved 20:42:25 → Authorization issued 20:42:25 → Payment initiated (Razorpay) 20:42:31 → Payment captured 20:42:34 |
| req_b4d9e2   | 20:37 | gemini | techmart  | MacBook Pro 14              | 42000  | electronics     | BLOCK LIMIT_TRANSACTION_EXCEEDED (policy, no approval requested). risk 46 MEDIUM. Audit: request received → authority checked → limit exceeded ₹42,000 > ₹20,000 → blocked → no approval requested → agent informed |
| req_c7e2a8   | 19:54 | gpt    | flipkart  | Amazon Pay Gift Card ₹5,000 | 5000   | gift_cards      | BLOCK CATEGORY_BLOCKED (policy). risk 30 LOW |
| req_d9f4b1   | 19:21 | claude | amazon    | Ergonomic Office Chair      | 8900   | office_supplies | accepted → auth_774 USED → CAPTURED. risk 22 |
| req_e1a11    | 20:05 | claude | croma     | Logitech MX Master 3S       | 9800   | electronics     | session sess_split_91: accepted → auth_901 → CAPTURED |
| req_e2b22    | 20:06 | claude | croma     | Keychron K3 Keyboard        | 9700   | electronics     | sess_split_91: accepted → auth_902 → CAPTURED |
| req_e3c33    | 20:07 | claude | croma     | Anker USB-C Hub             | 9900   | electronics     | sess_split_91: BLOCK CIRCUMVENTION_DETECTED score 96 aggregate ₹29,400 windowCount 3. Audit: "Circumvention pattern detected", "Aggregate exposure ₹29,400 vs ₹20,000 transaction limit", blocked, agent informed |
| req_f5g67    | 20:58 | gemini | bigbasket | Monthly groceries basket    | 6400   | groceries       | PENDING USER_APPROVAL warn NEW_MERCHANT. risk 34 MEDIUM. Audit up to "User notified". NOT decided yet |

Pending derivation: records where decision==USER_APPROVAL AND userActionAt missing.

Anomaly anom_001: claude CRITICAL_ANOMALY observed 21 txns / 8 min / ₹92,400 vs baseline 5–8/day; signals ["High transaction velocity","New merchants","Unusual spending time","Category deviation"]; recommendation FREEZE_AGENT; created 21:04; dismissed false; claude.riskState ELEVATED.

Dashboard stats: Today's spend ₹42,899 (sum CAPTURED: 14499+8900+9800+9700) · Pending approvals 1 · Active agents 3 · Blocked actions 4.

Demo scenarios (PRD judge demo §37): normal purchase (Sony 14499 ACCEPT), over_limit (MacBook 42000 vs 10000 BLOCK), splitting (9800+9700+9900 same session croma → third BLOCK), intent_mismatch (intent monitor budget 20000 → buy gift card 10000 → BLOCK INTENT_MISMATCH), new_merchant (first purchase unknown shop → USER_APPROVAL NEW_MERCHANT), compromised burst (8 rapid requests, velocity → HIGH_RISK approvals/blocks + anomaly).

---

## 5. Stack Map

- web: Next.js 14 App Router, TS strict, Tailwind 3, lucide-react, recharts. Local-first store in localStorage; optional live API via NEXT_PUBLIC_API_URL (default http://localhost:8000).
- backend: FastAPI + pydantic v2 + httpx; JSON file persistence; WS /ws/events; Razorpay Orders API when RAZORPAY_KEY_ID/SECRET set, else simulated orders.
- android: Kotlin, Jetpack Compose, Room, Android Keystore, WorkManager, Retrofit; local decision engine port; notification approve/reject actions; offline-first.
- agent: stdlib-only Python simulator hitting backend POST /agent/payment-request; modes normal/over_limit/intent_mismatch/splitting/new_merchant/compromised.
- ml: numpy/pandas/scikit-learn; synthetic 10k dataset; GradientBoosting risk model + IsolationForest anomaly; evaluation metrics.
