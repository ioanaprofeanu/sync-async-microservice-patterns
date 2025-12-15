Here is the revised and more detailed prompt for the AI.

-----

### 🤖 AI Programming Prompt

**Project Title:** Synchronous Architecture Implementation (Milestone 2)

**Objective:** You are a senior software engineer. Your task is to generate the complete code for **Milestone 2** of a comparative study project. This milestone focuses exclusively on implementing the **Synchronous (Request-Response) Architecture**. You will generate the complete code for all microservices, database schemas, Docker files, and test scripts required for this milestone.

-----

### 1\. Global Tech Constraints (Mandatory)

  * **Language:** Python 3.10+
  * **Framework:** FastAPI (for all microservices)
  * **Database:** PostgreSQL
  * **Orchestration:** Docker, with a single `docker-compose-sync.yml` file.
  * **Communication Model:** **Strictly Synchronous (Blocking)**. All inter-service communication must be via direct HTTP (REST) API calls.
  * **HTTP Client:** Use the `requests` library for all synchronous inter-service calls.
  * **Standard Port:** All FastAPI services should run on port `8000` inside their containers.

-----

### 2\. Standard Service Templates

**1. Base Service (No DB):**

  * `main.py`: Contains the FastAPI app. Includes a `/health` endpoint that returns `{"status": "ok"}`.
  * `Dockerfile`:
      * `FROM python:3.10-slim`
      * `WORKDIR /app`
      * `COPY requirements.txt .`
      * `RUN pip install --no-cache-dir -r requirements.txt`
      * `COPY . .`
      * `CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]`
  * `requirements.txt`:
    ```
    fastapi
    uvicorn[standard]
    requests
    ```

**2. Service (With DB):**

  * Same as "Base Service" but with additional dependencies.
  * `requirements.txt`:
    ```
    fastapi
    uvicorn[standard]
    requests
    sqlalchemy
    psycopg2-binary
    ```
  * `main.py` should include logic to connect to the PostgreSQL database using SQLAlchemy. Connection details (user, pass, db, host) should be read from environment variables.

-----

### 3\. Database Schema

Define the following simple SQLAlchemy models. These will be used by their respective services.

  * **User (for `UserService`):**
      * `id` (Integer, Primary Key)
      * `email` (String, Unique)
  * **Product (for `ProductService`):**
      * `id` (Integer, Primary Key)
      * `name` (String)
      * `stock` (Integer)
  * **Order (for `OrderService`):**
      * `id` (Integer, Primary Key)
      * `product_id` (Integer)
      * `status` (String, e.g., "pending", "failed", "completed")
  * **InventoryItem (for `InventoryService`):**
      * `product_id` (Integer, Primary Key)
      * `reserved` (Integer, default 0)

if possible, you can add fake data to this database. if during the implementation you think you need more tables/ columns, don t be afraid to create them.

-----

### 4\. Scenario & Service Implementation

Implement all 6 scenarios. Services should be built from the templates above.

#### Scenario 1: Non-Critical Task Decoupling

  * **Services:**
      * `UserService` (With DB): Manages user registration.
      * `EmailService` (No DB): Simulates sending an email.
  * **Flow:**
    1.  Create `POST /register` endpoint on `UserService`.
    2.  This endpoint receives a JSON `{"email": "..."}`.
    3.  `UserService` saves the new user to its `users` table in Postgres.
    4.  After saving, `UserService` makes a **synchronous** call: `requests.post("http://emailservice:8000/send_welcome_email", json={"email": "..."})`.
    5.  `EmailService` must implement `POST /send_welcome_email` which **sleeps for 500ms** (`time.sleep(0.5)`) and then returns `{"message": "Email sent"}`.
    6.  `UserService` waits for the response from `EmailService` before returning a `201 Created` response to the client.

#### Scenario 2: Simulated Long-Running Process

  * **Services:**
      * `PaymentService` (No DB): Simulates an external payment gateway.
  * **Flow:**
    1.  Implement `POST /process_payment` on `PaymentService`.
    2.  This endpoint **sleeps for 2 seconds** (`time.sleep(2)`) to simulate a slow external API.
    3.  After the delay, it returns `{"status": "success", "transaction_id": "..."}`.
    4.  **For Scenario 5:** Also add a `POST /process_payment_fail` endpoint that *immediately* returns an HTTP 400 error: `{"status": "failed", "reason": "Insufficient funds"}`.

#### Scenario 3: "Fan-Out" Flow

  * **Services:**
      * `ProductService` (With DB): Manages product information.
      * `SearchService` (No DB): Mock service.
      * `CacheService` (No DB): Mock service.
      * `AnalyticsService` (No DB): Mock service (will be used in S6 too).
  * **Flow:**
    1.  Implement `PUT /products/{product_id}` on `ProductService`.
    2.  The endpoint updates the product in its `products` table.
    3.  After the DB update, `ProductService` must execute the following calls **sequentially**:
        1.  `requests.post("http://searchservice:8000/reindex", json={"product_id": ...})`
        2.  `requests.post("http://cacheservice:8000/invalidate_cache", json={"product_id": ...})`
        3.  `requests.post("http://analyticsservice:8000/log_update", json={"product_id": ...})`
    4.  `SearchService`, `CacheService`, and `AnalyticsService` must implement their respective endpoints (`/reindex`, `/invalidate_cache`, `/log_update`). These endpoints do nothing and return `{"status": "ok"}` immediately.
    5.  Only after all three synchronous calls complete does `ProductService` return a `200 OK` to the client.

#### Scenario 4: CPU-Intensive Task

  * **Services:**
      * `ReportService` (No DB).
  * **Flow:**
    1.  Implement `POST /generate_report` on `ReportService`.
    2.  This endpoint must perform a **CPU-bound task for \~10 seconds**. **Do not use `time.sleep()`**.
    3.  **Implementation:** Run a loop that calculates a large number of SHA-256 hashes. Example:
        ```python
        import hashlib
        import time
        start_time = time.time()
        text = b"compute_hash"
        while (time.time() - start_time) < 10:
            text = hashlib.sha256(text).digest()
        return {"report_hash": text.hex()}
        ```
    4.  After the computation is complete, return the result.

#### Scenario 5: Synchronous Saga & Compensation

  * **Services:**
      * `OrderService` (With DB): Manages the order workflow.
      * `InventoryService` (With DB): Manages stock reservations.
      * `PaymentService` (From S2): Used for its failure endpoint.
  * **Flow:**
    1.  Implement `POST /create_order` on `OrderService`. It receives `{"product_id": 1, "quantity": 1}`.
    2.  `OrderService` creates an order in its `orders` table with `status="pending"`.
    3.  **Step 1 (Reserve Stock):** `OrderService` calls `requests.post("http://inventoryservice:8000/reserve_stock", json={...})`.
    4.  `InventoryService` implements `/reserve_stock`. It updates the `reserved` count in its `inventoryitem` table and returns `200 OK`.
    5.  **Step 2 (Take Payment):** `OrderService` calls `requests.post("http://paymentservice:8000/process_payment_fail", json={...})`.
    6.  As defined in S2, `PaymentService`'s `/process_payment_fail` endpoint returns an HTTP 400 error.
    7.  **Step 3 (Compensation):** `OrderService` receives the HTTP error. It must now execute **manual compensation**.
    8.  `OrderService` calls `requests.post("http://inventoryservice:8000/compensate_stock", json={...})`.
    9.  `InventoryService` implements `/compensate_stock`. It decrements the `reserved` count in its table.
    10. `OrderService` updates its local order status to `status="failed"`.
    11. `OrderService` returns a 400-level error to the client, e.g., `{"message": "Order failed due to payment issue"}`.

#### Scenario 6: High-Throughput Data Ingestion

  * **Services:**
      * `AnalyticsService` (From S3).
  * **Flow:**
    1.  Implement `POST /track_click` on the existing `AnalyticsService`.
    2.  This endpoint receives a small JSON payload (e.g., `{"user_id": 123, "page": "homepage"}`).
    3.  The endpoint does minimal work (e.g., a simple log print) and returns `{"status": "tracked"}` as fast as possible.

-----

### 5\. Docker Compose & k6 Test Setup

**1. `docker-compose-sync.yml`:**

  * Define a service for **every** service created above (10 total: `UserService`, `EmailService`, `PaymentService`, `ProductService`, `SearchService`, `CacheService`, `AnalyticsService`, `ReportService`, `OrderService`, `InventoryService`).
  * Each service definition should:
      * `build: ./servicename` (pointing to its directory).
      * `container_name: servicename`
      * `command: uvicorn main:app --host 0.0.0.0 --port 8000`
  * Define a `postgres` service:
      * `image: postgres:14`
      * `environment:` (set `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`).
      * `volumes:` (to persist data).
  * **Expose Ports:** For k6 testing, expose the ports of the "entrypoint" services:
      * `userservice`: `ports: ["8001:8000"]`
      * `paymentservice`: `ports: ["8002:8000"]`
      * `productservice`: `ports: ["8003:8000"]`
      * `reportservice`: `ports: ["8004:8000"]`
      * `orderservice`: `ports: ["8005:8000"]`
      * `analyticsservice`: `ports: ["8006:8000"]`

**2. `k6-tests/script-sync.js`:**

  * Create a JavaScript file for k6.
  * Define a `group` for each scenario, hitting the exposed ports on `localhost`.
  * **Scenario 1:** `http.post("http://localhost:8001/register", ...)` and `check` that `res.status === 201` and `res.timings.duration > 500`.
  * **Scenario 2:** `http.post("http://localhost:8002/process_payment", ...)` and `check` that `res.status === 200` and `res.timings.duration > 2000`.
  * **Scenario 3:** `http.put("http://localhost:8003/products/1", ...)` and `check` that `res.status === 200`.
  * **Scenario 4:** `http.post("http://localhost:8004/generate_report", ...)` and `check` that `res.status === 200` and `res.timings.duration > 10000`. (Note: k6's default timeout might need to be increased for this request).
  * **Scenario 5:** `http.post("http://localhost:8005/create_order", ...)` and `check` that `res.status === 400`.
  * **Scenario 6:** `http.post("http://localhost:8006/track_click", ...)` and `check` that `res.status === 200`. This group should be configured for high throughput (e.g., using `scenarios` in `options`).

-----

### 6\. Expected Output Format

Generate the complete code organized by file, matching this directory structure:

```
/synchronous-project
|-- /analyticsservice
|   |-- main.py
|   |-- Dockerfile
|   |-- requirements.txt
|-- /cacheservice
|   |-- ... (main.py, Dockerfile, requirements.txt)
|-- /emailservice
|   |-- ...
|-- /inventoryservice
|   |-- ...
|-- /orderservice
|   |-- ...
|-- /paymentservice
|   |-- ...
|-- /productservice
|   |-- ...
|-- /reportservice
|   |-- ...
|-- /searchservice
|   |-- ...
|-- /userservice
|   |-- ...
|-- /k6-tests
|   |-- script-sync.js
|-- docker-compose-sync.yml
```