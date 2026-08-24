export type AgentStatus = "ACTIVE" | "FROZEN" | "REVOKED";
export type RiskLevel = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
export type DecisionType = "ALLOW" | "USER_APPROVAL" | "BLOCK";
export type RiskState = "NORMAL" | "ELEVATED" | "CRITICAL";
export type Category =
  | "electronics"
  | "groceries"
  | "office_supplies"
  | "gift_cards"
  | "gambling"
  | "cryptocurrency"
  | "fashion"
  | "travel";
export type PaymentOutcome = "CAPTURED" | "PROCESSING" | "FAILED" | "DENIED" | "NOT_ATTEMPTED";

export interface ApprovalRules {
  newMerchant: boolean;
  international: boolean;
  amountAbove: number;
  highRisk: boolean;
}

export interface Policy {
  policyId: string;
  version: number;
  transactionLimit: number;
  dailyLimit: number;
  monthlyLimit: number;
  allowedCategories: Category[];
  blockedCategories: Category[];
  blockedMerchants: string[];
  approvalRules: ApprovalRules;
}

export interface Agent {
  agentId: string;
  name: string;
  ownerId: string;
  status: AgentStatus;
  trustScore: number;
  riskState: RiskState;
  policyId: string;
  createdAt: string;
}

export interface Intent {
  intentId: string;
  agentId: string;
  goal: string;
  category: Category;
  budget: number;
  currency: "INR";
  createdAt: string;
  expiresAt: string;
}

export interface PaymentRequest {
  requestId: string;
  agentId: string;
  intentId: string | null;
  merchant: string;
  product: string;
  amount: number;
  currency: "INR";
  category: Category;
  sessionId: string;
  timestamp: string;
}

export interface ReasonCode {
  code: string;
  label: string;
  severity: "ok" | "warn" | "block";
}

export interface RiskAssessment {
  score: number;
  level: RiskLevel;
  signals: string[];
}

export interface CircumventionResult {
  detected: boolean;
  score: number;
  aggregateAmount: number;
  windowCount: number;
}

export interface IntentAssessment {
  score: number;
  severe: boolean;
  warn: boolean;
  label: string;
}

export interface GuardDecision {
  requestId: string;
  decision: DecisionType;
  reasonCodes: ReasonCode[];
  riskScore: number;
  intentScore: number;
  circumventionScore: number;
  policyVersion: number;
  authorizationId: string | null;
  timestamp: string;
}

export interface Authorization {
  authorizationId: string;
  requestId: string;
  agentId: string;
  merchant: string;
  product: string;
  amount: number;
  currency: "INR";
  intentId: string | null;
  expiresAt: string;
  status: "AUTHORIZED" | "USED" | "EXPIRED";
}

export interface TransactionRecord {
  request: PaymentRequest;
  decision: GuardDecision;
  outcome: PaymentOutcome;
  decidedBy: "user" | "policy";
  userActionAt?: string;
  authorization?: Authorization;
}

export interface AuditEvent {
  eventId: string;
  requestId: string;
  at: string;
  label: string;
  detail?: string;
}

export interface AnomalyEvent {
  anomalyId: string;
  agentId: string;
  type: "CRITICAL_ANOMALY";
  observedTxns: number;
  observedMinutes: number;
  observedAmount: number;
  baselineTxnsPerDayMin: number;
  baselineTxnsPerDayMax: number;
  signals: string[];
  recommendation: "FREEZE_AGENT";
  createdAt: string;
  dismissed: boolean;
}

export interface SpendPoint {
  day: string;
  spend: number;
}
