from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, Tuple

from .settings import settings


def _cents_to_decimal(cents: int) -> Decimal:
    return (Decimal(cents) / Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def calculate_subtotals(
    follows: int,
    likes: int,
    views: int,
    comments: int,
) -> Tuple[Dict[str, int], int, Dict[str, int]]:
    unit_prices = {
        "follows": settings.PRICE_FOLLOW_CENTS,
        "likes": settings.PRICE_LIKE_CENTS,
        "views": settings.PRICE_VIEW_CENTS,
        "comments": settings.PRICE_COMMENT_CENTS,
    }

    subtotals = {
        "follows": follows * unit_prices["follows"],
        "likes": likes * unit_prices["likes"],
        "views": views * unit_prices["views"],
        "comments": comments * unit_prices["comments"],
    }
    total = sum(subtotals.values())
    return subtotals, total, unit_prices


def totals_for_mp(subtotals_cents: Dict[str, int]) -> Dict[str, Decimal]:
    return {key: _cents_to_decimal(value) for key, value in subtotals_cents.items()}


def total_for_mp(amount_cents: int) -> Decimal:
    return _cents_to_decimal(amount_cents)
