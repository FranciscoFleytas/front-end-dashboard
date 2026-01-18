from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
import httpx
from urllib.parse import urlparse

router = APIRouter(prefix="/api/proxy", tags=["proxy"])

ALLOWED_SUFFIXES = (
    ".fbcdn.net",
    ".cdninstagram.com",
)

@router.get("/image")
async def proxy_image(url: str = Query(..., min_length=10, max_length=4000)):
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()

    if parsed.scheme not in ("http", "https"):
        raise HTTPException(status_code=400, detail="Invalid URL scheme")

    if not any(host.endswith(suf) for suf in ALLOWED_SUFFIXES):
        raise HTTPException(status_code=400, detail="Host not allowed")

    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36",
        "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
        "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
        "Referer": "https://www.instagram.com/",
    }

    async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
        r = await client.get(url, headers=headers)
        if r.status_code != 200:
            raise HTTPException(status_code=404, detail=f"Upstream status {r.status_code}")

        content_type = r.headers.get("content-type", "image/jpeg")
        return StreamingResponse(r.aiter_bytes(), media_type=content_type)
