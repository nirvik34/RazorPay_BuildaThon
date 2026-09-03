# User Guide — AgentPay Guard

> **How to configure, monitor, and control AI agent payments with AgentPay Guard.**

---

## Introduction

As AI agents act autonomously to search, negotiate, and purchase items on your behalf, **AgentPay Guard** ensures that no money ever leaves your account without your explicit permission and rule compliance.

This guide walks you through navigating the **Web Control Plane**, managing **Policy Guardrails**, approving **Pending Requests**, controlling **Agent Access**, and connecting **AI Assistants** (Claude, Custom GPTs) via MCP.

---

## 1. Navigating the Web Control Plane

The web interface runs locally at `http://localhost:3000`.

```
+-------------------------------------------------------------------+
|  [Shield] AgentPay Guard    Dashboard   Approvals (1)  Settings   |
+-------------------------------------------------------------------+
|  Today's Spend    Pending Approvals    Active Agents    Blocked   |
|     ₹14,499              1                   3             2      |
+-------------------------------------------------------------------+
|  Recent AI Activity                     7-Day Spend Chart         |
|  [01:09] Claude - Sony WH-1000XM5      [=== Area Chart ===]       |
+-------------------------------------------------------------------+
```

### Executive Dashboard (`/`)
- **Today's Spend**: Displays total INR amount of successfully **CAPTURED** payments completed today.
- **Pending Approvals**: Shows requests requiring human intervention. Highlighted in amber when action is needed.
- **Active Agents**: Count of currently authorized AI agents.
- **Blocked Actions**: Count of automated hard blocks enforced by security policies.
- **7-Day Delegated Spend Chart**: Visual trend of daily agent expenditures.

---

## 2. Approving & Rejecting Requests (`/approvals`)

When an AI agent requests a purchase that meets user-approval criteria (e.g. unknown merchant, high amount, or new category), it enters the **Approvals Queue**.

```
+-------------------------------------------------------------------+
|  PENDING REQUEST #req_f82910                                       |
|  Agent: Claude Shopping Agent                                      |
|  Item: Sony WH-1000XM5 Wireless Headphones                        |
|  Amount: ₹14,499  | Merchant: Amazon | Category: Electronics    |
|  Reason: New merchant requires review                             |
|                                                                   |
|  [ ACCEPT & AUTHORIZE ]                  [ REJECT & BLOCK ]       |
|  Expires in 04:32                                                 |
+-------------------------------------------------------------------+
```

### Step-by-Step Approval Process:
1. **Review Request Details**: Inspect the agent ID, merchant, product name, amount, category, and trigger reason code.
2. **Accept & Authorize**:
   - Click **Accept**.
   - Guard issues a 5-minute single-use authorization token (`auth_xxxxxx`).
   - The payment modal or agent checkout proceeds directly to **Razorpay**.
3. **Reject**:
   - Click **Reject**.
   - The transaction is immediately canceled and logged as `DENIED`. The agent receives a clear rejection code.
4. **Auto-Expiration**:
   - Requests not acted upon within **5 minutes (300 seconds)** automatically expire to prevent stale background charges.

---

## 3. Configuring Security Policies (`/settings`)

You can set strict monetary limits and category rules in the Policy Settings:

```
+-------------------------------------------------------------------+
|  POLICY GUARDRAILS (v1)                                           |
|                                                                   |
|  Single Transaction Limit:  [ ₹20,000 ]                            |
|  Daily Spend Cap:           [ ₹50,000 ]                            |
|  Monthly Limit:             [ ₹1,50,000 ]                          |
|                                                                   |
|  Blocked Categories:  [ gambling, crypto, adult ]                 |
|  Blocked Merchants:   [ untrusted_store_x ]                       |
|                                                                   |
|  Approval Thresholds:                                             |
|  - Require review for purchases above: [ ₹10,000 ]                 |
|  - Require review for new/unknown merchants: [ ENABLED ]          |
|  - Require review for ML high-risk transactions: [ ENABLED ]      |
+-------------------------------------------------------------------+
```

### Policy Rules Hierarchy:
- **Transaction Limit**: Any single purchase above this amount is **HARD BLOCKED**.
- **Daily Spend Cap**: Sum of today's approved spend cannot exceed this threshold.
- **Blocklists**: Instant rejection if category or merchant matches your blocklist.
- **Approval Rules**: Define when requests must pause for human review instead of auto-approving.

---

## 4. Agent Access & Emergency Controls (`/agents`)

You maintain full control over individual AI agent permissions:

```
+-------------------------------------------------------------------+
|  AGENT MANAGEMENT                                                 |
|                                                                   |
|  1. Claude Shopping Assistant                                     |
|     Status: ACTIVE | Spend Today: ₹14,499 | Txns: 3               |
|     [ FREEZE AGENT ]  [ REVOKE ACCESS ]                           |
|                                                                   |
|  2. Gemini Bargain Bot                                            |
|     Status: FROZEN | Reason: 10 rapid burst requests detected    |
|     [ UNFREEZE ]      [ REVOKE ACCESS ]                           |
+-------------------------------------------------------------------+
```

### Agent Controls:
- **FREEZE**: Temporarily pauses all payment requests from the agent. Useful if an agent is behaving erratically.
- **UNFREEZE**: Restores active agent status.
- **REVOKE**: Permanently revokes agent authorization. All future requests are hard-blocked (`AGENT_REVOKED`).

---

## 5. Forensic Audit & Replay Timeline (`/activity` & `/audit/[id]`)

Click any transaction in the activity table to view its line-by-line decision timeline:

```
TIMELINE FOR REQUEST #req_f82910
---------------------------------------------------------------------
10:09:01 AM  [AGENT_REQUEST]    Received purchase request from Claude
10:09:01 AM  [POLICY_EVALUATE]  12-step decision engine execution started
10:09:01 AM  [CHECK_PASSED]     Single limit ₹14,499 <= ₹20,000 (Pass)
10:09:01 AM  [TRIGGER_RULE]     New merchant 'amazon' requires review
10:09:01 AM  [PAUSED]           Status set to USER_APPROVAL
10:09:45 AM  [USER_ACCEPT]      User approved request via Web Dashboard
10:09:45 AM  [AUTH_ISSUED]      Issued auth_72b1a9 (Expires in 300s)
10:10:02 AM  [RAZORPAY_CAPTURE] Payment pay_Kx910a captured successfully
```

---

## 6. Mobile App (Android Trust Anchor)

Using the **AgentPay Guard Android App**:

1. **Push Notifications**: Receive instant alerts on your phone whenever an approval is requested.
2. **1-Tap Quick Actions**: Approve or reject transactions directly from notification banners or lock screen.
3. **Hardware Signing**: Approvals generated on your Android device are cryptographically signed using `AndroidKeyStore`.
4. **Offline Sync**: Policy snapshots are saved locally using Room DB; pending items automatically sync when internet connection re-establishes.

---

## 7. Connecting AI Assistants via MCP

### Claude Desktop Integration

Add AgentPay Guard to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "agentpay-guard": {
      "command": "python",
      "args": ["/path/to/razorpay/src/mcp/server.py"]
    }
  }
}
```

Now you can ask Claude Desktop:
> *"Buy a Logitech MX Master 3S mouse on Amazon for me."*

Claude will invoke the `request_payment` tool, and AgentPay Guard will evaluate the purchase, triggering an approval request on your phone/web console!
