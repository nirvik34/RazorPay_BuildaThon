import type { Metadata } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";
import "./globals.css";
import { GuardProvider } from "@/lib/store";
import { ToastProvider } from "@/lib/toast";
import { Sidebar } from "@/components/sidebar";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });
const jetbrains = JetBrains_Mono({ subsets: ["latin"], variable: "--font-jetbrains" });

export const metadata: Metadata = {
  title: "AgentPay Guard",
  description: "Local-first consent and authorization layer for autonomous AI shopping agents."
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className={`${inter.variable} ${jetbrains.variable} font-sans`}>
        <GuardProvider>
          <ToastProvider>
            <Sidebar />
            <main className="ml-60 min-h-screen px-8 py-8">{children}</main>
          </ToastProvider>
        </GuardProvider>
      </body>
    </html>
  );
}
