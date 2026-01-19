from __future__ import annotations

import logging
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

logger = logging.getLogger(__name__)

# Configuración de caché
CACHE_TTL_SECONDS = 180
MAX_CACHE_ENTRIES = 100
_cache: OrderedDict[str, Tuple[float, Dict[str, Any]]] = OrderedDict()


def _sanitize_username(username: str) -> str:
    """
    Limpia y valida el username de Instagram.
    
    Args:
        username: Username a validar
        
    Returns:
        Username sanitizado
        
    Raises:
        HTTPException: Si el username es inválido
    """
    cleaned = username.strip().lstrip('@').lower()
    
    # Validar que solo contenga caracteres permitidos por Instagram
    if not cleaned or not all(c.isalnum() or c in '._' for c in cleaned):
        raise HTTPException(400, "INVALID_USERNAME")
    
    return cleaned


def _add_to_cache(key: str, value: Tuple[float, Dict[str, Any]]) -> None:
    """
    Agrega entrada al caché con límite LRU.
    
    Args:
        key: Clave del caché
        value: Tupla de (timestamp, datos)
    """
    if key in _cache:
        _cache.move_to_end(key)
    
    _cache[key] = value
    
    # Limpiar entradas antiguas si excede el límite
    while len(_cache) > MAX_CACHE_ENTRIES:
        _cache.popitem(last=False)


def _clean_expired_cache() -> None:
    """Elimina entradas de caché expiradas"""
    now = time.time()
    expired = [k for k, (ts, _) in _cache.items() if now - ts >= CACHE_TTL_SECONDS]
    for k in expired:
        del _cache[k]
    
    if expired:
        logger.debug(f"Cleaned {len(expired)} expired cache entries")


def _proxify_image(url: str) -> str:
    """
    Convierte URL de imagen a URL proxy.
    
    Args:
        url: URL original de la imagen
        
    Returns:
        URL proxy o string vacío
    """
    if not url:
        return ""
    
    url = url.strip()
    
    if url.startswith("/api/proxy/image?url="):
        return url
    
    return f"/api/proxy/image?url={quote(url, safe='')}"


def _caption_text(item: Dict[str, Any]) -> Optional[str]:
    """
    Extrae el texto del caption de un post.
    
    Args:
        item: Diccionario con datos del post
        
    Returns:
        Texto del caption o None
    """
    cap = item.get("caption")
    if isinstance(cap, dict):
        txt = cap.get("text")
        return str(txt) if txt else None
    return None


def _pick_thumbnail_from_item(item: Dict[str, Any]) -> str:
    """
    Extrae la URL del thumbnail de un post de Instagram.
    🚀 OPTIMIZACIÓN: Prioriza thumbnails de menor resolución para carga rápida.
    
    Prioridad:
    1) image_versions2.candidates (ordenados por tamaño, menor primero)
    2) carousel_media[0].image_versions2.candidates (menor primero)
    3) thumbnail_urls[0]
    
    Args:
        item: Diccionario con datos del post
        
    Returns:
        URL del thumbnail o string vacío
    """
    # Opción 1: image_versions2 - buscar el thumbnail más pequeño
    iv2 = (item.get("image_versions2") or {}).get("candidates") or []
    if isinstance(iv2, list) and iv2:
        # 🚀 OPTIMIZACIÓN: Ordenar por tamaño (menor primero) para carga rápida
        sorted_candidates = sorted(
            [c for c in iv2 if isinstance(c, dict) and c.get("url")],
            key=lambda x: (x.get("width", 9999) * x.get("height", 9999))
        )
        if sorted_candidates:
            return str(sorted_candidates[0]["url"])

    # Opción 2: carousel_media - buscar el thumbnail más pequeño
    carousel = item.get("carousel_media") or []
    if isinstance(carousel, list) and carousel:
        first = carousel[0] or {}
        iv2c = (first.get("image_versions2") or {}).get("candidates") or []
        if isinstance(iv2c, list) and iv2c:
            sorted_carousel = sorted(
                [c for c in iv2c if isinstance(c, dict) and c.get("url")],
                key=lambda x: (x.get("width", 9999) * x.get("height", 9999))
            )
            if sorted_carousel:
                return str(sorted_carousel[0]["url"])

    # Opción 3: thumbnail_urls
    thumbs = item.get("thumbnail_urls") or []
    if isinstance(thumbs, list) and thumbs:
        return str(thumbs[0])

    return ""


def _taken_at_iso(item: Dict[str, Any]) -> Optional[str]:
    """
    Convierte el timestamp de un post a formato ISO.
    
    Args:
        item: Diccionario con datos del post
        
    Returns:
        Fecha en formato ISO o None
    """
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
    """
    Obtiene los posts de un usuario de Instagram.
    
    🚀 OPTIMIZACIONES:
    - Caché LRU con límite de 100 entradas
    - Limpieza automática de caché expirado
    - Thumbnails de menor resolución para carga rápida
    - Sanitización de username
    - Logging completo para debugging
    
    Args:
        username: Nombre de usuario de Instagram
        limit: Cantidad de posts a retornar
        skip: Cantidad de posts a saltear
        
    Returns:
        Diccionario con posts y metadata de paginación
        
    Raises:
        HTTPException: En caso de error con Instagram API
    """
    # Sanitizar username
    username = _sanitize_username(username)
    
    # 🚀 OPTIMIZACIÓN: Limpiar caché expirado
    _clean_expired_cache()
    
    # 🚀 OPTIMIZACIÓN: Verificar caché
    cache_key = f"{username}:{skip}:{limit}"
    now = time.time()

    cached = _cache.get(cache_key)
    if cached and now - cached[0] < CACHE_TTL_SECONDS:
        logger.debug(f"Cache hit for {cache_key}")
        return cached[1]

    # Pedimos (skip + limit) para poder aplicar skip sin paginación por cursor
    count = skip + limit

    try:
        with get_ig_lock():
            cl = get_ig_client()
            user_id = cl.user_id_from_username(username)

            resp = cl.private_request(
                f"feed/user/{user_id}/",
                params={
                    "max_id": "",
                    "count": count,
                    "rank_token": cl.generate_uuid(),
                    "ranked_content": "true",
                },
            )

    except LoginRequired as e:
        logger.error(f"IG login required for user {username}: {e}")
        raise HTTPException(401, "IG_LOGIN_REQUIRED")
    except TwoFactorRequired as e:
        logger.error(f"IG 2FA required for user {username}: {e}")
        raise HTTPException(401, "IG_TWO_FACTOR_REQUIRED")
    except ChallengeRequired as e:
        logger.warning(f"IG challenge required for user {username}: {e}")
        raise HTTPException(403, "IG_CHALLENGE_REQUIRED")
    except PleaseWaitFewMinutes as e:
        logger.warning(f"IG rate limit for user {username}: {e}")
        raise HTTPException(429, "IG_RATE_LIMITED")
    except Exception as e:
        logger.exception(f"Unexpected error fetching posts for {username}")
        raise HTTPException(502, f"IG_FETCH_FAILED")

    items = resp.get("items") or []
    if not isinstance(items, list):
        logger.error(f"Invalid response format for user {username}")
        raise HTTPException(502, "IG_BAD_RESPONSE")

    # Aplicar paginación
    page = items[skip : skip + limit]

    posts: List[Dict[str, Any]] = []
    for item in page:
        if not isinstance(item, dict):
            continue

        media_id = str(item.get("id") or "")
        code = item.get("code") or item.get("shortcode") or ""
        product_type = item.get("product_type") or ""

        link_instagram = ""
        if code:
            if product_type == "clips":
                link_instagram = f"https://www.instagram.com/reel/{code}/"
            else:
                link_instagram = f"https://www.instagram.com/p/{code}/"

        # 🚀 OPTIMIZACIÓN: Usa thumbnails de menor resolución
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
    
    # 🚀 OPTIMIZACIÓN: Agregar a caché con LRU
    _add_to_cache(cache_key, (now, payload))
    
    logger.info(f"Fetched {len(posts)} posts for user {username} (cache_key: {cache_key})")
    
    return payload