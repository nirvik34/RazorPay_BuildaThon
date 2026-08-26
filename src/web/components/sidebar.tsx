"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import clsx from "clsx";
import { useEffect, useRef, useState } from "react";
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

  const navRef = useRef<HTMLDivElement>(null);
  const itemRefs = useRef<{ [key: string]: HTMLAnchorElement | null }>({});

  const [sliderStyle, setSliderStyle] = useState<{ top: number; height: number; opacity: number }>({
    top: 0,
    height: 0,
    opacity: 0
  });

  useEffect(() => {
    const updateSlider = () => {
      let activeItem = NAV.find(
        (item) => pathname === item.href || (item.href !== "/" && pathname.startsWith(item.href))
      );

      let key = activeItem?.href;

      if (!key && pathname.startsWith("/settings")) {
        key = "/settings";
      }

      if (key && itemRefs.current[key] && navRef.current) {
        const el = itemRefs.current[key];
        const container = navRef.current;
        if (el) {
          const containerRect = container.getBoundingClientRect();
          const elRect = el.getBoundingClientRect();
          setSliderStyle({
            top: elRect.top - containerRect.top,
            height: elRect.height,
            opacity: 1
          });
        }
      } else {
        setSliderStyle((prev) => ({ ...prev, opacity: 0 }));
      }
    };

    updateSlider();
    const timer = setTimeout(updateSlider, 50);
    window.addEventListener("resize", updateSlider);

    return () => {
      clearTimeout(timer);
      window.removeEventListener("resize", updateSlider);
    };
  }, [pathname]);

  return (
    <aside className="fixed inset-y-0 left-0 z-40 flex w-60 flex-col border-r border-slate-200/80 bg-white text-slate-800 shadow-sm">
      {/* Brand Header */}
      <div className="flex items-center gap-3 px-5 py-5 border-b border-slate-100">
        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-blue-50 border border-blue-100 shadow-sm">
          <ShieldCheck className="h-6 w-6 text-brand" />
        </div>
        <div>
          <div className="text-[14px] font-black tracking-wider text-slate-900 flex items-center gap-1">
            AGENTPAY <span className="text-brand font-black">GUARD</span>
          </div>
          <div className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">
            AI Risk Engine
          </div>
        </div>
      </div>

      {/* Navigation Section with Moving Slider */}
      <div ref={navRef} className="relative flex-1 overflow-y-auto px-3 py-4">
        {/* Animated Moving Active Sidebox */}
        <div
          className="absolute left-3 right-3 rounded-lg bg-blue-50/80 border border-blue-200/60 shadow-sm transition-all duration-300 ease-out pointer-events-none"
          style={{
            top: `${sliderStyle.top}px`,
            height: `${sliderStyle.height}px`,
            opacity: sliderStyle.opacity
          }}
        />

        <nav className="space-y-1">
          {NAV.map((item) => {
            const active = pathname === item.href || (item.href !== "/" && pathname.startsWith(item.href));
            const Icon = item.icon;
            return (
              <Link
                key={item.href}
                href={item.href}
                ref={(el) => {
                  itemRefs.current[item.href] = el;
                }}
                className={clsx(
                  "group relative flex items-center gap-3 rounded-lg px-3 py-2.5 text-[13px] font-medium transition-colors duration-150",
                  active
                    ? "text-brand font-semibold"
                    : "text-slate-600 hover:text-slate-900 hover:bg-slate-50/60"
                )}
              >
                <Icon
                  className={clsx(
                    "h-4 w-4 transition-colors",
                    active ? "text-brand" : "text-slate-400 group-hover:text-slate-600"
                  )}
                />
                <span>{item.label}</span>
                {item.href === "/approvals" && pending.length > 0 && (
                  <span className="ml-auto rounded-full bg-warning px-2 py-0.5 font-mono text-[10px] font-bold text-white shadow-sm">
                    {pending.length}
                  </span>
                )}
              </Link>
            );
          })}
        </nav>
      </div>

      {/* Footer Section: Settings & Status */}
      <div className="border-t border-slate-100 p-3 space-y-1.5 bg-slate-50/50">
        <Link
          href="/settings"
          ref={(el) => {
            itemRefs.current["/settings"] = el;
          }}
          className={clsx(
            "group flex items-center gap-3 rounded-lg px-3 py-2.5 text-[13px] font-medium transition-colors duration-150",
            pathname.startsWith("/settings")
              ? "text-brand font-semibold"
              : "text-slate-600 hover:text-slate-900 hover:bg-slate-100/70"
          )}
        >
          <Settings
            className={clsx(
              "h-4 w-4 transition-colors",
              pathname.startsWith("/settings") ? "text-brand" : "text-slate-400 group-hover:text-slate-600"
            )}
          />
          <span>Settings</span>
        </Link>

        {/* System Status Pill */}
        <div className="flex items-center gap-2 rounded-lg px-3 py-2 text-[11px] font-medium text-slate-500 bg-white border border-slate-200/60 shadow-2xs">
          <span
            className={clsx(
              "h-2 w-2 rounded-full animate-pulse",
              !connected ? "bg-danger" : pending.length > 0 ? "bg-warning" : "bg-success"
            )}
          />
          {!connected ? "BACKEND OFFLINE" : pending.length > 0 ? "ACTION REQUIRED" : "LIVE · PROTECTED"}
        </div>

        {/* User Account Info */}
        {user && (
          <div className="flex items-center justify-between rounded-lg px-3 py-2 bg-white border border-slate-200/60 shadow-2xs">
            <div className="min-w-0 pr-2">
              <div className="truncate text-[12px] font-semibold text-slate-800">{user.name}</div>
              <div className="truncate font-mono text-[10px] text-slate-400">{user.email}</div>
            </div>
            <button
              onClick={logout}
              title="Sign out"
              className="rounded-md px-2 py-1 text-[11px] font-semibold text-slate-500 hover:bg-slate-100 hover:text-slate-900 transition-colors"
            >
              EXIT
            </button>
          </div>
        )}
      </div>
    </aside>
  );
}

