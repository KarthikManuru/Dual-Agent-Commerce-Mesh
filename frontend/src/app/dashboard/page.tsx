"use client";

import { useEffect, useState, useRef } from "react";
import { API_URL, WS_URL } from "@/lib/config";
import Navbar from "@/components/Navbar";
import {
  Activity,
  ShieldAlert,
  CheckCircle2,
  Clock,
  ArrowRight,
  RefreshCw,
  Zap,
  CreditCard,
  FileText,
  AlertTriangle,
  Bot,
  Scale,
  Sparkles,
  Gift,
  Play,
  Loader2,
  ShieldCheck,
  Save,
} from "lucide-react";

interface OrderEvent {
  id: string;
  actor: string;
  action: string;
  from_status: string | null;
  to_status: string | null;
  detail: any;
  result: string;
  created_at: string;
}

interface Order {
  id: string;
  merchant_id: string;
  product_id: string;
  quantity: number;
  status: string;
  unit_price_paise: number;
  total_paise: number;
  currency: string;
  razorpay_order_id: string | null;
  razorpay_payment_id: string | null;
  events: OrderEvent[];
  created_at: string;
  updated_at: string;
}

interface LiveNegotiationMsg {
  sender: string;
  intent: string;
  offered_price_paise: number;
  discount_pct: number;
  reasoning_text: string;
  reason_codes: string[];
  bundle_suggestion?: any;
  reasoning_source: string;
  model_name: string;
  round: number;
  timestamp: string;
}

const STATUS_GROUPS: { [key: string]: { label: string; color: string; states: string[] } } = {
  created: {
    label: "Order Created & Discovery",
    color: "border-blue-500/30 bg-blue-500/5 text-blue-400",
    states: ["DISCOVERED", "SELECTED", "OFFER_CREATED", "NEGOTIATING", "OFFER_ACCEPTED", "CONSENT_REQUIRED", "CONSENT_RECEIVED", "ORDER_CREATED"],
  },
  payment: {
    label: "Payment & Razorpay",
    color: "border-amber-500/30 bg-amber-500/5 text-amber-400",
    states: ["PAYMENT_PENDING", "PAYMENT_AUTHORIZED", "PAYMENT_CAPTURED"],
  },
  paid: {
    label: "Paid & Fulfilled",
    color: "border-emerald-500/30 bg-emerald-500/5 text-emerald-400",
    states: ["ORDER_PAID", "FULFILLED"],
  },
  failed: {
    label: "Failed / Cancelled",
    color: "border-rose-500/30 bg-rose-500/5 text-rose-400",
    states: ["PAYMENT_FAILED", "CANCELLED"],
  },
};

export default function DashboardPage() {
  const [orders, setOrders] = useState<Order[]>([]);
  const [selectedOrder, setSelectedOrder] = useState<Order | null>(null);
  const [wsConnected, setWsConnected] = useState(false);
  const [liveLog, setLiveLog] = useState<{ id: string; time: string; text: string; type: string }[]>([]);
  
  // Negotiation Theater State
  const [theaterMessages, setTheaterMessages] = useState<LiveNegotiationMsg[]>([]);
  const [isSimulatingAgent, setIsSimulatingAgent] = useState(false);
  const [activeSessionOutcome, setActiveSessionOutcome] = useState<string | null>(null);
  
  const wsRef = useRef<WebSocket | null>(null);

  const [policy, setPolicy] = useState<{
    max_discount_pct: number;
    min_margin_pct: number;
    max_negotiation_rounds: number;
    offer_ttl_seconds: number;
  }>({
    max_discount_pct: 15,
    min_margin_pct: 10,
    max_negotiation_rounds: 2,
    offer_ttl_seconds: 600,
  });
  const [isSavingPolicy, setIsSavingPolicy] = useState(false);
  const [policySavedMsg, setPolicySavedMsg] = useState("");

  const fetchPolicy = async () => {
    try {
      const res = await fetch(`${API_URL}/policies/a1b2c3d4-e5f6-7890-abcd-ef1234567890`);
      if (res.ok) {
        const data = await res.json();
        setPolicy({
          max_discount_pct: Number(data.max_discount_pct),
          min_margin_pct: Number(data.min_margin_pct),
          max_negotiation_rounds: data.max_negotiation_rounds,
          offer_ttl_seconds: data.offer_ttl_seconds,
        });
      }
    } catch (e) {
      console.error("Fetch policy error:", e);
    }
  };

  const handleSavePolicy = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSavingPolicy(true);
    setPolicySavedMsg("");
    try {
      const res = await fetch(`${API_URL}/policies/a1b2c3d4-e5f6-7890-abcd-ef1234567890`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(policy),
      });
      if (res.ok) {
        setPolicySavedMsg("Policy bounds updated & enforced live!");
        setTimeout(() => setPolicySavedMsg(""), 4000);
      } else {
        const err = await res.json();
        alert(`Update failed: ${err.detail}`);
      }
    } catch (e: any) {
      alert(`Error updating policy: ${e.message}`);
    } finally {
      setIsSavingPolicy(false);
    }
  };

  useEffect(() => {
    fetchOrders();
    fetchPolicy();
    connectWebSocket();

    return () => {
      if (wsRef.current) wsRef.current.close();
    };
  }, []);

  const fetchOrders = async () => {
    try {
      const res = await fetch(`${API_URL}/orders`);
      if (res.ok) {
        const data = await res.json();
        setOrders(data.orders || []);
      }
    } catch (e) {
      console.error("Failed to load orders:", e);
    }
  };

  const connectWebSocket = () => {
    try {
      const ws = new WebSocket(WS_URL);
      wsRef.current = ws;

      ws.onopen = () => {
        setWsConnected(true);
        addLog("WebSocket connected to live Dual-Agent order stream", "info");
      };

      ws.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data);
          
          if (payload.type === "ORDER_CREATED" || payload.type === "ORDER_UPDATED") {
            addLog(`[MESH] Order ${payload.order_id.slice(0, 8)}... status: ${payload.status}`, "update");
            fetchOrders();
          } else if (payload.type === "NEGOTIATION_MESSAGE") {
            const m = payload.message;
            setTheaterMessages((prev) => [...prev.slice(-8), m]);
            addLog(`[AGENT LIVE] ${m.sender} -> ${m.intent} (₹${(m.offered_price_paise / 100).toFixed(2)})`, "update");
          } else if (payload.type === "NEGOTIATION_COMPLETE") {
            setActiveSessionOutcome(payload.outcome);
            addLog(`[DEAL] Negotiation ${payload.session_id.slice(0, 8)} closed: ${payload.outcome} at ₹${((payload.agreed_price_paise || 0)/100).toFixed(2)}`, "info");
            fetchOrders();
          }
        } catch (e) {
          console.error("WS Parse error:", e);
        }
      };

      ws.onclose = () => {
        setWsConnected(false);
        addLog("WebSocket disconnected. Reconnecting in 3s...", "warning");
        setTimeout(connectWebSocket, 3000);
      };
    } catch (e) {
      console.error("WS Connection error:", e);
    }
  };

  const addLog = (text: string, type: "info" | "update" | "warning") => {
    setLiveLog((prev) => [
      {
        id: Math.random().toString(),
        time: new Date().toLocaleTimeString(),
        text,
        type,
      },
      ...prev.slice(0, 25),
    ]);
  };

  // Demo Trigger: Simulate Live AI Agent Negotiation Session
  const handleTriggerSimulatedNegotiation = async () => {
    try {
      setIsSimulatingAgent(true);
      setTheaterMessages([]);
      setActiveSessionOutcome(null);

      const res = await fetch(`${API_URL}/sessions/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          query: "Find me ANC headphones under ₹3,000 for office calls",
          buyer_strategy: "BARGAIN_HUNTER",
        }),
      });

      if (!res.ok) {
        const err = await res.json();
        alert(`Session trigger error: ${err.detail}`);
      }
    } catch (e: any) {
      alert(`Error: ${e.message}`);
    } finally {
      setIsSimulatingAgent(false);
    }
  };

  // Stats calculation
  const totalOrders = orders.length;
  const totalVolumePaise = orders.reduce((sum, o) => sum + o.total_paise, 0);
  const fulfilledOrders = orders.filter((o) => o.status === "FULFILLED" || o.status === "ORDER_PAID").length;
  const pendingOrders = orders.filter((o) => o.status.includes("PAYMENT_") || o.status === "ORDER_CREATED").length;

  return (
    <div className="min-h-screen flex flex-col bg-[#090d16]">
      <Navbar wsConnected={wsConnected} />

      <main className="flex-1 max-w-7xl w-full mx-auto px-3 sm:px-6 py-4 sm:py-8 space-y-4 sm:space-y-8">
        {/* Header Title & Controls */}
        <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
          <div>
            <h1 className="text-xl sm:text-2xl md:text-3xl font-extrabold text-white flex flex-wrap items-center gap-2 sm:gap-3">
              Merchant Command Center & AI Theater
              <span className="text-xs font-mono font-normal px-2.5 py-1 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-ping" />
                Live Mesh
              </span>
            </h1>
            <p className="text-xs md:text-sm text-slate-400">
              Autonomous Dual-Agent Negotiation Engine, Deterministic Financial Guards & Cryptographic Audit Trails
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2 sm:gap-3">
            <button
              onClick={handleTriggerSimulatedNegotiation}
              disabled={isSimulatingAgent}
              className="px-4 py-2 rounded-xl bg-gradient-to-r from-blue-600 via-cyan-500 to-teal-400 text-white hover:opacity-90 text-xs font-mono font-semibold flex items-center gap-2 shadow-md shadow-cyan-500/20 cursor-pointer disabled:opacity-50"
            >
              {isSimulatingAgent ? (
                <>
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  Running AI Agents...
                </>
              ) : (
                <>
                  <Play className="w-3.5 h-3.5" />
                  Run Live AI Negotiation
                </>
              )}
            </button>

            <button
              onClick={fetchOrders}
              className="px-4 py-2 rounded-xl bg-slate-900 border border-white/10 text-slate-300 hover:text-white text-xs font-mono flex items-center gap-2 transition-colors cursor-pointer"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              Refresh
            </button>
          </div>
        </div>

        {/* Metrics Grid */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-2 sm:gap-4">
          <div className="glass-panel p-3 sm:p-5 rounded-xl sm:rounded-2xl border border-white/5 space-y-1">
            <span className="text-xs font-mono uppercase text-slate-400">Total Mesh Orders</span>
            <div className="text-lg sm:text-2xl font-extrabold text-white">{totalOrders}</div>
          </div>
          <div className="glass-panel p-3 sm:p-5 rounded-xl sm:rounded-2xl border border-white/5 space-y-1">
            <span className="text-xs font-mono uppercase text-slate-400">Settled Volume</span>
            <div className="text-lg sm:text-2xl font-extrabold text-cyan-400 font-mono truncate">
              ₹{(totalVolumePaise / 100).toLocaleString("en-IN", { minimumFractionDigits: 2 })}
            </div>
          </div>
          <div className="glass-panel p-3 sm:p-5 rounded-xl sm:rounded-2xl border border-white/5 space-y-1">
            <span className="text-xs font-mono uppercase text-slate-400">Fulfilled / Paid</span>
            <div className="text-lg sm:text-2xl font-extrabold text-emerald-400">{fulfilledOrders}</div>
          </div>
          <div className="glass-panel p-3 sm:p-5 rounded-xl sm:rounded-2xl border border-white/5 space-y-1">
            <span className="text-xs font-mono uppercase text-slate-400">In-Flight / Pending</span>
            <div className="text-lg sm:text-2xl font-extrabold text-amber-400">{pendingOrders}</div>
          </div>
        </div>

        {/* On-the-Fly Policy Management & Financial Guard Card */}
        <div className="p-4 sm:p-6 rounded-2xl sm:rounded-3xl glass-panel border border-purple-500/20 bg-purple-950/10 space-y-3 sm:space-y-4">
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2 border-b border-white/10 pb-3">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-lg bg-purple-600/30 border border-purple-500/40 flex items-center justify-center text-purple-400">
                <ShieldCheck className="w-4 h-4" />
              </div>
              <div>
                <h3 className="text-sm font-bold text-white flex items-center gap-2">
                  Merchant Guard Policy Controls
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-purple-500/20 text-purple-300 border border-purple-500/30">
                    Live Enforced
                  </span>
                </h3>
                <p className="text-xs text-slate-400">
                  Dynamically adjust concession bounds, margin floors, and round limits without redeploying.
                </p>
              </div>
            </div>
            {policySavedMsg && (
              <span className="text-xs font-mono px-2.5 py-1 rounded-lg bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 animate-pulse">
                ✓ {policySavedMsg}
              </span>
            )}
          </div>

          <form onSubmit={handleSavePolicy} className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-2 sm:gap-3 items-end">
            <div className="space-y-1">
              <label className="text-[11px] font-mono text-slate-400">Max Discount (%)</label>
              <input
                type="number"
                min="0"
                max="50"
                step="0.5"
                value={policy.max_discount_pct}
                onChange={(e) => setPolicy({ ...policy, max_discount_pct: parseFloat(e.target.value) || 0 })}
                className="w-full bg-slate-900/80 border border-white/10 rounded-xl px-3 py-2 text-xs font-mono text-white focus:outline-none focus:border-purple-500"
              />
            </div>
            <div className="space-y-1">
              <label className="text-[11px] font-mono text-slate-400">Min Margin Floor (%)</label>
              <input
                type="number"
                min="0"
                max="100"
                step="0.5"
                value={policy.min_margin_pct}
                onChange={(e) => setPolicy({ ...policy, min_margin_pct: parseFloat(e.target.value) || 0 })}
                className="w-full bg-slate-900/80 border border-white/10 rounded-xl px-3 py-2 text-xs font-mono text-white focus:outline-none focus:border-purple-500"
              />
            </div>
            <div className="space-y-1">
              <label className="text-[11px] font-mono text-slate-400">Max Rounds (Cap)</label>
              <input
                type="number"
                min="1"
                max="10"
                value={policy.max_negotiation_rounds}
                onChange={(e) => setPolicy({ ...policy, max_negotiation_rounds: parseInt(e.target.value) || 1 })}
                className="w-full bg-slate-900/80 border border-white/10 rounded-xl px-3 py-2 text-xs font-mono text-white focus:outline-none focus:border-purple-500"
              />
            </div>
            <div className="space-y-1">
              <label className="text-[11px] font-mono text-slate-400">Offer TTL (Seconds)</label>
              <input
                type="number"
                min="10"
                max="86400"
                value={policy.offer_ttl_seconds}
                onChange={(e) => setPolicy({ ...policy, offer_ttl_seconds: parseInt(e.target.value) || 600 })}
                className="w-full bg-slate-900/80 border border-white/10 rounded-xl px-3 py-2 text-xs font-mono text-white focus:outline-none focus:border-purple-500"
              />
            </div>
            <div>
              <button
                type="submit"
                disabled={isSavingPolicy}
                className="w-full py-2 px-3 rounded-xl bg-purple-600 hover:bg-purple-500 text-white font-mono text-xs font-semibold flex items-center justify-center gap-1.5 transition-colors cursor-pointer disabled:opacity-50 col-span-2 sm:col-span-1"
              >
                {isSavingPolicy ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Save className="w-3.5 h-3.5" />}
                Save Policy
              </button>
            </div>
          </form>
        </div>

        {/* Dual-Agent Live Negotiation Theater Panel */}
        <div className="p-4 sm:p-6 rounded-2xl sm:rounded-3xl glass-panel border border-cyan-500/20 space-y-4 sm:space-y-5 relative overflow-hidden">
          <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-3 border-b border-white/10 pb-4">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-cyan-500 to-blue-600 flex items-center justify-center shadow-lg shadow-cyan-500/20">
                <Bot className="w-5 h-5 text-white" />
              </div>
              <div>
                <h2 className="text-lg font-bold text-white flex items-center gap-2">
                  Dual-Agent Real-Time Negotiation Theater
                  <span className="text-[10px] font-mono font-normal px-2 py-0.5 rounded-full bg-cyan-500/20 text-cyan-400 border border-cyan-500/30">
                    Live Telemetry
                  </span>
                </h2>
                <p className="text-[10px] sm:text-xs text-slate-400 hidden sm:block">
                  Buyer LLM (Persuasive Demand) ◄──► Merchant LLM (Commercial Defense) ◄──► FinancialActionGuard (Rule Verification)
                </p>
              </div>
            </div>

            <div className="flex items-center gap-2 text-xs font-mono">
              <span className="px-2.5 py-1 rounded-lg bg-slate-900 border border-white/10 text-slate-300 flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-emerald-400" />
                Guard: Active (15% Max Disc / 10% Min Margin)
              </span>
            </div>
          </div>

          {/* Theater Dialogue Screen */}
          <div className="min-h-[180px] sm:min-h-[220px] max-h-[280px] sm:max-h-[320px] overflow-y-auto space-y-2 sm:space-y-3 font-mono text-[11px] sm:text-xs pr-1 sm:pr-2">
            {theaterMessages.length === 0 ? (
              <div className="h-44 flex flex-col items-center justify-center gap-3 text-slate-500 text-center">
                <Bot className="w-8 h-8 text-slate-600 animate-pulse" />
                <p>Waiting for live agent negotiation event stream...</p>
                <p className="text-[11px] text-slate-600">
                  Click <span className="text-cyan-400 font-semibold">"Run Live AI Negotiation"</span> above or trigger search on Storefront.
                </p>
              </div>
            ) : (
              theaterMessages.map((m, idx) => (
                <div
                  key={idx}
                  className={`p-2.5 sm:p-3.5 rounded-xl sm:rounded-2xl border space-y-1.5 ${
                    m.sender === "BUYER_AGENT"
                      ? "bg-blue-950/30 border-blue-500/30 sm:mr-12"
                      : m.sender === "MERCHANT_AGENT"
                      ? "bg-cyan-950/30 border-cyan-500/30 sm:ml-12"
                      : "bg-emerald-950/30 border-emerald-500/30 sm:mx-8"
                  }`}
                >
                  <div className="flex items-center justify-between text-[11px]">
                    <div className="flex items-center gap-2">
                      <span
                        className={`font-bold ${
                          m.sender === "BUYER_AGENT"
                            ? "text-blue-400"
                            : m.sender === "MERCHANT_AGENT"
                            ? "text-cyan-400"
                            : "text-emerald-400"
                        }`}
                      >
                        {m.sender} ({m.intent})
                      </span>
                      <span className="text-[10px] text-slate-500">Round {m.round}</span>
                    </div>

                    <span
                      className={`text-[10px] px-2 py-0.5 rounded-full ${
                        m.reasoning_source === "LLM"
                          ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30"
                          : m.reasoning_source === "DETERMINISTIC_GUARD"
                          ? "bg-purple-500/20 text-purple-400 border border-purple-500/30"
                          : "bg-amber-500/20 text-amber-400 border border-amber-500/30"
                      }`}
                    >
                      {m.reasoning_source === "LLM"
                        ? `🟢 ${m.model_name}`
                        : m.reasoning_source === "DETERMINISTIC_GUARD"
                        ? "🛡️ Deterministic Rule Guard"
                        : "🟡 Dev Heuristic"}
                    </span>
                  </div>

                  <p className="text-slate-200 text-xs font-sans">
                    "{m.reasoning_text}"
                  </p>

                  <div className="flex items-center justify-between pt-1 border-t border-white/5 text-[11px]">
                    <span className="text-white font-bold font-mono">
                      Proposed Price: ₹{(m.offered_price_paise / 100).toFixed(2)}
                    </span>
                    {m.discount_pct > 0 && (
                      <span className="text-emerald-400 font-mono">
                        {m.discount_pct}% discount
                      </span>
                    )}
                  </div>

                  {m.bundle_suggestion && (
                    <div className="mt-2 p-2 rounded-xl bg-slate-900/80 border border-cyan-500/30 flex items-center justify-between text-[11px]">
                      <span className="text-cyan-300 font-bold flex items-center gap-1">
                        <Gift className="w-3 h-3" />
                        Bundle Offer: {m.bundle_suggestion.name}
                      </span>
                      <span className="text-emerald-400">
                        +₹{(m.bundle_suggestion.bundled_price_paise / 100).toFixed(2)} ({m.bundle_suggestion.discount_pct}% off)
                      </span>
                    </div>
                  )}
                </div>
              ))
            )}
          </div>
        </div>

        {/* Real-time WebSocket Event Log Ticker */}
        <div className="p-3 sm:p-4 rounded-xl sm:rounded-2xl bg-slate-950/80 border border-white/10 font-mono text-[11px] sm:text-xs space-y-2">
          <div className="flex items-center justify-between text-slate-400 border-b border-white/5 pb-2">
            <div className="flex items-center gap-2">
              <Zap className="w-3.5 h-3.5 text-cyan-400" />
              <span>Real-Time WebSocket Mesh Stream</span>
            </div>
            <span className="text-[10px] text-slate-500">Auto-updating</span>
          </div>
          <div className="h-20 overflow-y-auto space-y-1.5 pr-2">
            {liveLog.length === 0 ? (
              <p className="text-slate-600">Waiting for live order events...</p>
            ) : (
              liveLog.map((l) => (
                <div key={l.id} className="flex items-center gap-3 text-[11px]">
                  <span className="text-slate-500">{l.time}</span>
                  <span
                    className={
                      l.type === "update"
                        ? "text-cyan-400 font-semibold"
                        : l.type === "warning"
                        ? "text-amber-400"
                        : "text-slate-400"
                    }
                  >
                    {l.text}
                  </span>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Order State Machine Kanban Swimlanes */}
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-bold text-white flex items-center gap-2">
              <Activity className="w-5 h-5 text-blue-400" />
              Order State Machine Mesh
            </h2>
            <span className="text-xs text-slate-400 font-mono">
              Click any card to inspect full cryptographic audit trail
            </span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-6">
            {Object.entries(STATUS_GROUPS).map(([groupKey, group]) => {
              const groupOrders = orders.filter((o) => group.states.includes(o.status));

              return (
                <div
                  key={groupKey}
                  className="glass-panel rounded-xl sm:rounded-2xl p-3 sm:p-4 flex flex-col gap-2 sm:gap-3 min-h-[200px] sm:min-h-[400px] border border-white/5"
                >
                  <div className={`flex items-center justify-between px-3 py-2 rounded-xl border text-xs font-semibold ${group.color}`}>
                    <span>{group.label}</span>
                    <span className="font-mono bg-black/30 px-2 py-0.5 rounded-full">
                      {groupOrders.length}
                    </span>
                  </div>

                  <div className="flex-1 space-y-2 sm:space-y-3 overflow-y-auto max-h-[300px] sm:max-h-[550px] pr-1">
                    {groupOrders.length === 0 ? (
                      <div className="h-32 flex items-center justify-center text-xs text-slate-600 font-mono">
                        No orders in this phase
                      </div>
                    ) : (
                      groupOrders.map((o) => (
                        <div
                          key={o.id}
                          onClick={() => setSelectedOrder(o)}
                          className="glass-card p-4 rounded-xl space-y-2 cursor-pointer hover:border-cyan-500/50 relative overflow-hidden"
                        >
                          <div className="flex items-center justify-between">
                            <span className="font-mono text-[11px] text-slate-400">
                              #{o.id.slice(0, 8)}
                            </span>
                            <span
                              className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded-full ${
                                o.status === "FULFILLED"
                                  ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30"
                                  : o.status.includes("PAYMENT_")
                                  ? "bg-amber-500/20 text-amber-400 border border-amber-500/30"
                                  : "bg-blue-500/20 text-blue-400 border border-blue-500/30"
                              }`}
                            >
                              {o.status}
                            </span>
                          </div>

                          <div className="flex items-baseline justify-between pt-1">
                            <span className="text-sm font-extrabold text-white font-mono">
                              ₹{(o.total_paise / 100).toFixed(2)}
                            </span>
                            <span className="text-[10px] text-slate-400 font-mono">
                              Qty: {o.quantity}
                            </span>
                          </div>

                          {o.razorpay_order_id && (
                            <div className="text-[10px] font-mono text-slate-500 truncate">
                              RZP: {o.razorpay_order_id}
                            </div>
                          )}

                          <div className="pt-2 border-t border-white/5 flex items-center justify-between text-[10px] text-slate-400 font-mono">
                            <span>{new Date(o.created_at).toLocaleTimeString()}</span>
                            <span className="text-cyan-400 flex items-center gap-1">
                              {o.events?.length || 0} audit logs <ArrowRight className="w-2.5 h-2.5" />
                            </span>
                          </div>
                        </div>
                      ))
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </main>

      {/* Audit Trail Modal Drilldown */}
      {selectedOrder && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-end sm:items-center justify-center p-0 sm:p-4">
          <div className="glass-panel max-w-2xl w-full max-h-[95vh] sm:max-h-[85vh] rounded-t-3xl sm:rounded-3xl p-4 sm:p-6 flex flex-col gap-4 sm:gap-6 relative border border-white/10">
            {/* Modal Header */}
            <div className="flex items-start justify-between border-b border-white/10 pb-4">
              <div>
                <div className="flex items-center gap-2">
                  <h3 className="font-bold text-lg text-white">Order Cryptographic Audit Trail</h3>
                  <span className="font-mono text-xs px-2.5 py-0.5 rounded-full bg-blue-500/20 text-blue-400 border border-blue-500/30">
                    {selectedOrder.status}
                  </span>
                </div>
                <p className="text-xs font-mono text-slate-400 mt-1">
                  ID: {selectedOrder.id} | Settled Total: ₹{(selectedOrder.total_paise / 100).toFixed(2)}
                </p>
              </div>
              <button
                onClick={() => setSelectedOrder(null)}
                className="text-slate-400 hover:text-white text-sm cursor-pointer"
              >
                ✕
              </button>
            </div>

            {/* Razorpay Meta */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 p-2 sm:p-3 rounded-xl bg-slate-900/80 border border-white/5 text-xs font-mono">
              <div>
                <span className="text-slate-500 block">Razorpay Order ID</span>
                <span className="text-cyan-400 font-semibold">{selectedOrder.razorpay_order_id || "N/A"}</span>
              </div>
              <div>
                <span className="text-slate-500 block">Razorpay Payment ID</span>
                <span className="text-emerald-400 font-semibold">{selectedOrder.razorpay_payment_id || "N/A"}</span>
              </div>
            </div>

            {/* Timeline of Order Events */}
            <div className="flex-1 overflow-y-auto space-y-3 pr-2">
              <h4 className="text-xs font-mono uppercase text-slate-400 tracking-wider">
                Cryptographic Audit Log Events ({selectedOrder.events?.length || 0})
              </h4>

              {(!selectedOrder.events || selectedOrder.events.length === 0) ? (
                <p className="text-xs text-slate-500 font-mono">No audit events recorded.</p>
              ) : (
                <div className="space-y-3 relative before:absolute before:left-3 before:top-2 before:bottom-2 before:w-0.5 before:bg-white/10">
                  {selectedOrder.events.map((ev, idx) => (
                    <div key={ev.id || idx} className="relative pl-8 space-y-1">
                      <div
                        className={`absolute left-1.5 top-1.5 w-3.5 h-3.5 rounded-full border-2 bg-slate-900 ${
                          ev.result === "ALLOW"
                            ? "border-emerald-400 text-emerald-400"
                            : ev.result === "DENY"
                            ? "border-rose-400 text-rose-400"
                            : "border-blue-400 text-blue-400"
                        }`}
                      />

                      <div className="p-3 rounded-xl bg-slate-900/60 border border-white/5 space-y-1.5 text-xs font-mono">
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-2">
                            <span className="font-bold text-white">{ev.action}</span>
                            <span className="text-[10px] px-2 py-0.5 rounded bg-slate-800 text-slate-300">
                              Actor: {ev.actor}
                            </span>
                          </div>
                          <span
                            className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${
                              ev.result === "ALLOW"
                                ? "bg-emerald-500/20 text-emerald-400"
                                : "bg-rose-500/20 text-rose-400"
                            }`}
                          >
                            {ev.result}
                          </span>
                        </div>

                        {ev.from_status && ev.to_status && (
                          <div className="text-slate-400 text-[11px]">
                            Transition: <span className="text-slate-300">{ev.from_status}</span> →{" "}
                            <span className="text-cyan-400 font-semibold">{ev.to_status}</span>
                          </div>
                        )}

                        {ev.detail && Object.keys(ev.detail).length > 0 && (
                          <pre className="text-[10px] text-slate-400 bg-black/40 p-2 rounded overflow-x-auto max-h-24">
                            {JSON.stringify(ev.detail, null, 2)}
                          </pre>
                        )}

                        <div className="text-[10px] text-slate-500 text-right">
                          {new Date(ev.created_at).toLocaleString()}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
