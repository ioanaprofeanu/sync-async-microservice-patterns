# Asynchronous Architecture Implementation - Milestone 3

This project implements an **asynchronous event-driven microservices architecture** using RabbitMQ as part of a comparative study analyzing communication patterns in distributed systems.

## Project Overview

**Objective:** Demonstrate the characteristics, performance advantages, and trade-offs of asynchronous event-driven communication through the same 6 scenarios implemented in the synchronous architecture.

**Communication Model:** Event-driven architecture using RabbitMQ message broker. HTTP endpoints accept requests and return immediately (202 Accepted), while actual processing happens asynchronously via message queues.

---

## Table of Contents

- [Architecture](#architecture)
- [Key Differences from Synchronous Version](#key-differences-from-synchronous-version)
- [Expected Performance Comparison](#expected-performance-comparison)
- [Programming Perspective](#programming-perspective)
- [Scenarios](#scenarios)
- [Getting Started](#getting-started)
- [Monitoring Stack](#monitoring-stack)
- [Troubleshooting](#troubleshooting)

---

## Architecture

### Technology Stack

- **Language:** Python 3.10+
- **Framework:** FastAPI (async endpoints)
- **Message Broker:** **RabbitMQ** (with management plugin)
- **Message Client:** **aio_pika** (async AMQP client)
- **Database:** PostgreSQL (async with asyncpg)
- **Orchestration:** Docker & Docker Compose
- **Testing:** k6 (load testing)
- **Monitoring:** Prometheus + Grafana + cAdvisor + RabbitMQ Management

### Microservices

| Service | Port | Database | Pattern | Description |
|---------|------|----------|---------|-------------|
| UserService | 8101 | Yes | Publisher | User registration, publishes UserRegistered events |
| EmailService | 8107 | No | Consumer | Listens to UserRegistered, sends emails async |
| PaymentService | 8102 | No | Publisher + Consumer | Processes payments async, participates in saga |
| ProductService | 8103 | Yes | Fanout Publisher | Product updates, publishes to fanout exchange |
| SearchService | 8108 | No | Fanout Consumer | Reindexes search from product events |
| CacheService | 8109 | No | Fanout Consumer | Invalidates cache from product events |
| AnalyticsService | 8106 | No | Fanout Consumer + Publisher | Analytics & high-throughput click tracking |
| ReportService | 8104 | No | Publisher + Consumer | Offloads CPU-intensive jobs to workers |
| OrderService | 8105 | Yes | Saga Orchestrator | Creates orders, handles saga events |
| InventoryService | 8110 | Yes | Saga Participant | Reserves stock, compensates on failure |
| PostgreSQL | 5433 | - | Shared database (different port to avoid conflicts) |
| **RabbitMQ** | **5672/15672** | **-** | **Message broker (AMQP + Management UI)** |
| **Prometheus** | **9091** | **-** | **Metrics collection** |
| **Grafana** | **3001** | **-** | **Metrics visualization** |
| **cAdvisor** | **8081** | **-** | **Container monitoring** |

### Event-Driven Patterns Used

| Pattern | Scenario | Services | Exchange Type | Description |
|---------|----------|----------|---------------|-------------|
| **Fire-and-Forget** | 1 | User → Email | Direct | Publish event, return immediately |
| **Background Processing** | 2, 4 | Payment, Report | Direct | Offload work to background workers |
| **Fan-Out (Pub/Sub)** | 3 | Product → Search/Cache/Analytics | **Fanout** | 1 event → multiple consumers in parallel |
| **Saga Choreography** | 5 | Order/Inventory/Payment | Direct | Event-driven compensation flow |
| **Buffering** | 6 | Analytics clicks | Direct | Queue acts as buffer for high throughput |

---

## Key Differences from Synchronous Version

### 1. Communication Mechanism

| Aspect | Synchronous | Asynchronous |
|--------|-------------|--------------|
| **Protocol** | HTTP (requests library) | AMQP (RabbitMQ via aio_pika) |
| **Inter-Service Calls** | `requests.post(url, ...)` | `rabbitmq_client.publish_message(queue, event)` |
| **Response Time** | Waits for downstream services | Returns immediately (202 Accepted) |
| **Coupling** | Tight (caller knows callee URL) | Loose (caller publishes to queue) |
| **Blocking** | Caller thread blocks | Non-blocking (event-driven) |

### 2. HTTP Response Codes

| Scenario | Synchronous | Asynchronous | Reason |
|----------|-------------|--------------|--------|
| User Registration | **201 Created** | **202 Accepted** | Email sent in background |
| Payment Processing | **200 OK** | **202 Accepted** | Payment processed async |
| Report Generation | **200 OK** | **202 Accepted** | CPU work offloaded to worker |
| Order Creation | **400 Bad Request** | **202 Accepted** | Saga runs in background |

### 3. Saga Pattern Implementation

| Aspect | Synchronous | Asynchronous |
|--------|-------------|--------------|
| **Compensation** | Manual try-catch blocks | Event-driven choreography |
| **Coordination** | OrderService orchestrates with direct HTTP calls | Services react to events autonomously |
| **Rollback** | Immediate, synchronous | Eventual consistency via events |
| **Complexity** | Complex nested try-catch | Simpler event handlers |
| **Example** | `try { reserve() } catch { unreserve() }` | Publish `PaymentFailed` → consumers react |

### 4. Infrastructure Requirements

**Synchronous:**
- PostgreSQL
- Prometheus
- Grafana
- cAdvisor

**Asynchronous (Additional):**
- ✅ **RabbitMQ** (message broker)
- ✅ **RabbitMQ Management UI** (monitoring)
- ✅ **Message queues** (8+ queues for different scenarios)
- ✅ **Consumer processes** (background workers in each service)

### 5. Code Structure Changes

**Synchronous Service (example):**
```python
@app.post("/register", status_code=201)
def register_user(user_data):
    # Save to DB
    user = save_user(user_data)

    # BLOCKING call to email service
    requests.post(EMAIL_SERVICE_URL + "/send_email", json={"email": user.email})

    return user  # Returns after email sent
```

**Asynchronous Service (example):**
```python
@app.post("/register", status_code=202)
async def register_user(user_data):
    # Save to DB (async)
    user = await save_user(user_data)

    # NON-BLOCKING publish event
    event = UserRegisteredEvent(user_id=user.id, email=user.email)
    await rabbitmq_client.publish_message("user_registered_queue", event_to_json(event))

    return user  # Returns IMMEDIATELY (email sent in background by EmailService consumer)
```

### 6. Dependency Management

**Synchronous:**
- Services depend on each other being available
- Cascading failures if one service is down
- `depends_on` in docker-compose for service order

**Asynchronous:**
- Services depend on RabbitMQ being available
- Queues buffer messages if consumer is down
- Messages processed when consumer comes back online
- More resilient to individual service failures

### 7. Testing Expectations

| Test Aspect | Synchronous | Asynchronous |
|-------------|-------------|--------------|
| **Response Time** | Includes processing time | Instant (< 100ms) |
| **Throughput** | Limited by slowest service | Much higher (queue buffering) |
| **Error Handling** | Immediate errors to client | Errors handled by consumers |
| **Verification** | Response contains results | Poll separate endpoint for status |

---

## Expected Performance Comparison

### Where Async is **BETTER** ⚡

#### 1. Response Time (Dramatically Better)

| Scenario | Sync P95 Latency | Async P95 Latency | Improvement |
|----------|------------------|-------------------|-------------|
| **Scenario 1** (Email) | >500ms | **<100ms** | **5x faster** |
| **Scenario 2** (Payment) | >2000ms | **<100ms** | **20x faster** |
| **Scenario 3** (Fan-Out) | ~300ms (3 sequential calls) | **<100ms** | **3x faster** |
| **Scenario 4** (CPU Task) | >10000ms | **<100ms** | **100x faster!** |
| **Scenario 6** (High Throughput) | <500ms | **<50ms** | **10x faster** |

**Why:** API returns immediately; processing happens in background.

#### 2. Throughput (Much Better)

| Metric | Synchronous | Asynchronous | Reason |
|--------|-------------|--------------|--------|
| **Max req/s** | ~50 | **~500+** | No thread blocking |
| **Concurrent requests** | Limited by thread pool | Very high | Event-driven |
| **Queue buffering** | None | **RabbitMQ buffers** | Absorbs traffic spikes |

**Why:** Non-blocking I/O allows handling many more concurrent requests.

#### 3. Resource Utilization (Better)

| Resource | Synchronous | Asynchronous | Reason |
|----------|-------------|--------------|--------|
| **CPU during I/O** | Wasted (threads blocked) | **Productive** | No blocking |
| **Memory per request** | High (thread stack) | **Lower** | Event loop |
| **Connection pool** | Exhausted under load | **Rarely exhausted** | Async connections |

**Why:** Async I/O is more efficient than thread-per-request model.

#### 4. Scalability (Much Better)

- **Horizontal scaling:** Add more consumer instances easily
- **Load distribution:** RabbitMQ distributes work across consumers
- **Resilience:** Queues buffer during traffic spikes
- **Graceful degradation:** Slow consumers don't block API

#### 5. Decoupling (Better)

- Services don't need to know about each other
- Can deploy/update services independently
- Adding new consumers doesn't affect publishers
- Failures isolated (one service down doesn't cascade)

### Where Async is **SAME** 🟰

#### 1. Functional Correctness
- Both architectures produce the same results
- Same business logic
- Same data consistency guarantees (eventual vs immediate)

#### 2. Database Operations
- Same database schema
- Same queries
- Same transactions (within service boundaries)

#### 3. Monitoring Metrics
- Both expose Prometheus metrics
- Same dashboard structure
- Same PromQL queries (just different values)

### Where Async is **WORSE/MORE COMPLEX** ⚠️

#### 1. Operational Complexity (Worse)

| Aspect | Synchronous | Asynchronous | Impact |
|--------|-------------|--------------|--------|
| **Infrastructure** | PostgreSQL only | PostgreSQL + **RabbitMQ** | More services to manage |
| **Debugging** | Linear stack traces | **Distributed traces across events** | Harder to debug |
| **Monitoring** | HTTP metrics | HTTP + **Queue metrics** | More complexity |
| **Deployment** | 11 services | 11 services + **RabbitMQ** | More moving parts |

#### 2. Development Complexity (More Complex)

| Aspect | Synchronous | Asynchronous | Difference |
|--------|-------------|--------------|------------|
| **Error Handling** | Try-catch | **DLQ, retries, idempotency** | More sophisticated |
| **Testing** | Unit tests | Unit tests + **Event testing** | More test scenarios |
| **Message Schemas** | Not needed | **Must define events** | Additional work |
| **Consumer Management** | Not needed | **Start/stop consumers** | Lifecycle management |

#### 3. Consistency Model (Different Trade-off)

| Aspect | Synchronous | Asynchronous |
|--------|-------------|--------------|
| **Consistency** | **Immediate** | **Eventual** |
| **Client sees result** | Instantly | Must poll or use webhooks |
| **Data freshness** | Always current | May be slightly delayed |

**Example:**
- **Sync:** User registration returns after email sent
- **Async:** User registration returns before email sent (user must trust it will be sent)

#### 4. Message Ordering (Potential Issue)

- Events may be processed out of order
- Must handle duplicate messages (idempotency)
- Need message versioning for schema changes

#### 5. Debugging Challenges

**Synchronous:**
```
Client → UserService → EmailService → Email Sent
         (single stack trace)
```

**Asynchronous:**
```
Client → UserService (returns immediately)
            ↓
        Queue → EmailService (separate process, separate logs)
                    ↓
                Email Sent (when?)
```

Debugging requires correlating logs across multiple services and queue states.

---

## Programming Perspective

### Ease of Implementation

#### **Synchronous: Simpler to Start** ✅

**Pros:**
- ✅ Straightforward request-response model
- ✅ Familiar HTTP/REST patterns
- ✅ Easy to understand flow: `A → B → C`
- ✅ Less boilerplate code
- ✅ Easier to debug (single call stack)

**Cons:**
- ❌ Manual error handling becomes complex
- ❌ Compensation logic is nested try-catch hell
- ❌ Performance issues appear under load
- ❌ Thread pool management required

**Example (Sync):**
```python
def create_order(order_data):
    try:
        # Step 1: Reserve stock
        inventory_response = requests.post(f"{INVENTORY_URL}/reserve", json=order_data)
        inventory_response.raise_for_status()

        try:
            # Step 2: Process payment
            payment_response = requests.post(f"{PAYMENT_URL}/process", json=order_data)
            payment_response.raise_for_status()

            # Success!
            return {"status": "success"}

        except requests.exceptions.HTTPError:
            # Compensate: Unreserve stock
            requests.post(f"{INVENTORY_URL}/unreserve", json=order_data)
            raise

    except Exception as e:
        # Handle errors...
        return {"status": "failed"}
```

**Code Smell:** Nested try-catch blocks, manual compensation.

---

#### **Asynchronous: More Complex Initially, Cleaner Long-term** 📈

**Pros:**
- ✅ Cleaner separation of concerns (publish vs consume)
- ✅ Event handlers are simple, focused functions
- ✅ No nested compensation logic
- ✅ Scales better with more scenarios
- ✅ Easier to add new consumers without changing publishers

**Cons:**
- ❌ Steeper learning curve (RabbitMQ, events, async/await)
- ❌ More initial setup (message schemas, consumers)
- ❌ Requires understanding of eventual consistency
- ❌ Debugging is harder (distributed traces)

**Example (Async):**
```python
# Publisher (OrderService)
@app.post("/create_order", status_code=202)
async def create_order(order_data):
    # Create order
    order = await create_order_in_db(order_data)

    # Publish event (fire and forget)
    event = OrderCreatedEvent(order_id=order.id, product_id=order_data.product_id)
    await rabbitmq_client.publish_message("order_created_queue", event_to_json(event))

    return order  # Done! No waiting, no compensation here

# Consumer (InventoryService)
async def handle_order_created(message_body, message):
    event = json_to_event(message_body, OrderCreatedEvent)

    # Reserve stock
    await reserve_stock(event.product_id, event.quantity)

    # Publish next event
    await publish_stock_reserved_event(event.order_id)

# Consumer (InventoryService - compensation)
async def handle_payment_failed(message_body, message):
    event = json_to_event(message_body, PaymentFailedEvent)

    # Compensate automatically on event
    await release_stock(event.order_id)
```

**Cleaner:** No nested try-catch, event handlers are simple, compensation is just another event handler.

---

### Logic Flow Comparison

#### **Synchronous: Linear, Easy to Follow** 📖

```
Client Request
    ↓
[OrderService]
    ↓ HTTP POST /reserve
[InventoryService] → Reserve Stock
    ↓ 200 OK
[OrderService]
    ↓ HTTP POST /payment
[PaymentService] → Process Payment (FAILS)
    ↓ 400 Error
[OrderService]
    ↓ HTTP POST /unreserve (Compensation)
[InventoryService] → Unreserve Stock
    ↓ 200 OK
[OrderService]
    ↓
Client Response (400 Error)
```

**Pros:** Can read top-to-bottom, single execution path.
**Cons:** Everything happens in one request cycle (slow).

---

#### **Asynchronous: Event-Driven, Parallel** 🔀

```
Client Request
    ↓
[OrderService] → Publish OrderCreated → Return 202 Accepted
    ↓                                        ↓
    |                                   Client Done! ⚡
    ↓
Queue: order_created_queue
    ↓
[InventoryService Consumer]
    ↓ Reserve Stock
    ↓ Publish StockReserved
    ↓
Queue: stock_reserved_queue
    ↓
[PaymentService Consumer]
    ↓ Process Payment (FAILS)
    ↓ Publish PaymentFailed
    ↓
Queue: payment_failed_queue
    ↓                    ↓
[InventoryService]   [OrderService]
    ↓                    ↓
Unreserve Stock     Update Order Status
(Compensation)      (to "failed")
```

**Pros:** Client gets instant response, processing happens in background, parallel event handling.
**Cons:** Harder to trace (need to follow events across services), eventual consistency.

---

### Which is Easier to Understand?

| Audience | Synchronous | Asynchronous |
|----------|-------------|--------------|
| **Beginners** | ✅ Much easier | ❌ Requires event-driven concepts |
| **Debugging Issues** | ✅ Single stack trace | ❌ Distributed tracing needed |
| **Adding New Features** | ❌ Modify existing code | ✅ Add new event handler |
| **Understanding Flow** | ✅ Linear, obvious | ⚠️ Follow events through queues |
| **Code Maintenance** | ⚠️ Gets messy with scale | ✅ Stays clean with proper event design |

---

### Development Workflow Comparison

#### **Synchronous Development**

1. ✅ Write endpoint
2. ✅ Make HTTP call to other service
3. ✅ Handle response
4. ❌ Add error handling (lots of try-catch)
5. ❌ Add compensation logic (complex)
6. ✅ Test with curl/Postman (easy)

**Time to first working prototype:** ~1-2 hours
**Time to production-ready:** ~1-2 days (error handling complexity)

---

#### **Asynchronous Development**

1. ⚠️ Define event schema (Pydantic model)
2. ⚠️ Set up RabbitMQ connection
3. ✅ Write publisher endpoint
4. ⚠️ Write consumer function
5. ⚠️ Start consumer as background task
6. ✅ Add compensation as another event handler
7. ❌ Test with RabbitMQ UI + logs (more complex)

**Time to first working prototype:** ~3-4 hours (learning curve)
**Time to production-ready:** ~1 day (simpler once pattern is established)

---

### Code Metrics Comparison

| Metric | Synchronous | Asynchronous | Winner |
|--------|-------------|--------------|--------|
| **Lines of Code (per service)** | ~150 | ~200 | Sync (less code) |
| **Complexity (Cyclomatic)** | Higher (nested try-catch) | Lower (simple event handlers) | **Async** |
| **Coupling** | High (knows other service URLs) | Low (only knows queue names) | **Async** |
| **Testability** | Medium (need to mock HTTP) | High (test event handlers separately) | **Async** |
| **Boilerplate** | Lower | Higher (event schemas, consumers) | Sync |

---

### When to Choose Which?

| Use Case | Recommendation | Reason |
|----------|----------------|--------|
| **Prototype/MVP** | **Synchronous** | Faster to build, easier to understand |
| **High-scale production** | **Asynchronous** | Better performance, scalability |
| **Simple CRUD app** | **Synchronous** | Overhead not worth it |
| **Long-running processes** | **Asynchronous** | Don't block HTTP threads |
| **Event-driven domain** | **Asynchronous** | Natural fit (orders, notifications) |
| **Strict consistency needed** | **Synchronous** | Immediate consistency |
| **Team new to async** | **Synchronous** | Lower learning curve |
| **Microservices at scale** | **Asynchronous** | Decoupling is critical |

---

## Scenarios

### Scenario 1: Non-Critical Task Decoupling
**Endpoint:** `POST http://localhost:8101/register`

Demonstrates fire-and-forget pattern for non-critical operations.

**Flow:**
1. Client registers a user
2. UserService saves to database
3. UserService publishes `UserRegistered` event to RabbitMQ
4. **Returns 202 Accepted immediately** ⚡
5. EmailService consumer picks up event and sends email (500ms delay in background)

**Key Difference from Sync:**
- **Sync:** Client waits >500ms
- **Async:** Client gets response in <100ms

**Example:**
```bash
curl -X POST http://localhost:8101/register \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com"}'

# Response: 202 Accepted (instant!)
{
  "id": 123,
  "email": "user@example.com",
  "message": "User registered successfully. Welcome email will be sent shortly.",
  "event_published": true
}
```

---

### Scenario 2: Long-Running Process (Background Processing)
**Endpoint:** `POST http://localhost:8102/process_payment`

Demonstrates offloading long-running tasks to background workers.

**Flow:**
1. Client requests payment processing
2. PaymentService publishes `PaymentInitiated` event to internal queue
3. **Returns 202 Accepted with job ID** ⚡
4. Background worker picks up event and processes payment (2s delay)
5. Worker publishes `PaymentCompleted` event when done

**Key Difference from Sync:**
- **Sync:** Client blocks for 2+ seconds
- **Async:** Client gets job ID in <100ms

**Example:**
```bash
curl -X POST http://localhost:8102/process_payment \
  -H "Content-Type: application/json" \
  -d '{"amount": 100.0, "currency": "USD"}'

# Response: 202 Accepted (instant!)
{
  "payment_id": "pay_abc123",
  "status": "processing",
  "message": "Payment initiated successfully. Processing asynchronously."
}
```

---

### Scenario 3: Fan-Out Flow (Pub/Sub Pattern)
**Endpoint:** `PUT http://localhost:8103/products/{product_id}`

Demonstrates parallel processing of the same event by multiple consumers.

**Flow:**
1. Client updates a product
2. ProductService updates database
3. ProductService publishes `ProductUpdated` event to **Fanout Exchange**
4. **Returns 200 OK immediately** ⚡
5. Three consumers receive event **simultaneously**:
   - SearchService reindexes
   - CacheService invalidates cache
   - AnalyticsService logs update

**Key Difference from Sync:**
- **Sync:** 3 sequential HTTP calls (total time = sum of all)
- **Async:** 1 fanout event → 3 parallel consumers (total time = slowest consumer)

**Example:**
```bash
curl -X PUT http://localhost:8103/products/1 \
  -H "Content-Type: application/json" \
  -d '{"name": "Updated Laptop", "stock": 75}'

# Response: 200 OK (instant!)
{
  "id": 1,
  "name": "Updated Laptop",
  "stock": 75,
  "event_published": true
}
```

**Check RabbitMQ:**
```bash
# Open RabbitMQ Management UI
http://localhost:15672

# See 3 queues bound to product_updates fanout exchange:
- search_product_updates_queue
- cache_product_updates_queue
- analytics_product_updates_queue
```

---

### Scenario 4: CPU-Intensive Task (Job Offloading)
**Endpoint:** `POST http://localhost:8104/generate_report`

Demonstrates offloading CPU-bound work to dedicated workers.

**Flow:**
1. Client requests report generation
2. ReportService publishes `GenerateReportJob` event to queue
3. **Returns 202 Accepted with job ID** ⚡
4. Background worker picks up job and performs 10 seconds of SHA-256 hashing
5. Worker logs completion (or publishes `ReportGenerated` event)

**Key Difference from Sync:**
- **Sync:** Client connection blocks for 10+ seconds (may timeout)
- **Async:** Client gets job ID in <100ms, can poll for status

**Example:**
```bash
curl -X POST http://localhost:8104/generate_report \
  -H "Content-Type: application/json" \
  -d '{"report_type": "monthly"}'

# Response: 202 Accepted (instant!)
{
  "job_id": "job_xyz789",
  "status": "queued",
  "message": "Report generation job queued. Processing in background."
}

# Poll for status (optional)
curl http://localhost:8104/jobs/job_xyz789
```

---

### Scenario 5: Saga Pattern (Event-Driven Choreography)
**Endpoint:** `POST http://localhost:8105/create_order`

Demonstrates distributed transaction coordination via events.

**Flow (Choreography - No Central Orchestrator):**
1. Client creates order
2. OrderService creates order (status: "pending"), publishes `OrderCreated`, **returns 202** ⚡
3. InventoryService consumes `OrderCreated` → reserves stock → publishes `StockReserved`
4. PaymentService consumes `StockReserved` → attempts payment → **fails** → publishes `PaymentFailed`
5. **Compensation (Choreography):**
   - InventoryService consumes `PaymentFailed` → releases stock
   - OrderService consumes `PaymentFailed` → updates order status to "failed"

**Key Difference from Sync:**
- **Sync:** Orchestrator calls services sequentially, manual try-catch compensation
- **Async:** Services react to events autonomously, event-driven compensation

**Example:**
```bash
curl -X POST http://localhost:8105/create_order \
  -H "Content-Type: application/json" \
  -d '{"product_id": 1, "quantity": 1}'

# Response: 202 Accepted (instant!)
{
  "id": 456,
  "product_id": 1,
  "quantity": 1,
  "status": "pending"
}

# Poll order status after 2 seconds
sleep 2
curl http://localhost:8105/orders/456

# Response: Saga completed with compensation
{
  "id": 456,
  "product_id": 1,
  "quantity": 1,
  "status": "failed"  # ← Saga failed, compensation executed
}
```

**Event Flow in RabbitMQ:**
```
order_created_queue → stock_reserved_queue → payment_failed_queue
                                                  ↓             ↓
                                          InventoryService  OrderService
                                          (compensate)      (update status)
```

---

### Scenario 6: High-Throughput Data Ingestion (Buffering)
**Endpoint:** `POST http://localhost:8106/track_click`

Demonstrates RabbitMQ acting as a buffer for high-volume events.

**Flow:**
1. Client sends click tracking event
2. AnalyticsService publishes to `click_tracked_queue`
3. **Returns 200 OK immediately** ⚡ (<50ms)
4. Background consumer processes clicks from queue

**Key Difference from Sync:**
- **Sync:** Under high load (100+ req/s), connection pool exhausted, errors occur
- **Async:** RabbitMQ buffers all requests, never rejects (queue grows if consumer slow)

**Example:**
```bash
# Single request
curl -X POST http://localhost:8106/track_click \
  -H "Content-Type: application/json" \
  -d '{"user_id": 123, "page": "homepage"}'

# Response: 200 OK (instant!)
{"status": "tracked"}

# High-throughput test (100 req/s)
k6 run k6-tests/script-async.js
# Scenario 6 should show P95 latency < 50ms even at 100 req/s!
```

**Monitor Queue:**
```bash
# Check queue depth in RabbitMQ UI
http://localhost:15672/#/queues
# click_tracked_queue should show message rate and consumer processing
```

---

## Getting Started

### Prerequisites

- Docker & Docker Compose
- k6 (for load testing): `brew install k6` or see [k6.io/docs](https://k6.io/docs/getting-started/installation/)

### Running the Application

1. **Navigate to async directory**
   ```bash
   cd asynchronous
   ```

2. **Start all services (including RabbitMQ)**
   ```bash
   docker compose -f docker-compose-async.yml up --build
   ```

3. **Wait for services to be healthy**

   Check all services including RabbitMQ:
   ```bash
   # Microservices
   curl http://localhost:8101/health  # UserService
   curl http://localhost:8102/health  # PaymentService
   curl http://localhost:8103/health  # ProductService

   # RabbitMQ
   curl -u guest:guest http://localhost:15672/api/overview
   ```

4. **Access RabbitMQ Management UI**
   ```
   http://localhost:15672
   Username: guest
   Password: guest
   ```

   You should see:
   - **Connections:** 10+ (one per service)
   - **Queues:** 8+ queues created automatically
   - **Exchanges:** Includes `product_updates` fanout exchange

5. **View logs**
   ```bash
   # All services
   docker compose -f docker-compose-async.yml logs -f

   # Specific service
   docker compose logs -f userservice

   # RabbitMQ logs
   docker compose logs -f rabbitmq
   ```

6. **Stop all services**
   ```bash
   docker compose -f docker-compose-async.yml down
   ```

### Running k6 Tests

The async k6 test script mirrors the sync version for direct comparison.

**Run tests:**
```bash
k6 run --env BASE_URL=http://localhost --out json=results-async.json k6-tests/script-async.js
```

**Expected Results:**
- ✅ P95 latency < 100ms for all scenarios (except Scenario 6: <50ms)
- ✅ High throughput (500+ req/s)
- ✅ Zero errors (RabbitMQ buffers everything)
- ✅ Scenario 5: Orders created with status "pending", saga completes in background

### Comparing Async vs Sync

**Terminal 1 - Start Sync:**
```bash
cd synchronous
docker compose -f docker-compose-sync.yml up -d
```

**Terminal 2 - Start Async:**
```bash
cd asynchronous
docker compose -f docker-compose-async.yml up -d
```

**Terminal 3 - Run Tests:**
```bash
# Sync
cd synchronous
k6 run --env BASE_URL=http://localhost --out json=results-sync.json k6-tests/script-sync.js

# Async
cd ../asynchronous
k6 run --env BASE_URL=http://localhost --out json=results-async.json k6-tests/script-async.js
```

**Compare Results:**
```bash
# Response times
cat results-sync.json | jq '.metrics.http_req_duration'
cat results-async.json | jq '.metrics.http_req_duration'

# Throughput
cat results-sync.json | jq '.metrics.http_reqs'
cat results-async.json | jq '.metrics.http_reqs'
```

**Open Grafana Dashboards Side-by-Side:**
- Sync: http://localhost:3000
- Async: http://localhost:3001

---

## Monitoring Stack

See [MONITORING_SETUP.md](MONITORING_SETUP.md) for complete monitoring guide.

### Quick Access

| Service | URL | Credentials |
|---------|-----|-------------|
| **Grafana** | http://localhost:3001 | admin / admin |
| **Prometheus** | http://localhost:9091 | None |
| **RabbitMQ Management** | http://localhost:15672 | guest / guest |
| **cAdvisor** | http://localhost:8081 | None |

### Key Metrics to Monitor

**Application Metrics (Prometheus):**
- `http_request_duration_seconds` - Response times (should be <100ms!)
- `http_requests_total` - Request rates per service

**RabbitMQ Metrics:**
- Queue depth (messages waiting)
- Message publish/consume rates
- Consumer counts

**Container Metrics (cAdvisor):**
- CPU usage (should be lower than sync)
- Memory usage
- Network traffic

---

## API Documentation

Each service exposes interactive API documentation:

- UserService: http://localhost:8101/docs
- PaymentService: http://localhost:8102/docs
- ProductService: http://localhost:8103/docs
- ReportService: http://localhost:8104/docs
- OrderService: http://localhost:8105/docs
- AnalyticsService: http://localhost:8106/docs

---

## Project Structure

```
asynchronous/
├── common/                          # Shared utilities
│   ├── rabbitmq_client.py          # RabbitMQ connection manager
│   ├── event_schemas.py            # Pydantic event models
│   ├── base_consumer.py            # Base consumer classes
│   ├── database.py                 # Async database utilities
│   └── requirements.txt
├── userservice/
│   ├── main.py                     # FastAPI app + event publisher
│   ├── Dockerfile
│   └── requirements.txt
├── emailservice/
│   ├── main.py                     # Consumer only (no HTTP endpoints)
│   ├── Dockerfile
│   └── requirements.txt
├── paymentservice/
│   ├── main.py                     # Publisher + consumer
│   ├── Dockerfile
│   └── requirements.txt
├── productservice/
│   ├── main.py                     # Fanout publisher
│   ├── Dockerfile
│   └── requirements.txt
├── searchservice/
│   ├── main.py                     # Fanout consumer
│   ├── Dockerfile
│   └── requirements.txt
├── cacheservice/
│   ├── main.py                     # Fanout consumer
│   ├── Dockerfile
│   └── requirements.txt
├── analyticsservice/
│   ├── main.py                     # Fanout consumer + publisher
│   ├── Dockerfile
│   └── requirements.txt
├── reportservice/
│   ├── main.py                     # Publisher + worker consumer
│   ├── Dockerfile
│   └── requirements.txt
├── orderservice/
│   ├── main.py                     # Saga orchestrator
│   ├── Dockerfile
│   └── requirements.txt
├── inventoryservice/
│   ├── main.py                     # Saga participant
│   ├── Dockerfile
│   └── requirements.txt
├── k6-tests/
│   └── script-async.js             # Load tests (mirrored from sync)
├── prometheus/
│   └── prometheus.yml              # Includes RabbitMQ scraping
├── grafana/
│   └── provisioning/
│       ├── datasources/
│       │   └── datasource.yml
│       └── dashboards/
│           ├── dashboard.yml
│           └── microservices-dashboard.json
├── docker-compose-async.yml         # Full stack orchestration
├── MONITORING_SETUP.md              # Monitoring guide
└── README.md                        # This file
```

---

## Troubleshooting

### RabbitMQ Connection Issues

**Symptoms:**
- Services showing "Connection refused" errors
- No queues in RabbitMQ UI

**Solutions:**
```bash
# Check RabbitMQ health
docker compose ps rabbitmq

# View RabbitMQ logs
docker compose logs rabbitmq

# Restart RabbitMQ
docker compose restart rabbitmq

# Verify RabbitMQ is ready
curl -u guest:guest http://localhost:15672/api/overview
```

### Messages Not Being Consumed

**Symptoms:**
- Queue depth growing continuously
- Consumers = 0 in RabbitMQ UI

**Solutions:**
```bash
# Check consumer service logs
docker compose logs <service-name>

# Restart consumer service
docker compose restart <service-name>

# Verify consumer started
# Check RabbitMQ UI → Queues → "Consumers" column should be > 0
```

### High Queue Depth

**Symptoms:**
- Queues have thousands of messages
- Processing lag increasing

**Solutions:**
```bash
# Check consumer processing time
docker compose logs <consumer-service>

# Increase consumers (scale horizontally)
docker compose up -d --scale emailservice=3

# Monitor consumer lag in Grafana
# Queue depth / message rate = lag time
```

### Database Connection Errors

```bash
# Ensure PostgreSQL is healthy
docker compose ps postgres

# Check PostgreSQL logs
docker compose logs postgres

# Restart database-dependent services
docker compose restart userservice productservice orderservice inventoryservice
```

### k6 Tests Failing

```bash
# Ensure all services are up
docker compose ps

# Check service health
curl http://localhost:8101/health

# Check RabbitMQ connectivity
curl -u guest:guest http://localhost:15672/api/queues

# Run with verbose logging
k6 run --verbose k6-tests/script-async.js
```

### Debugging Event Flow

**Trace events through the system:**

1. **Check if event was published:**
   - View publisher service logs
   - Check RabbitMQ queue in UI (Messages → Get Messages)

2. **Check if consumer received event:**
   - View consumer service logs
   - Check message acknowledgment in RabbitMQ

3. **Check for errors:**
   - Consumer logs will show processing errors
   - RabbitMQ "Nacked" messages indicate failures

**Useful commands:**
```bash
# View all messages in a queue (debugging)
curl -u guest:guest http://localhost:15672/api/queues/%2F/user_registered_queue/get \
  -X POST -d '{"count":10,"ackmode":"ack_requeue_false","encoding":"auto"}'

# Check exchange bindings
curl -u guest:guest http://localhost:15672/api/exchanges/%2F/product_updates/bindings/source
```

---

## Summary: Async vs Sync

| Aspect | Winner | Summary |
|--------|--------|---------|
| **Response Time** | 🏆 **Async** | 10-100x faster (immediate response) |
| **Throughput** | 🏆 **Async** | 10x higher (non-blocking) |
| **Resource Efficiency** | 🏆 **Async** | Better CPU/memory utilization |
| **Scalability** | 🏆 **Async** | Horizontal scaling, buffering |
| **Simplicity** | 🏆 **Sync** | Easier to understand and debug |
| **Development Speed** | 🏆 **Sync** | Faster initial development |
| **Operational Complexity** | 🏆 **Sync** | Fewer moving parts |
| **Long-term Maintainability** | 🏆 **Async** | Cleaner event handlers |

**Recommendation:**
- **Use Async** for production systems at scale with high traffic
- **Use Sync** for prototypes, MVPs, or simple applications with low traffic

---

## Detailed Queue Communication Per Scenario

This section explains how RabbitMQ queues and exchanges are used in each scenario.

### Scenario 1: Non-Critical Task Decoupling (Fire-and-Forget)

**Pattern:** Direct Queue with Single Consumer

```
┌─────────────┐     HTTP POST      ┌─────────────┐
│   Client    │ ─────────────────► │ UserService │
└─────────────┘                    └──────┬──────┘
                                          │
                                          │ 1. Save user to DB
                                          │ 2. Publish event
                                          │ 3. Return 202 Accepted
                                          ▼
                              ┌───────────────────────┐
                              │ user_registered_queue │  (Direct Queue)
                              └───────────┬───────────┘
                                          │
                                          │ Consumer pulls message
                                          ▼
                                   ┌─────────────┐
                                   │EmailService │
                                   │ (Consumer)  │
                                   └─────────────┘
                                          │
                                          ▼
                                   📧 Send Email
```

**Queue Details:**
| Component | Name | Type | Durable |
|-----------|------|------|---------|
| Queue | `user_registered_queue` | Direct | Yes |
| Exchange | Default (`""`) | Direct | - |

**Message Flow:**
1. **UserService** receives HTTP request, saves user to PostgreSQL
2. **UserService** publishes `UserRegisteredEvent` to `user_registered_queue`
3. **UserService** returns `202 Accepted` immediately (non-blocking)
4. **EmailService** consumer picks up message from queue
5. **EmailService** simulates sending email (500ms delay)
6. **EmailService** acknowledges message (removes from queue)

**Why This Pattern?**
- Email sending is non-critical (user doesn't need to wait)
- Decouples user registration from email delivery
- If EmailService is down, messages queue up and are processed later

---

### Scenario 2: Long-Running Process (Background Processing)

**Pattern:** Internal Queue for Background Workers

```
┌─────────────┐     HTTP POST      ┌────────────────┐
│   Client    │ ─────────────────► │ PaymentService │
└─────────────┘                    │   (API + Worker)│
       ▲                           └────────┬───────┘
       │                                    │
       │ 202 Accepted                       │ 1. Generate payment_id
       │ (instant!)                         │ 2. Publish to internal queue
       │                                    │ 3. Return 202 immediately
       │                                    ▼
       │                        ┌─────────────────────────┐
       │                        │ payment_initiated_queue │
       │                        └────────────┬────────────┘
       │                                     │
       │                                     │ Background worker
       │                                     ▼
       │                              ┌─────────────┐
       │                              │   Worker    │
       │                              │ (same svc)  │
       │                              └──────┬──────┘
       │                                     │
       │                                     │ Process payment (2s)
       │                                     ▼
       │                        ┌─────────────────────────┐
       │                        │ payment_completed_queue │
       └────────────────────────└─────────────────────────┘
```

**Queue Details:**
| Component | Name | Type | Purpose |
|-----------|------|------|---------|
| Queue | `payment_initiated_queue` | Direct | Incoming payment jobs |
| Queue | `payment_completed_queue` | Direct | Completed payment notifications |

**Message Flow:**
1. **Client** sends payment request
2. **PaymentService API** generates `payment_id`, publishes `PaymentInitiatedEvent`
3. **PaymentService API** returns `202 Accepted` with `payment_id` (instant)
4. **PaymentService Worker** (background consumer) picks up job
5. **Worker** simulates payment gateway call (2 second delay)
6. **Worker** publishes `PaymentCompletedEvent` when done

**Why This Pattern?**
- External payment gateways are slow (2-10 seconds)
- Client shouldn't wait for external services
- Job can be retried if it fails
- Can scale workers independently

---

### Scenario 3: Fan-Out Flow (Pub/Sub Pattern)

**Pattern:** Fanout Exchange with Multiple Bound Queues

```
┌─────────────┐     HTTP PUT       ┌────────────────┐
│   Client    │ ─────────────────► │ ProductService │
└─────────────┘                    └────────┬───────┘
                                            │
                                            │ 1. Update product in DB
                                            │ 2. Publish to fanout exchange
                                            │ 3. Return 200 OK
                                            ▼
                              ┌─────────────────────────┐
                              │   product_updates       │  ◄── FANOUT EXCHANGE
                              │   (fanout exchange)     │
                              └────────────┬────────────┘
                                           │
                    ┌──────────────────────┼──────────────────────┐
                    │                      │                      │
                    ▼                      ▼                      ▼
    ┌───────────────────────┐ ┌───────────────────────┐ ┌───────────────────────┐
    │search_product_updates │ │cache_product_updates  │ │analytics_product_     │
    │       _queue          │ │       _queue          │ │    updates_queue      │
    └───────────┬───────────┘ └───────────┬───────────┘ └───────────┬───────────┘
                │                         │                         │
                ▼                         ▼                         ▼
         ┌─────────────┐           ┌─────────────┐           ┌─────────────┐
         │SearchService│           │CacheService │           │Analytics    │
         │ (Consumer)  │           │ (Consumer)  │           │Service      │
         └─────────────┘           └─────────────┘           └─────────────┘
                │                         │                         │
                ▼                         ▼                         ▼
         🔍 Reindex              🗑️ Invalidate             📊 Log Update
            Search                   Cache                   Analytics
```

**Queue Details:**
| Component | Name | Type | Bound To |
|-----------|------|------|----------|
| Exchange | `product_updates` | **Fanout** | - |
| Queue | `search_product_updates_queue` | Direct | `product_updates` |
| Queue | `cache_product_updates_queue` | Direct | `product_updates` |
| Queue | `analytics_product_updates_queue` | Direct | `product_updates` |

**Message Flow:**
1. **Client** sends product update request
2. **ProductService** updates product in PostgreSQL
3. **ProductService** publishes `ProductUpdatedEvent` to `product_updates` **fanout exchange**
4. **RabbitMQ** copies the message to ALL bound queues simultaneously
5. **Three consumers** receive the same event in parallel:
   - **SearchService**: Reindexes product in search
   - **CacheService**: Invalidates cached product data
   - **AnalyticsService**: Logs product update for analytics

**Why Fanout Exchange?**
- One event needs to trigger multiple independent actions
- Consumers don't need to know about each other
- Adding a new consumer = just bind a new queue (no code changes to publisher)
- All consumers process in **parallel** (vs sequential in sync)

**Key Difference from Direct Queue:**
- **Direct Queue:** One message → one consumer (round-robin if multiple consumers)
- **Fanout Exchange:** One message → ALL bound queues (broadcast)

---

### Scenario 4: CPU-Intensive Task (Job Offloading)

**Pattern:** Job Queue with Dedicated Workers

```
┌─────────────┐     HTTP POST      ┌────────────────┐
│   Client    │ ─────────────────► │ ReportService  │
└─────────────┘                    │     (API)      │
       ▲                           └────────┬───────┘
       │                                    │
       │ 202 Accepted                       │ 1. Generate job_id
       │ + job_id                           │ 2. Publish job to queue
       │ (instant!)                         │ 3. Return 202 immediately
       │                                    ▼
       │                        ┌─────────────────────────┐
       │                        │    report_jobs_queue    │
       │                        └────────────┬────────────┘
       │                                     │
       │                                     │ Worker picks up job
       │                                     ▼
       │                              ┌─────────────────┐
       │                              │  Report Worker  │
       │                              │  (ThreadPool)   │
       │                              └────────┬────────┘
       │                                       │
       │                                       │ CPU work (10s SHA-256)
       │                                       │ in separate thread
       │                                       ▼
       │                                  📄 Report
       │                                    Generated
       └───────────────────────────────────────┘
                    (poll /jobs/{job_id} for status)
```

**Queue Details:**
| Component | Name | Type | Purpose |
|-----------|------|------|---------|
| Queue | `report_jobs_queue` | Direct | Pending report generation jobs |

**Message Flow:**
1. **Client** requests report generation
2. **ReportService API** generates `job_id`, publishes `GenerateReportJobEvent`
3. **ReportService API** returns `202 Accepted` with `job_id` (instant)
4. **ReportService Worker** picks up job from queue
5. **Worker** offloads CPU-intensive work to ThreadPool (10 seconds of hashing)
6. **Worker** logs completion (could also publish `ReportGeneratedEvent`)

**Why This Pattern?**
- CPU-intensive work would block HTTP thread
- Client connection would timeout (>30s work)
- Can scale workers on high-CPU machines
- Queue acts as job scheduler

---

### Scenario 5: Saga Pattern (Event-Driven Choreography)

**Pattern:** Multiple Queues with Fanout for Compensation Events

```
┌─────────────┐   HTTP POST    ┌────────────────┐
│   Client    │ ─────────────► │  OrderService  │
└─────────────┘                └───────┬────────┘
       ▲                               │
       │ 202 Accepted                  │ 1. Create order (status: pending)
       │ (instant!)                    │ 2. Publish OrderCreated
       │                               ▼
       │                   ┌────────────────────────┐
       │                   │  order_created_queue   │
       │                   └───────────┬────────────┘
       │                               │
       │                               ▼
       │                      ┌─────────────────┐
       │                      │InventoryService │
       │                      │   (Consumer)    │
       │                      └────────┬────────┘
       │                               │
       │                               │ Reserve stock
       │                               │ Publish StockReserved
       │                               ▼
       │                   ┌────────────────────────┐
       │                   │ stock_reserved_queue   │
       │                   └───────────┬────────────┘
       │                               │
       │                               ▼
       │                      ┌─────────────────┐
       │                      │ PaymentService  │
       │                      │   (Consumer)    │
       │                      └────────┬────────┘
       │                               │
       │                               │ Process payment → FAILS!
       │                               │ Publish PaymentFailed
       │                               ▼
       │                   ┌────────────────────────┐
       │                   │    payment_failed      │  ◄── FANOUT EXCHANGE
       │                   │   (fanout exchange)    │
       │                   └───────────┬────────────┘
       │                               │
       │              ┌────────────────┴────────────────┐
       │              │                                 │
       │              ▼                                 ▼
       │  ┌─────────────────────────┐    ┌─────────────────────────┐
       │  │inventory_payment_failed │    │ order_payment_failed    │
       │  │        _queue           │    │        _queue           │
       │  └───────────┬─────────────┘    └───────────┬─────────────┘
       │              │                               │
       │              ▼                               ▼
       │     ┌─────────────────┐             ┌─────────────────┐
       │     │InventoryService │             │  OrderService   │
       │     │  (Compensation) │             │  (Compensation) │
       │     └────────┬────────┘             └────────┬────────┘
       │              │                               │
       │              ▼                               ▼
       │        Release Stock                  Update Order
       │        (Compensate)                  status → "failed"
       │                                              │
       └──────────────────────────────────────────────┘
                   (poll /orders/{id} shows "failed")
```

**Queue Details:**
| Component | Name | Type | Purpose |
|-----------|------|------|---------|
| Queue | `order_created_queue` | Direct | Trigger inventory reservation |
| Queue | `stock_reserved_queue` | Direct | Trigger payment processing |
| Exchange | `payment_failed` | **Fanout** | Broadcast failure to all participants |
| Queue | `inventory_payment_failed_queue` | Direct | InventoryService compensation |
| Queue | `order_payment_failed_queue` | Direct | OrderService compensation |

**Message Flow (Happy Path would skip steps 5-7):**
1. **OrderService** creates order with `status: pending`, publishes `OrderCreatedEvent`
2. **InventoryService** reserves stock, publishes `StockReservedEvent`
3. **PaymentService** attempts payment → **FAILS** (simulated)
4. **PaymentService** publishes `PaymentFailedEvent` to `payment_failed` **fanout exchange**
5. **RabbitMQ** broadcasts to both bound queues
6. **InventoryService** receives event → releases reserved stock (compensation)
7. **OrderService** receives event → updates order `status: failed` (compensation)

**Why Fanout for PaymentFailed?**
- Multiple services need to react to failure
- Both InventoryService AND OrderService must compensate
- Without fanout, only ONE service would receive the message (round-robin)

**Saga Choreography vs Orchestration:**
- **Choreography (this implementation):** Services react to events autonomously
- **Orchestration:** Central coordinator tells each service what to do
- Choreography is more decoupled but harder to trace

---

### Scenario 6: High-Throughput Data Ingestion (Buffering)

**Pattern:** Queue as Buffer for Burst Traffic

```
┌─────────────┐                      ┌─────────────────┐
│   Client    │ ──── 100 req/s ────► │AnalyticsService │
│  (k6 load)  │                      │     (API)       │
└─────────────┘                      └────────┬────────┘
       ▲                                      │
       │ 200 OK                               │ 1. Publish click event
       │ (< 50ms!)                            │ 2. Return 200 OK instantly
       │                                      ▼
       │                          ┌────────────────────────┐
       │                          │  click_tracked_queue   │
       │                          │                        │
       │                          │  [msg][msg][msg][msg]  │  ◄── Queue buffers
       │                          │  [msg][msg][msg][msg]  │      burst traffic
       │                          │  [msg][msg][msg]       │
       │                          └───────────┬────────────┘
       │                                      │
       │                                      │ Consumer processes
       │                                      │ at its own pace
       │                                      ▼
       │                             ┌─────────────────┐
       │                             │AnalyticsWorker  │
       │                             │   (Consumer)    │
       │                             └────────┬────────┘
       │                                      │
       │                                      ▼
       │                               📊 Process
       │                                 Analytics
       └──────────────────────────────────────┘
```

**Queue Details:**
| Component | Name | Type | Purpose |
|-----------|------|------|---------|
| Queue | `click_tracked_queue` | Direct | Buffer for high-volume click events |

**Message Flow:**
1. **Load test** sends 100 requests/second
2. **AnalyticsService API** publishes each click to queue immediately
3. **API** returns `200 OK` in <50ms (non-blocking)
4. **Queue** buffers all messages (can grow to thousands)
5. **Consumer** processes messages at sustainable rate
6. Queue drains over time after burst ends

**Why This Pattern?**
- Click tracking is high-volume, low-priority
- Don't want to reject requests during traffic spikes
- Queue acts as shock absorber
- Consumer can process at constant rate (no overload)

**Buffer Behavior:**
```
Traffic Spike:  ████████████████  (100 req/s)
Queue Depth:    ▁▂▃▅▆▇██████▇▆▅▃▂▁  (grows then drains)
Consumer Rate:  ████████████████████  (constant 50/s)
```

---

### Queue Summary Table

| Scenario | Queue(s) | Exchange | Pattern | Key Benefit |
|----------|----------|----------|---------|-------------|
| **1** | `user_registered_queue` | Default (direct) | Fire-and-Forget | Decouple non-critical tasks |
| **2** | `payment_initiated_queue`, `payment_completed_queue` | Default (direct) | Background Worker | Offload slow external calls |
| **3** | 3 queues bound to `product_updates` | **Fanout** | Pub/Sub | Parallel multi-consumer |
| **4** | `report_jobs_queue` | Default (direct) | Job Queue | Offload CPU-intensive work |
| **5** | `order_created_queue`, `stock_reserved_queue`, 2 queues bound to `payment_failed` | Direct + **Fanout** | Saga Choreography | Distributed transactions |
| **6** | `click_tracked_queue` | Default (direct) | Buffer | Handle traffic spikes |

---

## Authors

- Profeanu Ioana
- Ciobanu
- Girlea
- Dumitrescu

---

## References

- FastAPI Async Documentation: https://fastapi.tiangolo.com/async/
- RabbitMQ Documentation: https://www.rabbitmq.com/documentation.html
- aio_pika Documentation: https://aio-pika.readthedocs.io/
- Docker Compose: https://docs.docker.com/compose/
- k6 Load Testing: https://k6.io/docs/
- Event-Driven Architecture: https://martinfowler.com/articles/201701-event-driven.html
