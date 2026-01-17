from __future__ import annotations

import hmac
import logging
from dataclasses import dataclass
from hashlib import sha256
from typing import Any, Dict, Optional, Tuple

import mercadopago
from tenacity import retry, stop_after_attempt, wait_exponential_jitter

from .pricing import total_for_mp, totals_for_mp
from .settings import settings

logger = logging.getLogger(__name__)


class MPRequestError(RuntimeError):
    pass


@dataclass
class PaymentData:
    payment_id: str
    status: str
    status_detail: Optional[str]
    transaction_amount: float
    currency_id: str
    external_reference: Optional[str]
    raw: Dict[str, Any]


class MercadoPagoClient:
    def __init__(self, access_token: str) -> None:
        if not access_token:
            raise MPRequestError("MP_ACCESS_TOKEN not configured")
        self._sdk = mercadopago.SDK(access_token)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential_jitter(initial=1, max=5), reraise=True)
    def _request(self, method, *args, **kwargs):
        try:
            return method(*args, **kwargs)
        except Exception as exc:
            raise MPRequestError("Mercado Pago SDK request failed") from exc

    def create_preference(self, data: Dict[str, Any]) -> Dict[str, Any]:
        response = self._request(self._sdk.preference().create, data)
        if not response or "response" not in response:
            raise MPRequestError("Mercado Pago preference create failed")
        return response["response"]

    def get_payment(self, payment_id: str) -> PaymentData:
        response = self._request(self._sdk.payment().get, payment_id)
        if not response or "response" not in response:
            raise MPRequestError("Mercado Pago payment fetch failed")
        payment = response["response"]
        return PaymentData(
            payment_id=str(payment.get("id", "")),
            status=str(payment.get("status", "")),
            status_detail=payment.get("status_detail"),
            transaction_amount=float(payment.get("transaction_amount", 0.0)),
            currency_id=str(payment.get("currency_id", "")),
            external_reference=payment.get("external_reference"),
            raw=payment,
        )


def build_preference_items(
    currency_id: str,
    subtotals_cents: Dict[str, int],
    quantities: Dict[str, int],
    unit_prices_cents: Dict[str, int],
) -> Tuple[list, Dict[str, Any]]:
    items = []
    metadata = {
        "quantities": quantities,
        "unit_prices_cents": unit_prices_cents,
        "subtotals_cents": subtotals_cents,
    }
    subtotals_mp = totals_for_mp(subtotals_cents)
    for key, subtotal_mp in subtotals_mp.items():
        if subtotal_mp == 0:
            continue
        if settings.GROUP_ITEMS_FOR_MP:
            items.append(
                {
                    "title": f"{key} service",
                    "quantity": 1,
                    "unit_price": float(subtotal_mp),
                    "currency_id": currency_id,
                }
            )
        else:
            quantity = max(1, int(quantities.get(key, 1)))
            unit_price = total_for_mp(unit_prices_cents[key])
            items.append(
                {
                    "title": f"{key} service",
                    "quantity": quantity,
                    "unit_price": float(unit_price),
                    "currency_id": currency_id,
                }
            )
    return items, metadata


def verify_mp_webhook(
    secret: str,
    x_signature: Optional[str],
    x_request_id: Optional[str],
    data_id: Optional[str],
) -> bool:
    if not secret:
        logger.warning("MP_WEBHOOK_SECRET empty; accepting webhook in dev mode")
        return True
    if not x_signature or not x_request_id or not data_id:
        return False

    parts = dict(
        (item.split("=")[0].strip(), item.split("=")[1].strip())
        for item in x_signature.split(",")
        if "=" in item
    )
    ts = parts.get("ts")
    v1 = parts.get("v1")
    if not ts or not v1:
        return False

    manifest = f"id:{data_id};request-id:{x_request_id};ts:{ts};"
    computed = hmac.new(secret.encode("utf-8"), manifest.encode("utf-8"), sha256).hexdigest()
    return hmac.compare_digest(computed, v1)
