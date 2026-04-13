# ERG Air Monitoring — Card-Based UI Reference

## Purpose

This document describes the architecture and design rationale for `cards.html`, a mobile-first card-based interface for the EPA Region 9 Emergency Response Group (ERG) air monitoring chemical reference table. It replaces a traditional HTML `<table>` with a layout optimized for field use on phones — gloved hands, direct sunlight, poor connectivity.

Feed this file and `cards.html` into Cursor as context when modifying the UI.

---

## File Overview

| File | Role |
|------|------|
| `cards.html` | Standalone HTML/CSS/JS page. No build step, no framework. Drops directly into the GitHub Pages PWA alongside `table.html`, `index.html`, etc. |
| `erg-air-monitoring-cards.jsx` | React prototype (for reference only). Same logic, useful if you ever migrate to a component framework. |

---

## Architecture

### Data Layer

The `DATA` array at the top of `<script>` is a flat array of objects. Each object represents one **chemical–device–sensor combination** (not one chemical). This means benzene appears multiple times — once per device/sensor pairing.

**To connect to real data:** Replace the `DATA` array with a `fetch()` call to a JSON file (e.g., `data_reference/air_monitoring.json`). The service worker should pre-cache this JSON so it works offline. The data shape per record:

```json
{
  "id": 1,
  "chemical": "Benzene",
  "cas": "71-43-2",
  "device": "MiniRAE 3000",
  "sensor": "PID (10.6 eV)",
  "range": "0–15,000 ppm",
  "resolution": "0.1 ppm",
  "cf": 0.53,
  "pel": 1,
  "stel": 5,
  "idlh": 500,
  "pac1": 9,
  "pac2": 150,
  "pac3": 800,
  "notes": "Known carcinogen. CF validated for isobutylene-calibrated PID."
}
```

**Nullable fields:** `cf`, `stel`, `idlh`, `notes` can all be `null`. The UI handles each gracefully (hides the cell, shows "N/D", etc.).

### Filtering System

There are **two filter mechanisms** that work together:

1. **Free-text search** — Matches against `chemical`, `device`, `sensor`, `cas`, and `notes`. Case-insensitive substring match. This is the primary entry point for most lookups.

2. **Cascading cross-filter dropdowns** — Chemical, Device, Sensor. Unlike the original `table.html` which forced a Chemical → Device → Sensor cascade, these are **bidirectional**: selecting a device narrows the chemical dropdown to only chemicals that device can detect, and vice versa. Any combination works as an entry point. The `populateDropdowns()` function rebuilds each `<select>` based on what the *other two* filters currently allow.

### Card Rendering

Cards are rendered via string concatenation in `renderCard()` and inserted as `innerHTML`. This is intentional — no virtual DOM, no diffing, no build step. For a dataset of <500 records with simple DOM, this is fast enough and keeps the PWA dependency-free.

**Card states:**
- **Collapsed (default):** Shows chemical name, CAS#, IDLH badge, device/sensor badges, and a values grid (PEL, STEL, CF, Range). This is the "glance" view — enough to confirm you have the right chemical/device and see the key numbers.
- **Expanded (tap):** Adds PAC-1/2/3 values, resolution, and field notes. Only one card expands at a time (`expandedId` tracks this).

### Layout & Responsiveness

- **Mobile (<640px):** Single column stack. Cards are full-width.
- **Tablet (640–959px):** 2-column CSS grid.
- **Desktop (960px+):** 3-column CSS grid.

The header and search bar are `position: sticky` so they remain accessible while scrolling through results.

---

## Design Rationale for Field Use

### Why cards instead of a table

A data table with 8+ columns forces horizontal scrolling on a phone. In the field, responders wear nitrile or Tyvek gloves that make precise horizontal pan gestures unreliable. A card layout presents each chemical–device–sensor combo as a self-contained block that can be read vertically with no horizontal interaction.

### Why dark theme

- Reduces glare in outdoor/variable lighting.
- Saves battery on OLED screens (which most modern phones have).
- Monospace font (`JetBrains Mono` → fallback chain) ensures numeric values align visually and are unambiguous (no confusion between 0/O, 1/l).

### Why search-first over dropdowns-first

In emergency response, the responder usually knows *what* they're looking for — a chemical name, a CAS number, or a device model. Typing 3–4 characters into a search box is faster than navigating three sequential dropdown menus. The dropdowns still exist for browsing/narrowing, but they're secondary (hidden behind a toggle by default).

### IDLH Badge placement

The IDLH (Immediately Dangerous to Life or Health) value is positioned in the top-right corner of every card as a prominent badge. This is the single most critical number for a responder — it determines whether they need SCBA or can work in APR. The color coding (red ≤50, orange ≤300, yellow >300, dark gold for N/D) is a severity indicator. **The owner has indicated they don't need the IDLH color coding** — this can be removed or simplified to a single accent color.

### PAC values in expanded view

PAC (Protective Action Criteria) tiers are shown only on expand because they're used for evacuation planning, not immediate PPE decisions. They're color-coded green/yellow/red for the three escalating tiers. Keeping them in the expanded section avoids visual overload on the collapsed card.

### Field notes with warning icon

The amber warning-triangle icon on field notes draws attention to operational caveats — cross-sensitivities, CF limitations, preferred alternative instruments. These are the kind of "gotchas" that experienced responders know but newer techs might miss.

---

## How to Modify

### Changing the color scheme

All colors are in CSS custom properties (`:root` block). Change `--accent` to rebrand the green highlight. Change `--bg-page`, `--bg-card`, `--bg-header` to switch between dark/light themes.

### Adding or removing card fields

1. Add the field to the `DATA` objects.
2. Add a `<div class="val-cell">` inside the `.values-grid` in `renderCard()` for collapsed-view fields, or add a `.detail-row` inside `.expanded-section` for expanded-view fields.
3. If the field is nullable, wrap it in a conditional: `${d.newField ? '...' : ''}`

### Connecting to live data

Replace the `DATA` array with:

```js
let DATA = [];
fetch('data_reference/air_monitoring.json')
  .then(r => r.json())
  .then(d => { DATA = d; render(); });
```

Make sure the service worker pre-caches `air_monitoring.json`:

```js
// In sw.js, add to the CACHE_URLS array:
'data_reference/air_monitoring.json'
```

### Adding the "last updated" timestamp

The `#last-updated` span is in the header. Set it dynamically from the data file's metadata or a build timestamp:

```js
document.getElementById('last-updated').textContent = '2026-04-01';
```

### Removing IDLH color coding

In `renderCard()`, replace the dynamic `idlhColor()` / `idlhBg()` calls with static values:

```js
style="color: var(--accent); background: var(--accent-bg); border-color: var(--accent-border);"
```

Then delete the `idlhColor()` and `idlhBg()` functions.

### Adding this page to the PWA nav

The nav bar in `cards.html` already includes links to `index.html`, `table.html`, `matrix-sampling.html`. Add a reciprocal link in those pages:

```html
<a href="cards.html">Card View</a>
```

Add `cards.html` to the service worker's cached file list.

---

## File Dependencies

- **None.** No npm packages, no build tools, no CDN imports. The page is fully self-contained HTML/CSS/JS.
- Fonts: Uses system monospace stack with `JetBrains Mono` as preferred (loaded from user's system if available; does not import from Google Fonts). Add a `<link>` to Google Fonts if you want guaranteed JetBrains Mono rendering.

---

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `/` | Focus search bar (when not already in an input) |

---

## Known Limitations / Future Work

- **No offline indicator** — should show a banner when the service worker is serving cached data vs. live.
- **No sorting** — cards are rendered in data-array order. Could add sort-by-chemical, sort-by-IDLH, sort-by-CF.
- **No export** — could add a "copy to clipboard" button per card for pasting values into field logs.
- **No unit conversion** — all values are in ppm. Some responders may want mg/m³.
- **Card expand/collapse re-renders entire list** — for <500 records this is fine; for larger datasets, consider targeted DOM updates.
