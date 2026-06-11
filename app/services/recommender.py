"""
CineAI Recommender Service
==========================
Content-based filtering using:
  - Bag-of-Words (CountVectorizer, 5 000 features)
  - Porter Stemming
  - Cosine Similarity
"""
from __future__ import annotations

import ast
import logging
import os
import pickle
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
from nltk.stem.porter import PorterStemmer
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity

logger = logging.getLogger(__name__)

# ── Paths ──────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"
MODEL_DIR = BASE_DIR / "saved_models"
MODEL_DIR.mkdir(exist_ok=True)

_MOVIES_CSV = DATA_DIR / "tmdb_5000_movies.csv"
_CREDITS_CSV = DATA_DIR / "tmdb_5000_credits.csv"
_PICKLE_DATA = MODEL_DIR / "movies_data.pkl"
_PICKLE_SIM = MODEL_DIR / "similarity.pkl"


# ── Helpers ────────────────────────────────────────────────────────────────
def _extract_names(col: str) -> list[str]:
    """Parse JSON-encoded list and return name values."""
    try:
        return [item["name"] for item in ast.literal_eval(col)]
    except Exception:
        return []


def _extract_top_cast(col: str, top: int = 3) -> list[str]:
    """Return top-N cast names."""
    try:
        return [item["name"] for item in ast.literal_eval(col)[:top]]
    except Exception:
        return []


def _extract_director(col: str) -> list[str]:
    """Return director name(s) from crew JSON."""
    try:
        return [item["name"] for item in ast.literal_eval(col) if item.get("job") == "Director"]
    except Exception:
        return []


def _collapse(lst: list[str]) -> list[str]:
    """Remove spaces inside multi-word tokens (e.g. 'Sam Worthington' → 'SamWorthington')."""
    return [s.replace(" ", "") for s in lst]


_ps = PorterStemmer()


def _stem(text: str) -> str:
    return " ".join(_ps.stem(w) for w in text.split())


# ── Service ────────────────────────────────────────────────────────────────
class RecommenderService:
    def __init__(self) -> None:
        self._data: Optional[pd.DataFrame] = None
        self._similarity: Optional[np.ndarray] = None
        self._loaded: bool = False

    # ── Public API ─────────────────────────────────────────────────────────
    @property
    def movie_count(self) -> int:
        return len(self._data) if self._data is not None else 0

    @property
    def model_loaded(self) -> bool:
        return self._loaded

    def load(self) -> None:
        """Load from cache or build from CSVs."""
        if _PICKLE_DATA.exists() and _PICKLE_SIM.exists():
            logger.info("Loading pre-built model from cache…")
            self._data = pickle.loads(_PICKLE_DATA.read_bytes())
            self._similarity = pickle.loads(_PICKLE_SIM.read_bytes())
        else:
            logger.info("No cache found — building model from CSV files…")
            self._build_and_cache()
        self._loaded = True

    def recommend(self, title: str, count: int = 10) -> tuple[dict, list[dict]]:
        """
        Return (query_movie_dict, [recommendation_dict, …]).
        Raises ValueError if movie not found.
        """
        self._ensure_loaded()
        key = title.strip().lower()
        matches = self._data[self._data["title"] == key]
        if matches.empty:
            raise ValueError(f"Movie '{title}' not found in the database.")

        idx = matches.index[0]
        scores = list(enumerate(self._similarity[idx]))
        scores.sort(key=lambda x: x[1], reverse=True)

        query_movie = self._row_to_dict(self._data.loc[idx], similarity=1.0)
        recs = [
            self._row_to_dict(self._data.iloc[i], similarity=float(score))
            for i, score in scores[1 : count + 1]
        ]
        return query_movie, recs

    def search(self, query: str, limit: int = 10) -> list[dict]:
        """Prefix/substring search on movie titles."""
        self._ensure_loaded()
        q = query.strip().lower()
        mask = self._data["title"].str.contains(q, na=False, regex=False)
        results = self._data[mask].head(limit)
        return [
            {
                "id": int(row["id"]),
                "title": row["display_title"],
                "year": int(row["release_date"]) if pd.notna(row["release_date"]) else None,
            }
            for _, row in results.iterrows()
        ]

    def get_movie_by_id(self, movie_id: int) -> Optional[dict]:
        """Fetch a single movie by TMDB id."""
        self._ensure_loaded()
        match = self._data[self._data["id"] == movie_id]
        if match.empty:
            return None
        return self._row_to_dict(match.iloc[0], similarity=1.0)

    # ── Internal ───────────────────────────────────────────────────────────
    def _ensure_loaded(self) -> None:
        if not self._loaded:
            raise RuntimeError("Recommender not loaded. Call load() first.")

    def _build_and_cache(self) -> None:
        if not _MOVIES_CSV.exists() or not _CREDITS_CSV.exists():
            raise FileNotFoundError(
                f"Dataset files not found in {DATA_DIR}. "
                "Please place tmdb_5000_movies.csv and tmdb_5000_credits.csv there."
            )

        logger.info("Reading CSVs…")
        movies_df = pd.read_csv(_MOVIES_CSV)
        credits_df = pd.read_csv(_CREDITS_CSV)
        data = movies_df.merge(credits_df, on="title")

        # Keep only needed columns
        data = data[["genres", "id", "keywords", "overview",
                     "release_date", "runtime", "title", "cast", "crew"]]

        # Drop rows with missing overview
        data = data.dropna(subset=["overview"])

        # Parse JSON columns
        logger.info("Parsing metadata columns…")
        data["genres"] = data["genres"].apply(_extract_names)
        data["keywords"] = data["keywords"].apply(_extract_names)
        data["cast"] = data["cast"].apply(_extract_top_cast)
        data["crew"] = data["crew"].apply(_extract_director)

        # Extract year
        data["release_date"] = pd.to_datetime(data["release_date"], errors="coerce").dt.year
        data = data.dropna(subset=["release_date"])
        data["release_date"] = data["release_date"].astype(int)

        # Store originals before collapsing spaces (for display)
        data["display_title"] = data["title"]
        data["display_genres"] = data["genres"].copy()
        data["display_cast"] = data["cast"].copy()
        data["display_crew"] = data["crew"].copy()
        data["display_overview"] = data["overview"].copy()

        # Tokenise overview
        data["overview"] = data["overview"].apply(lambda x: x.split())

        # Collapse multi-word tokens so they act as single features
        for col in ["cast", "crew", "genres", "keywords"]:
            data[col] = data[col].apply(_collapse)

        # Build tags
        data["tags"] = (
            data["overview"]
            + data["genres"]
            + data["keywords"]
            + data["cast"]
            + data["crew"]
        )
        data["tags"] = data["tags"].apply(lambda x: " ".join(x).lower())

        # Lowercase title for lookup
        data["title"] = data["title"].apply(str.lower)

        # Clean up
        data = data.drop(columns=["cast", "crew", "genres", "keywords",
                                   "overview", "runtime"])
        data = data.reset_index(drop=True)

        # Stem
        logger.info("Stemming tags…")
        data["tags"] = data["tags"].apply(_stem)

        # Vectorise
        logger.info("Fitting CountVectorizer…")
        cv = CountVectorizer(max_features=5000, stop_words="english")
        vectors = cv.fit_transform(data["tags"]).toarray()

        # Cosine similarity
        logger.info("Computing cosine similarity matrix…")
        sim = cosine_similarity(vectors)

        # Cache
        logger.info("Saving model to disk…")
        _PICKLE_DATA.write_bytes(pickle.dumps(data))
        _PICKLE_SIM.write_bytes(pickle.dumps(sim))

        self._data = data
        self._similarity = sim
        logger.info(f"Model built — {len(data):,} movies indexed.")

    @staticmethod
    def _row_to_dict(row: pd.Series, similarity: float) -> dict:
        year = row.get("release_date")
        return {
            "id": int(row["id"]),
            "title": str(row.get("display_title", row["title"])),
            "year": int(year) if pd.notna(year) else None,
            "genres": list(row.get("display_genres", [])),
            "cast": list(row.get("display_cast", [])),
            "director": list(row.get("display_crew", [])),
            "overview": str(row.get("display_overview", "")),
            "similarity_score": round(similarity, 4),
            "poster_url": None,   # enriched later via TMDB API helper
            "tmdb_url": f"https://www.themoviedb.org/movie/{int(row['id'])}",
        }


# ── Singleton ──────────────────────────────────────────────────────────────
recommender_service = RecommenderService()
