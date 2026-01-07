"""DataUpdateCoordinator for NiSource."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from homeassistant.components.recorder import get_instance
from homeassistant.components.recorder.statistics import (
    StatisticData,
    async_add_external_statistics,
    get_last_statistics,
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

        This method follows the Opower pattern for backfilling historical data
        into Home Assistant's statistics database. The Energy Dashboard uses
        these statistics, not the sensor values directly.
        """
        # Get last inserted statistics to avoid duplicates
        try:
            last_stats = await get_instance(self.hass).async_add_executor_job(
                get_last_statistics,
                self.hass,
                1,
                STATISTIC_CONSUMPTION,
                True,
                set(),
            )
            _LOGGER.debug("get_last_statistics returned: %s", last_stats)
        except Exception as err:
            _LOGGER.warning("Failed to get last statistics: %s", err)
            last_stats = {}

        last_consumption_time = None
        if last_stats and STATISTIC_CONSUMPTION in last_stats:
            stats_list = last_stats[STATISTIC_CONSUMPTION]
            if stats_list and len(stats_list) > 0:
                last_stat = stats_list[0]
                _LOGGER.debug("Last stat entry: %s", last_stat)
                if "start" in last_stat:
                    last_consumption_time = datetime.fromtimestamp(
                        last_stat["start"], tz=timezone.utc
                    )
                    _LOGGER.debug("Last consumption time: %s", last_consumption_time)

        # Parse usage history from CSV
        usage_csv = data.get("usage", [])

        if not usage_csv:
            _LOGGER.debug("No usage history data available")
            return

        # Build consumption statistics with cumulative sum
        # CSV format: Date, Type of Read, Avg Temp, Number of Days, Units Used, Yearly Usage, Bill Amount, Cost per Day
        consumption_statistics = []
        consumption_sum = 0.0

        for row in usage_csv:
            date_str = row.get("Date")
            units_used_str = row.get("Units Used")

            if not date_str or not units_used_str:
                continue

            try:
                # Parse date from MM/DD/YYYY format
                period_start = self.api.parse_date(date_str).replace(
                    hour=0, minute=0, second=0, microsecond=0, tzinfo=timezone.utc
                )

                # Skip if we've already inserted this period
                if last_consumption_time and period_start <= last_consumption_time:
                    # Still need to add to sum for correct cumulative calculation
                    ccf = float(units_used_str)
                    consumption_sum += ccf
                    continue

                # Parse CCF (hundred cubic feet)
                ccf = float(units_used_str)
                consumption_sum += ccf

                consumption_statistics.append(
                    StatisticData(
                        start=period_start,
                        state=ccf,  # This period's usage in CCF
                        sum=consumption_sum,  # Cumulative total
                    )
                )

            except (ValueError, TypeError) as err:
                _LOGGER.warning("Failed to parse usage data point %s: %s", row, err)
                continue

        # Insert consumption statistics
        if consumption_statistics:
            _LOGGER.info(
                "Inserting %d consumption statistics (starting from %s)",
                len(consumption_statistics),
                consumption_statistics[0]["start"],
            )
            async_add_external_statistics(self.hass, CONSUMPTION_METADATA, consumption_statistics)

        # Insert cost statistics from billing CSV
        await self._insert_cost_statistics(data)

    async def _insert_cost_statistics(self, data: dict) -> None:
        """Insert cost statistics from billing history CSV.

        Billing CSV format varies, but usage CSV has "Bill Amount" column
        which we can use for cost tracking.
        """
        # Get last inserted cost statistics
        try:
            last_stats = await get_instance(self.hass).async_add_executor_job(
                get_last_statistics,
                self.hass,
                1,
                STATISTIC_COST,
                True,
                set(),
            )
            _LOGGER.debug("get_last_statistics (cost) returned: %s", last_stats)
        except Exception as err:
            _LOGGER.warning("Failed to get last cost statistics: %s", err)
            last_stats = {}

        last_cost_time = None
        if last_stats and STATISTIC_COST in last_stats:
            stats_list = last_stats[STATISTIC_COST]
            if stats_list and len(stats_list) > 0:
                last_stat = stats_list[0]
                if "start" in last_stat:
                    last_cost_time = datetime.fromtimestamp(
                        last_stat["start"], tz=timezone.utc
                    )
                    _LOGGER.debug("Last cost time: %s", last_cost_time)

        # Parse usage CSV for bill amounts
        # (Usage CSV includes "Bill Amount" column)
        usage_csv = data.get("usage", [])

        if not usage_csv:
            _LOGGER.debug("No usage/billing data available")
            return

        # Build cost statistics with cumulative sum
        cost_statistics = []
        cost_sum = 0.0

        for row in usage_csv:
            date_str = row.get("Date")
            bill_amount_str = row.get("Bill Amount")

            if not date_str or not bill_amount_str:
                continue

            try:
                # Parse date from MM/DD/YYYY format
                period_start = self.api.parse_date(date_str).replace(
                    hour=0, minute=0, second=0, microsecond=0, tzinfo=timezone.utc
                )

                # Skip if we've already inserted this period
                if last_cost_time and period_start <= last_cost_time:
                    # Still need to add to sum for correct cumulative calculation
                    cost = self.api.parse_currency(bill_amount_str)
                    cost_sum += cost
                    continue

                # Parse cost (remove $ and convert to float)
                cost = self.api.parse_currency(bill_amount_str)
                cost_sum += cost

                cost_statistics.append(
                    StatisticData(
                        start=period_start,
                        state=cost,  # This bill's amount
                        sum=cost_sum,  # Cumulative total
                    )
                )

            except (ValueError, TypeError) as err:
                _LOGGER.warning("Failed to parse cost data point %s: %s", row, err)
                continue

        # Insert cost statistics
        if cost_statistics:
            _LOGGER.info(
                "Inserting %d cost statistics (starting from %s)",
                len(cost_statistics),
                cost_statistics[0]["start"],
            )
            async_add_external_statistics(self.hass, COST_METADATA, cost_statistics)
