"""
API Routes: /api/recommend, /api/search, /api/item/{id}, /health
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Query

from app.models.schemas import (
    HealthResponse,
    MovieCard,
    RecommendRequest,
    RecommendResponse,
    SearchSuggestion,
)
from app.services.recommender import recommender_service
from app.utils.helpers import enrich_with_posters

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Recommendations"])


# ── Health ─────────────────────────────────────────────────────────────────
@router.get("/health", response_model=HealthResponse, summary="Health check")
async def health() -> HealthResponse:
    return HealthResponse(
        status="ok" if recommender_service.model_loaded else "loading",
        movie_count=recommender_service.movie_count,
        model_loaded=recommender_service.model_loaded,
    )


# ── Recommend ──────────────────────────────────────────────────────────────
@router.post(
    "/recommend",
    response_model=RecommendResponse,
    summary="Get movie recommendations",
    description="Returns N content-based recommendations for the given movie title.",
)
async def recommend(body: RecommendRequest) -> RecommendResponse:
    try:
        query_movie_raw, recs_raw = recommender_service.recommend(
            body.title, count=body.count
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    # Enrich with posters (non-blocking, best-effort)
    all_movies = [query_movie_raw] + recs_raw
    await enrich_with_posters(all_movies)

    query_card = MovieCard(**all_movies[0])
    rec_cards = [MovieCard(**m) for m in all_movies[1:]]

    return RecommendResponse(
        query=body.title,
        query_movie=query_card,
        recommendations=rec_cards,
        total=len(rec_cards),
    )


# ── Search suggestions ─────────────────────────────────────────────────────
@router.get(
    "/search",
    response_model=list[SearchSuggestion],
    summary="Autocomplete movie title search",
)
async def search(
    q: str = Query(..., min_length=1, max_length=200, description="Search query"),
    limit: int = Query(default=8, ge=1, le=20),
) -> list[SearchSuggestion]:
    try:
        results = recommender_service.search(q, limit=limit)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    return [SearchSuggestion(**r) for r in results]


# ── Single movie detail ────────────────────────────────────────────────────
@router.get(
    "/item/{movie_id}",
    response_model=MovieCard,
    summary="Get movie details by TMDB ID",
)
async def get_movie(movie_id: int) -> MovieCard:
    try:
        movie = recommender_service.get_movie_by_id(movie_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    if movie is None:
        raise HTTPException(status_code=404, detail=f"Movie ID {movie_id} not found.")

    await enrich_with_posters([movie])
    return MovieCard(**movie)
