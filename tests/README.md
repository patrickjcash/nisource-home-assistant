# NiSource Integration Tests

## Running Tests

### Comprehensive Diagnostic Test

The main test script provides comprehensive diagnostics for the integration:

```bash
python tests/test_api_standalone.py
```

This script tests:
1. **Authentication** - Verifies login flow works
2. **CSV Data Retrieval** - Gets usage history and validates format
3. **Data Parsing** - Tests date, currency, and unit parsing
4. **Statistics Calculation** - Simulates consumption and cost statistics
5. **Account Summary** - Verifies balance and due date data
6. **Sensor Values** - Tests all sensor value extraction

### Requirements

```bash
# Install test dependencies
pip install requests python-dotenv
```

### Configuration

Create a `.env` file in the project root:

```bash
NISOURCE_USERNAME=your_email@example.com
NISOURCE_PASSWORD=your_password
```

## Test Results

The test will output detailed diagnostics including:
- CSV column structure
- Sample data records
- Parsed values
- Cumulative sum calculations
- Any errors or warnings

Use this script to:
- Verify the integration is working correctly
- Diagnose issues with sensors or statistics
- Confirm CSV format changes haven't broken parsing
- Test authentication after credential changes
