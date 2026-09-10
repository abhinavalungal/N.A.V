# N.A.V. — Nautical Agentic Navigator

**Intelligence for Every Voyage.**

A working prototype of an agentic maritime voyage-optimization assistant. N.A.V. routes a
voyage through real sea lanes, samples weather along the track, calculates fuel burn, ETA and
CO2 with documented maritime formulas, ranks four route variants against an objective, and
explains its recommendation. An operator approves, rejects or modifies it. N.A.V. never
controls a vessel.

Everything the interface shows is computed by the Python backend from the seeded database.
The language model is used to *explain and orchestrate*, never to produce numbers.

---

## What is in the box

```
nav/
├── backend/          FastAPI + SQLAlchemy + SQLite
│   ├── app/
│   │   ├── api/            HTTP layer (vessels, voyages, weather, fuel, optimization, agent, analytics)
│   │   ├── services/       geo, ports, routing, weather, fuel, eta, emissions, optimizer, agent
│   │   ├── ai/             provider abstraction (OpenAI or mock) and prompts
│   │   ├── models.py       13 tables
│   │   ├── schemas.py      Pydantic v2 request/response models
│   │   └── main.py         app factory, CORS, uniform error handling
│   ├── tests/              32 pytest cases over the calculators and the optimizer
│   └── seed.py             deterministic demo fleet
├── frontend/         Next.js 14 + TypeScript + Tailwind + MapLibre GL + Recharts
│                     static export; npm run build writes frontend/out/
├── data/             nav.db is created here
└── README.md
```

---

## Requirements

- Python 3.11 or newer
- Node.js 18.17 or newer
- No Docker, no cloud account, no paid API key. An OpenAI key is optional.

---

## Backend setup

```bash
cd backend
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python seed.py                     # creates ../data/nav.db and the demo fleet
uvicorn app.main:app --reload
```

The API is then on `http://localhost:8000`, with interactive docs at
`http://localhost:8000/docs` and a health probe at `/health`.

Re-running `seed.py` rebuilds the database from scratch. It is deterministic: same fleet,
same positions, same recommendations every time.

### Tests

```bash
cd backend
WEATHER_PROVIDER=mock pytest -q      # 32 passed
```

## Frontend setup

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:3000`. In development the app talks to
`http://localhost:8000/api/v1`; override that in `.env.local` if your backend
runs elsewhere (see `.env.local.example`).

For anything other than development, build it instead:

```bash
npm run build          # writes frontend/out/ — index.html and static assets
```

The app is a static export: no Node server, every page fetches from the API in
the browser. If `frontend/out/` exists, the backend serves it, so
`uvicorn app.main:app` alone puts the whole application on
`http://localhost:8000` with no second process and no CORS. `DEPLOY.md` covers
the alternative of hosting `out/` separately.

---

## Environment variables

Copy `.env.example` to `backend/.env` (or export the variables) to change any of these.

| Variable | Default | Meaning |
| --- | --- | --- |
| `OPENAI_API_KEY` | *(empty)* | Optional. With a key, the agent uses OpenAI tool-calling. Without one it uses the built-in mock agent, which calls exactly the same tools. |
| `OPENAI_MODEL` | `gpt-4o-mini` | Model used when a key is present. |
| `WEATHER_PROVIDER` | `auto` | `auto` tries Open-Meteo and silently falls back to the mock provider; `open_meteo` forces live data; `mock` forces the deterministic provider. |
| `DATABASE_URL` | `sqlite:///../data/nav.db` | SQLite file location. |
| `CORS_ORIGINS` | `http://localhost:3000` | Comma-separated list. |

Frontend (`frontend/.env.local`):

| Variable | Default | Meaning |
| --- | --- | --- |
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000/api/v1` | Backend base URL. |
| `NEXT_PUBLIC_MAP_STYLE_URL` | *(empty)* | Optional MapLibre style URL. Empty uses the bundled offline chart style, which needs no key and no network. |

---

## Weather data

Open-Meteo is free and needs no key. In `auto` mode the backend batches the track points into
two Open-Meteo calls (marine + atmospheric), caches them in memory, and degrades to the
deterministic mock provider if the service is unreachable or returns no marine data for an
open-sea point.

**Every weather sample carries the source it came from** (`OPEN_METEO` or `MOCK`), and the UI
labels it. Optimization runs record the source they used, and the recommendation text says so.
Mock weather is physically plausible — Pierson-Moskowitz wave heights from wind speed, storm
belts around 47° north and south — but it is synthetic, not a forecast.

---

## How the calculation chain works

1. **Routing** — a hand-built graph of 57 ocean waypoints and the lanes between them (Malacca,
   Suez, Gibraltar, Cape of Good Hope, Panama, Hormuz, Sunda). Dijkstra over great-circle leg
   distances, then the path is densified for weather sampling. Sanity-checked against published
   distances, e.g. Singapore to Rotterdam via Suez comes out at 8,419 NM.
2. **Weather** — samples at intervals along the track; wind, wave height and direction, surface
   current, visibility. A risk index combines wave height, wind and heading exposure into a band
   from very low to severe.
3. **Fuel** — `consumption = base × (speed / design speed)³ × weather factor`, plus a fixed
   auxiliary load. The cube law is the standard propulsion approximation. The weather factor is
   a documented heuristic in `config.py`, not a validated hull model.
4. **ETA** — distance over speed made good, with the along-track current component and a port
   allowance.
5. **Emissions** — fuel mass × the IMO MEPC.336(76) / EU MRV carbon factor for that fuel grade
   (HSFO 3.114, VLSFO 3.151, MGO 3.206, LNG 2.750), plus CO2 per nautical mile and AER.
6. **Optimization** — four variants (fastest, fuel efficient, weather optimized, eco slow steam)
   are each fully evaluated, constraints are applied, the survivors are min-max normalized and
   scored with the weights of the chosen objective. Lowest score wins.

If every variant breaches a constraint, N.A.V. returns `NO_FEASIBLE_OPTION` with the reason for
each. It does not invent a compromise.

---

## The agent

Ten tools are exposed to the model: `get_vessel`, `get_voyage`, `get_weather`, `get_routes`,
`calculate_fuel`, `calculate_eta`, `calculate_emissions`, `optimize_voyage`,
`get_historical_voyages`, `get_latest_optimization`. The loop runs up to four iterations, then
answers.

With no API key the mock agent plans which tools to call from the question, calls them for real,
and fills a template from the JSON they return. The numbers are identical either way — only the
prose differs.

Things worth asking:

- "Optimize this voyage for minimum fuel"
- "Why did you choose this route?"
- "What happens if I increase speed to 14 knots?"
- "Compare this voyage with the last five voyages"
- "What is the weather on this route?"
- "How much fuel can we save?"

---

## Demo walkthrough

1. Dashboard — fleet KPIs, active voyages with N.A.V. alerts, pending recommendations, chart.
2. Click a voyage with an ETA-slip alert.
3. Read the particulars strip and the weather panel; note the source badge.
4. Set an objective, add a maximum speed or a required arrival, run the optimization.
5. Watch the stages, then compare the four options; click one to highlight it on the chart.
6. Read "Why N.A.V. recommends this", then approve, reject or modify.
7. Ask the assistant why it chose that route, then ask a what-if at a different speed.
8. Vessel page — historical predicted against actual fuel.
9. Analytics — fleet fuel, CO2 and model bias.
10. Plan a voyage from the Voyages page and watch the backend route and cost it.

---

## Deployment

New to Render? `RENDER.md` is a click-by-click walkthrough for exactly that,
including the one command that prepares the repository.

See `DEPLOY.md` for the other options. Because the frontend exports to static files, the default
shape is a single service: FastAPI serves both the API and the app. Four
routes are covered — office LAN, Render free, Netlify plus a separate API
host, and a small VPS with Caddy. `render.yaml`, `frontend/netlify.toml` and
the systemd units in `deploy/` are included and configured.

Two things to read before putting it on the public internet: there is no
authentication, and the free Open-Meteo API is licensed for non-commercial use
only. Both are covered in `DEPLOY.md`.

---

## Honest limits

- All fleet, voyage, position, bunker-price and historical data is **seeded demo data**. Vessel
  names and IMO numbers are invented. Port coordinates are real.
- Weather is live only when Open-Meteo answers; otherwise it is synthetic and labelled as such.
- The weather resistance model, the fixed auxiliary load and the risk-index weights are
  prototype heuristics with the constants in one place (`backend/app/config.py`). They are not
  calibrated against sea trials.
- Routing follows a coarse lane graph, not a bathymetric or ENC-based router, and ignores ice,
  piracy zones, canal slots and traffic separation schemes.
- Nothing here is a substitute for a bridge team, a class-approved routing service or a
  compliance filing.
