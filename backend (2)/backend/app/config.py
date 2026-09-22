"""
All connection settings in one place, overridable by environment variables.

Defaults assume you are running uvicorn on your host machine and the databases
in Docker (the setup Person B documented). If you later containerise the API
itself, set MONGO_URI=mongodb://mongodb:27017/ etc. in docker-compose and
nothing in the code has to change.
"""

import os

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
MONGO_DB = os.getenv("MONGO_DB", "shopsphere")

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))

CASSANDRA_HOST = os.getenv("CASSANDRA_HOST", "127.0.0.1")
CASSANDRA_KEYSPACE = os.getenv("CASSANDRA_KEYSPACE", "shopsphere")

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")

CURRENCY = os.getenv("CURRENCY", "INR")

# How often the WebSocket loop re-reads Redis and pushes if something changed.
WS_POLL_SECONDS = float(os.getenv("WS_POLL_SECONDS", "2.0"))

# Cassandra has no cheap way to count rows across partitions, so click stats
# are computed by scanning up to this many rows and cached for a few seconds.
CLICK_SCAN_LIMIT = int(os.getenv("CLICK_SCAN_LIMIT", "50000"))
CLICK_CACHE_SECONDS = float(os.getenv("CLICK_CACHE_SECONDS", "15"))

# Origins allowed to call the API from a browser (Person D's Vite dev server).
CORS_ORIGINS = os.getenv(
    "CORS_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000",
).split(",")
