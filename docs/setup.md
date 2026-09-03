# Setup & Installation Guide — AgentPay Guard

> **Step-by-step instructions to install, configure, and run the AgentPay Guard stack locally.**

---

## System Requirements & Prerequisites

Before setting up AgentPay Guard, ensure you have the following installed on your machine:

| Software / Tool | Minimum Version | Recommended Version | Note |
|---|---|---|---|
| **Python** | 3.10+ | 3.11 / 3.12 | Required for Backend, ML, & MCP Server |
| **Node.js** | 18.0+ | 20.0+ | Required for Web Control Plane (Next.js) |
| **npm** / **yarn** | 9.0+ | 10.0+ | Node package manager |
| **Git** | 2.30+ | Latest | Version control |
| **Android Studio** *(Optional)* | Koala (2024.1+) | Latest | Required only to build/run the Android mobile app |
| **ngrok** *(Optional)* | 3.0+ | Latest | For exposing backend webhooks to live Razorpay callbacks |

---

## Environment Configuration

Copy `.env.example` to `.env` in `src/backend/` or root:

```bash
cp src/backend/.env.example src/backend/.env
```

### Key Environment Variables (`src/backend/.env`)

```env
# Server Port & Binding
PORT=8000
HOST=0.0.0.0

# Public URL (Used for Razorpay callback & checkout redirect)
GUARD_PUBLIC_URL=http://localhost:8000

# Razorpay Credentials (Optional — if omitted, runs in simulated mode)
RAZORPAY_KEY_ID=rzp_test_your_key_id
RAZORPAY_KEY_SECRET=your_key_secret
RAZORPAY_WEBHOOK_SECRET=your_webhook_secret

# Security Policies Defaults
DEFAULT_TRANSACTION_LIMIT=20000
DEFAULT_DAILY_LIMIT=50000
```

> **Note**: If Razorpay API keys are not provided, AgentPay Guard automatically defaults to **High-Fidelity Simulated Mode**, allowing full offline testing of authorizations, orders, and payment captures without real credentials.

---

## Option 1: Quick All-in-One Launch (Recommended)

Run the entire application stack using the automated startup script:

```bash
# Make script executable
chmod +x start.sh

# Run all services
./start.sh
```

### Services Started by `start.sh`:
- **Backend API & Swagger Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **FastMCP Server**: [http://localhost:8002/mcp](http://localhost:8002/mcp)
- **Web Control Plane**: [http://localhost:3000](http://localhost:3000)
- **ngrok Tunnel Dashboard**: [http://localhost:4040](http://localhost:4040) *(if ngrok is installed)*

---

## Option 2: Step-by-Step Manual Setup

### 1. Backend REST API (`src/backend/`)

```bash
# Navigate to backend directory
cd src/backend

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Start backend server with live reload
uvicorn app.main:app --reload --port 8000
```

Verify backend health:
```bash
curl http://localhost:8000/health
# Response: {"status":"healthy","version":"1.0.0"}
```

Run backend smoke test suite:
```bash
python tests/smoke_test.py
```

---

### 2. Web Control Plane (`src/web/`)

```bash
# Navigate to web frontend directory
cd src/web

# Install npm dependencies
npm install

# Start Next.js development server
npm run dev
```

Open your browser at [http://localhost:3000](http://localhost:3000).

---

### 3. MCP Server (`src/mcp/`)

To run the Model Context Protocol (MCP) server for Claude Desktop or AI tools:

```bash
cd src/mcp

# Activate backend virtual environment or install dependencies
source ../backend/.venv/bin/activate

# Run standalone FastMCP server on port 8002
python server.py
```

---

### 4. Agent Simulator (`src/agent/`)

Run shopping agent simulations to test policy enforcement, user approvals, and attack scenarios:

```bash
cd src/agent

# Run all 5 canonical test scenarios
python run_demo.py --api http://localhost:8000 --mode all

# Run specific attack scenario (e.g. split payment circumvention)
python run_demo.py --api http://localhost:8000 --mode split
```

#### Canonical Test Scenarios

| Scenario | Agent | Request Details | Expected Outcome | Guard Reason Code |
|:---|:---|:---|:---:|---|
| **1. Legitimate Purchase** | Claude | Sony WH-1000XM5 (`₹14,499`) | **USER APPROVAL** -> ACCEPT -> **Razorpay Captured** | `AMOUNT_REQUIRES_APPROVAL` |
| **2. Over-Limit Hard Block** | Gemini | MacBook Pro 14 (`₹42,000`) vs `₹20,000` limit | **HARD BLOCK** | `LIMIT_TRANSACTION_EXCEEDED` |
| **3. Micro-Splitting Attack** | Claude | 3 rapid purchases (`₹9,800` + `₹9,700` + `₹9,900`) | **BLOCK ON 3rd TXN** | `CIRCUMVENTION_DETECTED` (Aggregate `₹29,400`) |
| **4. Intent Mismatch** | ChatGPT | User Intent: "Monitor" -> Agent buys Gift Card | **HARD BLOCK** | `CATEGORY_BLOCKED` & `INTENT_MISMATCH` |
| **5. Compromised Agent Burst** | Gemini | 10 rapid requests in 5 seconds | **ANOMALY ALERT** -> **FREEZE AGENT** | `HIGH_VELOCITY_ANOMALY` |

---

### 5. Machine Learning Pipeline (`src/ml/`)

To generate datasets and retrain the risk models:

```bash
cd src/ml

# Install ML dependencies
pip install -r requirements.txt

# 1. Generate 10k synthetic payment requests dataset
python data/generate_dataset.py

# 2. Train GradientBoosting risk model
python training/train_risk_model.py

# 3. Train IsolationForest anomaly detector
python training/train_anomaly_model.py

# 4. Evaluate metrics & circumvention tests
python evaluation/evaluate.py
```

---

### 6. Android Trust Anchor (`src/android/`)

1. Launch **Android Studio**.
2. Select **Open** and choose the `src/android` directory.
3. Allow Gradle sync to complete automatically.
4. Set the `GUARD_API_URL` in `app/build.gradle.kts` (or default `http://10.0.2.2:8000` for Android Emulator).
5. Press **Run (Shift+F10)** to deploy to an Emulator or connected Android device.

---

## Resetting State & Troubleshooting

### Reset Application State
If you want to clear stored transactions, pending requests, and reset policies to seed defaults:

```bash
chmod +x reset-state.sh
./reset-state.sh
```

### Next.js Cache Issues
If the web UI shows compilation errors or stale pages:
```bash
cd src/web
rm -rf .next
npm run dev
```

### Port Conflicts
If ports `8000` or `3000` are already occupied:
```bash
# Check running processes
lsof -i :8000
lsof -i :3000

# Kill process if necessary
kill -9 <PID>
```
