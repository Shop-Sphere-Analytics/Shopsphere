"""Recent order feed, from MongoDB."""

from fastapi import APIRouter, HTTPException, Query

from .. import services
from ..models import OrdersResponse, ErrorResponse

router = APIRouter(prefix="/api", tags=["orders"])


@router.get(
    "/orders",
    response_model=OrdersResponse,
    responses={503: {"model": ErrorResponse}},
    summary="Most recently processed orders",
    description=(
        "Newest first by MongoDB `_id` (insertion order), NOT by the event's own "
        "`timestamp` - the generator emits random fake dates across decades. "
        "`received_at` is derived from the ObjectId and is the only trustworthy time. "
        "`product_name` falls back to the raw id for products outside the seeded P10-P19."
    ),
)
def orders(limit: int = Query(10, ge=1, le=100)):
    try:
        return services.get_recent_orders(limit)
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"mongodb unavailable: {e}")
