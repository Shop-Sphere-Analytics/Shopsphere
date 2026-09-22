"""
Cassandra is built for exactly this job: huge volumes of writes, always
read back in time order. We partition by day (so writes spread out
across partitions instead of piling into one) and cluster by timestamp
descending (so "most recent clicks first" is a cheap query, not a scan).
"""

from datetime import datetime
from cassandra.cluster import Cluster
from cassandra.io.twistedreactor import TwistedConnection

cluster = Cluster(["127.0.0.1"], connection_class=TwistedConnection)
session = cluster.connect()

session.execute("""
    CREATE KEYSPACE IF NOT EXISTS shopsphere
    WITH replication = {'class': 'SimpleStrategy', 'replication_factor': 1}
""")
session.set_keyspace("shopsphere")

session.execute("""
    CREATE TABLE IF NOT EXISTS clicks (
        event_date text,
        ts timestamp,
        event_id text,
        user_id text,
        page text,
        PRIMARY KEY (event_date, ts, event_id)
    ) WITH CLUSTERING ORDER BY (ts DESC)
""")

_insert_click = session.prepare("""
    INSERT INTO clicks (event_date, ts, event_id, user_id, page)
    VALUES (?, ?, ?, ?, ?)
""")


def write_click(event: dict):
    ts = datetime.fromisoformat(event["timestamp"])
    event_date = ts.strftime("%Y-%m-%d")
    session.execute(
        _insert_click,
        (event_date, ts, event["event_id"], event["user_id"], event["page"]),
    )
