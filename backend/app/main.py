from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .db import connect, init_db
from .routers import admin, public, webhooks, instagram, users, user_posts, image_proxy 
from .settings import settings

logging.basicConfig(level=settings.LOG_LEVEL.upper())
logger = logging.getLogger(__name__)

app = FastAPI()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_methods=settings.allowed_methods_list,
    allow_headers=settings.allowed_headers_list,
)

# Routers (sin duplicados)
app.include_router(public.router)
app.include_router(webhooks.router)
app.include_router(admin.router)
app.include_router(instagram.router)
app.include_router(users.router)
app.include_router(user_posts.router)
app.include_router(image_proxy.router)

@app.on_event("startup")
def on_startup() -> None:
    conn = connect()
    try:
        init_db(conn)
    finally:
        conn.close()
    logger.info("Database initialized")


@app.get("/health")
def health() -> dict:
    return {"ok": True}
