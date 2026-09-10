"""LLM provider abstraction.

The agent loop is identical for both providers: a provider is asked for the
next step and may answer with text or with tool calls. MockAIProvider plans
tool calls with keyword rules, so the whole product works with no API key.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

from ..config import settings
from . import prompts


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict


@dataclass
class AIResponse:
    text: str | None = None
    tool_calls: list[ToolCall] = field(default_factory=list)


class AIProvider:
    name = "base"
    model: str | None = None

    def complete(self, messages: list[dict], tools: list[dict]) -> AIResponse:
        raise NotImplementedError


# ---------------------------------------------------------------------------
# OpenAI
# ---------------------------------------------------------------------------


class OpenAIProvider(AIProvider):
    name = "openai"

    def __init__(self, api_key: str, model: str):
        from openai import OpenAI  # imported lazily so the package stays optional

        self.client = OpenAI(api_key=api_key)
        self.model = model

    def complete(self, messages: list[dict], tools: list[dict]) -> AIResponse:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=[{"type": "function", "function": t} for t in tools],
            temperature=0.2,
        )
        choice = response.choices[0].message
        calls = []
        for call in choice.tool_calls or []:
            try:
                args = json.loads(call.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {}
            calls.append(ToolCall(id=call.id, name=call.function.name, arguments=args))
        return AIResponse(text=choice.content, tool_calls=calls)


# ---------------------------------------------------------------------------
# Mock
# ---------------------------------------------------------------------------

OBJECTIVE_KEYWORDS = [
    ("MIN_EMISSIONS", ("emission", "co2", "carbon", "greenest")),
    ("MIN_FUEL", ("minimum fuel", "least fuel", "save fuel", "fuel saving", "cheapest", "min fuel")),
    ("FASTEST", ("fastest", "quickest", "asap", "soonest", "earliest arrival")),
    ("BALANCED", ("balanced", "best overall", "recommend")),
]


class MockAIProvider(AIProvider):
    """Deterministic keyword planner. No external calls, no invented numbers."""

    name = "mock"
    model = "nav-mock-agent"

    def complete(self, messages: list[dict], tools: list[dict]) -> AIResponse:
        user_text = ""
        for m in reversed(messages):
            if m["role"] == "user":
                user_text = m["content"]
                break
        text = user_text.lower()
        results = self._tool_results(messages)

        if results:
            return AIResponse(text=self._answer(text, results))

        context_voyage = self._context_voyage(messages)
        return AIResponse(tool_calls=self._plan(text, context_voyage))

    # -- planning ----------------------------------------------------------

    def _plan(self, text: str, voyage_id: int | None) -> list[ToolCall]:
        args: dict = {"voyage_id": voyage_id} if voyage_id else {}

        if any(k in text for k in ("compare", "previous voyage", "last five", "history", "historical")):
            return [ToolCall("mock-1", "get_historical_voyages", dict(args))]

        if any(k in text for k in ("why", "explain", "reason", "justify")):
            return [ToolCall("mock-1", "get_latest_optimization", dict(args))]

        if any(k in text for k in ("weather", "wind", "wave", "sea state", "swell", "storm")):
            return [ToolCall("mock-1", "get_weather", dict(args))]

        speed_match = re.search(r"(\d{1,2}(?:\.\d)?)\s*(?:kn|knot)", text)
        if speed_match and any(k in text for k in ("if", "what happens", "increase", "reduce", "at ")):
            return [
                ToolCall(
                    "mock-1",
                    "calculate_fuel",
                    {**args, "speed_kn": float(speed_match.group(1))},
                )
            ]

        if any(k in text for k in ("eta", "arrival", "delay", "late", "on time")):
            return [ToolCall("mock-1", "calculate_eta", dict(args))]

        if any(k in text for k in ("route", "options", "alternative")) and "optimi" not in text:
            return [ToolCall("mock-1", "get_routes", dict(args))]

        if any(k in text for k in ("optimi", "save fuel", "recommend", "best option", "minimum fuel", "fastest", "lowest emission")):
            objective = "BALANCED"
            for value, keywords in OBJECTIVE_KEYWORDS:
                if any(k in text for k in keywords):
                    objective = value
                    break
            return [
                ToolCall("mock-1", "optimize_voyage", {**args, "objective": objective})
            ]

        if any(k in text for k in ("vessel", "ship", "imo", "consumption")):
            return [ToolCall("mock-1", "get_vessel", dict(args))]

        if voyage_id or "voyage" in text:
            return [ToolCall("mock-1", "get_voyage", dict(args))]

        return []

    # -- answering ---------------------------------------------------------

    def _answer(self, text: str, results: list[tuple[str, dict]]) -> str:
        name, payload = results[-1]
        builders = {
            "optimize_voyage": prompts.optimization_answer,
            "get_latest_optimization": prompts.explain_answer,
            "get_weather": prompts.weather_answer,
            "get_historical_voyages": prompts.history_answer,
            "calculate_fuel": prompts.fuel_answer,
            "calculate_eta": _eta_answer,
            "get_voyage": prompts.voyage_answer,
            "get_vessel": _vessel_answer,
            "get_routes": _routes_answer,
            "calculate_emissions": _emissions_answer,
        }
        builder = builders.get(name)
        if builder is None:
            return prompts.FALLBACK_ANSWER
        return builder(payload)

    @staticmethod
    def _tool_results(messages: list[dict]) -> list[tuple[str, dict]]:
        out: list[tuple[str, dict]] = []
        for m in messages:
            if m.get("role") == "tool":
                try:
                    out.append((m.get("name", ""), json.loads(m["content"])))
                except (json.JSONDecodeError, KeyError):
                    continue
        return out

    @staticmethod
    def _context_voyage(messages: list[dict]) -> int | None:
        for m in messages:
            if m["role"] == "system":
                match = re.search(r"active voyage id: (\d+)", m["content"])
                if match:
                    return int(match.group(1))
        return None


def _eta_answer(result: dict) -> str:
    if result.get("error"):
        return f"I couldn't calculate the ETA: {result['error']}"
    return (
        f"At {result['speed_kn']} kn over {result['distance_nm']:,.0f} NM the passage takes "
        f"{result['duration_hours']} h ({result['sea_hours']} h at sea plus "
        f"{result['port_allowance_hours']} h allowance).\nETA {result['eta_utc']} UTC."
    )


def _vessel_answer(result: dict) -> str:
    if result.get("error"):
        return f"I couldn't find that vessel: {result['error']}"
    return (
        f"{result['name']} (IMO {result['imo']}) — {result['vessel_type']}, "
        f"{result['deadweight_t']:,.0f} DWT.\n"
        f"Design speed {result['design_speed_kn']} kn, currently {result['current_speed_kn']} kn at "
        f"{result['latitude']}, {result['longitude']}.\n"
        f"Burns {result['base_consumption_mt_per_day']} MT/day of {result['fuel_type']} at design speed."
    )


def _routes_answer(result: dict) -> str:
    if result.get("error"):
        return f"I couldn't generate routes: {result['error']}"
    lines = [f"{len(result['routes'])} route options from the waypoint network:"]
    for r in result["routes"]:
        via = " via " + ", ".join(r["via"][:3]) if r.get("via") else ""
        lines.append(f"- {r['label']}: {r['distance_nm']:,.0f} NM at {r['speed_kn']} kn{via}")
    return "\n".join(lines)


def _emissions_answer(result: dict) -> str:
    if result.get("error"):
        return f"I couldn't calculate emissions: {result['error']}"
    return (
        f"{result['fuel_mt']} MT of {result['fuel_type']} produces {result['co2_mt']} MT of CO2 "
        f"(factor {result['emission_factor']} t CO2 per t fuel, IMO/EU MRV default)."
    )


# ---------------------------------------------------------------------------

_provider: AIProvider | None = None


def get_ai_provider() -> AIProvider:
    global _provider
    if _provider is None:
        if settings.openai_api_key:
            try:
                _provider = OpenAIProvider(settings.openai_api_key, settings.openai_model)
            except Exception:  # noqa: BLE001 - missing package or bad key
                _provider = MockAIProvider()
        else:
            _provider = MockAIProvider()
    return _provider


def reset_provider() -> None:
    global _provider
    _provider = None
