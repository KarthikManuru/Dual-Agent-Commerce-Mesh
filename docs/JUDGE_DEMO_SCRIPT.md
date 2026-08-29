# 🎯 Judge Demo Walkthrough & Live Rehearsal Script

> **Dual-Agent Autonomous Commerce Mesh**  
> *Target Duration: 4–6 Minutes Live Presentation*

---

## 📋 Pre-Demo Setup (10 Seconds Before Presentation)

Open two terminal windows:

### Terminal 1: Backend Server (FastAPI)
```powershell
cd "c:\Users\Karth\Desktop\Dual-Agent Commerce Mesh\backend"
.\venv\Scripts\uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### Terminal 2: Frontend App (Next.js 16.3.2)
```powershell
cd "c:\Users\Karth\Desktop\Dual-Agent Commerce Mesh\frontend"
npm run dev
```

---

## 🎬 Live Walkthrough Steps

### 1️⃣ Tab 1 — Autonomous Buyer Storefront (1 Minute)
* **URL**: [http://localhost:3000](http://localhost:3000)
* **Action**:
  1. In the top conversational search bar, type:
     > *"Find me ANC headphones under 3000"*
  2. Click **"Ask AI Agent"** (or click **"Auto-Negotiate"** on the *ClearTalk Pro* card).
* **What to Say**:
  > *"Here is the autonomous buyer storefront. The user specifies what they want in natural language. Instead of a dumb search, the Buyer Agent matches products, evaluates competitive market alternatives, and enters dynamic negotiation with the Merchant Agent in real time."*
* **Highlight on Screen**:
  * Point to the live concession badges and the **`[LLM:gemini-3.6-flash]`** telemetry tag proving real-time multi-turn generative AI reasoning.
  * Show the bundled perk offered by the merchant (*e.g., 6 months extended warranty*).
  * Click **"Proceed to Razorpay Checkout"** to show real Test Mode modal.

---

### 2️⃣ Tab 2 — Merchant Command Center & Dynamic Policy Controls (1.5 Minutes)
* **URL**: [http://localhost:3000/dashboard](http://localhost:3000/dashboard)
* **Action**:
  1. Point out the **Live Negotiation Theater** updating in real time via WebSockets.
  2. Scroll to the **Merchant Guard Policy Controls** card. Change *Max Discount (%)* from `15` to `18`, and click **"Save Policy"**.
  3. Show the instant green confirmation badge: `✓ Policy bounds updated & enforced live!`.
* **What to Say**:
  > *"On the Merchant side, the Command Center streams live agent bargaining. Crucially, merchants set deterministic bounds — maximum discount ceilings, minimum profit margins, round limits, and offer time-to-live. Every agent turn is gated by our `FinancialActionGuard` before a single rupee can be committed."*

---

### 3️⃣ Terminal Verification — Cryptographic Audit Trail & Tamper Detection (1 Minute)
* **Action**: Run the SHA-256 tamper detection test in PowerShell:
  ```powershell
  cd "c:\Users\Karth\Desktop\Dual-Agent Commerce Mesh\backend"
  .\venv\Scripts\python scripts/demo_hash_chain.py
  ```
* **What to Say**:
  > *"Every single state transition and agent action is recorded into a cryptographic SHA-256 hash-chained audit ledger. To prove this is tamper-evident, this test script creates an order, validates the chain, and then executes a raw SQL update directly on the PostgreSQL database to simulate a malicious database breach. Notice how the verification engine instantly catches the tampered row with the exact broken event ID and mismatched hash."*

---

### 4️⃣ Terminal Verification — Concurrency Race & Failure Resilience (1.5 Minutes)
* **Action**: Run the live 6-scenario failure suite:
  ```powershell
  cd "c:\Users\Karth\Desktop\Dual-Agent Commerce Mesh\backend"
  .\venv\Scripts\python scripts/demo_failure_handling.py
  ```
* **What to Say**:
  > *"Finally, here is our full failure and concurrency resilience proof covering 6 critical production failure scenarios:"*
  1. **Concurrent 1-Stock Flash Race**: Two simultaneous requests fire at 1 unit of stock; PostgreSQL atomic conditional row locks ensure exactly 1 buyer wins and the other is gracefully rejected.
  2. **Price Tamper Resistance**: An attacker submitting `₹1.00` in the payload is overridden by server-side database truth.
  3. **Duplicate Webhook Idempotency**: Replayed webhook payloads return `ignored_duplicate` without duplicate transitions.
  4. **Illegal State Jump Rejection**: Direct jumps like `DISCOVERED -> FULFILLED` are strictly blocked by the 15-state Finite State Machine.
  5. **Policy Guard Violation**: A 25% discount concession is deterministically denied against the 15% merchant cap.
  6. **Offer TTL Expiration**: Checkout attempts against stale, expired offers are rejected immediately.

---

### 5️⃣ Machine-to-Machine Discovery (30 Seconds)
* **URL**: [http://127.0.0.1:8000/.well-known/ai-commerce](http://127.0.0.1:8000/.well-known/ai-commerce)
* **What to Say**:
  > *"External autonomous shopping agents can discover our store capabilities, machine-readable catalog (`/ai/catalog`), and negotiation policies (`/ai/policies`) through standard discovery endpoints, creating an interoperable agentic commerce mesh."*
