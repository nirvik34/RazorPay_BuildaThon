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
  Scale,
  ChevronDown,
  ChevronRight
} from "lucide-react";
import { useGuard } from "@/lib/store";

interface NavItem {
  href: string;
  label: string;
  icon: React.ElementType;
  badge?: string;
  isApproval?: boolean;
}

interface NavSection {
  title?: string;
  items: NavItem[];
}

const NAV_SECTIONS: NavSection[] = [
  {
    items: [
      { href: "/", label: "Home", icon: LayoutDashboard },
      { href: "/activity", label: "Transactions", icon: Activity },
      { href: "/approvals", label: "Approvals", icon: Bell, isApproval: true }
    ]
  },
  {
    title: "RISK & POLICIES",
    items: [
      { href: "/agents", label: "AI Agents", icon: Bot },
      { href: "/policies", label: "Guardrail Policies", icon: Scale },
      { href: "/risk", label: "Risk Engine", icon: ShieldAlert, badge: "Live" },
      { href: "/simulation", label: "Simulation", icon: FlaskConical },
      { href: "/audit", label: "Audit Log", icon: FileClock }
    ]
  }
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

  const [showMore, setShowMore] = useState(false);

  // Calculate sliding active box position
  useEffect(() => {
    const updateSlider = () => {
      let activeHref = "";
      
      const allItems = NAV_SECTIONS.flatMap((s) => s.items);
      const matched = allItems.find(
        (item) => pathname === item.href || (item.href !== "/" && pathname.startsWith(item.href))
      );

      if (matched) {
        activeHref = matched.href;
      } else if (pathname.startsWith("/settings")) {
        activeHref = "/settings";
      }

      if (activeHref && itemRefs.current[activeHref] && navRef.current) {
        const el = itemRefs.current[activeHref];
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
  }, [pathname, showMore]);

  return (
    <aside className="fixed inset-y-0 left-0 z-40 flex w-64 flex-col border-r border-slate-200/70 bg-[#F8F9FA] text-slate-800 shadow-xs">
      {/* Razorpay-style Brand Header */}
      <div className="flex items-center gap-3 px-4 py-4 border-b border-slate-200/60 bg-white">
        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-600 shadow-sm text-white font-bold shrink-0">
          <ShieldCheck className="h-6 w-6 text-white" />
        </div>
        <div>
          <div className="text-[15.5px] font-extrabold tracking-tight text-slate-900 flex items-center gap-1.5 leading-snug">
            AgentPay <span className="text-blue-600 font-black">Guard</span>
          </div>
          <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
            Razorpay Security Stack
          </div>
        </div>
      </div>

      {/* Navigation List with Dynamic Moving Sidebox Pill */}
      <div ref={navRef} className="relative flex-1 overflow-y-auto px-3 py-3 space-y-4">
        {/* Animated Active Pill (Light grey/slate box matching Razorpay design) */}
        <div
          className="absolute left-3 right-3 rounded-lg bg-[#EAECEF] border border-slate-300/40 shadow-2xs transition-all duration-200 ease-out pointer-events-none"
          style={{
            top: `${sliderStyle.top}px`,
            height: `${sliderStyle.height}px`,
            opacity: sliderStyle.opacity
          }}
        />

        {NAV_SECTIONS.map((section, idx) => (
          <div key={idx} className="space-y-1">
            {section.title && (
              <div className="px-3 pt-2.5 pb-1 text-[12px] font-bold text-slate-400 uppercase tracking-wider">
                {section.title}
              </div>
            )}
            <nav className="space-y-0.5">
              {section.items.map((item) => {
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
                      "group relative flex items-center gap-3 rounded-lg px-3 py-2.5 text-[14.5px] transition-all duration-150",
                      active
                        ? "font-bold text-slate-900"
                        : "font-medium text-slate-600 hover:text-slate-900 hover:bg-slate-200/50"
                    )}
                  >
                    <Icon
                      className={clsx(
                        "h-[18px] w-[18px] transition-colors shrink-0",
                        active ? "text-blue-600 stroke-[2.5]" : "text-slate-500 group-hover:text-slate-700"
                      )}
                    />
                    <span className="truncate">{item.label}</span>

                    {/* Pending Approvals Badge */}
                    {item.isApproval && pending.length > 0 && (
                      <span className="ml-auto rounded-full bg-amber-500 px-2 py-0.5 font-mono text-[11px] font-bold text-white shadow-2xs">
                        {pending.length}
                      </span>
                    )}

                    {/* Badge (e.g. Live / New Update) */}
                    {item.badge && (!item.isApproval || pending.length === 0) && (
                      <span className="ml-auto rounded-full bg-emerald-100 text-emerald-800 text-[11px] font-semibold px-2 py-0.5">
                        {item.badge}
                      </span>
                    )}
                  </Link>
                );
              })}
            </nav>
          </div>
        ))}

        {/* Collapsible "+ More" section matching Razorpay dashboard */}
        <div className="pt-1">
          <button
            onClick={() => setShowMore(!showMore)}
            className="w-full flex items-center gap-2 px-3 py-2 text-[13.5px] font-semibold text-slate-600 hover:text-slate-900 hover:bg-slate-200/50 rounded-lg transition-colors"
          >
            {showMore ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
            <span>{showMore ? "Show Less" : "+ Quick Controls"}</span>
          </button>

          {showMore && (
            <div className="mt-1 ml-3 pl-3 border-l border-slate-200 space-y-1">
              <Link
                href="/settings"
                className="flex items-center gap-2 px-2 py-1.5 text-[13px] font-medium text-slate-600 hover:text-slate-900 hover:bg-slate-200/40 rounded-md"
              >
                <span>Demo Triggers</span>
              </Link>
              <Link
                href="/simulation"
                className="flex items-center gap-2 px-2 py-1.5 text-[13px] font-medium text-slate-600 hover:text-slate-900 hover:bg-slate-200/40 rounded-md"
              >
                <span>Stress Test</span>
              </Link>
            </div>
          )}
        </div>
      </div>

      {/* Footer Section: Font Selector & System Controls */}
      <div className="border-t border-slate-200/70 p-3 space-y-2 bg-white">
        {/* Settings Navigation */}
        <Link
          href="/settings"
          ref={(el) => {
            itemRefs.current["/settings"] = el;
          }}
          className={clsx(
            "group flex items-center gap-3 rounded-lg px-3 py-2 text-[14px] transition-colors duration-150",
            pathname.startsWith("/settings")
              ? "font-bold text-slate-900 bg-[#EAECEF]"
              : "font-medium text-slate-600 hover:text-slate-900 hover:bg-slate-100"
          )}
        >
          <Settings
            className={clsx(
              "h-[18px] w-[18px] transition-colors shrink-0",
              pathname.startsWith("/settings") ? "text-blue-600" : "text-slate-500 group-hover:text-slate-700"
            )}
          />
          <span>Settings & Config</span>
        </Link>

        {/* Live Protection Status */}
        <div className="flex items-center gap-2 rounded-lg px-3 py-2 text-[12px] font-semibold text-slate-600 bg-slate-50 border border-slate-200/60">
          <span
            className={clsx(
              "h-2 w-2 rounded-full animate-pulse shrink-0",
              !connected ? "bg-red-500" : pending.length > 0 ? "bg-amber-500" : "bg-emerald-500"
            )}
          />
          <span className="truncate">
            {!connected ? "Backend Offline" : pending.length > 0 ? "Action Required" : "Live · Protected"}
          </span>
        </div>

        {/* User Badge */}
        {user && (
          <div className="flex items-center justify-between rounded-lg px-3 py-2 bg-slate-50 border border-slate-200/60">
            <div className="min-w-0 pr-2">
              <div className="truncate text-[12.5px] font-bold text-slate-800">{user.name}</div>
              <div className="truncate font-mono text-[11px] text-slate-400">{user.email}</div>
            </div>
            <button
              onClick={logout}
              className="rounded-md px-2 py-0.5 text-[11px] font-bold text-slate-500 hover:bg-slate-200 hover:text-slate-900 transition-colors"
            >
              EXIT
            </button>
          </div>
        )}
      </div>
    </aside>
  );
}
