from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import cache_dependency, index_manager_dependency
from app.api.schemas import AutocompleteResponse
from app.services import autocomplete_service
from app.services.index_manager import IndexManager
from app.storage.cache import ResultCache

router = APIRouter(tags=["autocomplete"])


@router.get("/autocomplete", response_model=AutocompleteResponse)
def autocomplete(
    prefix: str = Query(..., min_length=1, max_length=100),
    limit: int = Query(10, ge=1, le=50),
    index_manager: IndexManager = Depends(index_manager_dependency),
    cache: ResultCache = Depends(cache_dependency),
) -> AutocompleteResponse:
    if not prefix.strip():
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="prefix must not be blank")

    result = autocomplete_service.autocomplete(
        index_manager=index_manager, cache=cache, prefix=prefix, limit=limit
    )
    return AutocompleteResponse(**result)
