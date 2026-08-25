"use client";

import React, { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";
import type { Agent, AuditEvent, GuardDecision, PaymentRequest, Policy, TransactionRecord } from "./types";

const STORAGE_KEY = "agentpay-api-base";
const DEFAULT_API = "http://localhost:8000";

export interface PendingItem {
  request: PaymentRequest;
  decision: GuardDecision;
}

export interface SimulationReport {
  total: number;
  allowed: number;
  approvalRequired: number;
  blocked: number;
  byReason: Record<string, number>;
  preventedAmount: number;
  stages: { received: number; authority: number; policy: number; risk: number; decided: number };
}

interface GuardContextValue {
  connected: boolean;
  loading: boolean;
  apiBase: string;
  setApiBase: (url: string) => void;
  agents: Agent[];
  policy: Policy | null;
  transactions: TransactionRecord[];
  pending: PendingItem[];
  refresh: () => Promise<void>;
  decide: (requestId: string, accept: boolean) => Promise<boolean>;
  setAgentStatus: (agentId: string, status: Agent["status"]) => Promise<void>;
  savePolicy: (policy: Policy) => Promise<void>;
  runSimulation: (count: number, seed: number) => Promise<SimulationReport | null>;
  sendAgentRequest: (body: Record<string, unknown>) => Promise<GuardDecision | null>;
  getAudit: (requestId: string) => Promise<AuditEvent[]>;
}

const GuardContext = createContext<GuardContextValue | null>(null);

export function GuardProvider({ children }: { children: React.ReactNode }) {
  const [apiBase, setApiBaseState] = useState(DEFAULT_API);
  const [connected, setConnected] = useState(false);
  const [loading, setLoading] = useState(true);
  const [agents, setAgents] = useState<Agent[]>([]);
  const [policy, setPolicy] = useState<Policy | null>(null);
  const [transactions, setTransactions] = useState<TransactionRecord[]>([]);
  const [pending, setPending] = useState<PendingItem[]>([]);
  const apiBaseRef = useRef(apiBase);
  apiBaseRef.current = apiBase;

  useEffect(() => {
    try {
      const saved = window.localStorage.getItem(STORAGE_KEY);
      if (saved) setApiBaseState(saved);
    } catch {
      void 0;
    }
  }, []);

  const setApiBase = useCallback((url: string) => {
    setApiBaseState(url);
    try {
      window.localStorage.setItem(STORAGE_KEY, url);
    } catch {
      void 0;
    }
  }, []);

  const refresh = useCallback(async () => {
    const base = apiBaseRef.current.replace(/\/$/, "");
    try {
      const [agentsRes, policiesRes, txnsRes, pendingRes] = await Promise.all([
        fetch(`${base}/agents`, { signal: AbortSignal.timeout(4000) }),
        fetch(`${base}/policies`, { signal: AbortSignal.timeout(4000) }),
        fetch(`${base}/transactions`, { signal: AbortSignal.timeout(4000) }),
        fetch(`${base}/guard/pending`, { signal: AbortSignal.timeout(4000) }),
      ]);
      if (!agentsRes.ok || !txnsRes.ok) throw new Error("bad status");
      const agentsData = await agentsRes.json();
      const policiesData = await policiesRes.json();
      const txnsData = await txnsRes.json();
      const pendingData = pendingRes.ok ? await pendingRes.json() : [];

      setAgents(agentsData.agents ?? []);
      setPolicy(policiesData.policies?.[0] ?? null);
      setTransactions(
        (txnsData.transactions ?? []).map((t: Record<string, unknown>) => ({
          request: t.request,
          decision: t.decision,
          outcome: t.outcome ?? "NOT_ATTEMPTED",
          decidedBy:
            t.decision && (t.decision as GuardDecision).decision === "BLOCK" ? "policy" : "user",
          authorization: t.authorization,
        })) as TransactionRecord[]
      );
      setPending(pendingData ?? []);
      setConnected(true);
    } catch {
      setConnected(false);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
    const id = window.setInterval(refresh, 3000);
    return () => window.clearInterval(id);
  }, [refresh, apiBase]);

  const post = useCallback(async (path: string, body?: unknown) => {
    const base = apiBaseRef.current.replace(/\/$/, "");
    const res = await fetch(`${base}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
    if (!res.ok) throw new Error(`${path} failed: ${res.status}`);
    return res.json();
  }, []);

  const decide = useCallback(
    async (requestId: string, accept: boolean) => {
      try {
        await post(`/guard/approvals/${requestId}/action`, { action: accept ? "accept" : "reject" });
        await refresh();
        return true;
      } catch {
        return false;
      }
    },
    [post, refresh]
  );

  const setAgentStatus = useCallback(
    async (agentId: string, status: Agent["status"]) => {
      try {
        await post(`/guard/agents/${agentId}/${status.toLowerCase()}`);
        await refresh();
      } catch {
        void 0;
      }
    },
    [post, refresh]
  );

  const savePolicy = useCallback(
    async (p: Policy) => {
      try {
        const base = apiBaseRef.current.replace(/\/$/, "");
        const res = await fetch(`${base}/policies/${p.policyId}`, {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            transactionLimit: p.transactionLimit,
            dailyLimit: p.dailyLimit,
            monthlyLimit: p.monthlyLimit,
            blockedCategories: p.blockedCategories,
            blockedMerchants: p.blockedMerchants,
            amountAbove: p.approvalRules.amountAbove,
            newMerchant: p.approvalRules.newMerchant,
            highRisk: p.approvalRules.highRisk,
          }),
        });
        if (!res.ok) throw new Error("policy save failed");
        await refresh();
      } catch {
        void 0;
      }
    },
    [refresh]
  );

  const runSimulation = useCallback(
    async (count: number, seed: number) => {
      try {
        const r = await post("/simulate", { count, seed });
        return {
          total: r.requests ?? count,
          allowed: r.allowed ?? 0,
          approvalRequired: r.approvalRequired ?? 0,
          blocked: r.blocked ?? 0,
          byReason: r.byReason ?? {},
          preventedAmount: r.preventedAmount ?? 0,
          stages: r.stages ?? { received: count, authority: 0, policy: 0, risk: 0, decided: count },
        } as SimulationReport;
      } catch {
        return null;
      }
    },
    [post]
  );

  const sendAgentRequest = useCallback(
    async (body: Record<string, unknown>) => {
      try {
        const r = await post("/agent/payment-request", body);
        await refresh();
        return r as GuardDecision;
      } catch {
        return null;
      }
    },
    [post, refresh]
  );

  const getAudit = useCallback(async (requestId: string) => {
    const base = apiBaseRef.current.replace(/\/$/, "");
    try {
      const res = await fetch(`${base}/audit/${requestId}`, { signal: AbortSignal.timeout(4000) });
      if (!res.ok) return [];
      const data = await res.json();
      return data.audit ?? [];
    } catch {
      return [];
    }
  }, []);

  const value = useMemo<GuardContextValue>(
    () => ({
      connected,
      loading,
      apiBase,
      setApiBase,
      agents,
      policy,
      transactions,
      pending,
      refresh,
      decide,
      setAgentStatus,
      savePolicy,
      runSimulation,
      sendAgentRequest,
      getAudit,
    }),
    [
      connected, loading, apiBase, setApiBase, agents, policy, transactions, pending,
      refresh, decide, setAgentStatus, savePolicy, runSimulation, sendAgentRequest, getAudit,
    ]
  );

  return <GuardContext.Provider value={value}>{children}</GuardContext.Provider>;
}

export function useGuard(): GuardContextValue {
  const ctx = useContext(GuardContext);
  if (!ctx) throw new Error("useGuard must be used inside GuardProvider");
  return ctx;
}
