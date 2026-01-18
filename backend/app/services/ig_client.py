from __future__ import annotations

import os
import threading
from typing import Optional

from instagrapi import Client

from ..settings import settings

_ig_client: Optional[Client] = None
_ig_lock = threading.Lock()


def get_ig_lock() -> threading.Lock:
    return _ig_lock


def get_ig_client() -> Client:
    global _ig_client
    if _ig_client is not None:
        return _ig_client

    cl = Client()
    settings_path = settings.IG_SETTINGS_PATH
    if settings_path and os.path.exists(settings_path):
        cl.load_settings(settings_path)

    if not settings.IG_USER or not settings.IG_PASS:
        raise RuntimeError("IG_CREDENTIALS_MISSING")

    cl.login(settings.IG_USER, settings.IG_PASS)

    if settings_path:
        dir_path = os.path.dirname(settings_path)
        if dir_path:
            os.makedirs(dir_path, exist_ok=True)
        cl.dump_settings(settings_path)

    _ig_client = cl
    return cl
