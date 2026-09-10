"""External provider abstractions (LLM, weather, routing, fuel, vessel).

Interfaces plus mock implementations land in Phase 3 (weather/routing) and
Phase 5 (LLM). The application depends on the interface, never on a vendor.
"""
