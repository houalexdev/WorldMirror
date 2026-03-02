"""
collector.py ── WorldMirror Data Collector v1.0
============================================================
Runs every 15 minutes to collect all freely available real-time signals.

Dynamic Data Sources (this file):
  ✅ GDELT          Global Events/Conflicts/Protests       Every 15 min
  ✅ USGS           Earthquakes                            Real-time
  ✅ NASA EONET     Natural Disasters (Storm/Volcano/Flood) Real-time
  ✅ NASA FIRMS     Wildfire Hotspots                      Hourly
  ✅ OpenSky        Military Flight Tracking               Real-time
  ✅ Polymarket      Prediction Market Intelligence         Hourly
  ✅ RSS (186 src)  News/Intel/Cyber Threats               Real-time
  ✅ USGS Volcano   Volcanic Activity                      Real-time
  ✅ FAA NASSTATUS  Flight Delays/Ground Stops             Real-time
  ✅ NOAA Alerts    Weather Warnings                       Real-time
  ✅ NetBlocks/IODA Internet Outages                       Real-time
  ✅ ACLED (Protest) Social Unrest/Demonstrations         Daily

Static Layer Data → See layers_downloader.py (Monthly)

Output: ./data/signals_YYYY-MM-DD.ndjson
        ./data/layers/*.json

Usage:
  pip install requests feedparser python-dateutil --break-system-packages
  python collector.py

Environment Variables (Optional):
  NASA_FIRMS_KEY      NASA FIRMS API Key (Free from firms.modaps.eosdis.nasa.gov)
  OPENSKY_CLIENT_ID   OpenSky OAuth2 Client ID
  OPENSKY_CLIENT_SECRET
  ACLED_KEY           ACLED API Key (Free from acleddata.com)
============================================================
"""

import csv
import io
import json
import logging
import os
import re
import time
import uuid
import zipfile
from datetime import datetime, timezone
from typing import Optional
import xml.etree.ElementTree as ET

import feedparser
import requests
from dateutil import parser as dateparser

# ── Logging ───────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("collector")

# ── Directories ───────────────────────────────────────────────
DATA_DIR = "./data"
LAYERS_DIR = "./data/layers"
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(LAYERS_DIR, exist_ok=True)

# ── Environment Variables ─────────────────────────────────────
NASA_FIRMS_KEY      = os.getenv("NASA_FIRMS_KEY", "")
OPENSKY_CLIENT_ID   = os.getenv("OPENSKY_CLIENT_ID", "")
OPENSKY_CLIENT_SECRET = os.getenv("OPENSKY_CLIENT_SECRET", "")
ACLED_KEY           = os.getenv("ACLED_KEY", "")

# ── OpenSky Token Cache ───────────────────────────────────────
_opensky_token: Optional[str] = None
_opensky_token_expiry: float = 0

OPENSKY_TOKEN_URL = "https://auth.opensky-network.org/auth/realms/opensky-network/protocol/openid-connect/token"


# ═══════════════════════════════════════════════════════════════
# Utility Functions
# ═══════════════════════════════════════════════════════════════

def today_filename() -> str:
    return os.path.join(DATA_DIR, f"signals_{datetime.now(timezone.utc).strftime('%Y-%m-%d')}.ndjson")


def append_signals(signals: list[dict]):
    if not signals:
        return
    path = today_filename()
    with open(path, "a", encoding="utf-8") as f:
        for s in signals:
            f.write(json.dumps(s, ensure_ascii=False) + "\n")


def make_signal(source, stype, title, summary="", lat=None, lon=None,
                country="", severity="info", url="", extra=None) -> dict:
    return {
        "id": str(uuid.uuid4()),
        "source": source,
        "type": stype,
        "time": datetime.now(timezone.utc).isoformat(),
        "lat": lat,
        "lon": lon,
        "country": country,
        "title": title,
        "summary": summary,
        "severity": severity,
        "url": url,
        "raw": extra or {},
    }


def _get(url: str, timeout: int = 20, **kwargs) -> requests.Response:
    headers = kwargs.pop("headers", {})
    headers.setdefault("User-Agent", "WorldMirror/1.0 (research)")
    resp = requests.get(url, timeout=timeout, headers=headers, **kwargs)
    resp.raise_for_status()
    return resp


def _get_opensky_token() -> Optional[str]:
    global _opensky_token, _opensky_token_expiry
    if not OPENSKY_CLIENT_ID:
        return None
    now = time.time()
    if _opensky_token and now < _opensky_token_expiry:
        return _opensky_token
    try:
        resp = requests.post(OPENSKY_TOKEN_URL, data={
            "grant_type": "client_credentials",
            "client_id": OPENSKY_CLIENT_ID,
            "client_secret": OPENSKY_CLIENT_SECRET,
        }, timeout=15)
        resp.raise_for_status()
        j = resp.json()
        _opensky_token = j["access_token"]
        _opensky_token_expiry = now + j.get("expires_in", 1500) - 60
        return _opensky_token
    except Exception as e:
        log.warning(f"Failed to get OpenSky token: {e}")
        return None


# ═══════════════════════════════════════════════════════════════
# 1. GDELT ── Global Events/Conflicts/Protests (Updated every 15 min)
# ═══════════════════════════════════════════════════════════════

GDELT_SEVERITY = {
    # EventCode Prefix → severity
    "17": "critical", "18": "critical", "19": "critical", "20": "critical",
    "14": "high", "15": "high", "16": "high",
    "10": "high", "11": "high", "12": "high", "13": "high",
    "05": "medium", "06": "medium", "07": "medium", "08": "medium", "09": "medium",
}

GDELT_TYPE_MAP = {
    "14": "protest", "15": "protest", "16": "protest",
    "17": "conflict", "18": "conflict", "19": "conflict", "20": "conflict",
    "10": "conflict", "11": "conflict", "12": "conflict", "13": "conflict",
    "05": "diplomatic", "06": "diplomatic", "07": "diplomatic",
}

def collect_gdelt() -> list[dict]:
    log.info("GDELT: Collecting...")
    try:
        # Get latest 15-minute file list
        resp = _get("http://data.gdeltproject.org/gdeltv2/lastupdate.txt", timeout=15)
        lines = resp.text.strip().splitlines()
        zip_url = None
        for line in lines:
            parts = line.split()
            if len(parts) >= 3 and parts[2].endswith("export.CSV.zip"):
                zip_url = parts[2]
                break
        if not zip_url:
            log.warning("GDELT: CSV link not found")
            return []

        raw = _get(zip_url, timeout=60).content
        with zipfile.ZipFile(io.BytesIO(raw)) as zf:
            csv_text = zf.read(zf.namelist()[0]).decode("utf-8")

        signals = []
        reader = csv.reader(io.StringIO(csv_text), delimiter="\t")
        for row in reader:
            if len(row) < 57:
                continue
            try:
                lat = float(row[53]) if row[53] else None
                lon = float(row[54]) if row[54] else None
                if not lat or not lon:
                    continue
                event_code = row[26][:2] if row[26] else ""
                stype = GDELT_TYPE_MAP.get(event_code, "news_event")
                severity = GDELT_SEVERITY.get(event_code, "info")
                country = row[51] or ""
                actor1 = row[6] or ""
                actor2 = row[16] or ""
                title = f"GDELT: {actor1} → {actor2}" if actor1 else f"GDELT: {country} Event"
                url = row[57] if len(row) > 57 else ""
                signals.append(make_signal(
                    source="gdelt", stype=stype,
                    title=title, summary=f"EventCode:{event_code} Region:{country}",
                    lat=lat, lon=lon, country=country, severity=severity,
                    url=url,
                ))
            except (ValueError, IndexError):
                continue

        log.info(f"GDELT: {len(signals)} events")
        return signals
    except Exception as e:
        log.error(f"GDELT failed: {e}")
        return []


# ═══════════════════════════════════════════════════════════════
# 2. USGS ── Earthquakes (Real-time)
# ═══════════════════════════════════════════════════════════════

def collect_usgs() -> list[dict]:
    log.info("USGS: Collecting earthquake data...")
    url = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/significant_hour.geojson"
    # Also fetch M2.5+ earthquakes from the past hour
    url2 = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/2.5_hour.geojson"
    signals = []
    for u in [url, url2]:
        try:
            data = _get(u).json()
            for f in data.get("features", []):
                p = f["properties"]
                coords = f["geometry"]["coordinates"]
                mag = p.get("mag", 0) or 0
                severity = "critical" if mag >= 7 else "high" if mag >= 6 else "medium" if mag >= 5 else "low"
                place = p.get("place", "Unknown")
                signals.append(make_signal(
                    source="usgs", stype="earthquake",
                    title=f"Earthquake M{mag:.1f} - {place}",
                    summary=f"Mag {mag}, Depth {coords[2]:.1f} km",
                    lat=coords[1], lon=coords[0],
                    severity=severity,
                    url=p.get("url", ""),
                ))
        except Exception as e:
            log.error(f"USGS failed ({u}): {e}")
    log.info(f"USGS: {len(signals)} earthquakes")
    return signals


# ═══════════════════════════════════════════════════════════════
# 3. NASA EONET ── Natural Disasters (Storm/Volcano/Flood/Wildfire)
# ═══════════════════════════════════════════════════════════════

EONET_SEVERITY = {
    "Volcanoes": "high", "Wildfires": "medium", "Severe Storms": "high",
    "Floods": "medium", "Earthquakes": "high", "Landslides": "medium",
    "Sea and Lake Ice": "low", "Drought": "medium", "Dust and Haze": "low",
    "Snow": "low", "Temperature Extreme": "medium",
}

def collect_eonet() -> list[dict]:
    log.info("NASA EONET: Collecting natural disasters...")
    url = "https://eonet.gsfc.nasa.gov/api/v3/events?status=open&days=3&limit=100"
    signals = []
    for attempt in range(3):
        try:
            data = _get(url, timeout=20).json()
            for ev in data.get("events", []):
                cat = ev.get("categories", [{}])[0].get("title", "Unknown")
                geo = ev.get("geometry", [{}])[-1] if ev.get("geometry") else None
                if not geo or geo.get("type") != "Point":
                    continue
                coords = geo["coordinates"]
                severity = EONET_SEVERITY.get(cat, "info")
                signals.append(make_signal(
                    source="nasa_eonet", stype="natural_disaster",
                    title=f"{cat}: {ev.get('title', '')}",
                    summary=f"NASA EONET natural event, Category: {cat}",
                    lat=coords[1], lon=coords[0],
                    severity=severity,
                    url=ev.get("sources", [{}])[0].get("url", ""),
                ))
            log.info(f"NASA EONET: {len(signals)} events")
            return signals
        except requests.HTTPError as e:
            if e.response and e.response.status_code == 503:
                time.sleep(5 * (attempt + 1))
            else:
                log.error(f"NASA EONET failed: {e}")
                return []
        except Exception as e:
            log.error(f"NASA EONET failed: {e}")
            return []
    return signals


# ═══════════════════════════════════════════════════════════════
# 4. NASA FIRMS ── Wildfire Hotspots (Hourly)
# ═══════════════════════════════════════════════════════════════

def collect_firms() -> list[dict]:
    log.info("NASA FIRMS: Collecting wildfires...")
    key = NASA_FIRMS_KEY or "DEMO_KEY"
    url = f"https://firms.modaps.eosdis.nasa.gov/api/country/csv/{key}/VIIRS_SNPP_NRT/World/1"
    signals = []
    try:
        text = _get(url, timeout=60).text
        reader = csv.DictReader(io.StringIO(text))
        count = 0
        for row in reader:
            try:
                lat = float(row["latitude"])
                lon = float(row["longitude"])
                bright = float(row.get("bright_ti4", 0) or 0)
                frp = float(row.get("frp", 0) or 0)
                severity = "critical" if frp > 1000 else "high" if frp > 100 else "medium" if frp > 10 else "low"
                signals.append(make_signal(
                    source="nasa_firms", stype="wildfire",
                    title=f"Wildfire Hotspot (FRP:{frp:.0f} MW)",
                    summary=f"BrightTemp:{bright:.0f}K, RadiativePower:{frp:.0f}MW",
                    lat=lat, lon=lon,
                    country=row.get("country_id", ""),
                    severity=severity,
                ))
                count += 1
                if count >= 3000:  # Limit quantity
                    break
            except (ValueError, KeyError):
                continue
        log.info(f"NASA FIRMS: {len(signals)} fire points")
    except Exception as e:
        log.error(f"NASA FIRMS failed: {e}")
    return signals


# ═══════════════════════════════════════════════════════════════
# 5. OpenSky ── Military Flight Tracking
# ═══════════════════════════════════════════════════════════════

# Military callsign prefixes
MILITARY_CALLSIGNS = {
    # USA
    "RCH", "SAM", "VENUS", "JAKE", "DUKE", "ATOM", "REACH",
    "DARK", "EVIL", "VIPER", "GHOST", "DEATH", "WRATH",
    "KNIFE", "SABER", "HAWK", "EAGLE", "FALCON", "RAPTOR",
    "CANOPY", "IRON", "STEEL", "BRASS",
    # UK
    "RRR", "ASCOT", "VANGUARD",
    # Russia ICAO prefixes: RA- RU-
    # China PLA: B-PL
    # NATO
    "NATO", "AWACS",
}

MILITARY_ICAO_PREFIXES = {
    "ae": "US Military",
    "43": "Russian Military",
    "78": "Chinese Military",
    "4b": "NATO/UK Military",
    "3c": "German Military",
}


def collect_opensky() -> list[dict]:
    log.info("OpenSky: Collecting military flights...")
    token = _get_opensky_token()
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    # Use anonymous API when not authenticated (basic data only)
    url = "https://opensky-network.org/api/states/all"
    signals = []
    try:
        resp = requests.get(url, headers=headers, timeout=30)
        if resp.status_code == 401:
            log.warning("OpenSky: Authentication required, skipping")
            return []
        resp.raise_for_status()
        data = resp.json()

        for sv in (data.get("states") or []):
            if not sv or len(sv) < 6:
                continue
            icao24 = (sv[0] or "").lower()
            callsign = (sv[1] or "").strip().upper()
            lat = sv[6]
            lon = sv[5]
            if lat is None or lon is None:
                continue

            is_military = False
            mil_type = ""

            # Check callsign
            for prefix in MILITARY_CALLSIGNS:
                if callsign.startswith(prefix):
                    is_military = True
                    mil_type = f"Callsign:{prefix}"
                    break

            # Check ICAO prefix
            if not is_military:
                for prefix, nation in MILITARY_ICAO_PREFIXES.items():
                    if icao24.startswith(prefix):
                        is_military = True
                        mil_type = nation
                        break

            if not is_military:
                continue

            altitude = sv[7] or sv[13] or 0
            velocity = sv[9] or 0
            heading = sv[10] or 0
            on_ground = sv[8] or False

            signals.append(make_signal(
                source="opensky", stype="military_flight",
                title=f"Military Aircraft {callsign or icao24} [{mil_type}]",
                summary=f"Alt:{altitude:.0f}m Speed:{velocity:.0f}m/s Heading:{heading:.0f}°",
                lat=lat, lon=lon,
                severity="high" if not on_ground else "info",
                extra={"icao24": icao24, "callsign": callsign, "on_ground": on_ground},
            ))

        log.info(f"OpenSky: {len(signals)} military aircraft")
    except Exception as e:
        log.error(f"OpenSky failed: {e}")
    return signals


# ═══════════════════════════════════════════════════════════════
# 6. Polymarket ── Geopolitical Prediction Markets
# ═══════════════════════════════════════════════════════════════

GEO_KEYWORDS = [
    "war", "conflict", "military", "attack", "invasion", "missile",
    "nuclear", "sanction", "election", "coup", "crisis", "iran",
    "russia", "china", "taiwan", "ukraine", "israel", "nato",
    "north korea", "pakistan", "india",
]

def collect_polymarket() -> list[dict]:
    log.info("Polymarket: Collecting prediction markets...")
    url = "https://clob.polymarket.com/markets?active=true&closed=false&limit=100"
    signals = []
    try:
        data = _get(url, timeout=20).json()
        markets = data if isinstance(data, list) else data.get("data", [])
        for m in markets:
            q = (m.get("question") or "").lower()
            if not any(kw in q for kw in GEO_KEYWORDS):
                continue
            tokens = m.get("tokens", [])
            yes_price = next((float(t.get("price", 0)) for t in tokens if t.get("outcome", "").lower() == "yes"), 0)
            severity = "critical" if yes_price > 0.7 else "high" if yes_price > 0.4 else "medium"
            signals.append(make_signal(
                source="polymarket", stype="prediction_market",
                title=m.get("question", "Unknown Market"),
                summary=f"Yes Probability: {yes_price*100:.1f}%",
                severity=severity,
                url=f"https://polymarket.com/event/{m.get('condition_id','')}"
            ))
        log.info(f"Polymarket: {len(signals)} geopolitical markets")
    except Exception as e:
        log.error(f"Polymarket failed: {e}")
    return signals


# ═══════════════════════════════════════════════════════════════
# 7. FAA NASSTATUS ── Flight Delays / Ground Stops
# ═══════════════════════════════════════════════════════════════

def collect_faa() -> list[dict]:
    log.info("FAA: Collecting flight delays/stops...")
    url = "https://nasstatus.faa.gov/api/airport-status-information"
    signals = []
    try:
        data = _get(url, timeout=20).json()
        airports = data if isinstance(data, list) else (data.get("airport_status_information") or [])
        for ap in airports:
            name = ap.get("Name") or ap.get("ARPT") or ""
            status = ap.get("status") or ""
            delay = ap.get("Delay") or ap.get("GroundDelay") or ""
            if not delay and status.lower() in ("normal", ""):
                continue

            lat = ap.get("lat")
            lon = ap.get("lon")
            severity = "high" if "ground stop" in status.lower() else "medium" if delay else "low"

            signals.append(make_signal(
                source="faa", stype="flight_delay",
                title=f"FAA: {name} - {status or delay}",
                summary=str(ap),
                lat=float(lat) if lat else None,
                lon=float(lon) if lon else None,
                country="USA",
                severity=severity,
            ))
        log.info(f"FAA: {len(signals)} delays/stops")
    except Exception as e:
        log.warning(f"FAA failed: {e}")
    return signals


# ═══════════════════════════════════════════════════════════════
# 8. NOAA/NWS ── Weather Alerts
# ═══════════════════════════════════════════════════════════════

def collect_noaa_alerts() -> list[dict]:
    log.info("NOAA: Collecting weather alerts...")
    # US Weather Alerts (NWS)
    url = "https://api.weather.gov/alerts/active?status=actual&message_type=alert&urgency=Immediate,Expected"
    signals = []
    try:
        data = _get(url, timeout=20, headers={"Accept": "application/json"}).json()
        for f in data.get("features", [])[:50]:  # Limit 50 items
            p = f["properties"]
            event = p.get("event", "")
            headline = p.get("headline", "")
            severity_map = {"Extreme": "critical", "Severe": "high", "Moderate": "medium", "Minor": "low"}
            severity = severity_map.get(p.get("severity", ""), "info")

            # Get coordinates (centroid)
            lat, lon = None, None
            geo = f.get("geometry")
            if geo and geo.get("type") == "Point":
                coords = geo["coordinates"]
                lon, lat = coords[0], coords[1]

            signals.append(make_signal(
                source="noaa", stype="weather_alert",
                title=f"Weather Alert: {event}",
                summary=headline,
                lat=lat, lon=lon,
                country="USA",
                severity=severity,
                url=p.get("@id", ""),
            ))
        log.info(f"NOAA: {len(signals)} weather alerts")
    except Exception as e:
        log.warning(f"NOAA failed: {e}")
    return signals


# ═══════════════════════════════════════════════════════════════
# 9. Internet Outages ── IODA / NetBlocks (RSS/API)
# ═══════════════════════════════════════════════════════════════

def collect_internet_outages() -> list[dict]:
    log.info("Internet Outages: Collecting...")
    signals = []

    # NetBlocks RSS
    netblocks_rss = "https://netblocks.org/feed"
    try:
        feed = feedparser.parse(netblocks_rss)
        for entry in feed.entries[:20]:
            title = entry.get("title", "")
            summary = entry.get("summary", "")
            published = entry.get("published", "")

            # Extract country information
            country = ""
            country_match = re.search(r'in ([A-Z][a-z]+(?:\s[A-Z][a-z]+)?)', title)
            if country_match:
                country = country_match.group(1)

            severity = "critical" if "shutdown" in title.lower() else "high" if "disruption" in title.lower() else "medium"
            signals.append(make_signal(
                source="netblocks", stype="internet_outage",
                title=f"🌐 {title}",
                summary=summary,
                country=country,
                severity=severity,
                url=entry.get("link", ""),
            ))
        log.info(f"Internet Outages: {len(signals)} items")
    except Exception as e:
        log.warning(f"NetBlocks failed: {e}")

    return signals


# ═══════════════════════════════════════════════════════════════
# 10. ACLED ── Protests/Conflicts (Requires free API Key)
# ═══════════════════════════════════════════════════════════════

def collect_acled() -> list[dict]:
    if not ACLED_KEY:
        log.info("ACLED: Key not set, skipping (Register free at acleddata.com)")
        return []

    log.info("ACLED: Collecting protests/conflicts...")
    # ACLED provides event types like protests, riots, battles, etc.
    from datetime import timedelta
    yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    url = "https://api.acleddata.com/acled/read"
    signals = []
    try:
        resp = _get(url, params={
            "key": ACLED_KEY,
            "event_date": f"{yesterday}|{today}",
            "event_date_where": "BETWEEN",
            "limit": 500,
            "fields": "event_date|event_type|sub_event_type|country|admin1|location|latitude|longitude|fatalities|notes|source",
        }, timeout=30)
        data = resp.json()

        for ev in data.get("data", []):
            event_type = ev.get("event_type", "")
            stype = "protest" if "protest" in event_type.lower() else \
                    "conflict" if "battle" in event_type.lower() else \
                    "civil_unrest"
            fatalities = int(ev.get("fatalities", 0) or 0)
            severity = "critical" if fatalities > 50 else "high" if fatalities > 10 else \
                       "medium" if fatalities > 0 else "low"
            country = ev.get("country", "")
            location = ev.get("location", "")
            signals.append(make_signal(
                source="acled", stype=stype,
                title=f"{event_type}: {location}, {country}",
                summary=ev.get("notes", "")[:200],
                lat=float(ev.get("latitude", 0) or 0) or None,
                lon=float(ev.get("longitude", 0) or 0) or None,
                country=country,
                severity=severity,
            ))

        log.info(f"ACLED: {len(signals)} events")
    except Exception as e:
        log.error(f"ACLED failed: {e}")
    return signals


# ═══════════════════════════════════════════════════════════════
# 11. RSS News Collection (Selection of 186 data sources)
# ═══════════════════════════════════════════════════════════════

RSS_FEEDS = {
    # ─── Global Agencies ───
    "AP News":          "https://feeds.apnews.com/ApNewsWorldNews",
    "Reuters World":    "https://feeds.reuters.com/reuters/worldnews",
    "BBC World":        "https://feeds.bbci.co.uk/news/world/rss.xml",
    "Al Jazeera":       "https://www.aljazeera.com/xml/rss/all.xml",
    "AFP":              "https://www.afp.com/en/rss",

    # ─── Security/Defense ───
    "Breaking Defense": "https://breakingdefense.com/feed/",
    "Defense News":     "https://www.defensenews.com/arc/outboundfeeds/rss/",
    "Defense One":      "https://www.defenseone.com/rss/all/",
    "The War Zone":     "https://www.thedrive.com/the-war-zone/rss",
    "Military Times":   "https://www.militarytimes.com/arc/outboundfeeds/rss/",
    "USNI News":        "https://news.usni.org/feed",
    "Janes":            "https://www.janes.com/feeds/news",
    "Task & Purpose":   "https://taskandpurpose.com/feed/",
    "Oryx OSINT":       "https://www.oryxspioenkop.com/feeds/posts/default",
    "Bellingcat":       "https://www.bellingcat.com/feed/",

    # ─── Geopolitics/Think Tanks ───
    "Foreign Affairs":  "https://www.foreignaffairs.com/rss.xml",
    "Foreign Policy":   "https://foreignpolicy.com/feed/",
    "Atlantic Council": "https://www.atlanticcouncil.org/feed/",
    "War on the Rocks": "https://warontherocks.com/feed/",
    "Brookings":        "https://www.brookings.edu/feed/",
    "RAND":             "https://www.rand.org/feed.xml",
    "CSIS":             "https://www.csis.org/analysis/rss.xml",
    "RUSI":             "https://rusi.org/feed",
    "Stimson Center":   "https://www.stimson.org/feed/",
    "Carnegie":         "https://carnegieendowment.org/rss/carnegieMain.xml",
    "Chatham House":    "https://www.chathamhouse.org/rss.xml",
    "Wilson Center":    "https://www.wilsoncenter.org/rss.xml",
    "Jamestown":        "https://jamestown.org/feed/",
    "The Diplomat":     "https://thediplomat.com/feed/",
    "Kyiv Independent": "https://kyivindependent.com/rss/",
    "Meduza":           "https://meduza.io/rss/all",
    "Responsible Statecraft": "https://responsiblestatecraft.org/feed/",

    # ─── Nuclear/Weapons/Non-proliferation ───
    "Arms Control Assn":     "https://www.armscontrol.org/rss/news.xml",
    "Bulletin Atomic Sci":   "https://thebulletin.org/feed/",
    "NTI":                   "https://www.nti.org/feed/",
    "Krebs Security":        "https://krebsonsecurity.com/feed/",
    "Ransomware.live":       "https://ransomware.live/rss.xml",

    # ─── Middle East ───
    "Al Arabiya":       "https://english.alarabiya.net/rss.xml",
    "BBC Middle East":  "https://feeds.bbci.co.uk/news/world/middle_east/rss.xml",
    "Haaretz":          "https://www.haaretz.com/cmlink/1.628752",
    "Iran International": "https://www.iranintl.com/en/rss",
    "Middle East Institute": "https://www.mei.edu/rss.xml",
    "Iran Watch":       "https://www.iranwatch.org/feed",

    # ─── Asia-Pacific ───
    "South China MP":   "https://www.scmp.com/rss/91/feed",
    "Nikkei Asia":      "https://asia.nikkei.com/rss/feed/nar",
    "The Hindu":        "https://www.thehindu.com/feeder/default.rss",
    "Japan Today":      "https://japantoday.com/feed",
    "Bangkok Post":     "https://www.bangkokpost.com/rss/data/topstories.xml",
    "VnExpress":        "https://vnexpress.net/rss/tin-moi-nhat.rss",
    "India News Network": "https://www.indianewsnetwork.com/feed/",
    "Lowy Institute":   "https://www.lowyinstitute.org/the-interpreter/feed",
    "Tuoi Tre News":    "https://tuoitrenews.vn/rss/ttnenglish.rss",

    # ─── Europe/Russia ───
    "BBC Russian":      "https://feeds.bbci.co.uk/russian/rss.xml",
    "DW News":          "https://rss.dw.com/rdf/rss-en-all",
    "EuroNews":         "https://www.euronews.com/rss",
    "Novaya Gazeta EU": "https://novayagazeta.eu/rss",
    "Moscow Times":     "https://www.themoscowtimes.com/rss/news",
    "Le Monde":         "https://www.lemonde.fr/rss/en_continu.xml",
    "El Pais":          "https://feeds.elpais.com/mrss-s/pages/ep/site/english.elpais.com/portada",
    "Der Spiegel":      "https://www.spiegel.de/international/index.rss",
    "Guardian World":   "https://www.theguardian.com/world/rss",

    # ─── Africa ───
    "BBC Africa":       "https://feeds.bbci.co.uk/news/world/africa/rss.xml",
    "Africa News":      "https://www.africanews.com/feed",
    "Daily Trust":      "https://dailytrust.com/feed",
    "Sahel Crisis":     "https://www.sahelresearch.org/feed",
    "Premium Times":    "https://www.premiumtimesng.com/feed",
    "Vanguard Nigeria": "https://www.vanguardngr.com/feed/",

    # ─── Latin America ───
    "InSight Crime":    "https://insightcrime.org/feed/",
    "Reuters LatAm":    "https://feeds.reuters.com/reuters/latinnews",
    "La Silla Vacia":   "https://lasillavacia.com/feed",
    "Mexico Security":  "https://www.mexicosecuritymonitor.com/feed/",

    # ─── Government/Official ───
    "State Dept":       "https://www.state.gov/rss-feeds/",
    "Pentagon":         "https://www.defense.gov/DesktopModules/ArticleCS/RSS.ashx?max=10&ContentType=1&Site=945&isdlg=0&Group=0&Category=0",
    "White House":      "https://www.whitehouse.gov/briefing-room/feed/",
    "UN News":          "https://news.un.org/feed/subscribe/en/news/all/rss.xml",
    "IAEA":             "https://www.iaea.org/feeds/topnews.xml",
    "UNHCR":            "https://www.unhcr.org/rss/news.xml",
    "WHO":              "https://www.who.int/feeds/entity/mediacentre/news/en/rss.xml",
    "NASA":             "https://www.nasa.gov/rss/dyn/breaking_news.rss",

    # ─── Energy/Economy ───
    "Oil & Gas":        "https://www.rigzone.com/news/rss/rigzone_latest.aspx",
    "Reuters Business": "https://feeds.reuters.com/reuters/businessNews",
    "Financial Times":  "https://www.ft.com/rss/home/asia",
    "MarketWatch":      "https://feeds.marketwatch.com/marketwatch/topstories/",
    "Bloomberg":        "https://feeds.bloomberg.com/markets/news.rss",

    # ─── AI/Tech ───
    "Ars Technica":     "https://feeds.arstechnica.com/arstechnica/index",
    "The Verge":        "https://www.theverge.com/rss/index.xml",
    "MIT Tech Review":  "https://www.technologyreview.com/feed/",
    "Hacker News":      "https://hnrss.org/frontpage",
    "VentureBeat AI":   "https://venturebeat.com/category/ai/feed/",

    # ─── Climate/Disaster ───
    "RELIEFWEB":        "https://reliefweb.int/disasters/rss.xml",
    "FEMA":             "https://www.fema.gov/api/open/v2/disasterDeclarations.json",  # JSON API
    "Climate Signal":   "https://www.climatesignals.org/feed",
}

SECURITY_KEYWORDS = [
    "attack", "war", "conflict", "missile", "bomb", "explosion", "military",
    "troops", "invasion", "crisis", "nuclear", "sanction", "protest", "riot",
    "coup", "earthquake", "flood", "wildfire", "hurricane", "tornado", "volcano",
    "cyber", "hack", "shutdown", "arrest", "sanctions", "threat", "alert",
    "bomb", "attack", "war", "conflict", "earthquake", "flood",
]

def rss_severity(title: str, summary: str) -> str:
    text = (title + " " + summary).lower()
    critical_kw = ["war declared", "nuclear", "invasion begins", "massive attack", "coup"]
    high_kw = ["attack", "bomb", "explosion", "killed", "missile", "military", "troops", "crisis"]
    medium_kw = ["conflict", "protest", "riot", "earthquake", "flood", "wildfire"]
    if any(k in text for k in critical_kw):
        return "critical"
    if any(k in text for k in high_kw):
        return "high"
    if any(k in text for k in medium_kw):
        return "medium"
    return "info"

def collect_rss() -> list[dict]:
    log.info(f"RSS: Collecting {len(RSS_FEEDS)} data sources...")
    signals = []
    for name, url in RSS_FEEDS.items():
        if not url.endswith((".xml", ".rss", ".rdf", "rss.xml", "feed", "feed/")):
            if "json" in url.lower():
                continue  # Handle JSON API separately
        try:
            feed = feedparser.parse(url)
            count = 0
            for entry in feed.entries[:10]:  # Max 10 items per source
                title = entry.get("title", "")
                summary = entry.get("summary", entry.get("description", ""))
                link = entry.get("link", "")

                # Only include relevant content or important sources
                text = (title + " " + summary).lower()
                is_relevant = any(k in text for k in SECURITY_KEYWORDS)
                is_important_source = name in {
                    "Breaking Defense", "Defense News", "USNI News", "The War Zone",
                    "Bellingcat", "Kyiv Independent", "Oryx OSINT", "NTI", "IAEA",
                    "State Dept", "Pentagon", "UN News", "Ransomware.live",
                }
                if not (is_relevant or is_important_source):
                    continue

                severity = rss_severity(title, summary)
                signals.append(make_signal(
                    source="rss", stype="news",
                    title=f"[{name}] {title}",
                    summary=summary[:300],
                    severity=severity,
                    url=link,
                    extra={"feed_name": name},
                ))
                count += 1
            if count > 0:
                pass  # log.debug(f"  {name}: {count} items")
        except Exception as e:
            log.debug(f"RSS {name} failed: {e}")

    log.info(f"RSS: {len(signals)} news items")
    return signals


# ═══════════════════════════════════════════════════════════════
# 12. USGS Volcano Notifications (Volcano)
# ═══════════════════════════════════════════════════════════════

def collect_volcanoes() -> list[dict]:
    log.info("Volcano: Collecting USGS notifications...")
    # USGS Volcano Notifications RSS
    url = "https://volcanoes.usgs.gov/vhp/notifications.xml"
    signals = []
    try:
        feed = feedparser.parse(url)
        for entry in feed.entries[:20]:
            title = entry.get("title", "")
            summary = entry.get("summary", "")
            text = (title + summary).lower()
            severity = "critical" if "red" in text or "eruption" in text else \
                       "high" if "orange" in text else \
                       "medium" if "yellow" in text else "info"
            signals.append(make_signal(
                source="usgs_volcano", stype="volcanic_activity",
                title=f"🌋 {title}",
                summary=summary[:300],
                severity=severity,
                url=entry.get("link", ""),
            ))
        log.info(f"Volcano: {len(signals)} notifications")
    except Exception as e:
        log.warning(f"Volcano notifications failed: {e}")
    return signals


# ═══════════════════════════════════════════════════════════════
# main
# ═══════════════════════════════════════════════════════════════

COLLECTORS = [
    ("GDELT",           collect_gdelt),
    ("USGS Quake",      collect_usgs),
    ("NASA EONET",      collect_eonet),
    ("NASA FIRMS",      collect_firms),
    ("OpenSky Military", collect_opensky),
    ("Polymarket",      collect_polymarket),
    ("FAA Delay",       collect_faa),
    ("NOAA Weather",    collect_noaa_alerts),
    ("Internet Outage", collect_internet_outages),
    ("ACLED Protest",   collect_acled),
    ("Volcano",         collect_volcanoes),
    ("RSS News",        collect_rss),
]


def main():
    log.info("=" * 60)
    log.info(f"WorldMirror Data Collector v1.0")
    log.info(f"Output File: {today_filename()}")
    log.info("=" * 60)

    total = 0
    stats = {}

    for name, func in COLLECTORS:
        try:
            t0 = time.time()
            signals = func()
            elapsed = time.time() - t0
            append_signals(signals)
            stats[name] = len(signals)
            total += len(signals)
            log.info(f"  ✅ {name}: {len(signals)} items ({elapsed:.1f}s)")
        except Exception as e:
            log.error(f"  ❌ {name}: Exception - {e}")
            stats[name] = 0

    log.info("=" * 60)
    log.info(f"Collection Complete: {total} total signals")
    log.info(f"File: {today_filename()}")
    for name, count in stats.items():
        log.info(f"  {name:20s}: {count:5d}")
    log.info("=" * 60)


if __name__ == "__main__":
    main()
