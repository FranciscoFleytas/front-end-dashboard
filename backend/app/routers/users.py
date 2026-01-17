from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from typing import Any, Dict, Optional

# Reutilizá estas funciones desde tu router instagram existente:
# - normalize_ig_input(value) -> dict
# - fetch_og(url) -> dict (best effort)
from .instagram import build_label, fetch_og, normalize_ig_input

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("/search")
async def search_user(
    q: str = Query(min_length=2, max_length=80),
    email: Optional[str] = Query(default=None, max_length=120),
) -> Dict[str, Any]:
    """
    Devuelve un JSON estilo autocomplete para un perfil de Instagram.
    Opción A: sin login, best-effort OG preview.
    """
    norm = normalize_ig_input(q)

    if norm["type"] != "username":
        # si pegaron un link de post, no es un "user search"
        raise HTTPException(400, "USERNAME_REQUIRED")

    username = norm["username"]
    url = norm["url"]

    og = None
    try:
        og = await fetch_og(url)
    except Exception:
        og = None

    label = build_label(None, username)
    avatar_src = ""

    if og:
        label = build_label(og.get("title"), username)
        avatar_src = og.get("image") or ""

    # id estable para UI (NO es id real de IG)
    stable_id = (abs(hash(username)) % 10_000_000) or 1

    return {
        "id": stable_id,
        "label": label,
        "suffix": email or username,  # email lo pone el cliente; fallback al username
        "link_instagram": url,
        "avatar": {"src": avatar_src},
    }
