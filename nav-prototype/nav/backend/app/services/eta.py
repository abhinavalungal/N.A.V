"""ETA calculation. Backend maths only - the LLM just explains the result."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from ..config import MAX_CURRENT_EFFECT_KN, PORT_ALLOWANCE_HOURS


@dataclass
class EtaResult:
    duration_hours: float
    sea_hours: float
    port_allowance_hours: float
    effective_speed_kn: float
    eta_utc: datetime

    def to_dict(self) -> dict:
        return {
            "duration_hours": self.duration_hours,
            "sea_hours": self.sea_hours,
            "port_allowance_hours": self.port_allowance_hours,
            "effective_speed_kn": self.effective_speed_kn,
            "eta_utc": self.eta_utc.isoformat(),
        }


def calculate_eta(
    distance_nm: float,
    speed_kn: float,
    departure_utc: datetime,
    current_assist_kn: float = 0.0,
    port_allowance_hours: float = PORT_ALLOWANCE_HOURS,
) -> EtaResult:
    """distance / speed, adjusted for ocean current, plus a port allowance.

    `current_assist_kn` is positive when the current pushes the vessel along
    the route and negative when it sets against her.
    """
    if speed_kn <= 0:
        raise ValueError("speed_kn must be positive")
    if distance_nm < 0:
        raise ValueError("distance_nm cannot be negative")

    assist = max(-MAX_CURRENT_EFFECT_KN, min(MAX_CURRENT_EFFECT_KN, current_assist_kn))
    effective = max(1.0, speed_kn + assist)
    sea_hours = distance_nm / effective
    total = sea_hours + port_allowance_hours
    return EtaResult(
        duration_hours=round(total, 2),
        sea_hours=round(sea_hours, 2),
        port_allowance_hours=port_allowance_hours,
        effective_speed_kn=round(effective, 2),
        eta_utc=departure_utc + timedelta(hours=total),
    )
