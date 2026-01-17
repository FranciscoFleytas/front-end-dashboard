from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Header, Request

from ..mp_client import verify_mp_webhook
from ..services.orders import process_webhook_payment
from ..settings import settings

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/webhooks/mercadopago")
async def mercadopago_webhook(
    request: Request,
    x_signature: Optional[str] = Header(None, alias="x-signature"),
    x_request_id: Optional[str] = Header(None, alias="x-request-id"),
):
    try:
        payload = await request.json()
    except Exception:
        payload = {}

    data_id = None
    if isinstance(payload, dict):
        data = payload.get("data") or {}
        if isinstance(data, dict):
            data_id = data.get("id")
        data_id = data_id or payload.get("id") or payload.get("data_id")

    event_type = "unknown"
    if isinstance(payload, dict):
        event_type = payload.get("type") or payload.get("action") or "unknown"

    signature_valid = verify_mp_webhook(
        settings.MP_WEBHOOK_SECRET,
        x_signature,
        x_request_id,
        str(data_id) if data_id else None,
    )

    result = process_webhook_payment(
        str(data_id) if data_id else None,
        event_type,
        payload if isinstance(payload, dict) else {},
        signature_valid,
    )
    return result
