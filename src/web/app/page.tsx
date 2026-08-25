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
import { formatCompactINR, formatINR, formatTime } from "@/lib/format";
import { StatCard, PageHeader } from "@/components/stat-card";
import { Card, CardHeader } from "@/components/ui/card";
import { ActivityTable } from "@/components/activity-table";
import { StatusPill } from "@/components/status-pill";
import { AlertTriangle, Ban, Bot, Wallet, WifiOff } from "lucide-react";

function last7Days(transactions: ReturnType<typeof useGuard>["transactions"]) {
  const days: { day: string; spend: number }[] = [];
  const names = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
  for (let i = 6; i >= 0; i -= 1) {
    const d = new Date();
    d.setDate(d.getDate() - i);
    const key = d.toDateString();
    const spend = transactions
      .filter(
        (t) =>
          t.outcome === "CAPTURED" && new Date(t.request.timestamp).toDateString() === key
      )
      .reduce((sum, t) => sum + t.request.amount, 0);
    days.push({ day: i === 0 ? "Today" : names[d.getDay()], spend });
  }
  return days;
}

export default function DashboardPage() {
  const { transactions, agents, pending, connected, policy } = useGuard();

  const isToday = (iso: string) =>
    new Date(iso).toDateString() === new Date().toDateString();

  const capturedToday = transactions.filter(
    (r) => r.outcome === "CAPTURED" && isToday(r.request.timestamp)
  );
  const spendToday = capturedToday.reduce((sum, r) => sum + r.request.amount, 0);
  const blocked = transactions.filter((r) => r.decision.decision === "BLOCK");
  const activeAgents = agents.filter((a) => a.status === "ACTIVE");
  const recent = [...transactions]
    .sort((a, b) => new Date(b.request.timestamp).getTime() - new Date(a.request.timestamp).getTime())
    .slice(0, 6);
  const series = last7Days(transactions);

  return (
    <div>
      <PageHeader
        title="Dashboard"
        description="Is my AI spending safely? Every consequential action by your agents passes through this device."
      />

      {!connected && (
        <div className="mb-6 flex items-center gap-2 rounded-md border border-danger-border bg-danger-bg px-4 py-3 text-[13px] font-medium text-danger-text">
          <WifiOff className="h-4 w-4" />
          Backend offline — start it with `uvicorn app.main:app` in src/backend. Data shown is live-only.
        </div>
      )}

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
        <StatCard label="Today's Spend" value={formatINR(spendToday)} sub={`${capturedToday.length} payments captured`} icon={<Wallet className="h-4 w-4 text-muted" />} />
        <StatCard label="Pending Approvals" value={String(pending.length)} sub={pending.length > 0 ? "Action required" : "You're all caught up"} tone={pending.length > 0 ? "warning" : "neutral"} icon={<AlertTriangle className="h-4 w-4 text-warning" />} />
        <StatCard label="Active Agents" value={String(activeAgents.length)} sub={`${agents.length} registered`} icon={<Bot className="h-4 w-4 text-muted" />} />
        <StatCard label="Blocked Actions" value={String(blocked.length)} sub="Policy enforced automatically" tone={blocked.length > 0 ? "danger" : "neutral"} icon={<Ban className="h-4 w-4 text-danger" />} />
      </div>

      <div className="mt-6 grid grid-cols-1 gap-6 xl:grid-cols-3">
        <Card className="xl:col-span-2">
          <CardHeader title="Recent AI activity" action={<a href="/activity" className="text-[13px] font-medium text-brand hover:underline">View all</a>} />
          {recent.length === 0 ? (
            <p className="px-5 py-8 text-sm text-muted">
              No agent activity yet. Connect Claude via the AgentPay connector and ask it to buy something.
            </p>
          ) : (
            <ActivityTable records={recent} />
          )}
        </Card>

        <Card>
          <CardHeader title="7-day delegated spend" />
          <div className="h-56 px-4 py-4">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={series}>
                <defs>
                  <linearGradient id="spendFill" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#0D94FB" stopOpacity={0.18} />
                    <stop offset="100%" stopColor="#0D94FB" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#EBECF0" vertical={false} />
                <XAxis dataKey="day" tickLine={false} axisLine={{ stroke: "#EBECF0" }} tick={{ fontSize: 11, fill: "#5E6C84" }} />
                <YAxis tickFormatter={(v: number) => formatCompactINR(v)} tickLine={false} axisLine={false} tick={{ fontSize: 11, fill: "#5E6C84" }} width={54} />
                <Tooltip formatter={(v) => [formatINR(Number(v)), "Spend"]} contentStyle={{ borderRadius: 6, borderColor: "#EBECF0", fontSize: 12 }} />
                <Area type="monotone" dataKey="spend" stroke="#0D94FB" strokeWidth={2} fill="url(#spendFill)" />
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
            {pending.map(({ request, decision }) => (
              <div key={request.requestId} className="flex items-center justify-between px-5 py-3.5">
                <div>
                  <div className="text-sm font-medium text-foreground">{request.product}</div>
                  <div className="font-mono text-[11px] text-muted">
                    {request.agentId} · {formatINR(request.amount)} · {formatTime(request.timestamp)}
                  </div>
                </div>
                <StatusPill decision={decision.decision} outcome="NOT_ATTEMPTED" />
              </div>
            ))}
          </div>
        </Card>

        <Card>
          <CardHeader title="Live protection" />
          <div className="space-y-3 p-5">
            <div className="rounded-sm border border-border bg-background p-3 text-[12px] leading-relaxed text-muted">
              Hard limits, blocked categories and circumvention detection run on every request
              before you ever see it. Approve or reject from the Approvals queue — your decision
              gates the pending Razorpay checkout instantly.
            </div>
            <div className="rounded-sm border border-border bg-background p-3">
              <div className="text-[10px] font-bold uppercase tracking-wider text-muted">Active policy</div>
              <div className="mt-1 font-mono text-[12px] text-foreground">
                {policy
                  ? `v${policy.version} · ₹${policy.transactionLimit}/txn · ₹${policy.dailyLimit}/day · blocked: ${policy.blockedCategories.join(", ") || "none"}`
                  : "—"}
              </div>
            </div>
          </div>
        </Card>
      </div>
    </div>
  );
}
