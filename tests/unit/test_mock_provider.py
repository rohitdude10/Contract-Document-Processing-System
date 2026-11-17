
import pytest

from app.services.extraction.mock_provider import (
    MockExtractionProvider,
    TransientExtractionError,
)


@pytest.fixture
def document_file(tmp_path):
    file_path = tmp_path / "contract.txt"
    file_path.write_text(
        "This is a sample contract document.",
        encoding="utf-8",
    )
    return file_path


@pytest.mark.asyncio
async def test_extract_returns_all_requested_variables(document_file):
    provider = MockExtractionProvider(
        min_latency=0,
        max_latency=0,
        failure_rate=0,
    )

    variables = [
        "effective_date",
        "governing_law",
        "monthly_rent",
    ]

    findings = await provider.extract(document_file, variables)

    assert len(findings) == len(variables)
    assert [f.variable_name for f in findings] == variables

    for finding in findings:
        assert finding.extracted_value
        assert isinstance(finding.extracted_value, str)


@pytest.mark.asyncio
async def test_extract_supports_unknown_variables(document_file):
    provider = MockExtractionProvider(
        min_latency=0,
        max_latency=0,
        failure_rate=0,
    )

    findings = await provider.extract(
        document_file,
        ["custom_contract_variable"],
    )

    assert len(findings) == 1
    assert findings[0].variable_name == "custom_contract_variable"
    assert findings[0].extracted_value


@pytest.mark.asyncio
async def test_extract_returns_empty_list_for_no_variables(document_file):
    provider = MockExtractionProvider(
        min_latency=0,
        max_latency=0,
        failure_rate=0,
    )

    findings = await provider.extract(document_file, [])

    assert findings == []


@pytest.mark.asyncio
async def test_extract_raises_for_missing_document(tmp_path):
    provider = MockExtractionProvider(
        min_latency=0,
        max_latency=0,
        failure_rate=0,
    )

    with pytest.raises(FileNotFoundError):
        await provider.extract(
            tmp_path / "missing.pdf",
            ["effective_date"],
        )


@pytest.mark.asyncio
async def test_extract_simulates_failure(document_file):
    provider = MockExtractionProvider(
        min_latency=0,
        max_latency=0,
        failure_rate=1.0,
    )

    with pytest.raises(TransientExtractionError):
        await provider.extract(
            document_file,
            ["effective_date"],
        )


def test_invalid_failure_rate():
    with pytest.raises(ValueError):
        MockExtractionProvider(failure_rate=1.5)


def test_invalid_latency_configuration():
    with pytest.raises(ValueError):
        MockExtractionProvider(
            min_latency=5,
            max_latency=2,
        )
