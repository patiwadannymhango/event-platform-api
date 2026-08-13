# Copperbelt Marathon 2026 — Deployment Guide

Three projects, all built/wired together this session:

1. **backend/** — Django REST API (registration, payments/Lipila, notifications, admin)
2. **marathon-registration/** — the public registration site (React), now talking to the backend
3. **marathon-admin/** — the admin dashboard (React), talking to the same backend

---

## 0. Before anything else: rotate your secrets

Your uploaded `.env` contained real-looking Postgres credentials and **both Lipila
sandbox and production API keys**, and your message contained a Gmail app
password. All of that has now passed through this chat. Before this touches
real traffic:

- Rotate the Lipila sandbox **and** production API keys from your Lipila
  merchant dashboard
- Change the Postgres password
- Regenerate the Gmail app password (Google Account → Security → App passwords)

None of the code below depends on the specific values — swapping them in
`.env` is all that's needed.

---

## 1. Backend setup

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Edit `.env` (already present, using your existing Postgres credentials).
Key things to check/fill in:

```
DB_NAME=event_platform
DB_USER=postgres
DB_PASSWORD=...
DB_HOST=localhost
DB_PORT=5432

EMAIL_HOST_USER=patiwadannymhango2@gmail.com
EMAIL_HOST_PASSWORD=...        # Gmail App Password, not your normal password

LIPILA_ENVIRONMENT=sandbox      # switch to "production" when ready
LIPILA_SANDBOX_API_KEY=...
LIPILA_PRODUCTION_API_KEY=...
LIPILA_WEBHOOK_SECRET=...

CORS_ALLOWED_ORIGINS=http://localhost:5173,http://localhost:5174

SMS_BACKEND=console             # switch to "africastalking" once you have credentials
```

Create the database (if it doesn't exist yet), then:

```bash
python manage.py migrate
python manage.py createsuperuser   # this is your admin login for marathon-admin
python manage.py seed_copperbelt_marathon
```

The seed command prints an **Event ID** — copy it, you need it for both
frontends' `.env` files (`VITE_EVENT_ID`).

Run the server:

```bash
python manage.py runserver
```

The API is now at `http://localhost:8000`. Django's own admin (`/admin/`) also
works immediately with the superuser you created, and shows every model
(registrations, payments, transactions, withdrawals, notifications) if you
ever need to poke at the raw data.

### Lipila webhook

Lipila needs to reach `POST /api/v1/payments/webhooks/lipila/` on a public
URL. For local testing, use a tunnel (e.g. `ngrok http 8000`) and set that
URL in your Lipila dashboard's webhook settings. In production, this will be
your real domain.

**Important caveat on the Lipila integration:** the disbursement (send
money/withdraw/refund) and balance endpoints were built against the same
`x-api-key` + `/api/v1/...` style your existing collections code already
uses — but Lipila's public docs also describe a newer `Bearer` +
`/transactions/...` API surface. Before relying on withdrawals or refunds
with real money, do one test disbursement in sandbox and confirm the
response looks right; if it 404s, check your Lipila dashboard for the exact
path and update `LIPILA_DISBURSEMENT_ENDPOINT` / `LIPILA_BALANCE_ENDPOINT` in
`.env` (no code changes needed, just the path).

Similarly, the webhook payload parsing in
`apps/payments/providers/lipila/webhooks.py` reads a few likely field names
(`referenceId`/`status`) defensively — log one real sandbox webhook payload
and confirm the keys match, adjusting if needed.

---

## 2. Public registration site

```bash
cd marathon-registration
npm install
```

Edit `.env`:

```
VITE_API_BASE_URL=http://localhost:8000
VITE_EVENT_ID=<the event ID printed by seed_copperbelt_marathon>
```

```bash
npm run dev
```

This is the same site from earlier in our conversation — registration,
payment, reserve-a-spot, track-registration — now actually hitting the
backend instead of simulating everything locally.

---

## 3. Admin dashboard

```bash
cd marathon-admin
npm install
```

Edit `.env` the same way (same API base URL, same event ID):

```
VITE_API_BASE_URL=http://localhost:8000
VITE_EVENT_ID=<the event ID printed by seed_copperbelt_marathon>
```

```bash
npm run dev
```

Log in with the superuser you created (`python manage.py createsuperuser`).

**What's in it:**
- **Dashboard** — registration counts by status, revenue collected vs
  pending, ledger wallet balance, and a live Lipila balance call (falls back
  gracefully with an error message if Lipila is unreachable, rather than
  breaking the page)
- **Registrations** — search, filter by status, change status inline
  (e.g. flip a cash payment from PENDING to CONFIRMED), delete, bulk
  upload via CSV/XLSX, export everything to Excel
- **Payments & Wallet** — withdraw to mobile money/bank/cash, ad-hoc
  "send money," refund any successful payment, and browse the underlying
  ledger transactions/payments/withdrawals

**Known simplification:** every admin API endpoint currently just checks
"is this a logged-in Django user" (`IsAuthenticated`), not a specific
role. The codebase you uploaded already has an
`OrganizationMembership`/`EventMembership` role system (OWNER, ADMIN,
FINANCE, etc.) — wiring the admin endpoints to check those roles instead of
just "any authenticated user" is the natural next step, but wasn't done in
this pass given the "deploy today" timeline. For now, only give
`createsuperuser` accounts to people who should have full admin access.

---

## 4. What's genuinely production-ready vs. what needs a first real test

**Solid and testable right now:**
- Registration capture (all fields, reserve-or-pay branch)
- Manual registration, bulk upload, Excel export, status changes, search
- Email notifications (uses your real Gmail credentials)
- Dashboard stats and ledger balance

**Needs one live test against your Lipila sandbox before trusting it
unattended:**
- Mobile money collection → webhook → confirmation (the full payment loop)
- Withdrawals / send-money / refunds (disbursement endpoint path, as noted
  above)

**Needs a provider account before it does anything:**
- SMS — currently logs to the console/Notification log instead of sending.
  Sign up with Africa's Talking (or your preferred provider), set
  `AFRICASTALKING_USERNAME` / `AFRICASTALKING_API_KEY` and
  `SMS_BACKEND=africastalking` in `.env`, then uncomment the implementation
  in `apps/notifications/sms.py`.
