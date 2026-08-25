"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import clsx from "clsx";
import {
  Activity,
  Bell,
  FileClock,
  FlaskConical,
  LayoutDashboard,
  Settings,
  ShieldCheck,
  ShieldAlert,
  Bot,
  Scale
} from "lucide-react";
import { useGuard } from "@/lib/store";

const NAV = [
  { href: "/", label: "Overview", icon: LayoutDashboard },
  { href: "/approvals", label: "Approvals", icon: Bell },
  { href: "/activity", label: "Activity", icon: Activity },
  { href: "/agents", label: "Agents", icon: Bot },
  { href: "/policies", label: "Policies", icon: Scale },
  { href: "/risk", label: "Risk", icon: ShieldAlert },
  { href: "/simulation", label: "Simulation", icon: FlaskConical },
  { href: "/audit", label: "Audit", icon: FileClock }
];

export function Sidebar() {
  const pathname = usePathname();
  const { pending, connected, user, logout } = useGuard();

  return (
    <aside className="fixed inset-y-0 left-0 z-40 flex w-60 flex-col bg-navy text-white">
      <div className="flex items-center gap-2.5 px-5 py-5">
        <div className="flex h-9 w-9 items-center justify-center rounded-md bg-brand/20">
          <ShieldCheck className="h-5 w-5 text-[#0D94FB]" />
        </div>
        <div>
          <div className="text-[13px] font-bold leading-tight tracking-wide">AGENTPAY</div>
          <div className="text-[13px] font-bold leading-tight tracking-wide text-[#98A2B3]">GUARD</div>
        </div>
      </div>

      <nav className="mt-2 flex-1 space-y-0.5 overflow-y-auto px-3">
        {NAV.map((item) => {
          const active = pathname === item.href || (item.href !== "/" && pathname.startsWith(item.href));
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={clsx(
                "group relative flex items-center gap-3 rounded-sm px-3 py-2 text-[13px] font-medium",
                active ? "bg-[rgba(13,148,251,0.16)] text-white" : "text-[#98A2B3] hover:bg-white/5 hover:text-white"
              )}
            >
              {active && <span className="absolute left-0 top-1 bottom-1 w-[3px] rounded-full bg-[#0D94FB]" />}
              <Icon className="h-4 w-4" />
              <span>{item.label}</span>
              {item.href === "/approvals" && pending.length > 0 && (
                <span className="ml-auto rounded-full bg-warning px-1.5 py-px font-mono text-[10px] font-bold text-white">
                  {pending.length}
                </span>
              )}
            </Link>
          );
        })}
      </nav>

      <div className="space-y-0.5 border-t border-white/10 px-3 py-3">
        <Link
          href="/settings"
          className={clsx(
            "flex items-center gap-3 rounded-sm px-3 py-2 text-[13px] font-medium",
            pathname.startsWith("/settings") ? "bg-[rgba(13,148,251,0.16)] text-white" : "text-[#98A2B3] hover:bg-white/5 hover:text-white"
          )}
        >
          <Settings className="h-4 w-4" />
          Settings
        </Link>
        <div className="flex items-center gap-2 rounded-sm px-3 py-2 text-[12px] font-medium text-[#98A2B3]">
          <span className={clsx("h-2 w-2 rounded-full", !connected ? "bg-danger" : pending.length > 0 ? "bg-warning" : "bg-success")} />
          {!connected ? "BACKEND OFFLINE" : pending.length > 0 ? "ACTION REQUIRED" : "LIVE · PROTECTED"}
        </div>
        {user && (
          <div className="flex items-center justify-between rounded-sm px-3 py-2">
            <div className="min-w-0">
              <div className="truncate text-[12px] font-medium text-white">{user.name}</div>
              <div className="truncate font-mono text-[10px] text-[#98A2B3]">{user.email}</div>
            </div>
            <button
              onClick={logout}
              title="Sign out"
              className="rounded-sm px-2 py-1 text-[11px] font-semibold text-[#98A2B3] hover:bg-white/5 hover:text-white"
            >
              EXIT
            </button>
          </div>
        )}
      </div>
    </aside>
  );
}
