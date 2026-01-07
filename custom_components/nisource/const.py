"""Constants for the NiSource integration."""

from homeassistant.components.recorder.statistics import StatisticMetaData
from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.const import UnitOfVolume

DOMAIN = "nisource"

# Provider configurations
PROVIDERS = {
    "OH": {
        "name": "Columbia Gas of Ohio",
        "base_url": "https://myaccount.columbiagasohio.com",
        "state_code": "OH",
    },
    "KY": {
        "name": "Columbia Gas of Kentucky",
        "base_url": "https://myaccount.columbiagasofky.com",
        "state_code": "KY",
    },
    "PA": {
        "name": "Columbia Gas of Pennsylvania",
        "base_url": "https://myaccount.columbiagasofpa.com",
        "state_code": "PA",
    },
    "MD": {
        "name": "Columbia Gas of Maryland",
        "base_url": "https://myaccount.columbiagasofmd.com",
        "state_code": "MD",
    },
    "VA": {
        "name": "Columbia Gas of Virginia",
        "base_url": "https://myaccount.columbiagasofva.com",
        "state_code": "VA",
    },
    "IN": {
        "name": "NIPSCO (Northern Indiana)",
        "base_url": "https://myaccount.nipsco.com",
        "state_code": "IN",
    },
}

# API endpoints (relative to base URL)
ENDPOINT_LOGIN = "/login"
ENDPOINT_USAGE_HISTORY_CSV = "/UsageHistoryAllCsv/0"
ENDPOINT_BILLING_HISTORY_CSV = "/BillingHistoryAllCsv"
ENDPOINT_PAYMENT_HISTORY_CSV = "/PaymentHistoryAllCsv"
ENDPOINT_ACCOUNT_SUMMARY = "/api/LinkedAccounts/1.0"

# Update interval
UPDATE_INTERVAL = 86400  # 24 hours in seconds

# Gas units
# NiSource uses CCF (hundred cubic feet) in their CSV data
# 1 CCF = 100 cubic feet
UNIT_CCF = "CCF"
UNIT_CURRENCY = "USD"

# Statistics IDs for Energy Dashboard
STATISTIC_CONSUMPTION = f"{DOMAIN}:consumption"
STATISTIC_COST = f"{DOMAIN}:cost"

# Statistic names
STAT_NAME_CONSUMPTION = "NiSource Gas Consumption"
STAT_NAME_COST = "NiSource Gas Cost"

# Statistics metadata for Energy Dashboard
CONSUMPTION_METADATA = StatisticMetaData(
    has_mean=False,
    has_sum=True,
    name=STAT_NAME_CONSUMPTION,
    source=DOMAIN,
    statistic_id=STATISTIC_CONSUMPTION,
    unit_of_measurement=UNIT_CCF,
)

COST_METADATA = StatisticMetaData(
    has_mean=False,
    has_sum=True,
    name=STAT_NAME_COST,
    source=DOMAIN,
    statistic_id=STATISTIC_COST,
    unit_of_measurement=UNIT_CURRENCY,
)

# Sensor types
SENSOR_GAS_USAGE = "gas_usage"
SENSOR_BILL_AMOUNT = "bill_amount"
SENSOR_BALANCE_DUE = "balance_due"
SENSOR_CURRENT_AMOUNT_DUE = "current_amount_due"
SENSOR_DUE_DATE = "due_date"

# Config flow
CONF_PROVIDER = "provider"
