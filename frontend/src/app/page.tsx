"use client";

import { useEffect, useState } from "react";
import { API_URL } from "@/lib/config";
import Navbar from "@/components/Navbar";
import RazorpayModal from "@/components/RazorpayModal";
import {
  ShoppingBag,
  Tag,
  Box,
  ArrowRight,
  Shield,
  CheckCircle2,
  Sparkles,
  Bot,
  Zap,
  Send,
  Loader2,
  Scale,
  Gift,
  ShieldAlert,
  Search,
} from "lucide-react";

interface Product {
  id: string;
  name: string;
  description: string;
  category: string;
  price_paise: number;
  price_display: string;
  tags: string[];
  inventory: {
    total_stock: number;
    reserved: number;
    available: number;
  };
}

interface NegotiationMessage {
  sender: "BUYER_AGENT" | "MERCHANT_AGENT" | "FINANCIAL_GUARD" | "USER";
  intent: string;
  offered_price_paise: number;
  discount_pct: number;
  reasoning_text: string;
  reason_codes: string[];
  bundle_suggestion?: {
    product_id: string;
    name: string;
    original_price_paise: number;
    bundled_price_paise: number;
    discount_pct: number;
  };
  reasoning_source: string;
  model_name: string;
  latency_ms: number;
  round: number;
}

interface NegotiationSessionResult {
  session_id: string;
  product: Product;
  outcome: string;
  agreed_price_paise: number | null;
  discount_achieved_pct: number | null;
  bundle_included?: any;
  messages: NegotiationMessage[];
  order_id: string | null;
  razorpay_order_id: string | null;
  duration_ms: number;
}

const MERCHANT_ID = "a1b2c3d4-e5f6-7890-abcd-ef1234567890";

const PRESET_PROMPTS = [
  "Find me ANC wireless headphones for office calls under ₹3,000",
  "Tenkeyless mechanical keyboard with RGB for gaming under ₹5,500",
  "High-power multi-port 65W GaN USB-C laptop charger",
  "Ergonomic silent wireless mouse under ₹3,500",
];

export default function StorePage() {
  const [products, setProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedCategory, setSelectedCategory] = useState<string>("all");
  
  // Conversational Search State
  const [chatPrompt, setChatPrompt] = useState("");
  const [isProcessingAI, setIsProcessingAI] = useState(false);
  const [activeSession, setActiveSession] = useState<NegotiationSessionResult | null>(null);

  // Negotiation Modal for Selected Product
  const [negotiatingProduct, setNegotiatingProduct] = useState<Product | null>(null);
  const [buyerStrategy, setBuyerStrategy] = useState<"BARGAIN_HUNTER" | "EAGER" | "BUDGET_STRICT">("BARGAIN_HUNTER");
  const [targetBudget, setTargetBudget] = useState<string>("");

  // Checkout State
  const [activeCheckout, setActiveCheckout] = useState<{
    product: Product;
    orderId: string;
    razorpayOrderId: string;
    razorpayKeyId: string;
    amountPaise: number;
  } | null>(null);
  const [paymentSuccessId, setPaymentSuccessId] = useState<string | null>(null);

  useEffect(() => {
    fetchProducts();
  }, []);

  const fetchProducts = async () => {
    try {
      setLoading(true);
      const res = await fetch(`${API_URL}/products`);
      if (res.ok) {
        const data = await res.json();
        setProducts(data.products || []);
      }
    } catch (e) {
      console.error("Failed to load products:", e);
    } finally {
      setLoading(false);
    }
  };

  // Direct Manual Purchase (Phase 2 Spine)
  const handleDirectPurchase = async (product: Product) => {
    try {
      setIsProcessingAI(true);
      const res = await fetch(`${API_URL}/orders`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          product_id: product.id,
          merchant_id: MERCHANT_ID,
          quantity: 1,
        }),
      });

      if (!res.ok) {
        const err = await res.json();
        alert(`Order creation failed: ${err.detail}`);
        return;
      }

      const data = await res.json();
      setActiveCheckout({
        product,
        orderId: data.order.id,
        razorpayOrderId: data.razorpay_order_id,
        razorpayKeyId: data.razorpay_key_id,
        amountPaise: data.amount_paise,
      });
    } catch (e: any) {
      alert(`Error: ${e.message}`);
    } finally {
      setIsProcessingAI(false);
    }
  };

  // Conversational AI Search & Auto-Negotiation
  const handleConversationalSubmit = async (queryText?: string) => {
    const q = queryText || chatPrompt;
    if (!q.trim()) return;

    try {
      setIsProcessingAI(true);
      setActiveSession(null);
      const res = await fetch(`${API_URL}/sessions/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          query: q,
          buyer_strategy: "BARGAIN_HUNTER",
        }),
      });

      if (!res.ok) {
        const err = await res.json();
        alert(`AI Search Error: ${err.detail}`);
        return;
      }

      const sessionData: NegotiationSessionResult = await res.json();
      setActiveSession(sessionData);
    } catch (e: any) {
      alert(`Error: ${e.message}`);
    } finally {
      setIsProcessingAI(false);
    }
  };

  // Direct Product AI Auto-Negotiate
  const handleStartProductNegotiation = async () => {
    if (!negotiatingProduct) return;

    try {
      setIsProcessingAI(true);
      setActiveSession(null);

      const budgetPaise = targetBudget
        ? parseInt(targetBudget) * 100
        : Math.floor(negotiatingProduct.price_paise * 1.05);

      const res = await fetch(`${API_URL}/sessions/negotiate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          product_id: negotiatingProduct.id,
          buyer_strategy: buyerStrategy,
          buyer_budget_paise: budgetPaise,
        }),
      });

      if (!res.ok) {
        const err = await res.json();
        alert(`Negotiation Error: ${err.detail}`);
        return;
      }

      const sessionData: NegotiationSessionResult = await res.json();
      setActiveSession(sessionData);
      setNegotiatingProduct(null);
    } catch (e: any) {
      alert(`Error: ${e.message}`);
    } finally {
      setIsProcessingAI(false);
    }
  };

  // Proceed to Checkout from an Accepted Negotiation
  const handleProceedFromSession = (session: NegotiationSessionResult) => {
    if (!session.order_id || !session.razorpay_order_id || !session.agreed_price_paise) return;
    setActiveCheckout({
      product: session.product,
      orderId: session.order_id,
      razorpayOrderId: session.razorpay_order_id,
      razorpayKeyId: "rzp_test_TTy10rL0en9aP3",
      amountPaise: session.agreed_price_paise,
    });
    setActiveSession(null);
  };

  const categories = ["all", ...Array.from(new Set(products.map((p) => p.category)))];
  const filteredProducts =
    selectedCategory === "all"
      ? products
      : products.filter((p) => p.category === selectedCategory);

  return (
    <div className="min-h-screen flex flex-col bg-[#090d16]">
      <Navbar />

      <main className="flex-1 max-w-7xl w-full mx-auto px-3 sm:px-6 py-4 sm:py-8 space-y-6 sm:space-y-10">
        {/* Hero Section */}
        <section className="p-4 sm:p-6 lg:p-8 rounded-2xl sm:rounded-3xl glass-panel relative overflow-hidden">
          <div className="absolute -right-20 -top-20 w-40 sm:w-80 h-40 sm:h-80 bg-blue-500/10 rounded-full blur-3xl pointer-events-none" />
          <div className="absolute -left-20 -bottom-20 w-40 sm:w-80 h-40 sm:h-80 bg-cyan-500/10 rounded-full blur-3xl pointer-events-none" />

          <div className="relative z-10 space-y-4 sm:space-y-6">
            <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
              <div className="space-y-2">
                <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-cyan-500/10 border border-cyan-500/30 text-cyan-400 text-xs font-mono">
                  <Sparkles className="w-3.5 h-3.5" />
                  Dual-Agent Commerce Mesh Live Protocol
                </div>
                <h1 className="text-xl sm:text-3xl md:text-5xl font-black tracking-tight text-white">
                  Autonomous AI Commerce with{" "}
                  <span className="bg-clip-text text-transparent bg-gradient-to-r from-cyan-400 via-blue-400 to-indigo-400">
                    Real LLM & Financial Guard
                  </span>
                </h1>
                <p className="text-slate-400 text-sm md:text-base max-w-3xl">
                  AI Buyer and Merchant agents deliberate in natural language, negotiate prices over structured JSON contracts, and enforce strict deterministic financial safety guardrails.
                </p>
              </div>

              <div className="p-3 sm:p-4 rounded-xl sm:rounded-2xl bg-slate-900/80 border border-white/10 text-[11px] sm:text-xs font-mono space-y-1 sm:space-y-2 shrink-0 w-full md:w-auto">
                <div className="flex items-center gap-2 text-emerald-400 font-semibold">
                  <Shield className="w-4 h-4" />
                  <span>AI Proposes • Guard Decides</span>
                </div>
                <div className="text-slate-400 text-[11px]">
                  Max Discount: 15% • Min Margin: 10%
                </div>
              </div>
            </div>

            {/* Conversational Natural-Language AI Prompt Bar */}
            <div className="p-3 sm:p-4 rounded-xl sm:rounded-2xl bg-slate-900/90 border border-cyan-500/30 shadow-xl shadow-cyan-500/5 space-y-2 sm:space-y-3">
              <div className="flex items-center gap-2 text-xs font-mono text-cyan-400">
                <Bot className="w-4 h-4" />
                <span>Conversational In-App Mesh Search & Auto-Negotiation:</span>
              </div>

              <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2">
                <div className="relative flex-1">
                  <Search className="w-4 h-4 text-slate-500 absolute left-3.5 top-1/2 -translate-y-1/2" />
                  <input
                    type="text"
                    value={chatPrompt}
                    onChange={(e) => setChatPrompt(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && handleConversationalSubmit()}
                    placeholder="e.g. 'Find me ANC headphones under ₹3,000 for office calls' or 'Mechanical keyboard for gaming'"
                    className="w-full bg-slate-950/80 border border-white/10 rounded-xl pl-10 pr-4 py-2.5 sm:py-3 text-xs sm:text-sm text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500 transition-colors"
                  />
                </div>
                <button
                  onClick={() => handleConversationalSubmit()}
                  disabled={isProcessingAI || !chatPrompt.trim()}
                  className="px-4 sm:px-6 py-2.5 sm:py-3 rounded-xl bg-gradient-to-r from-blue-600 via-cyan-500 to-teal-400 hover:opacity-90 text-white font-semibold text-xs font-mono flex items-center justify-center gap-2 shadow-lg shadow-cyan-500/20 cursor-pointer disabled:opacity-50 shrink-0"
                >
                  {isProcessingAI ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <>
                      <Send className="w-4 h-4" />
                      <span>Ask AI Agent</span>
                    </>
                  )}
                </button>
              </div>

              {/* Preset prompt chips */}
              <div className="flex items-center gap-2 overflow-x-auto pt-1 pb-1 -mx-1 px-1">
                <span className="text-[11px] font-mono text-slate-500 shrink-0">Try prompt:</span>
                {PRESET_PROMPTS.map((p, idx) => (
                  <button
                    key={idx}
                    onClick={() => {
                      setChatPrompt(p);
                      handleConversationalSubmit(p);
                    }}
                    className="text-[11px] font-mono px-2.5 py-1 rounded-lg bg-slate-800/80 hover:bg-cyan-500/10 hover:text-cyan-300 hover:border-cyan-500/30 border border-white/5 text-slate-400 transition-all text-left shrink-0 cursor-pointer"
                  >
                    {p}
                  </button>
                ))}
              </div>
            </div>
          </div>
        </section>

        {/* Success Banner if paid */}
        {paymentSuccessId && (
          <div className="p-4 sm:p-6 rounded-2xl bg-emerald-950/40 border border-emerald-500/40 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 sm:gap-4">
            <div className="flex items-center gap-3">
              <CheckCircle2 className="w-6 h-6 text-emerald-400 shrink-0" />
              <div>
                <h4 className="font-semibold text-emerald-300">Payment Successfully Captured!</h4>
                <p className="text-xs font-mono text-slate-300">
                  Razorpay Payment ID: <span className="text-emerald-400">{paymentSuccessId}</span>
                </p>
              </div>
            </div>
            <a
              href="/dashboard"
              className="px-4 py-2 rounded-xl bg-emerald-500/20 text-emerald-300 hover:bg-emerald-500/30 text-xs font-mono flex items-center gap-1.5 transition-colors"
            >
              View in Command Center <ArrowRight className="w-3.5 h-3.5" />
            </a>
          </div>
        )}

        {/* Category Filters */}
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2 sm:gap-4 pb-2 border-b border-white/5">
          <div className="flex items-center gap-2 overflow-x-auto">
            {categories.map((cat) => (
              <button
                key={cat}
                onClick={() => setSelectedCategory(cat)}
                className={`px-4 py-1.5 rounded-xl text-xs font-medium uppercase tracking-wider transition-all cursor-pointer ${
                  selectedCategory === cat
                    ? "bg-blue-600 text-white shadow-md shadow-blue-500/20 border border-blue-400/30"
                    : "bg-slate-900/60 text-slate-400 hover:text-white border border-white/5"
                }`}
              >
                {cat}
              </button>
            ))}
          </div>

          <span className="text-xs font-mono text-slate-500">
            {filteredProducts.length} mesh items
          </span>
        </div>

        {/* Product Grid */}
        {loading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {[1, 2, 3, 4, 5, 6].map((i) => (
              <div key={i} className="h-64 rounded-2xl glass-card animate-pulse" />
            ))}
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {filteredProducts.map((p) => (
              <div
                key={p.id}
                className="glass-card rounded-2xl p-6 flex flex-col justify-between group relative overflow-hidden border border-white/5 hover:border-cyan-500/40"
              >
                <div>
                  <div className="flex items-center justify-between gap-2 mb-3">
                    <span className="text-[11px] font-mono uppercase tracking-wider px-2.5 py-1 rounded-md bg-slate-800 text-cyan-400 border border-cyan-500/20">
                      {p.category}
                    </span>
                    <div className="flex items-center gap-1 text-xs text-slate-400 font-mono">
                      <Box className="w-3.5 h-3.5" />
                      <span className={p.inventory?.available > 5 ? "text-emerald-400" : "text-amber-400"}>
                        {p.inventory?.available ?? 0} in stock
                      </span>
                    </div>
                  </div>

                  <h3 className="font-bold text-lg text-white group-hover:text-cyan-300 transition-colors mb-2">
                    {p.name}
                  </h3>
                  <p className="text-xs text-slate-400 line-clamp-3 mb-4 leading-relaxed">
                    {p.description}
                  </p>

                  {/* Tags */}
                  <div className="flex flex-wrap gap-1.5 mb-6">
                    {p.tags?.map((tag) => (
                      <span
                        key={tag}
                        className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-900/80 text-slate-400 border border-white/5"
                      >
                        #{tag}
                      </span>
                    ))}
                  </div>
                </div>

                <div className="pt-4 border-t border-white/5 space-y-3">
                  <div className="flex items-baseline justify-between gap-2 flex-wrap">
                    <div>
                      <span className="text-[10px] text-slate-500 uppercase block font-mono">List Price</span>
                      <span className="text-lg sm:text-xl font-extrabold text-white">
                        {p.price_display}
                      </span>
                    </div>

                    <span className="text-[9px] sm:text-[10px] font-mono text-cyan-400 bg-cyan-500/10 px-2 py-0.5 rounded border border-cyan-500/20">
                      AI Negotiable
                    </span>
                  </div>

                  {/* Dual Action Buttons */}
                  <div className="grid grid-cols-2 gap-2">
                    <button
                      onClick={() => {
                        setNegotiatingProduct(p);
                        setTargetBudget((p.price_paise / 100).toString());
                      }}
                      className="w-full py-2.5 rounded-xl bg-gradient-to-r from-blue-600 to-indigo-600 hover:opacity-90 text-white text-xs font-semibold font-mono flex items-center justify-center gap-1.5 shadow-md shadow-blue-500/20 cursor-pointer"
                    >
                      <Bot className="w-3.5 h-3.5" />
                      Auto-Negotiate
                    </button>

                    <button
                      onClick={() => handleDirectPurchase(p)}
                      disabled={isProcessingAI || p.inventory?.available <= 0}
                      className="w-full py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold font-mono flex items-center justify-center gap-1 cursor-pointer disabled:opacity-50"
                    >
                      Direct Buy <ArrowRight className="w-3 h-3" />
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </main>

      {/* Live AI Negotiation Transcript Modal */}
      {activeSession && (
        <div className="fixed inset-0 z-50 bg-black/85 backdrop-blur-md flex items-end sm:items-center justify-center p-0 sm:p-4">
          <div className="glass-panel max-w-2xl w-full max-h-[95vh] sm:max-h-[85vh] rounded-t-3xl sm:rounded-3xl p-4 sm:p-6 flex flex-col gap-3 sm:gap-5 relative border border-cyan-500/30">
            {/* Header */}
            <div className="flex items-start justify-between border-b border-white/10 pb-4">
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <span className="text-lg font-bold text-white">
                    Dual-Agent Negotiation Transcript
                  </span>
                  <span
                    className={`text-xs font-mono px-2.5 py-0.5 rounded-full font-semibold ${
                      activeSession.outcome === "ACCEPTED"
                        ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30"
                        : "bg-rose-500/20 text-rose-400 border border-rose-500/30"
                    }`}
                  >
                    {activeSession.outcome}
                  </span>
                </div>
                <p className="text-xs font-mono text-slate-400">
                  Product: <span className="text-white font-semibold">{activeSession.product.name}</span> | Catalog: {activeSession.product.price_display}
                </p>
              </div>

              <button
                onClick={() => setActiveSession(null)}
                className="text-slate-400 hover:text-white text-sm cursor-pointer"
              >
                ✕
              </button>
            </div>

            {/* Negotiation Dialogue Stream */}
            <div className="flex-1 overflow-y-auto space-y-2 sm:space-y-3 pr-1 sm:pr-2 font-mono text-[11px] sm:text-xs">
              {activeSession.messages.map((m, idx) => (
                <div
                  key={idx}
                  className={`p-2.5 sm:p-3.5 rounded-xl sm:rounded-2xl border space-y-1.5 ${
                    m.sender === "BUYER_AGENT"
                      ? "bg-blue-950/40 border-blue-500/30 sm:mr-8"
                      : m.sender === "MERCHANT_AGENT"
                      ? "bg-cyan-950/40 border-cyan-500/30 sm:ml-8"
                      : "bg-emerald-950/30 border-emerald-500/30 sm:mx-4"
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

                    {/* Verifiability Tag */}
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
                        ? "🛡️ Math Rule Guard"
                        : "🟡 Dev Heuristic"}
                    </span>
                  </div>

                  <p className="text-slate-200 text-xs leading-relaxed font-sans">
                    "{m.reasoning_text}"
                  </p>

                  <div className="flex items-center justify-between pt-1 border-t border-white/5 text-[11px]">
                    <span className="text-white font-bold">
                      Price: ₹{(m.offered_price_paise / 100).toFixed(2)}
                    </span>
                    {m.discount_pct > 0 && (
                      <span className="text-emerald-400">
                        {m.discount_pct}% discount
                      </span>
                    )}
                  </div>

                  {m.bundle_suggestion && (
                    <div className="mt-2 p-2.5 rounded-xl bg-slate-900 border border-cyan-500/30 space-y-1">
                      <div className="flex items-center gap-1.5 text-cyan-300 font-bold text-[11px]">
                        <Gift className="w-3.5 h-3.5" />
                        <span>Recommended Bundle Add-On: {m.bundle_suggestion.name}</span>
                      </div>
                      <div className="flex justify-between text-slate-300 text-[10px]">
                        <span>Add for only ₹{(m.bundle_suggestion.bundled_price_paise / 100).toFixed(2)}</span>
                        <span className="text-emerald-400">{m.bundle_suggestion.discount_pct}% off add-on</span>
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>

            {/* Outcome Footer & Action */}
            <div className="pt-3 border-t border-white/10 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 sm:gap-4">
              <div>
                {activeSession.outcome === "ACCEPTED" ? (
                  <div>
                    <span className="text-[10px] uppercase font-mono text-slate-400 block">Negotiated Final Price</span>
                    <span className="text-xl sm:text-2xl font-black text-cyan-400 font-mono">
                      ₹{((activeSession.agreed_price_paise || 0) / 100).toFixed(2)}
                    </span>
                    <span className="text-xs text-emerald-400 font-mono ml-2">
                      ({activeSession.discount_achieved_pct}% saved)
                    </span>
                  </div>
                ) : (
                  <span className="text-sm font-mono text-rose-400">
                    Negotiation ended without deal agreement.
                  </span>
                )}
              </div>

              {activeSession.outcome === "ACCEPTED" && (
                <button
                  onClick={() => handleProceedFromSession(activeSession)}
                  className="w-full sm:w-auto px-6 py-3 rounded-xl bg-gradient-to-r from-emerald-500 to-teal-500 hover:opacity-90 text-white font-semibold text-xs font-mono flex items-center justify-center gap-2 shadow-lg shadow-emerald-500/20 cursor-pointer"
                >
                  Proceed to Razorpay Checkout <ArrowRight className="w-4 h-4" />
                </button>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Product Specific Negotiation Setup Modal */}
      {negotiatingProduct && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-end sm:items-center justify-center p-0 sm:p-4">
          <div className="glass-panel max-w-md w-full rounded-t-3xl sm:rounded-3xl p-4 sm:p-6 space-y-4 sm:space-y-6 relative border border-white/10">
            <div className="flex items-center justify-between pb-4 border-b border-white/10">
              <div className="flex items-center gap-2">
                <Bot className="w-5 h-5 text-cyan-400" />
                <h3 className="font-bold text-lg text-white">Configure AI Buyer Agent</h3>
              </div>
              <button
                onClick={() => setNegotiatingProduct(null)}
                className="text-slate-400 hover:text-white text-sm cursor-pointer"
              >
                ✕
              </button>
            </div>

            <div className="space-y-4 text-xs font-mono">
              <div className="p-3 rounded-xl bg-slate-900/60 border border-white/5 space-y-1">
                <span className="text-slate-400 block">Product:</span>
                <span className="text-white font-bold text-sm">{negotiatingProduct.name}</span>
                <span className="text-cyan-400 block">Catalog Price: {negotiatingProduct.price_display}</span>
              </div>

              {/* Strategy Picker */}
              <div className="space-y-2">
                <label className="text-slate-300 font-semibold block">Buyer Agent Strategy Persona:</label>
                <div className="grid grid-cols-3 gap-2">
                  {(["BARGAIN_HUNTER", "EAGER", "BUDGET_STRICT"] as const).map((strat) => (
                    <button
                      key={strat}
                      onClick={() => setBuyerStrategy(strat)}
                      className={`p-2.5 rounded-xl border text-[10px] font-bold text-center cursor-pointer transition-all ${
                        buyerStrategy === strat
                          ? "bg-cyan-500/20 border-cyan-400 text-cyan-300 shadow-md shadow-cyan-500/10"
                          : "bg-slate-900/80 border-white/5 text-slate-400 hover:text-white"
                      }`}
                    >
                      {strat.replace("_", " ")}
                    </button>
                  ))}
                </div>
              </div>

              {/* Budget input */}
              <div className="space-y-1.5">
                <label className="text-slate-300 font-semibold block">Buyer Budget Ceiling (₹):</label>
                <input
                  type="number"
                  value={targetBudget}
                  onChange={(e) => setTargetBudget(e.target.value)}
                  placeholder="e.g. 2800"
                  className="w-full bg-slate-950 border border-white/10 rounded-xl px-4 py-2.5 text-white focus:outline-none focus:border-cyan-500"
                />
              </div>
            </div>

            <button
              onClick={handleStartProductNegotiation}
              disabled={isProcessingAI}
              className="w-full py-3 rounded-xl bg-gradient-to-r from-blue-600 via-cyan-500 to-teal-400 hover:opacity-90 text-white font-semibold text-xs font-mono flex items-center justify-center gap-2 shadow-lg shadow-cyan-500/20 cursor-pointer disabled:opacity-50"
            >
              {isProcessingAI ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Agents Negotiating...
                </>
              ) : (
                <>
                  <Zap className="w-4 h-4" />
                  Launch Autonomous Agent Deal
                </>
              )}
            </button>
          </div>
        </div>
      )}

      {/* Razorpay Checkout Modal Overlay */}
      {activeCheckout && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-end sm:items-center justify-center p-0 sm:p-4">
          <div className="glass-panel max-w-md w-full rounded-t-3xl sm:rounded-3xl p-4 sm:p-6 space-y-4 sm:space-y-6 relative border border-white/10">
            <div className="flex items-center justify-between pb-4 border-b border-white/10">
              <h3 className="font-bold text-lg text-white">Order Checkout</h3>
              <button
                onClick={() => setActiveCheckout(null)}
                className="text-slate-400 hover:text-white text-sm"
              >
                ✕
              </button>
            </div>

            <div className="space-y-3 bg-slate-900/60 p-4 rounded-2xl border border-white/5 text-sm">
              <div className="flex justify-between text-slate-300">
                <span>Product:</span>
                <span className="font-semibold text-white">{activeCheckout.product.name}</span>
              </div>
              <div className="flex justify-between text-slate-300">
                <span>Order Total:</span>
                <span className="font-mono font-bold text-cyan-400">
                  ₹{(activeCheckout.amountPaise / 100).toFixed(2)}
                </span>
              </div>
              <div className="flex justify-between text-xs text-slate-400 font-mono">
                <span>Razorpay Order:</span>
                <span>{activeCheckout.razorpayOrderId}</span>
              </div>
            </div>

            <RazorpayModal
              orderId={activeCheckout.orderId}
              razorpayOrderId={activeCheckout.razorpayOrderId}
              razorpayKeyId={activeCheckout.razorpayKeyId}
              amountPaise={activeCheckout.amountPaise}
              currency="INR"
              productName={activeCheckout.product.name}
              onSuccess={(payId) => {
                setPaymentSuccessId(payId);
                setActiveCheckout(null);
                fetchProducts();
              }}
              onFailure={(err) => {
                console.error("Checkout failed:", err);
              }}
            />
          </div>
        </div>
      )}
    </div>
  );
}
