"""
EmailService - Scenario 1: Decoupling Non-Critical Tasks
Consumer-only service that listens to UserRegistered events and sends welcome emails.
"""

import asyncio
import logging
import os
import sys
from contextlib import asynccontextmanager

# Add common module to path
sys.path.append('/app/common')

from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator

from rabbitmq_client import RabbitMQClient
from event_schemas import UserRegisteredEvent, json_to_event
from base_consumer import BaseConsumer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# RabbitMQ configuration
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "rabbitmq")
RABBITMQ_USER = os.getenv("RABBITMQ_USER", "guest")
RABBITMQ_PASSWORD = os.getenv("RABBITMQ_PASSWORD", "guest")

# Global variables
rabbitmq_client: RabbitMQClient = None
consumer_task: asyncio.Task = None


async def process_user_registered(message_body: str, message) -> None:
    """
    Process UserRegistered event and send welcome email.

    Args:
        message_body: JSON string of UserRegisteredEvent
        message: RabbitMQ message object
    """
    try:
        # Parse event
        event = json_to_event(message_body, UserRegisteredEvent)
        logger.info(f"Processing UserRegistered event for user {event.user_id}: {event.email}")

        # Simulate email sending delay (500ms as per requirements)
        await asyncio.sleep(0.5)

        logger.info(f"✉️ Welcome email sent to {event.email} (user_id: {event.user_id})")

    except Exception as e:
        logger.error(f"Error processing UserRegistered event: {e}")
        raise


async def start_consumer():
    """
    Start RabbitMQ consumer for UserRegistered events.
    """
    global rabbitmq_client

    try:
        # Initialize RabbitMQ client
        rabbitmq_client = RabbitMQClient(
            host=RABBITMQ_HOST,
            user=RABBITMQ_USER,
            password=RABBITMQ_PASSWORD
        )
        await rabbitmq_client.connect()

        # Create consumer
        consumer = BaseConsumer(
            queue_name="user_registered_queue",
            rabbitmq_client=rabbitmq_client,
            max_retries=3
        )

        # Start consuming
        logger.info("EmailService consumer started")
        await consumer.start(process_user_registered)

    except Exception as e:
        logger.error(f"Error in email consumer: {e}")
        raise


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage application lifecycle: start consumer on startup, stop on shutdown.
    """
    global consumer_task

    # Startup: Launch consumer as background task
    logger.info("Starting EmailService...")
    consumer_task = asyncio.create_task(start_consumer())

    yield

    # Shutdown: Close consumer and RabbitMQ connection
    logger.info("Shutting down EmailService...")
    if consumer_task:
        consumer_task.cancel()
        try:
            await consumer_task
        except asyncio.CancelledError:
            pass

    if rabbitmq_client:
        await rabbitmq_client.disconnect()


# FastAPI application
app = FastAPI(
    title="EmailService",
    version="1.0.0",
    description="Async event-driven email service (Scenario 1)",
    lifespan=lifespan
)

# Prometheus metrics instrumentation
Instrumentator().instrument(app).expose(app)


@app.get("/health")
async def health():
    """
    Health check endpoint.
    """
    return {
        "status": "healthy",
        "service": "emailservice",
        "architecture": "async",
        "rabbitmq_connected": rabbitmq_client is not None and rabbitmq_client.connection is not None
    }


@app.get("/")
async def root():
    """
    Root endpoint with service information.
    """
    return {
        "service": "EmailService",
        "version": "1.0.0",
        "architecture": "Event-Driven (Async)",
        "scenario": "1 - Decoupling Non-Critical Tasks",
        "description": "Consumes UserRegistered events and sends welcome emails asynchronously"
    }
