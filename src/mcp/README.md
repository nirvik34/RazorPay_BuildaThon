# Real AI shopping → Guard → Razorpay (MCP)

This is the **live** integration: you chat about shopping in Claude Desktop (or any MCP
client), the AI actually attempts a purchase, your phone gets an approval notification,
and only your ACCEPT lets the Razorpay payment execute. Blocked purchases return the
policy reason to the agent.

```
You: "buy wireless headphones under ₹15k"
  └─ Claude calls search_products → picks Sony WH-1000XM5 ₹14,499
      └─ Claude calls purchase(product_id)
          └─ MCP server → POST /agent/payment-request
              └─ Guard evaluates (policy/risk/circumvention)
                  ├─ BLOCK  → agent told immediately, no payment attempted
                  └─ USER_APPROVAL → your phone notification (ACCEPT / REJECT)
                        ├─ ACCEPT → scoped auth → Razorpay order → receipt to agent
                        └─ REJECT → agent told "user declined"
```

## 1. Start the Guard backend

```bash
cd src/backend
../../.venv/bin/uvicorn app.main:app --reload      # or: pip install -r requirements.txt && uvicorn app.main:app
```

For **real Razorpay orders** (test mode), copy `.env.example` → `.env` and fill:
```
RAZORPAY_KEY_ID=rzp_test_xxxxxxxx
RAZORPAY_KEY_SECRET=xxxxxxxx
```
Without keys, payments run in clearly-labelled simulated mode. With test keys, real
Razorpay Orders are created via the API (test mode = no actual money moves).

## 2. Connect Claude Desktop

Edit `~/Library/Application Support/Claude/claude_desktop_config.json`
(Windows: `%APPDATA%\Claude\claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "agentpay-guard": {
      "command": "python3",
      "args": ["/ABSOLUTE/PATH/TO/razorpay/src/mcp/guard_mcp_server.py"],
      "env": { "GUARD_API": "http://localhost:8000" }
    }
  }
}
```

Restart Claude Desktop. You'll see tools: `search_products`, `purchase`, `get_guard_policy`.

## 3. Use it

Chat naturally:

> "Find me wireless headphones under ₹15,000 and buy the best one"

Claude searches, picks, and calls `purchase`. Within ~4 seconds your phone
(emulator: `10.0.2.2` is auto-used) shows:

```
AI PURCHASE REQUEST
Sony WH-1000XM5 · amazon
₹14,499 · risk LOW            [REJECT] [ACCEPT]
```

- **ACCEPT** (in app or on the notification) → authorization issued → Razorpay order
  created → Claude receives the receipt.
- **REJECT** → Claude is told you declined; nothing was charged.
- Try "buy a gift card" or "casino chips" → **blocked instantly**, agent gets
  `CATEGORY_BLOCKED`, phone shows it in Activity/Audit.

## 4. Other agents

- **ChatGPT (Custom GPT / Actions):** the backend already serves an OpenAPI spec at
  `http://localhost:8000/openapi.json` — point a GPT Action at it (needs a public URL,
  e.g. ngrok) and the same endpoints drive the same flow.
- **Grok / any agent:** anything that can POST JSON:
  `POST /agent/payment-request` → poll `GET /agent/payment-status/{id}` →
  `POST /guard/approvals/{id}/action` → `POST /guard/payments/execute`.
- **Terminal:** `python src/agent/run_demo.py --mode all` drives the same backend.

## How it stays safe (trust anchor = phone)

The backend's evaluation is advisory. `LiveSync` (Android) pulls pending requests,
**re-evaluates them with the on-device engine**, and only then raises the approval.
If the backend were compromised and marked something ALLOW, the phone still enforces
its own policy, limits and circumvention detection before you ever see an approval.
Freezing an agent on the phone blocks its requests even if the cloud says yes.
