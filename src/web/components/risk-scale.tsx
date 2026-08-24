"use client";

import clsx from "clsx";
import type { RiskLevel } from "@/lib/types";

const SEGMENTS: Array<{ label: RiskLevel; color: string }> = [
  { label: "LOW", color: "#12B76A" },
  { label: "MEDIUM", color: "#F79009" },
  { label: "HIGH", color: "#F04438" },
  { label: "CRITICAL", color: "#B42318" }
];

function bucket(score: number): number {
  if (score < 25) return 0;
  if (score < 50) return 1;
  if (score < 75) return 2;
  return 3;
}

export function RiskScale({ score, compact }: { score: number; compact?: boolean }) {
  const active = bucket(score);
  return (
    <div className={clsx("w-full", compact ? "max-w-[180px]" : "")}>
      <div className="flex gap-1">
        {SEGMENTS.map((seg, i) => (
          <div
            key={seg.label}
            className="h-1.5 flex-1 rounded-full"
            style={{ backgroundColor: i <= active ? seg.color : "#E4E7EC" }}
          />
        ))}
      </div>
      <div className="mt-1.5 flex justify-between text-[10px] font-medium uppercase tracking-wide text-muted">
        {SEGMENTS.map((seg, i) => (
          <span key={seg.label} className={clsx(i === active && "font-bold", i === active ? "" : "opacity-60")}>
            {seg.label}
          </span>
        ))}
      </div>
      {!compact && <div className="mt-1 font-mono text-xs text-muted">{score}/100</div>}
    </div>
  );
}
