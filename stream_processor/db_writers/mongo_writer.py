"""
MongoDB stores order documents as-is — this is exactly why Mongo is the
right fit here: order events aren't a rigid shape, and Mongo doesn't
force one.
"""

from pymongo import MongoClient

client = MongoClient("mongodb://localhost:27017/")
db = client["shopsphere"]
orders_collection = db["orders"]


def write_order(event: dict):
    # .copy() so we never mutate the dict other writers (Neo4j, Redis) also use —
    # pymongo adds an "_id" field to whatever dict you pass it.
    orders_collection.insert_one(event.copy())
