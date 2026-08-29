# 🌐 Dual-Agent Autonomous Commerce Mesh (DA-ACM)

[![Live Storefront](https://img.shields.io/badge/Live_Storefront-Vercel-black?style=for-the-badge&logo=vercel)](https://dual-agent-commerce-mesh.vercel.app/)
[![Merchant Dashboard](https://img.shields.io/badge/Merchant_Dashboard-Live-00C7B7?style=for-the-badge&logo=nextdotjs)](https://dual-agent-commerce-mesh.vercel.app/dashboard)
[![Production API](https://img.shields.io/badge/Backend_API-Railway-0B0D0E?style=for-the-badge&logo=railway)](https://dual-agent-commerce-mesh-production.up.railway.app)
[![API Docs](https://img.shields.io/badge/Swagger_Docs-FastAPI-009688?style=for-the-badge&logo=fastapi)](https://dual-agent-commerce-mesh-production.up.railway.app/docs)
[![Protocol](https://img.shields.io/badge/Mesh_Standard-DA--ACP_v1.0-blueviolet?style=for-the-badge)](https://dual-agent-commerce-mesh-production.up.railway.app/.well-known/ai-commerce)

> **Track 01: AI Growth & Agentic Commerce**  
> *Grow the merchant's revenue, and make them transactable by an AI buyer end-to-end over Razorpay Test Mode.*

---

## 📌 Executive Summary & "Why Now"

With the emergence of **NPCI's Universal Authenticated Protocol (UAP)** and the global agent protocol race (**ACP**, **AP2**, **x402**), the paradigm of commerce is fundamentally pivoting from human-driven point-and-click websites to **autonomous agent-to-agent negotiation networks**.

However, autonomous commerce presents a critical challenge: **uncontrolled AI agents cannot be trusted with real money**. LLMs hallucinate prices, concede unbounded discounts, and fall prey to prompt injection attacks. 

The **Dual-Agent Autonomous Commerce Mesh** solves this with a groundbreaking hybrid architecture:
1. **Generative Intelligence at the Edge**: Autonomous Buyer and Merchant LLM agents engage in natural-language bargaining, competitive alternative matching, and dynamic cross-sell bundle synthesis.
2. **Deterministic Financial Guardrails at the Core**: A non-bypassable, mathematically bounded `FinancialActionGuard` gates every single proposed transaction before a rupee can be committed.
3. **Cryptographic SHA-256 Tamper-Evident Audit Trails**: An immutable hash-chained event log provides complete mathematical proof of every step and transaction state.

---

## 🚀 Live Production Deployments

* **🛒 Autonomous Buyer Storefront**: [https://dual-agent-commerce-mesh.vercel.app/](https://dual-agent-commerce-mesh.vercel.app/)
* **📊 Merchant Command Center & Live Theater**: [https://dual-agent-commerce-mesh.vercel.app/dashboard](https://dual-agent-commerce-mesh.vercel.app/dashboard)
* **⚡ Production API Gateway (FastAPI)**: [https://dual-agent-commerce-mesh-production.up.railway.app](https://dual-agent-commerce-mesh-production.up.railway.app)
* **📖 Interactive API Docs (Swagger / OpenAPI)**: [https://dual-agent-commerce-mesh-production.up.railway.app/docs](https://dual-agent-commerce-mesh-production.up.railway.app/docs)
* **🤖 AI Discovery Manifest (`.well-known`)**: [https://dual-agent-commerce-mesh-production.up.railway.app/.well-known/ai-commerce](https://dual-agent-commerce-mesh-production.up.railway.app/.well-known/ai-commerce)

---

## 🏛️ System Architecture

```
                                    ┌────────────────────────────────────────────────────────┐
                                    │               NATURAL LANGUAGE BUYER INPUT             │
                                    │    "Find me ANC headphones with good bass under ₹3000" │
                                    └───────────────────────────┬────────────────────────────┘
                                                                │
                                                                ▼
                                                ┌───────────────────────────────┐
                                                │        BUYER AGENT            │
                                                │   Intent Parser & Evaluator   │
                                                └───────────────┬───────────────┘
                                                                │
                                    ┌───────────────────────────┴───────────────────────────┐
                                    │  MULTI-TURN STRUCTURED JSON BARGAINING PROTOCOL       │
                                    │  (Concessions, Alternatives, Cross-Sell Perks)        │
                                    └───────────────────────────┬───────────────────────────┘
                                                                │
                                                                ▼
                                                ┌───────────────────────────────┐
                                                │       MERCHANT AGENT          │
                                                │ Dynamic Counter-Offers & Perks│
                                                └───────────────┬───────────────┘
                                                                │
                                                                ▼
                    ╔═══════════════════════════════════════════════════════════════════════════╗
                    ║                    DETERMINISTIC FINANCIAL ACTION GUARD                   ║
                    ║     - Max Discount Cap (%)         - Minimum Profit Margin (%)            ║
                    ║     - Max Negotiation Rounds (Cap) - Offer Time-To-Live (TTL seconds)     ║
                    ║     - Maximum Order Value (Cap)    - Stock Reservation Mutex (Redis)      ║
                    ╚═══════════════════════════════════════════════════════════════════════════╝
                                                                │
                                    ┌───────────────────────────┴───────────────────────────┐
                                    │                   GATED & BOUNDED                     │
                                    ▼                                                       ▼
                    ┌───────────────────────────────┐                       ┌───────────────────────────────┐
                    │    RAZORPAY TEST GATEWAY      │                       │     SHA-256 HASH CHAIN        │
                    │ Orders API + Signature Verify │                       │  Immutable Audit Event Ledger │
                    └───────────────┬───────────────┘                       └───────────────────────────────┘
                                    │
                                    ▼
                    ┌───────────────────────────────┐
                    │  REAL-TIME WEBSOCKET TELEMETRY│
                    │  Live Stream to Command Center│
                    └───────────────────────────────┘
```

---

## 🌟 Core Pillars & Unique Innovations

### 1. Dual-Agent Autonomous Bargaining Engine
* **Buyer Agent (`buyer_agent.py`)**: Parses human user prompts into structured constraints (budget, category, desired features). Evaluates seller proposals, counter-offers strategically across rounds, and rejects above-budget terms.
* **Merchant Agent (`merchant_agent.py`)**: Defends margin floors, offers incremental percentage concessions, and synthesizes dynamic value-add cross-sell packages (e.g., bundling USB-C cables or extended warranties to preserve unit economics).
* **LLM Engine**: Powered by Google Gemini / OpenAI `gpt-4o-mini` with zero-downtime heuristic graceful fallback.

### 2. The Deterministic Financial Action Guard (`financial_guard.py`)
No LLM ever writes directly to the database or creates a Razorpay transaction without passing the guard:
$$\text{Offered Price} \ge \text{Cost Price} \times (1 + \text{Min Margin Pct})$$
$$\text{Discount Pct} \le \text{Merchant Max Discount Pct}$$
$$\text{Round Count} \le \text{Policy Max Negotiation Rounds}$$
$$\text{Elapsed Time} \le \text{Offer TTL Seconds}$$

### 3. Cryptographic SHA-256 Audit Trail & Tamper Verification
Every order lifecycle event (`OrderEvent`) generates a cryptographic block:
$$\text{current\_hash} = \text{SHA-256}(\text{prev\_hash} \,\|\, \text{order\_id} \,\|\, \text{action} \,\|\, \text{from\_status} \,\|\, \text{to\_status} \,\|\, \text{timestamp})$$

Any manual row modification, status overwrite, or malicious tampering in the database breaks the mathematical chain instantly and is surfaced in the audit inspector:
```
[DEMO] Tampering Row: Overwriting Event #2 to_status = 'ORDER_PAID'...
[VERIFY] Chain Broken at Event #3!
         Stored prev_hash:   d4f291a...
         Calculated hash:    a8b91c0...
         Result: TAMPER DETECTED!
```

### 4. 15-State High-Integrity Transaction State Machine
Transitions are locked by strict formal verification rules:
`DISCOVERED` $\rightarrow$ `SELECTED` $\rightarrow$ `OFFER_CREATED` $\rightarrow$ `NEGOTIATING` $\rightarrow$ `OFFER_ACCEPTED` $\rightarrow$ `CONSENT_REQUIRED` $\rightarrow$ `CONSENT_RECEIVED` $\rightarrow$ `ORDER_CREATED` $\rightarrow$ `PAYMENT_PENDING` $\rightarrow$ `PAYMENT_AUTHORIZED` $\rightarrow$ `PAYMENT_CAPTURED` $\rightarrow$ `ORDER_PAID` $\rightarrow$ `FULFILLED`  
*(Terminal failure states: `PAYMENT_FAILED`, `CANCELLED`)*

### 5. Production Razorpay Test-Mode Settlement & Distributed Locking
* **Atomic Inventory Locking**: Protected by Redis-backed distributed mutex locks (`aioredis`) to eliminate race conditions under concurrent buyer checkouts.
* **Webhook Idempotency**: Razorpay webhooks are processed asynchronously via RQ background workers, deduplicating repetitive webhook deliveries.
* **HMAC-SHA256 Verification**: Server-side cryptographic signature verification on all Razorpay payments.

---

## 📊 Live Screenshots & UI Showcase

| Autonomous Buyer Storefront | Merchant Command Center & Negotiation Theater |
|:---:|:---:|
| Conversational AI search with real-time concessions | Live WebSocket event stream, Policy Controls & Audit Ledger |

---

## 🛠️ Technology Stack

| Layer | Technologies |
|---|---|
| **Frontend UI** | Next.js 16 (Turbopack, App Router), React 19, Tailwind CSS, Lucide Icons, WebSocket Client |
| **Backend API** | FastAPI (Python 3.10), Uvicorn, Pydantic v2 Settings |
| **Database & Cache** | PostgreSQL (SQLAlchemy 2.0 Async, Psycopg2), Redis 7, Redis Queue (RQ) |
| **Generative AI** | Google Gemini REST API (`gemini-2.5-flash`), OpenAI API (`gpt-4o-mini`) |
| **Fintech Engine** | Razorpay Test Mode API, HMAC-SHA256 Cryptography, SHA-256 Hash Chaining |
| **Cloud Hosting** | Vercel (Frontend Edge), Railway (Backend Container + Managed DBs) |

---

## 🧪 Chaos & Verification Test Suite

The repository includes standalone, verifiable test scripts proving every security and edge-case property:

### 1. Cryptographic Hash Chain Tamper Detection
```powershell
python backend/scripts/demo_hash_chain.py
```
*Creates an order, generates 4 hashed events, modifies event payload via direct raw SQL, and proves `verify_order_chain()` flags the exact broken event.*

### 2. Live Merchant Policy Update & Enforcement
```powershell
python backend/scripts/demo_policy_update.py
```
*Updates policy bounds via `PATCH /policies/{id}`, attempts an out-of-bounds agent discount, and shows immediate `FinancialActionGuard` rejection.*

### 3. Edge-Case & Chaos Suite
```powershell
python backend/scripts/demo_failure_handling.py
```
*Simulates 3 failure modes:*
1. **Offer TTL Expiry**: Rejects payment attempt after timer expiration.
2. **Concurrent Inventory Race**: 2 buyer agents attempt to buy 1 item simultaneously; Redis mutex grants 1 and rejects the 2nd with HTTP 409.
3. **Webhook Idempotency**: Duplicate webhook payloads processed with zero duplicate status transitions.

---

## 🚦 Local Quickstart Guide

### Prerequisites
* Python 3.10+
* Node.js 18+ & npm
* Docker & Docker Compose

### 1. Clone the Repository
```bash
git clone https://github.com/KarthikManuru/Dual-Agent-Commerce-Mesh.git
cd Dual-Agent-Commerce-Mesh
```

### 2. Start PostgreSQL & Redis
```bash
docker-compose up -d
```

### 3. Backend Setup
```bash
cd backend
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
cp ../.env.example .env
# Edit .env with your Razorpay and OpenAI/Gemini keys
alembic upgrade head
python scripts/seed.py
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### 4. Frontend Setup
```bash
cd ../frontend
npm install
npm run dev
```

Visit **`http://localhost:3000`** for the Storefront and **`http://localhost:3000/dashboard`** for the Command Center!

---

## 📑 Protocol Specification (`/.well-known/ai-commerce`)

Any external AI buyer agent can autonomously discover this merchant's capabilities by querying the standard manifest:

```json
{
  "manifest_version": "1.0.0",
  "mesh_standard": "Dual-Agent Autonomous Commerce Protocol (DA-ACP)",
  "merchant": {
    "merchant_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "name": "TechMesh Electronics",
    "settlement_currency": "INR",
    "capabilities": [
      "AUTONOMOUS_PRICE_NEGOTIATION",
      "COMPLEMENTARY_CROSS_SELL_BUNDLING",
      "DYNAMIC_VOLUME_DISCOUNTING",
      "DETERMINISTIC_FINANCIAL_GUARD",
      "REALTIME_WEBSOCKET_TELEMETRY",
      "CRYPTOGRAPHIC_AUDIT_LOGGING"
    ]
  },
  "endpoints": {
    "catalog": "/products",
    "conversational_chat": "/sessions/chat",
    "direct_negotiation": "/sessions/negotiate",
    "order_creation": "/orders",
    "order_verification": "/orders/{order_id}/verify",
    "realtime_events_ws": "/ws/orders"
  }
}
```

---

## 👥 Authors & License

* Built for **AI Growth & Agentic Commerce Hackathon 2026**
* Developed by **Karthik Manuru**
* Licensed under the **MIT License**.