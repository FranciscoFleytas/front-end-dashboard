from __future__ import annotations

from backend.app.db import connect, init_db
from backend.app.settings import settings


def main() -> None:
    conn = connect(settings.DB_PATH)
    try:
        init_db(conn)
    finally:
        conn.close()
    print(f"DB initialized at {settings.DB_PATH}")


if __name__ == "__main__":
    main()
