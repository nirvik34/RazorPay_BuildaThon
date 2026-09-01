# Backend API Reference — AgentPay Guard

> **Interactive Swagger OpenAPI docs are served at `http://localhost:8000/docs`.**

---

## Overview & Base URL

- **Base URL**: `http://localhost:8000`
- **Content-Type**: `application/json`
- **Authentication**: Zero-Trust Scoped Tokens & HMAC Signatures for Webhooks.

---

## 1. Core & Health

### `GET /health`
Returns the operational status of the AgentPay Guard backend server.

**Response `200 OK`**:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "mode": "simulated"
}
```

---

## 2. Agent Interception Endpoints

### `POST /agents/register`
Registers a new autonomous AI agent with AgentPay Guard.

**Request Body**:
```json
{
  "name": "Claude Shopping Agent",
  "description": "Assistant for electronics purchase",
  "status": "ACTIVE"
}
```

**Response `200 OK`**:
```json
{
  "agentId": "agent_c81f3a",
  "name": "Claude Shopping Agent",
  "status": "ACTIVE",
  "registeredAt": "2026-09-02T01:00:00Z"
}
```

---

### `POST /intents`
Registers a delegated user shopping intent (used for intent boundary verification).

**Request Body**:
```json
{
  "agentId": "agent_c81f3a",
  "category": "electronics",
  "budgetLimit": 15000,
  "description": "Buy a wireless headphone under ₹15,000"
}
```

**Response `200 OK`**:
```json
{
  "intentId": "intent_a92b4c",
  "agentId": "agent_c81f3a",
  "category": "electronics",
  "budgetLimit": 15000,
  "status": "ACTIVE"
}
```

---

### `POST /payment-request`
Intercepts an agent payment attempt and runs the **12-Step Hybrid Policy Engine**.

**Request Body**:
```json
{
  "agentId": "agent_c81f3a",
  "merchant": "amazon",
  "product": "Sony WH-1000XM5 Headphones",
  "amount": 14499,
  "currency": "INR",
  "category": "electronics",
  "intentId": "intent_a92b4c"
}
```

**Response `200 OK` (Policy ALLOW / AUTO_APPROVED)**:
```json
{
  "requestId": "req_f82910",
  "decision": "ALLOW",
  "reasonCodes": [
    {
      "code": "AUTO_APPROVED",
      "severity": "info",
      "label": "All policy checks passed"
    }
  ],
  "authorizationId": "auth_91a0c2",
  "expiresAt": "2026-09-02T01:05:00Z"
}
```

**Response `200 OK` (USER_APPROVAL Required)**:
```json
{
  "requestId": "req_f82910",
  "decision": "USER_APPROVAL",
  "reasonCodes": [
    {
      "code": "NEW_MERCHANT",
      "severity": "warn",
      "label": "New merchant requires user review"
    }
  ],
  "message": "Payment paused. Awaiting mobile/web user approval."
}
```

**Response `200 OK` (Policy HARD BLOCK)**:
```json
{
  "requestId": "req_f82910",
  "decision": "BLOCK",
  "reasonCodes": [
    {
      "code": "LIMIT_TRANSACTION_EXCEEDED",
      "severity": "block",
      "label": "₹42,000 exceeds ₹20,000 transaction limit"
    }
  ]
}
```

---

## 3. Human Consent & Guard Endpoints

### `GET /guard/pending`
Lists all pending payment requests awaiting user decision. Auto-expires requests older than 5 minutes.

**Response `200 OK`**:
```json
[
  {
    "request": {
      "requestId": "req_f82910",
      "agentId": "agent_c81f3a",
      "merchant": "amazon",
      "product": "Sony WH-1000XM5",
      "amount": 14499,
      "timestamp": "2026-09-02T01:09:00Z"
    },
    "decision": {
      "decision": "USER_APPROVAL",
      "reasonCodes": [{"code": "NEW_MERCHANT", "label": "New merchant review"}]
    }
  }
]
```

---

### `POST /guard/approvals/{request_id}/action`
Processes user consent action (**accept** or **reject**) from mobile or web interface.

**Request Body**:
```json
{
  "action": "accept"
}
```

**Response `200 OK` (Accepted)**:
```json
{
  "ok": true,
  "decision": "AUTHORIZED",
  "authorization": {
    "authorizationId": "auth_72b1a9",
    "requestId": "req_f82910",
    "agentId": "agent_c81f3a",
    "amount": 14499,
    "expiresAt": "2026-09-02T01:14:00Z",
    "status": "AUTHORIZED"
  }
}
```

---

### `POST /guard/execute`
Executes an authorized transaction by generating a Razorpay Order and Checkout link.

**Request Body**:
```json
{
  "authorizationId": "auth_72b1a9"
}
```

**Response `200 OK`**:
```json
{
  "ok": true,
  "orderId": "order_Nz19aK019s",
  "checkoutUrl": "http://localhost:8000/guard/checkout/auth_72b1a9",
  "status": "ORDER_CREATED"
}
```

---

### `POST /guard/payments/razorpay/callback`
Server-side callback to verify Razorpay checkout signatures and capture payment.

**Request Body**:
```json
{
  "authorizationId": "auth_72b1a9",
  "razorpay_payment_id": "pay_Kx910aBcDe",
  "razorpay_order_id": "order_Nz19aK019s",
  "razorpay_signature": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
}
```

**Response `200 OK`**:
```json
{
  "ok": true,
  "status": "CAPTURED",
  "paymentId": "pay_Kx910aBcDe",
  "amount": 14499
}
```

---

## 4. Control Plane & Data Endpoints

### `GET /transactions`
Fetches all transaction records, including request payload, policy decision, reason codes, and final outcome (`CAPTURED`, `PROCESSING`, `DENIED`, `NOT_ATTEMPTED`).

**Response `200 OK`**:
```json
{
  "transactions": [
    {
      "request": {
        "requestId": "req_f82910",
        "agentId": "agent_c81f3a",
        "merchant": "amazon",
        "product": "Sony WH-1000XM5",
        "amount": 14499
      },
      "decision": {
        "decision": "USER_APPROVAL"
      },
      "outcome": "CAPTURED"
    }
  ]
}
```

---

### `GET /policies` & `PUT /policies/{policy_id}`
Get or update active security rules.

**PUT Request Body**:
```json
{
  "transactionLimit": 25000,
  "dailyLimit": 60000,
  "blockedCategories": ["gambling", "crypto"],
  "blockedMerchants": ["untrusted_store"]
}
```

---

### `GET /audit/{request_id}`
Retrieves the step-by-step forensic audit timeline for a given transaction request ID.

---

## 5. WebSocket Live Events

### `WS /ws/events`
Real-time event feed for web console and mobile sync.

**Event Types Broadcasted**:
- `transaction_created` — New agent payment request received.
- `approvals_updated` — Pending queue state updated.
- `payment_captured` — Payment successfully executed via Razorpay.
- `agent_status_changed` — Agent status modified (ACTIVE / FROZEN / REVOKED).
