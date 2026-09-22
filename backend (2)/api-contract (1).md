# API Contract — ShopSphere (v2)

Owner: Person C. Base URL: `http://localhost:8000`.
Interactive docs: `http://localhost:8000/docs` · Spec: `http://localhost:8000/openapi.json`

> **v2 changes (Person C, after building against the real pipeline).** v1 was
> written on Day 1 with placeholder numbers, before anyone had seen what Person
> A's generator actually emits. Four fields in v1 don't exist in the data. They
> are corrected below and each change is explained. Two endpoints were added.
> Person D's dashboard should be built against **this** file.

## GET /api/health
New in v2. Per-database liveness — call this first when debugging.
```json
{ "api": "up", "databases": { "mongodb": "up", "redis": "up", "cassandra": "up", "neo4j": "up" } }
```

## GET /api/revenue
Source: Redis (pre-aggregated counters).
```json
{ "revenue_today": 15876.40, "currency": "INR", "orders_today": 342, "source": "redis" }
```
`source` is `"mongodb"` if the Redis counters are missing. Despite the field
name, this is an all-time running total — the generator's timestamps are not
usable for day-windowing (see Notes).

## GET /api/orders?limit=10
Source: MongoDB. `limit` 1–100, default 10. Newest first by insertion order.
```json
{
  "orders": [
    {
      "order_id": "ORD5690",
      "product_id": "P14",
      "product_name": "Monitor",
      "user_id": "USR816",
      "amount": 462.82,
      "status": "placed",
      "timestamp": "1981-07-09T14:52:36",
      "received_at": "2026-09-21T10:24:11Z"
    }
  ],
  "count": 1
}
```
- `product_name` — resolved from MongoDB `products`; falls back to the raw id
  for anything outside the seeded P10–P19.
- `status` — **constant `"placed"`**. The generator emits no order lifecycle.
- `timestamp` — the generator's fake date. Do not sort or filter on it.
- `received_at` — **new in v2**, real processing time from the MongoDB
  ObjectId. This is the only trustworthy time field.

## GET /api/active-users
Source: Redis (`SCARD active_users`).
```json
{ "active_users": 87, "as_of": "2026-09-21T10:25:00Z" }
```

## GET /api/top-products?limit=5
Source: MongoDB aggregation. `limit` 1–50, default 5.
```json
{
  "top_products": [
    { "product_id": "P14", "name": "Monitor", "orders": 128, "revenue": 41233.50 },
    { "product_id": "P33", "name": "P33", "orders": 96, "revenue": 30880.10 }
  ]
}
```
`revenue` is additive over v1. `name` falls back to the product id.

## GET /api/click-activity
New in v2. Source: Cassandra. The honest click data — clicks are recorded per
page category, not per product.
```json
{
  "total_clicks": 1240,
  "by_page": [
    { "page": "home", "clicks": 512 },
    { "page": "product_detail", "clicks": 340 },
    { "page": "cart", "clicks": 236 },
    { "page": "checkout", "clicks": 152 }
  ],
  "scanned_rows": 1240,
  "truncated": false
}
```
`truncated` is `true` if the scan hit its row cap and the counts are a sample.

## GET /api/user-activity?product_id=P14
Source: Cassandra + MongoDB. **Approximate — see the flag.**
```json
{ "product_id": "P14", "clicks_today": 340, "orders_today": 22, "conversion_rate": 0.0647, "approximate": true }
```
Click events carry a page category, never a `product_id`, so clicks cannot be
attributed to one product. `orders_today` is exact for the product;
`clicks_today` is the site-wide `product_detail` count. `approximate` is always
`true` until click events gain a `product_id` upstream.

## GET /api/recommendations?product_id=P14&limit=5
Source: Neo4j. `limit` 1–20, default 5.
```json
{
  "product_id": "P14",
  "name": "Monitor",
  "also_bought": [
    { "product_id": "P19", "name": "Speaker", "strength": 34 },
    { "product_id": "P33", "name": "P33", "strength": 21 }
  ]
}
```
`strength` = distinct users who bought both products. An empty `also_bought` is
a valid response, not an error.

## WS /ws/live-updates
Push-only; the client never sends. One snapshot on connect, then a message only
when a value changes (checked every 2s).
```json
{ "event": "snapshot", "revenue_today": 15876.40, "orders_today": 342, "active_users": 87, "as_of": "2026-09-21T10:25:00Z" }
```
```json
{ "event": "new_order", "revenue_today": 16339.22, "orders_today": 343, "active_users": 88, "as_of": "2026-09-21T10:25:02Z" }
```
`event` ∈ `snapshot` (on connect) · `new_order` (order count rose) · `tick`
(revenue or active users moved). All messages carry the same four fields.

## Conventions
- Money is a float in INR, rounded to 2 decimal places at the API boundary
  (Redis `INCRBYFLOAT` drift is absorbed here, not by the client).
- `as_of` / `received_at` are ISO 8601 UTC and are server-generated — trustworthy.
- `timestamp` on an order is generator-produced fake data and is **not** chronological.
- Errors: `{ "error": "message here" }` with a non-200 status. `503` = a
  database is down or still starting. `422` = invalid query parameter.
- CORS is enabled for `http://localhost:5173` and `http://localhost:3000`.
- Any new endpoint or field change must be added here first — Person D's
  dashboard is built against this exact shape.
