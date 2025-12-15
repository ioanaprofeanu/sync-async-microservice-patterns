"""
OrderService - Scenario 5: Choreography Saga Pattern
Creates orders and participates in event-driven saga choreography.
"""

import asyncio
import logging
import os
import sys
from contextlib import asynccontextmanager
from datetime import datetime

sys.path.append('/app/common')

from fastapi import FastAPI, Depends
from pydantic import BaseModel
from sqlalchemy import Column, Integer, String, select
from sqlalchemy.ext.asyncio import AsyncSession
from prometheus_fastapi_instrumentator import Instrumentator
from aio_pika import ExchangeType

from database import DatabaseManager, Base, get_db, set_db_manager
from rabbitmq_client import RabbitMQClient
from event_schemas import OrderCreatedEvent, PaymentFailedEvent, event_to_json, json_to_event
from base_consumer import BaseConsumer

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "rabbitmq")
RABBITMQ_USER = os.getenv("RABBITMQ_USER", "guest")
RABBITMQ_PASSWORD = os.getenv("RABBITMQ_PASSWORD", "guest")

# Fanout exchange for PaymentFailed events
PAYMENT_FAILED_EXCHANGE = "payment_failed"
# This service's dedicated queue for payment failed events
ORDER_PAYMENT_FAILED_QUEUE = "order_payment_failed_queue"

rabbitmq_client: RabbitMQClient = None
db_manager: DatabaseManager = None
consumer_task: asyncio.Task = None


# ==================== Database Models ====================

class Order(Base):
    """Order database model"""
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, nullable=False)
    quantity = Column(Integer, default=1, nullable=False)
    status = Column(String, default="pending", nullable=False)  # pending, failed, completed


# ==================== Pydantic Models ====================

class OrderRequest(BaseModel):
    """Request model for order creation"""
    product_id: int
    quantity: int = 1


class OrderResponse(BaseModel):
    """Response model for order operations"""
    id: int
    product_id: int
    quantity: int
    status: str


# ==================== Event Handlers ====================

async def process_payment_failed(message_body: str, message) -> None:
    """
    Handle PaymentFailed event (Saga compensation).
    Updates order status to "failed" when payment fails.
    """
    try:
        event = json_to_event(message_body, PaymentFailedEvent)
        logger.warning(f"⚠️ Payment failed for order {event.order_id}: {event.reason}")

        # Update order status to failed
        async with db_manager.get_session() as db:
            result = await db.execute(
                select(Order).where(Order.id == event.order_id)
            )
            order = result.scalar_one_or_none()

            if order:
                order.status = "failed"
                await db.commit()
                logger.info(f"Order {event.order_id} marked as FAILED (saga compensation complete)")
            else:
                logger.error(f"Order {event.order_id} not found for status update")

    except Exception as e:
        logger.error(f"Error processing PaymentFailed event: {e}")
        raise


async def start_consumer():
    """Start consumer for PaymentFailed events"""
    global rabbitmq_client

    consumer = BaseConsumer(
        queue_name=ORDER_PAYMENT_FAILED_QUEUE,
        rabbitmq_client=rabbitmq_client
    )

    logger.info("OrderService saga consumer started (PaymentFailed)")
    await consumer.start(process_payment_failed)


# ==================== Lifecycle Management ====================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle"""
    global rabbitmq_client, db_manager, consumer_task

    logger.info("Starting OrderService...")

    # Initialize database
    db_manager = DatabaseManager()
    set_db_manager(db_manager)  # Set global instance for get_db() dependency
    await db_manager.create_tables()

    # Initialize RabbitMQ
    rabbitmq_client = RabbitMQClient(
        host=RABBITMQ_HOST,
        user=RABBITMQ_USER,
        password=RABBITMQ_PASSWORD
    )
    await rabbitmq_client.connect()

    # Declare queues
    await rabbitmq_client.declare_queue("order_created_queue", durable=True)

    # Declare fanout exchange for PaymentFailed events and bind our dedicated queue
    await rabbitmq_client.declare_exchange(
        PAYMENT_FAILED_EXCHANGE,
        ExchangeType.FANOUT,
        durable=True
    )
    await rabbitmq_client.declare_queue(ORDER_PAYMENT_FAILED_QUEUE, durable=True)
    await rabbitmq_client.bind_queue_to_exchange(
        ORDER_PAYMENT_FAILED_QUEUE,
        PAYMENT_FAILED_EXCHANGE,
        routing_key=""
    )
    logger.info(f"Queue '{ORDER_PAYMENT_FAILED_QUEUE}' bound to '{PAYMENT_FAILED_EXCHANGE}' exchange")

    # Start consumer
    consumer_task = asyncio.create_task(start_consumer())

    yield

    logger.info("Shutting down OrderService...")
    if consumer_task:
        consumer_task.cancel()
        try:
            await consumer_task
        except asyncio.CancelledError:
            pass

    if rabbitmq_client:
        await rabbitmq_client.disconnect()
    if db_manager:
        await db_manager.close()


# FastAPI application
app = FastAPI(
    title="OrderService",
    version="1.0.0",
    description="Async order service with saga choreography (Scenario 5)",
    lifespan=lifespan
)

Instrumentator().instrument(app).expose(app)


# ==================== API Endpoints ====================

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "service": "orderservice",
        "architecture": "async",
        "rabbitmq_connected": rabbitmq_client is not None and rabbitmq_client.connection is not None
    }


@app.get("/")
async def root():
    return {
        "service": "OrderService",
        "version": "1.0.0",
        "architecture": "Event-Driven (Async)",
        "scenario": "5 - Choreography Saga Pattern",
        "description": "Creates orders and orchestrates saga with event-driven compensation"
    }


@app.post("/create_order", status_code=202, response_model=OrderResponse)
async def create_order(
    order_request: OrderRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Scenario 5: Choreography Saga Pattern (Async)

    Creates an order and publishes OrderCreated event to start saga.
    Returns 202 Accepted immediately. Saga will fail due to payment failure,
    demonstrating choreography-based compensation.

    Saga flow:
    1. OrderService creates order (pending) → publishes OrderCreated
    2. InventoryService reserves stock → publishes StockReserved
    3. PaymentService fails payment → publishes PaymentFailed
    4. InventoryService releases stock (compensation)
    5. OrderService updates order to failed (compensation)
    """
    try:
        # Create order with pending status
        new_order = Order(
            product_id=order_request.product_id,
            quantity=order_request.quantity,
            status="pending"
        )
        db.add(new_order)
        await db.commit()
        await db.refresh(new_order)

        logger.info(f"Order {new_order.id} created (status: pending)")

        # Publish OrderCreated event to start saga
        event = OrderCreatedEvent(
            order_id=new_order.id,
            product_id=order_request.product_id,
            quantity=order_request.quantity,
            timestamp=datetime.utcnow()
        )

        await rabbitmq_client.publish_message(
            exchange_name="",
            routing_key="order_created_queue",
            message_body=event_to_json(event)
        )

        logger.info(f"OrderCreated event published for order {new_order.id} (saga initiated)")

        return OrderResponse(
            id=new_order.id,
            product_id=new_order.product_id,
            quantity=new_order.quantity,
            status=new_order.status
        )

    except Exception as e:
        logger.error(f"Error creating order: {e}")
        raise


@app.get("/orders/{order_id}", response_model=OrderResponse)
async def get_order(order_id: int, db: AsyncSession = Depends(get_db)):
    """Get order by ID (for verifying saga completion)"""
    result = await db.execute(
        select(Order).where(Order.id == order_id)
    )
    order = result.scalar_one_or_none()

    if not order:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Order not found")

    return OrderResponse(
        id=order.id,
        product_id=order.product_id,
        quantity=order.quantity,
        status=order.status
    )
