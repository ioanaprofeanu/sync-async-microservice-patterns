### 🤖 AI Programming Prompt: Milestone 3

**Project Title:** Asynchronous Architecture Implementation (Milestone 3)

**Objective:** You are a senior software engineer. Your task is to generate the complete code for **Milestone 3** of the comparative study project. This milestone focuses on refactoring the previous synchronous microservices into a fully **Asynchronous (Event-Driven) Architecture** using **RabbitMQ**.

You must generate the code for all microservices, the Docker configuration (including RabbitMQ), and the updated test scripts.

-----

### 1\. Global Tech Constraints (Mandatory)

  * **Language:** Python 3.10+
  * **Framework:** FastAPI
  * **Message Broker:** **RabbitMQ** (Management Plugin enabled).
  * **RabbitMQ Client:** Use `aio_pika` (recommended for asyncio/FastAPI) or `pika`. Ensure robust connection handling (reconnection logic).
  * **Database:** PostgreSQL (same schemas as Milestone 2).
  * **Communication Model:** **Event-Driven / Fire-and-Forget**.
      * HTTP is used *only* for the Client-to-Service entry point.
      * Service-to-Service communication must be done exclusively via **RabbitMQ Messages/Events**.
  * **Orchestration:** Docker, with a single `docker-compose-async.yml` file.

-----

### 2\. Infrastructure & Setup

**1. Docker Compose (`docker-compose-async.yml`):**

  * Includes all microservices from Milestone 2.
  * **Add `rabbitmq` service:**
      * Image: `rabbitmq:3-management`
      * Ports: `5672` (messaging), `15672` (UI).
      * Healthcheck enabled.
  * Ensure all services wait for RabbitMQ to be healthy before starting.

**2. Service Template (Async):**

  * **API Layer (`main.py`):** Accepts HTTP requests, publishes an event to RabbitMQ, and **immediately returns** an HTTP 202 Accepted (or 200 OK) response. It should *not* wait for the background process to finish.
  * **Consumer Layer:** A background listener (e.g., using `asyncio.create_task` on startup or a separate worker thread) that subscribes to relevant RabbitMQ queues and processes messages.

-----

### 3\. Scenario Implementation (Event-Driven)

Refactor all 6 scenarios to use asynchronous communication.

#### Scenario 1: Decoupling Non-Critical Tasks

  * **Services:** `UserService`, `EmailService`.
  * **Flow:**
    1.  **Client** calls `POST /register` on `UserService`.
    2.  `UserService` saves the user to DB (Pending/Active).
    3.  `UserService` publishes a `UserRegistered` event to RabbitMQ.
    4.  `UserService` **immediately returns** 200/201 to the client (fast response).
    5.  **Background:** `EmailService` consumes `UserRegistered`. It executes the **500ms sleep** (`time.sleep(0.5)`) to simulate sending.

#### Scenario 2: Long-Running Process (Async Handoff)

  * **Services:** `PaymentService`.
  * **Flow:**
    1.  **Client** calls `POST /process_payment` on `PaymentService`.
    2.  `PaymentService` publishes a `PaymentInitiated` event to an internal queue.
    3.  `PaymentService` **immediately returns** 202 Accepted.
    4.  **Background:** A consumer within `PaymentService` picks up the message, **sleeps for 2 seconds**, and then logs the completion.

#### Scenario 3: Fan-Out (Pub/Sub)

  * **Services:** `ProductService` (Publisher), `SearchService`, `CacheService`, `AnalyticsService` (Subscribers).
  * **Flow:**
    1.  **Client** calls `PUT /products/{id}` on `ProductService`.
    2.  `ProductService` updates the DB.
    3.  `ProductService` publishes a single `ProductUpdated` event to a **RabbitMQ Fanout Exchange**.
    4.  `ProductService` **immediately returns** 200 OK.
    5.  **Background:** `SearchService`, `CacheService`, and `AnalyticsService` all have their own queues bound to this exchange. They consume the message in parallel and perform their tasks (logging/mocking).

#### Scenario 4: CPU-Intensive Task (Offloading)

  * **Services:** `ReportService`.
  * **Flow:**
    1.  **Client** calls `POST /generate_report`.
    2.  `ReportService` publishes `GenerateReportJob` to a queue.
    3.  `ReportService` **immediately returns** 202 Accepted (with a Job ID).
    4.  **Background:** A worker (inside `ReportService` container or separate) consumes the message and runs the **10-second SHA-256 hashing loop**.

#### Scenario 5: Choreography Saga (Event-Based Compensation)

  * **Pattern:** Choreography (Services react to events, no central orchestrator).
  * **Services:** `OrderService`, `InventoryService`, `PaymentService`.
  * **Flow (Failure Scenario):**
    1.  **Client** calls `POST /create_order`.
    2.  `OrderService` creates Order (status="Pending"), publishes `OrderCreated`, returns 202.
    3.  **InventoryService** consumes `OrderCreated` -\> Reserves Stock -\> Publishes `StockReserved`.
    4.  **PaymentService** consumes `StockReserved`.
          * *Logic:* Attempt payment. For this scenario, **simulate failure**.
          * Action: Publish `PaymentFailed` event.
    5.  **InventoryService** consumes `PaymentFailed` -\> **Compensates** (Releases Stock).
    6.  **OrderService** consumes `PaymentFailed` -\> Updates Order status to "Failed".

#### Scenario 6: High-Throughput Buffering

  * **Services:** `AnalyticsService`.
  * **Flow:**
    1.  **Client** sends high-volume `POST /track_click`.
    2.  `AnalyticsService` publishes message to RabbitMQ.
    3.  `AnalyticsService` **immediately returns** 200 OK.
    4.  **Goal:** This demonstrates RabbitMQ acting as a **buffer**. The HTTP layer should handle thousands of requests per second because it's only pushing to the queue, not processing.

-----

### 4\. k6 Test Script Updates (`script-async.js`)

Create a new `script-async.js`. The logic must change because responses are now immediate.

1.  **Expectations:** Assert that response times are **very low** (\< 100ms) for all scenarios (S1, S2, S3, S4, S6), because the API no longer blocks.
2.  **Status Codes:** Expect `202 Accepted` or `200 OK`.
3.  **Scenario 5 Check:** Since the API returns immediately, k6 cannot verify the final "Failed" status in the immediate response.
      * *Optional:* If possible, add a `GET /orders/{id}` check in the k6 script that polls after a few seconds to verify the final status is "failed", confirming the Saga finished.

-----

### 5\. Deliverables & Directory Structure

Generate the full code structure:

```
/asynchronous-project
|-- /common (optional, for shared rabbitmq connection logic)
|-- /analyticsservice
|   |-- main.py (FastAPI + Consumer)
|   |-- Dockerfile
|   |-- requirements.txt
|-- /cacheservice
|-- /emailservice
|-- /inventoryservice
|-- /orderservice
|-- /paymentservice
|-- /productservice
|-- /reportservice
|-- /searchservice
|-- /userservice
|-- /k6-tests
|   |-- script-async.js
|-- docker-compose-async.yml
```

**Important Implementation Note:**
Ensure the RabbitMQ consumer loop does not block the FastAPI server. Use `asyncio` features or run the consumer in a separate thread/process within the container.