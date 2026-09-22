"""Product leaderboard and per-product activity."""

from fastapi import APIRouter, HTTPException, Query

from .. import services
from ..models import (
    TopProductsResponse,
    UserActivity,
    ClickActivityResponse,
    ErrorResponse,
)

router = APIRouter(prefix="/api", tags=["products"])


@router.get(
    "/top-products",
    response_model=TopProductsResponse,
    responses={503: {"model": ErrorResponse}},
    summary="Best-selling products",
    description="MongoDB aggregation over the orders collection, grouped by product_id.",
)
def top_products(limit: int = Query(5, ge=1, le=50)):
    try:
        return services.get_top_products(limit)
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"mongodb unavailable: {e}")


@router.get(
    "/click-activity",
    response_model=ClickActivityResponse,
    responses={503: {"model": ErrorResponse}},
    summary="Click funnel by page",
    description=(
        "Real click data from Cassandra, broken down by page category "
        "(home / product_detail / cart / checkout). Result is cached briefly "
        "because Cassandra cannot aggregate across partitions cheaply."
    ),
)
def click_activity():
    try:
        return services.get_click_activity()
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"cassandra unavailable: {e}")


@router.get(
    "/user-activity",
    response_model=UserActivity,
    responses={503: {"model": ErrorResponse}},
    summary="Clicks vs orders for one product (approximate)",
    description=(
        "APPROXIMATE. Click events carry a page category, never a product_id, so "
        "clicks cannot be attributed to a single product. `clicks_today` is the "
        "site-wide product_detail count; `orders_today` is exact for this product. "
        "`approximate` is always true until click events gain a product_id."
    ),
)
def user_activity(product_id: str = Query(..., examples=["P14"])):
    try:
        return services.get_user_activity(product_id)
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"activity unavailable: {e}")
