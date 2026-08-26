"use client";

import React, { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import type { Agent, AuditEvent, GuardDecision, PaymentRequest, Policy, TransactionRecord } from "./types";

const STORAGE_KEY = "agentpay-api-base";
const TOKEN_KEY = "agentpay-token";
const DEFAULT_API = "http://127.0.0.1:8000";

export interface AuthUser {
  name: string;
  email: string;
}

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
  needsAuth: boolean;
  user: AuthUser | null;
  ownerExists: boolean;
  login: (email: string, password: string) => Promise<string | null>;
  register: (name: string, email: string, password: string) => Promise<string | null>;
  logout: () => void;
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

function extractError(data: { detail?: unknown }): string {
  const d = data?.detail;
  if (Array.isArray(d)) {
    return d
      .map((e) => {
        const item = e as { msg?: string; loc?: (string | number)[] };
        const field = item.loc && item.loc.length > 0 ? String(item.loc[item.loc.length - 1]) : "";
        return field && field !== "body" ? `${field}: ${item.msg}` : item.msg;
      })
      .filter(Boolean)
      .join("; ");
  }
  if (typeof d === "string") return d;
  return (d as { message?: string })?.message ?? "Request failed";
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
  const [token, setToken] = useState<string | null>(null);
  const [needsAuth, setNeedsAuth] = useState(true);
  const [user, setUser] = useState<AuthUser | null>(null);
  const [ownerExists, setOwnerExists] = useState(true);
  const apiBaseRef = useRef(apiBase);
  apiBaseRef.current = apiBase;
  const tokenRef = useRef(token);
  tokenRef.current = token;
  const pathname = usePathname();
  const router = useRouter();

  // Auth gate: unauthenticated users land on /login; signed-in users skip it.
  useEffect(() => {
    if (loading) return;
    if (needsAuth && pathname !== "/login") router.replace("/login");
    if (!needsAuth && user && pathname === "/login") router.replace("/");
  }, [loading, needsAuth, user, pathname, router]);

  // Initial boot: check saved base, verify token with /auth/me, and fetch owner status
  useEffect(() => {
    let cancelled = false;

    const init = async () => {
      let savedBase: string | null = null;
      let savedToken: string | null = null;
      try {
        savedBase = window.localStorage.getItem(STORAGE_KEY);
        savedToken = window.localStorage.getItem(TOKEN_KEY);
      } catch {
        void 0;
      }

      const base = (savedBase || DEFAULT_API).replace(/\/$/, "");
      if (savedBase) setApiBaseState(savedBase);

      try {
        const statusRes = await fetch(`${base}/auth/status`);
        if (statusRes.ok) {
          const statusData = await statusRes.json();
          if (!cancelled) setOwnerExists(!!statusData.ownerExists);
        }
      } catch {
        void 0;
      }

      if (savedToken) {
        tokenRef.current = savedToken;
        try {
          const meRes = await fetch(`${base}/auth/me`, {
            headers: { Authorization: `Bearer ${savedToken}` },
          });
          if (meRes.ok) {
            const meData = await meRes.json();
            if (!cancelled) {
              setToken(savedToken);
              setUser(meData.user);
              setNeedsAuth(false);
            }
          } else {
            try { window.localStorage.removeItem(TOKEN_KEY); } catch {}
            tokenRef.current = null;
            if (!cancelled) {
              setToken(null);
              setUser(null);
              setNeedsAuth(true);
            }
          }
        } catch {
          if (!cancelled) {
            setToken(savedToken);
            setNeedsAuth(false);
          }
        }
      } else {
        if (!cancelled) {
          setNeedsAuth(true);
        }
      }

      if (!cancelled) setLoading(false);
    };

    init();

    return () => {
      cancelled = true;
    };
  }, []);

  const applyAuth = useCallback((sessionToken: string, authUser: AuthUser) => {
    // Update the ref synchronously — refresh() called right after login must
    // already see the token, or it 401s and flips needsAuth back (redirect loop).
    tokenRef.current = sessionToken;
    try { window.localStorage.setItem(TOKEN_KEY, sessionToken); } catch {}
    setToken(sessionToken);
    setUser(authUser);
    setNeedsAuth(false);
    setOwnerExists(true);
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
    const headers: Record<string, string> = {};
    if (tokenRef.current) headers.Authorization = `Bearer ${tokenRef.current}`;
    try {
      const [agentsRes, policiesRes, txnsRes, pendingRes] = await Promise.all([
        fetch(`${base}/agents`, { headers, signal: AbortSignal.timeout(4000) }),
        fetch(`${base}/policies`, { headers, signal: AbortSignal.timeout(4000) }),
        fetch(`${base}/transactions`, { headers, signal: AbortSignal.timeout(4000) }),
        fetch(`${base}/guard/pending`, { signal: AbortSignal.timeout(4000) }),
      ]);
      // Any HTTP response (even 401) means the backend is REACHABLE.
      setConnected(true);
      if (agentsRes.status === 401) {
        try { window.localStorage.removeItem(TOKEN_KEY); } catch {}
        tokenRef.current = null;
        setToken(null);
        setNeedsAuth(true);
        setUser(null);
        setLoading(false);
        return;
      }
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

  // Live updates: WebSocket when reachable, 15s polling as fallback.
  // Fully paused while signed out — no 401 spam on the login page.
  useEffect(() => {
    if (loading || needsAuth || !token) return;
    refresh();
    const id = window.setInterval(refresh, 15000);
    return () => window.clearInterval(id);
  }, [loading, refresh, apiBase, needsAuth, token]);

  useEffect(() => {
    if (loading || needsAuth || !token) return;
    let ws: WebSocket | null = null;
    let closed = false;
    let reconnect: number | undefined;
    let lastEvent = 0;

    const connect = () => {
      const wsUrl = apiBase.replace(/^http/, "ws").replace(/\/$/, "") + "/ws/events";
      try {
        ws = new WebSocket(wsUrl);
        ws.onmessage = () => {
          // Debounce bursts of events into at most one refresh per second.
          const now = Date.now();
          if (now - lastEvent > 1000) {
            lastEvent = now;
            refresh();
          }
        };
        ws.onclose = () => {
          if (!closed) reconnect = window.setTimeout(connect, 5000);
        };
        ws.onerror = () => {
          ws?.close();
        };
      } catch {
        reconnect = window.setTimeout(connect, 5000);
      }
    };

    // Defer connection: React strict-mode mounts/unmounts effects twice in dev,
    // and connecting instantly then cleaning up logs browser warnings.
    const connectTimer = window.setTimeout(connect, 150);

    return () => {
      closed = true;
      window.clearTimeout(connectTimer);
      if (reconnect) window.clearTimeout(reconnect);
      if (ws) {
        ws.onclose = null;
        ws.onerror = null;
        if (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING) {
          ws.close();
        }
      }
    };
  }, [loading, apiBase, refresh, needsAuth, token]);

  const post = useCallback(async (path: string, body?: unknown) => {
    const base = apiBaseRef.current.replace(/\/$/, "");
    const headers: Record<string, string> = { "Content-Type": "application/json" };
    if (tokenRef.current) headers.Authorization = `Bearer ${tokenRef.current}`;
    const res = await fetch(`${base}${path}`, {
      method: "POST",
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
    });
    if (res.status === 401) {
      setNeedsAuth(true);
      setUser(null);
    }
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
        const headers: Record<string, string> = { "Content-Type": "application/json" };
        if (tokenRef.current) headers.Authorization = `Bearer ${tokenRef.current}`;
        const res = await fetch(`${base}/policies/${p.policyId}`, {
          method: "PUT",
          headers,
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

  const login = useCallback(async (email: string, password: string) => {
    const base = apiBaseRef.current.replace(/\/$/, "");
    try {
      const res = await fetch(`${base}/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });
      if (!res.ok) return extractError(await res.json());
      const data = await res.json();
      applyAuth(data.sessionToken, data.user);
      await refresh();
      return null;
    } catch (err) {
      return `Network error: ${err instanceof Error ? err.message : String(err)}`;
    }
  }, [applyAuth, refresh]);

  const register = useCallback(async (name: string, email: string, password: string) => {
    const base = apiBaseRef.current.replace(/\/$/, "");
    try {
      const res = await fetch(`${base}/auth/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, email, password }),
      });
      if (!res.ok) return extractError(await res.json());
      const data = await res.json();
      applyAuth(data.sessionToken, data.user);
      await refresh();
      return null;
    } catch (err) {
      return `Network error: ${err instanceof Error ? err.message : String(err)}`;
    }
  }, [applyAuth, refresh]);

  const logout = useCallback(() => {
    const base = apiBaseRef.current.replace(/\/$/, "");
    const token = tokenRef.current;
    tokenRef.current = null;
    if (token) {
      fetch(`${base}/auth/logout`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      }).catch(() => undefined);
    }
    try { window.localStorage.removeItem(TOKEN_KEY); } catch {}
    setToken(null);
    setUser(null);
    setNeedsAuth(true);
  }, []);

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
      needsAuth,
      user,
      ownerExists,
      login,
      register,
      logout,
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
      connected, loading, needsAuth, user, ownerExists, login, register, logout,
      apiBase, setApiBase, agents, policy, transactions, pending,
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
