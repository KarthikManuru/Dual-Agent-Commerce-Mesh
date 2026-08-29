/**
 * Runtime configuration — reads Next.js public env vars.
 * If running on a deployed domain (Vercel) without env vars,
 * automatically points to the production Railway backend.
 */
export const API_URL =
  (process.env.NEXT_PUBLIC_API_URL && process.env.NEXT_PUBLIC_API_URL !== "undefined")
    ? process.env.NEXT_PUBLIC_API_URL
    : typeof window !== "undefined" &&
      window.location.hostname !== "localhost" &&
      window.location.hostname !== "127.0.0.1"
    ? "https://dual-agent-commerce-mesh-production.up.railway.app"
    : "http://127.0.0.1:8000";

export const WS_URL =
  (process.env.NEXT_PUBLIC_WS_URL && process.env.NEXT_PUBLIC_WS_URL !== "undefined")
    ? process.env.NEXT_PUBLIC_WS_URL
    : typeof window !== "undefined" &&
      window.location.hostname !== "localhost" &&
      window.location.hostname !== "127.0.0.1"
    ? "wss://dual-agent-commerce-mesh-production.up.railway.app/ws/orders"
    : "ws://127.0.0.1:8000/ws/orders";
