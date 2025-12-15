"""
UserService - Scenario 1: Decoupling Non-Critical Tasks
HTTP endpoint that registers users and publishes UserRegistered events asynchronously.
"""

import asyncio
import logging
import os
import sys
from contextlib import asynccontextmanager
from datetime import datetime

# Add common module to path
sys.path.append('/app/common')

from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel, EmailStr
from sqlalchemy import Column, Integer, String, select
from sqlalchemy.ext.asyncio import AsyncSession
from prometheus_fastapi_instrumentator import Instrumentator

from database import DatabaseManager, Base, get_db
from rabbitmq_client import RabbitMQClient
from event_schemas import UserRegisteredEvent, event_to_json

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
db_manager: DatabaseManager = None


# ==================== Database Models ====================

class User(Base):
    """User database model"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)


# ==================== Pydantic Models ====================

class UserRegistration(BaseModel):
    """Request model for user registration"""
    email: EmailStr


class UserResponse(BaseModel):
    """Response model for user registration"""
    id: int
    email: str
    message: str
    event_published: bool


# ==================== Lifecycle Management ====================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage application lifecycle: initialize DB and RabbitMQ on startup.
    """
    global rabbitmq_client, db_manager

    # Startup
    logger.info("Starting UserService...")

    # Initialize database
    db_manager = DatabaseManager()
    await db_manager.create_tables()
    logger.info("Database tables created")

    # Initialize RabbitMQ
    rabbitmq_client = RabbitMQClient(
        host=RABBITMQ_HOST,
        user=RABBITMQ_USER,
        password=RABBITMQ_PASSWORD
    )
    await rabbitmq_client.connect()

    # Declare queue for UserRegistered events
    await rabbitmq_client.declare_queue("user_registered_queue", durable=True)
    logger.info("RabbitMQ connection established")

    yield

    # Shutdown
    logger.info("Shutting down UserService...")
    if rabbitmq_client:
        await rabbitmq_client.disconnect()
    if db_manager:
        await db_manager.close()


# FastAPI application
app = FastAPI(
    title="UserService",
    version="1.0.0",
    description="Async event-driven user registration service (Scenario 1)",
    lifespan=lifespan
)

# Prometheus metrics instrumentation
Instrumentator().instrument(app).expose(app)


# ==================== Helper Functions ====================

async def get_db_session() -> AsyncSession:
    """
    Dependency to get database session.
    """
    async with db_manager.get_session() as session:
        yield session


# ==================== API Endpoints ====================

@app.get("/health")
async def health():
    """
    Health check endpoint.
    """
    return {
        "status": "healthy",
        "service": "userservice",
        "architecture": "async",
        "timestamp": datetime.utcnow().isoformat(),
        "rabbitmq_connected": rabbitmq_client is not None and rabbitmq_client.connection is not None
    }


@app.get("/")
async def root():
    """
    Root endpoint with service information.
    """
    return {
        "service": "UserService",
        "version": "1.0.0",
        "architecture": "Event-Driven (Async)",
        "scenario": "1 - Decoupling Non-Critical Tasks",
        "description": "Registers users and publishes UserRegistered events for async email processing"
    }


@app.post("/register", status_code=202, response_model=UserResponse)
async def register_user(
    user_data: UserRegistration,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Scenario 1: Non-Critical Task Decoupling (Async)

    Registers a user and publishes UserRegistered event to RabbitMQ.
    Returns 202 Accepted immediately without waiting for email to be sent.

    Args:
        user_data: User registration data (email)
        db: Database session

    Returns:
        User information with confirmation that event was published
    """
    try:
        logger.info(f"Registering user with email: {user_data.email}")

        # Check if user already exists
        result = await db.execute(
            select(User).where(User.email == user_data.email)
        )
        existing_user = result.scalar_one_or_none()

        if existing_user:
            raise HTTPException(status_code=400, detail="Email already registered")

        # Save user to database
        new_user = User(email=user_data.email)
        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)

        logger.info(f"User {new_user.id} created successfully")

        # Publish UserRegistered event to RabbitMQ
        event = UserRegisteredEvent(
            user_id=new_user.id,
            email=user_data.email,
            timestamp=datetime.utcnow()
        )

        await rabbitmq_client.publish_message(
            exchange_name="",  # Default exchange
            routing_key="user_registered_queue",
            message_body=event_to_json(event)
        )

        logger.info(f"UserRegistered event published for user {new_user.id}")

        # Return immediately (202 Accepted)
        return UserResponse(
            id=new_user.id,
            email=new_user.email,
            message="User registered successfully. Welcome email will be sent shortly.",
            event_published=True
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error registering user: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.get("/users/{user_id}")
async def get_user(user_id: int, db: AsyncSession = Depends(get_db_session)):
    """
    Get user by ID.

    Args:
        user_id: User ID
        db: Database session

    Returns:
        User information
    """
    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return {
        "id": user.id,
        "email": user.email
    }


@app.get("/users")
async def list_users(db: AsyncSession = Depends(get_db_session)):
    """
    List all users.

    Args:
        db: Database session

    Returns:
        List of users
    """
    result = await db.execute(select(User))
    users = result.scalars().all()

    return {
        "users": [{"id": user.id, "email": user.email} for user in users],
        "count": len(users)
    }
