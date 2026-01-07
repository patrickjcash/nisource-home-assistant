# NiSource Gas Home Assistant Integration

Home Assistant integration for NiSource gas utilities (Columbia Gas and NIPSCO) to track natural gas usage and billing data. Integrates seamlessly with Home Assistant's Energy dashboard.

## Supported Providers

This integration works with all six NiSource family companies:

1. **Columbia Gas of Ohio** (OH) - ~1.5 million customers
2. **Columbia Gas of Kentucky** (KY) - ~135,000 customers
3. **Columbia Gas of Pennsylvania** (PA) - ~446,000 customers
4. **Columbia Gas of Maryland** (MD) - ~34,000 customers
5. **Columbia Gas of Virginia** (VA) - ~290,000 customers
6. **NIPSCO** (Northern Indiana) (IN) - ~1.4 million natural gas and electric customers

Nearly 4 million customers across six states can use this integration!

## Features

- **Historical gas consumption tracking** - View up to 18 months of historical usage data in the Energy Dashboard
- **Cost tracking** - Monitor gas costs with historical billing data
- **Account monitoring** - Track current bill, balance due, current amount due, and due date
- **Energy Dashboard integration** - Seamless integration with Home Assistant's native Energy Dashboard
- **Automatic statistics insertion** - Historical data is automatically backfilled on first setup
- **Automatic updates** - Data refreshes every 24 hours
- **Multi-provider support** - Works with all 6 NiSource utility companies

## Installation

### HACS (Recommended)

1. Open HACS in Home Assistant
2. Click on "Integrations"
3. Click the three dots in the top right corner
4. Select "Custom repositories"
5. Add this repository URL: `https://github.com/patrickjcash/nisource-home-assistant`
6. Select "Integration" as the category
7. Click "Add"
8. Click "Install"
9. Restart Home Assistant

### Manual Installation

1. Copy the `custom_components/nisource` directory to your Home Assistant `custom_components` directory
2. Restart Home Assistant

## Configuration

1. In Home Assistant, go to Configuration > Integrations
2. Click the "+ Add Integration" button
3. Search for "NiSource Gas"
4. Select your gas provider from the dropdown:
   - Columbia Gas of Ohio (OH)
   - Columbia Gas of Kentucky (KY)
   - Columbia Gas of Pennsylvania (PA)
   - Columbia Gas of Maryland (MD)
   - Columbia Gas of Virginia (VA)
   - NIPSCO (Northern Indiana) (IN)
5. Enter your portal credentials (same as your online account login)
6. Click Submit

## Energy Dashboard Integration

This integration uses **long-term statistics** (not sensors) for Energy Dashboard tracking. Historical data is automatically backfilled on first setup.

### Gas Consumption Tracking

1. Go to Settings → Dashboards → Energy
2. Under "Gas consumption", click "Add Gas Source"
3. Select the **statistic**: `NiSource Gas Consumption` (NOT the sensor)
4. Historical data (up to 18 months of billing period readings) will be visible immediately

### Cost Tracking

1. In the Energy Dashboard, under "Gas consumption"
2. Click "Add Cost" or configure cost tracking
3. Select the **statistic**: `NiSource Gas Cost`
4. Historical billing data will be displayed alongside consumption

**Note**: The integration provides both sensors (for current values) and statistics (for historical tracking). The Energy Dashboard uses statistics, not sensors.

## Sensors

The integration creates the following sensors:

1. **Gas Usage** - Latest billing period's gas consumption in CCF (hundred cubic feet)
2. **Total Bill Last Period** - Previous billing cycle amount in USD (billed in arrears)
3. **Balance Due** - Current account balance in USD
4. **Current Amount Due** - Amount currently due in USD
5. **Due Date** - Next payment due date

## Data Units

- **Gas consumption**: CCF (hundred cubic feet)
  - 1 CCF = 100 cubic feet of natural gas
  - Approximately 1 CCF ≈ 1 therm for natural gas
- **Cost**: USD (US Dollars)

## Development

### Testing

1. Create a `.env` file with your credentials:
   ```bash
   NISOURCE_USERNAME=your_email@example.com
   NISOURCE_PASSWORD=your_password
   ```

2. Install dependencies:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install requests python-dotenv beautifulsoup4
   ```

3. Run the diagnostic test:
   ```bash
   python tests/test_api_standalone.py
   ```

   This comprehensive test validates authentication, CSV parsing, statistics calculation, and sensor values.

### API Details

This integration uses the NiSource portal API:
- Authentication: Form-based POST with cookie session
- Data format: CSV downloads for historical data, JSON API for account summary
- Portal URLs vary by provider (e.g., myaccount.columbiagasohio.com)
- CSV endpoints provide up to 18 months of historical usage and billing data

### Architecture

The integration follows Home Assistant best practices:
- **Session-based authentication** with cookies
- **CSV parsing** for usage and billing history
- **JSON API** for account summary and balance information
- **Statistics insertion** for Energy Dashboard compatibility
- **DataUpdateCoordinator** for efficient data management

## Development

For developers interested in contributing or understanding the integration architecture, see [DEVELOPMENT.md](DEVELOPMENT.md) for:
- API endpoint documentation
- Implementation details
- Statistics insertion patterns
- Testing guidelines
- Common issues and solutions

## Credits

Built for NiSource customers (Columbia Gas and NIPSCO) who want to track their natural gas usage in Home Assistant.

Special thanks to the NiSource family of companies for providing accessible online portals for their customers.

## License

MIT License

## Support

For issues and feature requests, please use the [GitHub issue tracker](https://github.com/patrickjcash/nisource-home-assistant/issues).
