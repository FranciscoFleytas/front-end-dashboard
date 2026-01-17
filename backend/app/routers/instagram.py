from __future__ import annotations

import re
from urllib.parse import urlparse

import html

import httpx
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

router = APIRouter(prefix="/instagram", tags=["instagram"])

USERNAME_RE = re.compile(r"^[A-Za-z0-9._]{1,30}$")
POST_PATH_RE = re.compile(r"^/(p|reel|tv)/([A-Za-z0-9_-]+)/?")

# Extrae <meta property="og:..."> y <meta name="description">
OG_RE = re.compile(
    r'<meta\s+(?:property|name)="([^"]+)"\s+content="([^"]*)"\s*/?>',
    re.IGNORECASE,
)

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; GrowzaBot/1.0; +http://localhost)",
    "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
}


class NormalizeIn(BaseModel):
    value: str = Field(min_length=2, max_length=300)


def normalize_ig_input(value: str) -> dict:
    v = value.strip()

    # @username
    if v.startswith("@"):
        u = v[1:].strip()
        if not USERNAME_RE.match(u):
            raise HTTPException(400, "USERNAME_INVALID")
        return {"type": "username", "username": u, "url": f"https://www.instagram.com/{u}/"}

    # URL
    if v.startswith("http://") or v.startswith("https://"):
        parsed = urlparse(v)
        host = parsed.netloc.lower().replace("m.", "").replace("www.", "")
        if host != "instagram.com":
            raise HTTPException(400, "NOT_INSTAGRAM_URL")

        m = POST_PATH_RE.match(parsed.path)
        if m:
            kind, shortcode = m.group(1), m.group(2)
            return {
                "type": "post",
                "kind": kind,
                "shortcode": shortcode,
                "url": f"https://www.instagram.com/{kind}/{shortcode}/",
            }

        # profile url: /username/
        path = parsed.path.strip("/")
        if path and USERNAME_RE.match(path):
            return {"type": "username", "username": path, "url": f"https://www.instagram.com/{path}/"}

        raise HTTPException(400, "INSTAGRAM_URL_UNSUPPORTED")

    # bare username
    if USERNAME_RE.match(v):
        return {"type": "username", "username": v, "url": f"https://www.instagram.com/{v}/"}

    raise HTTPException(400, "INPUT_UNSUPPORTED")


async def fetch_og(url: str) -> dict:
    # Nota: Instagram a veces devuelve 403/429. Esto es “best effort”.
    timeout = httpx.Timeout(8.0, connect=5.0)
    async with httpx.AsyncClient(timeout=timeout, headers=DEFAULT_HEADERS, follow_redirects=True) as client:
        r = await client.get(url)
        if r.status_code in (401, 403):
            raise HTTPException(403, "INSTAGRAM_BLOCKED_OR_PRIVATE")
        if r.status_code == 404:
            raise HTTPException(404, "NOT_FOUND")
        if r.status_code >= 400:
            raise HTTPException(502, f"INSTAGRAM_HTTP_{r.status_code}")

        page_html = r.text

    og = {}
    for k, v in OG_RE.findall(page_html):
        # nos interesan principalmente og:title, og:image, og:description, description
        if k.lower() in ("og:title", "og:image", "og:description", "description"):
            og[k.lower()] = v

    title = og.get("og:title")
    image = og.get("og:image")
    desc = og.get("og:description") or og.get("description")

    def normalize_og_value(value: str | None) -> str | None:
        if not value:
            return None
        return html.unescape(value).strip()

    return {
        "url": url,
        "title": normalize_og_value(title),
        "image": normalize_og_value(image),
        "description": normalize_og_value(desc),
    }


def build_label(og_title: str | None, username: str) -> str:
    if not og_title:
        return f"@{username}"

    left = og_title.split("•")[0].strip()
    if not left:
        return f"@{username}"

    handle = f"@{username}"
    if handle.lower() in left.lower():
        return left

    return f"{left} ({handle})"




@router.post("/normalize")
async def normalize(payload: NormalizeIn):
    return normalize_ig_input(payload.value)


@router.get("/profile/preview")
async def profile_preview(username: str = Query(min_length=1, max_length=30)):
    if not USERNAME_RE.match(username):
        raise HTTPException(400, "USERNAME_INVALID")
    url = f"https://www.instagram.com/{username}/"
    return await fetch_og(url)


@router.get("/post/preview")
async def post_preview(url: str = Query(min_length=10, max_length=300)):
    n = normalize_ig_input(url)
    if n["type"] != "post":
        raise HTTPException(400, "POST_URL_REQUIRED")
    return await fetch_og(n["url"])
