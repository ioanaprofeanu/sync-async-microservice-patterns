#!/bin/bash

################################################################################
# Academic Performance Testing Suite
# Comprehensive test runner for research paper analysis
#
# Usage:
#   ./run-academic-tests.sh [phase]
#
# Phases:
#   quick     - Quick validation (2 hours)
#   standard  - Standard academic suite (12 hours)
#   full      - Full comprehensive suite (20+ hours)
#   custom    - Run specific test configurations
################################################################################

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

# Configuration
PHASE="${1:-standard}"
RESULTS_BASE="academic-results"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
RESULTS_DIR="${RESULTS_BASE}/${PHASE}_${TIMESTAMP}"

mkdir -p "${RESULTS_DIR}"

echo -e "${CYAN}"
cat << "EOF"
╔══════════════════════════════════════════════════════════════════╗
║              ACADEMIC PERFORMANCE TEST SUITE                     ║
║     Comprehensive Sync vs Async Microservices Analysis          ║
╚══════════════════════════════════════════════════════════════════╝
EOF
echo -e "${NC}"

echo -e "${BLUE}Phase:${NC} ${PHASE}"
echo -e "${BLUE}Results Directory:${NC} ${RESULTS_DIR}"
echo -e "${BLUE}Timestamp:${NC} ${TIMESTAMP}\n"

# Test configurations
declare -A TESTS

# Phase 1: Baseline & Light Load
TESTS[baseline]="2,2,2,1,2,50,300"          # VUs: 2,2,2,1,2 | Rate: 50 | Duration: 300s (5min)
TESTS[light]="5,5,5,2,5,100,600"            # VUs: 5,5,5,2,5 | Rate: 100 | Duration: 600s (10min)

# Phase 2: Progressive Load
TESTS[medium_low]="10,10,10,3,10,150,600"   # VUs: 10 | Duration: 10min
TESTS[medium]="15,15,15,5,15,200,600"       # VUs: 15 | Duration: 10min
TESTS[medium_high]="20,20,20,7,20,250,600"  # VUs: 20 | Duration: 10min
TESTS[heavy]="30,30,30,10,30,300,900"       # VUs: 30 | Duration: 15min

# Phase 3: Stress Testing
TESTS[high_stress]="50,50,50,15,50,500,600"     # VUs: 50 | Duration: 10min
TESTS[extreme_stress]="100,100,100,25,100,1000,300"  # VUs: 100 | Duration: 5min

# Phase 4: Specialized
TESTS[soak]="15,15,15,5,15,200,3600"        # VUs: 15 | Duration: 60min
TESTS[sustained_peak]="30,30,30,10,30,300,1800"  # VUs: 30 | Duration: 30min

# Function to parse test config
parse_test_config() {
    local config=$1
    IFS=',' read -r -a params <<< "$config"
    echo "${params[@]}"
}

# Function to run a single test
run_single_test() {
    local test_name=$1
    local arch=$2
    local run_number=$3
    local config=$4

    read -r s1_vus s2_vus s3_vus s4_vus s5_vus s6_rate duration <<< "$(parse_test_config "$config")"

    local arch_upper=$(echo "$arch" | tr '[:lower:]' '[:upper:]')
    local output_prefix="${RESULTS_DIR}/${test_name}_${arch}_run${run_number}"

    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${MAGENTA}${BOLD}Running: ${test_name} | ${arch_upper} | Run ${run_number}/${NUM_RUNS}${NC}"
    echo -e "${YELLOW}Config: VUs=(${s1_vus},${s2_vus},${s3_vus},${s4_vus},${s5_vus}) Rate=${s6_rate}/s Duration=${duration}s${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"

    # Create custom k6 script on-the-fly
    cat > "${output_prefix}_config.js" << EOJS
// Auto-generated test configuration
import { testScenario1, testScenario2, testScenario3, testScenario4, testScenario5, testScenario6 } from '../k6-tests/unified-test.js';

export { testScenario1, testScenario2, testScenario3, testScenario4, testScenario5, testScenario6 };

export const options = {
    scenarios: {
        scenario1_user_registration: {
            executor: 'constant-vus',
            exec: 'testScenario1',
            vus: ${s1_vus},
            duration: '${duration}s',
            tags: { scenario: 'scenario1' },
        },
        scenario2_payment_processing: {
            executor: 'constant-vus',
            exec: 'testScenario2',
            vus: ${s2_vus},
            duration: '${duration}s',
            tags: { scenario: 'scenario2' },
        },
        scenario3_product_update: {
            executor: 'constant-vus',
            exec: 'testScenario3',
            vus: ${s3_vus},
            duration: '${duration}s',
            tags: { scenario: 'scenario3' },
        },
        scenario4_report_generation: {
            executor: 'constant-vus',
            exec: 'testScenario4',
            vus: ${s4_vus},
            duration: '${duration}s',
            tags: { scenario: 'scenario4' },
        },
        scenario5_order_creation: {
            executor: 'constant-vus',
            exec: 'testScenario5',
            vus: ${s5_vus},
            duration: '${duration}s',
            tags: { scenario: 'scenario5' },
        },
        scenario6_click_tracking: {
            executor: 'constant-arrival-rate',
            exec: 'testScenario6',
            rate: ${s6_rate},
            timeUnit: '1s',
            duration: '${duration}s',
            preAllocatedVUs: Math.floor(${s6_rate} * 0.2),
            maxVUs: Math.ceil(${s6_rate} * 0.5),
            tags: { scenario: 'scenario6' },
        },
    },
};
EOJS

    # Run k6 test
    if k6 run \
        --env ARCH="${arch}" \
        --env BASE_URL=http://localhost \
        --out json="${output_prefix}_results.json" \
        --summary-export="${output_prefix}_summary.json" \
        "${output_prefix}_config.js" 2>&1 | tee "${output_prefix}_console.log"; then
        echo -e "${GREEN}✓ Test completed successfully${NC}\n"
        return 0
    else
        echo -e "${RED}✗ Test failed${NC}\n"
        return 1
    fi
}

# Function to run test suite
run_test_suite() {
    local test_name=$1
    local config=$2

    echo -e "\n${BOLD}${BLUE}╔════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BOLD}${BLUE}║  Test: ${test_name}${NC}"
    echo -e "${BOLD}${BLUE}╚════════════════════════════════════════════════════════╝${NC}\n"

    for run in $(seq 1 $NUM_RUNS); do
        # Run sync
        if ! run_single_test "$test_name" "sync" "$run" "$config"; then
            echo -e "${RED}Sync test failed, continuing...${NC}"
        fi

        sleep 30  # Cool down between architectures

        # Run async
        if ! run_single_test "$test_name" "async" "$run" "$config"; then
            echo -e "${RED}Async test failed, continuing...${NC}"
        fi

        if [ $run -lt $NUM_RUNS ]; then
            echo -e "${YELLOW}Cooling down 60s before next run...${NC}"
            sleep 60
        fi
    done
}

# Define test phases
case $PHASE in
    quick)
        echo -e "${GREEN}Running QUICK validation suite (2-3 hours)${NC}\n"
        NUM_RUNS=2
        run_test_suite "baseline" "${TESTS[baseline]}"
        run_test_suite "light" "${TESTS[light]}"
        run_test_suite "medium" "${TESTS[medium]}"
        run_test_suite "heavy" "${TESTS[heavy]}"
        ;;

    standard)
        echo -e "${GREEN}Running STANDARD academic suite (12-14 hours)${NC}\n"
        NUM_RUNS=3
        run_test_suite "baseline" "${TESTS[baseline]}"
        run_test_suite "light" "${TESTS[light]}"
        run_test_suite "medium_low" "${TESTS[medium_low]}"
        run_test_suite "medium" "${TESTS[medium]}"
        run_test_suite "medium_high" "${TESTS[medium_high]}"
        run_test_suite "heavy" "${TESTS[heavy]}"
        run_test_suite "high_stress" "${TESTS[high_stress]}"
        ;;

    full)
        echo -e "${GREEN}Running FULL comprehensive suite (20-24 hours)${NC}\n"
        NUM_RUNS=3
        run_test_suite "baseline" "${TESTS[baseline]}"
        run_test_suite "light" "${TESTS[light]}"
        run_test_suite "medium_low" "${TESTS[medium_low]}"
        run_test_suite "medium" "${TESTS[medium]}"
        run_test_suite "medium_high" "${TESTS[medium_high]}"
        run_test_suite "heavy" "${TESTS[heavy]}"
        run_test_suite "high_stress" "${TESTS[high_stress]}"
        run_test_suite "extreme_stress" "${TESTS[extreme_stress]}"
        NUM_RUNS=1  # Only 1 run for long tests
        run_test_suite "soak" "${TESTS[soak]}"
        run_test_suite "sustained_peak" "${TESTS[sustained_peak]}"
        ;;

    custom)
        echo -e "${GREEN}Custom test mode${NC}"
        echo "Usage: Edit this script to define custom tests"
        ;;

    *)
        echo -e "${RED}Unknown phase: $PHASE${NC}"
        echo "Valid phases: quick, standard, full, custom"
        exit 1
        ;;
esac

# Generate summary
echo -e "\n${CYAN}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║               TEST SUITE COMPLETED                     ║${NC}"
echo -e "${CYAN}╚════════════════════════════════════════════════════════╝${NC}\n"

echo -e "${GREEN}Results saved in: ${RESULTS_DIR}${NC}\n"
echo -e "${YELLOW}To analyze results, run:${NC}"
echo -e "${BLUE}  python3 analyze-academic-results.py ${RESULTS_DIR}${NC}\n"

# Save test metadata
cat > "${RESULTS_DIR}/test_metadata.json" << EOF
{
  "phase": "${PHASE}",
  "timestamp": "${TIMESTAMP}",
  "num_runs": ${NUM_RUNS},
  "system_info": {
    "os": "$(uname -s)",
    "arch": "$(uname -m)",
    "kernel": "$(uname -r)"
  }
}
EOF

echo -e "${GREEN}Test metadata saved to: ${RESULTS_DIR}/test_metadata.json${NC}\n"
