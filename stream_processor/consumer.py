"""
Stream Processor — Person B
Reads every event Person A's producer sends to Kafka, looks at its "type",
and routes it to the database that's the right fit for that kind of data.

    orders   -> MongoDB   (flexible order documents)
             -> Neo4j     (User -[:BOUGHT]-> Product relationship)
    clicks   -> Cassandra (high-volume, time-ordered event log)
    sessions -> Redis     (instant active-users tracking)

Run this only after all 4 databases + Kafka are up (docker compose up -d)
and only after confirming Person A's producer is actually sending events.
"""

import json
from kafka import KafkaConsumer

from db_writers.mongo_writer import write_order
from db_writers.cassandra_writer import write_click
from db_writers.redis_writer import write_session, update_order_metrics
from db_writers.neo4j_writer import write_purchase_relationship

TOPICS = ["orders", "clicks", "sessions"]

consumer = KafkaConsumer(
    *TOPICS,
    bootstrap_servers=["127.0.0.1:9092"],
    auto_offset_reset="earliest",   # replay from the start of the topic on first run
    enable_auto_commit=True,
    group_id="stream-processor-group",
    value_deserializer=lambda v: json.loads(v.decode("utf-8")),
)

print(f"Stream processor started. Listening on topics: {TOPICS}")
print("Waiting for events... (Ctrl+C to stop)\n")

try:
    for message in consumer:
        event = message.value
        event_type = event.get("type")

        try:
            if event_type == "order":
                write_order(event)                     # -> MongoDB
                write_purchase_relationship(event)      # -> Neo4j
                update_order_metrics(event)             # -> Redis (recommended, see HANDOFF.md)
                print(f"[orders]   -> MongoDB + Neo4j   | {event['order_id']} (${event['amount']})")

            elif event_type == "click":
                write_click(event)                      # -> Cassandra
                print(f"[clicks]   -> Cassandra         | {event['user_id']} viewed {event['page']}")

            elif event_type == "session":
                write_session(event)                    # -> Redis
                print(f"[sessions] -> Redis             | {event['user_id']} is {event['status']}")

            else:
                print(f"Unrecognized event type '{event_type}', skipping: {event}")

        except Exception as e:
            # Don't let one bad event kill the whole consumer — log it and keep going.
            print(f"ERROR processing event {event}: {e}")

except KeyboardInterrupt:
    print("\nStream processor stopped.")
