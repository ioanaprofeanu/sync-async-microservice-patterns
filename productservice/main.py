from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import requests
import logging
import os
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(title="ProductService", version="1.0.0")

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://dbuser:dbpass@postgres:5432/microservices_db")
SEARCH_SERVICE_URL = os.getenv("SEARCH_SERVICE_URL", "http://searchservice:8000")
CACHE_SERVICE_URL = os.getenv("CACHE_SERVICE_URL", "http://cacheservice:8000")
ANALYTICS_SERVICE_URL = os.getenv("ANALYTICS_SERVICE_URL", "http://analyticsservice:8000")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# Product model
class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    stock = Column(Integer, default=0)


# Create tables and seed data
Base.metadata.create_all(bind=engine)

# Seed initial products if table is empty
db = SessionLocal()
try:
    if db.query(Product).count() == 0:
        logger.info("Seeding initial products...")
        initial_products = [
            Product(id=1, name="Laptop", stock=50),
            Product(id=2, name="Mouse", stock=100),
            Product(id=3, name="Keyboard", stock=75),
        ]
        db.add_all(initial_products)
        db.commit()
        logger.info("Initial products seeded successfully")
except Exception as e:
    logger.error(f"Error seeding products: {str(e)}")
    db.rollback()
finally:
    db.close()


class ProductUpdate(BaseModel):
    name: str = None
    stock: int = None


@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "productservice",
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/products")
def get_products():
    """Get all products"""
    db = SessionLocal()
    try:
        products = db.query(Product).all()
        return {
            "products": [
                {"id": p.id, "name": p.name, "stock": p.stock}
                for p in products
            ],
            "count": len(products)
        }
    finally:
        db.close()


@app.get("/products/{product_id}")
def get_product(product_id: int):
    """Get a specific product"""
    db = SessionLocal()
    try:
        product = db.query(Product).filter(Product.id == product_id).first()
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")

        return {
            "id": product.id,
            "name": product.name,
            "stock": product.stock
        }
    finally:
        db.close()


@app.put("/products/{product_id}")
def update_product(product_id: int, update_data: ProductUpdate):
    """
    Scenario 3: Fan-Out Flow
    Updates a product and sequentially calls SearchService, CacheService, and AnalyticsService
    """
    db = SessionLocal()
    try:
        logger.info(f"Updating product {product_id}")

        # Find product
        product = db.query(Product).filter(Product.id == product_id).first()
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")

        # Update product
        if update_data.name is not None:
            product.name = update_data.name
        if update_data.stock is not None:
            product.stock = update_data.stock

        db.commit()
        db.refresh(product)

        logger.info(f"Product {product_id} updated in database")

        # Sequential blocking calls to dependent services
        errors = []

        # Step 1: Call SearchService
        try:
            logger.info(f"Calling SearchService to reindex product {product_id}")
            search_response = requests.post(
                f"{SEARCH_SERVICE_URL}/reindex",
                json={"product_id": product_id},
                timeout=10
            )
            search_response.raise_for_status()
            logger.info(f"SearchService responded: {search_response.json()}")
        except requests.exceptions.RequestException as e:
            error_msg = f"SearchService call failed: {str(e)}"
            logger.error(error_msg)
            errors.append(error_msg)

        # Step 2: Call CacheService
        try:
            logger.info(f"Calling CacheService to invalidate cache for product {product_id}")
            cache_response = requests.post(
                f"{CACHE_SERVICE_URL}/invalidate_cache",
                json={"product_id": product_id},
                timeout=10
            )
            cache_response.raise_for_status()
            logger.info(f"CacheService responded: {cache_response.json()}")
        except requests.exceptions.RequestException as e:
            error_msg = f"CacheService call failed: {str(e)}"
            logger.error(error_msg)
            errors.append(error_msg)

        # Step 3: Call AnalyticsService
        try:
            logger.info(f"Calling AnalyticsService to log update for product {product_id}")
            analytics_response = requests.post(
                f"{ANALYTICS_SERVICE_URL}/log_update",
                json={"product_id": product_id},
                timeout=10
            )
            analytics_response.raise_for_status()
            logger.info(f"AnalyticsService responded: {analytics_response.json()}")
        except requests.exceptions.RequestException as e:
            error_msg = f"AnalyticsService call failed: {str(e)}"
            logger.error(error_msg)
            errors.append(error_msg)

        # Return response
        response = {
            "id": product.id,
            "name": product.name,
            "stock": product.stock,
            "message": "Product updated successfully",
            "timestamp": datetime.utcnow().isoformat()
        }

        if errors:
            response["warnings"] = errors

        return response

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating product: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
