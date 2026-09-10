# N.A.V. — Nautical Agentic Navigator

**Intelligence for Every Voyage.**

Project report · v1 prototype · September 2026

---

## 1. What N.A.V. actually is

N.A.V. is a decision-support tool for the people who plan and watch over
merchant voyages. It answers one question, repeatedly and with its working
shown:

> This ship is going from A to B. What speed and what track should she keep,
> and what does that choice cost in fuel, in time and in CO2?

That question already gets answered every day — in spreadsheets, in a
superintendent's head, in emails between the operator and the master. It gets
answered inconsistently, without the weather properly folded in, and without
anyone able to reconstruct later why 12.5 knots was chosen over 14.

N.A.V. does three things about that.

**It calculates instead of guessing.** For a given voyage it builds four real
route options through actual sea lanes, samples the weather along each one,
and computes fuel burn, arrival time and emissions for each. Cube-law
propulsion, IMO carbon factors, current assist on the ETA. Every number is
arithmetic in Python, auditable in one config file.

**It recommends, with a reason.** The four options are scored against an
objective the operator picks — minimum fuel, fastest arrival, minimum
emissions, or balanced. The best-scoring one is surfaced with a written
rationale: what it saves, what it costs in time, what the weather looks like on
that track. If the laycan or a speed limit rules out every option, it says so
and names the breach instead of inventing a compromise.

**It leaves the decision with a human.** Every recommendation sits as *pending*
until someone approves, rejects, or modifies it. Approval updates the voyage
plan in the database. Nothing is sent to a vessel. Nothing is automated.

### What "agentic" means here, precisely

There is a conversational assistant, and this is the part usually done badly,
so it is worth being exact about the design.

The language model has **no numerical authority**. It cannot state a fuel
figure. What it can do is choose which of ten backend tools to call —
`get_voyage`, `get_weather`, `get_routes`, `calculate_fuel`, `calculate_eta`,
`calculate_emissions`, `optimize_voyage`, `get_historical_voyages`, and two
others — read the JSON they return, and put it into a sentence. Ask "what
happens if I increase speed to 14 knots?" and it calls the same fuel and ETA
calculators the interface uses, then reports what they said.

The consequence: the assistant cannot hallucinate a saving, because it never
produces a number, only relays one. With no OpenAI key configured, a built-in
mock agent picks the tools by keyword and fills a template from the identical
JSON. The figures are the same either way. Only the prose differs.

### Who would use it

An operations desk or a fleet performance team. The dashboard is the morning
view — which ships need attention, where a schedule is slipping, where there is
a saving on the table. The voyage page is the working view: chart, weather,
options, recommendation, decision.

### What it is not

Not a bridge system, not a class-approved routing service, not connected to any
vessel, and not a compliance filing tool. The fleet in it is invented. It is a
prototype that demonstrates a way of working, at a level of engineering where
the maths would survive review.

---

## 2. What was built

**5,544 lines of Python. 3,883 of TypeScript. 32 passing tests. One deployable
service.**

### Backend — FastAPI, SQLAlchemy, SQLite

13 tables and roughly 30 endpoints under `/api/v1`.

- **Routing.** A hand-built graph of 57 ocean waypoints and the lanes joining
  them — Malacca, Suez, Gibraltar, Cape of Good Hope, Panama, Hormuz, Sunda —
  with Dijkstra over great-circle legs. Checked against published distances:
  Singapore to Rotterdam via Suez comes out at 8,419 NM.
- **Weather.** Sampled along the track from Open-Meteo (free, no key, batched
  and cached), degrading silently to a deterministic mock provider when it is
  unreachable. Pierson-Moskowitz wave heights from wind speed, storm belts near
  47° north and south. Every sample records which source produced it.
- **Fuel.** Base consumption scaled by the cube of the speed ratio, multiplied
  by a weather resistance factor capped at 1.60, plus a fixed auxiliary load.
- **ETA.** Speed made good including the along-track current component, plus a
  port allowance.
- **Emissions.** Fuel mass times the IMO MEPC.336(76) / EU MRV carbon factor
  for the grade — HSFO 3.114, VLSFO 3.151, MGO 3.206, LNG 2.750 — with CO2 per
  nautical mile and AER.
- **Optimizer.** Four variants (fastest, fuel efficient, weather optimized, eco
  slow steam) fully evaluated, constraints applied, survivors min-max
  normalized and weighted by objective. Lowest score wins. Every exclusion
  carries its reason.

### Agent — provider-agnostic

Ten tools with OpenAI-format schemas, a four-iteration loop, chat history and
run persistence. OpenAI when a key is present; the mock planner otherwise.

### Frontend — Next.js 14, TypeScript, Tailwind, MapLibre GL, Recharts

Nine routes: dashboard, fleet, vessels, vessel detail, voyages, voyage detail,
optimization workspace, analytics, voyage planner. MapLibre renders a bundled
offline chart (Natural Earth land, 135 KB) with no tile key and no network.
Recharts covers predicted-against-actual fuel, fuel by vessel and CO2 by month.
The assistant panel shows the agent's tool calls as they complete. Every
recommendation carries approve, reject and modify.

Dark instrument-panel palette, IBM Plex Sans and Mono, monospace reserved for
figures, coordinates and timestamps.

### Data

A deterministic seed: 5 companies, 10 vessels, 23 voyages, 120 positions, 60
completed historical voyages, 20 bunker prices, and 5 pending recommendations
produced by running the real optimizer. Same fleet every time.

### Deployment

The frontend exports to static files, which the backend serves — one process,
one URL, no CORS. Ships with a Render blueprint, a Netlify config, systemd
units, a Caddyfile, a one-command prepare script, and a click-by-click Render
walkthrough.

---

## 3. Rating

**7.5 / 10 as a v1 prototype.**

| Dimension | Score | Note |
| --- | --- | --- |
| Backend correctness | 9 | Formulas sourced and tested; routing distance-checked; constraints handled honestly |
| Agent design | 8 | Clean tool boundary, sound mock fallback; the mock templates are rigid |
| Deployment story | 8.5 | Single service, tested end to end; the Docker route is unverified |
| Documentation | 8.5 | README, DEPLOY, RENDER, plus a stated-limits section |
| Frontend code | 7 | Builds clean and fully typed, but no tests and some duplication |
| Visual result | unrated | Never seen rendered in a browser |
| Production readiness | 3 | No authentication, no persistence strategy, no observability |
| Domain depth | 5 | CO2 only — no FuelEU GHG intensity, no CII rating, no EU ETS allowances |

Two caveats worth stating plainly.

The frontend was verified by build output and HTTP status codes, never by
looking at rendered pixels. Layout, spacing, and whether the map actually draws
are unconfirmed until someone opens it.

The domain-depth score matters most. This optimizes fuel and CO2. That is one
slice of maritime compliance work, and the narrowest one.

### Honest limits

- All fleet, voyage, position, price and history data is seeded fiction. Vessel
  names and IMO numbers are invented. Port coordinates and emission factors are
  real.
- Weather is live only when Open-Meteo answers; otherwise synthetic and
  labelled as such. The free Open-Meteo API is licensed for non-commercial use.
- The weather resistance model, the fixed auxiliary load and the risk weights
  are prototype heuristics, not calibrated against sea trials.
- Routing uses a coarse lane graph — no bathymetry, no ENC, no ice, piracy
  zones, canal slots or traffic separation schemes.
- There is no authentication of any kind.

---

## 4. Upgrade map — which files matter

### Tuning the maths

| File | What lives there |
| --- | --- |
| `backend/app/config.py` | **Start here.** Every constant: emission factors, cube-law exponent, weather-resistance coefficients, auxiliary load, risk bands, objective weights, route variants. Recalibration is this file and nothing else. |

### Changing behaviour

| File | Lines | What it controls |
| --- | --- | --- |
| `backend/app/services/optimizer.py` | 435 | Scoring, normalization, constraint handling, rationale text |
| `backend/app/services/routing.py` | — | Graph build, Dijkstra, variant geometry |
| `backend/app/services/ports.py` | — | Ports, waypoints, lanes. Add canals, ice or piracy zones here |
| `backend/app/services/weather.py` | 329 | Provider abstraction. A paid marine feed is one new class |
| `backend/app/services/fuel.py`, `emissions.py` | — | Where FuelEU, CII and EU ETS attach |

### Extending the agent

| File | Lines | What to change |
| --- | --- | --- |
| `backend/app/services/agent.py` | 681 | A new tool is one function, one schema entry, one `TOOL_LABELS` line |
| `backend/app/ai/prompts.py` | — | System prompt and mock answer builders. Add a tool, and the mock planner here needs to know about it |
| `backend/app/ai/provider.py` | 255 | Swapping OpenAI for another provider |

### Contract changes ripple in pairs

- `backend/app/schemas.py` ↔ `frontend/types/index.ts`
- `backend/app/api/*.py` ↔ `frontend/lib/api.ts`

Change one without the other and nothing catches it — the API boundary is
untyped across the wire. This is the most likely source of a runtime bug.

### Interface work

| File | Lines | Note |
| --- | --- | --- |
| `frontend/components/optimization/OptimizationPanel.tsx` | 493 | Main interaction surface and the largest frontend file. Split it before it grows |
| `frontend/components/map/MapView.tsx` | 260 | The only file touching MapLibre |
| `frontend/app/globals.css`, `tailwind.config.ts` | — | All design tokens |
| `backend/seed.py` | 416 | The demo fleet |

### Known wart

`OPTION_COLORS` is duplicated in `frontend/components/voyage/VoyageDetailView.tsx`
and `frontend/app/optimization/page.tsx`. Adding a fifth route variant means
editing three files. Lift it into `lib/format.ts` on the first pass.

### Highest-value next steps, in order

1. **FuelEU GHG intensity, CII rating, EU ETS allowances.** The actual domain,
   and the gap between a fuel tool and a compliance tool.
2. **Authentication.** Currently anyone with the URL can approve a
   recommendation.
3. **Postgres.** Already supported by a URL change; needed the moment two
   people use it at once.
4. **Frontend tests, and a browser pass over the layout.**
