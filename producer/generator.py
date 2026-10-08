from datetime import datetime, timezone
import random
import time
from faker import Faker

fake = Faker()
FUNNEL_PAGES = ["home", "product_detail", "cart", "checkout"]
FUNNEL_WEIGHTS = [50, 30, 14, 6]
def generate_event():
    event_type = random.choices(["order", "click", "session"], weights=[25, 50, 25])[0]
    
    # Stamp the exact current UTC time instead of arbitrary historical dates
    timestamp = datetime.now(timezone.utc).isoformat()
    
    if event_type == "order":
        return {
            "type": "order",
            "order_id": f"ORD{random.randint(1000, 9999)}",
            "user_id": f"USR{random.randint(100, 999)}",
            "product_id": f"P{random.randint(10, 19)}",
            "amount": round(random.uniform(10.0, 500.0), 2),
            "timestamp": timestamp
        }
    elif event_type == "click":
        return {
            "type": "click",
            "event_id": fake.uuid4()[:8],
            "user_id": f"USR{random.randint(100, 999)}",
            "page": random.choices(FUNNEL_PAGES, weights=FUNNEL_WEIGHTS)[0],
            "timestamp": timestamp
        }
    else:
        return {
            "type": "session",
            "session_id": fake.uuid4()[:8],
            "user_id": f"USR{random.randint(100, 999)}",
            "status": random.choice(["active", "idle", "logged_out"]),
            "timestamp": timestamp
        }

if __name__ == "__main__":
    while True:
        print(generate_event())
        time.sleep(1)
