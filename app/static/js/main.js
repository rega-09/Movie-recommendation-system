/* ── CineAI Frontend ─────────────────────────────────────────────────── */

// ── Theme ────────────────────────────────────────────────────────────────
const root = document.documentElement;
const themeBtn = document.getElementById('theme-toggle');

function applyTheme(theme) {
  root.setAttribute('data-theme', theme);
  localStorage.setItem('theme', theme);
  if (themeBtn) {
    themeBtn.querySelector('.theme-icon').textContent = theme === 'dark' ? '☀' : '☾';
  }
}

// On load
applyTheme(localStorage.getItem('theme') || 'dark');

themeBtn?.addEventListener('click', () => {
  applyTheme(root.getAttribute('data-theme') === 'dark' ? 'light' : 'dark');
});

// ── Elements ─────────────────────────────────────────────────────────────
const input       = document.getElementById('movie-input');
const searchBtn   = document.getElementById('search-btn');
const sugList     = document.getElementById('suggestions-list');
const resultsSection = document.getElementById('results-section');
const resultsTitle   = document.getElementById('results-title');
const queryCardWrap  = document.getElementById('query-card-wrap');
const recsGrid       = document.getElementById('recommendations-grid');
const clearBtn       = document.getElementById('clear-btn');
const loadingOverlay = document.getElementById('loading-overlay');
const toast          = document.getElementById('toast');

// ── Toast ─────────────────────────────────────────────────────────────────
let toastTimer = null;
function showToast(msg, isError = false) {
  clearTimeout(toastTimer);
  toast.textContent = msg;
  toast.classList.toggle('error', isError);
  toast.removeAttribute('hidden');
  requestAnimationFrame(() => toast.classList.add('show'));
  toastTimer = setTimeout(() => {
    toast.classList.remove('show');
    setTimeout(() => toast.setAttribute('hidden', ''), 300);
  }, 3500);
}

// ── Loading ───────────────────────────────────────────────────────────────
function setLoading(on) {
  if (on) loadingOverlay.removeAttribute('hidden');
  else loadingOverlay.setAttribute('hidden', '');
}

// ── Autocomplete ──────────────────────────────────────────────────────────
let sugTimer = null;
let activeSugIdx = -1;

async function fetchSuggestions(q) {
  if (!q.trim()) { hideSuggestions(); return; }
  try {
    const res = await fetch(`/api/search?q=${encodeURIComponent(q)}&limit=8`);
    if (!res.ok) return;
    const data = await res.json();
    renderSuggestions(data);
  } catch {
    hideSuggestions();
  }
}

function renderSuggestions(items) {
  if (!items.length) { hideSuggestions(); return; }
  sugList.innerHTML = items.map((m, i) =>
    `<li role="option" data-title="${escHtml(m.title)}" data-idx="${i}">
       <span>${escHtml(m.title)}</span>
       <span class="sug-year">${m.year || ''}</span>
     </li>`
  ).join('');
  activeSugIdx = -1;
  sugList.removeAttribute('hidden');
}

function hideSuggestions() {
  sugList.innerHTML = '';
  sugList.setAttribute('hidden', '');
  activeSugIdx = -1;
}

input.addEventListener('input', () => {
  clearTimeout(sugTimer);
  sugTimer = setTimeout(() => fetchSuggestions(input.value), 220);
});

input.addEventListener('keydown', (e) => {
  const items = sugList.querySelectorAll('li');
  if (!items.length) {
    if (e.key === 'Enter') triggerSearch();
    return;
  }
  if (e.key === 'ArrowDown') {
    e.preventDefault();
    activeSugIdx = Math.min(activeSugIdx + 1, items.length - 1);
    updateActiveSug(items);
  } else if (e.key === 'ArrowUp') {
    e.preventDefault();
    activeSugIdx = Math.max(activeSugIdx - 1, -1);
    updateActiveSug(items);
  } else if (e.key === 'Enter') {
    e.preventDefault();
    if (activeSugIdx >= 0 && items[activeSugIdx]) {
      selectSuggestion(items[activeSugIdx].dataset.title);
    } else {
      triggerSearch();
    }
  } else if (e.key === 'Escape') {
    hideSuggestions();
  }
});

function updateActiveSug(items) {
  items.forEach((li, i) => li.setAttribute('aria-selected', i === activeSugIdx));
  if (activeSugIdx >= 0) input.value = items[activeSugIdx].dataset.title;
}

sugList.addEventListener('click', (e) => {
  const li = e.target.closest('li');
  if (li) selectSuggestion(li.dataset.title);
});

function selectSuggestion(title) {
  input.value = title;
  hideSuggestions();
  triggerSearch();
}

// Close suggestions on outside click
document.addEventListener('click', (e) => {
  if (!e.target.closest('.search-wrap')) hideSuggestions();
});

// ── Search ────────────────────────────────────────────────────────────────
searchBtn.addEventListener('click', triggerSearch);

// Hint chips
document.querySelectorAll('.hint-chip').forEach(chip => {
  chip.addEventListener('click', () => {
    input.value = chip.dataset.title;
    triggerSearch();
  });
});

async function triggerSearch() {
  const title = input.value.trim();
  if (!title) {
    showToast('Please enter a movie title.', true);
    input.focus();
    return;
  }
  hideSuggestions();
  setLoading(true);

  try {
    const res = await fetch('/api/recommend', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title, count: 10 }),
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || `Error ${res.status}`);
    }

    const data = await res.json();
    renderResults(data);
  } catch (err) {
    showToast(err.message || 'Something went wrong. Please try again.', true);
  } finally {
    setLoading(false);
  }
}

// ── Render ────────────────────────────────────────────────────────────────
function renderResults(data) {
  // Title
  resultsTitle.textContent = data.query_movie.title;

  // Query card
  queryCardWrap.innerHTML = renderQueryCard(data.query_movie);

  // Recommendations
  recsGrid.innerHTML = data.recommendations
    .map((m, i) => renderMovieCard(m, i))
    .join('');

  // Show section, scroll to it
  resultsSection.removeAttribute('hidden');
  resultsSection.classList.add('reveal');
  resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function renderQueryCard(m) {
  const poster = m.poster_url
    ? `<img src="${escHtml(m.poster_url)}" alt="${escHtml(m.title)} poster" class="query-poster" loading="lazy" />`
    : '🎬';
  const genres = (m.genres || []).slice(0, 3)
    .map(g => `<span class="genre-tag">${escHtml(g)}</span>`).join('');
  return `
    <div class="query-card">
      <div class="query-poster-wrap">${poster}</div>
      <div class="query-info">
        <h3 class="query-title-display">${escHtml(m.title)}</h3>
        <p class="query-year">${m.year || '—'}</p>
        <div class="card-genres">${genres}</div>
        <p class="query-overview">${escHtml((m.overview || '').slice(0, 200))}${m.overview && m.overview.length > 200 ? '…' : ''}</p>
      </div>
    </div>`;
}

function renderMovieCard(m, idx) {
  const poster = m.poster_url
    ? `<img src="${escHtml(m.poster_url)}" alt="${escHtml(m.title)}" class="card-poster" loading="lazy" />`
    : `<div class="card-poster-placeholder"><span>🎬</span></div>`;
  const score = Math.round(m.similarity_score * 100);
  const genres = (m.genres || []).slice(0, 2)
    .map(g => `<span class="genre-tag small">${escHtml(g)}</span>`).join('');
  const overview = (m.overview || '').slice(0, 90);
  const delay = Math.min(idx * 50, 400);

  return `
    <article class="movie-card reveal" style="animation-delay:${delay}ms">
      <a href="/movie/${m.id}" class="card-link">
        <div class="card-poster-wrap">
          ${poster}
          <div class="card-score-badge">${score}% match</div>
        </div>
        <div class="card-body">
          <h3 class="card-title">${escHtml(m.title)}</h3>
          <p class="card-year">${m.year || '—'}</p>
          <div class="card-genres">${genres}</div>
          <p class="card-overview">${escHtml(overview)}${m.overview && m.overview.length > 90 ? '…' : ''}</p>
        </div>
      </a>
    </article>`;
}

// ── Clear ─────────────────────────────────────────────────────────────────
clearBtn?.addEventListener('click', () => {
  resultsSection.setAttribute('hidden', '');
  resultsSection.classList.remove('reveal');
  input.value = '';
  input.focus();
  window.scrollTo({ top: 0, behavior: 'smooth' });
});

// ── Helpers ───────────────────────────────────────────────────────────────
function escHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}
