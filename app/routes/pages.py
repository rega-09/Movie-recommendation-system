"""
Page routes: renders Jinja2 HTML templates.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.services.recommender import recommender_service
from app.utils.helpers import enrich_with_posters

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Pages"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/", response_class=HTMLResponse, include_in_schema=False)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@router.get("/movie/{movie_id}", response_class=HTMLResponse, include_in_schema=False)
async def movie_detail(request: Request, movie_id: int):
    try:
        movie = recommender_service.get_movie_by_id(movie_id)
    except RuntimeError:
        raise HTTPException(status_code=503, detail="Service unavailable")

    if not movie:
        raise HTTPException(status_code=404, detail="Movie not found")

    await enrich_with_posters([movie])

    # Also fetch similar movies
    try:
        _, recs_raw = recommender_service.recommend(movie["title"], count=6)
        await enrich_with_posters(recs_raw)
    except Exception:
        recs_raw = []

    return templates.TemplateResponse(
        "details.html",
        {"request": request, "movie": movie, "recommendations": recs_raw},
    )
