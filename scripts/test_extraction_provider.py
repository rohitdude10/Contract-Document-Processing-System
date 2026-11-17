import asyncio
from pathlib import Path

from app.services.extraction import MockExtractionProvider


async def main():
    provider = MockExtractionProvider(
        min_latency=1,
        max_latency=2,
        failure_rate=0,
    )

    document_path = Path("sample_contract.txt")

    findings = await provider.extract(
        document_path=document_path,
        requested_variables=[
            "effective_date",
            "expiry_date",
            "governing_law",
            "termination_clause",
            "monthly_rent",
            "security_deposit",
        ],
    )

    for finding in findings:
        print(f"{finding.variable_name}: {finding.extracted_value}")


if __name__ == "__main__":
    asyncio.run(main())