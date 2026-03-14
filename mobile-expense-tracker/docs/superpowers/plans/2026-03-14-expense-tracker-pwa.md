# Expense Tracker PWA Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a mobile-first PWA expense tracker as `index.html` + `manifest.json` + `sw.js` backed by the already-written `Code.gs` Google Apps Script backend.

**Architecture:** Single `index.html` with all CSS and JS inline. No build step, no framework. State lives in a plain JS object; the API layer is a thin `async` wrapper that shows a spinner and handles errors with a toast. Three separate files: `index.html` (app), `manifest.json` (PWA metadata), `sw.js` (service worker caching).

**Tech Stack:** Vanilla JS (ES2020), CSS custom properties, Google Fonts (Inter + JetBrains Mono), PWA (Web App Manifest + Service Worker).

**Spec:** `docs/superpowers/specs/2026-03-14-expense-tracker-pwa-design.md`

---

## Chunk 1: PWA Scaffold + Shell

### Task 1: manifest.json

**Files:**
- Create: `manifest.json`

- [ ] **Step 1: Create manifest.json**

```json
{
  "name": "Expense Tracker",
  "short_name": "Expenses",
  "description": "Personal expense tracker backed by Google Sheets",
  "theme_color": "#0f1117",
  "background_color": "#0f1117",
  "display": "standalone",
  "orientation": "portrait",
  "start_url": "./index.html",
  "scope": "./",
  "icons": [
    {
      "src": "data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 192 192'><rect width='192' height='192' rx='32' fill='%231a1d27'/><text y='130' x='96' text-anchor='middle' font-size='110'>💰</text></svg>",
      "sizes": "192x192",
      "type": "image/svg+xml"
    },
    {
      "src": "data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 512 512'><rect width='512' height='512' rx='80' fill='%231a1d27'/><text y='360' x='256' text-anchor='middle' font-size='300'>💰</text></svg>",
      "sizes": "512x512",
      "type": "image/svg+xml"
    }
  ]
}
```

- [ ] **Step 2: Verify**

Open `manifest.json` in a text editor. Confirm valid JSON (no syntax errors).

- [ ] **Step 3: Commit**

```bash
git add manifest.json
git commit -m "feat: add PWA manifest"
```

---

### Task 2: sw.js (service worker)

**Files:**
- Create: `sw.js`

- [ ] **Step 1: Create sw.js**

```js
const CACHE_NAME = 'expense-tracker-v1';
const SHELL_FILES = ['./index.html', './manifest.json'];
const API_PATTERN = 'script.google.com';

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => cache.addAll(SHELL_FILES))
  );
  self.skipWaiting();
});

self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k)))
    )
  );
  self.clients.claim();
});

self.addEventListener('fetch', event => {
  // Network-only for API calls
  if (event.request.url.includes(API_PATTERN)) return;

  // Cache-first for app shell
  event.respondWith(
    caches.match(event.request).then(cached => cached || fetch(event.request))
  );
});
```

- [ ] **Step 2: Verify**

Open `sw.js`. Confirm `CACHE_NAME`, `SHELL_FILES`, and `API_PATTERN` are all defined at the top. No syntax errors.

- [ ] **Step 3: Commit**

```bash
git add sw.js
git commit -m "feat: add service worker with cache-first shell strategy"
```

---

### Task 3: index.html shell — structure, CSS variables, fonts, nav

**Files:**
- Create: `index.html`

This task produces a working shell: dark background, bottom nav with 4 tabs, tab switching. No tab content yet.

- [ ] **Step 1: Create index.html with shell**

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
  <meta name="theme-color" content="#0f1117">
  <meta name="apple-mobile-web-app-capable" content="yes">
  <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
  <title>Expense Tracker</title>
  <link rel="manifest" href="manifest.json">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
  <style>
    /* ── CSS Variables ── */
    :root {
      --bg:       #0f1117;
      --surface:  #1a1d27;
      --border:   #2a2d3a;
      --accent:   #e8a020;
      --text:     #f0f0f5;
      --muted:    #6b7280;
      --danger:   #e05252;
      --success:  #4caf7d;

      --cat-food:          #e07b54;
      --cat-transport:     #5b8dee;
      --cat-shopping:      #c47fd4;
      --cat-health:        #4caf7d;
      --cat-entertainment: #e8a020;
      --cat-bills:         #e05252;
      --cat-other:         #6b7280;

      --nav-h: 64px;
      --safe-bottom: env(safe-area-inset-bottom, 0px);
    }

    /* ── Reset ── */
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
    html, body { height: 100%; overflow: hidden; }
    body {
      font-family: 'Inter', system-ui, sans-serif;
      background: var(--bg);
      color: var(--text);
      -webkit-font-smoothing: antialiased;
    }

    /* ── App layout ── */
    #app {
      display: flex;
      flex-direction: column;
      height: 100%;
    }

    /* ── Tab content ── */
    .tab-content {
      flex: 1;
      overflow-y: auto;
      overflow-x: hidden;
      -webkit-overflow-scrolling: touch;
      padding: 16px 16px calc(var(--nav-h) + var(--safe-bottom) + 16px);
    }

    .tab-pane { display: none; }
    .tab-pane.active { display: block; }

    /* ── Bottom nav ── */
    #bottom-nav {
      position: fixed;
      bottom: 0;
      left: 0;
      right: 0;
      height: calc(var(--nav-h) + var(--safe-bottom));
      padding-bottom: var(--safe-bottom);
      background: var(--surface);
      border-top: 1px solid var(--border);
      display: flex;
      align-items: stretch;
      z-index: 100;
    }

    .nav-btn {
      flex: 1;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      gap: 2px;
      background: none;
      border: none;
      cursor: pointer;
      color: var(--muted);
      font-size: 11px;
      font-family: inherit;
      transition: color 0.15s;
      -webkit-tap-highlight-color: transparent;
      min-height: 48px;
    }

    .nav-btn .nav-icon { font-size: 22px; line-height: 1; }
    .nav-btn .nav-label { display: none; }

    .nav-btn.active {
      color: var(--accent);
    }
    .nav-btn.active .nav-label { display: block; }

    /* ── Spinner overlay ── */
    #spinner {
      display: none;
      position: fixed;
      inset: 0;
      background: rgba(15,17,23,0.7);
      z-index: 200;
      align-items: center;
      justify-content: center;
    }
    #spinner.visible { display: flex; }
    .spinner-ring {
      width: 40px; height: 40px;
      border: 3px solid var(--border);
      border-top-color: var(--accent);
      border-radius: 50%;
      animation: spin 0.7s linear infinite;
    }
    @keyframes spin { to { transform: rotate(360deg); } }

    /* ── Toast ── */
    #toast {
      position: fixed;
      bottom: calc(var(--nav-h) + var(--safe-bottom) + 12px);
      left: 16px;
      right: 16px;
      background: var(--surface);
      border: 1px solid var(--border);
      color: var(--text);
      padding: 12px 16px;
      border-radius: 10px;
      font-size: 14px;
      z-index: 300;
      transform: translateY(20px);
      opacity: 0;
      transition: all 0.2s ease;
      pointer-events: none;
    }
    #toast.show { transform: translateY(0); opacity: 1; }

    /* ── Shared card ── */
    .card {
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 16px;
      margin-bottom: 12px;
    }

    /* ── Section label ── */
    .section-label {
      font-size: 11px;
      font-weight: 600;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      color: var(--muted);
      margin-bottom: 10px;
    }
  </style>
</head>
<body>
<div id="app">
  <div class="tab-content">
    <div id="tab-add"       class="tab-pane active"><p style="color:var(--muted)">Add tab</p></div>
    <div id="tab-history"   class="tab-pane"><p style="color:var(--muted)">History tab</p></div>
    <div id="tab-dashboard" class="tab-pane"><p style="color:var(--muted)">Dashboard tab</p></div>
    <div id="tab-settings"  class="tab-pane"><p style="color:var(--muted)">Settings tab</p></div>
  </div>

  <nav id="bottom-nav">
    <button class="nav-btn active" data-tab="add">
      <span class="nav-icon">➕</span>
      <span class="nav-label">Add</span>
    </button>
    <button class="nav-btn" data-tab="history">
      <span class="nav-icon">📋</span>
      <span class="nav-label">History</span>
    </button>
    <button class="nav-btn" data-tab="dashboard">
      <span class="nav-icon">📊</span>
      <span class="nav-label">Dashboard</span>
    </button>
    <button class="nav-btn" data-tab="settings">
      <span class="nav-icon">⚙️</span>
      <span class="nav-label">Settings</span>
    </button>
  </nav>
</div>

<div id="spinner"><div class="spinner-ring"></div></div>
<div id="toast"></div>

<script>
// ── Constants ──────────────────────────────────────────────
const API_URL = 'YOUR_APPS_SCRIPT_URL';

const CATEGORIES = [
  { id: 'Food',          emoji: '🍔', color: 'var(--cat-food)' },
  { id: 'Transport',     emoji: '🚌', color: 'var(--cat-transport)' },
  { id: 'Shopping',      emoji: '🛍️', color: 'var(--cat-shopping)' },
  { id: 'Health',        emoji: '💊', color: 'var(--cat-health)' },
  { id: 'Entertainment', emoji: '🎬', color: 'var(--cat-entertainment)' },
  { id: 'Bills',         emoji: '📄', color: 'var(--cat-bills)' },
  { id: 'Other',         emoji: '📦', color: 'var(--cat-other)' },
];

function catColor(id) {
  const c = CATEGORIES.find(c => c.id === id);
  return c ? c.color : 'var(--cat-other)';
}

// ── State ──────────────────────────────────────────────────
function todayStr() {
  return new Date().toISOString().slice(0, 10);
}
function thisMonth() {
  return new Date().toISOString().slice(0, 7);
}

const state = {
  currentTab: 'add',
  currentMonth: thisMonth(),
  expenses: [],
  favorites: [],
  budgets: {},
  usdRate: parseFloat(localStorage.getItem('usdRate') || '3.7'),
  form: {
    amount: '',
    category: null,
    note: '',
    date: todayStr(),
    isRecurring: false,
  }
};

// ── Spinner & Toast ────────────────────────────────────────
function showSpinner() { document.getElementById('spinner').classList.add('visible'); }
function hideSpinner() { document.getElementById('spinner').classList.remove('visible'); }

let toastTimer;
function showToast(msg) {
  const el = document.getElementById('toast');
  el.textContent = msg;
  el.classList.add('show');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => el.classList.remove('show'), 3000);
}

// ── API ────────────────────────────────────────────────────
async function api(params) {
  showSpinner();
  try {
    const res = await fetch(API_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(params),
    });
    const data = await res.json();
    if (data.error) throw new Error(data.error);
    return data;
  } catch (err) {
    showToast('Error: ' + err.message);
    throw err;
  } finally {
    hideSpinner();
  }
}

// ── Tab routing ────────────────────────────────────────────
function switchTab(tabId) {
  state.currentTab = tabId;
  document.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
  document.getElementById('tab-' + tabId).classList.add('active');
  document.querySelector(`.nav-btn[data-tab="${tabId}"]`).classList.add('active');

  if (tabId === 'add')       renderAdd();
  if (tabId === 'history')   renderHistory();
  if (tabId === 'dashboard') renderDashboard();
  if (tabId === 'settings')  renderSettings();
}

document.querySelectorAll('.nav-btn').forEach(btn => {
  btn.addEventListener('click', () => switchTab(btn.dataset.tab));
});

// ── Startup ────────────────────────────────────────────────
async function init() {
  try {
    const [favData, budgetData, expData] = await Promise.all([
      api({ action: 'get_favorites' }),
      api({ action: 'get_budgets' }),
      api({ action: 'get_expenses', month: state.currentMonth }),
    ]);
    state.favorites = favData.favorites || [];
    state.budgets   = budgetData.budgets || {};
    state.expenses  = expData.expenses  || [];
  } catch (_) { /* toasts already shown */ }
  renderAdd();
}

// Placeholder renders (filled in later tasks)
function renderAdd()       { /* implemented in Task 4 */ }
function renderHistory()   { /* implemented in Task 5 */ }
function renderDashboard() { /* implemented in Task 6 */ }
function renderSettings()  { /* implemented in Task 7 */ }

// Register service worker
if ('serviceWorker' in navigator) {
  navigator.serviceWorker.register('./sw.js').catch(() => {});
}

init();
</script>
</body>
</html>
```

- [ ] **Step 2: Open in browser and verify shell**

Open `index.html` in Chrome. Check:
- Dark `#0f1117` background fills screen
- Bottom nav shows 4 emoji buttons
- Tapping each nav button: active tab button turns amber and shows label; content area shows placeholder text
- No console errors

- [ ] **Step 3: Check mobile layout**

Open Chrome DevTools → Toggle Device Toolbar → iPhone 14 Pro. Verify:
- Nav bar sits at very bottom (no overlap with home indicator area)
- Content area doesn't clip behind nav bar
- Tap targets feel large enough

- [ ] **Step 4: Commit**

```bash
git add index.html
git commit -m "feat: add app shell with nav, spinner, toast, state, and API layer"
```

---

## Chunk 2: Add Tab

### Task 4: Add tab — HTML structure and CSS

**Files:**
- Modify: `index.html` — replace `renderAdd()` placeholder and add CSS

- [ ] **Step 1: Add CSS for Add tab inside the `<style>` block**

Add after the `.section-label` rule:

```css
/* ── Add Tab ── */
#tab-add { padding-top: 8px; }

/* Favorites strip */
.favorites-strip {
  display: flex;
  gap: 8px;
  overflow-x: auto;
  padding-bottom: 4px;
  margin-bottom: 16px;
  scrollbar-width: none;
}
.favorites-strip::-webkit-scrollbar { display: none; }

.fav-pill {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 14px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 20px;
  color: var(--text);
  font-size: 13px;
  font-family: inherit;
  cursor: pointer;
  white-space: nowrap;
  -webkit-tap-highlight-color: transparent;
  transition: border-color 0.15s;
}
.fav-pill:active { border-color: var(--accent); }

.fav-save-btn {
  flex-shrink: 0;
  padding: 8px 14px;
  background: none;
  border: 1px dashed var(--border);
  border-radius: 20px;
  color: var(--muted);
  font-size: 18px;
  cursor: pointer;
  -webkit-tap-highlight-color: transparent;
}

/* Amount input */
.amount-wrap {
  text-align: center;
  margin-bottom: 20px;
}
.amount-row {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}
.amount-currency {
  font-size: 32px;
  font-weight: 600;
  color: var(--muted);
  font-family: 'JetBrains Mono', monospace;
}
.amount-input {
  background: none;
  border: none;
  border-bottom: 2px solid var(--border);
  color: var(--text);
  font-size: 52px;
  font-family: 'JetBrains Mono', monospace;
  font-weight: 500;
  width: 180px;
  text-align: center;
  outline: none;
  -webkit-appearance: none;
  transition: border-color 0.15s;
}
.amount-input:focus { border-bottom-color: var(--accent); }
.amount-usd {
  color: var(--muted);
  font-size: 14px;
  font-family: 'JetBrains Mono', monospace;
  margin-top: 6px;
  min-height: 20px;
}

/* Category grid */
.category-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 8px;
  margin-bottom: 16px;
}
.cat-btn {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 4px;
  padding: 12px 4px;
  background: var(--surface);
  border: 1.5px solid var(--border);
  border-radius: 10px;
  color: var(--text);
  font-size: 11px;
  font-family: inherit;
  cursor: pointer;
  -webkit-tap-highlight-color: transparent;
  transition: border-color 0.15s, background 0.15s;
  min-height: 68px;
}
.cat-btn .cat-emoji { font-size: 24px; }
.cat-btn.selected {
  border-color: var(--accent);
  background: rgba(232,160,32,0.10);
}

/* Row 2 (3 items) centered using subgrid trick */
.category-row-2 {
  grid-column: 1 / -1;
  display: flex;
  justify-content: center;
  gap: 8px;
}
.category-row-2 .cat-btn { width: calc(25% - 6px); }

/* Note + date + recurring */
.form-field {
  margin-bottom: 14px;
}
.form-field label {
  display: block;
  font-size: 12px;
  color: var(--muted);
  margin-bottom: 6px;
  font-weight: 500;
}
.form-input {
  width: 100%;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 8px;
  color: var(--text);
  font-family: inherit;
  font-size: 15px;
  padding: 12px 14px;
  outline: none;
  transition: border-color 0.15s;
}
.form-input:focus { border-color: var(--accent); }

/* Toggle */
.toggle-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 0;
  border-top: 1px solid var(--border);
  margin-bottom: 16px;
}
.toggle-label { font-size: 15px; }
.toggle {
  position: relative;
  width: 48px;
  height: 28px;
}
.toggle input { opacity: 0; width: 0; height: 0; }
.toggle-track {
  position: absolute;
  inset: 0;
  background: var(--border);
  border-radius: 14px;
  transition: background 0.2s;
  cursor: pointer;
}
.toggle input:checked + .toggle-track { background: var(--accent); }
.toggle-track::after {
  content: '';
  position: absolute;
  width: 22px; height: 22px;
  background: #fff;
  border-radius: 50%;
  top: 3px; left: 3px;
  transition: transform 0.2s;
}
.toggle input:checked + .toggle-track::after { transform: translateX(20px); }

/* Submit button */
.btn-primary {
  width: 100%;
  height: 52px;
  background: var(--accent);
  color: #0f1117;
  font-size: 16px;
  font-weight: 600;
  font-family: inherit;
  border: none;
  border-radius: 12px;
  cursor: pointer;
  -webkit-tap-highlight-color: transparent;
  transition: opacity 0.15s, transform 0.1s;
}
.btn-primary:active { transform: scale(0.98); opacity: 0.9; }
.btn-primary:disabled { opacity: 0.4; cursor: not-allowed; }

@keyframes shake {
  0%,100% { transform: translateX(0); }
  20%,60%  { transform: translateX(-6px); }
  40%,80%  { transform: translateX(6px); }
}
.shake { animation: shake 0.35s ease; }
```

- [ ] **Step 2: Implement renderAdd() in the `<script>` block**

Replace `function renderAdd() { /* implemented in Task 4 */ }` with:

```js
function renderAdd() {
  const pane = document.getElementById('tab-add');

  // Build favorites HTML
  const favPills = state.favorites.map(f => `
    <button class="fav-pill" data-fav-id="${f.id}"
      onclick="applyFavorite('${f.id}')">
      <span style="color:${catColor(f.category)}">${CATEGORIES.find(c=>c.id===f.category)?.emoji||'📦'}</span>
      ${escHtml(f.favoriteName)}
    </button>
  `).join('');

  // Build category grid HTML
  const row1 = CATEGORIES.slice(0, 4).map(c => `
    <button class="cat-btn${state.form.category === c.id ? ' selected' : ''}"
      onclick="selectCategory('${c.id}')">
      <span class="cat-emoji">${c.emoji}</span>
      <span>${c.id}</span>
    </button>
  `).join('');

  const row2 = CATEGORIES.slice(4).map(c => `
    <button class="cat-btn${state.form.category === c.id ? ' selected' : ''}"
      onclick="selectCategory('${c.id}')">
      <span class="cat-emoji">${c.emoji}</span>
      <span>${c.id}</span>
    </button>
  `).join('');

  const usd = state.form.amount
    ? `≈ $${(parseFloat(state.form.amount) / state.usdRate).toFixed(2)}`
    : '';

  pane.innerHTML = `
    <div class="favorites-strip">
      ${favPills}
      <button class="fav-save-btn" onclick="saveFavorite()" title="Save as favorite">⭐</button>
    </div>

    <div class="amount-wrap">
      <div class="amount-row">
        <span class="amount-currency">₪</span>
        <input id="amount-input" class="amount-input" type="number" inputmode="decimal"
          placeholder="0" value="${escHtml(state.form.amount)}"
          oninput="onAmountInput(this.value)">
      </div>
      <div class="amount-usd" id="amount-usd">${usd}</div>
    </div>

    <div class="section-label">Category</div>
    <div class="category-grid">
      ${row1}
      <div class="category-row-2">${row2}</div>
    </div>

    <div class="form-field">
      <label>Note (optional)</label>
      <input class="form-input" type="text" id="note-input" placeholder="What was it for?"
        value="${escHtml(state.form.note)}"
        oninput="state.form.note = this.value">
    </div>

    <div class="form-field">
      <label>Date</label>
      <input class="form-input" type="date" id="date-input"
        value="${state.form.date}"
        onchange="state.form.date = this.value">
    </div>

    <div class="toggle-row">
      <span class="toggle-label">🔁 Recurring</span>
      <label class="toggle">
        <input type="checkbox" id="recurring-toggle"
          ${state.form.isRecurring ? 'checked' : ''}
          onchange="state.form.isRecurring = this.checked">
        <div class="toggle-track"></div>
      </label>
    </div>

    <button class="btn-primary" id="add-btn" onclick="submitExpense()">Add Expense</button>
  `;

  // Auto-focus amount
  setTimeout(() => document.getElementById('amount-input')?.focus(), 50);
}

function escHtml(s) {
  return String(s || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

function onAmountInput(val) {
  state.form.amount = val;
  const usdEl = document.getElementById('amount-usd');
  if (usdEl) {
    usdEl.textContent = val ? `≈ $${(parseFloat(val) / state.usdRate).toFixed(2)}` : '';
  }
}

function selectCategory(id) {
  state.form.category = state.form.category === id ? null : id;
  renderAdd();
}

function applyFavorite(id) {
  const f = state.favorites.find(f => f.id === id);
  if (!f) return;
  state.form.amount = String(f.amount);
  state.form.category = f.category;
  state.form.note = f.note || '';
  state.form.date = todayStr();
  state.form.isRecurring = false;
  renderAdd();
}

async function saveFavorite() {
  if (!state.form.amount || !state.form.category) {
    showToast('Fill in amount and category first');
    return;
  }
  const name = prompt('Favorite name:');
  if (!name) return;
  try {
    const res = await api({
      action: 'add_favorite',
      amount: parseFloat(state.form.amount),
      category: state.form.category,
      note: state.form.note,
      favoriteName: name,
    });
    state.favorites.push({
      id: res.id,
      amount: parseFloat(state.form.amount),
      category: state.form.category,
      note: state.form.note,
      favoriteName: name,
      isRecurring: false,
    });
    showToast('Saved as favorite!');
    renderAdd();
  } catch (_) {}
}

async function submitExpense() {
  if (!state.form.category) {
    const btn = document.getElementById('add-btn');
    btn.classList.remove('shake');
    void btn.offsetWidth; // reflow
    btn.classList.add('shake');
    showToast('Please select a category');
    return;
  }
  if (!state.form.amount || parseFloat(state.form.amount) <= 0) {
    showToast('Please enter an amount');
    return;
  }
  try {
    await api({
      action: 'add_expense',
      date: state.form.date,
      amount: parseFloat(state.form.amount),
      category: state.form.category,
      note: state.form.note,
      isRecurring: state.form.isRecurring,
    });
    // Reset form (keep date + recurring)
    const keepDate = state.form.date;
    const keepRecurring = state.form.isRecurring;
    state.form = { amount: '', category: null, note: '', date: keepDate, isRecurring: keepRecurring };
    // Reload expenses if current month matches
    if (keepDate.slice(0,7) === state.currentMonth) {
      const expData = await api({ action: 'get_expenses', month: state.currentMonth });
      state.expenses = expData.expenses || [];
    }
    showToast('Expense added ✓');
    renderAdd();
  } catch (_) {}
}
```

- [ ] **Step 3: Open in browser and verify Add tab**

Open `index.html`. Check:
- ₪ input is large and centered; typing updates `≈ $XX.XX` below it
- Category grid shows 4 buttons in row 1, 3 centered in row 2
- Tapping a category highlights it with amber border; tapping again deselects
- Note and date fields accept input
- Recurring toggle animates on/off
- Tapping "Add Expense" with no category selected: button shakes + toast appears
- Favorites strip shows ⭐ button at end (no favorites yet, that's fine)
- **Note:** Add will fail with a network error since `API_URL` is not set — that's expected; toast shows "Error: …"

- [ ] **Step 4: Commit**

```bash
git add index.html
git commit -m "feat: implement Add tab with form, category grid, favorites strip"
```

---

## Chunk 3: History Tab

### Task 5: History tab — expense list with day grouping and swipe-to-delete

**Files:**
- Modify: `index.html` — add History CSS + implement renderHistory()

- [ ] **Step 1: Add History CSS inside `<style>`**

```css
/* ── History Tab ── */
.history-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}
.history-month-title {
  font-size: 17px;
  font-weight: 600;
}
.history-total {
  font-family: 'JetBrains Mono', monospace;
  font-size: 14px;
  color: var(--accent);
}
.refresh-btn {
  background: none;
  border: none;
  color: var(--muted);
  font-size: 20px;
  cursor: pointer;
  padding: 4px 8px;
  -webkit-tap-highlight-color: transparent;
}

.day-group { margin-bottom: 8px; }
.day-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 4px;
  font-size: 12px;
  font-weight: 600;
  color: var(--muted);
  text-transform: uppercase;
  letter-spacing: 0.06em;
  position: sticky;
  top: 0;
  background: var(--bg);
  z-index: 1;
}
.day-total {
  font-family: 'JetBrains Mono', monospace;
  font-weight: 400;
  text-transform: none;
}

/* Swipeable expense row */
.expense-row-wrap {
  position: relative;
  overflow: hidden;
  border-radius: 10px;
  margin-bottom: 4px;
}
.expense-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 14px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 10px;
  transition: transform 0.2s ease;
  will-change: transform;
  position: relative;
  z-index: 1;
}
.expense-dot {
  width: 10px; height: 10px;
  border-radius: 50%;
  flex-shrink: 0;
}
.expense-center { flex: 1; min-width: 0; }
.expense-cat {
  font-size: 14px;
  font-weight: 500;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.expense-note {
  font-size: 12px;
  color: var(--muted);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.expense-icons { font-size: 11px; color: var(--muted); }
.expense-amount {
  font-family: 'JetBrains Mono', monospace;
  font-size: 15px;
  font-weight: 500;
  flex-shrink: 0;
}

/* Delete button revealed on swipe */
.delete-reveal {
  position: absolute;
  right: 0; top: 0; bottom: 0;
  width: 80px;
  background: var(--danger);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  border-radius: 0 10px 10px 0;
  cursor: pointer;
  z-index: 0;
}

/* Empty state */
.empty-state {
  text-align: center;
  padding: 60px 20px;
  color: var(--muted);
}
.empty-state .empty-icon { font-size: 48px; margin-bottom: 12px; }
.empty-state p { font-size: 15px; }
```

- [ ] **Step 2: Implement renderHistory() in `<script>`**

Replace `function renderHistory() { /* implemented in Task 5 */ }` with:

```js
async function renderHistory(forceRefresh = false) {
  const pane = document.getElementById('tab-history');
  if (!pane) return;

  if (forceRefresh || state.expenses.length === 0) {
    try {
      const data = await api({ action: 'get_expenses', month: state.currentMonth });
      state.expenses = data.expenses || [];
    } catch (_) {}
  }

  const total = state.expenses.reduce((s, e) => s + Number(e.amount), 0);

  // Group by date
  const byDay = {};
  [...state.expenses].sort((a,b) => b.date.localeCompare(a.date)).forEach(e => {
    if (!byDay[e.date]) byDay[e.date] = [];
    byDay[e.date].push(e);
  });

  const dayHTML = Object.entries(byDay).map(([date, items]) => {
    const dayTotal = items.reduce((s,e) => s + Number(e.amount), 0);
    const label = formatDate(date);
    const rows = items.map(e => buildExpenseRow(e)).join('');
    return `
      <div class="day-group">
        <div class="day-header">
          <span>${label}</span>
          <span class="day-total">₪${dayTotal.toFixed(2)}</span>
        </div>
        ${rows}
      </div>
    `;
  }).join('');

  pane.innerHTML = `
    <div class="history-header">
      <div>
        <div class="history-month-title">${state.currentMonth}</div>
        <div class="history-total">₪${total.toFixed(2)}</div>
      </div>
      <button class="refresh-btn" onclick="renderHistory(true)" title="Refresh">↻</button>
    </div>
    ${dayHTML || `
      <div class="empty-state">
        <div class="empty-icon">🧾</div>
        <p>No expenses this month</p>
      </div>
    `}
  `;

  attachSwipeHandlers();
}

function buildExpenseRow(e) {
  const icons = [e.isRecurring ? '↻' : ''].filter(Boolean).join(' ');
  return `
    <div class="expense-row-wrap" data-id="${e.id}">
      <div class="delete-reveal" onclick="deleteExpense('${e.id}')">🗑️</div>
      <div class="expense-row">
        <div class="expense-dot" style="background:${catColor(e.category)}"></div>
        <div class="expense-center">
          <div class="expense-cat">${escHtml(e.category)}${icons ? ` <span class="expense-icons">${icons}</span>` : ''}</div>
          ${e.note ? `<div class="expense-note">${escHtml(e.note)}</div>` : ''}
        </div>
        <div class="expense-amount">₪${Number(e.amount).toFixed(2)}</div>
      </div>
    </div>
  `;
}

function formatDate(dateStr) {
  const d = new Date(dateStr + 'T00:00:00');
  return d.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' });
}

function deleteExpense(id) {
  state.expenses = state.expenses.filter(e => e.id !== id);
  showToast('Deleted locally — server sync not yet supported.');
  renderHistory(false);
}

function attachSwipeHandlers() {
  document.querySelectorAll('.expense-row-wrap').forEach(wrap => {
    const row = wrap.querySelector('.expense-row');
    let startX = 0, currentX = 0, swiping = false;

    function onStart(e) {
      startX = e.touches ? e.touches[0].clientX : e.clientX;
      swiping = true;
    }
    function onMove(e) {
      if (!swiping) return;
      currentX = (e.touches ? e.touches[0].clientX : e.clientX) - startX;
      if (currentX > 0) currentX = 0; // no right-swipe
      row.style.transition = 'none';
      row.style.transform = `translateX(${Math.max(currentX, -80)}px)`;
    }
    function onEnd() {
      if (!swiping) return;
      swiping = false;
      row.style.transition = 'transform 0.2s ease';
      if (currentX < -60) {
        row.style.transform = 'translateX(-80px)'; // snap open
      } else {
        row.style.transform = 'translateX(0)'; // snap closed
      }
      currentX = 0;
    }

    row.addEventListener('touchstart', onStart, { passive: true });
    row.addEventListener('touchmove', onMove, { passive: true });
    row.addEventListener('touchend', onEnd);
    row.addEventListener('pointerdown', onStart);
    row.addEventListener('pointermove', onMove);
    row.addEventListener('pointerup', onEnd);
  });

  // Dismiss open swipes when tapping outside
  // Use a named function stored on the element to avoid accumulating listeners on re-renders
  if (!document._swipeDismissHandler) {
    document._swipeDismissHandler = e => {
      if (!e.target.closest('.expense-row-wrap')) {
        document.querySelectorAll('.expense-row').forEach(r => {
          r.style.transition = 'transform 0.2s ease';
          r.style.transform = 'translateX(0)';
        });
      }
    };
    document.addEventListener('pointerdown', document._swipeDismissHandler, { passive: true });
  }
}
```

- [ ] **Step 3: Open History tab in browser and verify**

Open `index.html` → tap History tab. Check:
- Shows empty state with 🧾 icon (since API_URL is placeholder)
- No JS errors in console

To test with real data: temporarily hardcode `state.expenses` in the `init()` function:
```js
state.expenses = [
  { id:'A1', date:'2026-03-14', amount:45.5, category:'Food', note:'Lunch', isRecurring:false },
  { id:'A2', date:'2026-03-14', amount:12, category:'Transport', note:'', isRecurring:true },
  { id:'A3', date:'2026-03-13', amount:200, category:'Shopping', note:'Shirt', isRecurring:false },
];
```

Verify:
- Expenses grouped by day with sticky headers
- Day totals correct
- Category dot color matches category
- Recurring item shows ↻ icon
- Swipe left on a row: drag past 60px threshold → row snaps to reveal 80px-wide red delete button
- Tap delete: row disappears + toast shows
- Tapping outside a swiped row: row snaps closed

Remove the hardcoded data after testing.

- [ ] **Step 4: Commit**

```bash
git add index.html
git commit -m "feat: implement History tab with grouping, swipe-to-delete"
```

---

## Chunk 4: Dashboard Tab

### Task 6: Dashboard tab — summary card, category bars, insights

**Files:**
- Modify: `index.html` — add Dashboard CSS + implement renderDashboard()

- [ ] **Step 1: Add Dashboard CSS inside `<style>`**

```css
/* ── Dashboard Tab ── */
.month-nav {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}
.month-nav-btn {
  background: none;
  border: none;
  color: var(--text);
  font-size: 24px;
  cursor: pointer;
  padding: 8px 12px;
  -webkit-tap-highlight-color: transparent;
  border-radius: 8px;
}
.month-nav-btn:disabled { color: var(--border); cursor: default; }
.month-nav-label {
  font-size: 17px;
  font-weight: 600;
}

.total-card {
  text-align: center;
  padding: 24px 16px;
}
.total-ils {
  font-family: 'JetBrains Mono', monospace;
  font-size: 42px;
  font-weight: 500;
  color: var(--text);
}
.total-ils::before { content: '₪'; font-size: 24px; color: var(--muted); vertical-align: top; margin-top: 10px; display: inline-block; }
.total-usd {
  font-family: 'JetBrains Mono', monospace;
  font-size: 14px;
  color: var(--muted);
  margin-top: 4px;
}

.cat-bar-row {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 14px;
}
.cat-bar-label {
  width: 100px;
  flex-shrink: 0;
  font-size: 13px;
  display: flex;
  align-items: center;
  gap: 6px;
}
.cat-bar-dot {
  width: 8px; height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}
.cat-bar-wrap {
  flex: 1;
}
.cat-bar-track {
  height: 8px;
  background: var(--border);
  border-radius: 4px;
  overflow: hidden;
}
.cat-bar-fill {
  height: 100%;
  border-radius: 4px;
  transition: width 0.4s ease;
}
.cat-bar-amount {
  font-family: 'JetBrains Mono', monospace;
  font-size: 12px;
  color: var(--muted);
  margin-top: 2px;
}

/* Insights */
.insight-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 0;
  border-bottom: 1px solid var(--border);
  font-size: 14px;
}
.insight-row:last-child { border-bottom: none; }
.insight-badge {
  font-family: 'JetBrains Mono', monospace;
  font-size: 13px;
  font-weight: 500;
  padding: 2px 8px;
  border-radius: 6px;
}
.insight-badge.up   { background: rgba(224,82,82,0.15);  color: var(--danger); }
.insight-badge.down { background: rgba(76,175,125,0.15); color: var(--success); }
.insight-badge.flat { background: var(--border); color: var(--muted); }
```

- [ ] **Step 2: Implement renderDashboard() in `<script>`**

Replace `function renderDashboard() { /* implemented in Task 6 */ }` with:

```js
async function renderDashboard() {
  const pane = document.getElementById('tab-dashboard');
  if (!pane) return;

  // Fetch current and previous month summaries
  let currSummary = {}, total = 0, prevSummary = {};
  const prevMonth = offsetMonth(state.currentMonth, -1);
  try {
    const [curr, prev] = await Promise.all([
      api({ action: 'get_summary', month: state.currentMonth }),
      api({ action: 'get_summary', month: prevMonth }),
    ]);
    currSummary = curr.summary || {};
    total = curr.total || 0;
    prevSummary = prev.summary || {};
  } catch (_) {}

  const isCurrentMonth = state.currentMonth === thisMonth();

  // Category bars
  const maxSpend = Math.max(...Object.values(currSummary), 1);
  const barsHTML = CATEGORIES.map(cat => {
    const spent = currSummary[cat.id] || 0;
    const limit = state.budgets[cat.id] || 0;
    const pct = limit > 0
      ? Math.min((spent / limit) * 100, 100)
      : (spent / maxSpend) * 100;
    const overBudget = limit > 0 && spent > limit;
    const fillColor = overBudget ? 'var(--danger)' : cat.color;
    const limitLabel = limit > 0 ? ` / ₪${limit}` : '';
    return `
      <div class="cat-bar-row">
        <div class="cat-bar-label">
          <div class="cat-bar-dot" style="background:${cat.color}"></div>
          ${cat.id}
        </div>
        <div class="cat-bar-wrap">
          <div class="cat-bar-track">
            <div class="cat-bar-fill" style="width:${pct}%;background:${fillColor}"></div>
          </div>
          <div class="cat-bar-amount">₪${(spent).toFixed(0)}${limitLabel}</div>
        </div>
      </div>
    `;
  }).join('');

  // Insights: categories with spend in either month
  const insightCats = CATEGORIES.filter(cat =>
    (currSummary[cat.id] || 0) > 0 || (prevSummary[cat.id] || 0) > 0
  );
  const insightsHTML = insightCats.map(cat => {
    const curr = currSummary[cat.id] || 0;
    const prev = prevSummary[cat.id] || 0;
    let badge = '';
    if (prev === 0 && curr > 0) {
      badge = `<span class="insight-badge up">NEW</span>`;
    } else if (prev > 0) {
      const pct = ((curr - prev) / prev) * 100;
      const sign = pct >= 0 ? '▲' : '▼';
      const cls = pct > 20 ? 'up' : pct < 0 ? 'down' : 'flat';
      badge = `<span class="insight-badge ${cls}">${sign} ${Math.abs(pct).toFixed(0)}%</span>`;
    }
    return `
      <div class="insight-row">
        <span>${cat.emoji} ${cat.id}</span>
        ${badge}
      </div>
    `;
  }).join('');

  pane.innerHTML = `
    <div class="month-nav">
      <button class="month-nav-btn" onclick="changeDashboardMonth(-1)">‹</button>
      <span class="month-nav-label">${state.currentMonth}</span>
      <button class="month-nav-btn" onclick="changeDashboardMonth(1)"
        ${isCurrentMonth ? 'disabled' : ''}>›</button>
    </div>

    <div class="card total-card">
      <div class="total-ils">${total.toFixed(2)}</div>
      <div class="total-usd">≈ $${(total / state.usdRate).toFixed(2)}</div>
    </div>

    <div class="card">
      <div class="section-label">By Category</div>
      ${barsHTML}
    </div>

    ${insightsHTML ? `
      <div class="card">
        <div class="section-label">vs Last Month (${prevMonth})</div>
        ${insightsHTML}
      </div>
    ` : ''}
  `;
}

function offsetMonth(ym, delta) {
  const [y, m] = ym.split('-').map(Number);
  const d = new Date(y, m - 1 + delta, 1);
  return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}`;
}

async function changeDashboardMonth(delta) {
  const next = offsetMonth(state.currentMonth, delta);
  if (delta > 0 && next > thisMonth()) return;
  state.currentMonth = next;
  // Also refresh expenses (used by History and Export)
  try {
    const data = await api({ action: 'get_expenses', month: state.currentMonth });
    state.expenses = data.expenses || [];
  } catch (_) {}
  renderDashboard();
}
```

- [ ] **Step 3: Open Dashboard tab in browser and verify**

Open `index.html` → tap Dashboard tab. Check:
- Month label shows current month
- Forward `›` arrow disabled (current month)
- Back `‹` arrow works (changes month label)
- No JS errors in console

To test visuals, temporarily set in `init()`:
```js
state.budgets = { Food: 500, Transport: 200, Shopping: 300, Health: 200, Entertainment: 150, Bills: 800 };
// Then call renderDashboard() after setting a mock summary
```

Or just connect to real API. Verify:
- Category bars render with correct colors
- Over-budget categories show red fill
- Insights section shows ▲/▼ badges

- [ ] **Step 4: Commit**

```bash
git add index.html
git commit -m "feat: implement Dashboard tab with category bars and insights"
```

---

## Chunk 5: Settings Tab

### Task 7: Settings tab — budgets, USD rate, favorites management, CSV export

**Files:**
- Modify: `index.html` — add Settings CSS + implement renderSettings()

- [ ] **Step 1: Add Settings CSS inside `<style>`**

```css
/* ── Settings Tab ── */
.settings-section {
  margin-bottom: 24px;
}
.settings-section .section-label {
  margin-bottom: 12px;
}

.budget-row {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 10px;
}
.budget-cat-label {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
}
.budget-input {
  width: 90px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 8px;
  color: var(--text);
  font-family: 'JetBrains Mono', monospace;
  font-size: 14px;
  padding: 8px 10px;
  text-align: right;
  outline: none;
  transition: border-color 0.15s;
}
.budget-input:focus { border-color: var(--accent); }

.fav-setting-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 0;
  border-bottom: 1px solid var(--border);
}
.fav-setting-row:last-child { border-bottom: none; }
.fav-setting-info { flex: 1; }
.fav-setting-name { font-size: 14px; font-weight: 500; }
.fav-setting-sub {
  font-size: 12px;
  color: var(--muted);
  font-family: 'JetBrains Mono', monospace;
}
.icon-btn {
  background: none;
  border: none;
  font-size: 18px;
  cursor: pointer;
  padding: 6px;
  border-radius: 6px;
  -webkit-tap-highlight-color: transparent;
  color: var(--danger);
}

.btn-secondary {
  display: block;
  width: 100%;
  padding: 14px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 10px;
  color: var(--text);
  font-size: 15px;
  font-family: inherit;
  cursor: pointer;
  text-align: center;
  -webkit-tap-highlight-color: transparent;
  transition: border-color 0.15s;
}
.btn-secondary:active { border-color: var(--accent); }
```

- [ ] **Step 2: Implement renderSettings() in `<script>`**

Replace `function renderSettings() { /* Task 8 */ }` with:

```js
function renderSettings() {
  const pane = document.getElementById('tab-settings');
  if (!pane) return;

  // Track original budget values to detect changes
  const origBudgets = { ...state.budgets };

  const budgetRows = CATEGORIES.map(cat => `
    <div class="budget-row">
      <div class="budget-cat-label">
        <span>${cat.emoji}</span>
        <span>${cat.id}</span>
      </div>
      <input class="budget-input" type="number" inputmode="decimal"
        data-cat="${cat.id}"
        placeholder="—"
        value="${state.budgets[cat.id] || ''}">
    </div>
  `).join('');

  const favRows = state.favorites.length
    ? state.favorites.map(f => `
        <div class="fav-setting-row">
          <div class="fav-setting-info">
            <div class="fav-setting-name">${escHtml(f.favoriteName)}</div>
            <div class="fav-setting-sub">${f.category} · ₪${Number(f.amount).toFixed(2)}</div>
          </div>
          <button class="icon-btn" onclick="deleteFavoriteSetting('${f.id}')" title="Delete">🗑️</button>
        </div>
      `).join('')
    : `<p style="color:var(--muted);font-size:13px">No favorites saved yet.</p>`;

  pane.innerHTML = `
    <div class="settings-section">
      <div class="section-label">USD Exchange Rate</div>
      <div class="card" style="display:flex;align-items:center;gap:12px;padding:12px 16px;">
        <span style="color:var(--muted);font-size:14px">1 USD =</span>
        <input class="form-input" type="number" inputmode="decimal" id="usd-rate-input"
          value="${state.usdRate}"
          style="flex:1;padding:8px 12px;font-family:'JetBrains Mono',monospace">
        <span style="color:var(--muted);font-size:14px">ILS</span>
      </div>
    </div>

    <div class="settings-section">
      <div class="section-label">Monthly Budget Limits (ILS)</div>
      <div class="card">
        ${budgetRows}
        <button class="btn-primary" style="margin-top:8px" onclick="saveBudgets()">Save Budgets</button>
      </div>
    </div>

    <div class="settings-section">
      <div class="section-label">Favorites</div>
      <div class="card">${favRows}</div>
    </div>

    <div class="settings-section">
      <div class="section-label">Data</div>
      <button class="btn-secondary" onclick="exportCSV()">
        📥 Export ${state.currentMonth}
      </button>
    </div>
  `;

  // USD rate: save on blur
  document.getElementById('usd-rate-input').addEventListener('blur', e => {
    const val = parseFloat(e.target.value);
    if (!isNaN(val) && val > 0) {
      state.usdRate = val;
      localStorage.setItem('usdRate', val);
      showToast('Exchange rate saved');
    }
  });
}

async function saveBudgets() {
  const inputs = document.querySelectorAll('.budget-input');
  const changed = [];
  inputs.forEach(inp => {
    const cat = inp.dataset.cat;
    const val = parseFloat(inp.value);
    const limit = isNaN(val) ? 0 : val;
    if (limit !== (state.budgets[cat] || 0)) {
      changed.push({ category: cat, monthlyLimit: limit });
    }
  });

  if (changed.length === 0) { showToast('No changes to save'); return; }

  const failed = [];
  for (const { category, monthlyLimit } of changed) {
    try {
      await api({ action: 'set_budget', category, monthlyLimit });
      state.budgets[category] = monthlyLimit;
    } catch (_) {
      failed.push(category);
    }
  }

  if (failed.length > 0) {
    showToast(`Failed to save: ${failed.join(', ')}. Tap Save to retry.`);
  } else {
    showToast('Budgets saved ✓');
  }
}

function deleteFavoriteSetting(id) {
  state.favorites = state.favorites.filter(f => f.id !== id);
  showToast('Removed locally — server sync not yet supported.');
  renderSettings();
}

function exportCSV() {
  if (state.expenses.length === 0) {
    showToast('No expenses to export');
    return;
  }
  const header = 'Date,Category,Amount (ILS),Note,IsRecurring';
  const rows = state.expenses.map(e =>
    [e.date, e.category, e.amount, `"${String(e.note||'').replace(/"/g,'""')}"`, e.isRecurring].join(',')
  );
  const csv = [header, ...rows].join('\n');
  const blob = new Blob([csv], { type: 'text/csv' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = `expenses-${state.currentMonth}.csv`;
  a.click();
  setTimeout(() => URL.revokeObjectURL(a.href), 100);
}
```

- [ ] **Step 3: Open Settings tab in browser and verify**

Open `index.html` → tap Settings tab. Check:
- USD rate input shows 3.7; editing and blurring updates it
- Budget rows show all 7 categories with ₪ inputs
- "Save Budgets" button present
- Favorites section shows "No favorites saved yet"
- Export button shows "Export YYYY-MM"

To test export: add hardcoded expenses to `state.expenses`, then tap Export. Verify a `.csv` file downloads with correct headers and content.

- [ ] **Step 4: Commit**

```bash
git add index.html
git commit -m "feat: implement Settings tab with budgets, favorites, USD rate, CSV export"
```

---

## Chunk 6: Polish + Integration

### Task 8: Integration pass — wire up init(), fix cross-tab state sync

**Files:**
- Modify: `index.html` — update `init()`, fix `submitExpense()` reload, fix `changeDashboardMonth`

- [ ] **Step 1: Update init() to handle API_URL placeholder gracefully**

Replace the existing `init()`:

```js
async function init() {
  if (API_URL === 'YOUR_APPS_SCRIPT_URL') {
    showToast('⚠️ Set API_URL in index.html to connect to your backend');
    renderAdd();
    return;
  }
  try {
    const [favData, budgetData, expData] = await Promise.all([
      api({ action: 'get_favorites' }),
      api({ action: 'get_budgets' }),
      api({ action: 'get_expenses', month: state.currentMonth }),
    ]);
    state.favorites = favData.favorites || [];
    state.budgets   = budgetData.budgets || {};
    state.expenses  = expData.expenses  || [];
  } catch (_) { /* toasts already shown */ }
  renderAdd();
}
```

- [ ] **Step 2: Add `_historyLoaded` flag to the state object**

In `index.html`, find this exact line inside the `const state = {` block:

```js
  currentTab: 'add',
```

Replace it with:

```js
  currentTab: 'add',
  _historyLoaded: false,
```

Do not modify any other lines in the state object.

- [ ] **Step 3: Replace the full `renderHistory` function with the updated version**

Find the full `renderHistory` function (starts with `async function renderHistory(forceRefresh = false) {`) and replace it entirely with:

```js
async function renderHistory(forceRefresh = false) {
  const pane = document.getElementById('tab-history');
  if (!pane) return;

  if (forceRefresh || !state._historyLoaded) {
    state._historyLoaded = true;
    try {
      const data = await api({ action: 'get_expenses', month: state.currentMonth });
      state.expenses = data.expenses || [];
    } catch (_) {}
  }

  const total = state.expenses.reduce((s, e) => s + Number(e.amount), 0);

  // Group by date
  const byDay = {};
  [...state.expenses].sort((a,b) => b.date.localeCompare(a.date)).forEach(e => {
    if (!byDay[e.date]) byDay[e.date] = [];
    byDay[e.date].push(e);
  });

  const dayHTML = Object.entries(byDay).map(([date, items]) => {
    const dayTotal = items.reduce((s,e) => s + Number(e.amount), 0);
    const label = formatDate(date);
    const rows = items.map(e => buildExpenseRow(e)).join('');
    return `
      <div class="day-group">
        <div class="day-header">
          <span>${label}</span>
          <span class="day-total">₪${dayTotal.toFixed(2)}</span>
        </div>
        ${rows}
      </div>
    `;
  }).join('');

  pane.innerHTML = `
    <div class="history-header">
      <div>
        <div class="history-month-title">${state.currentMonth}</div>
        <div class="history-total">₪${total.toFixed(2)}</div>
      </div>
      <button class="refresh-btn" onclick="renderHistory(true)" title="Refresh">↻</button>
    </div>
    ${dayHTML || `
      <div class="empty-state">
        <div class="empty-icon">🧾</div>
        <p>No expenses this month</p>
      </div>
    `}
  `;

  attachSwipeHandlers();
}
```

- [ ] **Step 4: Reset `_historyLoaded` on month change**

In `changeDashboardMonth`, add `state._historyLoaded = false;` after updating `state.currentMonth`:

```js
async function changeDashboardMonth(delta) {
  const next = offsetMonth(state.currentMonth, delta);
  if (delta > 0 && next > thisMonth()) return;
  state.currentMonth = next;
  state._historyLoaded = false;  // ← add this line so History re-fetches on next visit
  try {
    const data = await api({ action: 'get_expenses', month: state.currentMonth });
    state.expenses = data.expenses || [];
  } catch (_) {}
  renderDashboard();
}
```

- [ ] **Step 5: Cross-tab month sync — verify**

Confirm that History uses `state.currentMonth` in its header (it does). When Dashboard changes `state.currentMonth`, switching to History will re-fetch because `_historyLoaded` was reset to `false`.

- [ ] **Step 6: Open full app flow and verify end-to-end**

With `API_URL` still as placeholder:
- App loads → toast "Set API_URL…" appears
- All 4 tabs render without JS errors
- Tab switching works smoothly
- Category grid, toggles, inputs all respond

With `API_URL` set to real endpoint:
- App loads → spinner appears → data loads
- Add expense → appears in History on next visit
- Dashboard shows summary and category bars
- Settings saves budget → Dashboard bars update on revisit

- [ ] **Step 7: Test PWA installability**

Open in Chrome → DevTools → Application tab → Manifest. Confirm:
- Name, theme color, icons all load
- No manifest errors
- Service Worker shows as registered and active
- "Add to Home Screen" prompt appears (may require HTTPS or localhost)

- [ ] **Step 8: Final commit**

```bash
git add index.html
git commit -m "feat: polish init, history load flag, cross-tab month sync"
```

---

### Task 9: Deploy instructions comment at top of index.html

**Files:**
- Modify: `index.html`

- [ ] **Step 1: Add deploy comment after `<!DOCTYPE html>`**

```html
<!--
  EXPENSE TRACKER PWA
  ===================
  Setup:
  1. Deploy Code.gs as a Google Apps Script Web App
     (Execute as: Me, Access: Anyone)
  2. Replace YOUR_APPS_SCRIPT_URL below with the deployment URL
  3. Open index.html in a browser (or serve via any static host)

  Files: index.html (this), manifest.json, sw.js
-->
```

- [ ] **Step 2: Commit**

```bash
git add index.html
git commit -m "docs: add setup instructions comment to index.html"
```
