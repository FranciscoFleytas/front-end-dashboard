from __future__ import annotations

import time
from collections import OrderedDict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
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

CACHE_TTL_SECONDS = 180
MAX_CACHE_ENTRIES = 150

# key -> (timestamp, payload)
_cache: OrderedDict[str, Tuple[float, Dict[str, Any]]] = OrderedDict()


def _sanitize_username(username: str) -> str:
    cleaned = username.strip().lstrip("@").lower()
    if not cleaned or not all(c.isalnum() or c in "._" for c in cleaned):
        raise HTTPException(400, "INVALID_USERNAME")
    return cleaned


def _cache_get(key: str) -> Optional[Dict[str, Any]]:
    entry = _cache.get(key)
    if not entry:
        return None
    ts, payload = entry
    if time.time() - ts >= CACHE_TTL_SECONDS:
        # expirado
        del _cache[key]
        return None
    _cache.move_to_end(key)
    return payload


def _cache_set(key: str, payload: Dict[str, Any]) -> None:
    _cache[key] = (time.time(), payload)
    _cache.move_to_end(key)
    while len(_cache) > MAX_CACHE_ENTRIES:
        _cache.popitem(last=False)


def _proxify_image(url: str) -> str:
    if not url:
        return ""
    u = url.strip()
    if u.startswith("/api/proxy/image?url="):
        return u
    return f"/api/proxy/image?url={quote(u, safe='')}"


def _caption_text(item: Dict[str, Any]) -> Optional[str]:
    cap = item.get("caption")
    if isinstance(cap, dict):
        txt = cap.get("text")
        return str(txt) if txt else None
    return None


def _taken_at_iso(item: Dict[str, Any]) -> Optional[str]:
    taken_at = item.get("taken_at")
    if isinstance(taken_at, int):
        return datetime.fromtimestamp(taken_at, tz=timezone.utc).isoformat()
    return None


def _pick_smallest_candidate(cands: List[Dict[str, Any]]) -> str:
    # elige el más chico en O(n) (evita sorted O(n log n))
    best = None
    best_area = None
    for c in cands:
        if not isinstance(c, dict):
            continue
        url = c.get("url")
        if not url:
            continue
        w = c.get("width") or 9999
        h = c.get("height") or 9999
        area = w * h
        if best is None or area < best_area:
            best = url
            best_area = area
    return str(best) if best else ""


def _pick_thumbnail_from_item(item: Dict[str, Any]) -> str:
    iv2 = (item.get("image_versions2") or {}).get("candidates") or []
    if isinstance(iv2, list) and iv2:
        thumb = _pick_smallest_candidate(iv2)  # menor resolución
        if thumb:
            return thumb

    carousel = item.get("carousel_media") or []
    if isinstance(carousel, list) and carousel:
        first = carousel[0] or {}
        iv2c = (first.get("image_versions2") or {}).get("candidates") or []
        if isinstance(iv2c, list) and iv2c:
            thumb = _pick_smallest_candidate(iv2c)
            if thumb:
                return thumb

    thumbs = item.get("thumbnail_urls") or []
    if isinstance(thumbs, list) and thumbs:
        return str(thumbs[0])

    return ""


@router.get("/posts")
def get_user_posts(
    username: str = Query(min_length=1, max_length=30),
    limit: int = Query(default=12, ge=1, le=24),
    cursor: Optional[str] = Query(default=None),  # next_max_id de IG
) -> Dict[str, Any]:
    """
    Paginación por cursor:
    - Primera página: cursor=None
    - Siguiente: cursor=<next_cursor devuelto>
    """
    username = _sanitize_username(username)

    cache_key = f"{username}:{limit}:{cursor or 'FIRST'}"
    cached = _cache_get(cache_key)
    if cached:
        return cached

    try:
        with get_ig_lock():
            cl = get_ig_client()
            user_id = cl.user_id_from_username(username)

            params = {
                "count": limit,
                "rank_token": cl.generate_uuid(),
                "ranked_content": "true",
            }
            if cursor:
                params["max_id"] = cursor

            resp = cl.private_request(f"feed/user/{user_id}/", params=params)

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

    next_cursor = resp.get("next_max_id") or None

    posts: List[Dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue

        media_id = str(item.get("id") or "")
        code = item.get("code") or item.get("shortcode") or ""
        product_type = item.get("product_type") or ""

        link_instagram = ""
        if code:
            link_instagram = (
                f"https://www.instagram.com/reel/{code}/"
                if product_type == "clips"
                else f"https://www.instagram.com/p/{code}/"
            )

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
        "limit": limit,
        "next_cursor": next_cursor,
    }
    _cache_set(cache_key, payload)
    return payload
