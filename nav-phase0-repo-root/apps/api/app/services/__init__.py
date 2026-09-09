"""Domain services.

Business logic lives here, never in route handlers. Phase 3 adds the
weather, routing, fuel, ETA and emissions services; Phase 4 the optimizer.
"""

from app.services.health_service import HealthService

__all__ = ["HealthService"]
