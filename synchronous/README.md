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

## Getting Started

### Prerequisites

- Docker & Docker Compose
- k6 (for load testing): `brew install k6` or see [k6.io/docs](https://k6.io/docs/getting-started/installation/)

### Running the Application

1. **Clone the repository**
   ```bash
   cd sync-async-microservice-patterns
   ```

2. **Start all services**
   ```bash
   docker compose -f docker-compose-sync.yml up --build
   ```

3. **Wait for services to be healthy**

   All services should be running on their respective ports. Check health:
   ```bash
   curl http://localhost:8001/health  # UserService
   curl http://localhost:8002/health  # PaymentService
   curl http://localhost:8003/health  # ProductService
   curl http://localhost:8004/health  # ReportService
   curl http://localhost:8005/health  # OrderService
   curl http://localhost:8006/health  # AnalyticsService
   ```

4. **View logs**
   ```bash
   docker-compose -f docker-compose-sync.yml logs -f [service_name]
   ```

5. **Stop all services**
   ```bash
   docker-compose -f docker-compose-sync.yml down
   ```

### Running k6 Tests

The k6 test script tests all 6 scenarios simultaneously with different load patterns.

**Run from host machine:**
```bash
k6 run k6-tests/script-sync.js
```

**Run with custom duration:**
```bash
k6 run --duration 60s k6-tests/script-sync.js
```

**Run with custom base URL:**
```bash
k6 run --env BASE_URL=http://localhost k6-tests/script-sync.js
```

**View detailed results:**
```bash
k6 run --out json=results.json k6-tests/script-sync.js
```

### Test Results Interpretation

The k6 tests measure:
- **Response times:** How long each request takes
- **Throughput:** Requests per second
- **Error rates:** Failed requests
- **Resource utilization:** Connection pool exhaustion

Expected observations in synchronous architecture:
- **Scenario 1:** Latency increased by ~500ms due to email blocking
- **Scenario 2:** Latency increased by ~2s due to payment processing
- **Scenario 3:** Latency = sum of all three service calls
- **Scenario 4:** Potential timeouts, blocked worker processes
- **Scenario 5:** Successfully demonstrates compensation (always fails as designed)
- **Scenario 6:** Degraded performance at high throughput, connection errors

## Monitoring Stack

The project includes a complete monitoring stack with **Prometheus**, **Grafana**, and **cAdvisor** for real-time metrics visualization and analysis.

### Components

1. **Prometheus** (Port 9090)
   - Collects metrics from all FastAPI services via `/metrics` endpoints
   - Scrapes container metrics from cAdvisor
   - Stores time-series data for querying

2. **Grafana** (Port 3000)
   - Visualizes metrics through pre-configured dashboards
   - Default credentials: `admin` / `admin`
   - Auto-provisioned datasource and dashboards

3. **cAdvisor** (Port 8080)
   - Monitors container resource usage (CPU, memory, network)
   - Provides detailed container-level metrics

### Accessing Monitoring Tools

**Prometheus:**
```
http://localhost:9090
```
- Query metrics directly using PromQL
- Check target health: Status > Targets
- View all collected metrics

**Grafana Dashboard:**
```
http://localhost:3000
```
- Username: `admin`
- Password: `admin`
- Navigate to: Dashboards > Synchronous Microservices - Performance Dashboard

**cAdvisor:**
```
http://localhost:8080
```
- View real-time container metrics
- Monitor resource usage per container

### Available Metrics

#### Application Metrics (from FastAPI services)

Each service exposes Prometheus metrics at `/metrics`:

```bash
# Example: View UserService metrics
curl http://localhost:8001/metrics
```

**Key Metrics:**
- `http_requests_total` - Total HTTP requests by method, status, handler
- `http_request_duration_seconds` - Request latency histograms (P50, P90, P95, P99)
- `http_requests_in_progress` - Current in-flight requests

#### Container Metrics (from cAdvisor)

- `container_cpu_usage_seconds_total` - CPU usage per container
- `container_memory_usage_bytes` - Memory usage per container
- `container_network_receive_bytes_total` - Network ingress
- `container_network_transmit_bytes_total` - Network egress

### Grafana Dashboard Panels

The pre-configured dashboard includes:

**System Overview:**
- Total Request Rate (all services)
- Overall Error Rate (5xx errors)

**Service Request Metrics:**
- Request Rate per Service (RPS)
- Error Rate per Service (HTTP 5xx)

**Latency Metrics:**
- P95 Latency per Service (95th percentile response times)

**Container Resources:**
- CPU Usage per Container (%)
- Memory Usage per Container (MB)

**Scenario-Specific Panels:**
- Scenario 1: User Registration + Email latency
- Scenario 2: Payment Processing latency
- Scenario 3: Fan-Out Flow request rates
- Scenario 4: CPU-Intensive task CPU usage
- Scenario 5: Saga Pattern request rates
- Scenario 6: High-Throughput click tracking RPS

### Running Load Tests with Monitoring

**Complete workflow:**

1. **Start all services including monitoring stack:**
   ```bash
   docker-compose -f docker-compose-sync.yml up --build
   ```

2. **Open Grafana dashboard:**
   ```
   http://localhost:3000
   ```
   Login with `admin` / `admin`

3. **Run k6 load tests:**
   ```bash
   k6 run --env BASE_URL=http://localhost --out json=results.json k6-tests/script-sync.js
   ```

4. **Watch real-time metrics** in Grafana as tests execute

5. **Analyze results:**
   - Grafana: Visual trends and patterns
   - k6 output: Statistical summaries
   - Prometheus: Direct metric queries

### Useful Prometheus Queries

**Request rate by service:**
```promql
rate(http_requests_total{job="userservice"}[1m])
```

**Error rate percentage:**
```promql
sum(rate(http_requests_total{status=~"5..",job="userservice"}[5m]))
/
sum(rate(http_requests_total{job="userservice"}[5m]))
```

**P95 latency:**
```promql
histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket{job="userservice"}[5m])) by (le))
```

**Container CPU usage:**
```promql
rate(container_cpu_usage_seconds_total{name="userservice_sync"}[1m]) * 100
```

**Container memory in MB:**
```promql
container_memory_usage_bytes{name="userservice_sync"} / 1024 / 1024
```

### Monitoring Configuration Files

```
├── prometheus/
│   └── prometheus.yml          # Prometheus scrape config
├── grafana/
│   └── provisioning/
│       ├── datasources/
│       │   └── datasource.yml  # Auto-provision Prometheus
│       └── dashboards/
│           ├── dashboard.yml   # Dashboard provider config
│           └── microservices-dashboard.json  # Dashboard definition
```

### Tips for Monitoring

1. **Before running tests:** Check Prometheus targets are all UP
   - http://localhost:9090/targets
   - All FastAPI services should show "UP"

2. **During tests:** Watch Grafana dashboard in real-time
   - Refresh interval: 5s (auto-refresh enabled)
   - Time range: Last 15 minutes

3. **After tests:** Query Prometheus for specific metrics
   - Use PromQL to dig deeper into specific services
   - Compare metrics across different scenarios

4. **Resource monitoring:** Check cAdvisor for container health
   - Identify resource-constrained services
   - Monitor for memory leaks or CPU spikes

## API Documentation

Each service exposes interactive API documentation:

- UserService: http://localhost:8001/docs
- PaymentService: http://localhost:8002/docs
- ProductService: http://localhost:8003/docs
- ReportService: http://localhost:8004/docs
- OrderService: http://localhost:8005/docs
- AnalyticsService: http://localhost:8006/docs

## Database Schema

### Users Table (UserService)
```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR UNIQUE NOT NULL
);
```

### Products Table (ProductService)
```sql
CREATE TABLE products (
    id SERIAL PRIMARY KEY,
    name VARCHAR NOT NULL,
    stock INTEGER DEFAULT 0
);
```

### Orders Table (OrderService)
```sql
CREATE TABLE orders (
    id SERIAL PRIMARY KEY,
    product_id INTEGER NOT NULL,
    quantity INTEGER DEFAULT 1,
    status VARCHAR NOT NULL  -- 'pending', 'completed', 'failed'
);
```

### Inventory Items Table (InventoryService)
```sql
CREATE TABLE inventory_items (
    product_id INTEGER PRIMARY KEY,
    reserved INTEGER DEFAULT 0
);
```

## Project Structure

```
.
├── analyticsservice/
│   ├── main.py
│   ├── Dockerfile
│   └── requirements.txt
├── cacheservice/
│   ├── main.py
│   ├── Dockerfile
│   └── requirements.txt
├── emailservice/
│   ├── main.py
│   ├── Dockerfile
│   └── requirements.txt
├── inventoryservice/
│   ├── main.py
│   ├── Dockerfile
│   └── requirements.txt
├── orderservice/
│   ├── main.py
│   ├── Dockerfile
│   └── requirements.txt
├── paymentservice/
│   ├── main.py
│   ├── Dockerfile
│   └── requirements.txt
├── productservice/
│   ├── main.py
│   ├── Dockerfile
│   └── requirements.txt
├── reportservice/
│   ├── main.py
│   ├── Dockerfile
│   └── requirements.txt
├── searchservice/
│   ├── main.py
│   ├── Dockerfile
│   └── requirements.txt
├── userservice/
│   ├── main.py
│   ├── Dockerfile
│   └── requirements.txt
├── k6-tests/
│   └── script-sync.js
├── docker-compose-sync.yml
└── README.md
```

## Troubleshooting

### Services won't start
```bash
# Check Docker is running
docker ps

# Check for port conflicts
lsof -i :8001-8010

# View service logs
docker-compose -f docker-compose-sync.yml logs [service_name]
```

### Database connection errors
```bash
# Ensure PostgreSQL is healthy
docker-compose -f docker-compose-sync.yml ps postgres

# Check PostgreSQL logs
docker-compose -f docker-compose-sync.yml logs postgres

# Restart services
docker-compose -f docker-compose-sync.yml restart
```

### k6 tests failing
```bash
# Ensure all services are running
curl http://localhost:8001/health

# Check if ports are accessible
telnet localhost 8001

# Run with verbose logging
k6 run --verbose k6-tests/script-sync.js
```

## Next Steps: Milestone 3

Milestone 3 will implement the **asynchronous (event-driven) architecture** using:
- RabbitMQ message broker
- Asynchronous message passing
- Event choreography
- Comparison with synchronous results

## License

This project is part of an academic research study on microservice communication patterns.

## Authors

- Profeanu Ioana
- Ciobanu
- Girlea
- Dumitrescu

## References

- FastAPI Documentation: https://fastapi.tiangolo.com/
- Docker Compose: https://docs.docker.com/compose/
- k6 Load Testing: https://k6.io/docs/
- PostgreSQL: https://www.postgresql.org/docs/
