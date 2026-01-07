"""Sensor platform for NiSource."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, UNIT_CCF


@dataclass(frozen=True)
class NiSourceSensorEntityDescription(SensorEntityDescription):
    """Describes NiSource sensor entity."""

    value_fn: Callable[[dict[str, Any]], StateType] | None = None


def _get_latest_gas_usage(data: dict[str, Any]) -> StateType:
    """Extract latest gas usage from CSV data."""
    usage_csv = data.get("usage", [])

    if not usage_csv:
        return None

    # Get the latest (most recent) usage record
    # CSV is ordered newest-to-oldest, so [0] is the most recent
    latest = usage_csv[0]
    units_used = latest.get("Units Used")

    if units_used is None:
        return None

    try:
        return float(units_used)
    except (ValueError, TypeError):
        return None


def _get_latest_bill_amount(data: dict[str, Any]) -> StateType:
    """Extract latest bill amount from CSV data."""
    usage_csv = data.get("usage", [])

    if not usage_csv:
        return None

    # Get the latest bill amount from usage CSV
    # CSV is ordered newest-to-oldest, so [0] is the most recent
    latest = usage_csv[0]
    bill_amount = latest.get("Bill Amount")

    if not bill_amount or bill_amount.strip() in ("", "$0.00", "$"):
        return None

    try:
        # Remove $ and convert to float
        return float(bill_amount.replace("$", "").replace(",", "").strip())
    except (ValueError, TypeError, AttributeError):
        return None


def _get_balance_due(data: dict[str, Any]) -> StateType:
    """Extract balance due from account summary."""
    account = data.get("account", {})
    linked_accounts = account.get("linkedAccounts", [])

    if not linked_accounts:
        return None

    # Get first account
    account_info = linked_accounts[0]
    balance_info = account_info.get("customerAccountBalance", {})
    balance = balance_info.get("balanceAmount")

    if balance is None:
        return None

    try:
        return float(balance)
    except (ValueError, TypeError):
        return None


def _get_past_due_amount(data: dict[str, Any]) -> StateType:
    """Extract past due amount from account summary."""
    account = data.get("account", {})
    linked_accounts = account.get("linkedAccounts", [])

    if not linked_accounts:
        return None

    # Get first account
    account_info = linked_accounts[0]
    balance_info = account_info.get("customerAccountBalance", {})
    past_due = balance_info.get("pastDueAmount")

    if past_due is None:
        return None

    try:
        # Return absolute value (API may return negative)
        return abs(float(past_due))
    except (ValueError, TypeError):
        return None


def _get_due_date(data: dict[str, Any]) -> StateType:
    """Extract due date from account summary."""
    account = data.get("account", {})
    linked_accounts = account.get("linkedAccounts", [])

    if not linked_accounts:
        return None

    # Get first account
    account_info = linked_accounts[0]
    balance_info = account_info.get("customerAccountBalance", {})
    due_date = balance_info.get("dueDate")

    return due_date  # Return as string in YYYY-MM-DD format


# NOTE: These sensors display current/latest values for informational purposes.
# The Energy Dashboard uses STATISTICS (not sensors) for historical tracking.
# Statistics are inserted by the coordinator via _insert_statistics().

SENSORS: tuple[NiSourceSensorEntityDescription, ...] = (
    NiSourceSensorEntityDescription(
        key="gas_usage",
        name="Gas Usage",
        device_class=SensorDeviceClass.GAS,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UNIT_CCF,
        suggested_display_precision=0,
        value_fn=_get_latest_gas_usage,
        # This sensor shows the latest month's reading in CCF
        # Energy Dashboard uses statistic: nisource:consumption
    ),
    NiSourceSensorEntityDescription(
        key="bill_amount",
        name="Total Bill this Period",
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement="USD",
        suggested_display_precision=2,
        value_fn=_get_latest_bill_amount,
        # This sensor shows the latest bill amount
        # Energy Dashboard uses statistic: nisource:cost
    ),
    NiSourceSensorEntityDescription(
        key="balance_due",
        name="Balance Due",
        device_class=SensorDeviceClass.MONETARY,
        state_class=None,  # Balance can go up and down
        native_unit_of_measurement="USD",
        suggested_display_precision=2,
        value_fn=_get_balance_due,
    ),
    NiSourceSensorEntityDescription(
        key="past_due_amount",
        name="Past Due Amount",
        device_class=SensorDeviceClass.MONETARY,
        state_class=None,
        native_unit_of_measurement="USD",
        suggested_display_precision=2,
        value_fn=_get_past_due_amount,
    ),
    NiSourceSensorEntityDescription(
        key="due_date",
        name="Due Date",
        device_class=SensorDeviceClass.DATE,
        state_class=None,
        value_fn=_get_due_date,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up NiSource sensors."""
    coordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities(
        NiSourceSensor(coordinator, description, entry)
        for description in SENSORS
    )


class NiSourceSensor(CoordinatorEntity, SensorEntity):
    """Representation of a NiSource sensor."""

    entity_description: NiSourceSensorEntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator,
        description: NiSourceSensorEntityDescription,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"

        # Get provider name from config
        provider_name = entry.data.get("provider_name", "NiSource Gas")

        # Group sensors under a service device
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": provider_name,
            "manufacturer": "NiSource",
            "model": "Gas Service",
            "entry_type": "service",  # This is a service, not a physical device
        }

    @property
    def native_value(self) -> StateType:
        """Return the state of the sensor."""
        if self.entity_description.value_fn:
            return self.entity_description.value_fn(self.coordinator.data)
        return None
