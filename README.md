# Synchronous Architecture Implementation - Milestone 2

This project implements a **synchronous (request-response) microservices architecture** as part of a comparative study analyzing communication patterns in distributed systems.

## Project Overview

**Objective:** Demonstrate the characteristics, performance, and limitations of synchronous inter-service communication through 6 different scenarios.

**Communication Model:** Strictly synchronous HTTP/REST calls using the `requests` library. All inter-service communication is blocking and sequential.

## Architecture

### Technology Stack

- **Language:** Python 3.10+
- **Framework:** FastAPI
- **Database:** PostgreSQL
- **HTTP Client:** requests (synchronous)
- **Orchestration:** Docker & Docker Compose
- **Testing:** k6 (load testing)
- **Monitoring:** Prometheus + Grafana + cAdvisor

### Microservices

| Service | Port | Database | Description |
|---------|------|----------|-------------|
| UserService | 8001 | Yes | User registration with email notification |
| EmailService | 8007 | No | Email sending simulation (500ms delay) |
| PaymentService | 8002 | No | Payment processing simulation (2s delay) |
| ProductService | 8003 | Yes | Product management with fan-out updates |
| SearchService | 8008 | No | Search index updates |
| CacheService | 8009 | No | Cache invalidation |
| AnalyticsService | 8006 | No | Analytics logging & click tracking |
| ReportService | 8004 | No | CPU-intensive report generation |
| OrderService | 8005 | Yes | Order creation with saga compensation |
| InventoryService | 8010 | Yes | Stock reservation & compensation |
| PostgreSQL | 5432 | - | Shared database |
| **Prometheus** | **9090** | **-** | **Metrics collection and storage** |
| **Grafana** | **3000** | **-** | **Metrics visualization dashboard** |
| **cAdvisor** | **8080** | **-** | **Container resource monitoring** |

## Scenarios

### Scenario 1: Non-Critical Task Decoupling
**Endpoint:** `POST http://localhost:8001/register`

Demonstrates the impact of synchronously waiting for non-critical tasks (email sending).

**Flow:**
1. Client registers a user
2. UserService saves to database
3. UserService **blocks** while calling EmailService (500ms delay)
4. Client waits for entire operation to complete

**Test Point:** Increased latency and reduced throughput due to blocking on non-critical operations.

**Example:**
```bash
curl -X POST http://localhost:8001/register \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com"}'
```

### Scenario 2: Simulated Long-Running Process (External API)
**Endpoint:** `POST http://localhost:8002/process_payment`

Simulates synchronous calls to external APIs with significant latency.

**Flow:**
1. Client requests payment processing
2. PaymentService simulates external API call (2-second delay)
3. Client blocks for 2+ seconds

**Test Point:** Major impact on response time and connection pool exhaustion under load.

**Example:**
```bash
curl -X POST http://localhost:8002/process_payment \
  -H "Content-Type: application/json" \
  -d '{"order_id": 123, "amount": 100.0}'
```

### Scenario 3: Fan-Out Flow
**Endpoint:** `PUT http://localhost:8003/products/{product_id}`

Demonstrates sequential execution of multiple dependent service calls.

**Flow:**
1. Client updates a product
2. ProductService updates database
3. ProductService **sequentially** calls:
   - SearchService (reindex)
   - CacheService (invalidate)
   - AnalyticsService (log update)
4. Each call blocks until the previous completes

**Test Point:** Total latency = sum of all service latencies (no parallelization).

**Example:**
```bash
curl -X PUT http://localhost:8003/products/1 \
  -H "Content-Type: application/json" \
  -d '{"name": "Updated Laptop", "stock": 75}'
```

### Scenario 4: CPU-Intensive Task
**Endpoint:** `POST http://localhost:8004/generate_report`

Tests handling of long-running CPU-bound operations.

**Flow:**
1. Client requests report generation
2. ReportService performs 10 seconds of CPU-intensive work (SHA-256 hashing)
3. Client connection may timeout

**Test Point:** Synchronous systems struggle with long-running tasks (timeout issues, blocked workers).

**Example:**
```bash
curl -X POST http://localhost:8004/generate_report \
  -H "Content-Type: application/json" \
  -d '{"report_type": "monthly"}' \
  --max-time 15
```

### Scenario 5: Choreography and Compensation (Saga Pattern)
**Endpoint:** `POST http://localhost:8005/create_order`

Demonstrates **manual compensation logic** in synchronous saga implementations.

**Flow:**
1. OrderService creates order (status: pending)
2. Calls InventoryService to reserve stock ✓ (succeeds)
3. Calls PaymentService to process payment ✗ (fails intentionally)
4. **Compensation:** Calls InventoryService to unreserve stock
5. Updates order status to "failed"
6. Returns error to client

**Test Point:** Complexity of implementing manual rollback/compensation logic.

**Example:**
```bash
curl -X POST http://localhost:8005/create_order \
  -H "Content-Type: application/json" \
  -d '{"product_id": 1, "quantity": 1}'
```

Expected response: HTTP 400 with compensation details.

### Scenario 6: High-Throughput Data Ingestion
**Endpoint:** `POST http://localhost:8006/track_click`

Tests system behavior under high request volumes.

**Flow:**
1. Client sends click tracking event
2. AnalyticsService logs minimal data and responds immediately

**Test Point:** Synchronous systems will show degraded performance/errors at high throughput (connection pool exhaustion).

**Example:**
```bash
curl -X POST http://localhost:8006/track_click \
  -H "Content-Type: application/json" \
  -d '{"user_id": 123, "page": "homepage"}'
```
