import json
import time
from kafka import KafkaProducer
from generator import generate_event

# Explicitly pass api_version and connection timeout
producer = KafkaProducer(
    bootstrap_servers=['127.0.0.1:9092'],
    api_version=(7, 3, 0),
    request_timeout_ms=30000,
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

print("Starting Kafka Producer... Press Ctrl+C to stop.")

try:
    while True:
        event = generate_event()
        topic_name = event["type"] + "s"
        
        producer.send(topic_name, value=event)
        print(f"Sent to topic '{topic_name}': {event}")
        time.sleep(0.5)
except KeyboardInterrupt:
    print("\nProducer stopped.")
