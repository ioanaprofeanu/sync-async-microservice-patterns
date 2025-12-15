"""
ProductService - Scenario 3: Fan-Out Flow
HTTP endpoint that updates products and publishes ProductUpdated events to fanout exchange.
"""

import logging
import os
import sys
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional

# Add common module to path
sys.path.append('/app/common')

from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy import Column, Integer, String, select
from sqlalchemy.ext.asyncio import AsyncSession
from prometheus_fastapi_instrumentator import Instrumentator
from aio_pika import ExchangeType

from database import DatabaseManager, Base, get_db, set_db_manager
from rabbitmq_client import RabbitMQClient
from event_schemas import ProductUpdatedEvent, event_to_json

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

FANOUT_EXCHANGE = "product_updates"  # Fanout exchange for Scenario 3

# Global variables
rabbitmq_client: RabbitMQClient = None
db_manager: DatabaseManager = None


# ==================== Database Models ====================

class Product(Base):
    """Product database model"""
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    stock = Column(Integer, default=0)


# ==================== Pydantic Models ====================

class ProductCreate(BaseModel):
    """Request model for creating products"""
    name: str
    stock: int = 0


class ProductUpdate(BaseModel):
    """Request model for updating products"""
    name: Optional[str] = None
    stock: Optional[int] = None


class ProductResponse(BaseModel):
    """Response model for product operations"""
    id: int
    name: str
    stock: int
    event_published: bool = False


# ==================== Lifecycle Management ====================

async def seed_products():
    """Seed initial products if they don't exist (for testing)"""
    async with db_manager.get_session() as db:
        for product_id in range(1, 4):  # Products 1-3
            result = await db.execute(
                select(Product).where(Product.id == product_id)
            )
            if result.scalar_one_or_none() is None:
                product = Product(id=product_id, name=f"Product {product_id}", stock=100)
                db.add(product)
                logger.info(f"Seeded product {product_id}")
        await db.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle"""
    global rabbitmq_client, db_manager

    # Startup
    logger.info("Starting ProductService...")

    # Initialize database
    db_manager = DatabaseManager()
    set_db_manager(db_manager)  # Set global instance for get_db() dependency
    await db_manager.create_tables()

    # Seed products for testing
    await seed_products()

    # Initialize RabbitMQ
    rabbitmq_client = RabbitMQClient(
        host=RABBITMQ_HOST,
        user=RABBITMQ_USER,
        password=RABBITMQ_PASSWORD
    )
    await rabbitmq_client.connect()

    # Declare fanout exchange for product updates
    await rabbitmq_client.declare_exchange(
        FANOUT_EXCHANGE,
        ExchangeType.FANOUT,
        durable=True
    )
    logger.info(f"Fanout exchange '{FANOUT_EXCHANGE}' declared")

    yield

    # Shutdown
    logger.info("Shutting down ProductService...")
    if rabbitmq_client:
        await rabbitmq_client.disconnect()
    if db_manager:
        await db_manager.close()


# FastAPI application
app = FastAPI(
    title="ProductService",
    version="1.0.0",
    description="Async product management service with fanout pattern (Scenario 3)",
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
        "service": "productservice",
        "architecture": "async",
        "timestamp": datetime.utcnow().isoformat(),
        "rabbitmq_connected": rabbitmq_client is not None and rabbitmq_client.connection is not None
    }


@app.get("/")
async def root():
    """Root endpoint with service information"""
    return {
        "service": "ProductService",
        "version": "1.0.0",
        "architecture": "Event-Driven (Async)",
        "scenario": "3 - Fan-Out Flow",
        "description": "Manages products and publishes updates to fanout exchange for parallel processing"
    }


@app.post("/products", status_code=201, response_model=ProductResponse)
async def create_product(
    product: ProductCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new product"""
    new_product = Product(name=product.name, stock=product.stock)
    db.add(new_product)
    await db.commit()
    await db.refresh(new_product)

    logger.info(f"Product {new_product.id} created: {new_product.name}")

    return ProductResponse(
        id=new_product.id,
        name=new_product.name,
        stock=new_product.stock
    )


@app.put("/products/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: int,
    product_update: ProductUpdate,
    db: AsyncSession = Depends(get_db)
):
    """
    Scenario 3: Fan-Out Flow (Async)

    Updates product and publishes ProductUpdated event to fanout exchange.
    Multiple services (SearchService, CacheService, AnalyticsService) will receive
    the event simultaneously and process it in parallel.

    Args:
        product_id: Product ID to update
        product_update: Updated product data
        db: Database session

    Returns:
        Updated product information
    """
    try:
        # Fetch product
        result = await db.execute(
            select(Product).where(Product.id == product_id)
        )
        product = result.scalar_one_or_none()

        if not product:
            raise HTTPException(status_code=404, detail="Product not found")

        # Update product fields
        if product_update.name is not None:
            product.name = product_update.name
        if product_update.stock is not None:
            product.stock = product_update.stock

        await db.commit()
        await db.refresh(product)

        logger.info(f"Product {product_id} updated: {product.name} (stock: {product.stock})")

        # Publish ProductUpdated event to FANOUT exchange
        event = ProductUpdatedEvent(
            product_id=product.id,
            name=product.name,
            stock=product.stock,
            timestamp=datetime.utcnow()
        )

        await rabbitmq_client.publish_message(
            exchange_name=FANOUT_EXCHANGE,
            routing_key="",  # Empty routing key for fanout
            message_body=event_to_json(event),
            exchange_type=ExchangeType.FANOUT
        )

        logger.info(f"ProductUpdated event published to fanout exchange for product {product_id}")

        return ProductResponse(
            id=product.id,
            name=product.name,
            stock=product.stock,
            event_published=True
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating product: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.get("/products/{product_id}", response_model=ProductResponse)
async def get_product(product_id: int, db: AsyncSession = Depends(get_db)):
    """Get product by ID"""
    result = await db.execute(
        select(Product).where(Product.id == product_id)
    )
    product = result.scalar_one_or_none()

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    return ProductResponse(
        id=product.id,
        name=product.name,
        stock=product.stock
    )


@app.get("/products")
async def list_products(db: AsyncSession = Depends(get_db)):
    """List all products"""
    result = await db.execute(select(Product))
    products = result.scalars().all()

    return {
        "products": [
            {"id": p.id, "name": p.name, "stock": p.stock}
            for p in products
        ],
        "count": len(products)
    }
