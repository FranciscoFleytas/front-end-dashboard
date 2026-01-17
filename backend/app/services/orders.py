from __future__ import annotations

import json
import logging
import time
import uuid
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, Optional, Tuple

from fastapi import HTTPException, status

from ..db import dump_json, get_db, load_json, row_to_dict, transaction
from ..mp_client import MPRequestError, MercadoPagoClient, PaymentData, build_preference_items
from ..pricing import calculate_subtotals
from ..settings import settings

logger = logging.getLogger(__name__)


class QuoteNotFoundError(RuntimeError):
    pass


def _now_ts() -> int:
    return int(time.time())


def _amount_to_cents(amount: float) -> int:
    dec = Decimal(str(amount)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return int(dec * 100)


def _validate_qty(value: int, field: str) -> None:
    if value < 0 or value > settings.MAX_QTY_PER_FIELD:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{field} fuera de rango",
        )


def create_quote(payload: Dict[str, Any]) -> Dict[str, Any]:
    follows = int(payload.get("follows", 0))
    likes = int(payload.get("likes", 0))
    views = int(payload.get("views", 0))
    comments = int(payload.get("comments", 0))
    for field_name, value in (
        ("follows", follows),
        ("likes", likes),
        ("views", views),
        ("comments", comments),
    ):
        _validate_qty(value, field_name)

    subtotals_cents, total_cents, unit_prices_cents = calculate_subtotals(
        follows=follows,
        likes=likes,
        views=views,
        comments=comments,
    )

    quote_id = str(uuid.uuid4())
    created_at = _now_ts()
    expires_at = created_at + settings.QUOTE_TTL_SECONDS
    currency_id = payload.get("currency_id") or settings.DEFAULT_CURRENCY

    quote_row = {
        "quote_id": quote_id,
        "created_at": created_at,
        "expires_at": expires_at,
        "status": "open",
        "fulfillment_status": "none",
        "late_payment": 0,
        "currency_id": currency_id,
        "amount_cents": total_cents,
        "subtotals_cents_json": dump_json(subtotals_cents),
        "email": payload["email"],
        "username": payload["username"],
        "follows": follows,
        "likes": likes,
        "views": views,
        "comments": comments,
    }

    with get_db() as conn:
        with transaction(conn):
            conn.execute(
                """
                INSERT INTO quotes (
                    quote_id, created_at, expires_at, status, fulfillment_status,
                    late_payment, currency_id, amount_cents, subtotals_cents_json,
                    email, username, follows, likes, views, comments
                ) VALUES (
                    :quote_id, :created_at, :expires_at, :status, :fulfillment_status,
                    :late_payment, :currency_id, :amount_cents, :subtotals_cents_json,
                    :email, :username, :follows, :likes, :views, :comments
                );
                """,
                quote_row,
            )
    logger.info("Quote creada %s", quote_id)
    return {
        "quote_id": quote_id,
        "expires_at": expires_at,
        "currency_id": currency_id,
        "amount_cents": total_cents,
        "subtotals_cents": subtotals_cents,
        "unit_prices_cents": unit_prices_cents,
    }


def _fetch_quote(conn, quote_id: str) -> Optional[Dict[str, Any]]:
    row = conn.execute("SELECT * FROM quotes WHERE quote_id = ?", (quote_id,)).fetchone()
    if not row:
        return None
    result = row_to_dict(row)
    result["subtotals_cents"] = load_json(result.get("subtotals_cents_json")) or {}
    return result


def _mark_expired_if_needed(conn, quote: Dict[str, Any]) -> Dict[str, Any]:
    now = _now_ts()
    if quote["status"] in {"open", "pending_checkout", "pending_payment"} and now > quote["expires_at"]:
        quote["status"] = "expired"
        conn.execute(
            "UPDATE quotes SET status = ? WHERE quote_id = ?",
            ("expired", quote["quote_id"]),
        )
    return quote


def create_checkout_preference(quote_id: str) -> Dict[str, Any]:
    with get_db() as conn:
        with transaction(conn):
            quote = _fetch_quote(conn, quote_id)
            if not quote:
                raise QuoteNotFoundError()
            _mark_expired_if_needed(conn, quote)
            if quote["status"] == "expired":
                raise HTTPException(status_code=400, detail="Quote expirada")
            if quote.get("preference_id"):
                # Si ya existe preferencia, devolvemos init_point guardado para soportar reintentos.
                return {
                    "init_point": quote.get("init_point"),
                    "preference_id": quote["preference_id"],
                }


    mp_client = MercadoPagoClient(settings.MP_ACCESS_TOKEN)
    quantities = {
        "follows": quote["follows"],
        "likes": quote["likes"],
        "views": quote["views"],
        "comments": quote["comments"],
    }
    unit_prices_cents = {
        "follows": settings.PRICE_FOLLOW_CENTS,
        "likes": settings.PRICE_LIKE_CENTS,
        "views": settings.PRICE_VIEW_CENTS,
        "comments": settings.PRICE_COMMENT_CENTS,
    }
    items, metadata = build_preference_items(
        currency_id=quote["currency_id"],
        subtotals_cents=quote["subtotals_cents"],
        quantities=quantities,
        unit_prices_cents=unit_prices_cents,
    )

    preference_payload = {
        "items": items,
        "payer": {"email": quote["email"]},
        "external_reference": f"QUOTE_{quote_id}",
        "notification_url": settings.notification_url,
        "metadata": metadata,
    }

    preference = mp_client.create_preference(preference_payload)
    preference_id = str(preference.get("id", ""))
    init_point = preference.get("init_point") or preference.get("sandbox_init_point")

    with get_db() as conn:
        with transaction(conn):
            conn.execute(
                """
                UPDATE quotes
                SET preference_id = ?, init_point = ?, status = ?
                WHERE quote_id = ?
                """,
                (preference_id, init_point, "pending_checkout", quote_id),
            )


    logger.info("Preferencia creada %s para quote %s", preference_id, quote_id)
    return {"init_point": init_point, "preference_id": preference_id}


def get_order(quote_id: str) -> Dict[str, Any]:
    with get_db() as conn:
        with transaction(conn):
            quote = _fetch_quote(conn, quote_id)
            if not quote:
                raise QuoteNotFoundError()
            _mark_expired_if_needed(conn, quote)

    return {
        "quote_id": quote["quote_id"],
        "status": quote["status"],
        "payment_status": quote.get("payment_status"),
        "fulfillment_status": quote.get("fulfillment_status"),
        "currency_id": quote.get("currency_id"),
        "amount_cents": quote.get("amount_cents"),
        "subtotals_cents": quote.get("subtotals_cents"),
        "created_at": quote.get("created_at"),
        "expires_at": quote.get("expires_at"),
        "init_point": quote.get("init_point"),
    }


def _validate_payment_amount(quote: Dict[str, Any], payment: PaymentData) -> Tuple[bool, str]:
    payment_cents = _amount_to_cents(payment.transaction_amount)
    quote_cents = int(quote["amount_cents"])
    if payment.currency_id != quote["currency_id"]:
        return False, "currency_mismatch"
    if abs(payment_cents - quote_cents) > 1:
        return False, "amount_mismatch"
    return True, "ok"


def process_webhook_payment(
    data_id: Optional[str],
    event_type: str,
    payload: Dict[str, Any],
    signature_valid: bool,
) -> Dict[str, Any]:
    received_at = _now_ts()
    event_payload = {"payload": payload, "signature_valid": signature_valid}

    payment: Optional[PaymentData] = None
    if signature_valid and data_id:
        mp_client = MercadoPagoClient(settings.MP_ACCESS_TOKEN)
        try:
            payment = mp_client.get_payment(data_id)
        except MPRequestError:
            logger.error("Fallo al consultar pago en Mercado Pago", exc_info=True)
            with get_db() as conn:
                with transaction(conn):
                    conn.execute(
                        """
                        INSERT INTO payment_events (quote_id, payment_id, event_type, received_at, payload_json)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (None, data_id, event_type, received_at, dump_json(event_payload)),
                    )
            return {"mp_fetch_failed": True}

    with get_db() as conn:
        with transaction(conn):
            quote_id = None
            payment_id = data_id
            if payment and payment.external_reference:
                if payment.external_reference.startswith("QUOTE_"):
                    quote_id = payment.external_reference.replace("QUOTE_", "", 1)
                event_payload["external_reference"] = payment.external_reference
            conn.execute(
                """
                INSERT INTO payment_events (quote_id, payment_id, event_type, received_at, payload_json)
                VALUES (?, ?, ?, ?, ?)
                """,
                (quote_id, payment_id, event_type, received_at, dump_json(event_payload)),
            )

            if not signature_valid:
                logger.warning("Firma webhook invalida")
                return {"signature_valid": False}

            if not payment:
                return {"payment_missing": True}

            if not payment.external_reference or not payment.external_reference.startswith("QUOTE_"):
                logger.error("external_reference invalido: %s", payment.external_reference)
                return {"invalid_external_reference": True}

            quote_id = payment.external_reference.replace("QUOTE_", "", 1)
            quote = _fetch_quote(conn, quote_id)
            if not quote:
                logger.error("Quote no encontrada para webhook %s", quote_id)
                return {"quote_not_found": True}

            if quote["status"] == "paid":
                logger.info("Quote %s ya pagada; ignorando webhook", quote_id)
                return {"already_paid": True}

            valid_amount, reason = _validate_payment_amount(quote, payment)
            if not valid_amount:
                logger.warning("Pago no valido para quote %s: %s", quote_id, reason)
                conn.execute(
                    """
                    UPDATE quotes
                    SET payment_id = ?, payment_status = ?, raw_payment_json = ?
                    WHERE quote_id = ?
                    """,
                    (payment.payment_id, reason, json.dumps(payment.raw), quote_id),
                )
                if quote["status"] != "paid":
                    conn.execute(
                        "UPDATE quotes SET status = ? WHERE quote_id = ?",
                        ("payment_failed", quote_id),
                    )
                return {"payment_invalid": True, "reason": reason}

            new_status = quote["status"]
            fulfillment_status = quote.get("fulfillment_status", "none")
            late_payment = quote.get("late_payment", 0)

            if payment.status == "approved":
                new_status = "paid"
                fulfillment_status = "pending_manual"
                if _now_ts() > quote["expires_at"]:
                    late_payment = 1
            elif payment.status in {"pending", "in_process", "authorized"}:
                new_status = "pending_payment"
            elif payment.status in {"rejected", "cancelled", "refunded", "charged_back"}:
                if quote["status"] != "paid":
                    new_status = "payment_failed"
            else:
                new_status = "pending_payment"

            conn.execute(
                """
                UPDATE quotes
                SET status = ?,
                    fulfillment_status = ?,
                    late_payment = ?,
                    payment_id = ?,
                    payment_status = ?,
                    raw_payment_json = ?
                WHERE quote_id = ?
                """,
                (
                    new_status,
                    fulfillment_status,
                    late_payment,
                    payment.payment_id,
                    payment.status,
                    json.dumps(payment.raw),
                    quote_id,
                ),
            )

    logger.info("Webhook procesado para quote %s", quote_id)
    return {"processed": True}


def list_paid_orders(limit: int) -> Dict[str, Any]:
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT * FROM quotes
            WHERE status = ? AND fulfillment_status = ?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            ("paid", "pending_manual", limit),
        ).fetchall()
    orders = []
    for row in rows:
        data = row_to_dict(row)
        data["subtotals_cents"] = load_json(data.get("subtotals_cents_json")) or {}
        orders.append(data)
    return {"orders": orders}


def mark_delivered(quote_id: str) -> Dict[str, Any]:
    with get_db() as conn:
        with transaction(conn):
            quote = _fetch_quote(conn, quote_id)
            if not quote:
                raise QuoteNotFoundError()
            conn.execute(
                """
                UPDATE quotes
                SET fulfillment_status = ?
                WHERE quote_id = ?
                """,
                ("delivered", quote_id),
            )
    return {"quote_id": quote_id, "fulfillment_status": "delivered"}
