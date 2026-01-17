from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, EmailStr, Field

from ..mp_client import MPRequestError
from ..services.orders import QuoteNotFoundError, create_checkout_preference, create_quote, get_order
from ..settings import settings

logger = logging.getLogger(__name__)

router = APIRouter()


class QuoteRequest(BaseModel):
    email: EmailStr
    username: str = Field(min_length=1)
    follows: int
    likes: int
    views: int
    comments: int
    currency_id: Optional[str] = None


class CheckoutRequest(BaseModel):
    quote_id: str


@router.post("/quote")
async def quote_endpoint(payload: QuoteRequest):
    result = create_quote(payload.dict())
    return result


@router.post("/checkout/preferences")
async def checkout_preferences(payload: CheckoutRequest):
    try:
        result = create_checkout_preference(payload.quote_id)
        return result
    except QuoteNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Quote no encontrada") from exc
    except MPRequestError:
        logger.error("Error al crear preferencia en Mercado Pago", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Error al crear preferencia",
        )


@router.get("/orders/{quote_id}")
async def order_status(quote_id: str):
    try:
        return get_order(quote_id)
    except QuoteNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Quote no encontrada") from exc
