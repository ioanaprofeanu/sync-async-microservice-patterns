#!/bin/bash

################################################################################
# Sync vs Async Performance Comparison Test Runner
#
# This script runs comprehensive load tests against both synchronous and
# asynchronous implementations and generates comparison reports.
#
# Usage:
#   ./run-comparison-tests.sh [LOAD_PROFILE] [DURATION]
#
# Arguments:
#   LOAD_PROFILE: light, medium, heavy, stress, spike (default: medium)
#   DURATION: test duration in seconds (optional, uses profile default)
#
# Examples:
#   ./run-comparison-tests.sh                    # Run medium profile
#   ./run-comparison-tests.sh heavy              # Run heavy profile
#   ./run-comparison-tests.sh stress 180         # Run stress for 3 minutes
################################################################################

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
LOAD_PROFILE="${1:-medium}"
TEST_DURATION="${2:-}"
BASE_URL="http://localhost"
RESULTS_DIR="test-results"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
TEST_RUN_DIR="${RESULTS_DIR}/${LOAD_PROFILE}_${TIMESTAMP}"

# Create results directory
mkdir -p "${TEST_RUN_DIR}"

echo -e "${CYAN}"
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║   SYNC vs ASYNC MICROSERVICES PERFORMANCE COMPARISON TEST     ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo -e "${NC}"
echo -e "${BLUE}Load Profile:${NC} ${LOAD_PROFILE}"
echo -e "${BLUE}Test Duration:${NC} ${TEST_DURATION:-profile default}"
echo -e "${BLUE}Results Directory:${NC} ${TEST_RUN_DIR}"
echo ""

# Function to check if services are healthy
check_services() {
    local arch=$1
    local port_offset=$2

    echo -e "${YELLOW}Checking ${arch} services health...${NC}"

    local services=(8001 8002 8003 8004 8005 8006)
    local all_healthy=true

    for base_port in "${services[@]}"; do
        local port=$((base_port + port_offset))
        if ! curl -s "http://localhost:${port}/health" > /dev/null 2>&1; then
            echo -e "${RED}✗ Service on port ${port} is not healthy${NC}"
            all_healthy=false
        else
            echo -e "${GREEN}✓ Service on port ${port} is healthy${NC}"
        fi
    done

    if [ "$all_healthy" = false ]; then
        echo -e "${RED}ERROR: Not all ${arch} services are healthy!${NC}"
        echo -e "${YELLOW}Please ensure Docker containers are running:${NC}"
        if [ "$arch" = "sync" ]; then
            echo "  cd synchronous && docker compose -f docker-compose-sync.yml up -d"
        else
            echo "  cd asynchronous && docker compose -f docker-compose-async.yml up -d"
        fi
        exit 1
    fi

    echo -e "${GREEN}All ${arch} services are healthy!${NC}\n"
}

# Function to run k6 test
run_k6_test() {
    local arch=$1
    local output_file=$2

    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${MAGENTA}Running ${arch^^} test...${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"

    local cmd="k6 run \
        --env ARCH=${arch} \
        --env LOAD_PROFILE=${LOAD_PROFILE} \
        --env BASE_URL=${BASE_URL}"

    if [ -n "${TEST_DURATION}" ]; then
        cmd="${cmd} --env TEST_DURATION=${TEST_DURATION}"
    fi

    cmd="${cmd} --out json=${output_file} \
        --summary-export=${output_file%.json}_summary.json \
        k6-tests/unified-test.js"

    echo -e "${YELLOW}Command: ${cmd}${NC}\n"

    if eval "${cmd}"; then
        echo -e "\n${GREEN}✓ ${arch^^} test completed successfully${NC}\n"
        return 0
    else
        echo -e "\n${RED}✗ ${arch^^} test failed${NC}\n"
        return 1
    fi
}

# Function to wait between tests
wait_between_tests() {
    local wait_time=10
    echo -e "${YELLOW}Waiting ${wait_time} seconds before next test...${NC}"
    for i in $(seq ${wait_time} -1 1); do
        echo -ne "${YELLOW}${i}...${NC}\r"
        sleep 1
    done
    echo -e "${GREEN}Ready!${NC}\n"
}

# Main execution
main() {
    # Check prerequisites
    if ! command -v k6 &> /dev/null; then
        echo -e "${RED}ERROR: k6 is not installed!${NC}"
        echo "Install it from: https://k6.io/docs/getting-started/installation/"
        exit 1
    fi

    if ! command -v jq &> /dev/null; then
        echo -e "${RED}ERROR: jq is not installed!${NC}"
        echo "Install it: brew install jq (macOS) or apt-get install jq (Linux)"
        exit 1
    fi

    # Check synchronous services
    check_services "sync" 0

    # Check asynchronous services
    check_services "async" 100

    echo -e "${CYAN}╔════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║                    STARTING TESTS                              ║${NC}"
    echo -e "${CYAN}╚════════════════════════════════════════════════════════════════╝${NC}\n"

    # Run synchronous test
    local sync_success=true
    if ! run_k6_test "sync" "${TEST_RUN_DIR}/sync_results.json"; then
        sync_success=false
    fi

    # Wait between tests
    wait_between_tests

    # Run asynchronous test
    local async_success=true
    if ! run_k6_test "async" "${TEST_RUN_DIR}/async_results.json"; then
        async_success=false
    fi

    # Generate comparison report
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${MAGENTA}Generating comparison report...${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"

    if [ -f "compare-results.py" ]; then
        python3 compare-results.py "${TEST_RUN_DIR}" "${LOAD_PROFILE}"
    elif [ -f "compare-results.sh" ]; then
        bash compare-results.sh "${TEST_RUN_DIR}"
    else
        echo -e "${YELLOW}Warning: Comparison script not found. Results saved in ${TEST_RUN_DIR}${NC}"
    fi

    # Print summary
    echo -e "\n${CYAN}╔════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║                    TEST SUMMARY                                ║${NC}"
    echo -e "${CYAN}╚════════════════════════════════════════════════════════════════╝${NC}\n"

    if [ "$sync_success" = true ]; then
        echo -e "${GREEN}✓ Synchronous tests: PASSED${NC}"
    else
        echo -e "${RED}✗ Synchronous tests: FAILED${NC}"
    fi

    if [ "$async_success" = true ]; then
        echo -e "${GREEN}✓ Asynchronous tests: PASSED${NC}"
    else
        echo -e "${RED}✗ Asynchronous tests: FAILED${NC}"
    fi

    echo -e "\n${BLUE}Results saved in: ${TEST_RUN_DIR}${NC}"
    echo -e "${BLUE}Files:${NC}"
    ls -lh "${TEST_RUN_DIR}"

    echo ""
}

# Run main function
main
