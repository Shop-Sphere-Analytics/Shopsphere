"""
Response models.

These exist for one reason beyond type safety: FastAPI turns them into the
schemas and example payloads you see at /docs, which is Person D's contract.
Every model carries a realistic example so D can build the dashboard against
/docs alone, without the API even running.
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class Revenue(BaseModel):
    revenue_today: float = Field(..., description="Running revenue total, rounded to 2dp.")
    currency: str
    orders_today: int = Field(..., description="Total orders processed by the stream processor.")
    source: str = Field(..., description="Which database served this: 'redis' (fast path) or 'mongodb' (fallback).")

    model_config = {
        "json_schema_extra": {
            "example": {
                "revenue_today": 125400.00,
                "currency": "INR",
                "orders_today": 542,
                "source": "redis",
            }
        }
    }


class Order(BaseModel):
    order_id: str
    product_id: str
    product_name: str = Field(..., description="Resolved from MongoDB `products`; falls back to the raw id.")
    user_id: str
    amount: float
    status: str = Field(..., description="Always 'placed' - the generator emits no lifecycle status.")
    timestamp: Optional[str] = Field(None, description="Generator's fake timestamp. Not chronological - do not sort on it.")
    received_at: Optional[str] = Field(None, description="When the stream processor actually stored it (UTC). Sort on this.")


class OrdersResponse(BaseModel):
    orders: List[Order]
    count: int

    model_config = {
        "json_schema_extra": {
            "example": {
                "orders": [
                    {
                        "order_id": "ORD5690",
                        "product_id": "P14",
                        "product_name": "Monitor",
                        "user_id": "USR816",
                        "amount": 462.82,
                        "status": "placed",
                        "timestamp": "1981-07-09T14:52:36",
                        "received_at": "2026-09-21T10:24:11Z",
                    }
                ],
                "count": 1,
            }
        }
    }


class ActiveUsers(BaseModel):
    active_users: int
    as_of: str

    model_config = {
        "json_schema_extra": {
            "example": {"active_users": 87, "as_of": "2026-09-21T10:25:00Z"}
        }
    }


class TopProduct(BaseModel):
    product_id: str
    name: str
    orders: int
    revenue: float


class TopProductsResponse(BaseModel):
    top_products: List[TopProduct]

    model_config = {
        "json_schema_extra": {
            "example": {
                "top_products": [
                    {"product_id": "P14", "name": "Monitor", "orders": 128, "revenue": 41233.50},
                    {"product_id": "P11", "name": "Phone", "orders": 96, "revenue": 30880.10},
                ]
            }
        }
    }


class UserActivity(BaseModel):
    product_id: str
    clicks_today: int = Field(..., description="Site-wide product_detail clicks - see the caveat in HANDOFF.md.")
    orders_today: int
    conversion_rate: float
    approximate: bool = Field(True, description="True while click events carry no product_id.")

    model_config = {
        "json_schema_extra": {
            "example": {
                "product_id": "P14",
                "clicks_today": 340,
                "orders_today": 22,
                "conversion_rate": 0.065,
                "approximate": True,
            }
        }
    }


class PageActivity(BaseModel):
    page: str
    clicks: int


class ClickActivityResponse(BaseModel):
    total_clicks: int
    by_page: List[PageActivity]
    scanned_rows: int
    truncated: bool = Field(..., description="True if the scan hit CLICK_SCAN_LIMIT and numbers are a sample.")

    model_config = {
        "json_schema_extra": {
            "example": {
                "total_clicks": 1240,
                "by_page": [
                    {"page": "home", "clicks": 512},
                    {"page": "product_detail", "clicks": 340},
                    {"page": "cart", "clicks": 236},
                    {"page": "checkout", "clicks": 152},
                ],
                "scanned_rows": 1240,
                "truncated": False,
            }
        }
    }


class Recommendation(BaseModel):
    product_id: str
    name: str
    strength: int = Field(..., description="How many distinct users bought both products.")


class RecommendationsResponse(BaseModel):
    product_id: str
    name: str
    also_bought: List[Recommendation]

    model_config = {
        "json_schema_extra": {
            "example": {
                "product_id": "P14",
                "name": "Monitor",
                "also_bought": [
                    {"product_id": "P19", "name": "Speaker", "strength": 34},
                    {"product_id": "P33", "name": "P33", "strength": 21},
                ],
            }
        }
    }


class LiveUpdate(BaseModel):
    """Shape pushed over WS /ws/live-updates."""

    event: str = Field(..., description="'snapshot' on connect, then 'new_order' / 'tick' on change.")
    revenue_today: float
    orders_today: int
    active_users: int
    as_of: str

    model_config = {
        "json_schema_extra": {
            "example": {
                "event": "new_order",
                "revenue_today": 125799.00,
                "orders_today": 543,
                "active_users": 88,
                "as_of": "2026-09-21T10:25:02Z",
            }
        }
    }


class Health(BaseModel):
    api: str
    databases: dict

    model_config = {
        "json_schema_extra": {
            "example": {
                "api": "up",
                "databases": {
                    "mongodb": "up",
                    "redis": "up",
                    "cassandra": "up",
                    "neo4j": "up",
                },
            }
        }
    }


class ErrorResponse(BaseModel):
    error: str

    model_config = {"json_schema_extra": {"example": {"error": "redis unavailable"}}}
