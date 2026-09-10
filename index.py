"""Human-facing index at the API root.

Everything else the API serves is JSON for machines. This one route exists
because a deployed prototype's primary URL gets opened in a browser, and a
404 body is a poor answer to that. It links to the endpoints that do exist
and is explicit about what is not built yet.

Self-contained: no external stylesheet, font or script, so it renders on a
ship's terminal with no internet exactly as it does anywhere else.
"""

from __future__ import annotations

from fastapi import APIRouter, Response
from fastapi.responses import HTMLResponse

from app.api.dependencies import HealthServiceDep

router = APIRouter(include_in_schema=False)

_PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>N.A.V. API</title>
<style>
  :root {{
    color-scheme: dark;
    --canvas: #06121c; --surface: #0d2032; --hairline: #1c3244;
    --ink: #dce8f2; --muted: #7d97ad; --primary: #4fa3e3; --signal: #e8a33d;
  }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0; padding: 3rem 1.5rem; background: var(--canvas); color: var(--ink);
    font: 15px/1.6 ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif;
  }}
  main {{ max-width: 46rem; margin: 0 auto; }}
  .mark {{
    font-family: ui-monospace, "SF Mono", Menlo, monospace;
    letter-spacing: .22em; color: var(--primary); font-size: 1.1rem;
  }}
  h1 {{ font-size: 1.35rem; font-weight: 600; margin: .35rem 0 .25rem; }}
  p {{ color: var(--muted); margin: .35rem 0 0; }}
  .tag {{
    display: inline-block; margin-top: 1.25rem; padding: .15rem .5rem;
    border: 1px solid rgba(232,163,61,.4); background: rgba(232,163,61,.1);
    color: var(--signal); border-radius: 3px; font-size: .75rem;
  }}
  ul {{ list-style: none; padding: 0; margin: 2rem 0 0;
       border: 1px solid var(--hairline); border-radius: 3px; background: var(--surface); }}
  li {{ display: flex; gap: 1rem; align-items: baseline;
       padding: .7rem 1rem; border-bottom: 1px solid var(--hairline); }}
  li:last-child {{ border-bottom: 0; }}
  a {{ color: var(--primary); font-family: ui-monospace, Menlo, monospace;
       text-decoration: none; min-width: 12rem; }}
  a:hover {{ text-decoration: underline; }}
  span {{ color: var(--muted); font-size: .875rem; }}
  footer {{ margin-top: 2rem; color: var(--muted); font-size: .8125rem; }}
  code {{ font-family: ui-monospace, Menlo, monospace; color: var(--ink); }}
</style>
</head>
<body>
<main>
  <div class="mark">N.A.V.</div>
  <h1>Nautical Agentic Navigator</h1>
  <p>Intelligence for Every Voyage.</p>
  <div class="tag">{phase} &middot; v{version} &middot; {environment}</div>

  <ul>
    <li><a href="/docs">/docs</a><span>Interactive API documentation</span></li>
    <li><a href="/health">/health</a><span>Liveness — depends on nothing</span></li>
    <li><a href="/ready">/ready</a><span>Readiness, per dependency</span></li>
    <li><a href="/api/v1/meta">/api/v1/meta</a><span>Version and provider status</span></li>
  </ul>

  <footer>
    This is the API. The operations console is a separate service.
    No vessel, voyage or optimisation endpoint exists yet — the left rail of
    the console lists each screen against the phase that builds it.
    Providers currently returning mock data: <code>{mocked}</code>.
  </footer>
</main>
</body>
</html>
"""


@router.get("/", response_class=HTMLResponse, summary="API index")
async def index(service: HealthServiceDep) -> HTMLResponse:
    """A browsable index of the endpoints that exist."""
    meta = service.meta()
    return HTMLResponse(
        _PAGE.format(
            phase=meta.phase,
            version=meta.version,
            environment=meta.environment,
            mocked=", ".join(meta.mock_providers) or "none",
        )
    )


@router.get("/favicon.ico")
async def favicon() -> Response:
    """No icon to serve; answer cleanly instead of logging a 404 per page view."""
    return Response(status_code=204)
