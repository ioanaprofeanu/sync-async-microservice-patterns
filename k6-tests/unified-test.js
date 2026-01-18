/**
 * Unified K6 Test Script for Sync vs Async Comparison
 *
 * Environment Variables:
 * - ARCH: 'sync' or 'async' (required)
 * - LOAD_PROFILE: 'light', 'medium', 'heavy', 'stress', 'spike' (default: 'medium')
 * - TEST_DURATION: Duration in seconds (default: from profile)
 * - BASE_URL: Base URL for services (default: http://localhost)
 */

import http from 'k6/http';
import { check, sleep } from 'k6';
import { Counter, Rate, Trend } from 'k6/metrics';

// ==================== Configuration ====================

const ARCH = __ENV.ARCH || 'sync'; // 'sync' or 'async'
const LOAD_PROFILE = __ENV.LOAD_PROFILE || 'medium';
const BASE_URL = __ENV.BASE_URL || 'http://localhost';

// Custom metrics for detailed analysis
const errorRate = new Rate('error_rate');
const scenario1Duration = new Trend('scenario1_duration');
const scenario2Duration = new Trend('scenario2_duration');
const scenario3Duration = new Trend('scenario3_duration');
const scenario4Duration = new Trend('scenario4_duration');
const scenario5Duration = new Trend('scenario5_duration');
const scenario6Duration = new Trend('scenario6_duration');

const scenario1Errors = new Counter('scenario1_errors');
const scenario2Errors = new Counter('scenario2_errors');
const scenario3Errors = new Counter('scenario3_errors');
const scenario4Errors = new Counter('scenario4_errors');
const scenario5Errors = new Counter('scenario5_errors');
const scenario6Errors = new Counter('scenario6_errors');

// ==================== Load Profiles ====================

const LOAD_PROFILES = {
    // Light load - Baseline performance testing
    light: {
        scenario1_vus: 2,
        scenario2_vus: 2,
        scenario3_vus: 2,
        scenario4_vus: 1,
        scenario5_vus: 2,
        scenario6_rate: 20,
        scenario6_maxVUs: 10,
        duration: '30s',
        description: 'Light load - baseline performance'
    },

    // Medium load - Normal production traffic
    medium: {
        scenario1_vus: 5,
        scenario2_vus: 5,
        scenario3_vus: 5,
        scenario4_vus: 2,
        scenario5_vus: 5,
        scenario6_rate: 100,
        scenario6_maxVUs: 50,
        duration: '60s',
        description: 'Medium load - typical production'
    },

    // Heavy load - Peak traffic simulation
    heavy: {
        scenario1_vus: 10,
        scenario2_vus: 10,
        scenario3_vus: 10,
        scenario4_vus: 5,
        scenario5_vus: 10,
        scenario6_rate: 300,
        scenario6_maxVUs: 100,
        duration: '90s',
        description: 'Heavy load - peak traffic'
    },

    // Stress test - Beyond normal capacity
    stress: {
        scenario1_vus: 20,
        scenario2_vus: 20,
        scenario3_vus: 20,
        scenario4_vus: 10,
        scenario5_vus: 20,
        scenario6_rate: 500,
        scenario6_maxVUs: 200,
        duration: '120s',
        description: 'Stress test - capacity limits'
    },

    // Spike test - Sudden traffic surge
    spike: {
        scenario1_vus: 30,
        scenario2_vus: 30,
        scenario3_vus: 30,
        scenario4_vus: 15,
        scenario5_vus: 30,
        scenario6_rate: 1000,
        scenario6_maxVUs: 300,
        duration: '60s',
        description: 'Spike test - sudden surge'
    }
};

const profile = LOAD_PROFILES[LOAD_PROFILE] || LOAD_PROFILES.medium;
const testDuration = __ENV.TEST_DURATION ? `${__ENV.TEST_DURATION}s` : profile.duration;

console.log(`========================================`);
console.log(`Architecture: ${ARCH.toUpperCase()}`);
console.log(`Load Profile: ${LOAD_PROFILE.toUpperCase()}`);
console.log(`Description: ${profile.description}`);
console.log(`Duration: ${testDuration}`);
console.log(`========================================`);

// ==================== Service URLs ====================

const PORT_OFFSET = ARCH === 'async' ? 100 : 0; // async uses 81xx, sync uses 80xx
const USER_SERVICE = `${BASE_URL}:${8001 + PORT_OFFSET}`;
const PAYMENT_SERVICE = `${BASE_URL}:${8002 + PORT_OFFSET}`;
const PRODUCT_SERVICE = `${BASE_URL}:${8003 + PORT_OFFSET}`;
const REPORT_SERVICE = `${BASE_URL}:${8004 + PORT_OFFSET}`;
const ORDER_SERVICE = `${BASE_URL}:${8005 + PORT_OFFSET}`;
const ANALYTICS_SERVICE = `${BASE_URL}:${8006 + PORT_OFFSET}`;

// ==================== Test Configuration ====================

export const options = {
    scenarios: {
        scenario1_user_registration: {
            executor: 'constant-vus',
            exec: 'testScenario1',
            vus: profile.scenario1_vus,
            duration: testDuration,
            tags: { scenario: 'scenario1' },
        },
        scenario2_payment_processing: {
            executor: 'constant-vus',
            exec: 'testScenario2',
            vus: profile.scenario2_vus,
            duration: testDuration,
            tags: { scenario: 'scenario2' },
        },
        scenario3_product_update: {
            executor: 'constant-vus',
            exec: 'testScenario3',
            vus: profile.scenario3_vus,
            duration: testDuration,
            tags: { scenario: 'scenario3' },
        },
        scenario4_report_generation: {
            executor: 'constant-vus',
            exec: 'testScenario4',
            vus: profile.scenario4_vus,
            duration: testDuration,
            tags: { scenario: 'scenario4' },
        },
        scenario5_order_creation: {
            executor: 'constant-vus',
            exec: 'testScenario5',
            vus: profile.scenario5_vus,
            duration: testDuration,
            tags: { scenario: 'scenario5' },
        },
        scenario6_click_tracking: {
            executor: 'constant-arrival-rate',
            exec: 'testScenario6',
            rate: profile.scenario6_rate,
            timeUnit: '1s',
            duration: testDuration,
            preAllocatedVUs: Math.floor(profile.scenario6_maxVUs * 0.2),
            maxVUs: profile.scenario6_maxVUs,
            tags: { scenario: 'scenario6' },
        },
    },
    thresholds: ARCH === 'async' ? {
        // Async thresholds - expect fast responses
        'http_req_duration{scenario:scenario1}': ['p(95)<100', 'p(99)<200'],
        'http_req_duration{scenario:scenario2}': ['p(95)<100', 'p(99)<200'],
        'http_req_duration{scenario:scenario3}': ['p(95)<100', 'p(99)<200'],
        'http_req_duration{scenario:scenario4}': ['p(95)<200', 'p(99)<500'],
        'http_req_duration{scenario:scenario5}': ['p(95)<150', 'p(99)<300'],
        'http_req_duration{scenario:scenario6}': ['p(95)<50', 'p(99)<100'],
        'error_rate': ['rate<0.01'], // Less than 1% errors
    } : {
        // Sync thresholds - expect slower responses
        'http_req_duration{scenario:scenario1}': ['p(95)<1000', 'p(99)<2000'],
        'http_req_duration{scenario:scenario2}': ['p(95)<3000', 'p(99)<5000'],
        'http_req_duration{scenario:scenario3}': ['p(95)<1000', 'p(99)<2000'],
        'http_req_duration{scenario:scenario4}': ['p(95)<15000', 'p(99)<20000'],
        'http_req_duration{scenario:scenario5}': ['p(95)<5000', 'p(99)<10000'],
        'http_req_duration{scenario:scenario6}': ['p(95)<500', 'p(99)<1000'],
        'error_rate': ['rate<0.05'], // Less than 5% errors
    },
};

// ==================== Test Scenarios ====================

export function testScenario1() {
    const email = `user${Date.now()}${Math.random()}@example.com`;
    const payload = JSON.stringify({ email: email });
    const params = {
        headers: { 'Content-Type': 'application/json' },
        timeout: '10s',
    };

    const res = http.post(`${USER_SERVICE}/register`, payload, params);
    scenario1Duration.add(res.timings.duration);

    const expectedStatus = ARCH === 'async' ? 202 : 201;
    const success = check(res, {
        [`status is ${expectedStatus}`]: (r) => r.status === expectedStatus,
        'response has user id': (r) => {
            try {
                return JSON.parse(r.body).id !== undefined;
            } catch (e) {
                return false;
            }
        },
    });

    if (!success) {
        scenario1Errors.add(1);
        errorRate.add(1);
    } else {
        errorRate.add(0);
    }

    sleep(1);
}

export function testScenario2() {
    const payload = JSON.stringify({
        amount: 100.00,
        currency: 'USD'
    });
    const params = {
        headers: { 'Content-Type': 'application/json' },
        timeout: '10s',
    };

    const res = http.post(`${PAYMENT_SERVICE}/process_payment`, payload, params);
    scenario2Duration.add(res.timings.duration);

    const expectedStatus = ARCH === 'async' ? 202 : 200;
    const success = check(res, {
        [`status is ${expectedStatus}`]: (r) => r.status === expectedStatus,
        'response has payment/transaction id': (r) => {
            try {
                const body = JSON.parse(r.body);
                return ARCH === 'async' ? body.payment_id !== undefined : body.transaction_id !== undefined;
            } catch (e) {
                return false;
            }
        },
    });

    if (!success) {
        scenario2Errors.add(1);
        errorRate.add(1);
    } else {
        errorRate.add(0);
    }

    sleep(1);
}

export function testScenario3() {
    const productId = Math.floor(Math.random() * 3) + 1;
    const payload = JSON.stringify({
        name: `Updated Product ${Date.now()}`,
        stock: Math.floor(Math.random() * 100) + 1
    });
    const params = {
        headers: { 'Content-Type': 'application/json' },
        timeout: '10s',
    };

    const res = http.put(`${PRODUCT_SERVICE}/products/${productId}`, payload, params);
    scenario3Duration.add(res.timings.duration);

    const success = check(res, {
        'status is 200': (r) => r.status === 200,
        'response has product id': (r) => {
            try {
                return JSON.parse(r.body).id !== undefined;
            } catch (e) {
                return false;
            }
        },
    });

    if (!success) {
        scenario3Errors.add(1);
        errorRate.add(1);
    } else {
        errorRate.add(0);
    }

    sleep(1);
}

export function testScenario4() {
    const payload = JSON.stringify({ report_type: 'monthly' });
    const params = {
        headers: { 'Content-Type': 'application/json' },
        timeout: ARCH === 'async' ? '5s' : '20s',
    };

    const res = http.post(`${REPORT_SERVICE}/generate_report`, payload, params);
    scenario4Duration.add(res.timings.duration);

    const expectedStatus = ARCH === 'async' ? 202 : 200;
    const success = check(res, {
        [`status is ${expectedStatus}`]: (r) => r.status === expectedStatus,
        'response has job_id or report_hash': (r) => {
            try {
                const body = JSON.parse(r.body);
                return ARCH === 'async' ? body.job_id !== undefined : body.report_hash !== undefined;
            } catch (e) {
                return false;
            }
        },
    });

    if (!success) {
        scenario4Errors.add(1);
        errorRate.add(1);
    } else {
        errorRate.add(0);
    }

    sleep(2);
}

export function testScenario5() {
    const payload = JSON.stringify({
        product_id: 1,
        quantity: 1
    });
    const params = {
        headers: { 'Content-Type': 'application/json' },
        timeout: '10s',
    };

    const res = http.post(`${ORDER_SERVICE}/create_order`, payload, params);
    scenario5Duration.add(res.timings.duration);

    let success;
    if (ARCH === 'async') {
        // Async returns 202, order created with pending status
        success = check(res, {
            'status is 202': (r) => r.status === 202,
            'response has order id': (r) => {
                try {
                    return JSON.parse(r.body).id !== undefined;
                } catch (e) {
                    return false;
                }
            },
        });
    } else {
        // Sync returns 400, saga failed with compensation
        success = check(res, {
            'status is 400 (expected failure)': (r) => r.status === 400,
            'compensation executed': (r) => {
                try {
                    const body = JSON.parse(r.body);
                    return body.detail && body.detail.compensation_executed === true;
                } catch (e) {
                    return false;
                }
            },
        });
    }

    if (!success) {
        scenario5Errors.add(1);
        errorRate.add(1);
    } else {
        errorRate.add(0);
    }

    sleep(1);
}

export function testScenario6() {
    const payload = JSON.stringify({
        user_id: Math.floor(Math.random() * 10000),
        page: 'homepage'
    });
    const params = {
        headers: { 'Content-Type': 'application/json' },
        timeout: '5s',
    };

    const res = http.post(`${ANALYTICS_SERVICE}/track_click`, payload, params);
    scenario6Duration.add(res.timings.duration);

    const success = check(res, {
        'status is 200': (r) => r.status === 200,
        'has status tracked': (r) => {
            try {
                return JSON.parse(r.body).status === 'tracked';
            } catch (e) {
                return false;
            }
        },
    });

    if (!success) {
        scenario6Errors.add(1);
        errorRate.add(1);
    } else {
        errorRate.add(0);
    }
}

// ==================== Setup & Teardown ====================

export function setup() {
    console.log(`\n🚀 Starting ${ARCH.toUpperCase()} test with ${LOAD_PROFILE.toUpperCase()} profile\n`);
}

export function teardown(data) {
    console.log(`\n✅ Test completed for ${ARCH.toUpperCase()}\n`);
}
