import type {
  Agent,
  AnomalyEvent,
  AuditEvent,
  GuardDecision,
  Intent,
  Policy,
  ReasonCode,
  SpendPoint,
  TransactionRecord
} from "./types";

function todayAt(hour: number, minute: number, second = 0): string {
  const d = new Date();
  d.setHours(hour, minute, second, 0);
  return d.toISOString();
}

function plusSec(iso: string, s: number): string {
  return new Date(new Date(iso).getTime() + s * 1000).toISOString();
}

export interface SeedState {
  agents: Agent[];
  policies: Policy[];
  intents: Intent[];
  transactions: TransactionRecord[];
  audit: Record<string, AuditEvent[]>;
  anomalies: AnomalyEvent[];
  spendSeries: SpendPoint[];
}

export const DEFAULT_POLICY: Policy = {
  policyId: "pol_default",
  version: 3,
  transactionLimit: 20000,
  dailyLimit: 75000,
  monthlyLimit: 200000,
  allowedCategories: ["electronics", "groceries", "office_supplies"],
  blockedCategories: ["gift_cards", "gambling", "cryptocurrency"],
  blockedMerchants: [],
  approvalRules: { newMerchant: true, international: true, amountAbove: 10000, highRisk: true }
};

const ok = (code: string, label: string): ReasonCode => ({ code, label, severity: "ok" });
const warn = (code: string, label: string): ReasonCode => ({ code, label, severity: "warn" });
const blk = (code: string, label: string): ReasonCode => ({ code, label, severity: "block" });

interface Spec {
  requestId: string;
  agentId: string;
  intentId?: string;
  merchant: string;
  product: string;
  amount: number;
  category: TransactionRecord["request"]["category"];
  sessionId: string;
  h: number;
  m: number;
  decision: GuardDecision["decision"];
  reasons: ReasonCode[];
  riskScore: number;
  intentScore?: number;
  circumventionScore?: number;
  authId?: string;
  outcome?: TransactionRecord["outcome"];
  userActionAt?: string;
}

function buildTransaction(spec: Spec, ts: string): TransactionRecord {
  const request = {
    requestId: spec.requestId,
    agentId: spec.agentId,
    intentId: spec.intentId ?? null,
    merchant: spec.merchant,
    product: spec.product,
    amount: spec.amount,
    currency: "INR" as const,
    category: spec.category,
    sessionId: spec.sessionId,
    timestamp: ts
  };
  const decision: GuardDecision = {
    requestId: spec.requestId,
    decision: spec.decision,
    reasonCodes: spec.reasons,
    riskScore: spec.riskScore,
    intentScore: spec.intentScore ?? 50,
    circumventionScore: spec.circumventionScore ?? 0,
    policyVersion: 3,
    authorizationId: spec.authId ?? null,
    timestamp: ts
  };
  const record: TransactionRecord = {
    request,
    decision,
    outcome: spec.outcome ?? "NOT_ATTEMPTED",
    decidedBy: spec.decision === "BLOCK" ? "policy" : "user"
  };
  if (spec.userActionAt) record.userActionAt = spec.userActionAt;
  if (spec.authId && spec.outcome === "CAPTURED") {
    record.authorization = {
      authorizationId: spec.authId,
      requestId: spec.requestId,
      agentId: spec.agentId,
      merchant: spec.merchant,
      product: spec.product,
      amount: spec.amount,
      currency: "INR",
      intentId: request.intentId,
      expiresAt: plusSec(ts, 300),
      status: "USED"
    };
  }
  return record;
}

const SPECS: Spec[] = [
  {
    requestId: "req_a1c3f9", agentId: "claude-shopping-01", intentId: "intent_183", merchant: "amazon",
    product: "Sony WH-1000XM5", amount: 14499, category: "electronics", sessionId: "sess_claude_01",
    h: 20, m: 42, decision: "USER_APPROVAL", riskScore: 18, intentScore: 95, authId: "auth_981", outcome: "CAPTURED", userActionAt: "u13",
    reasons: [ok("AGENT_AUTHORIZED", "Agent authorized"), ok("CATEGORY_ALLOWED", "Category electronics allowed"), ok("MERCHANT_KNOWN", "Known merchant"), ok("BUDGET_VALID", "Within intent budget"), warn("AMOUNT_REQUIRES_APPROVAL", "Amount at or above ₹10,000 approval threshold")]
  },
  {
    requestId: "req_b4d9e2", agentId: "gemini-shopping-02", merchant: "techmart",
    product: "MacBook Pro 14", amount: 42000, category: "electronics", sessionId: "sess_gemini_07",
    h: 20, m: 37, decision: "BLOCK", riskScore: 46,
    reasons: [blk("LIMIT_TRANSACTION_EXCEEDED", "₹42,000 exceeds ₹20,000 transaction limit"), ok("CATEGORY_ALLOWED", "Category electronics allowed"), warn("NEW_MERCHANT", "New merchant requires review")]
  },
  {
    requestId: "req_c7e2a8", agentId: "gpt-assistant-03", merchant: "flipkart",
    product: "Amazon Pay Gift Card ₹5,000", amount: 5000, category: "gift_cards", sessionId: "sess_gpt_11",
    h: 19, m: 54, decision: "BLOCK", riskScore: 30,
    reasons: [blk("CATEGORY_BLOCKED", "Category gift_cards is disabled"), warn("NEW_MERCHANT", "New merchant requires review")]
  },
  {
    requestId: "req_d9f4b1", agentId: "claude-shopping-01", merchant: "amazon",
    product: "Ergonomic Office Chair", amount: 8900, category: "office_supplies", sessionId: "sess_claude_01",
    h: 19, m: 21, decision: "USER_APPROVAL", riskScore: 22, authId: "auth_774", outcome: "CAPTURED", userActionAt: "u15",
    reasons: [ok("AGENT_AUTHORIZED", "Agent authorized"), ok("CATEGORY_ALLOWED", "Category office_supplies allowed"), ok("MERCHANT_KNOWN", "Known merchant"), ok("BUDGET_VALID", "No linked intent")]
  },
  {
    requestId: "req_e1a11", agentId: "claude-shopping-01", merchant: "croma",
    product: "Logitech MX Master 3S", amount: 9800, category: "electronics", sessionId: "sess_split_91",
    h: 20, m: 5, decision: "USER_APPROVAL", riskScore: 41, circumventionScore: 20, authId: "auth_901", outcome: "CAPTURED", userActionAt: "u12",
    reasons: [ok("AGENT_AUTHORIZED", "Agent authorized"), ok("CATEGORY_ALLOWED", "Category electronics allowed"), warn("NEW_MERCHANT", "New merchant requires review"), ok("LIMIT_WITHIN", "Within transaction limit")]
  },
  {
    requestId: "req_e2b22", agentId: "claude-shopping-01", merchant: "croma",
    product: "Keychron K3 Keyboard", amount: 9700, category: "electronics", sessionId: "sess_split_91",
    h: 20, m: 6, decision: "USER_APPROVAL", riskScore: 44, circumventionScore: 40, authId: "auth_902", outcome: "CAPTURED", userActionAt: "u11",
    reasons: [ok("AGENT_AUTHORIZED", "Agent authorized"), ok("CATEGORY_ALLOWED", "Category electronics allowed"), ok("MERCHANT_KNOWN", "Known merchant"), ok("LIMIT_WITHIN", "Within transaction limit"), warn("BUDGET_WARN", "Repeated purchases in short window")]
  },
  {
    requestId: "req_e3c33", agentId: "claude-shopping-01", merchant: "croma",
    product: "Anker USB-C Hub", amount: 9900, category: "electronics", sessionId: "sess_split_91",
    h: 20, m: 7, decision: "BLOCK", riskScore: 52, circumventionScore: 96,
    reasons: [ok("AGENT_AUTHORIZED", "Agent authorized"), ok("CATEGORY_ALLOWED", "Category electronics allowed"), ok("LIMIT_WITHIN", "Within transaction limit"), blk("CIRCUMVENTION_DETECTED", "Split pattern: 3 payments, aggregate ₹29,400 vs ₹20,000 limit")]
  },
  {
    requestId: "req_f5g67", agentId: "gemini-shopping-02", merchant: "bigbasket",
    product: "Monthly groceries basket", amount: 6400, category: "groceries", sessionId: "sess_gemini_09",
    h: 20, m: 58, decision: "USER_APPROVAL", riskScore: 34,
    reasons: [ok("AGENT_AUTHORIZED", "Agent authorized"), ok("CATEGORY_ALLOWED", "Category groceries allowed"), warn("NEW_MERCHANT", "New merchant requires review"), ok("LIMIT_WITHIN", "Within transaction limit")]
  }
];

let evtCounter = 0;

function ev(requestId: string, at: string, label: string, detail?: string): AuditEvent {
  evtCounter += 1;
  return { eventId: `evt_${evtCounter.toString(16).padStart(4, "0")}`, requestId, at, label, detail };
}

function buildAudit(recs: TransactionRecord[]): Record<string, AuditEvent[]> {
  const out: Record<string, AuditEvent[]> = {};
  for (const rec of recs) {
    const id = rec.request.requestId;
    const ts = rec.request.timestamp;
    const level =
      rec.decision.riskScore < 25 ? "LOW" : rec.decision.riskScore < 50 ? "MEDIUM" : rec.decision.riskScore < 75 ? "HIGH" : "CRITICAL";
    const events: AuditEvent[] = [
      ev(id, plusSec(ts, -11), "Intent created"),
      ev(id, ts, "Payment request received", rec.request.product),
      ev(id, ts, "Agent authenticated", rec.request.agentId),
      ev(id, ts, "Policy evaluated", `v${rec.decision.policyVersion}`),
      ev(id, ts, `Risk assessed`, `${level} · ${rec.decision.riskScore}/100`),
      ev(id, plusSec(ts, 1), "User notified")
    ];
    if (rec.decision.decision === "BLOCK") {
      const reason = rec.decision.reasonCodes.find((r) => r.severity === "block");
      events.push(ev(id, plusSec(ts, 1), reason?.label ?? "Blocked by policy", reason?.code));
      events.push(ev(id, plusSec(ts, 2), "No approval requested", "Hard policy violation"));
      events.push(ev(id, plusSec(ts, 3), "Agent informed", "Structured denial returned"));
    } else if (!rec.userActionAt) {
      events.push(ev(id, plusSec(ts, 2), "Awaiting user decision"));
    } else if (rec.outcome === "DENIED") {
      events.push(ev(id, plusSec(ts, 13), "User rejected transaction"));
      events.push(ev(id, plusSec(ts, 13), "Authorization denied"));
      events.push(ev(id, plusSec(ts, 14), "Agent informed", "Structured denial returned"));
    } else {
      events.push(ev(id, plusSec(ts, 13), "User accepted"));
      events.push(ev(id, plusSec(ts, 13), "Authorization issued", rec.authorization?.authorizationId));
      events.push(ev(id, plusSec(ts, 19), "Payment initiated", "Razorpay order created"));
      events.push(ev(id, plusSec(ts, 22), "Payment captured", rec.authorization?.authorizationId));
    }
    out[id] = events;
  }
  return out;
}

export function buildSeed(): SeedState {
  const agents: Agent[] = [
    { agentId: "claude-shopping-01", name: "Claude Shopping Agent", ownerId: "user_001", status: "ACTIVE", trustScore: 94, riskState: "ELEVATED", policyId: "pol_default", createdAt: todayAt(9, 12) },
    { agentId: "gemini-shopping-02", name: "Gemini Shopping Agent", ownerId: "user_001", status: "ACTIVE", trustScore: 81, riskState: "NORMAL", policyId: "pol_default", createdAt: todayAt(9, 15) },
    { agentId: "gpt-assistant-03", name: "ChatGPT Assistant", ownerId: "user_001", status: "ACTIVE", trustScore: 88, riskState: "NORMAL", policyId: "pol_default", createdAt: todayAt(9, 18) }
  ];

  const intents: Intent[] = [
    {
      intentId: "intent_183",
      agentId: "claude-shopping-01",
      goal: "Find me noise-cancelling headphones under ₹15,000.",
      category: "electronics",
      budget: 15000,
      currency: "INR",
      createdAt: todayAt(20, 42, 1),
      expiresAt: todayAt(23, 59)
    }
  ];

  const transactions = SPECS.map((spec) => {
    const userOffset = typeof spec.userActionAt === "string" && spec.userActionAt.startsWith("u") ? Number(spec.userActionAt.slice(1)) : undefined;
    const fixed: Spec = { ...spec };
    if (userOffset !== undefined) {
      fixed.userActionAt = plusSec(todayAt(spec.h, spec.m), userOffset);
    }
    return buildTransaction(fixed, todayAt(spec.h, spec.m));
  });

  const audit = buildAudit(transactions);

  const anomalies: AnomalyEvent[] = [
    {
      anomalyId: "anom_001",
      agentId: "claude-shopping-01",
      type: "CRITICAL_ANOMALY",
      observedTxns: 21,
      observedMinutes: 8,
      observedAmount: 92400,
      baselineTxnsPerDayMin: 5,
      baselineTxnsPerDayMax: 8,
      signals: ["High transaction velocity", "New merchants", "Unusual spending time", "Category deviation"],
      recommendation: "FREEZE_AGENT",
      createdAt: todayAt(21, 4),
      dismissed: false
    }
  ];

  const spendSeries: SpendPoint[] = [
    { day: "Mon", spend: 12450 },
    { day: "Tue", spend: 8320 },
    { day: "Wed", spend: 15980 },
    { day: "Thu", spend: 6100 },
    { day: "Fri", spend: 21460 },
    { day: "Sat", spend: 11240 },
    { day: "Sun", spend: 42899 }
  ];

  return { agents, policies: [DEFAULT_POLICY], intents, transactions, audit, anomalies, spendSeries };
}
