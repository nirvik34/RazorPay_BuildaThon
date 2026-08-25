"use client";

import { useState } from "react";
import clsx from "clsx";
import { useGuard } from "@/lib/store";
import { PageHeader, EmptyState } from "@/components/stat-card";
import { ActivityTable } from "@/components/activity-table";

const FILTERS = ["ALL", "APPROVED", "PENDING", "BLOCKED"] as const;
type Filter = (typeof FILTERS)[number];

export default function ActivityPage() {
  const { transactions } = useGuard();
  const [filter, setFilter] = useState<Filter>("ALL");

  const records = [...transactions]
    .filter((rec) => {
      if (filter === "ALL") return true;
      if (filter === "BLOCKED") return rec.decision.decision === "BLOCK";
      if (filter === "PENDING") return rec.decision.decision === "USER_APPROVAL" && !rec.userActionAt;
      return rec.decision.decision !== "BLOCK" && !!rec.userActionAt && rec.outcome !== "DENIED";
    })
    .sort((a, b) => new Date(b.request.timestamp).getTime() - new Date(a.request.timestamp).getTime());

  return (
    <div>
      <PageHeader title="Activity" description="Every payment request, decision and outcome on this device." />

      <div className="mb-4 flex gap-2">
        {FILTERS.map((f) => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={clsx(
              "rounded-full px-3.5 py-1.5 text-[12px] font-semibold tracking-wide",
              filter === f ? "bg-navy text-white" : "border border-border bg-white text-muted hover:text-foreground"
            )}
          >
            {f}
          </button>
        ))}
      </div>

      {records.length === 0 ? (
        <EmptyState title="No financial activity yet." body="Connect an agent to start delegating safely." />
      ) : (
        <ActivityTable records={records} />
      )}
    </div>
  );
}
