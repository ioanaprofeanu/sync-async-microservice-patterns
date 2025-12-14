import http from 'k6/http';
import { check, sleep } from 'k6';
import { Counter } from 'k6/metrics';

// Custom metrics
const scenario1Errors = new Counter('scenario1_errors');
const scenario2Errors = new Counter('scenario2_errors');
const scenario3Errors = new Counter('scenario3_errors');
const scenario4Errors = new Counter('scenario4_errors');
const scenario5Errors = new Counter('scenario5_errors');
const scenario6Errors = new Counter('scenario6_errors');

// Test configuration
export const options = {
    scenarios: {
        // Scenario 1: Non-Critical Task Decoupling
        scenario1_user_registration: {
            executor: 'constant-vus',
            exec: 'testScenario1',
            vus: 5,
            duration: '30s',
            tags: { scenario: 'scenario1' },
        },

        // Scenario 2: Long-Running External API Call
        scenario2_payment_processing: {
            executor: 'constant-vus',
            exec: 'testScenario2',
            vus: 5,
            duration: '30s',
            tags: { scenario: 'scenario2' },
        },

        // Scenario 3: Fan-Out Flow
        scenario3_product_update: {
            executor: 'constant-vus',
            exec: 'testScenario3',
            vus: 5,
            duration: '30s',
            tags: { scenario: 'scenario3' },
        },

        // Scenario 4: CPU-Intensive Task (fewer VUs due to long duration)
        scenario4_report_generation: {
            executor: 'constant-vus',
            exec: 'testScenario4',
            vus: 2,
            duration: '30s',
            tags: { scenario: 'scenario4' },
        },

        // Scenario 5: Saga Pattern with Compensation
        scenario5_order_creation: {
            executor: 'constant-vus',
            exec: 'testScenario5',
            vus: 5,
            duration: '30s',
            tags: { scenario: 'scenario5' },
        },

        // Scenario 6: High-Throughput Data Ingestion
        scenario6_click_tracking: {
            executor: 'constant-arrival-rate',
            exec: 'testScenario6',
            rate: 100,  // 100 requests per second
            timeUnit: '1s',
            duration: '30s',
            preAllocatedVUs: 10,
            maxVUs: 50,
            tags: { scenario: 'scenario6' },
        },
    },
    thresholds: {
        'http_req_duration{scenario:scenario1}': ['p(95)<1000'],  // 95% of requests should be below 1s
        'http_req_duration{scenario:scenario2}': ['p(95)<3000'],  // 95% of requests should be below 3s
        'http_req_duration{scenario:scenario3}': ['p(95)<1000'],  // 95% of requests should be below 1s
        'http_req_duration{scenario:scenario4}': ['p(95)<15000'], // 95% of requests should be below 15s
        'http_req_duration{scenario:scenario6}': ['p(95)<500'],   // 95% of requests should be below 500ms
    },
};

// Base URLs
const BASE_URL = __ENV.BASE_URL || 'http://host.docker.internal';
const USER_SERVICE = `${BASE_URL}:8001`;
const PAYMENT_SERVICE = `${BASE_URL}:8002`;
const PRODUCT_SERVICE = `${BASE_URL}:8003`;
const REPORT_SERVICE = `${BASE_URL}:8004`;
const ORDER_SERVICE = `${BASE_URL}:8005`;
const ANALYTICS_SERVICE = `${BASE_URL}:8006`;

// Scenario 1: Non-Critical Task Decoupling
export function testScenario1() {
    const email = `user${Date.now()}${Math.random()}@example.com`;
    const payload = JSON.stringify({ email: email });

    const params = {
        headers: { 'Content-Type': 'application/json' },
        timeout: '10s',
    };

    const res = http.post(`${USER_SERVICE}/register`, payload, params);

    const success = check(res, {
        'Scenario 1: status is 201': (r) => r.status === 201,
        'Scenario 1: response time > 500ms': (r) => r.timings.duration > 500,
        'Scenario 1: response has user id': (r) => {
            try {
                const body = JSON.parse(r.body);
                return body.id !== undefined;
            } catch (e) {
                return false;
            }
        },
    });

    if (!success) {
        scenario1Errors.add(1);
    }

    sleep(1);
}

// Scenario 2: Simulated Long-Running Process (External API)
export function testScenario2() {
    const payload = JSON.stringify({
        order_id: Math.floor(Math.random() * 10000),
        amount: 100.00
    });

    const params = {
        headers: { 'Content-Type': 'application/json' },
        timeout: '10s',
    };

    const res = http.post(`${PAYMENT_SERVICE}/process_payment`, payload, params);

    const success = check(res, {
        'Scenario 2: status is 200': (r) => r.status === 200,
        'Scenario 2: response time > 2000ms': (r) => r.timings.duration > 2000,
        'Scenario 2: has transaction_id': (r) => {
            try {
                const body = JSON.parse(r.body);
                return body.transaction_id !== undefined;
            } catch (e) {
                return false;
            }
        },
    });

    if (!success) {
        scenario2Errors.add(1);
    }

    sleep(1);
}

// Scenario 3: Fan-Out Flow
export function testScenario3() {
    const productId = Math.floor(Math.random() * 3) + 1; // Products 1-3
    const payload = JSON.stringify({
        name: `Updated Product ${Date.now()}`,
        stock: Math.floor(Math.random() * 100) + 1
    });

    const params = {
        headers: { 'Content-Type': 'application/json' },
        timeout: '10s',
    };

    const res = http.put(`${PRODUCT_SERVICE}/products/${productId}`, payload, params);

    const success = check(res, {
        'Scenario 3: status is 200': (r) => r.status === 200,
        'Scenario 3: response has product id': (r) => {
            try {
                const body = JSON.parse(r.body);
                return body.id !== undefined;
            } catch (e) {
                return false;
            }
        },
    });

    if (!success) {
        scenario3Errors.add(1);
    }

    sleep(1);
}

// Scenario 4: CPU-Intensive Task
export function testScenario4() {
    const payload = JSON.stringify({ report_type: 'monthly' });

    const params = {
        headers: { 'Content-Type': 'application/json' },
        timeout: '20s',  // Increased timeout for CPU-intensive task
    };

    const res = http.post(`${REPORT_SERVICE}/generate_report`, payload, params);

    const success = check(res, {
        'Scenario 4: status is 200': (r) => r.status === 200,
        'Scenario 4: response time > 10000ms': (r) => r.timings.duration > 10000,
        'Scenario 4: has report_hash': (r) => {
            try {
                const body = JSON.parse(r.body);
                return body.report_hash !== undefined;
            } catch (e) {
                return false;
            }
        },
    });

    if (!success) {
        scenario4Errors.add(1);
    }

    sleep(2);
}

// Scenario 5: Choreography and Compensation (Saga Pattern)
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

    // We expect this to fail (status 400) due to payment failure
    const success = check(res, {
        'Scenario 5: status is 400 (expected failure)': (r) => r.status === 400,
        'Scenario 5: response has error message': (r) => {
            try {
                const body = JSON.parse(r.body);
                return body.detail && body.detail.message !== undefined;
            } catch (e) {
                return false;
            }
        },
        'Scenario 5: compensation was executed': (r) => {
            try {
                const body = JSON.parse(r.body);
                return body.detail && body.detail.compensation_executed === true;
            } catch (e) {
                return false;
            }
        },
    });

    if (!success) {
        scenario5Errors.add(1);
    }

    sleep(1);
}

// Scenario 6: High-Throughput Data Ingestion
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

    const success = check(res, {
        'Scenario 6: status is 200': (r) => r.status === 200,
        'Scenario 6: response is fast': (r) => r.timings.duration < 1000,
        'Scenario 6: has status tracked': (r) => {
            try {
                const body = JSON.parse(r.body);
                return body.status === 'tracked';
            } catch (e) {
                return false;
            }
        },
    });

    if (!success) {
        scenario6Errors.add(1);
    }

    // No sleep - high throughput testing
}
