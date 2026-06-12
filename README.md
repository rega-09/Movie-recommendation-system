# 🎬 CineAI — Movie Recommendation Engine

A production-ready content-based movie recommendation system built with **FastAPI**, **scikit-learn**, and a cinematic dark-mode UI.

Given any movie title from the TMDB 5000 dataset, CineAI analyses plot keywords, genres, cast, and director to surface the ten most similar films using cosine similarity over NLP-vectorised metadata.

---

## ✨ Features

- **Content-based filtering** — metadata fusion + Porter stemming + CountVectorizer + cosine similarity
- **Autocomplete search** — real-time prefix search as you type
- **TMDB poster fetching** — optional live poster images via TMDB API
- **Dark / light mode** — preference persisted in localStorage
- **Fully responsive** — works on mobile, tablet, desktop
- **FastAPI + Swagger docs** — auto-generated at `/api/docs`
- **Production-ready** — Docker, gunicorn, pre-built model cache, logging

---

## 🗂 Project Structure

```
cineai/
├── app/
│   ├── main.py                # FastAPI app + lifespan
│   ├── routes/
│   │   ├── recommendation.py  # POST /api/recommend, GET /api/search, GET /api/item/{id}
│   │   └── pages.py           # HTML page routes (Jinja2)
│   ├── services/
│   │   └── recommender.py     # Core ML pipeline (singleton)
│   ├── models/
│   │   └── schemas.py         # Pydantic request/response models
│   ├── utils/
│   │   └── helpers.py         # TMDB poster fetching util
│   ├── static/
│   │   ├── css/main.css
│   │   ├── css/details.css
│   │   └── js/main.js
│   └── templates/
│       ├── index.html
│       └── details.html
├── data/                      # Place CSV files here (git-ignored)
├── saved_models/              # Auto-generated pickle cache
├── requirements.txt
├── Dockerfile
├── setup_nltk.py
├── .env.example
└── README.md
```

---

## 🚀 Quick Start (Local)

### 1. Clone & install

```bash
git clone https://github.com/your-username/cineai.git
cd cineai
python -m venv venv && source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Add dataset files

Download from Kaggle — [TMDB 5000 Movie Dataset](https://www.kaggle.com/datasets/tmdb/tmdb-movie-metadata):

```
data/
├── tmdb_5000_movies.csv
└── tmdb_5000_credits.csv
```

### 3. Download NLTK data

```bash
python setup_nltk.py
```

### 4. Configure environment (optional)

```bash
cp .env.example .env
# Edit .env and add your TMDB_API_KEY for poster images
```

### 5. Run the server

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Visit: **http://localhost:8000**  
API docs: **http://localhost:8000/api/docs**

> **First run** builds the model (~30s depending on hardware) and caches it to `saved_models/`. Subsequent starts load the cache instantly.

---

## 🐳 Docker

```bash
# Build
docker build -t cineai .

# Run (mount data directory)
docker run -p 8000:8000 \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/saved_models:/app/saved_models \
  -e TMDB_API_KEY=your_key \
  cineai
```

---

## ☁️ Deployment

### Render

1. Push repo to GitHub (make sure `data/*.csv` are in `.gitignore` — they're too large for Render's free tier).
2. Create a new **Web Service** on Render, connect your repo.
3. Set **Build Command**: `pip install -r requirements.txt && python setup_nltk.py`
4. Set **Start Command**: `gunicorn app.main:app -w 2 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT`
5. Add environment variables: `TMDB_API_KEY`
6. Use a **Persistent Disk** mounted at `/app/data` and upload your CSVs there.

### Railway

```bash
railway init
railway up
# Set env vars in Railway dashboard
```

### VPS (Ubuntu)

```bash
sudo apt update && sudo apt install python3-pip nginx -y
git clone https://github.com/your-username/cineai /opt/cineai
cd /opt/cineai && pip install -r requirements.txt
python setup_nltk.py
# Copy CSVs to /opt/cineai/data/
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker \
  --bind 127.0.0.1:8000 --daemon
# Configure nginx to proxy to 127.0.0.1:8000
```

---

## 🔌 API Reference

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | Homepage |
| `POST` | `/api/recommend` | Get recommendations for a movie |
| `GET` | `/api/search?q=…` | Autocomplete title search |
| `GET` | `/api/item/{id}` | Single movie details |
| `GET` | `/api/health` | Health check |
| `GET` | `/api/docs` | Swagger UI |

### POST /api/recommend

```json
// Request
{
  "title": "Avatar",
  "count": 10
}

// Response
{
  "query": "Avatar",
  "query_movie": { "id": 19995, "title": "Avatar", "year": 2009, ... },
  "recommendations": [ { "id": 76341, "title": "Mad Max: Fury Road", ... }, ... ],
  "total": 10
}
```

---

## 🧠 How It Works

1. **Data ingestion** — merges TMDB movies + credits CSVs on `title`
2. **Feature extraction** — parses JSON columns for genres, keywords, top-3 cast, director
3. **Tag construction** — concatenates all features into one text blob per film
4. **Stemming** — Porter stemmer normalises vocabulary ("running" → "run")
5. **Vectorisation** — `CountVectorizer` (5000 features, English stopwords removed)
6. **Similarity** — cosine similarity matrix (4 800 × 4 800)
7. **Query** — lookup movie index → sort similarity scores → return top-N

---

## 📝 License

MIT — free to use, modify and deploy.

---

*Built with FastAPI · scikit-learn · NLTK · the TMDB 5000 dataset*
