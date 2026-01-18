#!/bin/bash

################################################################################
# Quick Academic Performance Testing Suite (1 Hour)
# Optimized for time-constrained comprehensive analysis
#
# Usage:
#   ./run-quick-academic-tests.sh
#
# Duration: ~58 minutes
# Runs: 2 per configuration
# Architectures: Both sync and async
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
RESULTS_DIR="academic-results/quick_$(date +"%Y%m%d_%H%M%S")"
mkdir -p "${RESULTS_DIR}"

echo -e "${CYAN}${BOLD}"
cat << "EOF"
╔══════════════════════════════════════════════════════════════════╗
║         QUICK ACADEMIC PERFORMANCE TEST SUITE (1 HOUR)          ║
║        Comprehensive Sync vs Async Analysis in 58 Minutes       ║
╚══════════════════════════════════════════════════════════════════╝
EOF
echo -e "${NC}"

echo -e "${BLUE}Results Directory:${NC} ${RESULTS_DIR}"
echo -e "${BLUE}Estimated Duration:${NC} ~58 minutes"
echo -e "${BLUE}Test Runs per Config:${NC} 2"
echo -e "${BLUE}Architectures:${NC} Sync + Async\n"

# Test configurations: name, s1_vus, s2_vus, s3_vus, s4_vus, s5_vus, s6_rate, duration
declare -a TESTS=(
    "baseline:2:2:2:1:2:50:120"
    "light:5:5:5:2:5:100:120"
    "medium:10:10:10:3:10:150:120"
    "medium_high:15:15:15:5:15:200:120"
    "heavy:20:20:20:7:20:250:180"
    "stress:30:30:30:10:30:300:180"
)

NUM_RUNS=2
TOTAL_TESTS=$((${#TESTS[@]} * 2 * NUM_RUNS))  # tests * architectures * runs
CURRENT_TEST=0

# Function to update progress
update_progress() {
    CURRENT_TEST=$((CURRENT_TEST + 1))
    local percent=$((CURRENT_TEST * 100 / TOTAL_TESTS))
    echo -e "${CYAN}Progress: ${CURRENT_TEST}/${TOTAL_TESTS} (${percent}%)${NC}\n"
}

# Function to run a single test
run_test() {
    local test_name=$1
    local arch=$2
    local run_num=$3
    local s1_vus=$4
    local s2_vus=$5
    local s3_vus=$6
    local s4_vus=$7
    local s5_vus=$8
    local s6_rate=$9
    local duration=${10}

    local arch_upper=$(echo "$arch" | tr '[:lower:]' '[:upper:]')
    local output_file="${RESULTS_DIR}/${test_name}_${arch}_run${run_num}"

    echo -e "${MAGENTA}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${MAGENTA}${BOLD}Test: ${test_name} | ${arch_upper} | Run ${run_num}/${NUM_RUNS}${NC}"
    echo -e "${YELLOW}VUs: (${s1_vus},${s2_vus},${s3_vus},${s4_vus},${s5_vus}) | Rate: ${s6_rate}/s | Duration: ${duration}s${NC}"
    echo -e "${MAGENTA}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"

    # Run k6 with inline options
    k6 run \
        --env ARCH="${arch}" \
        --env BASE_URL=http://localhost \
        --out json="${output_file}.json" \
        --summary-export="${output_file}_summary.json" \
        - <<EOJS
import http from 'k6/http';
import { check, sleep } from 'k6';
import { Counter, Rate, Trend } from 'k6/metrics';

const ARCH = __ENV.ARCH || 'sync';
const BASE_URL = __ENV.BASE_URL || 'http://localhost';
const PORT_OFFSET = ARCH === 'async' ? 100 : 0;

const USER_SERVICE = \`\${BASE_URL}:\${8001 + PORT_OFFSET}\`;
const PAYMENT_SERVICE = \`\${BASE_URL}:\${8002 + PORT_OFFSET}\`;
const PRODUCT_SERVICE = \`\${BASE_URL}:\${8003 + PORT_OFFSET}\`;
const REPORT_SERVICE = \`\${BASE_URL}:\${8004 + PORT_OFFSET}\`;
const ORDER_SERVICE = \`\${BASE_URL}:\${8005 + PORT_OFFSET}\`;
const ANALYTICS_SERVICE = \`\${BASE_URL}:\${8006 + PORT_OFFSET}\`;

const errorRate = new Rate('error_rate');
const scenario1Duration = new Trend('scenario1_duration');
const scenario2Duration = new Trend('scenario2_duration');
const scenario3Duration = new Trend('scenario3_duration');
const scenario4Duration = new Trend('scenario4_duration');
const scenario5Duration = new Trend('scenario5_duration');
const scenario6Duration = new Trend('scenario6_duration');

export const options = {
    scenarios: {
        scenario1: { executor: 'constant-vus', exec: 'testScenario1', vus: ${s1_vus}, duration: '${duration}s', tags: { scenario: 'scenario1' } },
        scenario2: { executor: 'constant-vus', exec: 'testScenario2', vus: ${s2_vus}, duration: '${duration}s', tags: { scenario: 'scenario2' } },
        scenario3: { executor: 'constant-vus', exec: 'testScenario3', vus: ${s3_vus}, duration: '${duration}s', tags: { scenario: 'scenario3' } },
        scenario4: { executor: 'constant-vus', exec: 'testScenario4', vus: ${s4_vus}, duration: '${duration}s', tags: { scenario: 'scenario4' } },
        scenario5: { executor: 'constant-vus', exec: 'testScenario5', vus: ${s5_vus}, duration: '${duration}s', tags: { scenario: 'scenario5' } },
        scenario6: { executor: 'constant-arrival-rate', exec: 'testScenario6', rate: ${s6_rate}, timeUnit: '1s', duration: '${duration}s', preAllocatedVUs: 10, maxVUs: 50, tags: { scenario: 'scenario6' } },
    },
};

export function testScenario1() {
    const res = http.post(\`\${USER_SERVICE}/register\`, JSON.stringify({ email: \`user\${Date.now()}\${Math.random()}@example.com\` }), { headers: { 'Content-Type': 'application/json' }, timeout: '10s' });
    scenario1Duration.add(res.timings.duration);
    const success = check(res, { 'status ok': (r) => ARCH === 'async' ? r.status === 202 : r.status === 201 });
    errorRate.add(success ? 0 : 1);
    sleep(1);
}

export function testScenario2() {
    const res = http.post(\`\${PAYMENT_SERVICE}/process_payment\`, JSON.stringify({ amount: 100.00, currency: 'USD' }), { headers: { 'Content-Type': 'application/json' }, timeout: '10s' });
    scenario2Duration.add(res.timings.duration);
    const success = check(res, { 'status ok': (r) => ARCH === 'async' ? r.status === 202 : r.status === 200 });
    errorRate.add(success ? 0 : 1);
    sleep(1);
}

export function testScenario3() {
    const res = http.put(\`\${PRODUCT_SERVICE}/products/\${Math.floor(Math.random() * 3) + 1}\`, JSON.stringify({ name: \`Product \${Date.now()}\`, stock: 100 }), { headers: { 'Content-Type': 'application/json' }, timeout: '10s' });
    scenario3Duration.add(res.timings.duration);
    const success = check(res, { 'status ok': (r) => r.status === 200 });
    errorRate.add(success ? 0 : 1);
    sleep(1);
}

export function testScenario4() {
    const res = http.post(\`\${REPORT_SERVICE}/generate_report\`, JSON.stringify({ report_type: 'monthly' }), { headers: { 'Content-Type': 'application/json' }, timeout: ARCH === 'async' ? '5s' : '20s' });
    scenario4Duration.add(res.timings.duration);
    const success = check(res, { 'status ok': (r) => ARCH === 'async' ? r.status === 202 : r.status === 200 });
    errorRate.add(success ? 0 : 1);
    sleep(2);
}

export function testScenario5() {
    const res = http.post(\`\${ORDER_SERVICE}/create_order\`, JSON.stringify({ product_id: 1, quantity: 1 }), { headers: { 'Content-Type': 'application/json' }, timeout: '10s' });
    scenario5Duration.add(res.timings.duration);
    const success = check(res, { 'status ok': (r) => ARCH === 'async' ? r.status === 202 : r.status === 400 });
    errorRate.add(success ? 0 : 1);
    sleep(1);
}

export function testScenario6() {
    const res = http.post(\`\${ANALYTICS_SERVICE}/track_click\`, JSON.stringify({ user_id: Math.floor(Math.random() * 10000), page: 'homepage' }), { headers: { 'Content-Type': 'application/json' }, timeout: '5s' });
    scenario6Duration.add(res.timings.duration);
    const success = check(res, { 'status ok': (r) => r.status === 200 });
    errorRate.add(success ? 0 : 1);
}
EOJS

    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Test completed${NC}\n"
        update_progress
        return 0
    else
        echo -e "${RED}✗ Test failed${NC}\n"
        update_progress
        return 1
    fi
}

# Main test execution
START_TIME=$(date +%s)

for test_config in "${TESTS[@]}"; do
    IFS=':' read -r name s1 s2 s3 s4 s5 s6 dur <<< "$test_config"

    echo -e "\n${BOLD}${BLUE}╔════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BOLD}${BLUE}║  Test Suite: ${name}${NC}"
    echo -e "${BOLD}${BLUE}╚════════════════════════════════════════════════════════╝${NC}\n"

    for run in $(seq 1 $NUM_RUNS); do
        # Sync test
        run_test "$name" "sync" "$run" "$s1" "$s2" "$s3" "$s4" "$s5" "$s6" "$dur"
        sleep 5  # Brief cool-down

        # Async test
        run_test "$name" "async" "$run" "$s1" "$s2" "$s3" "$s4" "$s5" "$s6" "$dur"

        if [ $run -lt $NUM_RUNS ]; then
            sleep 10  # Cool-down between runs
        fi
    done
done

END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))
MINUTES=$((DURATION / 60))
SECONDS=$((DURATION % 60))

echo -e "\n${CYAN}${BOLD}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}${BOLD}║            ALL TESTS COMPLETED                         ║${NC}"
echo -e "${CYAN}${BOLD}╚════════════════════════════════════════════════════════╝${NC}\n"

echo -e "${GREEN}✓ Total Duration: ${MINUTES}m ${SECONDS}s${NC}"
echo -e "${GREEN}✓ Results saved in: ${RESULTS_DIR}${NC}\n"

# Save metadata
cat > "${RESULTS_DIR}/metadata.json" << EOF
{
  "total_duration_seconds": ${DURATION},
  "num_tests": ${TOTAL_TESTS},
  "num_runs_per_config": ${NUM_RUNS},
  "timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "system": {
    "os": "$(uname -s)",
    "arch": "$(uname -m)"
  }
}
EOF

echo -e "${YELLOW}Next steps:${NC}"
echo -e "${BLUE}1. Analyze results: python3 analyze-academic-results.py ${RESULTS_DIR}${NC}"
echo -e "${BLUE}2. Generate report: The analysis script will create comparison tables${NC}\n"
