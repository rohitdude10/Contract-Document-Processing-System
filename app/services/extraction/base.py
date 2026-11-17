
from abc import ABC, abstractmethod
from pathlib import Path

from app.services.extraction.schemas import ExtractedFinding


class ExtractionProvider(ABC):

    @abstractmethod
    async def extract(
        self,
        document_path: Path,
        requested_variables: list[str],
    ) -> list[ExtractedFinding]:
        """
        Extract requested variables from a document.

        Args:
            document_path: Path to the document.
            requested_variables: Variables to extract.

        Returns:
            One ExtractedFinding per requested variable.
        """
        raise NotImplementedError
