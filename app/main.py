import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.routes import recommendation, pages
from app.services.recommender import recommender_service

# ── Logging ────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s │ %(levelname)-8s │ %(name)s │ %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


# ── Lifespan ──────────────────────────────────────────────────────────--
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load the recommendation model once at startup."""
    logger.info("🎬  CineAI starting — loading recommendation engine…")
    t0 = time.perf_counter()
    try:
        recommender_service.load()
        elapsed = time.perf_counter() - t0
        logger.info(f"✅  Recommendation engine ready in {elapsed:.2f}s  "
                    f"({recommender_service.movie_count:,} movies indexed)")
    except Exception as exc:
        logger.error(f"❌  Failed to load recommendation engine: {exc}")
        raise
    yield
    logger.info("👋  CineAI shutting down")


# ── App ────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="CineAI",
    description="Content-based movie recommendation engine powered by NLP & cosine similarity.",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="app/static"), name="static")

app.include_router(pages.router)
app.include_router(recommendation.router, prefix="/api")


# ── Global exception handler ───────────────────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception on {request.url}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected error occurred. Please try again."},
    )
