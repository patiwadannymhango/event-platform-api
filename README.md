# Copperbelt Marathon 2026 — Docker + GitHub + AWS + Vercel Deployment

Three independently deployed pieces:

- **`backend/`** — Django REST API, dockerized, deploys to an AWS server
  with a GitHub Actions pipeline that redeploys automatically on every
  push to `main`.
- **`public-site/`** — the public registration site (React), deploys
  standalone on Vercel.
- **`admin/`** — the admin dashboard (React), *also* deploys standalone
  on Vercel, as its own separate Vercel project.

All three are independent deployments talking to each other over real
network requests (not shared origins) — the two frontends reach the
backend cross-origin, so CORS is what "introduces" them to each other.

```
copperbelt-marathon/
├── backend/           Django REST API — deploys to AWS
├── public-site/       Public registration site (React) — deploys on Vercel
├── admin/             Admin dashboard (React) — deploys on Vercel (separate project)
├── docker-compose.yml         local development
├── docker-compose.prod.yml    what runs on your AWS server (backend only)
├── Caddyfile                  reverse proxy in front of the backend
└── .github/workflows/deploy.yml
```

---

## How it fits together in production

**No domain required for the backend.** It's reachable at a single
address — `localhost`, a LAN IP, or an EC2 public IP — fronted by Caddy.
Both frontends are separate Vercel projects, each with its own domain,
each making real cross-origin requests to the backend.

```
  https://your-public-site.vercel.app     https://your-admin.vercel.app
              │                                       │
              │        cross-origin fetches (need CORS_ALLOWED_ORIGINS)
              └───────────────────┬───────────────────┘
                                   ▼
                         ┌────────────────────┐
  http://<address>/  ──▶ │   Caddy (proxy)     │  port 80
                         └─────────┬──────────┘
                    ┌──────────────┴──────────────────┐
                    ▼                                  ▼
               /api/v1/*                       /static/*, /media/*
          backend (gunicorn)                    served by Caddy
            /django-admin/*                    from shared volumes
                 │
      ┌──────────┼──────────┐
      ▼          ▼          ▼
  Postgres    Redis      Lipila
                        (webhook → http://<address>
                         /api/v1/payments/webhooks/
                         lipila/)
```

| URL | What it is |
|---|---|
| `https://your-public-site.vercel.app` | Public registration site (Vercel) |
| `https://your-admin.vercel.app` | Admin dashboard (Vercel, separate project) |
| `http://<address>/api/v1/…` | Django REST API (AWS) |
| `http://<address>/django-admin/` | Django's built-in admin site (AWS) |

Both frontends are genuinely separate origins from the backend now, so
both need an **absolute** API URL baked in at build time
(`VITE_API_BASE_URL`), and the backend needs *both* their Vercel domains
in `CORS_ALLOWED_ORIGINS` — see the Vercel sections below. There's no
`same-origin` shortcut available anywhere in this layout anymore.

---

## 0. Rotate your secrets (still applies)

Same note as before: the Lipila keys, DB password, and Gmail app password
that have appeared in this conversation should be rotated before real
traffic hits this. Nothing below depends on specific values.

---

## 1. Push this to GitHub

```bash
cd copperbelt-marathon
git init
git add .
git commit -m "Initial dockerized setup"
git branch -M main
git remote add origin https://github.com/<your-username>/<your-repo>.git
git push -u origin main
```

`.env` files are gitignored everywhere (only `.env.example` /
`.env.prod.example` get committed) — you'll create the real ones directly
on the server in step 2, not in git.

---

## 2. Set up the AWS server (backend only)

Any EC2 instance running Ubuntu works. SSH in and install Docker:

```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
newgrp docker
sudo apt-get install -y docker-compose-plugin git
```

**Security group:** open ports 22 (SSH) and 80 to the internet. That's it —
no 443, because there's no domain to issue a certificate for yet.

**DNS:** nothing to do. You'll reach the API at `http://<server-public-IP>/`.

Clone the repo onto the server:

```bash
git clone https://github.com/<your-username>/<your-repo>.git
cd <your-repo>
```

Create the real env files (these never come from git):

```bash
cp .env.prod.example .env.prod
cp backend/.env.example backend/.env
```

Edit both:
- `.env.prod` — just DB password and `HTTP_PORT` (leave `HTTP_PORT=80`
  unless something else already owns port 80 on the machine).
- `backend/.env` — `DEBUG=False`,
  `DJANGO_SETTINGS_MODULE=config.settings.production`, a real `SECRET_KEY`,
  DB credentials matching `.env.prod`, your real Lipila/email/SMS values,
  and **`ALLOWED_HOSTS` listing every address you'll reach the API by**,
  e.g. `127.0.0.1,localhost,13.51.72.9`. Getting this wrong is the most
  likely cause of a `DisallowedHost` 400 on first load.
  Leave `CORS_ALLOWED_ORIGINS` for now — you'll add both frontends' real
  Vercel domains to it once they're deployed (see below).

First deploy:

```bash
docker compose --env-file .env.prod -f docker-compose.prod.yml up -d --build
```

The backend container runs migrations and seeds the event automatically on
startup (`docker-entrypoint.sh`). Check the logs for the printed Event ID —
you'll need it for both Vercel projects below:

```bash
docker compose -f docker-compose.prod.yml logs backend | grep "Event ID"
```

Create your admin login:

```bash
docker compose -f docker-compose.prod.yml exec backend python manage.py createsuperuser
```

Point Lipila's webhook URL (in your Lipila dashboard) at:
```
http://<server-public-IP>/api/v1/payments/webhooks/lipila/
```

⚠️ Lipila calls that URL from the internet, so it only works once the app
is on a machine reachable from outside — a laptop on `localhost` will never
receive webhooks. Everything else (registration, the dashboard, card/mobile
money *initiation*) works fine locally; only the payment **confirmation**
callback needs a public address. For local webhook testing, put a tunnel
(ngrok, cloudflared) in front of port 80 and use the tunnel's URL here.

That's the whole AWS side. Confirm it's up:

```bash
curl http://<server-public-IP>/api/v1/registrations/public/events/<event-id>/form/
```

Then head to the two Vercel sections below to deploy both frontends
against this backend.

---

## 2b. Running the backend on your own machine instead

Exactly the same commands — the stack doesn't care what address it's on:

```bash
cp .env.prod.example .env.prod
cp backend/.env.example backend/.env      # set ALLOWED_HOSTS=127.0.0.1,localhost
docker compose --env-file .env.prod -f docker-compose.prod.yml up -d --build
```

The API is then at <http://localhost/api/v1/...>. If something else
already owns port 80, set `HTTP_PORT=8080` in `.env.prod` and use
`http://localhost:8080` instead.

---

## 2c. Getting HTTPS (required before connecting real Vercel frontends)

Vercel always serves over HTTPS, and browsers block an HTTPS page from
calling a plain `http://` backend ("mixed content") — so this step isn't
optional once real frontends need to reach the API, even without a domain.

**Free, no domain needed — sslip.io:** with a fixed Elastic IP attached
(see step 2), `<ip-with-dashes>.sslip.io` is a real, publicly resolvable
hostname that resolves straight back to that IP — e.g. `15.240.170.199`
becomes `https://15-240-170-199.sslip.io`. Caddy can fetch a genuine
Let's Encrypt cert for it like any other domain. Set in `.env.prod`:

```
SITE_ADDRESS=https://15-240-170-199.sslip.io
```

**Or, with a real domain later:** point an A record at the Elastic IP,
then set `SITE_ADDRESS` to that domain instead — nothing else changes.

```
SITE_ADDRESS=https://api.copperbeltmarathon2026.org
```

Either way: open port 443 in the security group (`docker-compose.prod.yml`
already maps it), add the hostname to `ALLOWED_HOSTS` in `backend/.env`,
then recreate the proxy container:

```bash
docker compose --env-file .env.prod -f docker-compose.prod.yml up -d --force-recreate proxy
```

Caddy fetches the certificate automatically on the first request. Update
`VITE_API_BASE_URL` in both Vercel projects to the new `https://...`
address and redeploy them.

---

## 2d. Deploying the public site to Vercel

The public site (`public-site/`) is a plain Vite + React SPA — Vercel
detects it automatically, no config beyond what's already in this repo
(`public-site/vercel.json` handles the client-side routing rewrite so
direct links like `/races` don't 404).

**1. Import the project.** In the Vercel dashboard: **Add New → Project**,
pick this repo. Since it's a monorepo, set:
- **Root Directory:** `public-site`
- **Framework Preset:** Vite (auto-detected)
- Build/output settings: leave the defaults (`npm run build`, `dist`)

**2. Set environment variables** (Project Settings → Environment
Variables):

| Variable | Value |
|---|---|
| `VITE_API_BASE_URL` | The backend's real address, e.g. `http://<server-public-IP>` or `https://api.yourdomain.com` once you have a domain. **Must be an absolute URL.** |
| `VITE_EVENT_ID` | The Event ID printed by the backend on first boot (step 2). |

**3. Deploy.** Vercel builds and gives you a URL like
`https://your-public-site.vercel.app`.

**4. Allow it through CORS** — see the combined CORS step at the end of
2e below (do both frontends' domains at once).

---

## 2e. Deploying the admin dashboard to Vercel

Same process, **as a separate Vercel project** — `admin/` also has its
own `vercel.json` for the client-side routing rewrite.

**1. Import the project.** **Add New → Project**, same repo, but:
- **Root Directory:** `admin`
- **Framework Preset:** Vite (auto-detected)
- Build/output settings: leave the defaults

**2. Set environment variables:**

| Variable | Value |
|---|---|
| `VITE_API_BASE_URL` | Same backend address as the public site above. |
| `VITE_EVENT_ID` | Same Event ID as the public site above. |

**3. Deploy.** You get a second, separate URL, e.g.
`https://your-admin.vercel.app`.

**4. Allow both frontends through CORS.** Until you do this, every API
call from either deployed site fails with a CORS error in the browser
console — add both Vercel URLs to `CORS_ALLOWED_ORIGINS` in
`backend/.env` on the server:

```bash
CORS_ALLOWED_ORIGINS=http://localhost:5173,http://localhost:5174,https://your-public-site.vercel.app,https://your-admin.vercel.app
```

then recreate the backend container so it picks up the change:

```bash
docker compose --env-file .env.prod -f docker-compose.prod.yml up -d --force-recreate backend
```

**5. Point Lipila's webhook at the backend, not Vercel.** The webhook
callback (`/api/v1/payments/webhooks/lipila/`) is served by the Django
backend on AWS — nothing changes there from step 2.

**Custom domains / preview deployments:** if you attach a custom domain
to either Vercel project, add it to `CORS_ALLOWED_ORIGINS` too. Vercel
gives every git branch/PR its own preview URL with a random subdomain —
those won't be able to reach a CORS-locked-down backend unless you also
add them (or accept that previews can't hit the real API, which is fine
if you're only using previews for UI review).

---

## 3. Set up automatic deployment from GitHub (backend only)

Generate a **dedicated** deploy key rather than reusing your own admin
`.pem` — keeps that key off GitHub entirely, scoped to nothing but SSH
access:

```bash
# on your own machine
ssh-keygen -t ed25519 -f event-platform-deploy -N "" -C "github-actions-deploy"
```

Append the `.pub` file's contents to `~/.ssh/authorized_keys` **on the
server** (via your own admin key):

```bash
ssh -i your-admin-key.pem ubuntu@<server> "echo '$(cat event-platform-deploy.pub)' >> ~/.ssh/authorized_keys"
```

In your GitHub repo → **Settings → Secrets and variables → Actions**, add:

| Secret | Value |
|---|---|
| `AWS_HOST` | your server's public IP or hostname |
| `AWS_SSH_USER` | the SSH user (e.g. `ubuntu`) |
| `AWS_SSH_PRIVATE_KEY` | contents of the `event-platform-deploy` private key generated above (not your admin `.pem`) |
| `AWS_PROJECT_PATH` | the absolute path to the repo on the server, e.g. `/home/ubuntu/copperbelt-marathon` |

From then on: **any push to `main` automatically SSHs into the server,
pulls the latest code, and rebuilds/restarts the backend**
(`.github/workflows/deploy.yml`, `docker-compose.prod.yml`). That's the
"changes I make locally reflect there" behaviour you asked for —
commit, push, and within a minute or two it's live.

You can also trigger a deploy manually from the GitHub Actions tab
(**Run workflow**) without pushing anything, if you just changed a
server-side `.env` value and want a restart.

This workflow only touches the backend. Both frontends deploy via
Vercel's own GitHub integration instead (connect each Vercel project to
this repo, using the Root Directory settings from 2d/2e) — Vercel then
auto-deploys each one independently on every push.

---

## 3b. Database backups

The production Postgres container has no backup on its own — losing the
EC2 instance or its disk means losing the database. `infra/backup-db.sh`
and `infra/restore-db.sh` handle daily dumps (local + optional offsite S3
upload) and restoring from one. One-time S3/IAM setup and cron wiring are
in [`infra/README.md`](infra/README.md) — set this up before you have real
registrations to lose.

---

## 4. Local development (unchanged from before)

Locally, both frontends still run the same way regardless of where they
deploy in production — plain Vite dev servers at the project root:

```bash
# Terminal 1 — Postgres + Redis + Django, with hot-reload
cp backend/.env.example backend/.env   # fill in local values
docker compose up -d

# Terminal 2 — public site
cd public-site && npm install && npm run dev

# Terminal 3 — admin
cd admin && npm install && npm run dev
```

Both frontends talk to Django on `http://localhost:8000` cross-origin —
that's what `CORS_ALLOWED_ORIGINS` in `backend/.env` is for, and it's now
exactly how production works too (both frontends cross-origin from the
backend), so local dev and production match.

`docker-compose.yml` (no `.prod`) runs the backend with `runserver` and a
mounted volume, so Python changes reload instantly. Both frontends are
easiest to run natively with `npm run dev` for fast HMR rather than in
Docker — neither is built by Docker at all anymore; `docker-compose.prod.yml`
only builds the backend. To sanity-check the backend's AWS-side routing
before deploying, run the prod stack locally as in **2b** above.

---

## 5. Day-to-day workflow once this is live

```bash
# make changes locally, test with docker-compose.yml
git add .
git commit -m "..."
git push
# GitHub Actions redeploys the backend to AWS automatically;
# Vercel redeploys both frontends automatically (if connected via its
# own GitHub integration)
```

To watch a deploy or debug the backend directly:

```bash
ssh ubuntu@your-server
cd copperbelt-marathon
docker compose -f docker-compose.prod.yml logs -f backend
docker compose -f docker-compose.prod.yml ps
```

---

## Notes carried over from earlier

- Test the Lipila disbursement/balance endpoints once in sandbox before
  trusting withdrawals/refunds with real money (see the endpoint-path
  caveat in `backend/README.md`).
- SMS is still a console/logging placeholder until you add a provider
  (`SMS_BACKEND=africastalking` + credentials in `backend/.env`).
- Admin API access is "any logged-in Django user," not yet role-scoped —
  only give `createsuperuser` accounts to trusted admins for now.
