# Event Schema — ShopSphere

Source: Person A's producer (`producer/generator.py`), confirmed by Person B
by actually running it and inspecting real output, not from the original
plan's placeholder example.

Kafka topics: `orders`, `clicks`, `sessions` — one topic per event `type`.

## orders

```json
{ "type": "order", "order_id": "ORD5690", "user_id": "USR816", "product_id": "P14", "amount": 462.82, "timestamp": "2026-09-22T14:52:36Z" }
```

Routed to: MongoDB (`orders` collection, stored as-is), Neo4j (`(User)-[:BOUGHT]->(Product)`), and Redis (running counters).

## clicks

```json
{ "type": "click", "event_id": "3623bd25", "user_id": "USR278", "page": "product_detail", "timestamp": "2026-09-22T14:41:47Z" }
```

`page` is a category label, not a URL path. Observed values: `home`,
`product_detail`, `cart`, `checkout`.

> **Known limitation:** clicks carry a page category, never a `product_id`,
> so per-product click counts can't be derived from this data as-is. The
> backend's `/api/user-activity` discloses this with `"approximate": true`;
> `/api/click-activity` gives the honest, real per-page breakdown instead.
> The real fix — adding `product_id` to click events upstream — is logged as
> future work, not done this cycle.

Routed to: Cassandra (`clicks` table, partitioned by day, clustered by time).

## sessions

```json
{ "type": "session", "session_id": "481df8fb", "user_id": "USR389", "status": "active", "timestamp": "2026-09-22T14:49:20Z" }
```

`status` is one of: `active`, `idle`, `logged_out`.

Routed to: Redis (`active_users` set — added on `active`, removed otherwise).

## Timestamps

`generator.py` originally used `fake.iso8601()`, which produced random dates
spanning 1970–present (events in the same minute could be dated 1981 and
2012). This was fixed on 2026-09-22 to emit the real current UTC time instead.

- Any event generated **before** the fix still carries an old-style random date
- Any event generated **after** the fix has a real, chronological timestamp
- The backend does not trust this field for "today" windowing regardless —
  see `docs/api-contract.md`'s notes on `received_at`
