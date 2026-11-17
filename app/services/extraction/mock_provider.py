
import asyncio
import random
from pathlib import Path

from app.config import settings
from app.services.extraction.base import ExtractionProvider
from app.services.extraction.generators import generate_value
from app.services.extraction.schemas import ExtractedFinding


class TransientExtractionError(Exception):
    """Represents a simulated temporary extraction failure."""


class MockExtractionProvider(ExtractionProvider):

    def __init__(
        self,
        min_latency: float | None = None,
        max_latency: float | None = None,
        failure_rate: float | None = None,
    ):
        self.min_latency = (
            min_latency
            if min_latency is not None
            else settings.MOCK_EXTRACTION_MIN_LATENCY_SECONDS
        )

        self.max_latency = (
            max_latency
            if max_latency is not None
            else settings.MOCK_EXTRACTION_MAX_LATENCY_SECONDS
        )

        self.failure_rate = (
            failure_rate
            if failure_rate is not None
            else settings.MOCK_EXTRACTION_FAILURE_RATE
        )

        if self.min_latency < 0:
            raise ValueError("Minimum latency cannot be negative")

        if self.max_latency < self.min_latency:
            raise ValueError("Maximum latency must be >= minimum latency")

        if not 0 <= self.failure_rate <= 1:
            raise ValueError("Failure rate must be between 0 and 1")

    async def extract(
        self,
        document_path: Path,
        requested_variables: list[str],
    ) -> list[ExtractedFinding]:

        if not document_path.is_file():
            raise FileNotFoundError(
                f"Document does not exist: {document_path}"
            )

        if not requested_variables:
            return []

        # Simulate external API processing latency.
        latency = random.uniform(
            self.min_latency,
            self.max_latency,
        )
        await asyncio.sleep(latency)

        # Simulate a temporary extraction API failure.
        if random.random() < self.failure_rate:
            raise TransientExtractionError(
                "Simulated temporary extraction service failure"
            )

        findings = []

        for variable_name in requested_variables:
            value = generate_value(variable_name)

            findings.append(
                ExtractedFinding(
                    variable_name=variable_name,
                    extracted_value=value,
                )
            )

        return findings
