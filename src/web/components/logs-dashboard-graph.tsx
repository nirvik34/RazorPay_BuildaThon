"use client";

import { useMemo } from "react";
import {
  AreaChart,
  Area,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend
} from "recharts";
import type { TransactionRecord } from "@/lib/types";
import { formatCompactINR, formatINR, formatTime } from "@/lib/format";
import { Card, CardHeader } from "@/components/ui/card";
import { ShieldCheck, ShieldAlert, Ban, Activity, Wallet, Bot, TrendingUp, AlertTriangle } from "lucide-react";

interface LogsDashboardGraphProps {
  records: TransactionRecord[];
}

const DECISION_COLORS: Record<string, string> = {
  ALLOW: "#10B981", // Emerald
  USER_APPROVAL: "#F59E0B", // Amber
  BLOCK: "#EF4444" // Red
};

const RISK_LEVEL_COLORS = ["#10B981", "#3B82F6", "#F59E0B", "#EF4444"];

export function LogsDashboardGraph({ records }: LogsDashboardGraphProps) {
  // Compute analytics from records
  const stats = useMemo(() => {
    const totalCount = records.length;
    const totalSpend = records.reduce((sum, r) => sum + r.request.amount, 0);
    const capturedSpend = records
      .filter((r) => r.outcome === "CAPTURED")
      .reduce((sum, r) => sum + r.request.amount, 0);

    const allowed = records.filter((r) => r.decision.decision === "ALLOW").length;
    const pending = records.filter((r) => r.decision.decision === "USER_APPROVAL").length;
    const blocked = records.filter((r) => r.decision.decision === "BLOCK").length;

    const avgRisk = totalCount > 0
      ? Math.round(records.reduce((sum, r) => sum + r.decision.riskScore, 0) / totalCount)
      : 0;

    const blockRate = totalCount > 0 ? ((blocked / totalCount) * 100).toFixed(1) : "0";

    return {
      totalCount,
      totalSpend,
      capturedSpend,
      allowed,
      pending,
      blocked,
      avgRisk,
      blockRate
    };
  }, [records]);

  // Timeline Series Data
  const timelineData = useMemo(() => {
    if (records.length === 0) return [];
    
    // Group records by hour or time block
    const map = new Map<string, { timeLabel: string; spend: number; count: number; blocked: number }>();
    const sorted = [...records].sort(
      (a, b) => new Date(a.request.timestamp).getTime() - new Date(b.request.timestamp).getTime()
    );

    for (const rec of sorted) {
      const date = new Date(rec.request.timestamp);
      const timeLabel = `${date.getHours().toString().padStart(2, "0")}:${(
        Math.floor(date.getMinutes() / 15) * 15
      )
        .toString()
        .padStart(2, "0")}`;

      const existing = map.get(timeLabel) ?? { timeLabel, spend: 0, count: 0, blocked: 0 };
      existing.spend += rec.request.amount;
      existing.count += 1;
      if (rec.decision.decision === "BLOCK") existing.blocked += 1;
      map.set(timeLabel, existing);
    }

    return Array.from(map.values());
  }, [records]);

  // Decision Breakdown Pie Data
  const decisionPieData = useMemo(() => {
    return [
      { name: "Allowed", value: stats.allowed, color: DECISION_COLORS.ALLOW },
      { name: "User Approval", value: stats.pending, color: DECISION_COLORS.USER_APPROVAL },
      { name: "Blocked", value: stats.blocked, color: DECISION_COLORS.BLOCK }
    ].filter((d) => d.value > 0);
  }, [stats]);

  // Risk Score Bucket Distribution
  const riskDistributionData = useMemo(() => {
    const buckets = [
      { range: "0 - 25 (Low)", count: 0, color: "#10B981" },
      { range: "26 - 50 (Med)", count: 0, color: "#3B82F6" },
      { range: "51 - 75 (High)", count: 0, color: "#F59E0B" },
      { range: "76 - 100 (Crit)", count: 0, color: "#EF4444" }
    ];

    for (const r of records) {
      const score = r.decision.riskScore;
      if (score <= 25) buckets[0].count += 1;
      else if (score <= 50) buckets[1].count += 1;
      else if (score <= 75) buckets[2].count += 1;
      else buckets[3].count += 1;
    }

    return buckets;
  }, [records]);

  // Agent Activity & Risk Breakdown
  const agentBreakdownData = useMemo(() => {
    const map = new Map<string, { agent: string; count: number; spend: number; avgRisk: number; totalRisk: number }>();

    for (const r of records) {
      const agent = r.request.agentId.replace(/-.*/, "").toUpperCase();
      const existing = map.get(agent) ?? { agent, count: 0, spend: 0, avgRisk: 0, totalRisk: 0 };
      existing.count += 1;
      existing.spend += r.request.amount;
      existing.totalRisk += r.decision.riskScore;
      existing.avgRisk = Math.round(existing.totalRisk / existing.count);
      map.set(agent, existing);
    }

    return Array.from(map.values());
  }, [records]);

  // Reason Code Frequency Breakdown
  const reasonCodeData = useMemo(() => {
    const map = new Map<string, number>();

    for (const r of records) {
      for (const reason of r.decision.reasonCodes) {
        if (reason.code !== "OK") {
          map.set(reason.label || reason.code, (map.get(reason.label || reason.code) ?? 0) + 1);
        }
      }
    }

    return Array.from(map.entries())
      .map(([reason, count]) => ({ reason, count }))
      .sort((a, b) => b.count - a.count)
      .slice(0, 5);
  }, [records]);

  if (records.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-slate-300 bg-white p-12 text-center shadow-xs">
        <Activity className="h-10 w-10 text-slate-400 mb-3" />
        <h3 className="text-base font-bold text-slate-800">No Log Activity Data</h3>
        <p className="text-xs text-slate-500 max-w-sm mt-1">
          Graph dashboard visualization will display analytics here once agent logs are generated.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Overview Metric Row */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <div className="rounded-xl border border-slate-200/80 bg-white p-4 shadow-xs">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">Total Volume</span>
            <Wallet className="h-4 w-4 text-blue-600" />
          </div>
          <div className="mt-2 text-2xl font-black text-slate-900 font-mono tracking-tight">
            {formatINR(stats.totalSpend)}
          </div>
          <div className="mt-1 text-[11.5px] font-semibold text-emerald-600 flex items-center gap-1">
            <TrendingUp className="h-3.5 w-3.5" /> {formatINR(stats.capturedSpend)} captured
          </div>
        </div>

        <div className="rounded-xl border border-slate-200/80 bg-white p-4 shadow-xs">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">Log Entries</span>
            <Activity className="h-4 w-4 text-slate-500" />
          </div>
          <div className="mt-2 text-2xl font-black text-slate-900 font-mono tracking-tight">
            {stats.totalCount} <span className="text-xs font-semibold text-slate-400">records</span>
          </div>
          <div className="mt-1 text-[11.5px] font-medium text-slate-500">
            {stats.allowed} auto-pass · {stats.pending} pending
          </div>
        </div>

        <div className="rounded-xl border border-slate-200/80 bg-white p-4 shadow-xs">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">Block Rate</span>
            <Ban className="h-4 w-4 text-red-500" />
          </div>
          <div className="mt-2 text-2xl font-black text-red-600 font-mono tracking-tight">
            {stats.blockRate}%
          </div>
          <div className="mt-1 text-[11.5px] font-medium text-slate-500">
            {stats.blocked} unauthorized attempts stopped
          </div>
        </div>

        <div className="rounded-xl border border-slate-200/80 bg-white p-4 shadow-xs">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">Average Risk</span>
            <ShieldAlert className="h-4 w-4 text-amber-500" />
          </div>
          <div className="mt-2 text-2xl font-black text-slate-900 font-mono tracking-tight flex items-baseline gap-1">
            {stats.avgRisk} <span className="text-xs font-normal text-slate-400">/ 100</span>
          </div>
          <div className="mt-1 text-[11.5px] font-medium text-amber-600">
            Automated Risk Evaluation Engine
          </div>
        </div>
      </div>

      {/* Row 2: Timeline & Decision Distribution */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Timeline Chart */}
        <Card className="lg:col-span-2 border-slate-200 shadow-xs">
          <CardHeader
            title="Log Activity & Transaction Timeline"
            action={<span className="text-xs font-mono font-semibold text-slate-400">Real-time Telemetry</span>}
          />
          <div className="h-64 px-4 pb-4">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={timelineData}>
                <defs>
                  <linearGradient id="spendGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#2563EB" stopOpacity={0.25} />
                    <stop offset="100%" stopColor="#2563EB" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#F1F5F9" vertical={false} />
                <XAxis dataKey="timeLabel" tickLine={false} axisLine={{ stroke: "#E2E8F0" }} tick={{ fontSize: 11, fill: "#64748B" }} />
                <YAxis tickFormatter={(v: number) => formatCompactINR(v)} tickLine={false} axisLine={false} tick={{ fontSize: 11, fill: "#64748B" }} width={54} />
                <Tooltip
                  formatter={(v, name) => [
                    name === "spend" ? formatINR(Number(v)) : v,
                    name === "spend" ? "Amount" : "Count"
                  ]}
                  contentStyle={{ borderRadius: 8, borderColor: "#CBD5E1", fontSize: 12, boxShadow: "0 4px 6px -1px rgba(0, 0, 0, 0.1)" }}
                />
                <Area type="monotone" dataKey="spend" stroke="#2563EB" strokeWidth={2.5} fill="url(#spendGrad)" name="spend" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </Card>

        {/* Decision Ratio Pie Chart */}
        <Card className="border-slate-200 shadow-xs">
          <CardHeader title="Guard Decision Distribution" />
          <div className="h-64 px-4 pb-4 flex flex-col items-center justify-center">
            <ResponsiveContainer width="100%" height="80%">
              <PieChart>
                <Pie
                  data={decisionPieData}
                  cx="50%"
                  cy="50%"
                  innerRadius={50}
                  outerRadius={75}
                  paddingAngle={4}
                  dataKey="value"
                >
                  {decisionPieData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip formatter={(v) => [`${v} logs`, "Frequency"]} />
              </PieChart>
            </ResponsiveContainer>
            <div className="flex justify-center gap-4 text-xs font-semibold">
              {decisionPieData.map((item) => (
                <div key={item.name} className="flex items-center gap-1.5">
                  <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: item.color }} />
                  <span className="text-slate-600">{item.name} ({item.value})</span>
                </div>
              ))}
            </div>
          </div>
        </Card>
      </div>

      {/* Row 3: Agent Breakdown & Risk Distribution */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Agent Activity Bar Chart */}
        <Card className="border-slate-200 shadow-xs">
          <CardHeader title="Activity & Spend by AI Agent" />
          <div className="h-60 px-4 pb-4">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={agentBreakdownData} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" stroke="#F1F5F9" horizontal={false} />
                <XAxis type="number" tickFormatter={(v: number) => formatCompactINR(v)} tickLine={false} axisLine={false} tick={{ fontSize: 11, fill: "#64748B" }} />
                <YAxis dataKey="agent" type="category" tickLine={false} axisLine={{ stroke: "#E2E8F0" }} tick={{ fontSize: 11, fill: "#334155", fontWeight: 600 }} width={70} />
                <Tooltip formatter={(v, name) => [name === "spend" ? formatINR(Number(v)) : v, name === "spend" ? "Spend" : "Avg Risk Score"]} />
                <Bar dataKey="spend" fill="#3B82F6" radius={[0, 4, 4, 0]} barSize={20} name="spend" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>

        {/* Risk Score Distribution */}
        <Card className="border-slate-200 shadow-xs">
          <CardHeader title="Risk Score Bucket Breakdown" />
          <div className="h-60 px-4 pb-4">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={riskDistributionData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#F1F5F9" vertical={false} />
                <XAxis dataKey="range" tickLine={false} axisLine={{ stroke: "#E2E8F0" }} tick={{ fontSize: 11, fill: "#64748B" }} />
                <YAxis tickLine={false} axisLine={false} tick={{ fontSize: 11, fill: "#64748B" }} allowDecimals={false} />
                <Tooltip formatter={(v) => [`${v} logs`, "Records"]} />
                <Bar dataKey="count" radius={[4, 4, 0, 0]} barSize={32}>
                  {riskDistributionData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>
      </div>

      {/* Row 4: Triggered Guardrail Rules / Block Reasons if available */}
      {reasonCodeData.length > 0 && (
        <Card className="border-slate-200 shadow-xs">
          <CardHeader title="Top Triggered Guardrail Policies & Reason Codes" />
          <div className="p-5">
            <div className="space-y-3">
              {reasonCodeData.map(({ reason, count }) => {
                const percentage = Math.round((count / stats.totalCount) * 100);
                return (
                  <div key={reason} className="space-y-1">
                    <div className="flex items-center justify-between text-xs">
                      <span className="font-semibold text-slate-800 font-mono">{reason}</span>
                      <span className="font-mono text-slate-500">{count} occurrences ({percentage}%)</span>
                    </div>
                    <div className="h-2 w-full rounded-full bg-slate-100 overflow-hidden">
                      <div
                        className="h-full bg-amber-500 rounded-full transition-all duration-300"
                        style={{ width: `${Math.max(percentage, 5)}%` }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </Card>
      )}
    </div>
  );
}
