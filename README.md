# AgentPay Guard

> **A local-first zero-trust consent and authorization firewall for autonomous AI agent commerce.**  
> *AI agents discover & propose. AgentPay Guard evaluates & obtains consent. Razorpay executes.*

[![Razorpay Powered](https://img.shields.io/badge/Razorpay-Payment%20Execution-blue?logo=razorpay&logoColor=white)](https://razorpay.com)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Next.js 14](https://img.shields.io/badge/Next.js-14%20App%20Router-black?logo=next.js&logoColor=white)](https://nextjs.org)
[![Android Compose](https://img.shields.io/badge/Android-Kotlin%20%7C%20Compose%20%7C%20Room-3DDC84?logo=android&logoColor=white)](https://developer.android.com)
[![MCP Protocol](https://img.shields.io/badge/MCP-Model%20Context%20Protocol-purple)](https://modelcontextprotocol.io)
[![Scikit-Learn](https://img.shields.io/badge/ML-Scikit--Learn-F7931E?logo=scikit-learn&logoColor=white)](https://scikit-learn.org)
[![License MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

## The Problem & Inspiration

As autonomous AI agents (ChatGPT, Claude, Gemini, AutoGPT) evolve from research assistants into economic actors capable of booking travel, buying cloud resources, and shopping online, **agentic commerce** introduces unprecedented financial and security risks:

- **Uncontrolled Spending Loops**: Autonomous agents executing repeated unauthorized transactions without human oversight.
- **Prompt Injection Hijacks**: Malicious websites or inputs manipulating LLMs into making unauthorized wire transfers or buying fraudulent gift cards.
- **Micro-Splitting Evasion**: Smart agents attempting to bypass spending limits by breaking large orders into multiple smaller requests in rapid succession.
- **Context-Blind Gateways**: Traditional payment gateways (Razorpay, Stripe) only see payment credentials—they have zero awareness of agent identity, prompt intent, or user budget constraints.

---

## The Solution

**AgentPay Guard** acts as an interceptive zero-trust security firewall and local consent anchor positioned directly between autonomous AI agents and payment execution gateways.

When an AI agent requests a transaction via MCP tools or ChatGPT Actions:
1. **Interception**: AgentPay Guard intercepts the request before any funds or card tokens are exposed.
2. **Deterministic & ML Risk Evaluation**: Evaluates request parameters against a 12-step deterministic rule hierarchy combined with real-time ML risk scoring and micro-splitting anomaly detection.
3. **Hardware-Backed Human Consent**: Routes requests requiring user approval to an offline-first Android device signed via Android Keystore hardware keys or to the Web Control Plane.
4. **Scoped Razorpay Execution**: Upon approval, issues a single-use, 5-minute cryptographic authorization token allowing Razorpay to execute the transaction safely.

---

## System Architecture

![System Architecture](./docs/architecture.png)




## Key Features

- **Phone as the Trust Anchor (Android App)**: Built with an offline-first local decision engine, Android Keystore hardware signing, Room database storage, and low-latency push notifications with 1-tap **Accept / Reject** quick actions.
- **Deterministic & ML Hybrid Engine**: Combines a strict 12-step deterministic rule chain (synchronized identically in Python, TypeScript, and Kotlin) with GradientBoosting transaction risk scoring and IsolationForest behavior anomaly detection.
- **Circumvention & Micro-Splitting Defense**: Stateful session correlation engine detects agents attempting to bypass transaction limits by splitting large purchases into multiple smaller requests.
- **Scoped Razorpay Integration**: Authorizations expire in 300 seconds, are single-use, and tightly bound to merchant, product, and amount. Replay attacks are cryptographically and statefully rejected.
- **Native MCP & ChatGPT Action Support**: Includes Model Context Protocol (MCP) servers and OpenAPI 3.1 schema specs for plug-and-play integration with Custom GPTs, Claude Desktop, and LangChain/LlamaIndex agents.
- **Real-Time Control Plane & Replay Audit**: Next.js 14 control plane with WebSocket live events, active policy management, risk telemetry, and step-by-step forensic audit timelines for every transaction.



## Tech Stack

| Domain | Technology / Framework | Usage |
|---|---|---|
| **Control Plane (Web)** | Next.js 14 · TypeScript · Tailwind CSS · Recharts | Management dashboard, real-time approvals, policy editor, risk console, and forensic replay |
| **Backend & Core API** | FastAPI · Pydantic v2 · Uvicorn · WebSockets · Python 3.11 | Core REST API, 12-step decision engine, Razorpay Orders API, webhook handler, live WebSockets |
| **Mobile Anchor** | Kotlin · Jetpack Compose · Room DB · Android Keystore | Hardware trust anchor, offline-first local decision engine, hardware key signing, push notifications |
| **AI / ML Risk Engine** | PyTorch / Scikit-Learn · Pandas · NumPy | GradientBoosting risk classifier, IsolationForest anomaly detector, 10k synthetic request dataset |
| **Agent Protocols** | Model Context Protocol (MCP) · OpenAPI 3.1 | Remote & embedded MCP server (`request_payment`, `check_payment_status`), ChatGPT Action spec |
| **Payment Gateway** | Razorpay Orders API & Webhook API | Production & high-fidelity simulated Razorpay payment execution and verification |

---

## Quick Start Guide

### Prerequisites
- **Python 3.11+**
- **Node.js 18+** & `npm`
- *(Optional)* **Android Studio Koala+** for mobile anchor build

---

### All-in-One Launcher (Recommended)

Run the complete AgentPay Guard stack (Backend API, MCP Server, Web Dashboard, and ngrok Tunnel) with a single command:

```bash
chmod +x scripts/*.sh
./scripts/start.sh
```

**Services Launched:**
- **Backend API & Swagger Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Standalone MCP Server**: [http://localhost:8002/mcp](http://localhost:8002/mcp)
- **Web Dashboard**: [http://localhost:3000](http://localhost:3000)
- **ngrok Tunnel Dashboard**: [http://localhost:4040](http://localhost:4040)

*For step-by-step manual component commands, ML pipeline training, and Android setup, see [`docs/setup.md`](./docs/setup.md).*

---

## Comprehensive Documentation

Complete project documentation is available in the [`docs/`](./docs) directory:

- **[`docs/architecture.md`](./docs/architecture.md)**: Deep dive into the 12-step decision engine, cryptographic token lifecycle, threat matrix, and security model.
- **[`docs/setup.md`](./docs/setup.md)**: Complete step-by-step setup guide for developers, judges, and deployment environments.
- **[`docs/api.md`](./docs/api.md)**: Complete REST API endpoints, WebSocket event contracts, and MCP tool definitions.
- **[`docs/user-guide.md`](./docs/user-guide.md)**: Step-by-step instructions for managing agents, setting budget policies, and handling approvals.

