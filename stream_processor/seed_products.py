"""
OPTIONAL but recommended.

Person A's generator only ever produces a product_id like "P23" — there's
no product catalog anywhere in the pipeline. The sample final dashboard
shows real product names ("Laptop", "Phone", "Headset"), so someone needs
to provide that name mapping. MongoDB already holds "Products" in the
architecture table, so it's the natural place for it.

Run this once after MongoDB is up:
    python seed_products.py

Person C can then look up a name for any product_id when building the
/api/top-products endpoint, and fall back to showing the raw ID for any
product_id (P10-P50) that isn't in this list.
"""

from pymongo import MongoClient

client = MongoClient("mongodb://localhost:27017/")
db = client["shopsphere"]
products = db["products"]

catalog = [
    {"product_id": "P10", "name": "Laptop", "category": "Electronics"},
    {"product_id": "P11", "name": "Phone", "category": "Electronics"},
    {"product_id": "P12", "name": "Headset", "category": "Accessories"},
    {"product_id": "P13", "name": "Keyboard", "category": "Accessories"},
    {"product_id": "P14", "name": "Monitor", "category": "Electronics"},
    {"product_id": "P15", "name": "Mouse", "category": "Accessories"},
    {"product_id": "P16", "name": "Webcam", "category": "Accessories"},
    {"product_id": "P17", "name": "Tablet", "category": "Electronics"},
    {"product_id": "P18", "name": "Smartwatch", "category": "Electronics"},
    {"product_id": "P19", "name": "Speaker", "category": "Electronics"},
    # Extend this list toward P50 if you want every generated ID mapped.
    # Anything not listed here just won't have a friendly name yet —
    # that's a fine, deliberate scope decision to mention in the report.
]

products.delete_many({})
products.insert_many(catalog)
print(f"Seeded {len(catalog)} products into MongoDB.")
