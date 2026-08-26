"use client";

import { usePathname } from "next/navigation";
import { Sidebar } from "@/components/sidebar";

export function Shell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  if (pathname === "/login") return <>{children}</>;
  return (
    <div className="relative min-h-screen bg-[url('/bg.jpg')] bg-cover bg-center bg-fixed bg-no-repeat text-slate-900">
      <Sidebar />
      <main className="ml-64 min-h-screen px-8 py-8 relative z-10">{children}</main>
    </div>
  );
}

