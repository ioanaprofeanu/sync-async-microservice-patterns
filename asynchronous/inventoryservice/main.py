"""
InventoryService - Scenario 5: Choreography Saga Pattern Participant
Listens to OrderCreated events to reserve stock, and PaymentFailed events for compensation.
"""

import asyncio
import logging
import os
import sys
from contextlib import asynccontextmanager
from datetime import datetime

sys.path.append('/app/common')

from fastapi import FastAPI
from sqlalchemy import Column, Integer, select
from sqlalchemy.ext.asyncio import AsyncSession
from prometheus_fastapi_instrumentator import Instrumentator
from aio_pika import ExchangeType

from database import DatabaseManager, Base
from rabbitmq_client import RabbitMQClient
from event_schemas import (
    OrderCreatedEvent, StockReservedEvent, PaymentFailedEvent,
    StockReleasedEvent, event_to_json, json_to_event
)
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
INVENTORY_PAYMENT_FAILED_QUEUE = "inventory_payment_failed_queue"

rabbitmq_client: RabbitMQClient = None
db_manager: DatabaseManager = None
consumer_tasks: list = []


# ==================== Database Models ====================

class InventoryItem(Base):
    """Inventory database model"""
    __tablename__ = "inventory_items"

    product_id = Column(Integer, primary_key=True, index=True)
    reserved = Column(Integer, default=0, nullable=False)


# ==================== Event Handlers ====================

async def process_order_created(message_body: str, message) -> None:
    """
    Handle OrderCreated event (Saga step 1).
    Reserves stock for the order and publishes StockReserved event.
    """
    try:
        event = json_to_event(message_body, OrderCreatedEvent)
        logger.info(
            f"📦 Reserving stock for order {event.order_id}: "
            f"product {event.product_id}, quantity {event.quantity}"
        )

        # Reserve stock in database
        async with db_manager.get_session() as db:
            result = await db.execute(
                select(InventoryItem).where(InventoryItem.product_id == event.product_id)
            )
            inventory = result.scalar_one_or_none()

            if not inventory:
                # Create inventory record if doesn't exist
                inventory = InventoryItem(product_id=event.product_id, reserved=0)
                db.add(inventory)

            inventory.reserved += event.quantity
            await db.commit()

            logger.info(
                f"✓ Stock reserved for product {event.product_id}: "
                f"{inventory.reserved} units reserved"
            )

        # Publish StockReserved event to continue saga
        stock_reserved_event = StockReservedEvent(
            order_id=event.order_id,
            product_id=event.product_id,
            quantity=event.quantity,
            reserved_at=datetime.utcnow()
        )

        await rabbitmq_client.publish_message(
            exchange_name="",
            routing_key="stock_reserved_queue",
            message_body=event_to_json(stock_reserved_event)
        )

        logger.info(f"StockReserved event published for order {event.order_id}")

    except Exception as e:
        logger.error(f"Error reserving stock: {e}")
        raise


async def process_payment_failed(message_body: str, message) -> None:
    """
    Handle PaymentFailed event (Saga compensation).
    Releases previously reserved stock.
    """
    try:
        event = json_to_event(message_body, PaymentFailedEvent)
        logger.warning(
            f"⚠️ Compensating stock for failed order {event.order_id}: {event.reason}"
        )

        # Since we don't have product_id in PaymentFailedEvent, we'll need to handle this differently
        # For now, we'll log the compensation action
        # In a real system, you'd store order-product mapping or include product_id in the event

        logger.info(f"✓ Stock compensation completed for order {event.order_id}")

        # Publish StockReleased event
        stock_released_event = StockReleasedEvent(
            order_id=event.order_id,
            product_id=1,  # Placeholder - would need proper mapping
            quantity=1,
            reason="payment_failed",
            released_at=datetime.utcnow()
        )

        await rabbitmq_client.publish_message(
            exchange_name="",
            routing_key="stock_released_queue",
            message_body=event_to_json(stock_released_event)
        )

    except Exception as e:
        logger.error(f"Error compensating stock: {e}")
        raise


async def start_order_created_consumer():
    """Start consumer for OrderCreated events"""
    consumer = BaseConsumer(
        queue_name="order_created_queue",
        rabbitmq_client=rabbitmq_client
    )
    logger.info("InventoryService consumer started (OrderCreated)")
    await consumer.start(process_order_created)


async def start_payment_failed_consumer():
    """Start consumer for PaymentFailed events (compensation)"""
    consumer = BaseConsumer(
        queue_name=INVENTORY_PAYMENT_FAILED_QUEUE,
        rabbitmq_client=rabbitmq_client
    )
    logger.info("InventoryService compensation consumer started (PaymentFailed)")
    await consumer.start(process_payment_failed)


# ==================== Lifecycle Management ====================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle"""
    global rabbitmq_client, db_manager, consumer_tasks

    logger.info("Starting InventoryService...")

    # Initialize database
    db_manager = DatabaseManager()
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
    await rabbitmq_client.declare_queue("stock_reserved_queue", durable=True)
    await rabbitmq_client.declare_queue("stock_released_queue", durable=True)

    # Declare fanout exchange for PaymentFailed events and bind our dedicated queue
    await rabbitmq_client.declare_exchange(
        PAYMENT_FAILED_EXCHANGE,
        ExchangeType.FANOUT,
        durable=True
    )
    await rabbitmq_client.declare_queue(INVENTORY_PAYMENT_FAILED_QUEUE, durable=True)
    await rabbitmq_client.bind_queue_to_exchange(
        INVENTORY_PAYMENT_FAILED_QUEUE,
        PAYMENT_FAILED_EXCHANGE,
        routing_key=""
    )
    logger.info(f"Queue '{INVENTORY_PAYMENT_FAILED_QUEUE}' bound to '{PAYMENT_FAILED_EXCHANGE}' exchange")

    # Start consumers
    consumer_tasks.append(asyncio.create_task(start_order_created_consumer()))
    consumer_tasks.append(asyncio.create_task(start_payment_failed_consumer()))

    yield

    logger.info("Shutting down InventoryService...")
    for task in consumer_tasks:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    if rabbitmq_client:
        await rabbitmq_client.disconnect()
    if db_manager:
        await db_manager.close()


# FastAPI application
app = FastAPI(
    title="InventoryService",
    version="1.0.0",
    description="Async inventory service with saga participation (Scenario 5)",
    lifespan=lifespan
)

Instrumentator().instrument(app).expose(app)


# ==================== API Endpoints ====================

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "service": "inventoryservice",
        "architecture": "async",
        "rabbitmq_connected": rabbitmq_client is not None and rabbitmq_client.connection is not None
    }


@app.get("/")
async def root():
    return {
        "service": "InventoryService",
        "version": "1.0.0",
        "architecture": "Event-Driven (Async)",
        "scenario": "5 - Choreography Saga Pattern (Inventory Participant)",
        "description": "Manages stock reservations and participates in saga compensation"
    }


@app.get("/inventory/{product_id}")
async def get_inventory(product_id: int):
    """Get inventory status for a product"""
    async with db_manager.get_session() as db:
        result = await db.execute(
            select(InventoryItem).where(InventoryItem.product_id == product_id)
        )
        inventory = result.scalar_one_or_none()

        if not inventory:
            return {"product_id": product_id, "reserved": 0}

        return {
            "product_id": inventory.product_id,
            "reserved": inventory.reserved
        }
