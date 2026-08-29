import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Dual-Agent Commerce Mesh | Razorpay Test Mode",
  description: "AI Buyer and Merchant autonomous commerce mesh with deterministic financial guardrails and real-time state machine.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark h-full antialiased">
      <body className="min-h-full flex flex-col bg-[#090d16] text-[#f8fafc]">
        {children}
      </body>
    </html>
  );
}
