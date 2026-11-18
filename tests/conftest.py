
import os

import pytest
import pytest_asyncio
from dotenv import dotenv_values, load_dotenv
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

# Load test configuration before importing application settings.
test_environment = dotenv_values(".env.test")
load_dotenv(".env.test")
os.environ["ENVIRONMENT"] = "test"

from app.core.database import get_db
from app.main import app
from app.models.base import Base

TEST_DATABASE_URL = (
    os.getenv("TEST_DATABASE_URL")
    or test_environment.get("DATABASE_URL")
)

test_engine = (
    create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        poolclass=NullPool,
    )
    if TEST_DATABASE_URL
    else None
)

TestSessionLocal = (
    async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    if test_engine is not None
    else None
)


@pytest_asyncio.fixture(scope="function")
async def db_session():
    if test_engine is None or TestSessionLocal is None:
        pytest.skip(
            "Set TEST_DATABASE_URL to run PostgreSQL integration tests."
        )

    """
    Creates a clean database schema for each test.

    This is simple and reliable for an assignment.
    For a larger suite, use transaction rollback fixtures
    or a disposable database per test worker.
    """
    async with test_engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
        await connection.run_sync(Base.metadata.create_all)

    async with TestSessionLocal() as session:
        yield session
        await session.rollback()

    async with test_engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def client(db_session):
    async def override_get_db():
        async with TestSessionLocal() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture
def temp_storage(tmp_path, monkeypatch):
    from app.config import settings

    upload_dir = tmp_path / "uploads"
    temp_dir = tmp_path / "temp"

    upload_dir.mkdir()
    temp_dir.mkdir()

    monkeypatch.setattr(settings, "UPLOAD_DIR", upload_dir)
    monkeypatch.setattr(settings, "TEMP_DIR", temp_dir)

    return {
        "root": tmp_path,
        "uploads": upload_dir,
        "temp": temp_dir,
    }


@pytest_asyncio.fixture
async def rabbitmq_connection():
    """
    Real RabbitMQ integration fixture.

    The test vhost must exist and be accessible.
    """
    import aio_pika

    from app.config import settings

    connection = await aio_pika.connect_robust(
        settings.RABBITMQ_URL
    )

    yield connection

    await connection.close()


@pytest.fixture
def worker_session_factory():
    if TestSessionLocal is None:
        pytest.skip(
            "Set TEST_DATABASE_URL to run PostgreSQL integration tests."
        )

    return TestSessionLocal


@pytest_asyncio.fixture
async def seeded_document(db_session, tmp_path, monkeypatch):
    from app.models.batch import Batch
    from app.models.document import Document
    from app.services.extraction.mock_provider import MockExtractionProvider
    from app.workers import tasks

    monkeypatch.setattr(tasks, "AsyncSessionLocal", TestSessionLocal)
    monkeypatch.setattr(
        tasks,
        "extraction_provider",
        MockExtractionProvider(
            min_latency=0,
            max_latency=0,
            failure_rate=0,
        ),
    )

    document_path = tmp_path / "contract.txt"
    document_path.write_text(
        "Effective date: 2026-01-01.",
        encoding="utf-8",
    )

    batch = Batch(
        original_filename="contract.zip",
        status="queued",
        total_documents=1,
        processed_documents=0,
        failed_documents=0,
        requested_variables=["effective_date"],
        upload_size=document_path.stat().st_size,
    )
    db_session.add(batch)
    await db_session.flush()

    document = Document(
        batch_id=batch.id,
        original_filename=document_path.name,
        stored_path=str(document_path),
        file_size=document_path.stat().st_size,
        mime_type="text/plain",
        status="queued",
        attempt_count=0,
    )
    db_session.add(document)
    await db_session.commit()

    return batch.id, document.id