
import random
from datetime import date, timedelta
from typing import Callable


def generate_date() -> str:
    start = date(2024, 1, 1)
    end = date(2028, 12, 31)
    days = (end - start).days

    return (start + timedelta(days=random.randint(0, days))).isoformat()


def generate_expiry_date() -> str:
    start = date(2027, 1, 1)
    end = date(2035, 12, 31)
    days = (end - start).days

    return (start + timedelta(days=random.randint(0, days))).isoformat()


def generate_governing_law() -> str:
    return random.choice([
        "Laws of India",
        "Laws of England and Wales",
        "Laws of the State of California",
        "Laws of Singapore",
        "Laws of New York",
    ])


def generate_termination_clause() -> str:
    return random.choice([
        "Either party may terminate this agreement with 30 days written notice.",
        "Either party may terminate this agreement with 60 days written notice.",
        "The agreement may be terminated by mutual written consent.",
        "The agreement may be terminated in case of a material breach.",
    ])


def generate_security_deposit() -> str:
    return f"INR {random.choice([50000, 100000, 150000, 200000, 250000])}"


def generate_monthly_rent() -> str:
    return f"INR {random.choice([15000, 20000, 25000, 30000, 40000, 50000])}"


def generate_maintenance_charges() -> str:
    return f"INR {random.choice([1000, 1500, 2000, 2500, 3000])}"


def generate_notice_period() -> str:
    return random.choice(["15 days", "30 days", "45 days", "60 days", "90 days"])


def generate_generic_value() -> str:
    return random.choice([
        "As specified in the agreement.",
        "Applicable as mutually agreed by both parties.",
        "INR 100000",
        "30 days",
        "Subject to applicable laws.",
    ])


VARIABLE_GENERATORS: dict[str, Callable[[], str]] = {
    "effective_date": generate_date,
    "expiry_date": generate_expiry_date,
    "governing_law": generate_governing_law,
    "termination_clause": generate_termination_clause,
    "security_deposit": generate_security_deposit,
    "monthly_rent": generate_monthly_rent,
    "maintenance_charges": generate_maintenance_charges,
    "notice_period": generate_notice_period,
}


def generate_value(variable_name: str) -> str:
    generator = VARIABLE_GENERATORS.get(
        variable_name.strip().lower(),
        generate_generic_value,
    )

    return generator()
