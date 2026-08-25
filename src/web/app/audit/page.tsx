"use client";

import { useMemo } from "react";
import { useGuard } from "@/lib/store";
import { PageHeader, EmptyState } from "@/components/stat-card";
import { ActivityTable } from "@/components/activity-table";
import { relativeDay } from "@/lib/format";

export default function AuditPage() {
  const { transactions } = useGuard();

  const groups = useMemo(() => {
    const sorted = [...transactions].sort(
      (a, b) => new Date(b.request.timestamp).getTime() - new Date(a.request.timestamp).getTime()
    );
    const map = new Map<string, typeof sorted>();
    for (const rec of sorted) {
      const key = relativeDay(rec.request.timestamp);
      const list = map.get(key) ?? [];
      list.push(rec);
      map.set(key, list);
    }
    return Array.from(map.entries());
  }, [transactions]);

  return (
    <div>
      <PageHeader
        title="Audit"
        description="Financial flight recorder. Every decision chain is recorded locally and replayable."
      />
      {groups.length === 0 ? (
        <EmptyState title="No audit records yet." body="Decisions will appear here as agents act." />
      ) : (
        <div className="space-y-8">
          {groups.map(([day, records]) => (
            <section key={day}>
              <h2 className="mb-3 font-mono text-[11px] font-bold uppercase tracking-widest text-muted">{day}</h2>
              <ActivityTable records={records} />
            </section>
          ))}
        </div>
      )}
    </div>
  );
}
