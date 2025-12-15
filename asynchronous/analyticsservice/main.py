"""
AnalyticsService - Scenario 3 & 6
Fanout consumer for ProductUpdated events + High-throughput click tracking endpoint.
"""

import asyncio
import logging
import os
import sys
import uuid
from contextlib import asynccontextmanager
from datetime import datetime

sys.path.append('/app/common')

from fastapi import FastAPI
from pydantic import BaseModel
from prometheus_fastapi_instrumentator import Instrumentator

from rabbitmq_client import RabbitMQClient
from event_schemas import ProductUpdatedEvent, ClickTrackedEvent, event_to_json, json_to_event
from base_consumer import FanoutConsumer, BaseConsumer

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "rabbitmq")
RABBITMQ_USER = os.getenv("RABBITMQ_USER", "guest")
RABBITMQ_PASSWORD = os.getenv("RABBITMQ_PASSWORD", "guest")

FANOUT_EXCHANGE = "product_updates"
PRODUCT_QUEUE = "analytics_product_updates_queue"
CLICK_QUEUE = "click_tracked_queue"

rabbitmq_client: RabbitMQClient = None
consumer_tasks: list = []


class ClickTrackingRequest(BaseModel):
    """Request model for click tracking (Scenario 6)"""
    user_id: int
    page: str
    session_id: str = None


async def process_product_updated(message_body: str, message) -> None:
    """Process ProductUpdated event (Scenario 3)"""
    try:
        event = json_to_event(message_body, ProductUpdatedEvent)
        logger.info(f"📊 Logging analytics for product {event.product_id}: {event.name}")
        await asyncio.sleep(0.05)
        logger.info(f"✓ Analytics logged for product {event.product_id}")
    except Exception as e:
        logger.error(f"Error logging analytics: {e}")
        raise


async def process_click_tracked(message_body: str, message) -> None:
    """Process ClickTracked event (Scenario 6)"""
    try:
        event = json_to_event(message_body, ClickTrackedEvent)
        # Just log - demonstrates high-throughput buffering
        logger.debug(f"Click tracked: user {event.user_id} on {event.page}")
    except Exception as e:
        logger.error(f"Error processing click: {e}")


async def start_product_consumer():
    """Start fanout consumer for ProductUpdated events"""
    consumer = FanoutConsumer(
        exchange_name=FANOUT_EXCHANGE,
        queue_name=PRODUCT_QUEUE,
        rabbitmq_client=rabbitmq_client
    )
    logger.info(f"ProductUpdated consumer started")
    await consumer.start(process_product_updated)


async def start_click_consumer():
    """Start consumer for ClickTracked events"""
    consumer = BaseConsumer(
        queue_name=CLICK_QUEUE,
        rabbitmq_client=rabbitmq_client
    )
    logger.info(f"ClickTracked consumer started")
    await consumer.start(process_click_tracked)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle"""
    global rabbitmq_client, consumer_tasks

    logger.info("Starting AnalyticsService...")

    rabbitmq_client = RabbitMQClient(
        host=RABBITMQ_HOST,
        user=RABBITMQ_USER,
        password=RABBITMQ_PASSWORD
    )
    await rabbitmq_client.connect()

    # Declare queues
    await rabbitmq_client.declare_queue(CLICK_QUEUE, durable=True)

    # Start consumers
    consumer_tasks.append(asyncio.create_task(start_product_consumer()))
    consumer_tasks.append(asyncio.create_task(start_click_consumer()))

    yield

    logger.info("Shutting down AnalyticsService...")
    for task in consumer_tasks:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    if rabbitmq_client:
        await rabbitmq_client.disconnect()


app = FastAPI(
    title="AnalyticsService",
    version="1.0.0",
    description="Async analytics service (Scenario 3 & 6)",
    lifespan=lifespan
)

Instrumentator().instrument(app).expose(app)


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "service": "analyticsservice",
        "architecture": "async",
        "rabbitmq_connected": rabbitmq_client is not None and rabbitmq_client.connection is not None
    }


@app.get("/")
async def root():
    return {
        "service": "AnalyticsService",
        "version": "1.0.0",
        "architecture": "Event-Driven (Async)",
        "scenarios": ["3 - Fan-Out Flow (Analytics)", "6 - High-Throughput Data Ingestion"],
        "description": "Tracks product analytics and high-throughput click events"
    }


@app.post("/track_click", status_code=200)
async def track_click(click_data: ClickTrackingRequest):
    """
    Scenario 6: High-Throughput Data Ingestion

    Accepts click tracking data and publishes to RabbitMQ buffer.
    Returns immediately for maximum throughput.
    """
    try:
        # Publish to queue (acts as buffer)
        event = ClickTrackedEvent(
            user_id=click_data.user_id,
            page=click_data.page,
            session_id=click_data.session_id or str(uuid.uuid4()),
            timestamp=datetime.utcnow()
        )

        await rabbitmq_client.publish_message(
            exchange_name="",
            routing_key=CLICK_QUEUE,
            message_body=event_to_json(event)
        )

        return {"status": "tracked"}

    except Exception as e:
        logger.error(f"Error tracking click: {e}")
        return {"status": "error", "detail": str(e)}
