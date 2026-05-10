from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any


def get_month_key(now: datetime) -> str:
    """Return the local year-month key for the current statistics bucket."""
    return now.strftime("%Y-%m")


@dataclass(slots=True, kw_only=True)
class BrineStatsConfig:
    """Runtime configuration for brine validity tracking."""

    pump_threshold: float
    valid_after: timedelta
    sample_interval: timedelta


@dataclass(slots=True, kw_only=True)
class BrineMonthlyStats:
    """Track brine temperature samples for the current month."""

    month_key: str
    temperature_sum: float = 0.0
    sample_count: int = 0
    run_started_at: datetime | None = None
    last_sample_at: datetime | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any], *, now: datetime) -> BrineMonthlyStats:
        """Restore persisted monthly statistics."""
        return cls(
            month_key=str(data.get("month_key") or get_month_key(now)),
            temperature_sum=float(data.get("temperature_sum", 0.0)),
            sample_count=int(data.get("sample_count", 0)),
        )

    def as_dict(self) -> dict[str, Any]:
        """Return the persistent subset of the monthly statistics."""
        return {
            "month_key": self.month_key,
            "temperature_sum": self.temperature_sum,
            "sample_count": self.sample_count,
        }

    @property
    def monthly_mean(self) -> float | None:
        """Return the monthly mean temperature."""
        if self.sample_count == 0:
            return None
        return self.temperature_sum / self.sample_count

    def is_valid(self, now: datetime, config: BrineStatsConfig) -> bool:
        """Return if the pump has been active long enough to trust brine input."""
        return (
            self.run_started_at is not None
            and now - self.run_started_at >= config.valid_after
        )

    def valid_temperature(
        self,
        now: datetime,
        config: BrineStatsConfig,
        brine_temperature: float | None,
    ) -> float | None:
        """Return the current brine temperature only while the source is valid."""
        if not self.is_valid(now, config):
            return None
        return brine_temperature

    def update(
        self,
        *,
        now: datetime,
        config: BrineStatsConfig,
        pump_percentage: float | None,
        brine_temperature: float | None,
    ) -> bool:
        """Update monthly statistics from the latest coordinator sample."""
        changed = False
        sampled = False
        current_month_key = get_month_key(now)

        if pump_percentage is None or pump_percentage <= config.pump_threshold:
            self.run_started_at = None
            self.last_sample_at = None
            if self.month_key != current_month_key:
                self.month_key = current_month_key
                self.temperature_sum = 0.0
                self.sample_count = 0
                changed = True
            return changed

        if self.run_started_at is None:
            self.run_started_at = now

        if not self.is_valid(now, config) or brine_temperature is None:
            if self.month_key != current_month_key:
                self.month_key = current_month_key
                self.temperature_sum = 0.0
                self.sample_count = 0
                self.run_started_at = None
                self.last_sample_at = None
                changed = True
            return changed

        if (
            self.last_sample_at is None
            or now - self.last_sample_at >= config.sample_interval
        ):
            self.temperature_sum += brine_temperature
            self.sample_count += 1
            self.last_sample_at = now
            changed = True
            sampled = True

        if self.month_key != current_month_key and not sampled:
            self.month_key = current_month_key
            self.temperature_sum = 0.0
            self.sample_count = 0
            self.run_started_at = None
            self.last_sample_at = None
            changed = True

        return changed
