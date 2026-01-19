from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
import httpx
from urllib.parse import urlparse

router = APIRouter(prefix="/api/proxy", tags=["proxy"])

ALLOWED_SUFFIXES = (
    ".fbcdn.net",
    ".cdninstagram.com",
)

# Cliente global con pooling: evita crear un client por imagen (MUCHA mejora)
_http = httpx.AsyncClient(
    timeout=15,
    follow_redirects=True,
    limits=httpx.Limits(max_keepalive_connections=50, max_connections=100),
)

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36",
    "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
    "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
    "Referer": "https://www.instagram.com/",
}

@router.get("/image")
async def proxy_image(url: str = Query(..., min_length=10, max_length=4000)):
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()

    if parsed.scheme not in ("http", "https"):
        raise HTTPException(status_code=400, detail="Invalid URL scheme")

    if not any(host.endswith(suf) for suf in ALLOWED_SUFFIXES):
        raise HTTPException(status_code=400, detail="Host not allowed")

    try:
        r = await _http.get(url, headers=_HEADERS)
        if r.status_code != 200:
            raise HTTPException(status_code=404, detail=f"Upstream status {r.status_code}")

        content_type = r.headers.get("content-type", "image/jpeg")

        # Cache fuerte para que el navegador no vuelva a pedir thumbnails ya vistas
        headers = {
            "Cache-Control": "public, max-age=86400",
        }

        return StreamingResponse(r.aiter_bytes(), media_type=content_type, headers=headers)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=502, detail="Proxy fetch failed")
