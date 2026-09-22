"""
Person A's generator never emits a separate "relationship" event — the
order event already has everything we need (user_id + product_id), so
we build the graph directly from it.

MERGE means "create if missing, otherwise reuse the existing node/edge" —
this is what lets us build up "bought together" recommendation data
across many orders instead of duplicating nodes every time.
"""

from neo4j import GraphDatabase

driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "password"))

_query = """
MERGE (u:User {id: $user_id})
MERGE (p:Product {id: $product_id})
MERGE (u)-[b:BOUGHT]->(p)
ON CREATE SET b.count = 1, b.last_amount = $amount, b.last_purchase = $timestamp
ON MATCH  SET b.count = b.count + 1, b.last_amount = $amount, b.last_purchase = $timestamp
"""


def write_purchase_relationship(event: dict):
    with driver.session() as session:
        session.run(
            _query,
            user_id=event["user_id"],
            product_id=event["product_id"],
            amount=event["amount"],
            timestamp=event["timestamp"],
        )
