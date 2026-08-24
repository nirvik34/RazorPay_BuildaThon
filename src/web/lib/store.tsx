"use client";

import React, { createContext, useCallback, useContext, useEffect, useMemo, useReducer, useRef } from "react";
import type {
  Agent,
  AnomalyEvent,
  AuditEvent,
  Category,
  PaymentRequest,
  Policy,
  SpendPoint,
  TransactionRecord
} from "./types";
import { auditChainFor, evaluateFull } from "./engine";
import { buildSeed } from "./seed";

const STORAGE_KEY = "agentpay-guard-v2";

export interface GuardState {
  agents: Agent[];
  policies: Policy[];
  intents: import("./types").Intent[];
  transactions: TransactionRecord[];
  audit: Record<string, AuditEvent[]>;
  anomalies: AnomalyEvent[];
  spendSeries: SpendPoint[];
  apiBase: string;
}

type Action =
  | { type: "hydrate"; state: GuardState }
  | { type: "reset" }
  | { type: "decide"; requestId: string; accept: boolean }
  | { type: "setAgentStatus"; agentId: string; status: Agent["status"] }
  | { type: "savePolicy"; policy: Policy }
  | { type: "ingest"; record: TransactionRecord }
  | { type: "appendAudit"; requestId: string; events: AuditEvent[] }
  | { type: "addAnomaly"; anomaly: AnomalyEvent }
  | { type: "dismissAnomaly"; anomalyId: string }
  | { type: "setRiskState"; agentId: string; riskState: Agent["riskState"] }
  | { type: "setApiBase"; url: string };

function freshState(): GuardState {
  const s = buildSeed();
  return { ...s, apiBase: "http://localhost:8000" };
}

function reducer(state: GuardState, action: Action): GuardState {
  switch (action.type) {
    case "hydrate":
      return action.state;
    case "reset":
      return freshState();
    case "decide": {
      const now = new Date().toISOString();
      const rec = state.transactions.find((r) => r.request.requestId === action.requestId);
      if (!rec || rec.userActionAt) return state;
      let transactions = state.transactions;
      let audit = state.audit;
      if (action.accept) {
        const authorizationId = `auth_${Math.random().toString(16).slice(2, 6)}`;
        const authorization = {
          authorizationId,
          requestId: rec.request.requestId,
          agentId: rec.request.agentId,
          merchant: rec.request.merchant,
          product: rec.request.product,
          amount: rec.request.amount,
          currency: "INR" as const,
          intentId: rec.request.intentId,
          expiresAt: new Date(Date.now() + 300000).toISOString(),
          status: "USED" as const
        };
        transactions = state.transactions.map((r) =>
          r.request.requestId === action.requestId
            ? { ...r, outcome: "CAPTURED", userActionAt: now, authorization }
            : r
        );
        audit = appendAuditEvents(state.audit, action.requestId, [
          ["User accepted"],
          ["Authorization issued", authorizationId],
          ["Payment initiated", "Razorpay order created"],
          ["Payment captured", authorizationId]
        ], now);
      } else {
        transactions = state.transactions.map((r) =>
          r.request.requestId === action.requestId ? { ...r, outcome: "DENIED", userActionAt: now } : r
        );
        audit = appendAuditEvents(state.audit, action.requestId, [
          ["User rejected transaction"],
          ["Authorization denied"],
          ["Agent informed", "Structured denial returned"]
        ], now);
      }
      return { ...state, transactions, audit };
    }
    case "setAgentStatus":
      return {
        ...state,
        agents: state.agents.map((a) => (a.agentId === action.agentId ? { ...a, status: action.status } : a)),
        anomalies:
          action.status !== "ACTIVE"
            ? state.anomalies.map((an) => (an.agentId === action.agentId ? { ...an, dismissed: true } : an))
            : state.anomalies
      };
    case "setRiskState":
      return {
        ...state,
        agents: state.agents.map((a) => (a.agentId === action.agentId ? { ...a, riskState: action.riskState } : a))
      };
    case "savePolicy": {
      const exists = state.policies.some((p) => p.policyId === action.policy.policyId);
      const policies = exists
        ? state.policies.map((p) => (p.policyId === action.policy.policyId ? action.policy : p))
        : [...state.policies, action.policy];
      return { ...state, policies };
    }
    case "ingest":
      return { ...state, transactions: [...state.transactions, action.record] };
    case "appendAudit": {
      const existing = state.audit[action.requestId] ?? [];
      return {
        ...state,
        audit: { ...state.audit, [action.requestId]: [...existing, ...action.events] }
      };
    }
    case "addAnomaly":
      return { ...state, anomalies: [action.anomaly, ...state.anomalies] };
    case "dismissAnomaly":
      return { ...state, anomalies: state.anomalies.map((a) => (a.anomalyId === action.anomalyId ? { ...a, dismissed: true } : a)) };
    case "setApiBase":
      return { ...state, apiBase: action.url };
    default:
      return state;
  }
}

function appendAuditEvents(
  audit: Record<string, AuditEvent[]>,
  requestId: string,
  rows: Array<[string] | [string, string?]>,
  at: string
): Record<string, AuditEvent[]> {
  const existing = audit[requestId] ?? [];
  const additions: AuditEvent[] = rows.map(([label, detail]) => ({
    eventId: `evt_${Math.random().toString(16).slice(2, 10)}`,
    requestId,
    at,
    label,
    detail
  }));
  return { ...audit, [requestId]: [...existing, ...additions] };
}

export function newRequestId(): string {
  return `req_${Math.random().toString(16).slice(2, 8)}`;
}

interface IngestInput {
  agentId: string;
  product: string;
  merchant: string;
  amount: number;
  category: Category;
  intentId?: string | null;
  sessionId?: string;
}

interface GuardContextValue {
  state: GuardState;
  decide: (requestId: string, accept: boolean) => void;
  freezeAgent: (agentId: string) => void;
  unfreezeAgent: (agentId: string) => void;
  revokeAgent: (agentId: string) => void;
  savePolicy: (policy: Policy) => void;
  ingestRequest: (input: IngestInput) => TransactionRecord | null;
  dismissAnomaly: (anomalyId: string) => void;
  resetDemo: () => void;
  setApiBase: (url: string) => void;
}

const GuardContext = createContext<GuardContextValue | null>(null);

export function GuardProvider({ children }: { children: React.ReactNode }) {
  const [state, dispatch] = useReducer(reducer, undefined, freshState);
  const loaded = useRef(false);

  useEffect(() => {
    if (loaded.current) return;
    loaded.current = true;
    try {
      const raw = window.localStorage.getItem(STORAGE_KEY);
      if (raw) dispatch({ type: "hydrate", state: JSON.parse(raw) as GuardState });
    } catch {
      void 0;
    }
  }, []);

  useEffect(() => {
    try {
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
    } catch {
      void 0;
    }
  }, [state]);

  const ingestRequest = useCallback(
    (input: IngestInput): TransactionRecord | null => {
      const agent = state.agents.find((a) => a.agentId === input.agentId);
      const policy = state.policies.find((p) => p.policyId === (agent?.policyId ?? "pol_default"));
      if (!agent || !policy) return null;
      const request: PaymentRequest = {
        requestId: newRequestId(),
        agentId: input.agentId,
        intentId: input.intentId ?? null,
        merchant: input.merchant.toLowerCase(),
        product: input.product,
        amount: input.amount,
        currency: "INR",
        category: input.category,
        sessionId: input.sessionId ?? `sess_${Math.random().toString(16).slice(2, 8)}`,
        timestamp: new Date().toISOString()
      };
      const evaluation = evaluateFull({
        request,
        agent,
        policy,
        history: state.transactions,
        intents: state.intents,
        now: new Date()
      });
      const record: TransactionRecord = {
        request,
        decision: evaluation.decision,
        outcome: "NOT_ATTEMPTED",
        decidedBy: evaluation.decision.decision === "BLOCK" ? "policy" : "user"
      };
      dispatch({ type: "ingest", record });
      const chain: AuditEvent[] = auditChainFor(record).map((e, idx) => ({
        eventId: `evt_${request.requestId}_${idx}`,
        requestId: request.requestId,
        at: e.at,
        label: e.label,
        detail: e.detail
      }));
      dispatch({ type: "appendAudit", requestId: request.requestId, events: chain });

      const cutoff = Date.now() - 600000;
      const recentCount =
        state.transactions.filter((r) => r.request.agentId === input.agentId && new Date(r.request.timestamp).getTime() >= cutoff).length + 1;
      if (recentCount >= 6 && !state.anomalies.some((a) => a.agentId === input.agentId && !a.dismissed)) {
        const observedAmount = state.transactions
          .filter((r) => r.request.agentId === input.agentId && new Date(r.request.timestamp).getTime() >= cutoff)
          .reduce((sum, r) => sum + r.request.amount, request.amount);
        dispatch({
          type: "addAnomaly",
          anomaly: {
            anomalyId: `anom_${Math.random().toString(16).slice(2, 6)}`,
            agentId: input.agentId,
            type: "CRITICAL_ANOMALY",
            observedTxns: recentCount,
            observedMinutes: 10,
            observedAmount,
            baselineTxnsPerDayMin: 5,
            baselineTxnsPerDayMax: 8,
            signals: ["High transaction velocity", "New merchants", "Unusual spending time", "Category deviation"],
            recommendation: "FREEZE_AGENT",
            createdAt: new Date().toISOString(),
            dismissed: false
          }
        });
        dispatch({ type: "setRiskState", agentId: input.agentId, riskState: "ELEVATED" });
      }
      return record;
    },
    [state]
  );

  const value = useMemo<GuardContextValue>(
    () => ({
      state,
      decide: (requestId, accept) => dispatch({ type: "decide", requestId, accept }),
      freezeAgent: (agentId) => dispatch({ type: "setAgentStatus", agentId, status: "FROZEN" }),
      unfreezeAgent: (agentId) => dispatch({ type: "setAgentStatus", agentId, status: "ACTIVE" }),
      revokeAgent: (agentId) => dispatch({ type: "setAgentStatus", agentId, status: "REVOKED" }),
      savePolicy: (policy) => dispatch({ type: "savePolicy", policy }),
      ingestRequest,
      dismissAnomaly: (anomalyId) => dispatch({ type: "dismissAnomaly", anomalyId }),
      resetDemo: () => {
        try {
          window.localStorage.removeItem(STORAGE_KEY);
        } catch {
          void 0;
        }
        dispatch({ type: "reset" });
      },
      setApiBase: (url) => dispatch({ type: "setApiBase", url })
    }),
    [state, ingestRequest]
  );

  return <GuardContext.Provider value={value}>{children}</GuardContext.Provider>;
}

export function useGuard(): GuardContextValue {
  const ctx = useContext(GuardContext);
  if (!ctx) throw new Error("useGuard must be used inside GuardProvider");
  return ctx;
}
