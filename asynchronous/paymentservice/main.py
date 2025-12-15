"""
PaymentService - Scenario 2: Long-Running Process + Scenario 5: Saga Pattern
HTTP endpoint that accepts payment requests and processes them asynchronously.
Also participates in Saga pattern by listening to StockReserved events.
"""

import asyncio
import logging
import os
import sys
import uuid
from contextlib import asynccontextmanager
from datetime import datetime

# Add common module to path
sys.path.append('/app/common')

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from prometheus_fastapi_instrumentator import Instrumentator
from aio_pika import ExchangeType

from rabbitmq_client import RabbitMQClient
from event_schemas import (
    PaymentInitiatedEvent, PaymentCompletedEvent, PaymentFailedEvent,
    StockReservedEvent, event_to_json, json_to_event
)
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

# Fanout exchange for PaymentFailed events (multiple consumers need to receive)
PAYMENT_FAILED_EXCHANGE = "payment_failed"

# Global variables
rabbitmq_client: RabbitMQClient = None
consumer_tasks: list = []


# ==================== Pydantic Models ====================

class PaymentRequest(BaseModel):
    """Request model for payment processing"""
    amount: float
    currency: str = "USD"


class PaymentResponse(BaseModel):
    """Response model for payment initiation"""
    payment_id: str
    status: str
    message: str


# ==================== Event Handlers ====================

async def process_payment_initiated(message_body: str, message) -> None:
    """
    Process PaymentInitiated event (Scenario 2: Long-running process).
    Simulates 2-second payment gateway delay.

    Args:
        message_body: JSON string of PaymentInitiatedEvent
        message: RabbitMQ message object
    """
    try:
        event = json_to_event(message_body, PaymentInitiatedEvent)
        logger.info(f"Processing payment {event.payment_id} for ${event.amount} {event.currency}")

        # Simulate long-running external payment gateway call (2 seconds)
        await asyncio.sleep(2)

        # Generate transaction ID
        transaction_id = f"txn_{uuid.uuid4().hex[:12]}"

        # Publish PaymentCompleted event
        completed_event = PaymentCompletedEvent(
            payment_id=event.payment_id,
            transaction_id=transaction_id,
            status="success",
            timestamp=datetime.utcnow()
        )

        await rabbitmq_client.publish_message(
            exchange_name="",
            routing_key="payment_completed_queue",
            message_body=event_to_json(completed_event)
        )

        logger.info(f"✓ Payment {event.payment_id} completed successfully (txn: {transaction_id})")

    except Exception as e:
        logger.error(f"Error processing payment: {e}")
        raise


async def process_stock_reserved(message_body: str, message) -> None:
    """
    Process StockReserved event (Scenario 5: Saga Pattern).
    This handler simulates payment failure to demonstrate saga compensation.

    Args:
        message_body: JSON string of StockReservedEvent
        message: RabbitMQ message object
    """
    try:
        event = json_to_event(message_body, StockReservedEvent)
        logger.info(f"Received StockReserved for order {event.order_id} (product {event.product_id})")

        # Simulate payment processing delay
        await asyncio.sleep(0.5)

        # SIMULATE PAYMENT FAILURE (as per Scenario 5 requirements)
        logger.warning(f"⚠️ Payment FAILED for order {event.order_id} (simulated failure)")

        # Publish PaymentFailed event to fanout exchange (both OrderService and InventoryService need it)
        failed_event = PaymentFailedEvent(
            order_id=event.order_id,
            reason="Insufficient funds (simulated failure for saga demonstration)",
            timestamp=datetime.utcnow()
        )

        await rabbitmq_client.publish_message(
            exchange_name=PAYMENT_FAILED_EXCHANGE,
            routing_key="",  # Empty routing key for fanout
            message_body=event_to_json(failed_event),
            exchange_type=ExchangeType.FANOUT
        )

        logger.info(f"PaymentFailed event published for order {event.order_id}")

    except Exception as e:
        logger.error(f"Error processing StockReserved event: {e}")
        raise


# ==================== Consumers ====================

async def start_payment_consumer():
    """
    Start consumer for PaymentInitiated events (Scenario 2).
    """
    consumer = BaseConsumer(
        queue_name="payment_initiated_queue",
        rabbitmq_client=rabbitmq_client,
        max_retries=3
    )
    logger.info("Starting PaymentInitiated consumer...")
    await consumer.start(process_payment_initiated)


async def start_saga_consumer():
    """
    Start consumer for StockReserved events (Scenario 5 Saga).
    """
    consumer = BaseConsumer(
        queue_name="stock_reserved_queue",
        rabbitmq_client=rabbitmq_client,
        max_retries=3
    )
    logger.info("Starting StockReserved consumer (Saga)...")
    await consumer.start(process_stock_reserved)


# ==================== Lifecycle Management ====================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage application lifecycle.
    """
    global rabbitmq_client, consumer_tasks

    # Startup
    logger.info("Starting PaymentService...")

    # Initialize RabbitMQ
    rabbitmq_client = RabbitMQClient(
        host=RABBITMQ_HOST,
        user=RABBITMQ_USER,
        password=RABBITMQ_PASSWORD
    )
    await rabbitmq_client.connect()

    # Declare queues
    await rabbitmq_client.declare_queue("payment_initiated_queue", durable=True)
    await rabbitmq_client.declare_queue("payment_completed_queue", durable=True)
    await rabbitmq_client.declare_queue("stock_reserved_queue", durable=True)

    # Declare fanout exchange for PaymentFailed events (multiple consumers)
    await rabbitmq_client.declare_exchange(
        PAYMENT_FAILED_EXCHANGE,
        ExchangeType.FANOUT,
        durable=True
    )
    logger.info(f"Fanout exchange '{PAYMENT_FAILED_EXCHANGE}' declared")

    # Start consumers as background tasks
    consumer_tasks.append(asyncio.create_task(start_payment_consumer()))
    consumer_tasks.append(asyncio.create_task(start_saga_consumer()))

    logger.info("PaymentService started successfully")

    yield

    # Shutdown
    logger.info("Shutting down PaymentService...")
    for task in consumer_tasks:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    if rabbitmq_client:
        await rabbitmq_client.disconnect()


# FastAPI application
app = FastAPI(
    title="PaymentService",
    version="1.0.0",
    description="Async payment processing service (Scenario 2 & 5)",
    lifespan=lifespan
)

# Prometheus metrics instrumentation
Instrumentator().instrument(app).expose(app)


# ==================== API Endpoints ====================

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "paymentservice",
        "architecture": "async",
        "timestamp": datetime.utcnow().isoformat(),
        "rabbitmq_connected": rabbitmq_client is not None and rabbitmq_client.connection is not None
    }


@app.get("/")
async def root():
    """Root endpoint with service information"""
    return {
        "service": "PaymentService",
        "version": "1.0.0",
        "architecture": "Event-Driven (Async)",
        "scenarios": ["2 - Long-Running Process", "5 - Saga Pattern (Payment Failure)"],
        "description": "Processes payments asynchronously and participates in saga choreography"
    }


@app.post("/process_payment", status_code=202, response_model=PaymentResponse)
async def process_payment(payment: PaymentRequest):
    """
    Scenario 2: Long-Running Process (Async)

    Accepts payment request and processes it asynchronously.
    Returns 202 Accepted immediately without waiting for gateway response.

    Args:
        payment: Payment details (amount, currency)

    Returns:
        Payment ID and status
    """
    try:
        # Generate unique payment ID
        payment_id = f"pay_{uuid.uuid4().hex[:12]}"

        logger.info(f"Received payment request {payment_id} for ${payment.amount} {payment.currency}")

        # Publish PaymentInitiated event
        event = PaymentInitiatedEvent(
            payment_id=payment_id,
            amount=payment.amount,
            currency=payment.currency,
            timestamp=datetime.utcnow()
        )

        await rabbitmq_client.publish_message(
            exchange_name="",
            routing_key="payment_initiated_queue",
            message_body=event_to_json(event)
        )

        logger.info(f"PaymentInitiated event published for {payment_id}")

        # Return immediately (202 Accepted)
        return PaymentResponse(
            payment_id=payment_id,
            status="processing",
            message="Payment initiated successfully. Processing asynchronously."
        )

    except Exception as e:
        logger.error(f"Error initiating payment: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.post("/process_payment_fail", status_code=202)
async def process_payment_fail():
    """
    Scenario 5: Saga Pattern - Simulate payment failure endpoint
    (Used by OrderService in saga pattern for testing compensation)

    This endpoint is kept for compatibility but is not the primary failure mechanism.
    The actual failure happens in the StockReserved event handler.

    Returns:
        Failure confirmation
    """
    logger.warning("Payment failure endpoint called (saga test)")

    return {
        "status": "failed",
        "reason": "Insufficient funds",
        "message": "Payment failed as expected for saga demonstration"
    }
