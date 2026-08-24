import type {
  Agent,
  AuditEvent,
  CircumventionResult,
  GuardDecision,
  Intent,
  IntentAssessment,
  PaymentRequest,
  Policy,
  ReasonCode,
  RiskAssessment,
  RiskLevel,
  TransactionRecord
} from "./types";

export interface EvaluateInput {
  request: PaymentRequest;
  agent: Agent;
  policy: Policy;
  history: TransactionRecord[];
  intents: Intent[];
  now?: Date;
}

const VELOCITY_WINDOW_MS = 10 * 60 * 1000;
const CIRCUMVENTION_WINDOW_MS = 5 * 60 * 1000;

function isSameDay(a: Date, b: Date): boolean {
  return (
    a.getFullYear() === b.getFullYear() &&
    a.getMonth() === b.getMonth() &&
    a.getDate() === b.getDate()
  );
}

export function knownMerchants(history: TransactionRecord[]): Set<string> {
  const set = new Set<string>();
  for (const rec of history) {
    const approved =
      rec.decision.decision === "ALLOW" || (rec.decision.decision === "USER_APPROVAL" && !!rec.userActionAt);
    if (approved) set.add(rec.request.merchant);
  }
  return set;
}

export function todayApprovedSpend(history: TransactionRecord[], agentId: string, now?: Date): number {
  const ref = now ?? new Date();
  let total = 0;
  for (const rec of history) {
    if (rec.request.agentId !== agentId) continue;
    if (rec.decision.decision === "BLOCK") continue;
    if (rec.outcome !== "CAPTURED") continue;
    if (isSameDay(new Date(rec.request.timestamp), ref)) total += rec.request.amount;
  }
  return total;
}

export function scoreIntent(request: PaymentRequest, intents: Intent[]): IntentAssessment {
  if (!request.intentId) {
    return { score: 50, severe: false, warn: false, label: "No linked intent" };
  }
  const intent = intents.find((i) => i.intentId === request.intentId);
  if (!intent) {
    return { score: 50, severe: false, warn: false, label: "Intent not found" };
  }
  if (request.category !== intent.category) {
    return { score: 15, severe: true, warn: true, label: `Category mismatch: intent ${intent.category}, got ${request.category}` };
  }
  if (request.amount > intent.budget * 1.5) {
    return { score: 15, severe: true, warn: true, label: `Amount far exceeds intent budget ₹${intent.budget}` };
  }
  if (request.amount > intent.budget * 1.1) {
    return { score: 55, severe: false, warn: true, label: `Amount exceeds intent budget ₹${intent.budget}` };
  }
  return { score: Math.min(100, 90 + Math.round((intent.budget - request.amount) / Math.max(intent.budget, 1) * 20)), severe: false, warn: false, label: "Matches user intent" };
}

export function computeRisk(request: PaymentRequest, policy: Policy, history: TransactionRecord[], known: Set<string>, now?: Date): RiskAssessment {
  const ref = now ?? new Date();
  const ts = new Date(request.timestamp).getTime();
  const signals: string[] = [];
  let score = 0;

  if (!known.has(request.merchant)) {
    score += 22;
    signals.push("Merchant not previously approved");
  }

  const amountFactor = Math.min(20, Math.round((request.amount / policy.transactionLimit) * 20));
  score += amountFactor;
  if (amountFactor >= 10) signals.push("Amount close to transaction limit");

  const hour = new Date(request.timestamp).getHours();
  if (hour < 8 || hour >= 21) {
    score += 12;
    signals.push("Unusual spending time");
  }

  const recent = history.filter((rec) => {
    if (rec.request.agentId !== request.agentId) return false;
    const t = new Date(rec.request.timestamp).getTime();
    return ts - t >= 0 && ts - t <= VELOCITY_WINDOW_MS;
  });
  if (recent.length + 1 >= 3) {
    score += 15;
    signals.push(`High velocity: ${recent.length + 1} requests in 10 minutes`);
  }

  const usedCategories = new Set(
    history.filter((r) => r.request.agentId === request.agentId).map((r) => r.request.category)
  );
  if (!usedCategories.has(request.category)) {
    score += 12;
    signals.push(`Unfamiliar category for this agent: ${request.category}`);
  }

  const blockedToday = history.some(
    (rec) =>
      rec.request.agentId === request.agentId &&
      rec.decision.decision === "BLOCK" &&
      isSameDay(new Date(rec.request.timestamp), ref)
  );
  if (blockedToday) {
    score += 14;
    signals.push("Agent had a blocked action today");
  }

  score = Math.max(0, Math.min(100, score));
  const level: RiskLevel = score < 25 ? "LOW" : score < 50 ? "MEDIUM" : score < 75 ? "HIGH" : "CRITICAL";
  if (signals.length === 0) signals.push("Activity within baseline");
  return { score, level, signals };
}

export function detectCircumvention(request: PaymentRequest, policy: Policy, history: TransactionRecord[]): CircumventionResult {
  const ts = new Date(request.timestamp).getTime();
  const prior: TransactionRecord[] = [];

  for (const rec of history) {
    if (rec.decision.decision === "BLOCK") continue;
    const req = rec.request;
    if (req.agentId !== request.agentId || req.sessionId !== request.sessionId) continue;
    const t = new Date(req.timestamp).getTime();
    if (t > ts || ts - t > CIRCUMVENTION_WINDOW_MS) continue;
    const ratio = req.amount > 0 ? Math.abs(req.amount - request.amount) / req.amount : 1;
    const similarAmount = ratio <= 0.15;
    const sameContext = req.merchant === request.merchant && req.category === request.category;
    if (similarAmount || sameContext) prior.push(rec);
  }

  const aggregateAmount = prior.reduce((sum, rec) => sum + rec.request.amount, 0) + request.amount;

  if (prior.length >= 2 && aggregateAmount >= 0.9 * policy.transactionLimit) {
    return {
      detected: true,
      score: Math.min(100, 55 + 15 * prior.length),
      aggregateAmount,
      windowCount: prior.length + 1
    };
  }
  return {
    detected: false,
    score: prior.length > 0 ? Math.min(60, prior.length * 20) : 0,
    aggregateAmount,
    windowCount: prior.length + 1
  };
}

function block(code: string, label: string): ReasonCode {
  return { code, label, severity: "block" };
}

export function evaluateRequest(input: EvaluateInput): GuardDecision {
  const { request, agent, policy, history, intents } = input;
  const now = input.now ?? new Date(request.timestamp);
  const known = knownMerchants(history);
  const risk = computeRisk(request, policy, history, known, now);
  const circ = detectCircumvention(request, policy, history);
  const intent = scoreIntent(request, intents);

  const reasons: ReasonCode[] = [];

  if (agent.status === "ACTIVE") reasons.push({ code: "AGENT_AUTHORIZED", label: "Agent authorized", severity: "ok" });
  if (policy.blockedCategories.includes(request.category)) {
    reasons.push(block("CATEGORY_BLOCKED", `Category ${request.category} is disabled`));
  } else {
    reasons.push({ code: "CATEGORY_ALLOWED", label: `Category ${request.category} allowed`, severity: "ok" });
  }
  if (policy.blockedMerchants.includes(request.merchant)) {
    reasons.push(block("MERCHANT_BLOCKED", `Merchant ${request.merchant} is prohibited`));
  } else if (known.has(request.merchant)) {
    reasons.push({ code: "MERCHANT_KNOWN", label: "Known merchant", severity: "ok" });
  } else {
    reasons.push({ code: "NEW_MERCHANT", label: "New merchant requires review", severity: "warn" });
  }
  if (request.amount <= policy.transactionLimit) {
    reasons.push({ code: "LIMIT_WITHIN", label: "Within transaction limit", severity: "ok" });
  } else {
    reasons.push(block("LIMIT_TRANSACTION_EXCEEDED", `₹${request.amount} exceeds ₹${policy.transactionLimit} transaction limit`));
  }
  if (intent.severe) reasons.push(block("INTENT_MISMATCH", intent.label));
  else if (intent.warn) reasons.push({ code: "BUDGET_WARN", label: intent.label, severity: "warn" });
  else reasons.push({ code: "BUDGET_VALID", label: "Budget within intent", severity: "ok" });
  if (circ.detected) {
    reasons.push(
      block(
        "CIRCUMVENTION_DETECTED",
        `Split pattern: ${circ.windowCount} payments, aggregate ₹${circ.aggregateAmount} vs ₹${policy.transactionLimit} limit`
      )
    );
  }

  const spend = todayApprovedSpend(history, request.agentId, now);
  const dailyExceeded = spend + request.amount > policy.dailyLimit;
  if (dailyExceeded) {
    reasons.push(block("LIMIT_DAILY_EXCEEDED", `Daily exposure ₹${spend + request.amount} would exceed ₹${policy.dailyLimit}`));
  }

  let decision: GuardDecision["decision"] = "ALLOW";

  const ordered: Array<() => boolean> = [
    () => {
      if (agent.status === "REVOKED") {
        reasons.unshift(block("AGENT_REVOKED", "Agent access has been revoked"));
        decision = "BLOCK";
        return true;
      }
      return false;
    },
    () => {
      if (agent.status === "FROZEN") {
        reasons.unshift(block("AGENT_FROZEN", "Agent is frozen on this device"));
        decision = "BLOCK";
        return true;
      }
      return false;
    },
    () => {
      if (reasons.some((r) => r.code === "CATEGORY_BLOCKED")) {
        decision = "BLOCK";
        return true;
      }
      return false;
    },
    () => {
      if (reasons.some((r) => r.code === "MERCHANT_BLOCKED")) {
        decision = "BLOCK";
        return true;
      }
      return false;
    },
    () => {
      if (reasons.some((r) => r.code === "LIMIT_TRANSACTION_EXCEEDED")) {
        decision = "BLOCK";
        return true;
      }
      return false;
    },
    () => {
      if (dailyExceeded) {
        decision = "BLOCK";
        return true;
      }
      return false;
    },
    () => {
      if (reasons.some((r) => r.code === "INTENT_MISMATCH")) {
        decision = "BLOCK";
        return true;
      }
      return false;
    },
    () => {
      if (circ.detected) {
        decision = "BLOCK";
        return true;
      }
      return false;
    },
    () => {
      if (!known.has(request.merchant) && policy.approvalRules.newMerchant) {
        decision = "USER_APPROVAL";
        return false;
      }
      return false;
    },
    () => {
      if (request.amount >= policy.approvalRules.amountAbove) {
        reasons.push({
          code: "AMOUNT_REQUIRES_APPROVAL",
          label: `Amount at or above ₹${policy.approvalRules.amountAbove} approval threshold`,
          severity: "warn"
        });
        decision = "USER_APPROVAL";
        return false;
      }
      return false;
    },
    () => {
      if ((risk.level === "HIGH" || risk.level === "CRITICAL") && policy.approvalRules.highRisk) {
        reasons.push({ code: "HIGH_RISK", label: `Risk ${risk.level}`, severity: "warn" });
        decision = "USER_APPROVAL";
        return false;
      }
      return false;
    }
  ];

  for (const step of ordered) {
    if (step()) break;
  }

  return {
    requestId: request.requestId,
    decision,
    reasonCodes: reasons,
    riskScore: risk.score,
    intentScore: intent.score,
    circumventionScore: circ.score,
    policyVersion: policy.version,
    authorizationId: null,
    timestamp: now.toISOString()
  };
}

export interface FullEvaluation {
  decision: GuardDecision;
  risk: RiskAssessment;
  circumvention: CircumventionResult;
  intent: IntentAssessment;
}

export function evaluateFull(input: EvaluateInput): FullEvaluation {
  const known = knownMerchants(input.history);
  const risk = computeRisk(input.request, input.policy, input.history, known, input.now);
  const circumvention = detectCircumvention(input.request, input.policy, input.history);
  const intent = scoreIntent(input.request, input.intents);
  const decision = evaluateRequest(input);
  return { decision, risk, circumvention, intent };
}

export function auditChainFor(record: TransactionRecord): Omit<AuditEvent, "eventId">[] {
  const base: Array<{ offsetSec: number; label: string; detail?: string }> = [];
  const t0 = new Date(record.request.timestamp).getTime();

  base.push({ offsetSec: 0, label: "Payment request received", detail: record.request.product });
  base.push({ offsetSec: 0, label: "Agent authenticated", detail: record.request.agentId });
  base.push({ offsetSec: 0, label: "Policy evaluated", detail: `v${record.decision.policyVersion}` });
  base.push({ offsetSec: 0, label: `Risk assessed`, detail: `${record.decision.riskScore}/100` });

  if (record.decision.decision === "BLOCK") {
    const reason = record.decision.reasonCodes.find((r) => r.severity === "block");
    base.push({ offsetSec: 0, label: reason?.label ?? "Blocked by policy", detail: reason?.code });
    base.push({ offsetSec: 1, label: "No approval requested", detail: "Hard policy violation" });
    base.push({ offsetSec: 2, label: "Agent informed", detail: "Structured denial returned" });
  } else if (!record.userActionAt) {
    base.push({ offsetSec: 1, label: "User notified" });
    base.push({ offsetSec: 2, label: "Awaiting user decision" });
  } else if (record.outcome === "DENIED") {
    base.push({ offsetSec: 1, label: "User notified" });
    base.push({ offsetSec: 13, label: "User rejected transaction" });
    base.push({ offsetSec: 13, label: "Authorization denied" });
    base.push({ offsetSec: 14, label: "Agent informed", detail: "Structured denial returned" });
  } else {
    base.push({ offsetSec: 1, label: "User notified" });
    base.push({ offsetSec: 13, label: "User approved" });
    base.push({ offsetSec: 13, label: "Authorization issued", detail: record.authorization?.authorizationId ?? "auth_issued" });
    base.push({ offsetSec: 19, label: "Payment initiated", detail: "Razorpay order created" });
    base.push({ offsetSec: 22, label: "Payment captured" });
  }

  return base.map((step, idx) => ({
    at: new Date(t0 + step.offsetSec * 1000).toISOString(),
    label: step.label,
    detail: step.detail,
    eventId: `evt_${idx}`
  }));
}
