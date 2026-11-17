
import pytest

from app.services.tracking_service import percentage


@pytest.mark.parametrize(
    "completed,total,expected",
    [
        (0, 0, 0.0),
        (0, 10, 0.0),
        (5, 10, 50.0),
        (7, 10, 70.0),
        (10, 10, 100.0),
        (1, 3, 33.33),
    ],
)
def test_percentage(completed, total, expected):
    assert percentage(completed, total) == expected

