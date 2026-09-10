# Deploying N.A.V.

The frontend is a **static export**. `npm run build` writes `frontend/out/` —
`index.html`, per-route folders and hashed assets, about 3.3 MB. There is no
Node server in production: every page fetches from the API in the browser.

That gives two shapes:

| Shape | What runs | When to pick it |
| --- | --- | --- |
| **Single service** | FastAPI serves the API *and* `frontend/out/` | Default. One process, one URL, no CORS. |
| **Split** | Static host for `out/`, separate host for the API | You already have a static host you like, or you want a CDN in front. |

FastAPI mounts the export automatically when `frontend/out/index.html` exists,
so `uvicorn app.main:app` alone serves the whole application on
`http://localhost:8000`. Override the location with `NAV_FRONTEND_DIR` if the
folder lives somewhere else. With no export present the backend logs that it is
running API-only and nothing breaks.

---

## A. One machine on the office LAN

Cheapest, fastest, no cold starts, and it never leaves your network.

```bash
cd frontend && npm ci && npm run build     # writes out/
cd ../backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python seed.py
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Colleagues open `http://<machine-ip>:8000`. One port, one process. No
`CORS_ORIGINS`, no `NEXT_PUBLIC_API_URL` — the build already points at
`/api/v1` on whatever origin serves it.

`deploy/nav-api.service` keeps it running after logout. (`nav-web.service` is
only needed for the split shape.)

---

## B. Render free, single service

1. `cd frontend && npm ci && npm run build`
2. `git add -f frontend/out && git commit && git push` — Render's Python
   runtime has no Node.js, so the export is built on your machine and shipped
   as files. `.gitignore` ignores `out/` by default, hence the `-f`.
3. Render → New → Blueprint → pick the repo. `render.yaml` does the rest:
   Python runtime, root directory `backend`, health check on `/health`, seed
   then uvicorn.

Repeat steps 1 and 2 whenever the frontend changes.

What the free tier costs you:

- **Sleeps after 15 minutes idle, ~1 minute to wake.** The first click of a
  demo sits on a spinner. Open the URL a minute before you present, or move to
  the $7 always-on instance for the day.
- **No persistent disk.** SQLite is in `/tmp` and is wiped on restart, so
  approvals disappear. The seed is deterministic, so the fleet returns
  identical — for a demo, arguably a feature. See Postgres below if not.
- 512 MB RAM and 0.1 CPU is plenty. An optimization run is milliseconds of
  arithmetic plus at most two weather calls.

---

## C. Split: Netlify plus an API host

Only worth it if you want the CDN. Netlify's free tier permits commercial use;
Vercel's Hobby plan does not, which matters if this is shown as GeoServe work.

1. Netlify → import the repo, base directory `frontend`.
   `frontend/netlify.toml` sets `publish = "out"`. No Next.js runtime plugin is
   involved — it is a plain static site.
2. Netlify → Environment variables →
   `NEXT_PUBLIC_API_URL = https://your-api-host/api/v1`. This must be set
   **before** the build: the value is compiled into the bundle. Without it the
   build falls back to `.env.production`, which assumes a same-origin API and
   will not work here.
3. Deploy the backend anywhere (Render blueprint above works; the committed
   `out/` folder is simply ignored when it is not used), then set
   `CORS_ORIGINS` to the Netlify URL and redeploy the API.

---

## D. One small VPS

Best if this becomes something people use regularly: always on, real
persistence, one origin, and a password on the front door.

```bash
sudo adduser --system --group --home /opt/nav nav
sudo -u nav git clone <your-repo> /opt/nav

cd /opt/nav/frontend && sudo -u nav npm ci && sudo -u nav npm run build

cd /opt/nav/backend
sudo -u nav python3 -m venv .venv
sudo -u nav .venv/bin/pip install -r requirements.txt
sudo -u nav .venv/bin/python seed.py

sudo cp /opt/nav/deploy/nav-api.service /etc/systemd/system/
sudo cp /opt/nav/deploy/Caddyfile /etc/caddy/Caddyfile   # edit the hostname
caddy hash-password                                       # paste into the Caddyfile
sudo systemctl daemon-reload && sudo systemctl enable --now nav-api
sudo systemctl reload caddy
```

Caddy terminates TLS, adds basic auth and proxies everything to uvicorn, which
serves both the app and the API. Back up the database if the approval history
matters:

```
0 2 * * *  sqlite3 /opt/nav/data/nav.db ".backup '/opt/nav/backups/nav-$(date +\%F).db'"
```

---

## Switching to Postgres

Only needed where the filesystem is ephemeral or several instances run at once.
No application code changes — `app/database.py` picks its connection settings
from the URL scheme.

```bash
pip install "psycopg[binary]==3.2.3"
export DATABASE_URL="postgresql+psycopg://user:password@host/dbname"
python seed.py
```

A free Render Postgres expires 30 days after creation. Neon and Supabase free
tiers do not, and you already use both elsewhere.

---

## Before it goes anywhere public

**There is no authentication.** The spec ruled it out, so anyone with the URL
can approve recommendations, create voyages and run the agent. Put a password
in front of it: basic auth in Caddy, Netlify's site password, or keep it on the
LAN. Never put an OpenAI key on an unprotected public deployment —
`/api/v1/agent/chat` becomes an open proxy to your account.

**Open-Meteo's free API is licensed for non-commercial use only**, capped at
10,000 calls a day, and requires CC BY 4.0 attribution (the weather panel
carries it). A hosted GeoServe demo shown to clients is arguable at best. Run
public deployments with `WEATHER_PROVIDER=mock`, which is what `render.yaml`
does, or buy an Open-Meteo customer plan and point the provider at
`customer-api.open-meteo.com`. Batching and caching keep volume low — an
optimization run costs two calls — but the licence is about who is using it,
not how much.

**Keep the demo-data framing visible.** Vessel names, IMO numbers, positions,
bunker prices and history are seeded fiction; only port coordinates and
emission factors are real.

**Set a spend cap** on any account you attach a card to.

---

## Checklist

- [ ] `frontend/out/` rebuilt after any frontend change (and re-committed, on Render)
- [ ] `NEXT_PUBLIC_API_URL` set before the build — split shape only
- [ ] `CORS_ORIGINS` set to the exact frontend origin — split shape only
- [ ] `WEATHER_PROVIDER` chosen deliberately (`mock` for public deployments)
- [ ] `OPENAI_API_KEY` set only where the deployment is access-controlled
- [ ] `/health` returns 200 from outside the host
- [ ] A password or a private network in front of the whole thing
- [ ] Backend woken before a live demo, if it is on a free tier
