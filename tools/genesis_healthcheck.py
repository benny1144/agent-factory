from __future__ import annotations

import sys

# Ensure repo root + src on path for consistency if needed
try:
    import tools.startup  # noqa: F401
except Exception:
    pass

import httpx


def main() -> int:
    url = "http://127.0.0.1:5055/health"
    try:
        r = httpx.get(url, timeout=5.0)
        if r.status_code == 200:
            print(f"[OK] {url} -> 200 OK")
            return 0
        print(f"[FAIL] {url} -> {r.status_code}")
        return 2
    except Exception as e:
        print(f"[ERROR] {url} -> {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
