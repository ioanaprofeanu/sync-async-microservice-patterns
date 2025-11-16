from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
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

app = FastAPI(title="InventoryService", version="1.0.0")

# Prometheus metrics instrumentation
Instrumentator().instrument(app).expose(app)

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://dbuser:dbpass@postgres:5432/microservices_db")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# InventoryItem model
class InventoryItem(Base):
    __tablename__ = "inventory_items"

    product_id = Column(Integer, primary_key=True, index=True)
    reserved = Column(Integer, default=0, nullable=False)


# Create tables and seed data
Base.metadata.create_all(bind=engine)

# Seed initial inventory if table is empty
db = SessionLocal()
try:
    if db.query(InventoryItem).count() == 0:
        logger.info("Seeding initial inventory...")
        initial_inventory = [
            InventoryItem(product_id=1, reserved=0),
            InventoryItem(product_id=2, reserved=0),
            InventoryItem(product_id=3, reserved=0),
        ]
        db.add_all(initial_inventory)
        db.commit()
        logger.info("Initial inventory seeded successfully")
except Exception as e:
    logger.error(f"Error seeding inventory: {str(e)}")
    db.rollback()
finally:
    db.close()


class StockReservationRequest(BaseModel):
    product_id: int
    quantity: int = 1


class CompensationRequest(BaseModel):
    product_id: int
    quantity: int = 1


@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "inventoryservice",
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/inventory")
def get_inventory():
    """Get all inventory items"""
    db = SessionLocal()
    try:
        items = db.query(InventoryItem).all()
        return {
            "inventory": [
                {"product_id": item.product_id, "reserved": item.reserved}
                for item in items
            ],
            "count": len(items)
        }
    finally:
        db.close()


@app.post("/reserve_stock")
def reserve_stock(request: StockReservationRequest):
    """
    Scenario 5: Saga Pattern - Reserve stock for an order
    """
    db = SessionLocal()
    try:
        logger.info(f"Reserving {request.quantity} units of product {request.product_id}")

        # Find inventory item
        inventory = db.query(InventoryItem).filter(
            InventoryItem.product_id == request.product_id
        ).first()

        if not inventory:
            # Create inventory item if it doesn't exist
            inventory = InventoryItem(product_id=request.product_id, reserved=0)
            db.add(inventory)

        # Reserve stock
        inventory.reserved += request.quantity
        db.commit()
        db.refresh(inventory)

        logger.info(f"Stock reserved successfully. Product {request.product_id}: {inventory.reserved} reserved")

        return {
            "status": "ok",
            "product_id": request.product_id,
            "quantity": request.quantity,
            "total_reserved": inventory.reserved,
            "message": "Stock reserved successfully",
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        db.rollback()
        logger.error(f"Error reserving stock: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@app.post("/compensate_stock")
def compensate_stock(request: CompensationRequest):
    """
    Scenario 5: Saga Pattern - Compensate (undo) stock reservation
    This is called when a later step in the saga fails (e.g., payment failure)
    """
    db = SessionLocal()
    try:
        logger.info(f"Compensating {request.quantity} units of product {request.product_id}")

        # Find inventory item
        inventory = db.query(InventoryItem).filter(
            InventoryItem.product_id == request.product_id
        ).first()

        if not inventory:
            raise HTTPException(status_code=404, detail="Inventory item not found")

        # Compensate (unreserve) stock
        inventory.reserved -= request.quantity
        if inventory.reserved < 0:
            inventory.reserved = 0

        db.commit()
        db.refresh(inventory)

        logger.info(f"Stock compensation completed. Product {request.product_id}: {inventory.reserved} reserved")

        return {
            "status": "ok",
            "product_id": request.product_id,
            "quantity": request.quantity,
            "total_reserved": inventory.reserved,
            "message": "Stock compensation completed successfully",
            "timestamp": datetime.utcnow().isoformat()
        }

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error compensating stock: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
