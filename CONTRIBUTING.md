# Contributing Guide

Thank you for your interest in **WorldMirror**! Below are the ways you can contribute.

---

## Ways to Contribute

### 🐛 Report Bugs

Before opening an issue, please:

1. Visit `http://localhost:5000/test` to check whether the map loads correctly.
2. Visit `http://localhost:5000/api/debug` to confirm that the data files exist.
3. Check the browser console (F12) for any JavaScript errors.
4. Check the terminal output of `collector.py` for error messages.

Your issue should include:
your operating system, Python version, and a screenshot or log of the error.

---

### 💡 Contribute Data

The most welcome contributions are:

**RSS data sources** (`collector.py` → `RSS_FEEDS` dictionary)

* Format: `"Media name": "RSS_URL"`
* Priority sources:

  * Regional / local media
  * Official government media
  * Military / defense-focused professional media

**Static layer data** (`layers_downloader.py`)

* Fix coordinate inaccuracies
* Add missing military bases / launch sites / mining areas
* Note: all data must come from publicly verifiable sources, and a reference link must be provided

---

### 🔧 Code Improvements

* Add new data sources (follow the existing `fetch_*` function patterns)
* Performance optimizations (signal loading, map rendering)
* Mobile responsive support
* New map layer renderers

---

## Development Environment

```bash
git clone https://github.com/houalexdev/worldmirror.git
cd worldmirror
pip install -r requirements.txt

# Run the collector (test mode)
python collector.py

# Start the development server
python app.py
```

---

## Code Style

* Python: follow PEP 8; function naming should use `fetch_xxx` / `render_xxx`
* When adding a new data source, add a description in the header comment of `collector.py`
* Coordinate data format must be unified as:
  `{"lat": float, "lon": float, "name": str, ...}`
* Signal data must include the following fields:
  `id`, `source`, `type`, `time`, `title`, `severity`

---

## Data Source Requirements

* Only data from public and legal sources is accepted
* Do **not** submit any classified, restricted, or unauthorized data
* For military / nuclear facilities, clearly cite public sources
  (such as FAS, public versions of Jane’s, satellite imagery reports, etc.)

---

Thank you to every contributor!
