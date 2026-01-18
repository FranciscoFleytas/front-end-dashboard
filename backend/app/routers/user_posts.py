from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import quote

from fastapi import APIRouter, HTTPException, Query
from instagrapi.exceptions import (
    ChallengeRequired,
    LoginRequired,
    PleaseWaitFewMinutes,
    TwoFactorRequired,
)

from ..services.ig_client import get_ig_client, get_ig_lock

router = APIRouter(prefix="/api/users", tags=["users-posts"])

# Cache corto para evitar pegarle a IG en cada refresh/scroll
CACHE_TTL_SECONDS = 60
_cache: Dict[str, tuple[float, Dict[str, Any]]] = {}


def _proxify_image(url: str) -> str:
    if not url:
        return ""
    if url.startswith("/api/proxy/image?url="):
        return url
    return f"/api/proxy/image?url={quote(url, safe='')}"


def _caption_text(item: Dict[str, Any]) -> Optional[str]:
    cap = item.get("caption")
    if isinstance(cap, dict):
        txt = cap.get("text")
        return str(txt) if txt else None
    return None


def _pick_thumbnail_from_item(item: Dict[str, Any]) -> str:
    """
    Intenta obtener una imagen “pintable” en este orden:
    1) image_versions2.candidates[0].url (feed normal)
    2) carousel_media[0].image_versions2.candidates[0].url (carrusel)
    3) thumbnail_urls[0] (algunos casos de video/reel)
    """
    iv2 = (item.get("image_versions2") or {}).get("candidates") or []
    if isinstance(iv2, list) and iv2 and isinstance(iv2[0], dict) and iv2[0].get("url"):
        return str(iv2[0]["url"])

    carousel = item.get("carousel_media") or []
    if isinstance(carousel, list) and carousel:
        first = carousel[0] or {}
        iv2c = (first.get("image_versions2") or {}).get("candidates") or []
        if isinstance(iv2c, list) and iv2c and isinstance(iv2c[0], dict) and iv2c[0].get("url"):
            return str(iv2c[0]["url"])

    thumbs = item.get("thumbnail_urls") or []
    if isinstance(thumbs, list) and thumbs:
        return str(thumbs[0])

    return ""


def _taken_at_iso(item: Dict[str, Any]) -> Optional[str]:
    taken_at = item.get("taken_at")
    if isinstance(taken_at, int):
        return datetime.fromtimestamp(taken_at, tz=timezone.utc).isoformat()
    return None


@router.get("/posts")
def get_user_posts(
    username: str = Query(min_length=1, max_length=30),
    limit: int = Query(default=12, ge=1, le=24),
    skip: int = Query(default=0, ge=0),
) -> Dict[str, Any]:
    cache_key = f"{username}:{skip}:{limit}"
    now = time.time()

    cached = _cache.get(cache_key)
    if cached and (now - cached[0] < CACHE_TTL_SECONDS):
        return cached[1]

    ig_lock = get_ig_lock()

    try:
        with ig_lock:
            cl = get_ig_client()
            user_id = cl.user_id_from_username(username)

            # Pedimos más para poder aplicar skip+limit en memoria
            count = skip + limit

            resp = cl.private_request(
                f"feed/user/{user_id}/",
                params={
                    "max_id": "",
                    "count": count,
                    "rank_token": cl.generate_uuid(),
                    "ranked_content": "true",
                },
            )

    except LoginRequired:
        raise HTTPException(401, "IG_LOGIN_REQUIRED")
    except TwoFactorRequired:
        raise HTTPException(401, "IG_TWO_FACTOR_REQUIRED")
    except ChallengeRequired:
        raise HTTPException(403, "IG_CHALLENGE_REQUIRED")
    except PleaseWaitFewMinutes:
        raise HTTPException(429, "IG_RATE_LIMITED")
    except Exception:
        raise HTTPException(502, "IG_FETCH_FAILED")

    items = resp.get("items") or []
    if not isinstance(items, list):
        raise HTTPException(502, "IG_BAD_RESPONSE")

    page = items[skip : skip + limit]

    posts: List[Dict[str, Any]] = []
    for item in page:
        if not isinstance(item, dict):
            continue

        media_id = str(item.get("id") or "")

        # code/shortcode a veces no viene en feed/user. Lo manejamos igual.
        code = item.get("code") or item.get("shortcode") or ""
        product_type = item.get("product_type") or ""  # "clips" / "feed" / etc

        link_instagram = ""
        if code:
            if product_type == "clips":
                link_instagram = f"https://www.instagram.com/reel/{code}/"
            else:
                link_instagram = f"https://www.instagram.com/p/{code}/"

        thumb = _pick_thumbnail_from_item(item)

        posts.append(
            {
                "id": media_id,
                "thumbnail": _proxify_image(thumb),
                "shortcode": str(code),
                "link_instagram": link_instagram,
                "caption": _caption_text(item),
                "taken_at": _taken_at_iso(item),
            }
        )

    payload = {
        "posts": posts,
        "total": len(posts),
        "skip": skip,
        "limit": limit,
    }

    _cache[cache_key] = (now, payload)
    return payload
