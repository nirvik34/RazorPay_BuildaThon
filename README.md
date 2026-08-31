# AgentPay Guard

> **A local-first consent and authorization boundary for agentic commerce.**  
> *AI agents discover & propose. AgentPay Guard evaluates & obtains consent. Razorpay executes.*

[![Razorpay Powered](https://img.shields.io/badge/Razorpay-Payment%20Execution-blue?logo=razorpay&logoColor=white)](https://razorpay.com)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Next.js 14](https://img.shields.io/badge/Next.js-14%20App%20Router-black?logo=next.js&logoColor=white)](https://nextjs.org)
[![Android Compose](https://img.shields.io/badge/Android-Kotlin%20%7C%20Compose%20%7C%20Room-3DDC84?logo=android&logoColor=white)](https://developer.android.com)
[![MCP Protocol](https://img.shields.io/badge/MCP-Model%20Context%20Protocol-purple)](https://modelcontextprotocol.io)
[![Scikit-Learn](https://img.shields.io/badge/ML-Scikit--Learn-F7931E?logo=scikit-learn&logoColor=white)](https://scikit-learn.org)
[![License MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

## Executive Summary

As autonomous AI agents (ChatGPT, Claude, Gemini) transition from recommendation to execution, **agentic commerce** introduces critical financial and security risks: rogue spending loops, prompt injection hijacks, vendor spoofing, and boundary evasion.

**AgentPay Guard** is an end-to-end zero-trust security firewall and local consent anchor designed for AI payment authorization. Whenever an autonomous agent attempts a financial transaction, AgentPay Guard interceptively evaluates the request against **identity, intent, policy rules, ML risk scores, and multi-request circumvention patterns**.

Upon user approval (via mobile notification or web console), AgentPay Guard issues a **scoped, single-use, 5-minute cryptographic authorization token** that authorizes **Razorpay** to process payment execution securely.

---

## Key Highlights & Innovation

- **Phone as the Trust Anchor (Android App)**: Built with an offline-first local decision engine, Android Keystore hardware signing, Room database storage, and low-latency push notifications with 1-tap **Accept / Reject** quick actions.
- **Deterministic & ML Hybrid Engine**: Combines a strict 12-step deterministic rule chain (synchronized identically in Python, TypeScript, and Kotlin) with GradientBoosting transaction risk scoring and IsolationForest behavior anomaly detection.
- **Circumvention & Micro-Splitting Defense**: Stateful session correlation engine detects agents attempting to bypass transaction limits by splitting large purchases into multiple smaller requests.
- **Scoped Razorpay Integration**: Authorizations expire in 300 seconds, are single-use, and tightly bound to merchant, product, and amount. Replay attacks are cryptographically and statefully rejected.
- **Native MCP & ChatGPT Action Support**: Includes Model Context Protocol (MCP) servers and OpenAPI 3.1 schema specs for seamless plug-and-play integration with Custom GPTs, Claude Desktop, and LangChain/LlamaIndex agents.
- **Real-Time Control Plane & Replay Audit**: Next.js 14 control plane with WebSocket live events, active policy management, risk telemetry, and step-by-step forensic audit timelines for every transaction.

---

## System Architecture & Data Flow

![System Architecture](./docs/architecture.png)


---

## Repository Structure & Stack Map

| Component | Technology Stack | Description | Directory |
|---|---|---|---|
| **Control Plane** | Next.js 14 · TypeScript · Tailwind CSS · Recharts | Management dashboard, real-time approvals queue, policy editor, agent risk console, simulation, & forensic audit replay | [`src/web/`](./src/web) |
| **API & Core** | FastAPI · Pydantic v2 · Uvicorn · WebSockets | Core REST API, decision engine, Razorpay Orders API integration, webhook handler, and live WebSocket streaming | [`src/backend/`](./src/backend) |
| **Mobile Anchor** | Kotlin · Jetpack Compose · Room · Android Keystore | Offline-first local decision engine, hardware key signing, push notifications with inline Accept/Reject quick actions | [`src/android/`](./src/android) |
| **Agent Simulator**| Python (stdlib-only) | Deterministic shopping-agent simulator supporting normal purchases and 5 attack scenario modes | [`src/agent/`](./src/agent) |
| **ML Engine** | PyTorch / Scikit-learn · Pandas · NumPy | 10k synthetic request dataset generator, GradientBoosting risk model, IsolationForest anomaly detector, & circumvention tests | [`src/ml/`](./src/ml) |
| **MCP Server** | Python · FastMCP · Model Context Protocol | Remote & embedded MCP server exposing `request_payment` and `check_payment_status` tools to LLM agents | [`src/mcp/`](./src/mcp) |

> **Shared Technical Specification**: [`src/SPEC.md`](./src/SPEC.md) — Data contracts, 12-step decision hierarchy, design system tokens, and canonical seed story.

---

## Decision Engine Rules Hierarchy

The Guard evaluates every payment request using a deterministic 12-step decision chain synchronized across TypeScript, Python, and Kotlin engines:

| Step | Check Name | Condition | Result | Reason Code |
|:---:|---|---|:---:|---|
| **1** | Agent Revocation | `agent.status == REVOKED` | **BLOCK** | `AGENT_REVOKED` |
| **2** | Agent Freeze | `agent.status == FROZEN` | **BLOCK** | `AGENT_FROZEN` |
| **3** | Category Filter | `category in policy.blockedCategories` | **BLOCK** | `CATEGORY_BLOCKED` |
| **4** | Merchant Filter | `merchant in policy.blockedMerchants` | **BLOCK** | `MERCHANT_BLOCKED` |
| **5** | Single Txn Limit | `amount > policy.transactionLimit` | **BLOCK** | `LIMIT_TRANSACTION_EXCEEDED` |
| **6** | Daily Limit | `todayApprovedSpend + amount > policy.dailyLimit` | **BLOCK** | `LIMIT_DAILY_EXCEEDED` |
| **7** | Intent Matching | Severe category/budget deviation | **BLOCK** | `INTENT_MISMATCH` |
| **8** | Circumvention | Multi-request sequence score `≥ 80` | **BLOCK** | `CIRCUMVENTION_DETECTED` |
| **9** | New Merchant | Merchant unknown & `approvalRules.newMerchant` | **USER_APPROVAL** | `NEW_MERCHANT` |
| **10** | High Amount | `amount >= approvalRules.amountAbove` | **USER_APPROVAL** | `AMOUNT_REQUIRES_APPROVAL` |
| **11** | High Risk Level | Risk level `HIGH` or `CRITICAL` | **USER_APPROVAL** | `HIGH_RISK` |
| **12** | Policy Pass | All checks clear | **ALLOW** | `AUTO_APPROVED` |

---

## Quick Start Guide

### Prerequisites
- **Python 3.11+**
- **Node.js 18+** & `npm`
- *(Optional)* **Android Studio Koala+** for mobile app build

---

### Option A: All-in-One Launcher (Recommended)

Run the entire stack (Backend API, MCP Server, Web Dashboard, & ngrok Tunnel) with a single command:

```bash
chmod +x start.sh
./start.sh
```

**Services Launched:**
- **Backend API & Swagger Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Standalone MCP Server**: [http://localhost:8002/mcp](http://localhost:8002/mcp)
- **Web Dashboard**: [http://localhost:3000](http://localhost:3000)
- **ngrok Tunnel Dashboard**: [http://localhost:4040](http://localhost:4040)

---

### Option B: Step-by-Step Manual Setup

#### 1. Backend Server (Port 8000)
```bash
cd src/backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# (Optional) Copy .env.example and add Razorpay Credentials
cp .env.example .env

# Start Backend API
uvicorn app.main:app --reload --port 8000
```
> *Note: If Razorpay keys are omitted, the backend automatically runs in high-fidelity simulated mode.*

Run end-to-end smoke test suite:
```bash
python tests/smoke_test.py
```

#### 2. Web Control Plane (Port 3000)
```bash
cd src/web
npm install
npm run dev
```
Open [http://localhost:3000](http://localhost:3000) in your browser.

#### 3. Agent Shopping Simulator
```bash
cd src/agent
# Run all demo scenarios against live backend
python run_demo.py --api http://localhost:8000 --mode all
```

#### 4. Machine Learning Pipeline
```bash
cd src/ml
pip install -r requirements.txt
python data/generate_dataset.py        # Generate 10k synthetic request dataset
python training/train_risk_model.py    # Train GradientBoosting risk classifier
python training/train_anomaly_model.py # Train IsolationForest anomaly detector
python evaluation/evaluate.py          # Run metrics & circumvention tests
```

#### 5. Android Trust Anchor
Open [`src/android/`](./src/android) in Android Studio, let Gradle sync, and run on an Android Emulator or physical device.

---

## Hackathon Judge Demo Script

Execute these 5 canonical scenarios to evaluate AgentPay Guard in real-time:

| Scenario | Agent | Action / Request | Expected Outcome | Guard Reason |
|:---|:---|:---|:---:|---|
| **1. Legitimate Purchase** | Claude | Sony WH-1000XM5 (`₹14,499`) within `₹15,000` intent | **USER APPROVAL** -> ACCEPT -> **Razorpay Order Captured** | `AMOUNT_REQUIRES_APPROVAL` |
| **2. Over-Limit Hard Block** | Gemini | MacBook Pro 14 (`₹42,000`) vs `₹20,000` limit | **HARD BLOCK** | `LIMIT_TRANSACTION_EXCEEDED` |
| **3. Micro-Splitting Attack** | Claude | 3 rapid purchases: `₹9,800` + `₹9,700` + `₹9,900` at Croma | **BLOCK ON 3rd TXN** | `CIRCUMVENTION_DETECTED` (Aggregate `₹29,400`) |
| **4. Intent Mismatch** | ChatGPT | User Intent: "Monitor" -> Agent buys Amazon Gift Card (`₹5,000`) | **HARD BLOCK** | `CATEGORY_BLOCKED` & `INTENT_MISMATCH` |
| **5. Compromised Agent Burst** | Gemini | 10 rapid transaction requests in 5 seconds | **ANOMALY ALERT** -> **FREEZE AGENT** | `HIGH_VELOCITY_ANOMALY` |

---

## Security Model & Design Principles

1. **Zero Silent Retries**: Blocked transactions log reasons permanently. Agents receive immutable rejection payloads and cannot bypass checks by altering request parameters.
2. **5-Minute Single-Use Token**: Authorizations (`auth_xxxxxx`) expire in 300 seconds and can only be redeemed once via Razorpay Order capture.
3. **Android Hardware Keystore**: Mobile approvals are signed using hardware-backed cryptographic keys (`AndroidKeyStore`), ensuring authorization integrity even if web channels are intercepted.
4. **Local-First & Offline Resilience**: Android app retains full evaluation capabilities offline with Room DB sync when connection restores.
5. **Clear Visual Design System**:
   - **Guard Blue (`#2563EB`)**: System infrastructure & boundaries
   - **Green**: Approved / Captured transactions only
   - **Red**: Hard blocks, frozen agents, & security breaches only
   - **Amber**: Action required / pending user approval
   - **Purple**: AI-generated context & intent tracking

---

## API & MCP Tool Integration

### OpenAPI / ChatGPT Action Spec
Exposed at [`docs/openapi_chatgpt_action.json`](./docs/openapi_chatgpt_action.json) for direct import into Custom GPTs or Action plugins.

### Model Context Protocol (MCP) Tools Exposing Guard:
```json
{
  "tools": [
    {
      "name": "request_payment",
      "description": "Submit a payment request for AgentPay Guard evaluation and user approval.",
      "parameters": ["agent_id", "merchant", "product", "amount", "category", "intent_id"]
    },
    {
      "name": "check_payment_status",
      "description": "Poll status of a pending authorization request until APPROVED or DENIED.",
      "parameters": ["request_id", "wait_seconds"]
    }
  ]
}
```

---

## License

Distributed under the MIT License. See `LICENSE` for details.

---

<p align="center">
Made for the Razorpay Hackathon by Team AgentPay Guard.
</p>
