# WhatsApp Business API Setup Guide

How to connect Sage to WhatsApp for local development using ngrok.

---

## Prerequisites

Before you start, make sure you have:

- **Meta Business account** (free at [business.facebook.com](https://business.facebook.com))
- **Docker Desktop** running (for Postgres and Redis)
- **Python 3.12+** with the backend virtualenv set up
- **ngrok** installed (`brew install ngrok`) with a free account at [ngrok.com](https://ngrok.com)
- **Anthropic API key** from [console.anthropic.com](https://console.anthropic.com)

---

## 1. Meta Business Account Setup

1. Go to [business.facebook.com](https://business.facebook.com) and create a Meta Business account if you don't have one.
2. Go to [developers.facebook.com](https://developers.facebook.com) and click **My Apps > Create App**.
3. Select app type **Business**.
4. Give it a name (e.g. "Sage Dev") and link it to your Business account.
5. On the app dashboard, find **WhatsApp** in the product list and click **Set Up**.

---

## 2. WhatsApp Business API Configuration

1. In the Meta Developer dashboard, go to **WhatsApp > Getting Started**.
2. Note the following values — you'll need them for your `.env` file:
   - **Temporary Access Token** — valid for 24 hours
   - **Phone Number ID** — under the test phone number
3. Under **To**, add your personal WhatsApp number as a test recipient.
4. You can use the **Send Message** button on this page to verify Meta can reach your phone.

---

## 3. Local Environment Setup

Copy the example env file and fill in the values:

```bash
cd backend
cp ../.env.example .env
```

Edit `.env` and set these variables:

```
WHATSAPP_TOKEN=<temporary access token from Meta dashboard>
WHATSAPP_PHONE_NUMBER_ID=<phone number ID from Meta dashboard>
WHATSAPP_VERIFY_TOKEN=sage-webhook-verify
WHATSAPP_APP_SECRET=<app secret from Meta App Settings > Basic>
ANTHROPIC_API_KEY=sk-ant-<your key from console.anthropic.com>
```

The `WHATSAPP_VERIFY_TOKEN` can be any string you choose. You'll use the same value when configuring the webhook in Meta's dashboard.

---

## 4. Start Local Services

You need three terminals running.

**Terminal 1 — Infrastructure (Postgres + Redis):**

```bash
make up
```

**Then run migrations and seed the plant database (one-time):**

```bash
make migrate
make seed
```

**Terminal 2 — API server:**

```bash
make dev
```

The server starts on `http://localhost:8000`.

**Terminal 3 — Message worker:**

```bash
make worker
```

The worker processes inbound WhatsApp messages through the Sage orchestrator and sends replies.

---

## 5. Ngrok Tunnel Setup

Ngrok creates a public HTTPS URL that tunnels to your local server. Meta requires HTTPS for webhooks.

```bash
ngrok http 8000
```

You'll see output like:

```
Forwarding  https://a1b2c3d4.ngrok-free.app -> http://localhost:8000
```

Copy the `https://...ngrok-free.app` URL. This is your webhook base URL.

> **Tip:** Leave ngrok running. If you restart it, you get a new URL and must update the webhook in Meta's dashboard.

---

## 6. Configure Webhook in Meta Dashboard

1. In the Meta Developer dashboard, go to **WhatsApp > Configuration**.
2. Under **Webhook**, click **Edit**.
3. Set the fields:
   - **Callback URL:** `https://<your-ngrok-url>/webhook/whatsapp`
   - **Verify Token:** the same value you set for `WHATSAPP_VERIFY_TOKEN` in `.env`
4. Click **Verify and Save**. Meta sends a GET request to your server — if everything is running, it will verify successfully.
5. Under **Webhook Fields**, subscribe to **messages**.

---

## 7. Test It

1. Open WhatsApp on your phone.
2. Send **"Hello"** to the test phone number shown in the Meta dashboard.
3. Sage should respond with the onboarding welcome message.
4. Walk through the onboarding flow (name, location, experience level, what you're growing).
5. After onboarding, try asking a gardening question like "When should I plant tomatoes?"

---

## 8. Troubleshooting

### Check ngrok request logs

Open [http://127.0.0.1:4040](http://127.0.0.1:4040) in your browser. This shows every request hitting your tunnel — useful for seeing whether Meta is actually sending webhook events.

### Check server logs

The `make dev` terminal shows all incoming requests and errors. Look for:
- `WhatsApp webhook verified successfully` — confirms the GET verification worked
- Errors during message processing — usually logged with tracebacks

### Common issues

| Problem | Cause | Fix |
|---------|-------|-----|
| Webhook verification fails | Verify token mismatch | Check `WHATSAPP_VERIFY_TOKEN` matches in `.env` and Meta dashboard |
| No response from Sage | Worker not running | Make sure `make worker` is running in a separate terminal |
| 401 / auth errors | Expired token | Temporary access tokens expire every 24h — refresh in Meta dashboard |
| Connection refused | Port mismatch | Confirm the API server is running on port 8000 and ngrok points to 8000 |
| Messages not arriving | Webhook field not subscribed | Go to WhatsApp > Configuration and make sure **messages** is ticked |
| ngrok URL changed | Restarted ngrok | Update the Callback URL in Meta dashboard with the new ngrok URL |

---

## 9. Development Tips

- **Local testing without WhatsApp:** Use the CLI for fast iteration — no ngrok or Meta setup needed:
  ```bash
  cd backend
  source .venv/bin/activate
  python -m app.cli
  ```

- **Temporary tokens expire every 24 hours.** When your token expires, go to WhatsApp > Getting Started in the Meta dashboard and generate a new one. Update `WHATSAPP_TOKEN` in `.env` and restart the API server.

- **For permanent access tokens:** In Meta Business Settings, create a **System User**, grant it the `whatsapp_business_messaging` permission, and generate a permanent token. This avoids the 24h expiry cycle.

- **Ngrok free tier** gives you a random URL each time. If you want a stable URL, upgrade to a paid ngrok plan or use `ngrok http 8000 --domain=your-custom-domain.ngrok-free.app` with a reserved domain.

- **Rate limits:** The test number has low rate limits. Don't send a flood of messages during testing.
