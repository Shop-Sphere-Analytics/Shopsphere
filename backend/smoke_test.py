"""
Zero-dependency smoke test for the ShopSphere API.

Usage (with the API already running on :8000):
    python smoke_test.py

Checks every endpoint returns 200 with the documented top-level keys, and
prints a one-line result per endpoint. Exit code 1 if anything failed, so it
can drop straight into CI later if Person D sets up GitHub Actions.
"""

import json
import sys
import urllib.error
import urllib.request

BASE = "http://localhost:8000"

CHECKS = [
    ("/api/health", ["api", "databases"]),
    ("/api/revenue", ["revenue_today", "currency", "orders_today"]),
    ("/api/orders?limit=5", ["orders", "count"]),
    ("/api/active-users", ["active_users", "as_of"]),
    ("/api/top-products?limit=5", ["top_products"]),
    ("/api/click-activity", ["total_clicks", "by_page"]),
    ("/api/user-activity?product_id=P14", ["product_id", "clicks_today", "orders_today", "conversion_rate"]),
    ("/api/recommendations?product_id=P14", ["product_id", "also_bought"]),
]


def check(path, keys):
    try:
        with urllib.request.urlopen(BASE + path, timeout=15) as resp:
            body = json.loads(resp.read().decode())
            status = resp.status
    except urllib.error.HTTPError as e:
        print(f"FAIL {path} -> HTTP {e.code}: {e.read().decode()[:120]}")
        return False
    except Exception as e:
        print(f"FAIL {path} -> {type(e).__name__}: {e}")
        return False

    missing = [k for k in keys if k not in body]
    if status != 200 or missing:
        print(f"FAIL {path} -> HTTP {status}, missing keys {missing}")
        return False

    preview = json.dumps(body)[:100]
    print(f"OK   {path} -> {preview}...")
    return True


if __name__ == "__main__":
    results = [check(p, k) for p, k in CHECKS]
    passed, total = sum(results), len(results)
    print(f"\n{passed}/{total} endpoints passed")
    sys.exit(0 if passed == total else 1)
