# Expense Tracker PWA — Design Spec

**Date:** 2026-03-14
**Status:** Approved

---

## Overview

A mobile-first PWA expense tracker delivered as a single `index.html` file backed by a Google Apps Script REST API (`Code.gs`). Installable on iOS/Android via PWA manifest. No build step, no framework — vanilla JS + CSS.

---

## Files

| File | Purpose |
|------|---------|
| `index.html` | App shell + all HTML, CSS, JS inline |
| `manifest.json` | PWA manifest (name, icons, theme color) |
| `sw.js` | Service worker — caches app shell for offline launch |

---

## Visual Language

### Color Palette

```
Background:   #0f1117   near-black slate
Surface:      #1a1d27   card/sheet background
Border:       #2a2d3a   subtle separators
Accent:       #e8a020   amber — CTAs, active tab, highlights
Text primary: #f0f0f5
Text muted:   #6b7280
Danger:       #e05252   over-budget, delete
Success:      #4caf7d   under budget
```

### Category Colors (muted, dark-background-friendly)

| Category | Color |
|---|---|
| Food | #e07b54 terracotta |
| Transport | #5b8dee slate blue |
| Shopping | #c47fd4 muted purple |
| Health | #4caf7d green |
| Entertainment | #e8a020 amber |
| Bills | #e05252 red |
| Other | #6b7280 gray |

### Typography
- UI labels: Inter (Google Fonts)
- Amounts: JetBrains Mono or system monospace
- Minimum touch target: 48px
- Amount input: very large (48–56px font), centered

---

## Navigation

Fixed bottom nav bar (64px, safe-area-aware) with 4 tabs:

| Tab | Icon | Label |
|-----|------|-------|
| Add | ➕ | Add |
| History | 📋 | History |
| Dashboard | 📊 | Dashboard |
| Settings | ⚙️ | Settings |

Active tab: amber accent + label visible. Inactive: muted icon only.
Content area scrolls independently above the nav bar.

---

## Tab: Add

### Layout (top to bottom)
1. **Favorites strip** — horizontal scroll row of pill buttons. Tapping pre-fills the form. A ⭐ button at the end saves current form as a new favorite (prompts for a name).
2. **Amount input** — large centered `₪` field, number keyboard. Line below shows `≈ $XX.XX` using current USD rate.
3. **Category grid** — 3×3 grid of emoji+label tap buttons. Selected state: amber border + slight background tint.
4. **Note field** — single-line optional text input.
5. **Date picker** — defaults to today (`YYYY-MM-DD`). Tapping opens native date input.
6. **Recurring toggle** — pill toggle switch, off by default.
7. **Add Expense button** — full-width amber, 52px tall. Submits to `add_expense` API.

### Behavior
- Amount field auto-focuses on tab open.
- Form resets after successful submission (amount cleared, category deselected, note cleared; date + recurring preserved).
- If no category selected, button disabled + shake animation on tap.

---

## Tab: History

### Layout
- Month header with total for that month (matches `currentMonth` in state).
- Expenses grouped by day — sticky day header showing date + daily subtotal.
- Each expense row:
  - Left: colored dot (category color)
  - Center: category label + note (if any)
  - Right: `₪ amount` in mono font
  - Swipe left to reveal red Delete button

### Behavior
- Loads `get_expenses` for current month on tab open.
- Refresh icon in header re-fetches.
- Delete calls `delete_expense` — **Note:** `Code.gs` does not currently implement delete; frontend should optimistically remove from list and show a "not yet implemented" toast, or skip delete for MVP.
- Empty state: illustrated empty state message ("No expenses this month").

---

## Tab: Dashboard

### Layout (top to bottom)
1. **Month selector** — `← 2026-03 →` arrows to navigate months.
2. **Total card** — large ILS total, USD equivalent below, surface card style.
3. **Category breakdown** — one row per category:
   - Label + spent amount
   - Progress bar: filled = spent, background = limit. Turns red when `spent > limit`.
   - If no budget set, bar shows as indeterminate gray.
4. **Insights section** — compare current vs previous month per category:
   - Badge: `▲ +34%` in danger red if >20% increase, `▼ -12%` in success green if decrease.
   - Only shows categories with spend in either month.

### Behavior
- On month change, fetches `get_summary` for selected month and the month before it.
- Budgets loaded from `get_budgets` (cached in state, refreshed on Settings save).

---

## Tab: Settings

### Sections
1. **USD Exchange Rate** — number input, saves to `localStorage` on blur.
2. **Budget Limits** — one editable row per category (category name + `₪` input). "Save Budgets" button calls `set_budget` for each changed row.
3. **Favorites** — list of saved favorites with name, category, amount. Trash icon deletes (removes from Google Sheet — **Note:** no delete API exists in `Code.gs`; for MVP, remove from local state only and show toast).
4. **Export CSV** — fetches all expenses for current month, formats as CSV, triggers browser download.

---

## State Model

```js
const state = {
  currentTab: 'add',
  currentMonth: 'YYYY-MM',     // defaults to today's month
  expenses: [],                 // current month's expenses
  favorites: [],                // loaded on startup
  budgets: {},                  // { Category: monthlyLimit }
  usdRate: 3.7,                 // persisted in localStorage
  form: {
    amount: '',
    category: null,
    note: '',
    date: today,
    isRecurring: false,
  }
}
```

---

## API Layer

Thin inline module. Every call:
1. Shows full-screen spinner overlay
2. POSTs JSON to `API_URL` (constant at top of file)
3. Hides spinner on resolve/reject
4. On error: shows bottom toast (3s auto-dismiss, non-blocking)

### Actions used by frontend

| Action | Trigger |
|--------|---------|
| `add_expense` | Add form submit |
| `get_expenses` | History tab open, month change |
| `get_summary` | Dashboard tab open, month change |
| `get_favorites` | App startup |
| `add_favorite` | ⭐ button on Add tab |
| `get_budgets` | App startup |
| `set_budget` | Settings save |
| `get_recurring` | Not used in frontend MVP |
| `apply_recurring` | Not used in frontend MVP |

---

## PWA

### `manifest.json`
- `name`: "Expense Tracker"
- `short_name`: "Expenses"
- `theme_color`: `#0f1117`
- `background_color`: `#0f1117`
- `display`: `standalone`
- `start_url`: `./index.html`
- Icons: placeholder 192×192 and 512×512 (SVG-based, inline-generated)

### `sw.js`
- Cache-first strategy for app shell (`index.html`, `manifest.json`)
- Network-only for all API calls (no caching of expense data)
- Cache version constant at top for easy invalidation

---

## Out of Scope (MVP)

- Installments UI (field hidden; backend column exists)
- `apply_recurring` UI trigger
- Delete expense API (backend not implemented)
- Delete favorite API (backend not implemented)
- Multi-currency support beyond ILS/USD
- Authentication / multi-user
- Push notifications for budget alerts
