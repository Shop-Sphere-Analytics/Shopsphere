"""
ShopSphere Backend API - Person C.

The single front desk: the only service that talks to all four databases, so
the frontend never has to know which one holds which answer.

    GET  /api/revenue          -> Redis      (pre-aggregated counters)
    GET  /api/orders           -> MongoDB    (order documents + product names)
    GET  /api/active-users     -> Redis      (set cardinality)
    GET  /api/top-products     -> MongoDB    (aggregation)
    GET  /api/click-activity   -> Cassandra  (click log, grouped by page)
    GET  /api/user-activity    -> Cassandra + MongoDB
    GET  /api/recommendations  -> Neo4j      (graph traversal)
    WS   /ws/live-updates      -> Redis      (pushed every ~2s on change)

Run:  uvicorn app.main:app --reload --port 8000
Docs: http://localhost:8000/docs
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from . import config, db
from .models import Health
from .routers import metrics, orders, products, recommendations
from .ws import hub

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    hub.start()
    yield
    await hub.stop()


app = FastAPI(
    title="ShopSphere Analytics API",
    version="1.0.0",
    description=(
        "Real-time analytics over a polyglot-persistence backend: MongoDB, "
        "Cassandra, Redis and Neo4j behind one HTTP + WebSocket surface.\n\n"
        "Every endpoint names the database it reads from and why that database "
        "is the right home for that question. See `backend/HANDOFF.md` for the "
        "data quirks the frontend needs to know about."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request, exc: StarletteHTTPException):
    """The contract says errors are `{"error": "..."}`, so honour that everywhere."""
    return JSONResponse(status_code=exc.status_code, content={"error": str(exc.detail)})


app.include_router(metrics.router)
app.include_router(orders.router)
app.include_router(products.router)
app.include_router(recommendations.router)


@app.get("/api/health", response_model=Health, tags=["meta"], summary="Per-database liveness")
def health():
    """
    Pings all four databases. Run this first when something looks wrong - it
    tells you in one call whether the problem is the API or a database that
    has not finished starting (Cassandra needs ~45s after `docker compose up`).
    """
    return {"api": "up", "databases": db.health()}


@app.websocket("/ws/live-updates")
async def live_updates(websocket: WebSocket):
    """
    Push channel for the dashboard.

    On connect: one `{"event": "snapshot", ...}` with the current numbers.
    Thereafter: a message only when revenue, order count or active users change.
    """
    await hub.connect(websocket)
    try:
        while True:
            # We never expect client messages; this receive just keeps the
            # connection open and surfaces the disconnect promptly.
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        await hub.disconnect(websocket)
