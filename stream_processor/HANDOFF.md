Person B → Person C
What I built
A Kafka consumer (`consumer.py`) that reads every event Person A's producer sends
across the `orders`, `clicks`, and `sessions` topics, and routes each one into the
right database:
```
order   -> MongoDB (orders collection)
        -> Neo4j   ((User)-[:BOUGHT]->(Product))
        -> Redis   (fast-path counters, see below)
click   -> Cassandra (clicks table)
session -> Redis     (session status + active_users set)
```
Also included: `seed_products.py`, a one-time script that seeds a `products`
lookup collection in MongoDB (product_id -> name/category), since the producer
only ever emits raw product IDs like `P14`.
Event schema (as actually produced by Person A — confirmed by running it)
Kafka topics: `orders`, `clicks`, `sessions`.
orders
```json
{ "type": "order", "order_id": "ORD5690", "user_id": "USR816", "product_id": "P14", "amount": 462.82, "timestamp": "1981-07-09T14:52:36" }
```
clicks — note: `page` is a category label, not a URL path
```json
{ "type": "click", "event_id": "3623bd25", "user_id": "USR278", "page": "product_detail", "timestamp": "2012-04-06T14:41:47" }
```
Observed `page` values: `home`, `product_detail`, `cart`, `checkout`.
> **Downstream note:** because clicks carry a page category and never a
> product_id, per-product click counts aren't derivable from this table as-is.
> Person C's backend handles this explicitly — `/api/user-activity` returns
> `"approximate": true` and uses a site-wide proxy, and a separate
> `/api/click-activity` endpoint gives the honest, real per-page breakdown
> instead of pretending to be per-product. If we want true per-product click
> tracking, the actual fix is adding `product_id` to click events upstream in
> Person A's generator — logged as future work, not done this cycle.
sessions
```json
{ "type": "session", "session_id": "481df8fb", "user_id": "USR389", "status": "active", "timestamp": "2004-01-17T11:49:20" }
```
`status` is one of: `active`, `idle`, `logged_out`.
> Note: timestamps are randomly generated fake data scattered across past and
> future years — don't build any "last hour" / "today" trend logic off this
> field. Anything "live" on the dashboard should be driven by processing
> order (when the consumer handles the event), not the embedded timestamp.
>
> **Downstream note:** Person C's backend solves this for order recency by
> sorting MongoDB's `orders` collection by `_id` (descending) instead of the
> `timestamp` field, and deriving a real `received_at` from the ObjectId's
> built-in `generation_time` — a genuine insertion-order timestamp, free,
> with no change needed here. Worth reusing this pattern anywhere else "most
> recent" matters.
Database schemas — what's actually in each one
MongoDB (`shopsphere` database)
`orders` collection — one document per order event, written as-is:
```json
{ "_id": "...", "type": "order", "order_id": "ORD5690", "user_id": "USR816", "product_id": "P14", "amount": 462.82, "timestamp": "1981-07-09T14:52:36" }
```
`products` collection — seeded once via `seed_products.py`, 10 products (`P10`–`P19`):
```json
{ "product_id": "P10", "name": "Laptop", "category": "Electronics" }
```
> Only P10–P19 have names. Any product_id outside that range (generator produces
> up to roughly P50) won't have a match — fall back to showing the raw ID.
Cassandra (`shopsphere` keyspace, `clicks` table)
```sql
CREATE TABLE clicks (
  event_date text,
  ts timestamp,
  event_id text,
  user_id text,
  page text,
  PRIMARY KEY (event_date, ts, event_id)
) WITH CLUSTERING ORDER BY (ts DESC);
```
Sample row:
```
event_date | ts                              | event_id | page           | user_id
2012-04-06 | 2012-04-06 14:41:47.000000+0000 | 3623bd25 | product_detail | USR278
```
Redis
Key	Type	Purpose
`active_users`	Set	`user_id`s with a recent `active` session status
`orders:count`	String (INCR)	Total orders processed
`orders:revenue_today`	String (INCRBYFLOAT)	Running revenue total
> **Known float-precision issue:** `orders:revenue_today` accumulates floating-point
> error over many INCRBYFLOAT calls (observed value: `"15876.39999999999999947"`).
> Round to 2 decimals when displaying — don't trust the raw string as-is.
For live dashboard numbers, read these Redis keys directly instead of
querying MongoDB/Cassandra — they're pre-aggregated and much faster for
real-time use. Fall back to MongoDB only for full order details or history.
Neo4j (bolt://localhost:7687, user `neo4j`, password `password`)
```
(:User {id})-[:BOUGHT]->(:Product {id})
```
> **Corrected 2026-09-22:** this previously read `(:User {user_id})-[:BOUGHT]->
> (:Product {product_id})`, which does not match what `neo4j_writer.py` actually
> writes. The real property key on both node types is `id`. The query below was
> silently returning zero rows against the real graph — Cypher doesn't error on
> a missing property, it just matches nothing. Caught by Person C while building
> the recommendations endpoint; fixed here to match `neo4j_writer.py`, which was
> always correct — only this doc was wrong.
Recommendation query ("customers who bought X also bought Y"):
```cypher
MATCH (:Product {id: $pid})<-[:BOUGHT]-(u:User)-[:BOUGHT]->(rec:Product)
WHERE rec.id <> $pid
RETURN rec.id AS product_id, count(*) AS strength
ORDER BY strength DESC LIMIT 5
```
Confirmed against the real graph two ways: the underlying `User -> Product`
pairs are visible via Neo4j Browser table view (e.g. `USR578 -> P40`,
`USR188 -> P22`), and this corrected query shape is what Person C's
`/api/recommendations` endpoint runs in production.
[ ] Re-ran this exact query with a real `$pid` value and confirmed non-empty results (do this yourself before your next PR — inherited confirmation from a teammate's endpoint isn't the same as verifying it here)
How to run this locally
Start all services from the repo root (not any subfolder):
```bash
   cd shopsphereanalytics
   docker compose up -d
   docker ps   # confirm 6 containers: kafka, zookeeper, mongodb, cassandra, redis, neo4j
   ```
Wait ~45 seconds before connecting to Cassandra — it takes a while to
become ready even though Docker shows it as "Up" immediately.
Install dependencies:
```bash
   cd stream_processor
   pip install -r requirements.txt
   pip install pyasyncore   # see Known Issues #2 below
   ```
Seed product names (one-time):
```bash
   python seed_products.py   # or: py seed_products.py on Windows
   ```
Run Person A's producer (separate terminal) and this consumer together:
```bash
   # terminal 1
   cd producer && python kafka_producer.py
   # terminal 2
   cd stream_processor && python consumer.py
   ```
Verify data landed (see verification commands per database above, or just
spot-check with `docker exec -it mongodb mongosh --eval "db.getSiblingDB('shopsphere').orders.countDocuments()"`).
Known issues / gotchas (read this before you debug from scratch)
Port 27017 conflict on Windows: if you have MongoDB installed natively
on your machine (not just via Docker), it silently binds to
`127.0.0.1:27017` alongside Docker's container on the same port. Python's
`mongodb://localhost:27017/` connects to whichever one resolves first —
which may NOT be the Docker container, causing writes to silently succeed
against the wrong database while Docker's Mongo stays empty. Check with
`netstat -ano | grep 27017` — if you see two PIDs, stop the native service:
`net stop MongoDB` (as Administrator), then `sc config MongoDB start=disabled`
to stop it recurring on reboot.
Cassandra driver fails to import on Python 3.12+ (including 3.14):
the driver's default connection class relies on the `asyncore` module,
which was removed from the standard library in 3.12. Fix: `pip install pyasyncore` — this restores an importable `asyncore` shim and the driver's
normal auto-detection succeeds without any code changes needed.
Data does not persist across `docker compose down` by default — the
compose file now includes named volumes (`mongo_data`, `cassandra_data`,
`neo4j_data`) for exactly this reason. If you rebuild the compose file from
scratch, make sure to carry these over or data will be lost on every restart.
`docker compose down` + `up` needs a run from the repo root — running
it from inside a subfolder changes the Compose "project name" and can spin
up a second, separate set of containers with the same container names,
causing a naming conflict error.
Neo4j property names are `id`, not `user_id`/`product_id` — see the
corrected Neo4j section above. If you're writing any new Cypher against
this graph, match on `id`.
Confirmation checklist
[x] Kafka consumer running, reads all 3 topics
[x] MongoDB: orders + products collections populated, correct shape
[x] Cassandra: clicks table populated, correct shape
[x] Redis: active_users set + order counters populated
[x] Neo4j: BOUGHT relationships populated, confirmed via table view
[ ] Neo4j: corrected recommendation query re-verified with a real `$pid` (see above)
[x] Data persists across `docker compose down` / `up` (verified: count
unchanged across a full teardown/recreate with nothing writing)
[x] docker-compose.yml uses named volumes for all 3 stateful databases
