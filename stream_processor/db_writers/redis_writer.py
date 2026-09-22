"""
Redis is the "instant numbers" database: sub-millisecond reads for
whatever the live dashboard needs right now.

write_session()        -> required. Tracks who's currently active.
update_order_metrics()  -> recommended, not required by the base plan.
    Pre-aggregating revenue/order-count/recent-orders here means Person C's
    /api/revenue and /api/orders endpoints can read one instant Redis value
    instead of re-scanning MongoDB on every dashboard refresh. This is the
    same "pre-aggregate in the stream processor, use Redis for anything
    instant" tip from the project plan's own challenges table — mention it
    to Person C so they know these keys exist and use them.
"""

import redis

r = redis.Redis(host="localhost", port=6379, decode_responses=True)


def write_session(event: dict):
    user_id = event["user_id"]
    status = event["status"]
    if status == "active":
        r.sadd("active_users", user_id)
    else:  # idle or logged_out
        r.srem("active_users", user_id)


def update_order_metrics(event: dict):
    r.incr("orders:count")
    r.incrbyfloat("orders:revenue_today", event["amount"])
    r.lpush("orders:recent", f'{event["order_id"]}|{event["amount"]}')
    r.ltrim("orders:recent", 0, 19)  # keep only the latest 20 for the live feed
