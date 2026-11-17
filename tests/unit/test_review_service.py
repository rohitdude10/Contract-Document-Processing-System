
import pytest

from app.services.review_service import calculate_progress


@pytest.mark.parametrize(
    "reviewed,total,expected",
    [
        (0, 0, 0.0),
        (0, 10, 0.0),
        (5, 10, 50.0),
        (7, 12, 58.33),
        (10, 10, 100.0),
        (1, 3, 33.33),
    ],
)
def test_calculate_progress(reviewed, total, expected):
    assert calculate_progress(reviewed, total) == expected
