from __future__ import annotations

from datetime import datetime, timedelta

from custom_components.eplucon.brine import (
    BrineMonthlyStats,
    BrineStatsConfig,
)


def test_brine_stats_wait_for_validity_before_sampling() -> None:
    """The tracker should only sample after the validity window has elapsed."""
    config = BrineStatsConfig(
        pump_threshold=5.0,
        valid_after=timedelta(minutes=15),
        sample_interval=timedelta(minutes=5),
    )
    now = datetime(2026, 5, 9, 12, 0, 0)
    stats = BrineMonthlyStats(month_key="2026-05")

    assert not stats.update(
        now=now,
        config=config,
        pump_percentage=6.0,
        brine_temperature=11.5,
    )
    assert stats.sample_count == 0
    assert stats.valid_temperature(now, config, 11.5) is None

    later = now + timedelta(minutes=14, seconds=59)
    assert not stats.update(
        now=later,
        config=config,
        pump_percentage=6.0,
        brine_temperature=11.8,
    )
    assert stats.sample_count == 0

    valid_at = now + timedelta(minutes=15)
    assert stats.update(
        now=valid_at,
        config=config,
        pump_percentage=6.0,
        brine_temperature=12.0,
    )
    assert stats.sample_count == 1
    assert stats.monthly_mean == 12.0
    assert stats.valid_temperature(valid_at, config, 12.0) == 12.0


def test_brine_stats_sample_interval_and_month_reset() -> None:
    """The tracker should rate-limit samples and reset when a new month starts."""
    config = BrineStatsConfig(
        pump_threshold=5.0,
        valid_after=timedelta(minutes=15),
        sample_interval=timedelta(minutes=5),
    )
    started_at = datetime(2026, 5, 31, 23, 40, 0)
    stats = BrineMonthlyStats(month_key="2026-05", run_started_at=started_at)

    first_valid_sample = started_at + timedelta(minutes=15)
    assert stats.update(
        now=first_valid_sample,
        config=config,
        pump_percentage=10.0,
        brine_temperature=8.0,
    )
    assert stats.monthly_mean == 8.0

    too_soon = first_valid_sample + timedelta(minutes=4, seconds=59)
    assert not stats.update(
        now=too_soon,
        config=config,
        pump_percentage=10.0,
        brine_temperature=10.0,
    )
    assert stats.sample_count == 1

    second_sample = first_valid_sample + timedelta(minutes=5)
    assert stats.update(
        now=second_sample,
        config=config,
        pump_percentage=10.0,
        brine_temperature=10.0,
    )
    assert stats.monthly_mean == 9.0

    next_month = datetime(2026, 6, 1, 0, 0, 10)
    assert stats.update(
        now=next_month,
        config=config,
        pump_percentage=10.0,
        brine_temperature=7.5,
    )
    assert stats.month_key == "2026-06"
    assert stats.sample_count == 0
    assert stats.monthly_mean is None


def test_brine_stats_restore_persistent_state_only() -> None:
    """Restoring statistics should not restore transient validity timers."""
    now = datetime(2026, 5, 9, 12, 0, 0)
    restored = BrineMonthlyStats.from_dict(
        {
            "month_key": "2026-05",
            "temperature_sum": 30.0,
            "sample_count": 3,
        },
        now=now,
    )

    assert restored.month_key == "2026-05"
    assert restored.monthly_mean == 10.0
    assert restored.run_started_at is None
    assert restored.last_sample_at is None
    assert restored.as_dict() == {
        "month_key": "2026-05",
        "temperature_sum": 30.0,
        "sample_count": 3,
    }
