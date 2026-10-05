# Person A → Person B

## What I built
A Faker-based event generator (`generator.py`) and a Kafka producer
(`kafka_producer.py`) that publishes e-commerce events to Kafka.

## Kafka topics
- `orders`, `clicks`, `sessions` (topic name = event `type` + "s")
- Broker: `127.0.0.1:9092`

## How to run
1. From the repo root: `docker compose up -d` (Kafka runs from the root compose file)
2. `cd producer`
3. `pip install -r requirements.txt`
4. `python kafka_producer.py`

## Expected result
About 2 events/second printed as `Sent to topic '<topic>': {...}`.
Verify with:
`docker exec kafka kafka-console-consumer --bootstrap-server localhost:9092 --topic orders --from-beginning`

## Event schemas
See `docs/event-schema.md`. The `type` field decides routing, so don't rename it.
Orders use `product_id` P10–P19 (matches the seeded products collection).
Timestamps are current UTC (ISO 8601).

## Known issues
- Clicks have no `product_id`, so per-product click counts aren't possible (future work).
