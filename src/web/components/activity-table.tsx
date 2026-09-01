"use client";

import Link from "next/link";
import type { TransactionRecord } from "@/lib/types";
import { formatINR, formatTime, formatReasonCode } from "@/lib/format";
import { StatusPill } from "@/components/status-pill";

export function ActivityTable({ records }: { records: TransactionRecord[] }) {
  return (
    <div className="overflow-x-auto rounded-md border border-border bg-card shadow-low">
      <table className="w-full text-left text-[13px]">
        <thead>
          <tr className="border-b border-border text-[11px] uppercase tracking-wider text-muted">
            <th className="px-4 py-2.5 font-semibold">Time</th>
            <th className="px-4 py-2.5 font-semibold">Agent</th>
            <th className="px-4 py-2.5 font-semibold">Merchant</th>
            <th className="px-4 py-2.5 font-semibold">Item</th>
            <th className="px-4 py-2.5 text-right font-semibold">Amount</th>
            <th className="px-4 py-2.5 font-semibold">Status</th>
            <th className="px-4 py-2.5 font-semibold">Reason</th>
          </tr>
        </thead>
        <tbody>
          {records.map((rec) => {
            const blockReason = rec.decision.reasonCodes.find((r) => r.severity === "block");
            const warnReason = rec.decision.reasonCodes.find((r) => r.severity === "warn");
            const rawReason =
              rec.decision.decision === "BLOCK"
                ? blockReason?.label || blockReason?.code || "BLOCKED"
                : rec.outcome === "DENIED"
                  ? "USER_REJECTED"
                  : (warnReason?.label || warnReason?.code || "APPROVED");
            const formattedReason = formatReasonCode(rawReason);
            return (
              <tr key={rec.request.requestId} className="border-b border-border last:border-b-0 hover:bg-background">
                <td className="whitespace-nowrap px-4 py-2.5 font-mono text-xs text-muted">{formatTime(rec.request.timestamp)}</td>
                <td className="whitespace-nowrap px-4 py-2.5 capitalize">{agentShort(rec.request.agentId)}</td>
                <td className="whitespace-nowrap px-4 py-2.5 capitalize">{rec.request.merchant}</td>
                <td className="max-w-[220px] truncate px-4 py-2.5">{rec.request.product}</td>
                <td className="whitespace-nowrap px-4 py-2.5 text-right font-mono tabular-nums">{formatINR(rec.request.amount)}</td>
                <td className="px-4 py-2.5">
                  <StatusPill decision={rec.decision.decision} outcome={rec.outcome} />
                </td>
                <td className="px-4 py-2.5">
                  <Link href={`/audit/${rec.request.requestId}`} className="text-xs font-medium text-brand hover:underline">
                    {formattedReason}
                  </Link>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function agentShort(agentId: string): string {
  if (agentId.startsWith("claude")) return "Claude";
  if (agentId.startsWith("gemini")) return "Gemini";
  if (agentId.startsWith("gpt")) return "GPT";
  return agentId;
}
