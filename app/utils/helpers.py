"""
Utility helpers for CineAI.
"""
from __future__ import annotations

import logging
import os
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

TMDB_API_KEY = os.getenv("TMDB_API_KEY", "")
TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p/w500"
TMDB_API_BASE = "https://api.themoviedb.org/3"

# Simple in-process cache: {tmdb_id: poster_url | None}
_poster_cache: dict[int, Optional[str]] = {}


async def fetch_poster_url(tmdb_id: int) -> Optional[str]:
    """
    Fetch poster URL from TMDB for a given movie ID.
    Returns None if API key is missing or request fails.
    """
    if not TMDB_API_KEY:
        return None

    if tmdb_id in _poster_cache:
        return _poster_cache[tmdb_id]

    url = f"{TMDB_API_BASE}/movie/{tmdb_id}"
    params = {"api_key": TMDB_API_KEY}
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()
            path = data.get("poster_path")
            result = f"{TMDB_IMAGE_BASE}{path}" if path else None
    except Exception as exc:
        logger.debug(f"TMDB poster fetch failed for id={tmdb_id}: {exc}")
        result = None

    _poster_cache[tmdb_id] = result
    return result


async def enrich_with_posters(movies: list[dict]) -> list[dict]:
    """Add poster_url to a list of movie dicts in parallel."""
    import asyncio
    tasks = [fetch_poster_url(m["id"]) for m in movies]
    posters = await asyncio.gather(*tasks)
    for movie, poster in zip(movies, posters):
        movie["poster_url"] = poster
    return movies


def title_case(s: str) -> str:
    return s.title()


def format_similarity(score: float) -> str:
    return f"{score * 100:.1f}%"
