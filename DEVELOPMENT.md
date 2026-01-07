# NiSource Home Assistant Integration - Development Guide

## Overview

This integration provides Home Assistant support for NiSource gas utilities (Columbia Gas and NIPSCO) to track gas usage and billing data with Energy Dashboard integration.

## Architecture

### Authentication

**Method**: Form-based authentication with cookie session management

**Login Flow**:
```python
session = requests.Session()
response = session.post(
    f"{base_url}/login",
    data={
        "ReturnUrl": "",
        "Username": "email@example.com",
        "Password": "password",
        "rememberme": "true"
    }
)
# Returns 302 redirect to: /dashboard/{account_id}/{state}?dlp=LoginSuccess
```

**Session Management**:
- Cookie-based session (not token-based)
- Key cookies: `vlgSession`, `vlgXsrf`, `CustomerToken`, `vlgAccount`, `selectedAccount`

## API Endpoints

### 1. Usage History (CSV)
- **Endpoint**: `/UsageHistoryAllCsv/0`
- **Method**: GET
- **Content-Type**: text/csv
- **Data**: 18 months of historical usage

**CSV Structure**:
```csv
Date,Type of Read,Avg Temp,Number of Days,Units Used, Yearly Usage, Bill Amount, Cost per Day
01/15/2024,ACTUAL READING,42.5,30,150.00,5%,$185.50,$6.18
```

**IMPORTANT**: Several column names have **leading spaces** in the actual CSV:
- `' Yearly Usage'` (with leading space)
- `' Bill Amount'` (with leading space)
- `' Cost per Day'` (with leading space)

**Best Practice**: Use the `get_csv_value()` helper method to access these fields:
```python
bill_amount = api.get_csv_value(row, "Bill Amount")  # Handles both "Bill Amount" and " Bill Amount"
```

This helper tries both the correct name and the variant with a leading space, making the code resilient to CSV format changes.

**Fields**:
- `Date`: MM/DD/YYYY format
- `Type of Read`: ACTUAL READING or CALC BY DATA CENTER
- `Avg Temp`: Average temperature in °F
- `Number of Days`: Billing period length
- `Units Used`: CCF (hundred cubic feet)
- ` Yearly Usage`: Percentage change with leading space (e.g., "20%")
- ` Bill Amount`: Dollar amount with leading space (e.g., "$232.00")
- ` Cost per Day`: Dollar amount with leading space (e.g., "$7.03")

### 2. Billing History (CSV)
- **Endpoint**: `/BillingHistoryAllCsv`
- **Method**: GET
- **Content-Type**: text/csv

### 3. Payment History (CSV)
- **Endpoint**: `/PaymentHistoryAllCsv`
- **Method**: GET
- **Content-Type**: text/csv

### 4. Account Summary (JSON)
- **Endpoint**: `/api/LinkedAccounts/1.0?query=&limit=10&ascending=1&page=1&byColumn=0&diagId={diagId}`
- **Method**: GET
- **Content-Type**: application/json
- **Headers**:
  - `x-nis-ldc`: State code (e.g., OH, KY, PA, MD, VA, IN)
  - `adrum`: `isAjax:true`

**Response Structure**:
```json
{
  "linkedAccounts": [{
    "customerAccountId": "string",
    "customerNumber": "string",
    "serviceAddress": {
      "address1": "string",
      "city": "string",
      "state": "string",
      "zip": "string"
    },
    "customerAccountBalance": {
      "balanceAmount": 0.00,
      "dueDate": "YYYY-MM-DD",
      "pastDueAmount": 0.00,
      "currentAmountDue": 0.00
    },
    "status": "Active",
    "ldc": "OH"
  }],
  "count": 1
}
```

## Data Units & Conversions

### Gas Measurement
- **Units Used**: CCF (hundred cubic feet)
- **Conversion**: 1 CCF = 100 cubic feet
- **Note**: Approximately 1 CCF ≈ 1 therm for natural gas

### Currency
- Bill amounts include "$" prefix in CSV - must strip and convert to float
- Percentages in "Yearly Usage" include "%" suffix

## Sensors

The integration creates the following sensors:

1. **Gas Usage** (latest period)
   - Device Class: `GAS`
   - State Class: `TOTAL_INCREASING`
   - Unit: CCF

2. **Total Bill this Period**
   - Device Class: `MONETARY`
   - State Class: `TOTAL`
   - Unit: USD

3. **Balance Due**
   - Device Class: `MONETARY`
   - State Class: None (can fluctuate)
   - Unit: USD

4. **Past Due Amount**
   - Device Class: `MONETARY`
   - State Class: None
   - Unit: USD

5. **Due Date**
   - Device Class: `DATE`
   - Shows next payment due date

## Energy Dashboard Statistics

The integration uses Home Assistant's statistics system for Energy Dashboard integration:

### Gas Consumption Statistics
- **Statistic ID**: `nisource:consumption`
- **Name**: "NiSource Gas Consumption"
- **Unit**: CCF
- **Source**: Parsed from `/UsageHistoryAllCsv/0`
- **Method**: `async_add_external_statistics`

### Cost Statistics
- **Statistic ID**: `nisource:cost`
- **Name**: "NiSource Gas Cost"
- **Unit**: USD
- **Source**: Parsed from CSV bill amounts
- **Method**: `async_add_external_statistics`

## Integration Structure

```
custom_components/nisource/
├── __init__.py          # Entry point, setup coordinator
├── api.py               # API client with CSV/JSON parsing
├── config_flow.py       # UI configuration flow
├── const.py             # Constants, statistics metadata
├── coordinator.py       # DataUpdateCoordinator + statistics insertion
├── manifest.json        # Integration metadata
├── sensor.py            # Sensor entities
├── strings.json         # UI strings
└── translations/
    └── en.json          # English translations
```

## Key Implementation Details

### API Client (`api.py`)

**Session Management**:
```python
import requests
from io import StringIO
import csv

class NiSourceAPI:
    def __init__(self, base_url, username, password, state_code):
        self.session = requests.Session()
        # Session maintains cookies automatically
```

**CSV Parsing**:
```python
response = self.session.get(f"{base_url}/UsageHistoryAllCsv/0")
csv_file = StringIO(response.text)
reader = csv.DictReader(csv_file)
data = list(reader)
```

**Important**: CSV data is ordered **newest-to-oldest**, so use `reversed()` for chronological statistics:
```python
for row in reversed(usage_csv):
    # Process oldest to newest for cumulative sum
```

### Coordinator (`coordinator.py`)

**Data Flow**:
1. Authenticate and fetch all data sources (usage CSV, billing CSV, account JSON)
2. Parse CSV data into structured format
3. Call `_insert_statistics()` to backfill historical data
4. Update interval: 24 hours (86400 seconds)

**Statistics Insertion**:
```python
from homeassistant.components.recorder.statistics import (
    StatisticData,
    async_add_external_statistics,
    get_last_statistics,
)

# Check last inserted statistic to avoid duplicates
last_stats = await get_instance(self.hass).async_add_executor_job(
    get_last_statistics,
    self.hass,
    1,
    STATISTIC_CONSUMPTION,
    True,
    set(),
)

# Build statistics with cumulative sum (oldest to newest)
consumption_statistics = []
consumption_sum = 0.0

for row in reversed(csv_data):  # Reverse for chronological order
    date = parse_date(row['Date'])
    ccf = float(row['Units Used'])
    consumption_sum += ccf

    consumption_statistics.append(
        StatisticData(
            start=date,
            state=ccf,          # This period's usage
            sum=consumption_sum,  # Cumulative total
        )
    )

async_add_external_statistics(
    self.hass,
    CONSUMPTION_METADATA,
    consumption_statistics
)
```

## Multi-Provider Support

NiSource operates 6 utilities across the United States:

1. Columbia Gas of Ohio (OH)
2. Columbia Gas of Kentucky (KY)
3. Columbia Gas of Pennsylvania (PA)
4. Columbia Gas of Maryland (MD)
5. Columbia Gas of Virginia (VA)
6. NIPSCO - Northern Indiana (IN)

**Portal URLs** (all use the same platform):
- OH: `https://myaccount.columbiagasohio.com`
- KY: `https://myaccount.columbiagasofky.com`
- PA: `https://myaccount.columbiagasofpa.com`
- MD: `https://myaccount.columbiagasofmd.com`
- VA: `https://myaccount.columbiagasofva.com`
- IN: `https://myaccount.nipsco.com`

**Implementation**: Base URL is configured during setup via the config flow.

## Dependencies

### manifest.json
```json
{
  "requirements": ["requests>=2.31.0"],
  "dependencies": ["recorder"]
}
```

**Note**: BeautifulSoup is not required - integration uses CSV and JSON endpoints only.

## Testing

### Local Development Setup

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install requests python-dotenv

# Create .env file
cat > .env << EOF
NISOURCE_USERNAME=your_email@example.com
NISOURCE_PASSWORD=your_password
EOF

# Run test scripts
python tests/test_auth.py
python tests/test_integration_api.py
```

### Test Files
- `test_auth.py` - Authentication flow verification
- `test_api.py` - API endpoint testing
- `test_csv_download.py` - CSV parsing validation
- `test_integration_api.py` - Full integration test

## Common Issues & Solutions

### Issue: Negative consumption values
**Cause**: CSV data is ordered newest-to-oldest
**Solution**: Use `reversed()` when building statistics

### Issue: Missing cost statistics
**Cause**: Same as above
**Solution**: Reverse CSV order for chronological processing

### Issue: Sensors showing 0 or Unknown
**Cause**: Using wrong array index (CSV is reversed)
**Solution**: Use index `[0]` for newest record, not `[-1]`

### Issue: Due Date sensor hidden
**Cause**: Empty or invalid date value from API
**Solution**: Check account summary JSON for valid `dueDate` field

## Energy Dashboard Integration

The integration uses Home Assistant's long-term statistics system:
- **Statistics** (not sensors) are used for Energy Dashboard
- Historical data is automatically backfilled on first setup
- Cumulative sums are calculated for proper dashboard display
- Updates occur every 24 hours to minimize API load

## Contributing

When contributing to this integration:

1. Maintain the statistics-based approach for Energy Dashboard
2. Follow Home Assistant's integration quality scale guidelines
3. Test with multiple NiSource providers if possible
4. Add appropriate error handling for API failures
5. Document any new API endpoints discovered

## References

- [Home Assistant Integration Development](https://developers.home-assistant.io/)
- [Recorder Statistics Documentation](https://developers.home-assistant.io/docs/core/entity/sensor/#long-term-statistics)
- [Energy Dashboard Integration](https://www.home-assistant.io/docs/energy/)
