"use client";

import clsx from "clsx";
import { BarChart3, ListFilter } from "lucide-react";

export type ViewMode = "graph" | "logs";

interface ViewToggleProps {
  mode: ViewMode;
  onChange: (mode: ViewMode) => void;
  className?: string;
}

export function ViewToggle({ mode, onChange, className }: ViewToggleProps) {
  const isGraph = mode === "graph";

  return (
    <div className={clsx("flex items-center gap-3", className)}>
      {/* Label indicator for clarity */}
      <span className="text-[12px] font-semibold text-slate-500 uppercase tracking-wider hidden sm:inline-block">
        Mode: <span className="text-slate-900 font-bold">{isGraph ? "Graph Dashboard" : "Logs Table"}</span>
      </span>

      {/* Pill Toggle Switch styled to match the user screenshot */}
      <div className="relative inline-flex items-center rounded-full bg-slate-100 p-1 border border-slate-200 shadow-inner">
        {/* Animated Sliding Background Knob */}
        <button
          type="button"
          onClick={() => onChange(isGraph ? "logs" : "graph")}
          aria-label={isGraph ? "Switch to Logs View" : "Switch to Graph Dashboard"}
          className={clsx(
            "relative flex h-8 w-[88px] items-center rounded-full transition-all duration-300 ease-in-out focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500",
            isGraph ? "bg-blue-600" : "bg-slate-700"
          )}
        >
          {/* Inner Knob white circle with micro-dots matching user graphic */}
          <div
            className={clsx(
              "absolute top-1 flex h-6 w-6 items-center justify-center rounded-full bg-white shadow-md transition-transform duration-300 ease-in-out",
              isGraph ? "translate-x-1 text-blue-600" : "translate-x-[58px] text-slate-700"
            )}
          >
            {isGraph ? (
              <BarChart3 className="h-3.5 w-3.5 stroke-[2.5]" />
            ) : (
              <ListFilter className="h-3.5 w-3.5 stroke-[2.5]" />
            )}
          </div>

          {/* Icon indicators on left & right inside the track */}
          <div className="flex w-full items-center justify-between px-2.5 text-white/90">
            <span
              className={clsx(
                "text-[10px] font-bold tracking-wider transition-opacity duration-200 ml-6",
                isGraph ? "opacity-100" : "opacity-40"
              )}
            >
              GRAPH
            </span>
            <span
              className={clsx(
                "text-[10px] font-bold tracking-wider transition-opacity duration-200 mr-6",
                !isGraph ? "opacity-100" : "opacity-40"
              )}
            >
              LOGS
            </span>
          </div>
        </button>
      </div>
    </div>
  );
}
