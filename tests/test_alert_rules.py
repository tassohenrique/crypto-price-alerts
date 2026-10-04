from decimal import Decimal

import pytest

from app.models import AlertDirection
from app.services.alert import is_triggered

ABOVE = AlertDirection.ABOVE
BELOW = AlertDirection.BELOW


@pytest.mark.parametrize(
    ("direction", "price", "expected"),
    [
        (ABOVE, "100.01", True),
        (ABOVE, "100", True),
        (ABOVE, "99.99", False),
        (BELOW, "99.99", True),
        (BELOW, "100", True),
        (BELOW, "100.01", False),
    ],
)
def test_is_triggered(direction, price, expected):
    assert is_triggered(direction, Decimal(100), Decimal(price)) is expected
