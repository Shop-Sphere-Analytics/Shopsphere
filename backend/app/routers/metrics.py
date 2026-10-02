"""Live counters: revenue and active users. Both served from Redis."""

from fastapi import APIRouter, HTTPException

from .. import services
from ..models import Revenue, ActiveUsers, ErrorResponse

router = APIRouter(prefix="/api", tags=["metrics"])


@router.get(
    "/revenue",
    response_model=Revenue,
    responses={503: {"model": ErrorResponse}},
    summary="Total revenue and order count",
    description=(
        "Reads the pre-aggregated Redis counters written by the stream processor, "
        "rounded to 2dp to absorb INCRBYFLOAT drift. Falls back to a MongoDB "
        "aggregation if the Redis keys are missing; `source` tells you which was used."
    ),
)
def revenue():
    try:
        return services.get_revenue()
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"revenue unavailable: {e}")


@router.get(
    "/active-users",
    response_model=ActiveUsers,
    responses={503: {"model": ErrorResponse}},
    summary="Users currently active",
    description="Cardinality of the Redis `active_users` set (SCARD) - a sub-millisecond read.",
)
def active_users():
    try:
        return services.get_active_users()
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"redis unavailable: {e}")
