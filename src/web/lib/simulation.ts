import type { Agent, Category, GuardDecision, Intent, PaymentRequest, Policy, TransactionRecord } from "./types";
import { evaluateFull } from "./engine";

function mulberry32(seed: number): () => number {
  let a = seed >>> 0;
  return () => {
    a |= 0;
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

const KNOWN_MERCHANTS = ["amazon", "flipkart", "bigbasket", "croma"];
const UNKNOWN_MERCHANTS = ["shopquick", "gadgethub", "megamart", "valuecart", "techdeals"];
const ALLOWED_CATEGORIES: Category[] = ["electronics", "groceries", "office_supplies"];
const PRODUCTS: Record<Category, string[]> = {
  electronics: ["Wireless earbuds", "USB-C cable", "Bluetooth speaker", "Power bank", "Smart watch"],
  groceries: ["Atta 5kg", "Rice 10kg", "Cooking oil 1L", "Dry fruits pack"],
  office_supplies: ["Notebook set", "Desk organizer", "Printer paper"],
  gift_cards: ["Amazon Pay Gift Card", "Retail voucher"],
  gambling: ["Casino chips"],
  cryptocurrency: ["Crypto pack"],
  fashion: ["Running shoes", "Cotton shirt"],
  travel: ["Flight booking"]
};

export interface SimulationReport {
  total: number;
  allowed: number;
  approvalRequired: number;
  blocked: number;
  byReason: Record<string, number>;
  preventedAmount: number;
  stages: { received: number; authority: number; policy: number; risk: number; decided: number };
}

interface SimAgentState {
  agents: Record<string, Agent>;
}

function baseAgents(): SimAgentState {
  const mk = (agentId: string, name: string): Agent => ({
    agentId,
    name,
    ownerId: "user_001",
    status: "ACTIVE",
    trustScore: 90,
    riskState: "NORMAL",
    policyId: "pol_default",
    createdAt: new Date(0).toISOString()
  });
  return {
    agents: {
      "claude-shopping-01": mk("claude-shopping-01", "Claude Shopping Agent"),
      "gemini-shopping-02": mk("gemini-shopping-02", "Gemini Shopping Agent"),
      "gpt-assistant-03": mk("gpt-assistant-03", "ChatGPT Assistant")
    }
  };
}

const REQUESTS_PER_DAY = 8;

function makeRequest(
  rng: () => number,
  idx: number,
  minuteOffset: number,
  opts: { merchant: string; category: Category; product: string; amount: number }
): PaymentRequest {
  const hour = 8 + Math.floor(rng() * 13);
  const d = new Date();
  d.setDate(d.getDate() - Math.floor(idx / REQUESTS_PER_DAY));
  d.setHours(hour, (idx * 7 + minuteOffset) % 60, Math.floor(rng() * 60), 0);
  return {
    requestId: `sim_${idx.toString().padStart(5, "0")}`,
    agentId: "claude-shopping-01",
    intentId: null,
    merchant: opts.merchant,
    product: opts.product,
    amount: opts.amount,
    currency: "INR",
    category: opts.category,
    sessionId: `sim_sess_${Math.floor(idx / 3)}`,
    timestamp: d.toISOString()
  };
}

export function runSimulation(count: number, seed: number, policy: Policy): SimulationReport {
  const rng = mulberry32(seed);
  const { agents } = baseAgents();
  const history: TransactionRecord[] = [];
  const intents: Intent[] = [];

  let allowed = 0;
  let approvalRequired = 0;
  let blocked = 0;
  let preventedAmount = 0;
  const byReason: Record<string, number> = {};
  const stages = { received: count, authority: 0, policy: 0, risk: 0, decided: count };

  let simIdx = 0;
  for (let i = 0; i < count; i += 1) {
    const roll = rng();
    const batch: Array<{ merchant: string; category: Category; product: string; amount: number }> = [];

    if (roll < 0.62) {
      const category = ALLOWED_CATEGORIES[Math.floor(rng() * ALLOWED_CATEGORIES.length)];
      const products = PRODUCTS[category];
      batch.push({
        merchant: KNOWN_MERCHANTS[Math.floor(rng() * KNOWN_MERCHANTS.length)],
        category,
        product: products[Math.floor(rng() * products.length)],
        amount: 150 + Math.floor(rng() * 8500)
      });
    } else if (roll < 0.74) {
      batch.push({
        merchant: KNOWN_MERCHANTS[Math.floor(rng() * KNOWN_MERCHANTS.length)],
        category: "electronics",
        product: "MacBook Pro 14",
        amount: 22000 + Math.floor(rng() * 38000)
      });
    } else if (roll < 0.82) {
      batch.push({
        merchant: KNOWN_MERCHANTS[Math.floor(rng() * KNOWN_MERCHANTS.length)],
        category: "gift_cards",
        product: PRODUCTS.gift_cards[0],
        amount: 2000 + Math.floor(rng() * 8000)
      });
    } else if (roll < 0.92) {
      batch.push({
        merchant: UNKNOWN_MERCHANTS[Math.floor(rng() * UNKNOWN_MERCHANTS.length)],
        category: ALLOWED_CATEGORIES[Math.floor(rng() * ALLOWED_CATEGORIES.length)],
        product: "Assorted order",
        amount: 800 + Math.floor(rng() * 7000)
      });
    } else if (roll < 0.97) {
      const merchant = UNKNOWN_MERCHANTS[Math.floor(rng() * UNKNOWN_MERCHANTS.length)];
      for (let k = 0; k < 3; k += 1) {
        batch.push({ merchant, category: "electronics", product: "Electronics bundle item", amount: 9400 + Math.floor(rng() * 500) });
      }
    } else {
      const merchant = UNKNOWN_MERCHANTS[Math.floor(rng() * UNKNOWN_MERCHANTS.length)];
      for (let k = 0; k < 6; k += 1) {
        batch.push({ merchant, category: "electronics", product: "Flash sale item", amount: 3000 + Math.floor(rng() * 6500) });
      }
    }

    for (const opts of batch) {
      simIdx += 1;
      if (simIdx > count) break;
      const request = makeRequest(rng, simIdx, i % 9, opts);
      const agent = agents[request.agentId];
      const evaluation = evaluateFull({ request, agent, policy, history, intents });
      const decision: GuardDecision = evaluation.decision;
      const record: TransactionRecord = {
        request,
        decision,
        outcome:
          decision.decision === "BLOCK"
            ? "NOT_ATTEMPTED"
            : decision.decision === "ALLOW"
              ? "CAPTURED"
              : "NOT_ATTEMPTED",
        decidedBy: decision.decision === "BLOCK" ? "policy" : "user",
        userActionAt: decision.decision === "ALLOW" ? request.timestamp : undefined
      };
      if (record.outcome === "CAPTURED") record.userActionAt = request.timestamp;
      history.push(record);

      const blockReason = decision.reasonCodes.find((r) => r.severity === "block");
      const warnReason = decision.reasonCodes.find((r) => r.code === "NEW_MERCHANT" || r.code === "AMOUNT_REQUIRES_APPROVAL" || r.code === "HIGH_RISK");

      if (decision.decision === "BLOCK") {
        blocked += 1;
        preventedAmount += request.amount;
        const code = blockReason?.code ?? "BLOCKED";
        byReason[code] = (byReason[code] ?? 0) + 1;
        if (code.startsWith("AGENT_")) stages.authority += 1;
        else if (code.startsWith("LIMIT_") || code.startsWith("CATEGORY") || code.startsWith("MERCHANT")) stages.policy += 1;
        else stages.risk += 1;
      } else if (decision.decision === "USER_APPROVAL") {
        approvalRequired += 1;
        const code = warnReason?.code ?? "APPROVAL";
        byReason[code] = (byReason[code] ?? 0) + 1;
        if (Math.random() < 0.8) {
          record.userActionAt = request.timestamp;
          record.outcome = "CAPTURED";
          record.authorization = {
            authorizationId: `auth_sim_${simIdx}`,
            requestId: request.requestId,
            agentId: request.agentId,
            merchant: request.merchant,
            product: request.product,
            amount: request.amount,
            currency: "INR",
            intentId: null,
            expiresAt: request.timestamp,
            status: "USED"
          };
        }
      } else {
        allowed += 1;
        byReason["AUTO_APPROVED"] = (byReason["AUTO_APPROVED"] ?? 0) + 1;
      }
    }
  }

  return { total: count, allowed, approvalRequired, blocked, byReason, preventedAmount, stages };
}
