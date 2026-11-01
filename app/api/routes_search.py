from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import cache_dependency, index_manager_dependency
from app.api.schemas import SearchResponse
from app.services import search_service
from app.services.index_manager import IndexManager
from app.storage.cache import ResultCache

router = APIRouter(tags=["search"])


@router.get("/search", response_model=SearchResponse)
def search(
    q: str = Query(..., min_length=1, max_length=512, description="Search query"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    limit: int = Query(10, ge=1, le=100, description="Page size"),
    index_manager: IndexManager = Depends(index_manager_dependency),
    cache: ResultCache = Depends(cache_dependency),
) -> SearchResponse:
    if not q.strip():
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="q must not be blank")

    result = search_service.search(
        index_manager=index_manager, cache=cache, query=q, offset=offset, limit=limit
    )
    return SearchResponse(**result)
