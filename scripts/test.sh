#!/bin/bash

# Set environment variables for testing
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
export TEST_CONFIG_PATH="config/config.yaml"
export TEST_ENV="test"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Function to run tests and check status
run_test() {
    local test_name=$1
    local test_file=$2
    echo -e "\n${GREEN}Running ${test_name} Tests...${NC}"
    python -m pytest tests/${test_file} -v
    if [ $? -ne 0 ]; then
        echo -e "${RED}${test_name} tests failed!${NC}"
        exit 1
    fi
}

# Create test results directory
mkdir -p test_results

# Run tests with proper module structure
run_test "Monitor Backend" "test_monitor.py"
run_test "Performance Monitor" "test_performance_monitor.py"
run_test "Alert Manager" "test_alert_manager.py"
run_test "Data Fetcher" "test_data_fetcher.py"
run_test "Backtester" "test_backtester.py"
run_test "Risk Manager" "test_risk_manager.py"
run_test "Strategy Manager" "test_multi_strategy_manager.py"
run_test "Executor" "test_executor.py"

# Generate coverage report
echo -e "\n${GREEN}Generating Coverage Report...${NC}"
coverage run -m pytest tests/
coverage report
coverage html -d test_results/coverage_report

echo -e "\n${GREEN}All tests completed successfully!${NC}"
