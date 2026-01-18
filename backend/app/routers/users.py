from __future__ import annotations

import time
from typing import Any, Dict, Optional
from urllib.parse import quote

from fastapi import APIRouter, HTTPException, Query
from instagrapi.exceptions import (
    ChallengeRequired,
    LoginRequired,
    PleaseWaitFewMinutes,
    TwoFactorRequired,
)

# Reutilizá estas funciones desde tu router instagram existente:
# - normalize_ig_input(value) -> dict
# - fetch_og(url) -> dict (best effort)
from .instagram import build_label, fetch_og, normalize_ig_input
from ..services.ig_client import get_ig_client, get_ig_lock

router = APIRouter(prefix="/api/users", tags=["users"])

CACHE_TTL_SECONDS = 90
_search_cache: Dict[str, tuple[float, list[Dict[str, Any]]]] = {}


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


@router.get("/search/list")
def search_users_list(
    q: str = Query(min_length=1, max_length=80),
    limit: int = Query(default=10, ge=1, le=20),
) -> list[Dict[str, Any]]:
    query = q.strip().lstrip("@")
    if len(query) < 2:
        return []

    cache_key = f"{query.lower()}:{limit}"
    cached = _search_cache.get(cache_key)
    now = time.time()
    if cached and now - cached[0] < CACHE_TTL_SECONDS:
        return cached[1]

    try:
        with get_ig_lock():
            cl = get_ig_client()
            users = cl.search_users(query)
    except PleaseWaitFewMinutes:
        raise HTTPException(429, "IG_RATE_LIMITED")
    except (LoginRequired, ChallengeRequired, TwoFactorRequired):
        raise HTTPException(409, "IG_LOGIN_REQUIRED")
    except Exception:
        raise HTTPException(502, "IG_SEARCH_FAILED")

    results = []
    for user in users[:limit]:
        username = getattr(user, "username", "") or ""
        if not username:
            continue
        full_name = (getattr(user, "full_name", "") or "").strip()
        label = f"{full_name} (@{username})" if full_name else f"@{username}"
        user_id = getattr(user, "pk", None)
        stable_id = user_id or ((abs(hash(username)) % 10_000_000) or 1)
        avatar_src = getattr(user, "profile_pic_url", None) or ""
        proxied_avatar = (
            f"/api/proxy/image?url={quote(str(avatar_src), safe='')}"
            if avatar_src
            else ""
        )

        results.append(
            {
                "id": stable_id,
                "label": label,
                "suffix": f"@{username}",
                "link_instagram": f"https://www.instagram.com/{username}/",
                "avatar": {"src": proxied_avatar},
            }
        )

    _search_cache[cache_key] = (now, results)
    return results
