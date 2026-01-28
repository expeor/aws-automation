# Reports Module Tests

Comprehensive test suite for the `reports/` module in the aws-automation-toolkit project.

## Test Structure

```
tests/reports/
├── __init__.py
├── README.md                                    # This file
├── test_reports_init.py                         # Main reports module structure tests
├── cost_dashboard/
│   ├── __init__.py
│   └── test_cost_dashboard_init.py             # Cost dashboard structure tests
├── inventory/
│   ├── __init__.py
│   └── test_inventory_init.py                  # Inventory structure tests
├── ip_search/
│   ├── __init__.py
│   ├── test_ip_search_init.py                  # IP search structure tests
│   └── test_parser.py                          # ENI description parser tests
└── log_analyzer/
    ├── __init__.py
    └── test_alb_log_analyzer.py                # ALB log analyzer tests
```

## Test Coverage

### Reports Module (`reports/__init__.py`)
- **Coverage**: 100%
- **Tests**: 21 tests
- Tests CATEGORY and TOOLS metadata
- Validates all report tool definitions
- Ensures proper structure for all reports

### Cost Dashboard (`reports/cost_dashboard/`)
- **Coverage**: types.py: 100%, others: 12-24%
- **Tests**: 37 tests
- Tests CATEGORY and TOOLS definitions
- Validates RESOURCE_FIELD_MAP structure
- Tests WASTE_FIELDS configuration
- Tests UnusedResourceSummary dataclass
- Tests SessionCollectionResult dataclass
- Tests UnusedAllResult dataclass

### Inventory (`reports/inventory/`)
- **Coverage**: __init__.py: 100%, inventory.py: 0%
- **Tests**: 15 tests
- Tests CATEGORY and TOOLS definitions
- Validates inventory tool structure

### IP Search (`reports/ip_search/`)
- **Coverage**: __init__.py: 100%, parser.py: 93%
- **Tests**: 44 tests
- Tests CATEGORY and TOOLS definitions
- Comprehensive parser tests for ENI descriptions
- Tests all resource type parsing (EC2, Lambda, ELB, RDS, etc.)
- Tests ParsedResource dataclass
- Tests display string generation

### Log Analyzer (`reports/log_analyzer/`)
- **Coverage**: __init__.py: 100%, alb_log_analyzer.py: 25%
- **Tests**: 11 tests
- Tests ALBLogAnalyzer initialization
- Tests datetime string conversion
- Tests timezone handling
- Tests empty analysis results structure
- Tests DuckDB availability checking
- Tests cleanup functionality

## Running Tests

### Run all reports tests
```bash
pytest tests/reports/ -v
```

### Run with coverage
```bash
pytest tests/reports/ --cov=reports --cov-report=term-missing
```

### Run specific test module
```bash
pytest tests/reports/test_reports_init.py -v
pytest tests/reports/cost_dashboard/ -v
pytest tests/reports/ip_search/test_parser.py -v
```

### Run specific test class or function
```bash
pytest tests/reports/test_reports_init.py::TestReportsCategory -v
pytest tests/reports/ip_search/test_parser.py::TestParseEniDescription::test_parse_ec2_instance -v
```

## Test Statistics

- **Total Tests**: 128
- **Total Test Files**: 11
- **Overall Module Coverage**: 14%
- **Fully Tested Components**:
  - All module `__init__.py` files (100% coverage)
  - `cost_dashboard/types.py` (100% coverage)
  - `ip_search/parser.py` (93% coverage)

## Test Focus Areas

### 1. Module Structure Tests
- Validates CATEGORY metadata (name, display_name, description, aliases)
- Validates TOOLS metadata (name, description, permission, area, module/ref)
- Ensures all required fields are present
- Checks for proper data types

### 2. Data Structure Tests
- Tests dataclass creation and default values
- Tests field assignments and type safety
- Validates complex nested structures

### 3. Logic Tests
- Tests ENI description parsing logic
- Tests resource type identification
- Tests error handling and edge cases

### 4. Integration Tests
- Tests ALBLogAnalyzer with mocked dependencies
- Tests timezone handling
- Tests cleanup operations

## Known Issues

### Parser Bug in Route53 Resolver
The `ip_search/parser.py` has a bug where it checks for `"Route 53 Resolver" in description.lower()` which will never match due to case sensitivity. The test documents this behavior:

```python
# Parser bug: checks uppercase string in lowercase result
result = parse_eni_description(description="Route 53 Resolver endpoint")
assert result is None  # Bug: should match but doesn't
```

## Future Improvements

1. **Increase Coverage**: Current overall coverage is 14%, targeting 80%+
2. **Add Integration Tests**: Test end-to-end report generation
3. **Mock AWS API Calls**: Use moto for AWS service testing
4. **Test Error Scenarios**: Add more error handling tests
5. **Performance Tests**: Add tests for large dataset handling
6. **Fix Parser Bugs**: Fix Route53 Resolver case sensitivity issue

## Dependencies

### Runtime
- Python 3.10+
- pytest
- pytest-cov
- pytest-mock

### Optional (for full testing)
- moto (for AWS mocking)
- duckdb (for log analyzer tests)

## Contributing

When adding new tests:

1. Follow existing test patterns
2. Use descriptive test names starting with `test_`
3. Group related tests in test classes
4. Add docstrings explaining what each test validates
5. Use fixtures from `tests/conftest.py` when possible
6. Mock external dependencies (AWS APIs, file I/O)
7. Aim for high coverage of new code

## Test Conventions

- **Test file naming**: `test_<module_name>.py`
- **Test class naming**: `Test<FeatureName>`
- **Test method naming**: `test_<what_it_tests>`
- **Docstring format**: Brief description of what is being tested
- **Assertions**: Use descriptive assertion messages
- **Mocking**: Prefer `unittest.mock` or `pytest-mock`
