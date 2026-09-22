"""
The actual database reads, kept out of the route functions.

Why a service layer: the WebSocket loop and the REST endpoints need the same
numbers. Putting the queries here means /api/revenue and the live push can
never drift apart.
"""

import time
from datetime import datetime, timezone

from . import config
from .db import (
    orders_collection,
    redis_client,
    cassandra,
    neo4j,
    product_names,
)


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ------------------------------------------------------------------ Redis fast path
def get_revenue() -> dict:
    """
    Redis first - Person B pre-aggregates here precisely so the dashboard never
    re-scans MongoDB on every refresh. Mongo is only the fallback if the keys
    are missing (e.g. the consumer was run before those counters existed).
    """
    try:
        r = redis_client()
        raw_revenue = r.get("orders:revenue_today")
        raw_count = r.get("orders:count")
        if raw_revenue is not None:
            # INCRBYFLOAT accumulates float error - Person B measured
            # "15876.39999999999999947". Round at the edge, every time.
            return {
                "revenue_today": round(float(raw_revenue), 2),
                "currency": config.CURRENCY,
                "orders_today": int(raw_count or 0),
                "source": "redis",
            }
    except Exception:
        pass

    agg = list(
        orders_collection().aggregate(
            [{"$group": {"_id": None, "revenue": {"$sum": "$amount"}, "orders": {"$sum": 1}}}]
        )
    )
    row = agg[0] if agg else {"revenue": 0.0, "orders": 0}
    return {
        "revenue_today": round(float(row.get("revenue", 0.0)), 2),
        "currency": config.CURRENCY,
        "orders_today": int(row.get("orders", 0)),
        "source": "mongodb",
    }


def get_active_users() -> dict:
    count = redis_client().scard("active_users")
    return {"active_users": int(count), "as_of": utc_now()}


# ----------------------------------------------------------------------- MongoDB
def get_recent_orders(limit: int = 10) -> dict:
    """
    Sorted by _id descending, NOT by the event's own timestamp.

    Person A's generator produces random fake dates scattered across decades
    (1981, 2012...), so the embedded timestamp says nothing about recency. A
    MongoDB ObjectId, however, has the insertion time baked into its first four
    bytes - so _id order IS processing order, and its generation_time gives us a
    real "received_at" for free without asking Person B to change anything.
    """
    docs = list(orders_collection().find().sort("_id", -1).limit(limit))
    names = product_names([d.get("product_id") for d in docs])

    orders = []
    for d in docs:
        pid = d.get("product_id", "")
        try:
            received_at = d["_id"].generation_time.strftime("%Y-%m-%dT%H:%M:%SZ")
        except Exception:
            received_at = None
        orders.append(
            {
                "order_id": d.get("order_id", ""),
                "product_id": pid,
                "product_name": names.get(pid, pid),
                "user_id": d.get("user_id", ""),
                "amount": round(float(d.get("amount", 0.0)), 2),
                # Constant: the generator emits no lifecycle status. Kept so
                # Person D's UI column from the original contract still binds.
                "status": "placed",
                "timestamp": d.get("timestamp"),
                "received_at": received_at,
            }
        )
    return {"orders": orders, "count": len(orders)}


def get_top_products(limit: int = 5) -> dict:
    pipeline = [
        {
            "$group": {
                "_id": "$product_id",
                "orders": {"$sum": 1},
                "revenue": {"$sum": "$amount"},
            }
        },
        {"$sort": {"orders": -1}},
        {"$limit": limit},
    ]
    rows = list(orders_collection().aggregate(pipeline))
    names = product_names([r["_id"] for r in rows])
    return {
        "top_products": [
            {
                "product_id": r["_id"],
                "name": names.get(r["_id"], r["_id"]),
                "orders": int(r["orders"]),
                "revenue": round(float(r.get("revenue", 0.0)), 2),
            }
            for r in rows
        ]
    }


def count_orders_for_product(product_id: str) -> int:
    return orders_collection().count_documents({"product_id": product_id})


# ---------------------------------------------------------------------- Cassandra
_click_cache = {"at": 0.0, "value": None}


def get_click_activity() -> dict:
    """
    Cassandra's clicks table is partitioned by event_date, so there is no cheap
    cross-partition aggregate - any total is a scan. At demo volumes that is
    fine; we cap the scan and cache the result for a few seconds so a dashboard
    polling every second cannot hammer the cluster.
    """
    now = time.time()
    if _click_cache["value"] and now - _click_cache["at"] < config.CLICK_CACHE_SECONDS:
        return _click_cache["value"]

    session = cassandra()
    stmt = f"SELECT page FROM clicks LIMIT {config.CLICK_SCAN_LIMIT}"
    counts = {}
    scanned = 0
    for row in session.execute(stmt):
        scanned += 1
        page = row.page or "unknown"
        counts[page] = counts.get(page, 0) + 1

    result = {
        "total_clicks": scanned,
        "by_page": [
            {"page": p, "clicks": c}
            for p, c in sorted(counts.items(), key=lambda kv: kv[1], reverse=True)
        ],
        "scanned_rows": scanned,
        "truncated": scanned >= config.CLICK_SCAN_LIMIT,
    }
    _click_cache["at"] = now
    _click_cache["value"] = result
    return result


def get_user_activity(product_id: str) -> dict:
    """
    Approximate by design, and the approximation is documented.

    Click events carry a page CATEGORY ("product_detail"), never a product_id,
    so no click can be attributed to a specific product. We use site-wide
    product_detail views as the denominator. The one-line fix - Person A adding
    product_id to click events - is written up in HANDOFF.md as future work.
    """
    orders = count_orders_for_product(product_id)
    clicks = 0
    try:
        for row in get_click_activity()["by_page"]:
            if row["page"] == "product_detail":
                clicks = row["clicks"]
                break
    except Exception:
        clicks = 0

    conversion = round(orders / clicks, 4) if clicks else 0.0
    return {
        "product_id": product_id,
        "clicks_today": clicks,
        "orders_today": orders,
        "conversion_rate": conversion,
        "approximate": True,
    }


# -------------------------------------------------------------------------- Neo4j
_RECS_CYPHER = """
MATCH (:Product {id: $pid})<-[:BOUGHT]-(u:User)-[:BOUGHT]->(rec:Product)
WHERE rec.id <> $pid
RETURN rec.id AS product_id, count(DISTINCT u) AS strength
ORDER BY strength DESC
LIMIT $limit
"""


def get_recommendations(product_id: str, limit: int = 5) -> dict:
    """
    Note the property name: `id`, not `product_id`.

    Person B's handoff document writes this query as
    `MATCH (:Product {product_id: $pid})`, but neo4j_writer.py actually MERGEs
    nodes as `(:Product {id: ...})`. The documented query silently returns zero
    rows against the real graph. This version matches the data that is there.
    """
    driver = neo4j()
    with driver.session() as session:
        rows = session.run(_RECS_CYPHER, pid=product_id, limit=limit).data()

    ids = [r["product_id"] for r in rows] + [product_id]
    names = product_names(ids)
    return {
        "product_id": product_id,
        "name": names.get(product_id, product_id),
        "also_bought": [
            {
                "product_id": r["product_id"],
                "name": names.get(r["product_id"], r["product_id"]),
                "strength": int(r["strength"]),
            }
            for r in rows
        ],
    }


# ------------------------------------------------------------- live snapshot (WS)
def live_snapshot() -> dict:
    """One combined read of everything the live dashboard header shows."""
    revenue = {"revenue_today": 0.0, "orders_today": 0}
    active = 0
    try:
        revenue = get_revenue()
    except Exception:
        pass
    try:
        active = get_active_users()["active_users"]
    except Exception:
        pass
    return {
        "revenue_today": revenue.get("revenue_today", 0.0),
        "orders_today": revenue.get("orders_today", 0),
        "active_users": active,
        "as_of": utc_now(),
    }
