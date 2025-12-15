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

// Test configuration - SAME LOAD PATTERNS as sync version for fair comparison
export const options = {
    scenarios: {
        // Scenario 1: Non-Critical Task Decoupling (ASYNC)
        scenario1_user_registration: {
            executor: 'constant-vus',
            exec: 'testScenario1',
            vus: 5,
            duration: '30s',
            tags: { scenario: 'scenario1' },
        },

        // Scenario 2: Long-Running External API Call (ASYNC)
        scenario2_payment_processing: {
            executor: 'constant-vus',
            exec: 'testScenario2',
            vus: 5,
            duration: '30s',
            tags: { scenario: 'scenario2' },
        },

        // Scenario 3: Fan-Out Flow (ASYNC)
        scenario3_product_update: {
            executor: 'constant-vus',
            exec: 'testScenario3',
            vus: 5,
            duration: '30s',
            tags: { scenario: 'scenario3' },
        },

        // Scenario 4: CPU-Intensive Task (ASYNC - can handle MORE VUs now!)
        scenario4_report_generation: {
            executor: 'constant-vus',
            exec: 'testScenario4',
            vus: 2,  // Same VUs for fair comparison
            duration: '30s',
            tags: { scenario: 'scenario4' },
        },

        // Scenario 5: Saga Pattern with Compensation (ASYNC)
        scenario5_order_creation: {
            executor: 'constant-vus',
            exec: 'testScenario5',
            vus: 5,
            duration: '30s',
            tags: { scenario: 'scenario5' },
        },

        // Scenario 6: High-Throughput Data Ingestion (ASYNC)
        scenario6_click_tracking: {
            executor: 'constant-arrival-rate',
            exec: 'testScenario6',
            rate: 100,  // Same rate: 100 requests per second
            timeUnit: '1s',
            duration: '30s',
            preAllocatedVUs: 10,
            maxVUs: 50,
            tags: { scenario: 'scenario6' },
        },
    },
    thresholds: {
        // ASYNC THRESHOLDS: Dramatically lower response times expected
        'http_req_duration{scenario:scenario1}': ['p(95)<100'],  // <100ms vs 1000ms (10x faster!)
        'http_req_duration{scenario:scenario2}': ['p(95)<100'],  // <100ms vs 3000ms (30x faster!)
        'http_req_duration{scenario:scenario3}': ['p(95)<100'],  // <100ms vs 1000ms (10x faster!)
        'http_req_duration{scenario:scenario4}': ['p(95)<100'],  // <100ms vs 15000ms (150x faster!)
        'http_req_duration{scenario:scenario5}': ['p(95)<150'],  // <150ms (allows for slight variability)
        'http_req_duration{scenario:scenario6}': ['p(95)<50'],   // <50ms vs 500ms (10x faster!)
    },
};

// Base URLs - ASYNC PORTS (81xx range)
const BASE_URL = __ENV.BASE_URL || 'http://host.docker.internal';
const USER_SERVICE = `${BASE_URL}:8101`;
const PAYMENT_SERVICE = `${BASE_URL}:8102`;
const PRODUCT_SERVICE = `${BASE_URL}:8103`;
const REPORT_SERVICE = `${BASE_URL}:8104`;
const ORDER_SERVICE = `${BASE_URL}:8105`;
const ANALYTICS_SERVICE = `${BASE_URL}:8106`;

// Scenario 1: Non-Critical Task Decoupling (ASYNC)
// Expected: Immediate 202 response, email sent in background
export function testScenario1() {
    const email = `user${Date.now()}${Math.random()}@example.com`;
    const payload = JSON.stringify({ email: email });

    const params = {
        headers: { 'Content-Type': 'application/json' },
        timeout: '5s',  // Lower timeout - async should be fast
    };

    const res = http.post(`${USER_SERVICE}/register`, payload, params);

    const success = check(res, {
        'Scenario 1 (ASYNC): status is 202 Accepted': (r) => r.status === 202,
        'Scenario 1 (ASYNC): response time < 100ms': (r) => r.timings.duration < 100,
        'Scenario 1 (ASYNC): response has user id': (r) => {
            try {
                const body = JSON.parse(r.body);
                return body.id !== undefined;
            } catch (e) {
                return false;
            }
        },
        'Scenario 1 (ASYNC): event_published is true': (r) => {
            try {
                const body = JSON.parse(r.body);
                return body.event_published === true;
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

// Scenario 2: Long-Running Process (ASYNC)
// Expected: Immediate 202 response, payment processed in background
export function testScenario2() {
    const payload = JSON.stringify({
        amount: 100.00,
        currency: 'USD'
    });

    const params = {
        headers: { 'Content-Type': 'application/json' },
        timeout: '5s',  // Lower timeout - no longer blocking
    };

    const res = http.post(`${PAYMENT_SERVICE}/process_payment`, payload, params);

    const success = check(res, {
        'Scenario 2 (ASYNC): status is 202 Accepted': (r) => r.status === 202,
        'Scenario 2 (ASYNC): response time < 100ms': (r) => r.timings.duration < 100,
        'Scenario 2 (ASYNC): has payment_id': (r) => {
            try {
                const body = JSON.parse(r.body);
                return body.payment_id !== undefined;
            } catch (e) {
                return false;
            }
        },
        'Scenario 2 (ASYNC): status is processing': (r) => {
            try {
                const body = JSON.parse(r.body);
                return body.status === 'processing';
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

// Scenario 3: Fan-Out Flow (ASYNC)
// Expected: Fast response, events propagate to 3 consumers in parallel
export function testScenario3() {
    const productId = Math.floor(Math.random() * 3) + 1; // Products 1-3
    const payload = JSON.stringify({
        name: `Updated Product ${Date.now()}`,
        stock: Math.floor(Math.random() * 100) + 1
    });

    const params = {
        headers: { 'Content-Type': 'application/json' },
        timeout: '5s',
    };

    const res = http.put(`${PRODUCT_SERVICE}/products/${productId}`, payload, params);

    const success = check(res, {
        'Scenario 3 (ASYNC): status is 200 OK': (r) => r.status === 200,
        'Scenario 3 (ASYNC): response time < 100ms': (r) => r.timings.duration < 100,
        'Scenario 3 (ASYNC): response has product id': (r) => {
            try {
                const body = JSON.parse(r.body);
                return body.id !== undefined;
            } catch (e) {
                return false;
            }
        },
        'Scenario 3 (ASYNC): event_published is true': (r) => {
            try {
                const body = JSON.parse(r.body);
                return body.event_published === true;
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

// Scenario 4: CPU-Intensive Task (ASYNC)
// Expected: Immediate 202 with job_id, CPU work happens in background
export function testScenario4() {
    const payload = JSON.stringify({ report_type: 'monthly' });

    const params = {
        headers: { 'Content-Type': 'application/json' },
        timeout: '5s',  // Dramatically reduced from 20s!
    };

    const res = http.post(`${REPORT_SERVICE}/generate_report`, payload, params);

    const success = check(res, {
        'Scenario 4 (ASYNC): status is 202 Accepted': (r) => r.status === 202,
        'Scenario 4 (ASYNC): response time < 150ms': (r) => r.timings.duration < 150,
        'Scenario 4 (ASYNC): has job_id': (r) => {
            try {
                const body = JSON.parse(r.body);
                return body.job_id !== undefined;
            } catch (e) {
                return false;
            }
        },
        'Scenario 4 (ASYNC): status is queued': (r) => {
            try {
                const body = JSON.parse(r.body);
                return body.status === 'queued';
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

// Scenario 5: Choreography Saga Pattern (ASYNC)
// Expected: Immediate 202, saga completes in background, order becomes "failed"
export function testScenario5() {
    const payload = JSON.stringify({
        product_id: 1,
        quantity: 1
    });

    const params = {
        headers: { 'Content-Type': 'application/json' },
        timeout: '5s',
    };

    const res = http.post(`${ORDER_SERVICE}/create_order`, payload, params);

    // First check: Order creation should return 202 immediately
    const creationSuccess = check(res, {
        'Scenario 5 (ASYNC): status is 202 Accepted': (r) => r.status === 202,
        'Scenario 5 (ASYNC): response time < 150ms': (r) => r.timings.duration < 150,
        'Scenario 5 (ASYNC): response has order id': (r) => {
            try {
                const body = JSON.parse(r.body);
                return body.id !== undefined;
            } catch (e) {
                return false;
            }
        },
        'Scenario 5 (ASYNC): initial status is pending': (r) => {
            try {
                const body = JSON.parse(r.body);
                return body.status === 'pending';
            } catch (e) {
                return false;
            }
        },
    });

    if (!creationSuccess) {
        scenario5Errors.add(1);
        sleep(1);
        return;
    }

    // Get order ID for polling
    let orderId;
    try {
        const body = JSON.parse(res.body);
        orderId = body.id;
    } catch (e) {
        scenario5Errors.add(1);
        sleep(1);
        return;
    }

    // Poll for saga completion (optional - demonstrates async saga)
    // Wait a bit for saga to complete (in background)
    // The saga flow: OrderCreated → StockReserved (instant) → PaymentFailed (0.5s delay) → Order status update
    // Need to account for message queue latency under load (multiple queue hops)
    sleep(4);

    // Check if order status changed to "failed" after saga compensation
    const statusRes = http.get(`${ORDER_SERVICE}/orders/${orderId}`, params);

    const sagaSuccess = check(statusRes, {
        'Scenario 5 (ASYNC): saga completed - status is failed': (r) => {
            try {
                const body = JSON.parse(r.body);
                return body.status === 'failed';
            } catch (e) {
                return false;
            }
        },
    });

    if (!sagaSuccess) {
        scenario5Errors.add(1);
    }

    sleep(1);
}

// Scenario 6: High-Throughput Data Ingestion (ASYNC)
// Expected: Ultra-fast response, RabbitMQ acts as buffer
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
        'Scenario 6 (ASYNC): status is 200 OK': (r) => r.status === 200,
        'Scenario 6 (ASYNC): response time < 50ms': (r) => r.timings.duration < 50,
        'Scenario 6 (ASYNC): has status tracked': (r) => {
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
