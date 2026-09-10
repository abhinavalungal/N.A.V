# Deploying N.A.V. to Render, step by step

There is no single file to upload. Render deploys from a **GitHub repository**,
not from a zip, and this project is two things at once: a Python service and a
browser app. What you can have is one service and one URL, which is what this
guide sets up.

Roughly 15 minutes the first time. No credit card.

---

## Before you start

You need a GitHub account and Git installed. Check:

```bash
git --version
```

Pick one of the two routes below. **Route 1** is what I tested end to end.
**Route 2** needs no Node.js on your machine, but I could not run a container
build in my sandbox, so treat it as untested.

| | Route 1 — build it yourself | Route 2 — let Render build it |
| --- | --- | --- |
| Needs Node.js locally | yes | no |
| Steps per frontend change | run one script, push | push |
| Uses Docker | no | yes |
| Verified | yes | no |

---

# Route 1 — recommended

## Step 1. Build the frontend and commit it

From the project folder:

```bash
bash deploy/prepare.sh
```

It installs the frontend dependencies, builds `frontend/out/`, checks that an
`index.html` really appeared, and commits the result. If it says npm is
missing, install Node.js 18+ from nodejs.org first.

On Windows, use Git Bash (installed with Git) and the same command.

If the folder is not a Git repository yet, the script tells you to run:

```bash
git init
git add -A
git commit -m "N.A.V."
```

then run `bash deploy/prepare.sh` again.

## Step 2. Push to GitHub

1. Go to **github.com/new**.
2. Name it `nav` (or anything). **Private** is fine. Do **not** tick "Add a
   README" — the repo must start empty.
3. Click **Create repository**.
4. GitHub shows a box titled "…or push an existing repository". Copy those two
   or three lines and run them in your project folder. They look like:

```bash
git remote add origin https://github.com/YOUR-NAME/nav.git
git branch -M main
git push -u origin main
```

Refresh the GitHub page. You should see `backend/`, `frontend/`, `render.yaml`
and, inside `frontend/`, an `out/` folder. **If `out/` is missing, Render will
serve the API but no app** — go back to step 1.

## Step 3. Create the Render service

1. Sign up at **render.com** with your GitHub account.
2. Dashboard → **New +** → **Blueprint**.
3. Connect GitHub if prompted, then pick your `nav` repository.
   Grant access to that repo when GitHub asks.
4. Render reads `render.yaml` and shows one service called **nav**. Give the
   blueprint any name.
5. Click **Apply** / **Create resources**.

That is the whole configuration. `render.yaml` already sets the Python
runtime, the root directory, the build and start commands, the health check
and the environment variables.

## Step 4. Watch the first deploy

Click the **nav** service → **Logs**. Expect, in order:

```
==> Installing dependencies
Successfully installed fastapi ... uvicorn ...
==> Running 'python seed.py --if-empty && uvicorn app.main:app ...'
Database: sqlite:////tmp/nav.db
  vessels              10
  voyages              23
INFO nav: Serving the exported frontend from /opt/render/project/src/frontend/out
INFO:     Uvicorn running on http://0.0.0.0:10000
==> Your service is live 🎉
```

Three to five minutes. The line that matters is **"Serving the exported
frontend"** — if it says "running API only" instead, `frontend/out/` did not
reach GitHub.

## Step 5. Open it

Your URL is at the top of the service page, e.g.
`https://nav-xxxx.onrender.com`. Open it and you should get the dashboard.

Quick checks:

- `https://your-url.onrender.com/health` → `{"status":"ok"}`
- `https://your-url.onrender.com/docs` → the API documentation
- `https://your-url.onrender.com/api/v1/meta` → JSON with the version

## Step 6. Put a password on it

The app has no login. Anyone with the URL can approve recommendations and run
the agent. Until you add protection, treat the URL as a secret: don't post it
anywhere public. `DEPLOY.md` covers adding basic auth properly.

## Updating it later

```bash
bash deploy/prepare.sh   # only if you changed anything in frontend/
git push
```

Backend-only changes need just `git add -A && git commit -m "..." && git push`.
Render redeploys on every push.

---

# Route 2 — let Render build everything

No Node.js needed locally, and nothing to rebuild by hand. **I could not test
this one** — there was no container runtime in my environment — so if it
fails, fall back to Route 1.

1. Open `render.yaml` and change these two lines:

```yaml
    runtime: docker          # was: runtime: python
    dockerfilePath: ./Dockerfile
```

   then delete the `rootDir`, `buildCommand` and `startCommand` lines. The
   `Dockerfile` at the project root already runs the frontend build, installs
   the Python dependencies, seeds and starts uvicorn.

2. Commit and push, then follow **Step 3** onwards above.

Builds take longer this way (Node install plus the Next build on Render's
pipeline, roughly 5–8 minutes) but you never touch `frontend/out/` again.

---

## When something goes wrong

**"Your service is live" but the page is blank or 404s.**
`frontend/out/` is not in the repo. Run `git ls-files frontend/out | wc -l` —
it should print about 109. If it prints 0, run `bash deploy/prepare.sh`, then
`git push`.

**Build fails on `pip install`.**
Check the log for the failing package. `PYTHON_VERSION` in `render.yaml` is
`3.12.7`; nothing here needs anything newer.

**First visit takes a minute and then works.**
Normal. Free services sleep after 15 minutes of no traffic. Open the URL a
minute before you demo it, or switch the instance to Starter ($7/month) for
always-on.

**Approvals disappear.**
Also expected. Free instances have no persistent disk, so the database lives
in `/tmp` and is rebuilt from the seed on each restart. The fleet always comes
back identical. `DEPLOY.md` explains switching to Postgres if you need
approvals to survive.

**Weather shows "Mock data".**
Deliberate. `render.yaml` sets `WEATHER_PROVIDER=mock` because the free
Open-Meteo API is licensed for non-commercial use only. To use live data on a
deployment, change that variable to `auto` and read the licence note in
`DEPLOY.md` first.

**You want the AI answers to come from OpenAI rather than the mock agent.**
Service → **Environment** → add `OPENAI_API_KEY`. Do this only after the URL
is password-protected: `/api/v1/agent/chat` would otherwise be an open proxy
to your account.
