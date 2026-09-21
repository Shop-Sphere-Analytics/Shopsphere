"""
One lazy client per database.

Design rule: nothing connects at import time. If Cassandra is still warming up
(Person B's handoff warns it takes ~45s) or Neo4j is down, the API must still
boot and the endpoints backed by the *other* databases must still work. Each
getter connects on first use and caches the client; failures raise and are
turned into a clean 503 by the route.
"""

import threading
from typing import Optional

from pymongo import MongoClient
import redis as redis_lib
from neo4j import GraphDatabase

from . import config

_lock = threading.Lock()

_mongo: Optional[MongoClient] = None
_redis: Optional["redis_lib.Redis"] = None
_cassandra_session = None
_neo4j_driver = None


# --------------------------------------------------------------------------- Mongo
def mongo():
    global _mongo
    if _mongo is None:
        with _lock:
            if _mongo is None:
                _mongo = MongoClient(config.MONGO_URI, serverSelectionTimeoutMS=3000)
    return _mongo[config.MONGO_DB]


def orders_collection():
    return mongo()["orders"]


def products_collection():
    return mongo()["products"]


# --------------------------------------------------------------------------- Redis
def redis_client():
    global _redis
    if _redis is None:
        with _lock:
            if _redis is None:
                _redis = redis_lib.Redis(
                    host=config.REDIS_HOST,
                    port=config.REDIS_PORT,
                    decode_responses=True,
                    socket_connect_timeout=3,
                )
    return _redis


# ----------------------------------------------------------------------- Cassandra
def cassandra():
    """
    Person B hit an import-time crash here: the driver's default connection
    class uses `asyncore`, removed from the stdlib in Python 3.12. Their fix was
    `pip install pyasyncore`; their code went further and pinned the Twisted
    connection class. We try Twisted first (matches the consumer, and `twisted`
    is in requirements.txt), and fall back to the driver's own auto-detection so
    this still works on a teammate's 3.11 machine or with the pyasyncore shim.
    """
    global _cassandra_session
    if _cassandra_session is None:
        with _lock:
            if _cassandra_session is None:
                from cassandra.cluster import Cluster

                try:
                    from cassandra.io.twistedreactor import TwistedConnection

                    cluster = Cluster(
                        [config.CASSANDRA_HOST], connection_class=TwistedConnection
                    )
                except Exception:
                    cluster = Cluster([config.CASSANDRA_HOST])

                session = cluster.connect()
                session.set_keyspace(config.CASSANDRA_KEYSPACE)
                _cassandra_session = session
    return _cassandra_session


# --------------------------------------------------------------------------- Neo4j
def neo4j():
    global _neo4j_driver
    if _neo4j_driver is None:
        with _lock:
            if _neo4j_driver is None:
                _neo4j_driver = GraphDatabase.driver(
                    config.NEO4J_URI,
                    auth=(config.NEO4J_USER, config.NEO4J_PASSWORD),
                )
    return _neo4j_driver


# ------------------------------------------------------------------- shared helpers
def product_names(product_ids) -> dict:
    """
    product_id -> friendly name, for the ids we were asked about.

    Person B seeded only P10-P19 while Person A's generator emits up to P50, so
    any id with no catalog row simply maps to itself. That fallback is
    deliberate, not a bug - it is called out in HANDOFF.md.
    """
    ids = list({pid for pid in product_ids if pid})
    if not ids:
        return {}
    try:
        rows = products_collection().find(
            {"product_id": {"$in": ids}}, {"_id": 0, "product_id": 1, "name": 1}
        )
        found = {r["product_id"]: r.get("name") or r["product_id"] for r in rows}
    except Exception:
        found = {}
    return {pid: found.get(pid, pid) for pid in ids}


def health() -> dict:
    """Ping every database. Used by GET /api/health and the demo checklist."""
    status = {}

    try:
        mongo().command("ping")
        status["mongodb"] = "up"
    except Exception as e:
        status["mongodb"] = f"down: {type(e).__name__}"

    try:
        redis_client().ping()
        status["redis"] = "up"
    except Exception as e:
        status["redis"] = f"down: {type(e).__name__}"

    try:
        cassandra().execute("SELECT release_version FROM system.local")
        status["cassandra"] = "up"
    except Exception as e:
        status["cassandra"] = f"down: {type(e).__name__}"

    try:
        neo4j().verify_connectivity()
        status["neo4j"] = "up"
    except Exception as e:
        status["neo4j"] = f"down: {type(e).__name__}"

    return status


__all__ = [
    "mongo",
    "orders_collection",
    "products_collection",
    "redis_client",
    "cassandra",
    "neo4j",
    "product_names",
    "health",
]
