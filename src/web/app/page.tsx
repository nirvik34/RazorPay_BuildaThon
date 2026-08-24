"use client";

import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis
} from "recharts";
import { useGuard } from "@/lib/store";
import { formatCompactINR, formatINR, relativeDay } from "@/lib/format";
import { StatCard, PageHeader } from "@/components/stat-card";
import { Card, CardHeader } from "@/components/ui/card";
import { ActivityTable } from "@/components/activity-table";
import { StatusPill } from "@/components/status-pill";
import { AlertTriangle, Ban, Bot, Wallet } from "lucide-react";

export default function DashboardPage() {
  const { state } = useGuard();

  const pending = state.transactions.filter(
    (r) => r.decision.decision === "USER_APPROVAL" && !r.userActionAt
  );
  const captured = state.transactions.filter(
    (r) => r.outcome === "CAPTURED" && new Date(r.request.timestamp).toDateString() === new Date().toDateString()
  );
  const spendToday = captured.reduce((sum, r) => sum + r.request.amount, 0);
  const blocked = state.transactions.filter((r) => r.decision.decision === "BLOCK");
  const activeAgents = state.agents.filter((a) => a.status === "ACTIVE");
  const openAnomalies = state.anomalies.filter((a) => !a.dismissed);
  const recent = [...state.transactions]
    .sort((a, b) => new Date(b.request.timestamp).getTime() - new Date(a.request.timestamp).getTime())
    .slice(0, 6);

  return (
    <div>
      <PageHeader
        title="Dashboard"
        description="Is my AI spending safely? Every consequential action by your agents passes through this device."
      />

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
        <StatCard label="Today's Spend" value={formatINR(spendToday)} sub={`${captured.length} payments captured`} icon={<Wallet className="h-4 w-4 text-muted" />} />
        <StatCard label="Pending Approvals" value={String(pending.length)} sub={pending.length > 0 ? "Action required" : "You're all caught up"} tone={pending.length > 0 ? "warning" : "neutral"} icon={<AlertTriangle className="h-4 w-4 text-warning" />} />
        <StatCard label="Active Agents" value={String(activeAgents.length)} sub={`${state.agents.length} registered`} icon={<Bot className="h-4 w-4 text-muted" />} />
        <StatCard label="Blocked Actions" value={String(blocked.length)} sub="Policy enforced automatically" tone={blocked.length > 0 ? "danger" : "neutral"} icon={<Ban className="h-4 w-4 text-danger" />} />
      </div>

      {openAnomalies.length > 0 && (
        <div className="mt-6 rounded-md border border-danger-border border-l-4 border-l-danger bg-card p-5 shadow-low">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-[13px] font-bold uppercase tracking-wide text-danger-text">Critical agent anomaly</div>
              <p className="mt-1 text-sm text-foreground">
                {state.agents.find((a) => a.agentId === openAnomalies[0].agentId)?.name} —{" "}
                {openAnomalies[0].observedTxns} transactions in {openAnomalies[0].observedMinutes} minutes,{" "}
                exposure {formatINR(openAnomalies[0].observedAmount)}.
              </p>
            </div>
            <a
              href="/risk"
              className="rounded-sm bg-danger px-4 py-2 text-[13px] font-semibold text-white hover:bg-danger/90"
            >
              REVIEW &amp; FREEZE
            </a>
          </div>
        </div>
      )}

      <div className="mt-6 grid grid-cols-1 gap-6 xl:grid-cols-3">
        <Card className="xl:col-span-2">
          <CardHeader title="Recent AI activity" action={<a href="/activity" className="text-[13px] font-medium text-brand hover:underline">View all</a>} />
          <ActivityTable records={recent} />
        </Card>

        <Card>
          <CardHeader title="7-day delegated spend" />
          <div className="h-56 px-4 py-4">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={state.spendSeries}>
                <defs>
                  <linearGradient id="spendFill" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#2563EB" stopOpacity={0.18} />
                    <stop offset="100%" stopColor="#2563EB" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#E4E7EC" vertical={false} />
                <XAxis dataKey="day" tickLine={false} axisLine={{ stroke: "#E4E7EC" }} tick={{ fontSize: 11, fill: "#667085" }} />
                <YAxis tickFormatter={(v: number) => formatCompactINR(v)} tickLine={false} axisLine={false} tick={{ fontSize: 11, fill: "#667085" }} width={54} />
                <Tooltip formatter={(v) => [formatINR(Number(v)), "Spend"]} contentStyle={{ borderRadius: 10, borderColor: "#E4E7EC", fontSize: 12 }} />
                <Area type="monotone" dataKey="spend" stroke="#2563EB" strokeWidth={2} fill="url(#spendFill)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </Card>
      </div>

      <div className="mt-6 grid grid-cols-1 gap-6 xl:grid-cols-2">
        <Card>
          <CardHeader title="Pending approvals" action={<a href="/approvals" className="text-[13px] font-medium text-brand hover:underline">Open queue</a>} />
          <div className="divide-y divide-border">
            {pending.length === 0 && (
              <p className="px-5 py-6 text-sm text-muted">No AI agent currently needs your approval.</p>
            )}
            {pending.map((rec) => (
              <div key={rec.request.requestId} className="flex items-center justify-between px-5 py-3.5">
                <div>
                  <div className="text-sm font-medium text-foreground">{rec.request.product}</div>
                  <div className="font-mono text-[11px] text-muted">
                    {rec.request.agentId} · {formatINR(rec.request.amount)} · {relativeDay(rec.request.timestamp)}{" "}
                    {new Date(rec.request.timestamp).toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit", hour12: false })}
                  </div>
                </div>
                <StatusPill decision={rec.decision.decision} outcome={rec.outcome} />
              </div>
            ))}
          </div>
        </Card>

        <Card>
          <CardHeader title="Risk overview" action={<a href="/risk" className="text-[13px] font-medium text-brand hover:underline">Risk console</a>} />
          <div className="space-y-3 p-5">
            {openAnomalies.length === 0 ? (
              <p className="text-sm text-muted">No active risks. Your agents are behaving within their current baseline.</p>
            ) : (
              openAnomalies.map((anomaly) => (
                <div key={anomaly.anomalyId} className="rounded-sm border border-danger-border bg-danger-bg p-3">
                  <div className="text-[13px] font-semibold text-danger-text">{anomaly.type.replace("_", " ")}</div>
                  <div className="mt-0.5 font-mono text-[11px] text-muted">{anomaly.agentId}</div>
                  <ul className="mt-2 list-disc pl-4 text-[12px] text-foreground">
                    {anomaly.signals.slice(0, 3).map((s) => (
                      <li key={s}>{s}</li>
                    ))}
                  </ul>
                </div>
              ))
            )}
            <div className="rounded-sm border border-border bg-background p-3 text-[12px] text-muted">
              Hard limits, blocked categories and circumvention detection run locally on this device — even offline.
            </div>
          </div>
        </Card>
      </div>
    </div>
  );
}
