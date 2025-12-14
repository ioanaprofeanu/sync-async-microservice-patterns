# k6 Load Testing Guide - How to Modify Tests

## Quick Reference: What Each Parameter Does

### 1. Virtual Users (VUs)

**What it is:** Number of concurrent simulated users

```javascript
vus: 5,  // 5 concurrent users
```

**Effect:**
- **Increase (vus: 50):** More concurrent load
  - ✅ Tests parallelism and scalability
  - ✅ Reveals connection pool issues
  - ❌ May overwhelm small systems

- **Decrease (vus: 1):** Single-user smoke test
  - ✅ Good for basic functionality testing
  - ✅ Establishes baseline performance
  - ❌ Won't reveal concurrency issues

**Recommended Values:**
- Smoke test: 1-2 VUs
- Load test: 10-50 VUs
- Stress test: 100+ VUs

---

### 2. Duration

**What it is:** How long the test runs

```javascript
duration: '30s',  // Run for 30 seconds
```

**Effect:**
- **Increase (duration: '5m'):** Longer sustained load
  - ✅ Reveals memory leaks
  - ✅ Tests system stability over time
  - ✅ Better statistical averages

- **Decrease (duration: '10s'):** Quick validation
  - ✅ Fast feedback
  - ❌ May miss warm-up effects
  - ❌ Less reliable averages

**Recommended Values:**
- Quick test: 10-30s
- Standard test: 1-5m
- Soak test: 30m-1h

---

### 3. Arrival Rate (Requests per Second)

**What it is:** Target throughput in requests/second

```javascript
rate: 100,  // 100 requests per second
timeUnit: '1s',
```

**Effect:**
- **Increase (rate: 500):** Higher throughput
  - ✅ Tests maximum capacity
  - ✅ Reveals breaking points
  - ❌ May cause complete failure

- **Decrease (rate: 10):** Gentle load
  - ✅ Safe for testing
  - ❌ Won't reveal limits

**Recommended Values:**
- Light: 10-50 req/s
- Moderate: 100-200 req/s
- Heavy: 500-1000 req/s
- Extreme: 2000+ req/s

---

## Test Modification Examples

### Example 1: Smoke Test (Quick Validation)

**Goal:** Verify all endpoints work with minimal load

```javascript
export const options = {
    scenarios: {
        scenario1_user_registration: {
            executor: 'constant-vus',
            vus: 1,           // ← Change from 5 to 1
            duration: '10s',  // ← Change from 30s to 10s
            exec: 'testScenario1',
        },
        // Repeat for all scenarios
    },
};
```

**Expected Results:**
- Very few/no failures
- Low latency
- Confirms functionality

---

### Example 2: Load Test (Normal Production Traffic)

**Goal:** Test realistic production load

```javascript
export const options = {
    scenarios: {
        scenario1_user_registration: {
            executor: 'constant-vus',
            vus: 20,          // ← Increase from 5
            duration: '3m',   // ← Increase from 30s
            exec: 'testScenario1',
        },

        scenario6_click_tracking: {
            executor: 'constant-arrival-rate',
            rate: 300,        // ← Increase from 100
            timeUnit: '1s',
            duration: '3m',
            preAllocatedVUs: 30,  // ← Increase
            maxVUs: 100,          // ← Increase
            exec: 'testScenario6',
        },
    },
};
```

**Expected Results:**
- Higher throughput
- Some failures may appear
- Latency increases

---

### Example 3: Stress Test (Find Breaking Point)

**Goal:** Push system until it breaks

```javascript
export const options = {
    scenarios: {
        scenario6_click_tracking: {
            executor: 'ramping-arrival-rate',
            startRate: 10,
            timeUnit: '1s',
            stages: [
                { duration: '30s', target: 100 },   // Warm up
                { duration: '1m', target: 500 },    // Increase
                { duration: '1m', target: 1000 },   // Stress
                { duration: '1m', target: 2000 },   // Breaking point
                { duration: '30s', target: 0 },     // Cool down
            ],
            preAllocatedVUs: 50,
            maxVUs: 200,
            exec: 'testScenario6',
        },
    },
};
```

**Expected Results:**
- Gradual performance degradation
- Increasing failure rate
- Identifies maximum capacity

---

### Example 4: Soak Test (Long-Term Stability)

**Goal:** Test for memory leaks and degradation over time

```javascript
export const options = {
    scenarios: {
        scenario1_user_registration: {
            executor: 'constant-vus',
            vus: 10,
            duration: '1h',   // ← Run for 1 hour
            exec: 'testScenario1',
        },
    },
};
```

**Expected Results:**
- Consistent performance over time
- Or: gradual slowdown (indicates leak)
- Memory usage should stabilize

---

### Example 5: Spike Test (Sudden Traffic Burst)

**Goal:** Test how system handles sudden load spikes

```javascript
export const options = {
    scenarios: {
        scenario6_click_tracking: {
            executor: 'ramping-arrival-rate',
            startRate: 50,
            timeUnit: '1s',
            stages: [
                { duration: '1m', target: 50 },     // Baseline
                { duration: '10s', target: 1000 },  // ← Sudden spike!
                { duration: '1m', target: 50 },     // Back to normal
            ],
            preAllocatedVUs: 100,
            maxVUs: 300,
            exec: 'testScenario6',
        },
    },
};
```

**Expected Results:**
- High failure rate during spike
- System recovers after spike
- Queue buildup if async

---

## Understanding Executor Types

### 1. `constant-vus` (Fixed Concurrent Users)

```javascript
executor: 'constant-vus',
vus: 10,
duration: '1m',
```

**Behavior:** 10 users continuously making requests for 1 minute

**Use case:** Test concurrent user load

---

### 2. `constant-arrival-rate` (Fixed Requests/Second)

```javascript
executor: 'constant-arrival-rate',
rate: 100,
timeUnit: '1s',
duration: '1m',
preAllocatedVUs: 20,
maxVUs: 100,
```

**Behavior:** 100 requests/second, k6 adjusts VUs automatically

**Use case:** Test throughput capacity

---

### 3. `ramping-vus` (Gradually Increase Users)

```javascript
executor: 'ramping-vus',
startVUs: 0,
stages: [
    { duration: '1m', target: 50 },
    { duration: '2m', target: 100 },
    { duration: '1m', target: 0 },
],
```

**Behavior:** Gradually increase from 0 → 50 → 100 → 0 VUs

**Use case:** Find capacity limits gradually

---

### 4. `ramping-arrival-rate` (Gradually Increase Req/s)

```javascript
executor: 'ramping-arrival-rate',
startRate: 0,
timeUnit: '1s',
stages: [
    { duration: '1m', target: 100 },
    { duration: '2m', target: 500 },
],
preAllocatedVUs: 50,
maxVUs: 200,
```

**Behavior:** Gradually increase from 0 → 100 → 500 req/s

**Use case:** Stress testing throughput

---

## Practical Test Scenarios for Your Project

### Test 1: Verify Scenario 1 Blocking (Email Delay)

**Goal:** Confirm 500ms email delay is observed

```javascript
scenario1_verification: {
    executor: 'constant-vus',
    vus: 1,              // Single user
    duration: '10s',
    exec: 'testScenario1',
}
```

**Check:** Response time should be 500ms+

---

### Test 2: Find Scenario 6 Breaking Point

**Goal:** How many req/s before failures?

```javascript
scenario6_stress: {
    executor: 'ramping-arrival-rate',
    startRate: 50,
    timeUnit: '1s',
    stages: [
        { duration: '30s', target: 100 },
        { duration: '30s', target: 300 },
        { duration: '30s', target: 500 },
        { duration: '30s', target: 1000 },
    ],
    preAllocatedVUs: 50,
    maxVUs: 300,
    exec: 'testScenario6',
}
```

**Expected:** Start seeing failures at 300-500 req/s

---

### Test 3: Test Scenario 4 Worker Exhaustion

**Goal:** Show that CPU-intensive tasks block workers

```javascript
scenario4_worker_exhaustion: {
    executor: 'constant-vus',
    vus: 10,             // ← Increase from 2 to 10
    duration: '1m',
    exec: 'testScenario4',
}
```

**Expected:**
- Some requests will timeout (>20s)
- Only 1-2 requests complete at a time (workers blocked)

---

### Test 4: Test Saga Compensation Under Load

**Goal:** Verify compensation works under concurrent load

```javascript
scenario5_concurrent_sagas: {
    executor: 'constant-vus',
    vus: 50,             // ← High concurrency
    duration: '2m',
    exec: 'testScenario5',
}
```

**Expected:**
- 100% compensation success
- Database shows no orphaned reservations

---

## Interpreting Results

### Key Metrics to Watch

1. **http_req_duration (Response Time)**
   - **P50 (median):** Typical user experience
   - **P95:** 95% of users see this or better
   - **P99:** Worst-case (excluding outliers)
   - **Max:** Absolute worst case

2. **http_req_failed (Failure Rate)**
   - **0-1%:** Excellent
   - **1-5%:** Acceptable
   - **5-10%:** Concerning
   - **>10%:** System overloaded

3. **http_reqs (Throughput)**
   - Requests per second achieved
   - Compare to target rate

4. **iterations (Completed Tests)**
   - How many test loops completed
   - Lower than expected = slow responses

---

## Running Different Test Types

### Command Line Options

**Basic test:**
```bash
k6 run k6-tests/script-sync.js
```

**Save results to JSON:**
```bash
k6 run --out json=results.json k6-tests/script-sync.js
```

**Save results to CSV:**
```bash
k6 run --out csv=results.csv k6-tests/script-sync.js
```

**Override duration:**
```bash
k6 run --duration 60s k6-tests/script-sync.js
```

**Override VUs:**
```bash
k6 run --vus 50 k6-tests/script-sync.js
```

**Run specific scenario only:**
```bash
k6 run --scenario scenario1_user_registration k6-tests/script-sync.js
```

**Quiet mode (less output):**
```bash
k6 run --quiet k6-tests/script-sync.js
```

**Verbose mode (more details):**
```bash
k6 run --verbose k6-tests/script-sync.js
```

---

## Creating Custom Test Configurations

### Save custom config as separate file:

**heavy-load.js:**
```javascript
import { testScenario1, testScenario6 } from './script-sync.js';

export { testScenario1, testScenario6 };

export const options = {
    scenarios: {
        scenario1_heavy: {
            executor: 'constant-vus',
            vus: 100,
            duration: '5m',
            exec: 'testScenario1',
        },
        scenario6_heavy: {
            executor: 'constant-arrival-rate',
            rate: 1000,
            timeUnit: '1s',
            duration: '5m',
            preAllocatedVUs: 100,
            maxVUs: 500,
            exec: 'testScenario6',
        },
    },
};
```

**Run it:**
```bash
k6 run k6-tests/heavy-load.js
```

---

## Recommended Test Progression

### Phase 1: Smoke Test
- 1 VU, 10s duration
- Verify functionality

### Phase 2: Load Test
- 10-20 VUs, 1-3 minutes
- Verify normal operation

### Phase 3: Stress Test
- Ramp up to 100+ VUs or 500+ req/s
- Find breaking point

### Phase 4: Soak Test
- Moderate load (20 VUs) for 30-60 minutes
- Test stability

### Phase 5: Spike Test
- Sudden bursts of traffic
- Test recovery

---

## Comparing Sync vs Async (for Milestone 3)

When you implement async architecture, run **identical tests** and compare:

```bash
# Sync architecture (current)
k6 run --out json=results-sync.json k6-tests/script-sync.js

# Async architecture (Milestone 3)
k6 run --out json=results-async.json k6-tests/script-async.js
```

**Expected differences:**

| Metric | Sync | Async |
|--------|------|-------|
| Scenario 1 latency | 500ms+ | <50ms |
| Scenario 6 max throughput | 100-300 req/s | 1000+ req/s |
| Failure rate at 500 req/s | 10-20% | <1% |
| Worker blocking (S4) | Yes | No |

---

## Troubleshooting k6 Tests

### Problem: All requests timing out

**Solution:**
```javascript
// Increase timeout in test
const params = {
    timeout: '30s',  // Increase from default
};
```

### Problem: VUs not scaling

**Solution:**
```javascript
// Increase maxVUs
maxVUs: 500,  // Was too low
```

### Problem: Can't reach localhost from k6

**Mac/Windows Docker:**
```javascript
const BASE_URL = 'http://host.docker.internal';
```

**Linux Docker:**
```javascript
const BASE_URL = 'http://172.17.0.1';
```

### Problem: Inconsistent results

**Solution:** Run multiple times and average
```bash
for i in {1..5}; do
    k6 run --out json=results-$i.json k6-tests/script-sync.js
done
```

---

**Quick Reference Created:** 2025-11-16
**For:** Milestone 2 Synchronous Architecture Testing
