"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import { ShoppingBag, Activity, ShieldCheck, Zap, Menu, X } from "lucide-react";

export default function Navbar({ wsConnected }: { wsConnected?: boolean }) {
  const pathname = usePathname();
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <header className="sticky top-0 z-50 glass-panel border-b border-white/10 px-4 sm:px-6 py-3 sm:py-4">
      <div className="max-w-7xl mx-auto flex items-center justify-between">
        {/* Brand */}
        <Link href="/" className="flex items-center gap-2 sm:gap-3 group shrink-0">
          <div className="w-8 h-8 sm:w-10 sm:h-10 rounded-xl bg-gradient-to-tr from-cyan-500 to-blue-600 flex items-center justify-center shadow-lg shadow-blue-500/20 group-hover:scale-105 transition-transform">
            <Zap className="w-4 h-4 sm:w-5 sm:h-5 text-white" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-bold text-sm sm:text-lg tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-white via-slate-100 to-slate-400">
                Commerce Mesh
              </span>
              <span className="hidden sm:inline text-[10px] uppercase font-mono px-2 py-0.5 rounded-full bg-blue-500/20 text-blue-400 border border-blue-500/30">
                Razorpay Test
              </span>
            </div>
            <p className="text-[10px] sm:text-xs text-slate-400 hidden sm:block">Dual-Agent Autonomous Protocol</p>
          </div>
        </Link>

        {/* Desktop Navigation Tabs */}
        <nav className="hidden md:flex items-center gap-2 bg-slate-900/60 p-1.5 rounded-xl border border-white/5">
          <Link
            href="/"
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${
              pathname === "/"
                ? "bg-gradient-to-r from-blue-600 to-cyan-600 text-white shadow-md shadow-blue-500/20"
                : "text-slate-400 hover:text-white hover:bg-slate-800/50"
            }`}
          >
            <ShoppingBag className="w-4 h-4" />
            Buyer Store
          </Link>
          <Link
            href="/dashboard"
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${
              pathname === "/dashboard"
                ? "bg-gradient-to-r from-blue-600 to-cyan-600 text-white shadow-md shadow-blue-500/20"
                : "text-slate-400 hover:text-white hover:bg-slate-800/50"
            }`}
          >
            <Activity className="w-4 h-4" />
            Command Center
          </Link>
        </nav>

        {/* Right side: Live Indicator + Mobile Toggle */}
        <div className="flex items-center gap-2 sm:gap-3">
          {/* Live Indicator */}
          <div className="flex items-center gap-1.5 sm:gap-2 px-2 sm:px-3 py-1 sm:py-1.5 rounded-full bg-slate-900/80 border border-white/10 text-[10px] sm:text-xs">
            <span
              className={`w-2 h-2 sm:w-2.5 sm:h-2.5 rounded-full ${
                wsConnected ?? true
                  ? "bg-emerald-500 shadow-[0_0_8px_#10b981]"
                  : "bg-amber-500"
              }`}
            />
            <span className="font-mono text-slate-300 hidden sm:inline">
              {wsConnected ?? true ? "MESH LIVE (WS)" : "CONNECTING..."}
            </span>
            <span className="font-mono text-slate-300 sm:hidden">
              {wsConnected ?? true ? "LIVE" : "..."}
            </span>
          </div>

          {/* Mobile Hamburger */}
          <button
            onClick={() => setMobileOpen(!mobileOpen)}
            className="md:hidden p-2 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800/50 transition-colors cursor-pointer"
          >
            {mobileOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </button>
        </div>
      </div>

      {/* Mobile Navigation Drawer */}
      {mobileOpen && (
        <div className="md:hidden mt-3 pt-3 border-t border-white/10 space-y-2">
          <Link
            href="/"
            onClick={() => setMobileOpen(false)}
            className={`flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium transition-all ${
              pathname === "/"
                ? "bg-gradient-to-r from-blue-600 to-cyan-600 text-white shadow-md shadow-blue-500/20"
                : "text-slate-400 hover:text-white hover:bg-slate-800/50"
            }`}
          >
            <ShoppingBag className="w-4 h-4" />
            Buyer Store
          </Link>
          <Link
            href="/dashboard"
            onClick={() => setMobileOpen(false)}
            className={`flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium transition-all ${
              pathname === "/dashboard"
                ? "bg-gradient-to-r from-blue-600 to-cyan-600 text-white shadow-md shadow-blue-500/20"
                : "text-slate-400 hover:text-white hover:bg-slate-800/50"
            }`}
          >
            <Activity className="w-4 h-4" />
            Command Center
          </Link>
        </div>
      )}
    </header>
  );
}
