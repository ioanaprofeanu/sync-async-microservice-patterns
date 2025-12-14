# Monitoring Stack Setup Guide

## Overview

Your synchronous microservices project now includes a complete monitoring stack with:
- **Prometheus** - Metrics collection and storage
- **Grafana** - Visualization and dashboards
- **cAdvisor** - Container resource monitoring
- **Prometheus FastAPI Instrumentator** - Automatic metrics from all FastAPI services

---

## What Was Added

### 1. Docker Compose Services

Added to `docker-compose-sync.yml`:

```yaml
prometheus:      # Port 9090 - Metrics database
grafana:         # Port 3000 - Visualization
cadvisor:        # Port 8080 - Container metrics
```

### 2. Configuration Files Created

```
prometheus/
└── prometheus.yml                    # Scrape config for all services

grafana/
└── provisioning/
    ├── datasources/
    │   └── datasource.yml           # Auto-add Prometheus
    └── dashboards/
        ├── dashboard.yml            # Dashboard provider
        └── microservices-dashboard.json  # Complete dashboard
```

### 3. All Services Instrumented

Each of the 10 FastAPI services now has:
- `prometheus-fastapi-instrumentator==6.1.0` in requirements.txt
- Prometheus instrumentation in main.py:
  ```python
  from prometheus_fastapi_instrumentator import Instrumentator
  Instrumentator().instrument(app).expose(app)
  ```
- `/metrics` endpoint exposing Prometheus metrics

---

## Quick Start

### 1. Start Everything

```bash
cd sync-async-microservice-patterns
docker compose -f docker-compose-sync.yml up --build
```

Wait for all services to start (~30-60 seconds)

### 2. Access Monitoring Tools

**Grafana Dashboard:**
```
http://localhost:3000
Username: admin
Password: admin
```

**Prometheus:**
```
http://localhost:9090
```

**cAdvisor:**
```
http://localhost:8080
```

### 3. View the Dashboard

1. Go to http://localhost:3000
2. Login with `admin` / `admin`
3. Navigate to: **Dashboards → Synchronous Microservices - Performance Dashboard**
4. You should see the complete monitoring dashboard!

### 4. Run Load Tests and Watch Metrics

Open Grafana dashboard, then in another terminal:

```bash
k6 run --env BASE_URL=http://localhost --out json=results.json k6-tests/script-sync.js
```

Watch the metrics update in real-time!

---

## Dashboard Panels Explained

### System Overview

**Total Request Rate:**
- Shows aggregate requests/second across all services
- Useful for seeing overall system load

**Overall Error Rate (5xx):**
- Gauge showing percentage of 5xx errors
- Green (<1%), Yellow (1-5%), Red (>5%)

### Service Metrics

**Request Rate per Service (RPS):**
- Line chart showing req/s for each of the 10 services
- Identifies which services receive most traffic

**Error Rate per Service:**
- Line chart showing error percentage per service
- Quickly identify problematic services

**P95 Latency per Service:**
- Shows 95th percentile response times
- Identifies slow services (95% of requests complete within this time)

### Container Resources

**CPU Usage per Container (%):**
- Real-time CPU percentage for each Docker container
- Identifies CPU-intensive services (look for ReportService during Scenario 4!)

**Memory Usage per Container (MB):**
- Memory consumption per container
- Useful for detecting memory leaks

### Scenario-Specific

**Scenario 1 (User Registration):**
- Latency for UserService and EmailService
- Should show 500ms+ latency due to email blocking

**Scenario 2 (Payment Processing):**
- PaymentService latency
- Should show 2+ second delays

**Scenario 3 (Fan-Out Flow):**
- Request rates for ProductService, SearchService, CacheService
- Shows sequential blocking behavior

**Scenario 4 (CPU-Intensive):**
- ReportService CPU usage
- Should spike to high % during report generation

**Scenario 5 (Saga Pattern):**
- Request rates for OrderService and InventoryService
- Shows compensation flow

**Scenario 6 (High Throughput):**
- AnalyticsService click tracking throughput
- Tests at 100+ req/s

---

## Metrics Available

### FastAPI Application Metrics

Each service exposes these at `/metrics`:

**http_requests_total**
- Counter of total HTTP requests
- Labels: method, status, handler, job

**http_request_duration_seconds**
- Histogram of request latencies
- Enables P50, P90, P95, P99 calculations

**http_requests_in_progress**
- Gauge of current in-flight requests

**Example:**
```bash
curl http://localhost:8001/metrics
```

### Container Metrics (from cAdvisor)

**CPU:**
- `container_cpu_usage_seconds_total`
- `container_cpu_system_seconds_total`

**Memory:**
- `container_memory_usage_bytes`
- `container_memory_max_usage_bytes`

**Network:**
- `container_network_receive_bytes_total`
- `container_network_transmit_bytes_total`

---

## Useful Prometheus Queries

### Application Performance

**Request rate for UserService:**
```promql
rate(http_requests_total{job="userservice"}[1m])
```

**Error rate percentage:**
```promql
sum(rate(http_requests_total{status=~"5..",job="userservice"}[5m]))
/
sum(rate(http_requests_total{job="userservice"}[5m]))
```

**P95 latency in seconds:**
```promql
histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket{job="userservice"}[5m])) by (le))
```

**P99 latency (worst case):**
```promql
histogram_quantile(0.99, sum(rate(http_request_duration_seconds_bucket{job="userservice"}[5m])) by (le))
```

**Requests by status code:**
```promql
sum by (status) (rate(http_requests_total{job="userservice"}[5m]))
```

### Container Resources

**CPU percentage:**
```promql
rate(container_cpu_usage_seconds_total{name="userservice_sync"}[1m]) * 100
```

**Memory in MB:**
```promql
container_memory_usage_bytes{name="userservice_sync"} / 1024 / 1024
```

**Memory in GB:**
```promql
container_memory_usage_bytes{name="userservice_sync"} / 1024 / 1024 / 1024
```

**Network receive rate (bytes/sec):**
```promql
rate(container_network_receive_bytes_total{name="userservice_sync"}[1m])
```

### Comparing Services

**Top 5 services by request rate:**
```promql
topk(5, sum by (job) (rate(http_requests_total[5m])))
```

**Services with highest error rates:**
```promql
topk(5, sum by (job) (rate(http_requests_total{status=~"5.."}[5m])))
```

**Services with highest latency:**
```promql
topk(5, histogram_quantile(0.95, sum by (job, le) (rate(http_request_duration_seconds_bucket[5m]))))
```

---

## Troubleshooting

### Prometheus Targets Not UP

**Check target status:**
```
http://localhost:9090/targets
```

**If services show "DOWN":**
1. Ensure all containers are running:
   ```bash
   docker-compose -f docker-compose-sync.yml ps
   ```
2. Check service logs:
   ```bash
   docker-compose -f docker-compose-sync.yml logs userservice
   ```
3. Verify `/metrics` endpoint:
   ```bash
   curl http://localhost:8001/metrics
   ```

### Grafana Dashboard Not Showing Data

**Check Prometheus datasource:**
1. Go to Configuration → Data Sources
2. Click on "Prometheus"
3. Click "Test" at the bottom
4. Should show "Data source is working"

**If no data appears:**
1. Check time range (top right) - set to "Last 15 minutes"
2. Ensure Prometheus has targets UP
3. Run k6 tests to generate traffic

### No Metrics from Services

**Rebuild containers:**
```bash
docker-compose -f docker-compose-sync.yml down
docker compose -f docker-compose-sync.yml up --build
```

**Verify instrumentation:**
```bash
curl http://localhost:8001/metrics | grep http_requests_total
```

Should return metrics lines.

### cAdvisor Not Working on Mac

If cAdvisor fails to start on Mac:

1. Edit `docker-compose-sync.yml`
2. In cadvisor section, remove or comment out:
   ```yaml
   devices:
     - /dev/kmsg
   ```

### High CPU Usage

This is expected during:
- Scenario 4 (ReportService generates reports)
- High load k6 tests

Monitor with:
```bash
docker stats
```

---

## Advanced Usage

### Custom Dashboard

To create your own dashboard:
1. Go to http://localhost:3000
2. Click "+" → "Dashboard"
3. Add panels with custom queries
4. Save dashboard

### Export Metrics to File

```bash
# Export current metrics
curl http://localhost:9090/api/v1/query?query=http_requests_total > metrics.json
```

### Alert Rules (Optional)

Create `prometheus/alerts.yml`:
```yaml
groups:
  - name: api_alerts
    rules:
      - alert: HighErrorRate
        expr: |
          sum(rate(http_requests_total{status=~"5.."}[5m]))
          /
          sum(rate(http_requests_total[5m]))
          > 0.05
        for: 1m
        labels:
          severity: warning
        annotations:
          summary: "High error rate detected"
```

Update `prometheus/prometheus.yml`:
```yaml
rule_files:
  - "alerts.yml"
```

---

## Metrics for Your Research Paper

### Key Metrics to Collect

**Performance:**
- Request Rate (RPS)
- P50, P95, P99 Latency
- Throughput under load

**Reliability:**
- Error rate %
- Success rate %
- Timeout rate

**Resources:**
- CPU usage (%)
- Memory usage (MB)
- Network I/O

**Scenario-Specific:**
- S1: Email blocking impact (500ms delay)
- S2: External API impact (2s delay)
- S3: Sequential fan-out latency accumulation
- S4: CPU-intensive task worker blocking
- S5: Saga compensation execution
- S6: Maximum throughput capacity

### Collecting Data for Comparison

**For Synchronous Architecture (Milestone 2):**
```bash
# Run 5-minute load test
k6 run --duration 5m --env BASE_URL=http://localhost k6-tests/script-sync.js

# Export Prometheus metrics
curl http://localhost:9090/api/v1/query_range?query=rate(http_requests_total[1m])&start=$(date -u -d '5 minutes ago' +%s)&end=$(date +%s)&step=15s > sync_metrics.json
```

**For Asynchronous Architecture (Milestone 3):**
- Run same tests
- Compare metrics side-by-side
- Create comparison charts

---

## File Structure

Complete monitoring setup:

```
sync-async-microservice-patterns/
├── docker-compose-sync.yml           # Updated with monitoring services
├── prometheus/
│   └── prometheus.yml                # Scrape all 10 services + cAdvisor
├── grafana/
│   └── provisioning/
│       ├── datasources/
│       │   └── datasource.yml        # Auto-provision Prometheus
│       └── dashboards/
│           ├── dashboard.yml         # Dashboard provider
│           └── microservices-dashboard.json  # Pre-built dashboard
├── userservice/
│   ├── main.py                       # ✓ Prometheus instrumentation added
│   └── requirements.txt              # ✓ prometheus-fastapi-instrumentator added
├── emailservice/
│   ├── main.py                       # ✓ Instrumented
│   └── requirements.txt              # ✓ Updated
├── paymentservice/
│   ├── main.py                       # ✓ Instrumented
│   └── requirements.txt              # ✓ Updated
├── productservice/
│   ├── main.py                       # ✓ Instrumented
│   └── requirements.txt              # ✓ Updated
├── searchservice/
│   ├── main.py                       # ✓ Instrumented
│   └── requirements.txt              # ✓ Updated
├── cacheservice/
│   ├── main.py                       # ✓ Instrumented
│   └── requirements.txt              # ✓ Updated
├── analyticsservice/
│   ├── main.py                       # ✓ Instrumented
│   └── requirements.txt              # ✓ Updated
├── reportservice/
│   ├── main.py                       # ✓ Instrumented
│   └── requirements.txt              # ✓ Updated
├── orderservice/
│   ├── main.py                       # ✓ Instrumented
│   └── requirements.txt              # ✓ Updated
└── inventoryservice/
    ├── main.py                       # ✓ Instrumented
    └── requirements.txt              # ✓ Updated
```

---

## Summary

You now have:
✅ Complete monitoring stack (Prometheus + Grafana + cAdvisor)
✅ All 10 services instrumented with Prometheus metrics
✅ Pre-configured comprehensive Grafana dashboard
✅ Real-time visualization of all 6 scenarios
✅ Container resource monitoring
✅ Ready for comparative study with async architecture

**Next steps:**
1. Start services: `docker-compose -f docker-compose-sync.yml up --build`
2. Open Grafana: http://localhost:3000 (admin/admin). If it shows problem with prometheus, restart grafana service: docker compose -f docker-compose-sync.yml restart grafana
3. Run k6 tests and watch metrics in real-time!

Happy monitoring! 📊
