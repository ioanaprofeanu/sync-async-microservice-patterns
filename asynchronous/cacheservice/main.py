"""
CacheService - Scenario 3: Fan-Out Flow Consumer
Consumes ProductUpdated events from fanout exchange and invalidates cache.
"""

import asyncio
import logging
import os
import sys
from contextlib import asynccontextmanager

sys.path.append('/app/common')

from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator

from rabbitmq_client import RabbitMQClient
from event_schemas import ProductUpdatedEvent, json_to_event
from base_consumer import FanoutConsumer

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "rabbitmq")
RABBITMQ_USER = os.getenv("RABBITMQ_USER", "guest")
RABBITMQ_PASSWORD = os.getenv("RABBITMQ_PASSWORD", "guest")

FANOUT_EXCHANGE = "product_updates"
QUEUE_NAME = "cache_product_updates_queue"

rabbitmq_client: RabbitMQClient = None
consumer_task: asyncio.Task = None


async def process_product_updated(message_body: str, message) -> None:
    """Process ProductUpdated event and invalidate cache"""
    try:
        event = json_to_event(message_body, ProductUpdatedEvent)
        logger.info(f"🗑️  Invalidating cache for product {event.product_id}: {event.name}")

        # Simulate cache invalidation
        await asyncio.sleep(0.05)

        logger.info(f"✓ Cache invalidated for product {event.product_id}")

    except Exception as e:
        logger.error(f"Error invalidating cache: {e}")
        raise


async def start_consumer():
    """Start fanout consumer for ProductUpdated events"""
    global rabbitmq_client

    rabbitmq_client = RabbitMQClient(
        host=RABBITMQ_HOST,
        user=RABBITMQ_USER,
        password=RABBITMQ_PASSWORD
    )
    await rabbitmq_client.connect()

    consumer = FanoutConsumer(
        exchange_name=FANOUT_EXCHANGE,
        queue_name=QUEUE_NAME,
        rabbitmq_client=rabbitmq_client
    )

    logger.info(f"CacheService consumer started on fanout exchange '{FANOUT_EXCHANGE}'")
    await consumer.start(process_product_updated)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle"""
    global consumer_task

    logger.info("Starting CacheService...")
    consumer_task = asyncio.create_task(start_consumer())

    yield

    logger.info("Shutting down CacheService...")
    if consumer_task:
        consumer_task.cancel()
        try:
            await consumer_task
        except asyncio.CancelledError:
            pass

    if rabbitmq_client:
        await rabbitmq_client.disconnect()


app = FastAPI(
    title="CacheService",
    version="1.0.0",
    description="Async cache invalidation service (Scenario 3)",
    lifespan=lifespan
)

Instrumentator().instrument(app).expose(app)


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "service": "cacheservice",
        "architecture": "async",
        "rabbitmq_connected": rabbitmq_client is not None and rabbitmq_client.connection is not None
    }


@app.get("/")
async def root():
    return {
        "service": "CacheService",
        "version": "1.0.0",
        "architecture": "Event-Driven (Async)",
        "scenario": "3 - Fan-Out Flow (Cache Invalidation)",
        "description": "Consumes ProductUpdated events and invalidates cache in parallel"
    }
