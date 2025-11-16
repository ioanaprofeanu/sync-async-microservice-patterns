from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import requests
import logging
import os
from datetime import datetime
from prometheus_fastapi_instrumentator import Instrumentator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(title="OrderService", version="1.0.0")

# Prometheus metrics instrumentation
Instrumentator().instrument(app).expose(app)

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://dbuser:dbpass@postgres:5432/microservices_db")
INVENTORY_SERVICE_URL = os.getenv("INVENTORY_SERVICE_URL", "http://inventoryservice:8000")
PAYMENT_SERVICE_URL = os.getenv("PAYMENT_SERVICE_URL", "http://paymentservice:8000")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# Order model
class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, nullable=False)
    quantity = Column(Integer, default=1, nullable=False)
    status = Column(String, default="pending", nullable=False)  # pending, completed, failed


# Create tables
Base.metadata.create_all(bind=engine)


class OrderRequest(BaseModel):
    product_id: int
    quantity: int = 1


@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "orderservice",
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/orders")
def get_orders():
    """Get all orders"""
    db = SessionLocal()
    try:
        orders = db.query(Order).all()
        return {
            "orders": [
                {
                    "id": order.id,
                    "product_id": order.product_id,
                    "quantity": order.quantity,
                    "status": order.status
                }
                for order in orders
            ],
            "count": len(orders)
        }
    finally:
        db.close()


@app.post("/create_order", status_code=400)
def create_order(order_request: OrderRequest):
    """
    Scenario 5: Choreography and Compensation (Saga Pattern)

    This endpoint demonstrates manual compensation logic in a synchronous architecture:
    1. Create order with status "pending"
    2. Call InventoryService to reserve stock (succeeds)
    3. Call PaymentService to process payment (fails intentionally)
    4. Execute compensation: call InventoryService to unreserve stock
    5. Update order status to "failed"
    6. Return error to client
    """
    db = SessionLocal()
    stock_reserved = False
    order = None

    try:
        logger.info(f"Creating order for product {order_request.product_id}, quantity {order_request.quantity}")

        # Step 1: Create order with pending status
        order = Order(
            product_id=order_request.product_id,
            quantity=order_request.quantity,
            status="pending"
        )
        db.add(order)
        db.commit()
        db.refresh(order)

        logger.info(f"Order {order.id} created with status 'pending'")

        # Step 2: Reserve stock in InventoryService
        try:
            logger.info(f"Calling InventoryService to reserve stock for order {order.id}")
            inventory_response = requests.post(
                f"{INVENTORY_SERVICE_URL}/reserve_stock",
                json={"product_id": order_request.product_id, "quantity": order_request.quantity},
                timeout=10
            )
            inventory_response.raise_for_status()
            stock_reserved = True
            logger.info(f"Stock reserved successfully: {inventory_response.json()}")
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to reserve stock: {str(e)}")
            order.status = "failed"
            db.commit()
            raise HTTPException(
                status_code=500,
                detail={
                    "message": "Order failed: could not reserve stock",
                    "order_id": order.id,
                    "reason": str(e)
                }
            )

        # Step 3: Process payment (this will fail intentionally)
        try:
            logger.info(f"Calling PaymentService to process payment for order {order.id}")
            payment_response = requests.post(
                f"{PAYMENT_SERVICE_URL}/process_payment_fail",
                json={
                    "order_id": order.id,
                    "product_id": order_request.product_id,
                    "quantity": order_request.quantity
                },
                timeout=10
            )
            payment_response.raise_for_status()
            logger.info(f"Payment processed successfully: {payment_response.json()}")

            # If we reach here, payment succeeded (won't happen with process_payment_fail)
            order.status = "completed"
            db.commit()

            return {
                "order_id": order.id,
                "status": "completed",
                "product_id": order_request.product_id,
                "quantity": order_request.quantity,
                "message": "Order created successfully"
            }

        except requests.exceptions.RequestException as e:
            # Payment failed - execute compensation logic
            logger.error(f"Payment failed for order {order.id}: {str(e)}")

            # Step 4: COMPENSATION - Unreserve the stock
            if stock_reserved:
                try:
                    logger.info(f"Executing compensation: unreserving stock for order {order.id}")
                    compensation_response = requests.post(
                        f"{INVENTORY_SERVICE_URL}/compensate_stock",
                        json={"product_id": order_request.product_id, "quantity": order_request.quantity},
                        timeout=10
                    )
                    compensation_response.raise_for_status()
                    logger.info(f"Stock compensation successful: {compensation_response.json()}")
                except requests.exceptions.RequestException as comp_error:
                    logger.error(f"CRITICAL: Compensation failed for order {order.id}: {str(comp_error)}")
                    # In a real system, this would need to be handled with retry logic or alerts

            # Update order status to failed
            order.status = "failed"
            db.commit()

            # Return error to client
            raise HTTPException(
                status_code=400,
                detail={
                    "message": "Order failed due to payment issue",
                    "order_id": order.id,
                    "product_id": order_request.product_id,
                    "reason": "Payment processing failed",
                    "compensation_executed": stock_reserved,
                    "timestamp": datetime.utcnow().isoformat()
                }
            )

    except HTTPException:
        raise
    except Exception as e:
        # Handle unexpected errors
        logger.error(f"Unexpected error creating order: {str(e)}")
        if order:
            order.status = "failed"
            db.commit()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
