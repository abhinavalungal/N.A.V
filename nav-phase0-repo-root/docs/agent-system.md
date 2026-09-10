# Agent system

Planned for Phase 5. Nothing in `apps/api/app/agents` is implemented yet.

## Boundary

The agent may: interpret a request, plan, choose tools, call them within its
budget, and write an explanation grounded in what those tools returned.

The agent may not: compute a number, reach the database directly, issue
arbitrary HTTP requests, touch the filesystem or shell, or take a
safety-critical action without a recorded human approval.

## Loop

    intent -> plan -> select tools -> execute -> validate results
           -> optimise -> recommend -> constraint check
           -> human approval -> action -> outcome

The loop is bounded, never open-ended: `AGENT_MAX_TOOL_CALLS`,
`AGENT_MAX_ITERATIONS` and `AGENT_TIMEOUT_SECONDS` are configuration, and a run
that hits a limit ends with a clear failure rather than looping.

## Tools

Each tool declares a name, description, input schema, output schema, required
permission, and a risk level:

    READ_ONLY           vessel, voyage, position, weather, route lookups
    LOW_RISK            run optimisation, create recommendation
    REQUIRES_APPROVAL   send a voyage plan, change operational parameters
    PROHIBITED          autonomous navigation

Every call is validated against its schema, authorised against the caller's
permissions and company, logged to `tool_calls`, and attached to its
`agent_run_id`.

## Explanations

Concise reasoning summaries, not chain-of-thought. Every figure in an
explanation traces to a tool output; if a value is missing the agent says so.

> Option 2 is recommended: 6.2% less estimated fuel than the fastest option,
> arriving 2.1 hours later, within the required arrival window, at lower
> weather risk.

## Untrusted text

Master messages, uploaded documents, emails and third-party API text are data,
never instructions. They cannot change system policy, tool permissions or
approval state. A message that reads like an approval is not an approval - only
a recorded approval action is.

## Observability

Each run stores `agent_run_id`, parent run, agent name, prompt version, model,
start and end time, status, tools called, token usage, error and final
recommendation. Prompts are versioned (`NAV_AGENT_PROMPT_VERSION`) and the
version is stored with the run, so a past decision can be reconstructed.
