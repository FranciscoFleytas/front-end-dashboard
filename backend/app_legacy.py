# app.py
# Backend FastAPI para:
# - Cotizar (precio por unidad) con cantidades grandes
# - Crear preferencia de Mercado Pago (Checkout Pro) y devolver init_point
# - Recibir webhook, verificar firma, consultar pago, validar monto/moneda y marcar paid
# - Entrega manual: deja fulfillment_status='pending_manual' (24-48h)
#
# Endpoints para tu frontend:
#   POST /quote
#   POST /checkout/preferences
#   GET  /orders/{quote_id}
#
# Webhook:
#   POST /webhooks/mercadopago  (PUBLICO/HTTPS)
#
# Admin opcional:
#   GET  /admin/orders/paid
#   POST /admin/orders/{quote_id}/mark-delivered
#
# Reqs:
#   pip install fastapi uvicorn[standard] mercadopago python-dotenv pydantic
#
# Run:
#   uvicorn app:app --reload --port 8000

import os
import json
import time
import uuid
import hmac
import hashlib
import sqlite3
import logging
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional, List, Dict, Any

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, Field, conint

import mercadopago

# -------------------- Setup --------------------
load_dotenv()

logger = logging.getLogger("mp-backend")
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))

MP_ACCESS_TOKEN = os.getenv("MP_ACCESS_TOKEN")
MP_WEBHOOK_SECRET = os.getenv("MP_WEBHOOK_SECRET", "")  # setear en prod (firma webhook)
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "http://localhost:3000")  # tu dominio frontend (para back_urls)
MP_NOTIFICATION_URL = os.getenv("MP_NOTIFICATION_URL", "http://localhost:8000/webhooks/mercadopago")

DB_PATH = os.getenv("DB_PATH", "quotes.sqlite3")
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "")

ALLOWED_ORIGINS = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "").split(",") if o.strip()]
ALLOWED_METHODS = [m.strip() for m in os.getenv("ALLOWED_METHODS", "GET,POST,OPTIONS").split(",") if m.strip()]
ALLOWED_HEADERS = [h.strip() for h in os.getenv("ALLOWED_HEADERS", "content-type,x-admin-token").split(",") if h.strip()]

# Límite de cantidades por orden (para evitar cargas absurdas / overflow)
MAX_QTY_PER_FIELD = int(os.getenv("MAX_QTY_PER_FIELD", "500000000"))  # 500M por tipo (ajustá)
QUOTE_TTL_SECONDS = int(os.getenv("QUOTE_TTL_SECONDS", str(15 * 60)))  # 15 min

DEFAULT_CURRENCY = os.getenv("DEFAULT_CURRENCY", "USD")  # si usás ARS, poné ARS

# Precios por unidad: idealmente migrar a DB; por ahora config/env
# Podés sobreescribir por env (ej: PRICE_FOLLOWS=0.03 etc.)
def _env_decimal(name: str, fallback: str) -> Decimal:
    return Decimal(os.getenv(name, fallback))

PRICE_PER_UNIT = {
    "follows": _env_decimal("PRICE_FOLLOWS", "0.02499"),
    "likes": _env_decimal("PRICE_LIKES", "0.02499"),
    "views": _env_decimal("PRICE_VIEWS", "0.01499"),
    "comments": _env_decimal("PRICE_COMMENTS", "0.01999"),
}

# Para cantidades grandes: "agrupamos" en Mercado Pago sin quantities gigantes.
# 1 item por tipo con quantity=1 y unit_price=subtotal_del_tipo
GROUP_ITEMS_FOR_MP = os.getenv("GROUP_ITEMS_FOR_MP", "1") == "1"

if not MP_ACCESS_TOKEN:
    raise RuntimeError("Falta MP_ACCESS_TOKEN en el entorno (.env)")

sdk = mercadopago.SDK(MP_ACCESS_TOKEN)

# -------------------- Utils dinero --------------------
def money_2(x: Decimal) -> Decimal:
    # Redondeo bancario “normal” a 2 decimales
    return x.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

def compute_subtotals(follows: int, likes: int, views: int, comments: int) -> Dict[str, Decimal]:
    return {
        "follows": money_2(Decimal(follows) * PRICE_PER_UNIT["follows"]),
        "likes": money_2(Decimal(likes) * PRICE_PER_UNIT["likes"]),
        "views": money_2(Decimal(views) * PRICE_PER_UNIT["views"]),
        "comments": money_2(Decimal(comments) * PRICE_PER_UNIT["comments"]),
    }

def compute_total(subtotals: Dict[str, Decimal]) -> Decimal:
    return money_2(sum(subtotals.values(), start=Decimal("0")))

def build_mp_items(currency_id: str, subtotals: Dict[str, Decimal], quantities: Dict[str, int]) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []

    def add(title: str, key: str):
        qty = int(quantities[key])
        if qty <= 0:
            return
        if GROUP_ITEMS_FOR_MP:
            # Para cantidades grandes: quantity=1, unit_price=subtotal
            unit_price = float(subtotals[key])
            if unit_price <= 0:
                return
            items.append({
                "title": f"{title} (paquete)",
                "quantity": 1,
                "currency_id": currency_id,
                "unit_price": unit_price,
            })
        else:
            # Si tus cantidades son chicas, podés mandar quantity real
            unit_price = float(PRICE_PER_UNIT[key])
            items.append({
                "title": title,
                "quantity": qty,
                "currency_id": currency_id,
                "unit_price": unit_price,
            })

    add("Seguidores", "follows")
    add("Likes", "likes")
    add("Vistas", "views")
    add("Comentarios", "comments")
    return items

# -------------------- Firma webhook MP --------------------
def parse_x_signature(x_signature: str) -> tuple[str, str]:
    # Formato esperado: "ts=...,v1=..."
    ts = None
    v1 = None
    for part in x_signature.split(","):
        part = part.strip()
        if "=" not in part:
            continue
        k, v = part.split("=", 1)
        k = k.strip()
        v = v.strip()
        if k == "ts":
            ts = v
        elif k == "v1":
            v1 = v
    if not ts or not v1:
        raise ValueError("x-signature inválida")
    return ts, v1

def verify_mp_webhook(*, secret: str, x_signature: str, x_request_id: str, data_id: str) -> bool:
    ts, v1 = parse_x_signature(x_signature)
    manifest = f"id:{data_id};request-id:{x_request_id};ts:{ts};"
    calc = hmac.new(secret.encode("utf-8"), manifest.encode("utf-8"), hashlib.sha256).hexdigest()
    return hmac.compare_digest(calc, v1)

# -------------------- DB (SQLite) --------------------
def db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, isolation_level=None)  # autocommit, controlamos BEGIN/COMMIT manual
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("PRAGMA busy_timeout=3000;")
    return conn

def init_db():
    with db() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS quotes (
                quote_id TEXT PRIMARY KEY,
                created_at INTEGER NOT NULL,
                expires_at INTEGER NOT NULL,

                status TEXT NOT NULL,                     -- open | pending_checkout | paid | cancelled | expired
                fulfillment_status TEXT NOT NULL,          -- none | pending_manual | delivered | cancelled

                currency_id TEXT NOT NULL,
                amount REAL NOT NULL,
                subtotals_json TEXT NOT NULL,

                email TEXT NOT NULL,
                username TEXT NOT NULL,
                follows INTEGER NOT NULL,
                likes INTEGER NOT NULL,
                views INTEGER NOT NULL,
                comments INTEGER NOT NULL,

                preference_id TEXT,
                payment_id TEXT,
                payment_status TEXT,
                raw_payment_json TEXT
            )
            """
        )

def get_quote_row(conn: sqlite3.Connection, quote_id: str) -> Optional[sqlite3.Row]:
    return conn.execute("SELECT * FROM quotes WHERE quote_id=?", (quote_id,)).fetchone()

def mark_expired_if_needed(conn: sqlite3.Connection, row: sqlite3.Row):
    if row["status"] in ("paid", "cancelled", "expired"):
        return
    if row["expires_at"] < int(time.time()):
        conn.execute("UPDATE quotes SET status='expired' WHERE quote_id=?", (row["quote_id"],))

def require_admin(x_admin_token: Optional[str]):
    if not ADMIN_TOKEN:
        raise HTTPException(500, "ADMIN_TOKEN no configurado en el servidor")
    if not x_admin_token or x_admin_token != ADMIN_TOKEN:
        raise HTTPException(401, "No autorizado")

# -------------------- Models --------------------
class QuoteIn(BaseModel):
    email: EmailStr
    username: str = Field(min_length=1, max_length=80)

    follows: conint(ge=0, le=MAX_QTY_PER_FIELD) = 0
    likes: conint(ge=0, le=MAX_QTY_PER_FIELD) = 0
    views: conint(ge=0, le=MAX_QTY_PER_FIELD) = 0
    comments: conint(ge=0, le=MAX_QTY_PER_FIELD) = 0

    currency_id: str = DEFAULT_CURRENCY

class QuoteOut(BaseModel):
    quote_id: str
    amount: float
    currency_id: str
    expires_at: int
    status: str
    fulfillment_status: str
    subtotals: Dict[str, float]

class CheckoutIn(BaseModel):
    quote_id: str

class CheckoutOut(BaseModel):
    quote_id: str
    preference_id: str
    init_point: str

class OrderOut(BaseModel):
    quote_id: str
    created_at: int
    expires_at: int
    status: str
    fulfillment_status: str
    currency_id: str
    amount: float
    subtotals: Dict[str, float]
    email: str
    username: str
    follows: int
    likes: int
    views: int
    comments: int
    preference_id: Optional[str] = None
    payment_id: Optional[str] = None
    payment_status: Optional[str] = None

def row_to_order_out(row: sqlite3.Row) -> OrderOut:
    return OrderOut(
        quote_id=row["quote_id"],
        created_at=row["created_at"],
        expires_at=row["expires_at"],
        status=row["status"],
        fulfillment_status=row["fulfillment_status"],
        currency_id=row["currency_id"],
        amount=float(row["amount"]),
        subtotals={k: float(v) for k, v in json.loads(row["subtotals_json"]).items()},
        email=row["email"],
        username=row["username"],
        follows=int(row["follows"]),
        likes=int(row["likes"]),
        views=int(row["views"]),
        comments=int(row["comments"]),
        preference_id=row["preference_id"],
        payment_id=row["payment_id"],
        payment_status=row["payment_status"],
    )

# -------------------- App --------------------
app = FastAPI(title="MP Checkout Pro (cantidades grandes + verificación + entrega manual)")

if ALLOWED_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=ALLOWED_METHODS,
        allow_headers=ALLOWED_HEADERS,
    )

@app.on_event("startup")
def _startup():
    init_db()
    logger.info("DB ready. GROUP_ITEMS_FOR_MP=%s", GROUP_ITEMS_FOR_MP)

@app.get("/health")
def health():
    return {"ok": True}

# -------------------- Public API --------------------
@app.post("/quote", response_model=QuoteOut)
def create_quote(payload: QuoteIn):
    quantities = {
        "follows": int(payload.follows),
        "likes": int(payload.likes),
        "views": int(payload.views),
        "comments": int(payload.comments),
    }

    subtotals = compute_subtotals(**quantities)
    total = compute_total(subtotals)
    if total <= 0:
        raise HTTPException(400, "El total debe ser mayor a 0")

    now = int(time.time())
    quote_id = str(uuid.uuid4())
    expires_at = now + QUOTE_TTL_SECONDS

    with db() as conn:
        conn.execute(
            """
            INSERT INTO quotes (
                quote_id, created_at, expires_at,
                status, fulfillment_status,
                currency_id, amount, subtotals_json,
                email, username, follows, likes, views, comments
            ) VALUES (?, ?, ?, 'open', 'none', ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                quote_id, now, expires_at,
                payload.currency_id,
                float(total),
                json.dumps({k: float(v) for k, v in subtotals.items()}),
                str(payload.email), payload.username,
                quantities["follows"], quantities["likes"], quantities["views"], quantities["comments"],
            ),
        )

    logger.info("Quote created %s amount=%s %s", quote_id, float(total), payload.currency_id)

    return QuoteOut(
        quote_id=quote_id,
        amount=float(total),
        currency_id=payload.currency_id,
        expires_at=expires_at,
        status="open",
        fulfillment_status="none",
        subtotals={k: float(v) for k, v in subtotals.items()},
    )

@app.post("/checkout/preferences", response_model=CheckoutOut)
def create_preference(body: CheckoutIn):
    with db() as conn:
        row = get_quote_row(conn, body.quote_id)
        if not row:
            raise HTTPException(404, "quote_id inexistente")

        mark_expired_if_needed(conn, row)
        row = get_quote_row(conn, body.quote_id)
        if not row:
            raise HTTPException(404, "quote_id inexistente")

        if row["status"] == "expired":
            raise HTTPException(400, "Quote expirada")
        if row["status"] == "paid":
            raise HTTPException(409, "Quote ya pagada")

        subtotals = {k: Decimal(str(v)) for k, v in json.loads(row["subtotals_json"]).items()}
        quantities = {
            "follows": int(row["follows"]),
            "likes": int(row["likes"]),
            "views": int(row["views"]),
            "comments": int(row["comments"]),
        }
        items = build_mp_items(row["currency_id"], subtotals, quantities)
        if not items:
            raise HTTPException(400, "No hay unidades para cobrar")

        external_reference = f"QUOTE_{row['quote_id']}"

        preference_data = {
            "items": items,
            "external_reference": external_reference,
            "metadata": {
                "quote_id": row["quote_id"],
                "email": row["email"],
                "username": row["username"],
                "quantities": quantities,
                "unit_prices": {k: float(v) for k, v in PRICE_PER_UNIT.items()},
                "subtotals": {k: float(v) for k, v in subtotals.items()},
                "amount": float(row["amount"]),
                "currency_id": row["currency_id"],
                "grouped_for_large_qty": GROUP_ITEMS_FOR_MP,
            },
            "notification_url": MP_NOTIFICATION_URL,
            "back_urls": {
                "success": f"{PUBLIC_BASE_URL}/pago-exitoso",
                "failure": f"{PUBLIC_BASE_URL}/pago-fallido",
                "pending": f"{PUBLIC_BASE_URL}/pago-pendiente",
            },
            "auto_return": "approved",
        }

        try:
            res = sdk.preference().create(preference_data)
        except Exception as e:
            logger.exception("MP preference.create exception")
            raise HTTPException(502, f"Error Mercado Pago: {e}")

        if res.get("status") not in (200, 201):
            logger.error("MP preference.create failed: %s", res)
            raise HTTPException(502, {"mp_error": res})

        pref = res["response"]
        preference_id = pref["id"]
        init_point = pref.get("init_point") or pref.get("sandbox_init_point")
        if not init_point:
            raise HTTPException(502, "Mercado Pago no devolvió init_point")

        conn.execute(
            "UPDATE quotes SET status='pending_checkout', preference_id=? WHERE quote_id=?",
            (preference_id, row["quote_id"]),
        )

    logger.info("Preference created quote=%s pref=%s", body.quote_id, preference_id)
    return CheckoutOut(quote_id=body.quote_id, preference_id=preference_id, init_point=init_point)

@app.get("/orders/{quote_id}", response_model=OrderOut)
def get_order(quote_id: str):
    with db() as conn:
        row = get_quote_row(conn, quote_id)
        if not row:
            raise HTTPException(404, "Orden inexistente")
        mark_expired_if_needed(conn, row)
        row = get_quote_row(conn, quote_id)
        if not row:
            raise HTTPException(404, "Orden inexistente")
        return row_to_order_out(row)

# -------------------- Webhook --------------------
@app.post("/webhooks/mercadopago")
async def mercadopago_webhook(request: Request):
    params = dict(request.query_params)
    content_type = (request.headers.get("content-type") or "").lower()

    body = None
    if "application/json" in content_type:
        try:
            body = await request.json()
        except Exception:
            body = None

    event_type = params.get("type") or params.get("topic") or (body or {}).get("type")
    data_id = params.get("data.id") or params.get("id") or ((body or {}).get("data") or {}).get("id")
    if not data_id:
        # Respondemos OK para que no reintente infinito
        return {"ok": True, "ignored": True}

    # Verificación de firma (recomendado en prod)
    if MP_WEBHOOK_SECRET:
        x_signature = request.headers.get("x-signature")
        x_request_id = request.headers.get("x-request-id")
        if not x_signature or not x_request_id:
            logger.warning("Webhook missing signature headers")
            raise HTTPException(401, "Faltan headers de firma")

        try:
            valid = verify_mp_webhook(
                secret=MP_WEBHOOK_SECRET,
                x_signature=x_signature,
                x_request_id=x_request_id,
                data_id=str(data_id),
            )
        except Exception:
            logger.exception("Webhook signature parse error")
            raise HTTPException(401, "Firma inválida")

        if not valid:
            logger.warning("Webhook signature invalid")
            raise HTTPException(401, "Firma inválida")

    # Procesamos payments
    if event_type not in ("payment", "payments"):
        return {"ok": True, "unhandled_type": event_type, "data_id": str(data_id)}

    payment_id = str(data_id)

    # Consultamos el pago a MP (no confiamos en lo que llega en el webhook)
    try:
        payment_res = sdk.payment().get(payment_id)
    except Exception:
        logger.exception("MP payment.get exception payment_id=%s", payment_id)
        # Devolvemos 200 para evitar tormenta de reintentos; loguear y monitorear
        return {"ok": True, "mp_fetch_failed": True, "payment_id": payment_id}

    if payment_res.get("status") != 200:
        logger.error("MP payment.get failed: %s", payment_res)
        return {"ok": True, "mp_fetch_failed": True, "payment_id": payment_id}

    payment = payment_res["response"]
    status = payment.get("status")
    external_reference = payment.get("external_reference") or ""
    currency_id = payment.get("currency_id")
    paid_amount = Decimal(str(payment.get("transaction_amount") or "0"))

    if not external_reference.startswith("QUOTE_"):
        logger.warning("Payment without QUOTE_ external_reference payment_id=%s", payment_id)
        return {"ok": True, "unmatched": True, "payment_id": payment_id}

    quote_id = external_reference.replace("QUOTE_", "", 1)

    with db() as conn:
        # Transacción atómica para evitar race conditions
        conn.execute("BEGIN IMMEDIATE;")
        row = get_quote_row(conn, quote_id)
        if not row:
            conn.execute("COMMIT;")
            return {"ok": True, "unknown_quote": True, "quote_id": quote_id}

        # Si ya estaba paid, idempotente
        if row["status"] == "paid":
            conn.execute("COMMIT;")
            return {"ok": True, "already_paid": True, "quote_id": quote_id, "payment_id": payment_id}

        quote_currency = row["currency_id"]
        quote_amount = Decimal(str(row["amount"]))

        # Validaciones de coherencia (moneda/monto)
        # Nota: tolerancia por redondeo de 1 centavo.
        if currency_id != quote_currency:
            logger.error("Currency mismatch quote=%s paid=%s expected=%s", quote_id, currency_id, quote_currency)
            conn.execute("COMMIT;")
            raise HTTPException(409, "Moneda no coincide")

        if abs(paid_amount - quote_amount) > Decimal("0.01"):
            logger.error("Amount mismatch quote=%s paid=%s expected=%s", quote_id, paid_amount, quote_amount)
            conn.execute("COMMIT;")
            raise HTTPException(409, "Monto no coincide")

        # Regla de negocio:
        # - Si approved: marcar paid y pending_manual (aunque la quote estuviera expirada, la plata vale)
        # - Si pending/rejected: solo registramos payment_id/status (no marcamos paid)
        new_status = row["status"]
        new_fulfillment = row["fulfillment_status"]

        if status == "approved":
            new_status = "paid"
            if new_fulfillment in ("none", "cancelled"):
                new_fulfillment = "pending_manual"

        conn.execute(
            """
            UPDATE quotes
            SET status=?,
                fulfillment_status=?,
                payment_id=?,
                payment_status=?,
                raw_payment_json=?
            WHERE quote_id=? AND status!='paid'
            """,
            (new_status, new_fulfillment, payment_id, status, json.dumps(payment), quote_id),
        )
        conn.execute("COMMIT;")

    logger.info("Webhook processed quote=%s payment=%s status=%s", quote_id, payment_id, status)
    return {"ok": True, "quote_id": quote_id, "payment_id": payment_id, "status": status}

# -------------------- Admin API (manual fulfillment) --------------------
@app.get("/admin/orders/paid", response_model=List[OrderOut])
def admin_list_paid_orders(
    x_admin_token: Optional[str] = Header(default=None, alias="X-Admin-Token"),
    limit: int = 50,
):
    require_admin(x_admin_token)
    limit = max(1, min(int(limit), 200))

    with db() as conn:
        rows = conn.execute(
            """
            SELECT * FROM quotes
            WHERE status='paid'
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

    return [row_to_order_out(r) for r in rows]

@app.post("/admin/orders/{quote_id}/mark-delivered")
def admin_mark_delivered(
    quote_id: str,
    x_admin_token: Optional[str] = Header(default=None, alias="X-Admin-Token"),
):
    require_admin(x_admin_token)

    with db() as conn:
        row = get_quote_row(conn, quote_id)
        if not row:
            raise HTTPException(404, "Orden inexistente")
        if row["status"] != "paid":
            raise HTTPException(409, "Solo se puede marcar delivered si la orden está paid")

        conn.execute("UPDATE quotes SET fulfillment_status='delivered' WHERE quote_id=?", (quote_id,))

    logger.info("Order delivered quote=%s", quote_id)
    return {"ok": True, "quote_id": quote_id, "fulfillment_status": "delivered"}
