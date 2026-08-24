# Real AI shopping → Guard → Razorpay (MCP)

This is the **live** integration: you chat about shopping in Claude (Desktop, web, or the
Android app), the AI actually attempts a purchase, your phone gets an approval notification,
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

## 2. Connect Claude

### A. Claude Android / web — remote MCP (Streamable HTTP)

The stdio config above only works for Claude Desktop. For Claude's mobile/web apps you need a
**remote MCP server** on a public URL:

```bash
# terminal 1 — Guard backend
cd src/backend && ../../.venv/bin/uvicorn app.main:app --port 8000

# terminal 2 — remote MCP server (Streamable HTTP)
cd src/mcp && ../../.venv/bin/uvicorn remote_server:app --port 8002

# terminal 3 — public tunnel
ngrok http 8002          # or: cloudflared tunnel --url http://localhost:8002
```

Then in Claude (web or Android app): **Settings → Connectors → Add custom connector** and use:

```
https://<your-subdomain>.ngrok-free.app/mcp
```

Say **"buy me a keyboard under ₹10k"** in the chat. Claude calls `search_products` →
`purchase` → your phone gets the approval notification → ACCEPT → real Razorpay order
(test mode) → receipt lands back in the chat.

Optional hardening: set `GUARD_MCP_TOKEN=<secret>` on the remote server and use
`https://<subdomain>.ngrok-free.app/mcp` — requests without `Authorization: Bearer <secret>`
get 401. (Claude sends no auth headers for unauthenticated connectors; use the token in the
URL via a reverse-proxy rule, or rely on ngrok's random subdomain for the hackathon.)

### B. Claude Desktop — stdio MCP

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

- **ChatGPT (Custom GPT / Actions):** the backend serves an OpenAPI spec at
  `http://localhost:8000/openapi.json` — point a GPT Action at it (needs a public URL,
  e.g. ngrok) and the same endpoints drive the same flow.
- **Grok / any agent:** anything that can POST JSON:
  `POST /agent/payment-request` → poll `GET /agent/payment-status/{id}` →
  `POST /guard/approvals/{id}/action` → `POST /guard/payments/execute`.
- **Terminal:** `python src/agent/run_demo.py --mode all` drives the same backend.

## Payment modes

- **No keys** → simulated orders (labelled `SIMULATED` in receipts).
- **Test keys** (`rzp_test_…`) → **real Razorpay Orders** created via the API; the order is
  genuine and visible in your Razorpay dashboard, but no money moves until checkout completes
  (test mode). Status shows `processing` until paid.
- **Live keys** (`rzp_live_…`) → real money. Rotate any secret that has ever been pasted
  into a chat or screenshot.

## How it stays safe (trust anchor = phone)

The backend's evaluation is advisory. `LiveSync` (Android) pulls pending requests,
**re-evaluates them with the on-device engine**, and only then raises the approval.
If the backend were compromised and marked something ALLOW, the phone still enforces
its own policy, limits and circumvention detection before you ever see an approval.
Freezing an agent on the phone blocks its requests even if the cloud says yes.
