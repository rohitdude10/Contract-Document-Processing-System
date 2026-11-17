
from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.core.database import check_database_connection
from app.core.messaging import check_rabbitmq_connection


router = APIRouter()


@router.get("/health")
async def health_check():

    services = {
        "api": "healthy",
        "database": "unknown",
        "rabbitmq": "unknown",
    }

    # Check PostgreSQL
    try:
        await check_database_connection()
        services["database"] = "healthy"

    except Exception:
        services["database"] = "unhealthy"

    # Check RabbitMQ
    try:
        is_connected = await check_rabbitmq_connection()

        services["rabbitmq"] = (
            "healthy" if is_connected else "unhealthy"
        )

    except Exception:
        services["rabbitmq"] = "unhealthy"

    overall_status = (
        "healthy"
        if all(status == "healthy" for status in services.values())
        else "degraded"
    )

    response = {
        "status": overall_status,
        "services": services,
    }

    status_code = 200 if overall_status == "healthy" else 503

    return JSONResponse(
        status_code=status_code,
        content=response,
    )
