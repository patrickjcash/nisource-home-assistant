"""DataUpdateCoordinator for NiSource."""
from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import datetime, timedelta, timezone

from homeassistant.components.recorder import get_instance
from homeassistant.components.recorder.statistics import (
    StatisticData,
    StatisticMetaData,
    async_add_external_statistics,
    statistics_during_period,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import NiSourceAPI
from .const import (
    CONSUMPTION_METADATA,
    COST_METADATA,
    STATISTIC_CONSUMPTION,
    STATISTIC_COST,
    UPDATE_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)

# Earliest date to search for stored statistics when anchoring the running sum
HISTORY_START = datetime(2000, 1, 1, tzinfo=timezone.utc)


class NiSourceCoordinator(DataUpdateCoordinator):
    """NiSource data update coordinator."""

    def __init__(self, hass: HomeAssistant, api: NiSourceAPI) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name="NiSource",
            update_interval=timedelta(seconds=UPDATE_INTERVAL),
        )
        self.api = api

    async def _async_update_data(self) -> dict:
        """Fetch data from API and insert statistics."""
        try:
            # Authenticate and fetch data
            await self.hass.async_add_executor_job(self.api.authenticate)

            usage_csv = await self.hass.async_add_executor_job(
                self.api.get_usage_history_csv
            )
            billing_csv = await self.hass.async_add_executor_job(
                self.api.get_billing_history_csv
            )
            account_summary = await self.hass.async_add_executor_job(
                self.api.get_account_summary
            )

            data = {
                "usage": usage_csv,
                "billing": billing_csv,
                "account": account_summary,
            }

            # Insert statistics for Energy Dashboard
            await self._insert_statistics(data)

            return data
        except Exception as err:
            raise UpdateFailed(f"Error communicating with API: {err}") from err

    async def _insert_statistics(self, data: dict) -> None:
        """Insert long-term statistics for consumption and cost.

        NiSource only provides one row per billing period, so each bill becomes
        a single statistic on its read date. The Energy Dashboard uses these
        statistics, not the sensor values directly.
        """
        usage_csv = data.get("usage", [])
        if not usage_csv:
            _LOGGER.debug("No usage history data available")
            return

        await self._import_statistics(
            usage_csv,
            "Units Used",
            float,
            STATISTIC_CONSUMPTION,
            CONSUMPTION_METADATA,
        )
        await self._import_statistics(
            usage_csv,
            "Bill Amount",
            self.api.parse_currency,
            STATISTIC_COST,
            COST_METADATA,
        )

    async def _import_statistics(
        self,
        usage_csv: list[dict[str, str]],
        column: str,
        parse: Callable[[str], float],
        statistic_id: str,
        metadata: StatisticMetaData,
    ) -> None:
        """Import every bill-period row in the CSV, anchored to stored history.

        NiSource's CSV is a rolling window of bills. Every refresh rewrites all
        rows in the window, with the running sum anchored to the stored statistic
        at (or just before) the oldest row. This keeps sums continuous as old rows
        fall out of the window, and repairs sums written by earlier versions.
        """
        # CSV is ordered newest-to-oldest, so reverse it for chronological order
        rows: list[tuple[datetime, float]] = []
        for row in reversed(usage_csv):
            date_str = row.get("Date")
            value_str = self.api.get_csv_value(row, column)
            if not date_str or not value_str:
                continue
            try:
                rows.append(
                    (
                        self.api.parse_date(date_str).replace(tzinfo=timezone.utc),
                        parse(value_str),
                    )
                )
            except (ValueError, TypeError) as err:
                _LOGGER.warning("Failed to parse %s from row %s: %s", column, row, err)

        if not rows:
            return

        oldest = rows[0][0]
        try:
            stored = await get_instance(self.hass).async_add_executor_job(
                statistics_during_period,
                self.hass,
                HISTORY_START,
                oldest + timedelta(hours=1),
                {statistic_id},
                "hour",
                None,
                {"state", "sum"},
            )
        except Exception as err:
            _LOGGER.warning("Failed to read stored statistics for %s: %s", statistic_id, err)
            return

        # Sum of everything recorded before the oldest row in the window
        running_sum = 0.0
        if anchor_rows := stored.get(statistic_id):
            anchor = anchor_rows[-1]
            running_sum = anchor.get("sum") or 0.0
            if anchor["start"] >= oldest.timestamp():
                running_sum -= anchor.get("state") or 0.0

        statistics = []
        for start, value in rows:
            running_sum += value
            statistics.append(StatisticData(start=start, state=value, sum=running_sum))

        _LOGGER.debug(
            "Importing %d %s statistics (%s to %s)",
            len(statistics),
            statistic_id,
            statistics[0]["start"],
            statistics[-1]["start"],
        )
        async_add_external_statistics(self.hass, metadata, statistics)
