"""
ReportService - Scenario 4: CPU-Intensive Task Offloading
HTTP endpoint accepts report requests, consumer processes CPU-intensive hashing job.
"""

import asyncio
import hashlib
import logging
import os
import sys
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from datetime import datetime

sys.path.append('/app/common')

from fastapi import FastAPI
from pydantic import BaseModel
from prometheus_fastapi_instrumentator import Instrumentator

from rabbitmq_client import RabbitMQClient
from event_schemas import GenerateReportJobEvent, event_to_json, json_to_event
from base_consumer import BaseConsumer

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "rabbitmq")
RABBITMQ_USER = os.getenv("RABBITMQ_USER", "guest")
RABBITMQ_PASSWORD = os.getenv("RABBITMQ_PASSWORD", "guest")

REPORT_QUEUE = "report_job_queue"

rabbitmq_client: RabbitMQClient = None
consumer_task: asyncio.Task = None
thread_pool: ThreadPoolExecutor = None


class ReportJobResponse(BaseModel):
    """Response model for report job submission"""
    job_id: str
    status: str
    message: str


def cpu_intensive_hashing() -> str:
    """
    Synchronous CPU-intensive task that runs in a thread pool.
    Performs 10 seconds of actual CPU work (SHA-256 hashing loop).

    Returns:
        Hex digest of the final hash
    """
    start_time = time.time()
    text = b"compute_hash"

    # CPU-intensive task: SHA-256 hashing for ~10 seconds
    while (time.time() - start_time) < 10:
        text = hashlib.sha256(text).digest()

    return text.hex()


async def process_report_job(message_body: str, message) -> None:
    """
    Process GenerateReportJob event with CPU-intensive task.
    Runs the CPU work in a thread pool to avoid blocking the event loop.
    """
    try:
        event = json_to_event(message_body, GenerateReportJobEvent)
        logger.info(f"🔄 Processing report job {event.job_id} (type: {event.report_type})")

        start_time = time.time()

        # Run CPU-intensive work in thread pool to avoid blocking event loop
        loop = asyncio.get_event_loop()
        report_hash = await loop.run_in_executor(thread_pool, cpu_intensive_hashing)

        duration = time.time() - start_time

        logger.info(
            f"✓ Report job {event.job_id} completed in {duration:.2f}s. Hash: {report_hash[:16]}..."
        )

    except Exception as e:
        logger.error(f"Error processing report job: {e}")
        raise


async def start_consumer():
    """Start consumer for report job queue (uses global rabbitmq_client)"""
    global rabbitmq_client

    consumer = BaseConsumer(
        queue_name=REPORT_QUEUE,
        rabbitmq_client=rabbitmq_client
    )

    logger.info("ReportService consumer started")
    await consumer.start(process_report_job)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle"""
    global rabbitmq_client, consumer_task, thread_pool

    logger.info("Starting ReportService...")

    # Initialize thread pool for CPU-intensive tasks
    thread_pool = ThreadPoolExecutor(max_workers=4)

    # Initialize RabbitMQ connection (before starting consumer or accepting requests)
    rabbitmq_client = RabbitMQClient(
        host=RABBITMQ_HOST,
        user=RABBITMQ_USER,
        password=RABBITMQ_PASSWORD
    )
    await rabbitmq_client.connect()

    # Declare queue
    await rabbitmq_client.declare_queue(REPORT_QUEUE, durable=True)

    # Start consumer as background task
    consumer_task = asyncio.create_task(start_consumer())

    logger.info("ReportService initialized successfully")

    yield

    logger.info("Shutting down ReportService...")

    # Cancel consumer task
    if consumer_task:
        consumer_task.cancel()
        try:
            await consumer_task
        except asyncio.CancelledError:
            pass

    # Shutdown thread pool
    if thread_pool:
        thread_pool.shutdown(wait=True)

    # Disconnect RabbitMQ
    if rabbitmq_client:
        await rabbitmq_client.disconnect()


app = FastAPI(
    title="ReportService",
    version="1.0.0",
    description="Async report generation service (Scenario 4)",
    lifespan=lifespan
)

Instrumentator().instrument(app).expose(app)


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "service": "reportservice",
        "architecture": "async",
        "rabbitmq_connected": rabbitmq_client is not None and rabbitmq_client.connection is not None
    }


@app.get("/")
async def root():
    return {
        "service": "ReportService",
        "version": "1.0.0",
        "architecture": "Event-Driven (Async)",
        "scenario": "4 - CPU-Intensive Task Offloading",
        "description": "Offloads CPU-intensive report generation to background worker"
    }


@app.post("/generate_report", status_code=202, response_model=ReportJobResponse)
async def generate_report():
    """
    Scenario 4: CPU-Intensive Task Offloading (Async)

    Accepts report generation request and offloads to background worker.
    Returns 202 Accepted immediately with job ID.
    """
    try:
        # Generate unique job ID
        job_id = f"job_{uuid.uuid4().hex[:12]}"

        logger.info(f"Received report generation request: {job_id}")

        # Publish job to queue
        event = GenerateReportJobEvent(
            job_id=job_id,
            report_type="performance_summary",
            parameters={},
            timestamp=datetime.utcnow()
        )

        await rabbitmq_client.publish_message(
            exchange_name="",
            routing_key=REPORT_QUEUE,
            message_body=event_to_json(event)
        )

        logger.info(f"Report job {job_id} queued for processing")

        return ReportJobResponse(
            job_id=job_id,
            status="queued",
            message="Report generation job queued. Processing in background."
        )

    except Exception as e:
        logger.error(f"Error queueing report job: {e}")
        return ReportJobResponse(
            job_id="",
            status="error",
            message=str(e)
        )
