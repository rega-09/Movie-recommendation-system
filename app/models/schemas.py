from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field, field_validator


class RecommendRequest(BaseModel):
    title: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Movie title to base recommendations on",
        examples=["Avatar"],
    )
    count: int = Field(
        default=10,
        ge=1,
        le=20,
        description="Number of recommendations to return (1–20)",
    )

    @field_validator("title")
    @classmethod
    def strip_title(cls, v: str) -> str:
        return v.strip()


class MovieCard(BaseModel):
    id: int
    title: str
    year: Optional[int]
    genres: list[str]
    cast: list[str]
    director: list[str]
    overview: str
    similarity_score: float = Field(ge=0.0, le=1.0)
    poster_url: Optional[str] = None
    tmdb_url: Optional[str] = None


class RecommendResponse(BaseModel):
    query: str
    query_movie: MovieCard
    recommendations: list[MovieCard]
    total: int


class SearchSuggestion(BaseModel):
    title: str
    year: Optional[int]
    id: int


class HealthResponse(BaseModel):
    status: str
    movie_count: int
    model_loaded: bool
