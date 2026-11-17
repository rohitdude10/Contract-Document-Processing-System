
from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI

from app.config import settings
from app.api.routes.health import router as health_router

from app.core.database import close_database_connection
from app.core.messaging import (
    connect_rabbitmq,
    close_rabbitmq_connection,
)
from app.api.routes.batches import router as batches_router
from app.api.routes import tracking
from app.api.routes import reviews


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):

    logging.info("Starting Contract Processing API")

    # Establish RabbitMQ connection.
    # API startup should remain available if RabbitMQ is temporarily down.
    await connect_rabbitmq()

    yield

    logging.info("Shutting down Contract Processing API")

    await close_rabbitmq_connection()
    await close_database_connection()


app = FastAPI(
    title=settings.APP_NAME,
    description="Bulk contract document processing system",
    version="1.0.0",
    lifespan=lifespan,
)


app.include_router(health_router)
app.include_router(batches_router)
app.include_router(
    tracking.router,
    prefix="/api/v1",
)
app.include_router(
    reviews.router,
    prefix="/api/v1",
)

@app.get("/")
async def root():
    return {
        "message": "Contract Processing API is running",
        "environment": settings.APP_ENV,
    }

