from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Header, HTTPException, status

from ..services.orders import QuoteNotFoundError, list_paid_orders, mark_delivered
from ..settings import settings

router = APIRouter(prefix="/admin")


def _require_admin(token: Optional[str]) -> None:
    if not settings.ADMIN_TOKEN or token != settings.ADMIN_TOKEN:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")


@router.get("/orders/paid")
async def paid_orders(limit: int = 50, x_admin_token: Optional[str] = Header(None, alias="X-Admin-Token")):
    _require_admin(x_admin_token)
    safe_limit = max(1, min(limit, 200))
    return list_paid_orders(safe_limit)


@router.post("/orders/{quote_id}/mark-delivered")
async def mark_order_delivered(
    quote_id: str, x_admin_token: Optional[str] = Header(None, alias="X-Admin-Token")
):
    _require_admin(x_admin_token)
    try:
        return mark_delivered(quote_id)
    except QuoteNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Quote no encontrada") from exc
