import type { Metadata } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";
import "./globals.css";
import { GuardProvider } from "@/lib/store";
import { ToastProvider } from "@/lib/toast";
import { Shell } from "@/components/shell";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });
const jetbrains = JetBrains_Mono({ subsets: ["latin"], variable: "--font-jetbrains" });

export const metadata: Metadata = {
  title: "AgentPay Guard",
  description: "Local-first consent and authorization layer for autonomous AI shopping agents."
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" data-font="metropolis">
      <body className={`${inter.variable} ${jetbrains.variable} font-sans`}>
        <GuardProvider>
          <ToastProvider>
            <Shell>{children}</Shell>
          </ToastProvider>
        </GuardProvider>
      </body>
    </html>
  );
}
