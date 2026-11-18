
import pytest


def next_retry_count(current_count: int) -> int:
    return current_count + 1


@pytest.mark.parametrize(
    "current,expected",
    [
        (0, 1),
        (1, 2),
        (2, 3),
    ],
)
def test_retry_count_increments(current, expected):
    assert next_retry_count(current) == expected
