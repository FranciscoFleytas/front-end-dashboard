from __future__ import annotations

import asyncio
import logging
import time
from collections import OrderedDict
from typing import Any, Dict, Optional
from urllib.parse import quote

from fastapi import APIRouter, HTTPException, Query
from instagrapi.exceptions import (
    ChallengeRequired,
    LoginRequired,
    PleaseWaitFewMinutes,
    TwoFactorRequired,
)

# Reutiliza estas funciones desde tu router instagram existente:
# - normalize_ig_input(value) -> dict
# - fetch_og(url) -> dict (best effort)
from .instagram import build_label, fetch_og, normalize_ig_input
from ..services.ig_client import get_ig_client, get_ig_lock

router = APIRouter(prefix="/api/users", tags=["users"])

logger = logging.getLogger(__name__)

# Configuración de caché
CACHE_TTL_SECONDS = 90
MAX_SEARCH_CACHE = 50
_search_cache: OrderedDict[str, tuple[float, list[Dict[str, Any]]]] = OrderedDict()

# 🚀 OPTIMIZACIÓN: Timeout para fetch de OG tags
OG_FETCH_TIMEOUT = 5.0


def _sanitize_username(username: str) -> str:
    """
    Limpia y valida el username de Instagram.
    
    Args:
        username: Username a validar
        
    Returns:
        Username sanitizado o string vacío si es inválido
    """
    cleaned = username.strip().lstrip('@')
    
    # Validar que solo contenga caracteres permitidos por Instagram
    if not cleaned or not all(c.isalnum() or c in '._' for c in cleaned):
        return ""
    
    return cleaned


def _add_to_search_cache(key: str, value: tuple[float, list[Dict[str, Any]]]) -> None:
    """
    Agrega entrada al caché de búsqueda con límite LRU.
    
    Args:
        key: Clave del caché
        value: Tupla de (timestamp, resultados)
    """
    if key in _search_cache:
        _search_cache.move_to_end(key)
    
    _search_cache[key] = value
    
    # 🚀 OPTIMIZACIÓN: Limpiar entradas antiguas si excede el límite (LRU)
    while len(_search_cache) > MAX_SEARCH_CACHE:
        _search_cache.popitem(last=False)


def _clean_expired_search_cache() -> None:
    """Elimina entradas de caché de búsqueda expiradas"""
    now = time.time()
    expired = [k for k, (ts, _) in _search_cache.items() if now - ts >= CACHE_TTL_SECONDS]
    for k in expired:
        del _search_cache[k]
    
    if expired:
        logger.debug(f"Cleaned {len(expired)} expired search cache entries")


def _proxify_image_url(url: Optional[str]) -> str:
    """
    Convierte URL de imagen a URL proxy.
    
    Args:
        url: URL original de la imagen
        
    Returns:
        URL proxy o string vacío
    """
    if not url:
        return ""
    
    url = str(url).strip()
    
    if not url or url.startswith("/api/proxy/image?url="):
        return url
    
    return f"/api/proxy/image?url={quote(url, safe='')}"


@router.get("/search")
async def search_user(
    q: str = Query(min_length=2, max_length=80),
    email: Optional[str] = Query(default=None, max_length=120),
) -> Dict[str, Any]:
    """
    Devuelve un JSON estilo autocomplete para un perfil de Instagram.
    Opción A: sin login, best-effort OG preview.
    
    🚀 OPTIMIZACIONES:
    - Timeout de 5 segundos en fetch de OG tags para evitar bloqueos
    - Manejo de errores robusto
    - Logging completo
    
    Args:
        q: Query de búsqueda (username o URL)
        email: Email opcional del usuario
        
    Returns:
        Diccionario con información del perfil
        
    Raises:
        HTTPException: Si el input no es un username válido
    """
    try:
        norm = normalize_ig_input(q)
    except Exception as e:
        logger.warning(f"Failed to normalize input '{q}': {e}")
        raise HTTPException(400, "INVALID_INPUT")

    if norm["type"] != "username":
        # Si pegaron un link de post, no es un "user search"
        raise HTTPException(400, "USERNAME_REQUIRED")

    username = norm["username"]
    url = norm["url"]

    og = None
    try:
        # 🚀 OPTIMIZACIÓN: Timeout de 5 segundos para evitar bloqueos
        og = await asyncio.wait_for(fetch_og(url), timeout=OG_FETCH_TIMEOUT)
    except asyncio.TimeoutError:
        logger.warning(f"OG fetch timeout for {url}")
        og = None
    except Exception as e:
        logger.debug(f"OG fetch failed for {url}: {e}")
        og = None

    label = build_label(None, username)
    avatar_src = ""

    if og:
        label = build_label(og.get("title"), username)
        avatar_src = og.get("image") or ""

    # ID estable para UI (NO es id real de IG)
    stable_id = (abs(hash(username)) % 10_000_000) or 1

    return {
        "id": stable_id,
        "label": label,
        "suffix": email or username,  # Email lo pone el cliente; fallback al username
        "link_instagram": url,
        "avatar": {"src": _proxify_image_url(avatar_src)},
    }


@router.get("/search/list")
def search_users_list(
    q: str = Query(min_length=1, max_length=80),
    limit: int = Query(default=10, ge=1, le=20),
) -> list[Dict[str, Any]]:
    """
    Busca usuarios de Instagram usando la API de Instagram.
    Retorna una lista de resultados para autocomplete.
    
    🚀 OPTIMIZACIONES:
    - Caché LRU con límite de 50 entradas
    - Limpieza automática de caché expirado
    - Sanitización de queries
    - Manejo de errores granular por usuario
    - Logging completo
    
    Args:
        q: Query de búsqueda
        limit: Cantidad máxima de resultados
        
    Returns:
        Lista de diccionarios con información de usuarios
        
    Raises:
        HTTPException: En caso de error con Instagram API
    """
    # 🚀 OPTIMIZACIÓN: Sanitizar query
    query = _sanitize_username(q)
    
    # Retornar lista vacía si el query es inválido o muy corto
    if not query or len(query) < 2:
        return []
    
    # 🚀 OPTIMIZACIÓN: Limpiar caché expirado
    _clean_expired_search_cache()
    
    # 🚀 OPTIMIZACIÓN: Verificar caché
    cache_key = f"{query.lower()}:{limit}"
    cached = _search_cache.get(cache_key)
    now = time.time()
    
    if cached and now - cached[0] < CACHE_TTL_SECONDS:
        logger.debug(f"Search cache hit for '{query}'")
        return cached[1]

    try:
        with get_ig_lock():
            cl = get_ig_client()
            users = cl.search_users(query)
            
    except PleaseWaitFewMinutes as e:
        logger.warning(f"IG rate limit for search '{query}': {e}")
        raise HTTPException(429, "IG_RATE_LIMITED")
    except (LoginRequired, ChallengeRequired, TwoFactorRequired) as e:
        logger.error(f"IG login/auth issue for search '{query}': {e}")
        raise HTTPException(409, "IG_LOGIN_REQUIRED")
    except Exception as e:
        logger.exception(f"Unexpected error searching for '{query}'")
        raise HTTPException(502, "IG_SEARCH_FAILED")

    results = []
    for user in users[:limit]:
        try:
            username = getattr(user, "username", "") or ""
            if not username:
                continue
            
            full_name = (getattr(user, "full_name", "") or "").strip()
            label = f"{full_name} (@{username})" if full_name else f"@{username}"
            
            user_id = getattr(user, "pk", None)
            stable_id = user_id or ((abs(hash(username)) % 10_000_000) or 1)
            
            avatar_src = getattr(user, "profile_pic_url", None) or ""
            proxied_avatar = _proxify_image_url(avatar_src)

            results.append(
                {
                    "id": stable_id,
                    "label": label,
                    "suffix": f"@{username}",
                    "link_instagram": f"https://www.instagram.com/{username}/",
                    "avatar": {"src": proxied_avatar},
                }
            )
        except Exception as e:
            # 🚀 OPTIMIZACIÓN: Manejo de errores granular - no fallar todo si un usuario falla
            logger.warning(f"Error processing user result: {e}")
            continue

    # 🚀 OPTIMIZACIÓN: Agregar a caché con LRU
    _add_to_search_cache(cache_key, (now, results))
    
    logger.info(f"Search for '{query}' returned {len(results)} results (cache_key: {cache_key})")
    
    return results