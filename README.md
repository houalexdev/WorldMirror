# WorldMirror 🌍

**Global Situational Awareness Dashboard**

A real-time global monitoring dashboard built entirely on free and public data sources.
It aggregates conflict events, natural disasters, military activities, nuclear facilities, and strategic infrastructure across **27 layers**, providing an intelligence-grade visualization interface.
No paid APIs are required.

![alt tag](https://raw.githubusercontent.com/houalexdev/WorldMirror/main/demo.png)

> A free, open-source global intelligence dashboard built entirely on public data. No paid APIs required.

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python\&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-3.x-000000?logo=flask)
![License](https://img.shields.io/badge/License-MIT-22c55e)
![Sources](https://img.shields.io/badge/Data_Sources-12_live_·_15_static-f97316)

---

## Features Overview

### Real-Time Signal Collection (12 data sources)

| Source               | Content                                                 | Update Frequency |
| -------------------- | ------------------------------------------------------- | ---------------- |
| **GDELT**            | Global conflicts / protests / diplomatic events         | Every 15 minutes |
| **USGS**             | Earthquakes M2.5+                                       | Real time        |
| **NASA EONET**       | Storms / volcanoes / floods and other natural disasters | Real time        |
| **NASA FIRMS**       | Wildfire hotspot pixels                                 | Hourly           |
| **OpenSky Network**  | Real-time military aircraft tracking                    | Real time        |
| **NOAA Alerts**      | Severe weather alerts                                   | Real time        |
| **ACLED**            | Protests / armed conflicts / civil unrest               | Daily            |
| **Polymarket**       | Geopolitical prediction-market intelligence             | Hourly           |
| **FAA NASSTATUS**    | Flight delays / ground stops                            | Real time        |
| **NetBlocks / IODA** | Internet outage events                                  | Real time        |
| **USGS Volcano**     | Volcanic activity bulletins                             | Real time        |
| **RSS (186 feeds)**  | Global news / military / cybersecurity                  | Real time        |

---

### Static Strategic Layers (15 layers, updated monthly)

| Category                   | Layers                                                                                                                       |
| -------------------------- | ---------------------------------------------------------------------------------------------------------------------------- |
| ☢️ Nuclear & Strategic     | Nuclear power plants, nuclear weapons facilities (stockpiles / enrichment / design institutes), industrial gamma irradiators |
| 🪖 Military & Space        | 150+ US / NATO / China / Russia military bases, 30+ global space launch sites                                                |
| 🌊 Critical Infrastructure | Submarine cables, oil & gas pipelines, 61 strategic ports, 20 strategic waterways, major trade routes                        |
| 🌍 Humanitarian            | UCDP armed conflict events, UNHCR refugee flows                                                                              |
| 💰 Economy & Resources     | Global stock exchanges / central banks, critical mineral sites, AI data centers (≥10,000 GPUs)                               |
| 🌐 Overlay                 | Real-time day / night terminator line (auto-updated every 60 seconds)                                                        |

---

### Visualization Features

* Interactive dark map (CartoDB Dark Matter basemap) with 5 severity color levels
* Real-time signal stream panel with multi-dimensional filtering by date, source, severity, and keywords
* Independent layer toggles with lazy loading (non-blocking UI)
* Click a signal to auto-locate on the map and expand its detail panel
* Auto refresh every 15 minutes, real-time UTC clock
* Built-in diagnostics tools (`/test` test page, `/api/debug` diagnostics endpoint)

---

## Quick Start

### Requirements

* Python 3.10+
* Public internet access (for map CDN and data APIs)

---

### Installation

```bash
git clone https://github.com/YOUR_USERNAME/worldmirror.git
cd worldmirror
pip install -r requirements.txt
```

---

### Step 1 — Download static layers (first run, ~1 minute)

```bash
python layers_downloader.py
```

Data will be saved to `data/layers/`.
After that, running it once per month is sufficient.

---

### Step 2 — Collect real-time signals

```bash
python collector.py
```

Data is saved to:

```
data/signals_YYYY-MM-DD.ndjson
```

It is recommended to schedule the collector to run every 15 minutes:

```bash
# Linux / macOS (crontab -e)
*/15 * * * * cd /path/to/worldmirror && python collector.py >> logs/collector.log 2>&1

# Windows Task Scheduler
schtasks /create /tn "WorldMirror" /tr "python C:\worldmirror\collector.py" /sc minute /mo 15 /f
```

---

### Step 3 — Start the dashboard

```bash
python app.py
# Open http://localhost:5000
```

---

## Optional API Key Configuration

The system works without any API keys.
Providing keys unlocks more complete or higher-resolution data:

```bash
cp .env.example .env
# Edit .env and fill in the corresponding keys
```

| Environment Variable                        | Purpose                               | Apply at                                                                               |
| ------------------------------------------- | ------------------------------------- | -------------------------------------------------------------------------------------- |
| `NASA_FIRMS_KEY`                            | Wildfire hotspots (higher resolution) | [https://firms.modaps.eosdis.nasa.gov/api/](https://firms.modaps.eosdis.nasa.gov/api/) |
| `OPENSKY_CLIENT_ID` `OPENSKY_CLIENT_SECRET` | Military aircraft real-time tracking  | [https://opensky-network.org](https://opensky-network.org) → API Client                |
| `ACLED_KEY`                                 | Protest / conflict events             | [https://acleddata.com/register/](https://acleddata.com/register/)                     |

---

## Project Structure

```
worldmirror/
├── app.py                    # Flask server + full frontend (single file)
├── collector.py              # Real-time data collector
├── layers_downloader.py      # Static layer downloader (run monthly)
├── requirements.txt
├── .env.example
├── .gitignore
└── data/                     # Runtime data (not committed)
    ├── signals_YYYY-MM-DD.ndjson
    └── layers/
        ├── military_bases.json
        ├── nuclear_weapons.json
        ├── nuclear_plants.json
        ├── gamma_irradiators.json
        ├── spaceports.json
        ├── chokepoints.json
        ├── ports.json
        ├── trade_routes.json
        ├── submarine_cables.json
        ├── pipelines.json
        ├── economic_centers.json
        ├── minerals.json
        ├── ai_datacenters.json
        ├── unhcr_flows.json
        └── ucdp_events.json
```

---

## REST API

| Endpoint               | Description                                                 |
| ---------------------- | ----------------------------------------------------------- |
| `GET /api/signals`     | Signal list, supports `?date=&source[]=&severity[]=&limit=` |
| `GET /api/dates`       | List of available dates                                     |
| `GET /api/stats?date=` | Statistics by source / severity / type                      |
| `GET /api/layer/<n>`   | Single static layer (JSON)                                  |
| `GET /api/layers`      | List of downloaded layers                                   |
| `GET /api/debug`       | Data directory diagnostics                                  |
| `GET /test`            | Map loading test page                                       |

**Signal data structure (NDJSON, one record per line):**

```json
{
  "id": "uuid",
  "source": "gdelt",
  "type": "conflict",
  "time": "2026-03-01T07:00:00+00:00",
  "lat": 33.724,
  "lon": 51.727,
  "country": "Iran",
  "title": "Event title",
  "summary": "Summary text",
  "severity": "critical|high|medium|low|info",
  "url": "https://...",
  "raw": {}
}
```

---

## Data Sources

GDELT · USGS · NASA EONET · NASA FIRMS · OpenSky Network · ACLED · NOAA · UCDP · UNHCR · GeoNuclearData · Polymarket · NetBlocks

---

## Disclaimer

This project is intended for academic research and information aggregation only.
All data is collected from public sources.

Coordinates and information for military bases and nuclear facilities are derived from open-source intelligence and public reports and may be inaccurate or outdated.

Do not use this tool for any illegal or harmful purposes.
This project is not affiliated with any government agency.

---

## License

MIT

---

## Contributing

Pull requests are welcome.
In particular, we highly appreciate:

* Adding RSS data sources
* Fixing coordinate data
* Adding new layers
* Mobile adaptation
* Multi-language support

If you encounter problems, please check `/test` and `/api/debug` first before opening an issue.
