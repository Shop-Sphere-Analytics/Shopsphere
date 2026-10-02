"""Graph-powered 'customers who bought X also bought Y', from Neo4j."""

from fastapi import APIRouter, HTTPException, Query

from .. import services
from ..models import RecommendationsResponse, ErrorResponse

router = APIRouter(prefix="/api", tags=["recommendations"])


@router.get(
    "/recommendations",
    response_model=RecommendationsResponse,
    responses={503: {"model": ErrorResponse}},
    summary="Products frequently bought by the same users",
    description=(
        "Two-hop Cypher traversal: product <- user -> other product, ranked by the "
        "number of distinct users who bought both. An empty `also_bought` list is a "
        "valid answer for a product no one has co-purchased yet."
    ),
)
def recommendations(
    product_id: str = Query(..., examples=["P14"]),
    limit: int = Query(5, ge=1, le=20),
):
    try:
        return services.get_recommendations(product_id, limit)
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"neo4j unavailable: {e}")
