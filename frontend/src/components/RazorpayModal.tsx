"use client";

import { useState } from "react";
import { API_URL } from "@/lib/config";
import { Loader2, CheckCircle2, AlertCircle } from "lucide-react";

declare global {
  interface Window {
    Razorpay: any;
  }
}

interface RazorpayCheckoutProps {
  orderId: string;
  razorpayOrderId: string;
  razorpayKeyId: string;
  amountPaise: number;
  currency: string;
  productName: string;
  onSuccess: (paymentId: string) => void;
  onFailure: (error: string) => void;
}

export function loadRazorpayScript(): Promise<boolean> {
  return new Promise((resolve) => {
    if (typeof window === "undefined") {
      resolve(false);
      return;
    }
    if (window.Razorpay) {
      resolve(true);
      return;
    }
    const script = document.createElement("script");
    script.src = "https://checkout.razorpay.com/v1/checkout.js";
    script.onload = () => resolve(true);
    script.onerror = () => resolve(false);
    document.body.appendChild(script);
  });
}

export default function RazorpayModal({
  orderId,
  razorpayOrderId,
  razorpayKeyId,
  amountPaise,
  currency,
  productName,
  onSuccess,
  onFailure,
}: RazorpayCheckoutProps) {
  const [loading, setLoading] = useState(false);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  const handleOpenCheckout = async () => {
    setLoading(true);
    setStatusMessage("Loading Razorpay Test Checkout...");

    const isLoaded = await loadRazorpayScript();
    if (!isLoaded) {
      setLoading(false);
      setStatusMessage("Failed to load Razorpay SDK. Please check your internet connection.");
      onFailure("SDK load error");
      return;
    }

    const options = {
      key: razorpayKeyId,
      amount: amountPaise,
      currency: currency,
      name: "TechMesh Electronics",
      description: `Test Purchase: ${productName}`,
      order_id: razorpayOrderId,
      theme: {
        color: "#06b6d4",
      },
      handler: async function (response: any) {
        setStatusMessage("Verifying payment signature with backend...");
        try {
          const verifyRes = await fetch(`${API_URL}/orders/${orderId}/verify`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              razorpay_order_id: response.razorpay_order_id,
              razorpay_payment_id: response.razorpay_payment_id,
              razorpay_signature: response.razorpay_signature,
            }),
          });

          if (!verifyRes.ok) {
            const err = await verifyRes.json();
            throw new Error(err.detail || "Payment signature verification failed");
          }

          setStatusMessage("Payment Verified Successfully!");
          onSuccess(response.razorpay_payment_id);
        } catch (err: any) {
          setStatusMessage(err.message || "Payment verification failed");
          onFailure(err.message);
        } finally {
          setLoading(false);
        }
      },
      modal: {
        ondismiss: function () {
          setLoading(false);
          setStatusMessage("Checkout closed by user.");
        },
      },
      prefill: {
        name: "Test Buyer",
        email: "test.buyer@mesh.commerce",
        contact: "9999999999",
      },
    };

    const paymentObject = new window.Razorpay(options);
    paymentObject.open();
    setLoading(false);
  };

  return (
    <div className="flex flex-col items-center gap-3">
      <button
        onClick={handleOpenCheckout}
        disabled={loading}
        className="w-full py-3 px-6 rounded-xl font-semibold text-white bg-gradient-to-r from-blue-600 via-cyan-500 to-teal-400 hover:opacity-95 shadow-lg shadow-cyan-500/25 transition-all flex items-center justify-center gap-2 cursor-pointer disabled:opacity-50"
      >
        {loading ? (
          <>
            <Loader2 className="w-5 h-5 animate-spin" />
            Initializing Checkout...
          </>
        ) : (
          <>
            Pay with Razorpay Test Mode (₹{(amountPaise / 100).toFixed(2)})
          </>
        )}
      </button>

      {statusMessage && (
        <p className="text-xs font-mono text-slate-300 text-center bg-slate-900/60 px-3 py-1.5 rounded-lg border border-white/5">
          {statusMessage}
        </p>
      )}
    </div>
  );
}
