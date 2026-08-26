"use client";

import { usePathname } from "next/navigation";
import { Sidebar } from "@/components/sidebar";

export function Shell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  if (pathname === "/login") return <>{children}</>;
  return (
    <>
      <Sidebar />
      <main className="ml-64 min-h-screen px-8 py-8">{children}</main>
    </>
  );
}
