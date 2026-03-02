"""
app.py - WorldMirror Global Situational Awareness Dashboard v1.0
============================================================
Flask visualization server, supporting all static layers + real-time signal streams

Run:
  pip install flask
  python app.py
  Visit: http://localhost:5000

Data Dependencies:
  ./data/signals_YYYY-MM-DD.ndjson  (Collected by collector.py)
  ./data/layers/*.json              (Downloaded by layers_downloader.py)
============================================================
"""

from flask import Flask, jsonify, request, Response
import json, os, glob
from datetime import datetime, timezone
from pathlib import Path

app = Flask(__name__)

# Use relative path of the script directory to ensure data is found regardless of execution path
_BASE_DIR  = os.path.dirname(os.path.abspath(__file__))
DATA_DIR   = os.path.join(_BASE_DIR, "data")
LAYERS_DIR = os.path.join(_BASE_DIR, "data", "layers")


# - Utility Functions ---------------------------

def list_signal_dates():
    files = sorted(glob.glob(os.path.join(DATA_DIR, "signals_*.ndjson")), reverse=True)
    dates = []
    for f in files:
        base = os.path.basename(f)
        date = base.replace("signals_", "").replace(".ndjson", "")
        dates.append(date)
    return dates


def load_signals(date=None, sources=None, severities=None, limit=2000):
    if not date:
        dates = list_signal_dates()
        if not dates:
            return []
        date = dates[0]
    path = os.path.join(DATA_DIR, f"signals_{date}.ndjson")
    if not os.path.exists(path):
        return []
    signals = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                s = json.loads(line)
                if sources and s.get("source") not in sources:
                    continue
                if severities and s.get("severity") not in severities:
                    continue
                signals.append(s)
            except:
                continue
    return signals[-limit:]


def load_layer(name):
    path = os.path.join(LAYERS_DIR, f"{name}.json")
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        return json.load(f)


# - API Routes -----------------------------─

@app.route("/api/signals")
def api_signals():
    date = request.args.get("date")
    sources = request.args.getlist("source") or None
    severities = request.args.getlist("severity") or None
    limit = int(request.args.get("limit", 2000))
    signals = load_signals(date, sources, severities, limit)
    return jsonify(signals)


@app.route("/api/dates")
def api_dates():
    return jsonify(list_signal_dates())


@app.route("/api/stats")
def api_stats():
    date = request.args.get("date")
    signals = load_signals(date, limit=99999)
    by_source, by_severity, by_type = {}, {}, {}
    for s in signals:
        src = s.get("source","?"); by_source[src] = by_source.get(src,0)+1
        sev = s.get("severity","?"); by_severity[sev] = by_severity.get(sev,0)+1
        t = s.get("type","?"); by_type[t] = by_type.get(t,0)+1
    return jsonify({"total":len(signals),"by_source":by_source,"by_severity":by_severity,"by_type":by_type})


@app.route("/api/layer/<layer_name>")
def api_layer(layer_name):
    # Security: Only alphanumeric underscores are allowed
    if not layer_name.replace("_","").isalnum():
        return jsonify({"error":"invalid"}), 400
    data = load_layer(layer_name)
    return jsonify(data)


@app.route("/api/layers")
def api_layers():
    """Return the list of downloaded layers"""
    if not os.path.exists(LAYERS_DIR):
        return jsonify([])
    files = os.listdir(LAYERS_DIR)
    return jsonify([f.replace(".json","") for f in files if f.endswith(".json")])


# - Main Page ---------------------------─


@app.route("/api/debug")
def api_debug():
    """Diagnostic routing: Display data directory status"""
    info = {
        "script_dir": os.path.dirname(os.path.abspath(__file__)),
        "data_dir": DATA_DIR,
        "layers_dir": LAYERS_DIR,
        "data_dir_exists": os.path.exists(DATA_DIR),
        "layers_dir_exists": os.path.exists(LAYERS_DIR),
        "layer_files": [],
        "signal_files": [],
    }
    if os.path.exists(LAYERS_DIR):
        info["layer_files"] = sorted(os.listdir(LAYERS_DIR))
    if os.path.exists(DATA_DIR):
        info["signal_files"] = [f for f in os.listdir(DATA_DIR) if f.endswith(".ndjson")]
    return jsonify(info)


@app.route("/test")
def test_page():
    """Minimize the map test page"""
    return Response(TEST_HTML, mimetype="text/html")

TEST_HTML = """<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>Layer Test</title>
<style>
body{margin:0;background:#111;color:#0f0;font-family:monospace;padding:10px}
#map{height:350px;margin-bottom:10px;border:1px solid #0f0}
#log{height:280px;overflow-y:auto;white-space:pre;font-size:12px;border:1px solid #333;padding:8px}
button{background:#0f0;color:#000;border:none;padding:6px 12px;margin:4px;cursor:pointer;font-family:monospace}
</style>
</head>
<body>
<div id="map"></div>
<div id="log">Starting tests...\n</div>
<button onclick="runTest()">▶ Run the test</button>
<button onclick="loadLeafletAndRun()">⟳ Reload Leaflet</button>

<script>
const log = s => {
  const el = document.getElementById('log');
  el.textContent += s + '\n';
  el.scrollTop = el.scrollHeight;
};

function loadScript(src) {
  return new Promise((resolve, reject) => {
    const s = document.createElement('script');
    s.src = src;
    s.onload = resolve;
    s.onerror = () => reject(new Error('Failed: ' + src));
    document.head.appendChild(s);
  });
}

function loadCSS(href) {
  const l = document.createElement('link');
  l.rel = 'stylesheet';
  l.href = href;
  document.head.appendChild(l);
}

async function loadLeafletAndRun() {
  log('\n--- Loading Leaflet ---');
  
  // Try CDNs in order
  const cdns = [
    'https://cdn.jsdelivr.net/npm/leaflet@1.9.4/dist/leaflet.min.js',
    'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js',
    'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.js',
  ];
  
  for (const cdn of cdns) {
    try {
      log('Trying: ' + cdn.split('/')[2]);
      await loadScript(cdn);
      if (typeof L !== 'undefined') {
        log('✅ Leaflet loaded from: ' + cdn.split('/')[2]);
        loadCSS(cdn.replace('.js','.css').replace('min.js','min.css'));
        
        // Load MarkerCluster
        const mcCdns = [
          'https://cdn.jsdelivr.net/npm/leaflet.markercluster@1.5.3/dist/leaflet.markercluster.js',
          'https://unpkg.com/leaflet.markercluster@1.5.3/dist/leaflet.markercluster.js',
        ];
        for (const mc of mcCdns) {
          try {
            await loadScript(mc);
            if (typeof L.markerClusterGroup === 'function') {
              log('✅ MarkerCluster loaded');
              break;
            }
          } catch(e) {}
        }
        if (typeof L.markerClusterGroup !== 'function') {
          log('⚠️ MarkerCluster not available (will use LayerGroup)');
        }
        await runTest();
        return;
      }
    } catch(e) {
      log('❌ Failed: ' + e.message);
    }
  }
  log('\n❌ ALL CDNs FAILED');
  log('Please check your network connection or firewall settings');
  log('Need to be able to access: cdn.jsdelivr.net or unpkg.com or cdnjs.cloudflare.com');
}

async function runTest() {
  log('\n--- Map Test ---');
  log('Leaflet: ' + (typeof L !== 'undefined' ? '✅ v' + L.version : '❌ NOT LOADED'));
  if (typeof L === 'undefined') {
    log('Unable to continue testing, please click "Reload Leaflet" first');
    return;
  }
  
  // Create map
  try {
    const mapEl = document.getElementById('map');
    if (mapEl._leaflet_id) {
      // Already has a map, remove it
      mapEl._leaflet_id = null;
      mapEl.innerHTML = '';
    }
    const map = L.map('map').setView([20, 10], 2);
    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png',
      {subdomains:'abcd',attribution:'CARTO'}).addTo(map);
    log('Map: ✅ created');
    
    // Add test marker
    L.circleMarker([48.85, 2.35], {radius:12, fillColor:'#ff0000', color:'#fff', weight:2, fillOpacity:1}).addTo(map).bindPopup('Paris test');
    L.circleMarker([35.68, 139.69], {radius:12, fillColor:'#ffff00', color:'#fff', weight:2, fillOpacity:1}).addTo(map).bindPopup('Tokyo test');
    L.circleMarker([40.71, -74.0], {radius:12, fillColor:'#00ff00', color:'#fff', weight:2, fillOpacity:1}).addTo(map).bindPopup('NYC test');
    log('Manual markers: ✅ (red=Paris, yellow=Tokyo, green=NYC should be visible)');
    
    // Test API
    log('\n--- API Test ---');
    const layers = ['military_bases','nuclear_weapons','chokepoints','ports','spaceports'];
    for (const name of layers) {
      try {
        const r = await fetch('/api/layer/' + name);
        const data = await r.json();
        const withCoords = data.filter(d => d.lat && d.lon);
        log(name + ': HTTP ' + r.status + ' → ' + data.length + ' items, ' + withCoords.length + ' with coords');
        
        // Add to map
        const group = L.layerGroup().addTo(map);
        withCoords.forEach(d => {
          L.circleMarker([d.lat, d.lon], {
            radius: 6, fillColor: '#00ffff', color: '#00ffff', 
            weight: 1, fillOpacity: 0.8
          }).bindPopup(d.name || name).addTo(group);
        });
        log('  → Added ' + withCoords.length + ' markers to map ✅');
      } catch(e) {
        log(name + ': ❌ ' + e);
      }
    }
    log('\n✅ Test complete - check map above for cyan dots');
  } catch(e) {
    log('Map ERROR: ' + e);
  }
}

// Auto-run on load
window.onload = () => loadLeafletAndRun();
</script>
</body>
</html>"""



@app.route("/")
def index():
    return Response(HTML, mimetype="text/html")


# ══════════════════════════════════════════════════════════════════
# Front end HTML (single file, inline CSS+JS)
# ══════════════════════════════════════════════════════════════════

HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>WorldMirror Global Awareness System</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@400;600;800;900&family=Share+Tech+Mono&family=Rajdhani:wght@300;400;500;600&display=swap" rel="stylesheet">
<script>
// - Dynamic loading of map library (multi CDN rollback) ---------------
function _loadRes(tag, attrs) {
  return new Promise((res, rej) => {
    const el = document.createElement(tag);
    Object.assign(el, attrs);
    el.onload = res; el.onerror = rej;
    document.head.appendChild(el);
  });
}
const LEAFLET_CDNS = [
  'https://cdn.jsdelivr.net/npm/leaflet@1.9.4/dist',
  'https://unpkg.com/leaflet@1.9.4/dist',
  'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4',
];
const MC_CDNS = [
  'https://cdn.jsdelivr.net/npm/leaflet.markercluster@1.5.3/dist',
  'https://unpkg.com/leaflet.markercluster@1.5.3/dist',
  'https://cdnjs.cloudflare.com/ajax/libs/leaflet.markercluster/1.5.3',
];
window._mapsReady = (async () => {
  // Load Leaflet
  for (const base of LEAFLET_CDNS) {
    try {
      await _loadRes('link', {rel:'stylesheet', href: base+'/leaflet.min.css'});
      await _loadRes('script', {src: base+'/leaflet.min.js'});
      if (typeof L !== 'undefined') break;
    } catch(e) {}
  }
  if (typeof L === 'undefined') throw new Error('Leaflet loading failed, please check the network');
  // Load MarkerCluster
  for (const base of MC_CDNS) {
    try {
      await _loadRes('link', {rel:'stylesheet', href: base+'/MarkerCluster.css'});
      await _loadRes('link', {rel:'stylesheet', href: base+'/MarkerCluster.Default.css'});
      await _loadRes('script', {src: base+'/leaflet.markercluster.js'});
      if (typeof L.markerClusterGroup === 'function') break;
    } catch(e) {}
  }
})();
</script>
<style>
/* ═══════════════════ RESET & BASE ═══════════════════ */
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

:root {
  --bg:        #020b10;
  --bg2:       #041520;
  --bg3:       #071e2c;
  --panel:     #061828;
  --border:    #0e3a55;
  --accent:    #00d4ff;
  --accent2:   #00ff88;
  --dim:       #1a4a63;
  --text:      #b8d8e8;
  --text-dim:  #4a7a98;
  --critical:  #ff2244;
  --high:      #ff7700;
  --medium:    #ffcc00;
  --low:       #0088ff;
  --info:      #00cc66;
  --font-head: 'Orbitron', monospace;
  --font-mono: 'Share Tech Mono', monospace;
  --font-body: 'Rajdhani', sans-serif;
}

html, body { height: 100%; overflow: hidden; background: var(--bg); color: var(--text); font-family: var(--font-body); }

/* ═══════════════════ SCANLINE OVERLAY ═══════════════════ */
body::before {
  content:''; position:fixed; inset:0; pointer-events:none; z-index:9999;
  background: repeating-linear-gradient(0deg, transparent, transparent 2px, rgba(0,0,0,.08) 2px, rgba(0,0,0,.08) 4px);
}

/* ═══════════════════ LAYOUT ═══════════════════ */
#app { display:flex; flex-direction:column; height:100vh; }

/* - Topbar - */
#topbar {
  flex-shrink:0; height:52px;
  background: linear-gradient(90deg, var(--bg2) 0%, #041c2e 50%, var(--bg2) 100%);
  border-bottom: 1px solid var(--border);
  display:flex; align-items:center; gap:16px; padding:0 16px;
  position:relative; overflow:hidden;
}
#topbar::after {
  content:''; position:absolute; bottom:0; left:0; right:0; height:1px;
  background: linear-gradient(90deg, transparent, var(--accent), transparent);
  opacity:.6;
}

.logo {
  font-family:var(--font-head); font-size:14px; font-weight:900;
  color:var(--accent); letter-spacing:3px; white-space:nowrap;
  text-shadow: 0 0 20px rgba(0,212,255,.5);
}
.logo span { color: var(--text-dim); font-weight:400; font-size:11px; }

.topbar-divider { width:1px; height:28px; background:var(--border); flex-shrink:0; }

#clock {
  font-family:var(--font-mono); font-size:13px; color:var(--accent2);
  letter-spacing:1px; white-space:nowrap;
}

.stat-pill {
  display:flex; align-items:center; gap:6px;
  background:rgba(0,212,255,.06); border:1px solid rgba(0,212,255,.15);
  border-radius:3px; padding:3px 10px;
  font-family:var(--font-mono); font-size:11px;
}
.stat-pill .label { color:var(--text-dim); }
.stat-pill .val { color:var(--accent); font-weight:bold; }
.stat-pill.crit .val { color:var(--critical); }
.stat-pill.high .val { color:var(--high); }
.stat-pill.med .val { color:var(--medium); }

.topbar-right { margin-left:auto; display:flex; align-items:center; gap:10px; }

.btn-auto {
  font-family:var(--font-mono); font-size:10px; letter-spacing:1px;
  background:transparent; border:1px solid var(--border); color:var(--text-dim);
  padding:4px 12px; border-radius:2px; cursor:pointer; transition:all .2s;
}
.btn-auto.on { border-color:var(--accent2); color:var(--accent2); box-shadow: 0 0 8px rgba(0,255,136,.3); }
.btn-auto:hover { border-color:var(--accent); color:var(--accent); }

/* - Main body - */
#main { flex:1; display:flex; overflow:hidden; }

/* - Left panel - */
#sidebar {
  width:320px; flex-shrink:0;
  display:flex; flex-direction:column;
  background:var(--panel); border-right:1px solid var(--border);
  overflow:hidden;
}

/* - Layer panel (right) - */
#layer-panel {
  width:280px; flex-shrink:0;
  background:var(--panel); border-left:1px solid var(--border);
  display:flex; flex-direction:column; overflow:hidden;
}

/* - Map - */
#map { flex:1; }
#map .leaflet-container { background:#020b10; }

/* ═══════════════════ SIDEBAR ═══════════════════ */
.panel-header {
  padding:10px 12px 8px;
  border-bottom:1px solid var(--border);
  font-family:var(--font-head); font-size:10px; letter-spacing:2px;
  color:var(--text-dim); display:flex; align-items:center; justify-content:space-between;
}
.panel-header .count { color:var(--accent); font-size:12px; }

/* Filter bar */
#filter-bar {
  padding:8px 10px; border-bottom:1px solid var(--border);
  display:flex; flex-direction:column; gap:6px;
}

.filter-row { display:flex; gap:4px; align-items:center; flex-wrap:wrap; }
.filter-label { font-family:var(--font-mono); font-size:9px; color:var(--text-dim); width:40px; flex-shrink:0; }

.chip {
  font-family:var(--font-mono); font-size:9px; letter-spacing:.5px;
  padding:2px 7px; border-radius:2px; cursor:pointer; user-select:none;
  border:1px solid var(--border); color:var(--text-dim); transition:all .15s;
}
.chip:hover { border-color:var(--accent); color:var(--accent); }
.chip.active { background:rgba(0,212,255,.12); border-color:var(--accent); color:var(--accent); }
.chip.sev-critical.active { background:rgba(255,34,68,.15); border-color:var(--critical); color:var(--critical); }
.chip.sev-high.active { background:rgba(255,119,0,.15); border-color:var(--high); color:var(--high); }
.chip.sev-medium.active { background:rgba(255,204,0,.15); border-color:var(--medium); color:var(--medium); }
.chip.sev-low.active { background:rgba(0,136,255,.15); border-color:var(--low); color:var(--low); }
.chip.sev-info.active { background:rgba(0,204,102,.15); border-color:var(--info); color:var(--info); }

.date-select {
  background:var(--bg3); border:1px solid var(--border); color:var(--text);
  font-family:var(--font-mono); font-size:10px; padding:3px 6px; border-radius:2px;
  cursor:pointer; width:100%;
}
.date-select:focus { outline:none; border-color:var(--accent); }

/* Signal feed */
#signal-feed { flex:1; overflow-y:auto; }
#signal-feed::-webkit-scrollbar { width:4px; }
#signal-feed::-webkit-scrollbar-track { background:var(--bg2); }
#signal-feed::-webkit-scrollbar-thumb { background:var(--dim); }

.signal-item {
  padding:8px 12px; border-bottom:1px solid rgba(14,58,85,.4);
  cursor:pointer; transition:background .1s; position:relative;
}
.signal-item::before {
  content:''; position:absolute; left:0; top:0; bottom:0; width:2px;
}
.signal-item.sev-critical::before { background:var(--critical); }
.signal-item.sev-high::before { background:var(--high); }
.signal-item.sev-medium::before { background:var(--medium); }
.signal-item.sev-low::before { background:var(--low); }
.signal-item.sev-info::before { background:var(--info); }
.signal-item:hover { background:rgba(0,212,255,.04); }
.signal-item.active { background:rgba(0,212,255,.08); }

.sig-title { font-size:12px; color:var(--text); line-height:1.4; margin-bottom:3px; }
.sig-meta { display:flex; gap:6px; align-items:center; flex-wrap:wrap; }
.sig-badge {
  font-family:var(--font-mono); font-size:8px; letter-spacing:.5px;
  padding:1px 5px; border-radius:1px; border:1px solid;
  color:var(--text-dim); border-color:var(--border);
}
.sig-badge.src { color:var(--accent); border-color:var(--dim); }
.sig-badge.sev-critical { color:var(--critical); border-color:rgba(255,34,68,.4); }
.sig-badge.sev-high { color:var(--high); border-color:rgba(255,119,0,.4); }
.sig-badge.sev-medium { color:var(--medium); border-color:rgba(255,204,0,.4); }
.sig-badge.sev-low { color:var(--low); border-color:rgba(0,136,255,.4); }
.sig-badge.sev-info { color:var(--info); border-color:rgba(0,204,102,.4); }
.sig-time { font-family:var(--font-mono); font-size:8px; color:var(--text-dim); }

/* ═══════════════════ LAYER PANEL ═══════════════════ */
.layer-panel-inner { flex:1; overflow-y:auto; padding:8px; }
.layer-panel-inner::-webkit-scrollbar { width:4px; }
.layer-panel-inner::-webkit-scrollbar-track { background:var(--bg2); }
.layer-panel-inner::-webkit-scrollbar-thumb { background:var(--dim); }

.layer-group { margin-bottom:12px; }
.layer-group-title {
  font-family:var(--font-head); font-size:8px; letter-spacing:2px;
  color:var(--text-dim); padding:4px 4px 6px; border-bottom:1px solid var(--border);
  margin-bottom:6px;
}

.layer-item {
  display:flex; align-items:center; gap:8px;
  padding:5px 6px; border-radius:2px; cursor:pointer;
  transition:background .15s; margin-bottom:2px;
}
.layer-item:hover { background:rgba(0,212,255,.06); }
.layer-item.active { background:rgba(0,212,255,.1); }

.layer-toggle {
  width:28px; height:14px; border-radius:7px; flex-shrink:0; position:relative;
  background:var(--bg3); border:1px solid var(--border); cursor:pointer;
  transition:all .2s;
}
.layer-toggle::after {
  content:''; position:absolute; top:1px; left:1px;
  width:10px; height:10px; border-radius:50%;
  background:var(--text-dim); transition:all .2s;
}
.layer-item.active .layer-toggle { background:rgba(0,212,255,.2); border-color:var(--accent); }
.layer-item.active .layer-toggle::after { left:15px; background:var(--accent); }

.layer-icon { width:16px; height:16px; font-size:12px; text-align:center; flex-shrink:0; }
.layer-name { font-size:11px; color:var(--text); flex:1; line-height:1.2; }
.layer-count { font-family:var(--font-mono); font-size:9px; color:var(--text-dim); }
.layer-status { width:6px; height:6px; border-radius:50%; flex-shrink:0; background:var(--dim); }
.layer-status.loaded { background:var(--info); }
.layer-status.loading { background:var(--medium); animation:pulse 1s infinite; }
.layer-status.error { background:var(--critical); }

/* ═══════════════════ DETAIL PANEL ═══════════════════ */
#detail-panel {
  position:fixed; right:296px; top:60px; width:300px;
  background:var(--panel); border:1px solid var(--accent);
  border-radius:2px; padding:0; z-index:1000; display:none;
  box-shadow: 0 0 30px rgba(0,212,255,.15);
}
#detail-panel.open { display:block; }
.detail-header {
  display:flex; align-items:center; justify-content:space-between;
  padding:10px 14px; border-bottom:1px solid var(--border);
  font-family:var(--font-head); font-size:9px; letter-spacing:2px; color:var(--accent);
}
.detail-close {
  background:none; border:none; color:var(--text-dim); cursor:pointer; font-size:14px;
  line-height:1; padding:0 2px;
}
.detail-close:hover { color:var(--critical); }
.detail-body { padding:12px 14px; display:flex; flex-direction:column; gap:8px; }
.detail-row { display:flex; gap:8px; }
.detail-key {
  font-family:var(--font-mono); font-size:9px; color:var(--text-dim);
  letter-spacing:1px; width:70px; flex-shrink:0; padding-top:1px;
}
.detail-val { font-size:12px; color:var(--text); line-height:1.4; flex:1; word-break:break-word; }
.detail-val.url a { color:var(--accent); text-decoration:none; font-size:11px; }
.detail-val.url a:hover { text-decoration:underline; }

/* ═══════════════════ LEGEND ═══════════════════ */
#legend {
  position:absolute; bottom:20px; left:328px; z-index:500;
  background:rgba(4,21,32,.9); border:1px solid var(--border);
  padding:8px 12px; border-radius:2px; backdrop-filter:blur(4px);
}
.legend-title { font-family:var(--font-head); font-size:8px; letter-spacing:2px; color:var(--text-dim); margin-bottom:6px; }
.legend-row { display:flex; align-items:center; gap:6px; margin-bottom:3px; }
.legend-dot { width:8px; height:8px; border-radius:50%; flex-shrink:0; }
.legend-label { font-family:var(--font-mono); font-size:9px; color:var(--text-dim); }

/* ═══════════════════ LOADING ═══════════════════ */
#loading-overlay {
  position:fixed; inset:0; background:var(--bg); z-index:10000;
  display:flex; flex-direction:column; align-items:center; justify-content:center; gap:20px;
  transition: opacity .5s;
}
#loading-overlay.hidden { opacity:0; pointer-events:none; }
.loading-logo { font-family:var(--font-head); font-size:24px; font-weight:900; color:var(--accent); letter-spacing:6px; text-shadow: 0 0 40px rgba(0,212,255,.6); }
.loading-sub { font-family:var(--font-mono); font-size:10px; color:var(--text-dim); letter-spacing:3px; }
.loading-bar-wrap { width:300px; height:2px; background:var(--bg3); border-radius:1px; overflow:hidden; }
.loading-bar { height:100%; background:linear-gradient(90deg, var(--accent), var(--accent2)); width:0%; transition:width .3s; }
.loading-status { font-family:var(--font-mono); font-size:9px; color:var(--text-dim); letter-spacing:1px; }

/* ═══════════════════ MAP CUSTOM STYLES ═══════════════════ */
.leaflet-popup-content-wrapper {
  background:rgba(4,21,32,.95) !important; border:1px solid var(--accent) !important;
  border-radius:2px !important; box-shadow: 0 0 20px rgba(0,212,255,.2) !important;
  color:var(--text) !important; font-family:var(--font-body) !important;
  backdrop-filter:blur(8px);
}
.leaflet-popup-tip { background:rgba(4,21,32,.95) !important; }
.leaflet-popup-content { margin:12px 14px !important; font-size:12px; line-height:1.5; }
.popup-title { font-weight:600; color:var(--accent); margin-bottom:4px; font-size:13px; }
.popup-meta { font-family:var(--font-mono); font-size:9px; color:var(--text-dim); margin-bottom:6px; }
.popup-summary { font-size:11px; color:var(--text); }
.popup-link { display:block; margin-top:6px; font-family:var(--font-mono); font-size:9px; color:var(--accent); text-decoration:none; }

/* Marker cluster override */
.marker-cluster { background:rgba(0,212,255,.15) !important; border:1px solid rgba(0,212,255,.4) !important; }
.marker-cluster div { background:rgba(0,212,255,.25) !important; color:var(--accent) !important; font-family:var(--font-mono) !important; font-size:11px !important; font-weight:bold; }

/* Pulse animation for critical markers */
@keyframes pulse { 0%,100%{opacity:1} 50%{opacity:.4} }
@keyframes ring-pulse { 0%{transform:scale(1);opacity:.8} 100%{transform:scale(2.5);opacity:0} }

.pulse-ring {
  position:absolute; border-radius:50%; border:2px solid var(--critical);
  animation: ring-pulse 1.5s infinite;
  pointer-events:none;
}

/* Scrollbar global */
::-webkit-scrollbar { width:4px; height:4px; }
::-webkit-scrollbar-track { background:var(--bg2); }
::-webkit-scrollbar-thumb { background:var(--dim); border-radius:2px; }

/* ═══════════════════ SEARCH BAR ═══════════════════ */
#search-input {
  width:100%; background:var(--bg3); border:1px solid var(--border);
  color:var(--text); font-family:var(--font-mono); font-size:10px;
  padding:5px 10px; border-radius:2px; outline:none;
}
#search-input:focus { border-color:var(--accent); }
#search-input::placeholder { color:var(--text-dim); }

/* No data message */
.no-data {
  padding:40px 20px; text-align:center;
  font-family:var(--font-mono); font-size:10px; color:var(--text-dim); letter-spacing:1px;
}
</style>
</head>
<body>

<div id="loading-overlay">
  <div class="loading-logo">WorldMirror</div>
  <div class="loading-sub">Global Awareness System</div>
  <div class="loading-bar-wrap"><div class="loading-bar" id="loading-bar"></div></div>
  <div class="loading-status" id="loading-status">Loading system modules...</div>
</div>

<div id="app">
  <!-- - Top - -->
  <div id="topbar">
    <div class="logo">WorldMirror<span> v1.0</span></div>
    <div class="topbar-divider"></div>
    <div id="clock">--:--:-- UTC</div>
    <div class="topbar-divider"></div>
    <div class="stat-pill"><span class="label">SIGNALS</span><span class="val" id="stat-total">0</span></div>
    <div class="stat-pill crit"><span class="label">CRIT</span><span class="val" id="stat-crit">0</span></div>
    <div class="stat-pill high"><span class="label">HIGH</span><span class="val" id="stat-high">0</span></div>
    <div class="stat-pill med"><span class="label">MED</span><span class="val" id="stat-med">0</span></div>
    <div class="topbar-right">
      <div class="stat-pill"><span class="label">MAP PTS</span><span class="val" id="stat-map">0</span></div>
      <button class="btn-auto" id="btn-auto" onclick="toggleAuto()">⟳ AUTO</button>
      <button class="btn-auto" onclick="showDiag()" title="Diagnostic Data Catalog">⚙ DIAG</button>
    </div>
  </div>

  <!-- - Main - -->
  <div id="main">

    <!-- - Left signal panel - -->
    <div id="sidebar">
      <div class="panel-header">
        <span>SIGNAL INTELLIGENCE FEED</span>
        <span class="count" id="feed-count">0</span>
      </div>

      <div id="filter-bar">
        <select class="date-select" id="date-select" onchange="applyFilters()">
          <option value="">-- Select date --</option>
        </select>
        <input id="search-input" type="text" placeholder="Search Keywords..." oninput="applyFilters()">
        <div class="filter-row">
          <span class="filter-label">Source</span>
          <div id="chips-source"></div>
        </div>
        <div class="filter-row">
          <span class="filter-label">Level</span>
          <div id="chips-sev">
            <span class="chip sev-critical active" data-sev="critical" onclick="toggleChip(this,'sev')">CRIT</span>
            <span class="chip sev-high active" data-sev="high" onclick="toggleChip(this,'sev')">HIGH</span>
            <span class="chip sev-medium active" data-sev="medium" onclick="toggleChip(this,'sev')">MED</span>
            <span class="chip sev-low active" data-sev="low" onclick="toggleChip(this,'sev')">LOW</span>
            <span class="chip sev-info active" data-sev="info" onclick="toggleChip(this,'sev')">INFO</span>
          </div>
        </div>
      </div>

      <div id="signal-feed"><div class="no-data">Loading signal data...</div></div>
    </div>

    <!-- - Map - -->
    <div id="map"></div>

    <!-- - Right layer panel - -->
    <div id="layer-panel">
      <div class="panel-header">
        <span>LAYER PANEL</span>
      </div>
      <div class="layer-panel-inner" id="layer-list">
        <!-- Dynamic generation -->
      </div>
    </div>

  </div><!-- /main -->
</div><!-- /app -->

<!-- Legend -->
<div id="legend">
  <div class="legend-title">SEVERITY SCALE</div>
  <div class="legend-row"><div class="legend-dot" style="background:var(--critical)"></div><span class="legend-label">CRITICAL</span></div>
  <div class="legend-row"><div class="legend-dot" style="background:var(--high)"></div><span class="legend-label">HIGH</span></div>
  <div class="legend-row"><div class="legend-dot" style="background:var(--medium)"></div><span class="legend-label">MEDIUM</span></div>
  <div class="legend-row"><div class="legend-dot" style="background:var(--low)"></div><span class="legend-label">LOW</span></div>
  <div class="legend-row"><div class="legend-dot" style="background:var(--info)"></div><span class="legend-label">INFO</span></div>
</div>

<!-- Details panel -->
<div id="detail-panel">
  <div class="detail-header">
    <span>SIGNAL DETAIL</span>
    <button class="detail-close" onclick="closeDetail()">✕</button>
  </div>
  <div class="detail-body" id="detail-body"></div>
</div>

<script>
// ══════════════════════════════════════════════════════════════
// WorldMirror FRONTEND v3.0
// ══════════════════════════════════════════════════════════════

// - Staus --------------------------─
const state = {
  signals: [],
  filtered: [],
  activeSevs: new Set(['critical','high','medium','low','info']),
  activeSrcs: new Set(),
  allSrcs: new Set(),
  date: '',
  autoRefresh: false,
  autoTimer: null,
  layers: {},        // name → { active, leafletLayer, data, status }
  map: null,
  signalCluster: null,
  selectedSignalId: null,
};

const SEV_COLOR = {
  critical: '#ff2244', high: '#ff7700', medium: '#ffcc00',
  low: '#0088ff', info: '#00cc66'
};

const SEV_RADIUS = { critical:9, high:7, medium:6, low:5, info:4 };

// - Layer Definition -------------------------
const LAYER_GROUPS = [
  {
    group: "🗺️ Real-time Signals",
    layers: [
      { key:'signal_conflict',  icon:'⚔️', name:'Conflict Events',   desc:'GDELT Armed Conflicts',     api:'signals', filter:{type:'conflict'} },
      { key:'signal_protest',   icon:'✊', name:'Protests',          desc:'Demonstrations/Unrest',      api:'signals', filter:{type:'protest'} },
      { key:'signal_earthquake',icon:'🌊', name:'Earthquakes',       desc:'USGS M2.5+',                 api:'signals', filter:{source:'usgs'} },
      { key:'signal_fire',      icon:'🔥', name:'Wildfire Hotspots', desc:'NASA FIRMS',                 api:'signals', filter:{source:'nasa_firms'} },
      { key:'signal_military',  icon:'✈️', name:'Military Flights',  desc:'OpenSky Real-time Mil-Air',  api:'signals', filter:{source:'opensky'} },
      { key:'signal_weather',   icon:'⛈️', name:'Weather Alerts',    desc:'NOAA Severe Weather',        api:'signals', filter:{source:'noaa'} },
      { key:'signal_outage',    icon:'📡', name:'Internet Outages',  desc:'NetBlocks/IODA',             api:'signals', filter:{type:'internet_outage'} },
      { key:'signal_volcano',   icon:'🌋', name:'Volcanic Activity', desc:'USGS Volcano Notifications', api:'signals', filter:{source:'usgs_volcano'} },
    ]
  },
  {
    group: "☢️ Nuclear & Strategic",
    layers: [
      { key:'nuclear_plants',   icon:'⚛️', name:'Nuclear Plants',    desc:'Global Power Plants (Active)', api:'layer', layerFile:'nuclear_plants',   renderer:'nuclear_plants' },
      { key:'nuclear_weapons',  icon:'💣', name:'Nuclear Facilities', desc:'Arsenals/Enrichment/Labs',  api:'layer', layerFile:'nuclear_weapons',  renderer:'nuclear_weapons' },
      { key:'gamma_irradiators',icon:'☢️', name:'Gamma Irradiators', desc:'Industrial Facilities (IAEA)', api:'layer', layerFile:'gamma_irradiators',renderer:'gamma_irradiators' },
    ]
  },
  {
    group: "🪖 Military & Space",
    layers: [
      { key:'military_bases',   icon:'🪖', name:'Military Bases',    desc:'US/NATO/CN/RU 150+',         api:'layer', layerFile:'military_bases',   renderer:'military_bases' },
      { key:'spaceports',       icon:'🚀', name:'Spaceports',        desc:'Global Launch Sites 30+',    api:'layer', layerFile:'spaceports',       renderer:'spaceports' },
    ]
  },
  {
    group: "🌊 Infrastructure",
    layers: [
      { key:'submarine_cables', icon:'🔗', name:'Subsea Cables',     desc:'Major Backbone Cables',      api:'layer', layerFile:'submarine_cables', renderer:'submarine_cables' },
      { key:'pipelines',        icon:'⛽', name:'Pipelines',         desc:'NordStream/TAPI/BTC etc.',   api:'layer', layerFile:'pipelines',        renderer:'pipelines' },
      { key:'chokepoints',      icon:'⚓', name:'Strategic Chokepoints', desc:'20 Maritime Chokepoints', api:'layer', layerFile:'chokepoints',      renderer:'chokepoints' },
      { key:'ports',            icon:'🚢', name:'Strategic Ports',   desc:'61 Critical Ports',          api:'layer', layerFile:'ports',            renderer:'ports' },
      { key:'trade_routes',     icon:'🗺️', name:'Trade Routes',      desc:'Main Shipping Lanes',        api:'layer', layerFile:'trade_routes',     renderer:'lines' },
    ]
  },
  {
    group: "🌍 Humanitarian & Conflict",
    layers: [
      { key:'ucdp_events',      icon:'📍', name:'UCDP Conflicts',    desc:'Uppsala Conflict Data',      api:'layer', layerFile:'ucdp_events',      renderer:'ucdp' },
      { key:'unhcr_flows',      icon:'🚶', name:'Refugee Flows',     desc:'UNHCR Displacement Data',    api:'layer', layerFile:'unhcr_flows',      renderer:'unhcr' },
    ]
  },
  {
    group: "🌐 Overlays",
    layers: [
      { key:'daynight',         icon:'🌗', name:'Day/Night',         desc:'Real-time Day/Night Cycle',  api:'builtin', renderer:'daynight' },
      { key:'chokepoints_labels', icon:'⚓', name:'Chokepoint Labels', desc:'Strategic Waterway Labels',  api:'layer', layerFile:'chokepoints', renderer:'chokepoints' },
    ]
  },
  {
    group: "💰 Economy & Resources",
    layers: [
      { key:'economic_centers', icon:'🏦', name:'Economic Centers',  desc:'Exchanges/Central Banks',    api:'layer', layerFile:'economic_centers', renderer:'economic' },
      { key:'minerals',         icon:'💎', name:'Critical Minerals', desc:'Strategic Mining Sites',     api:'layer', layerFile:'minerals',         renderer:'minerals' },
      { key:'ai_datacenters',   icon:'🖥️', name:'AI Data Centers',   desc:'>=10,000 GPU Clusters',      api:'layer', layerFile:'ai_datacenters',   renderer:'ai_dc' },
    ]
  },
];

// - Initialization ----------------------
async function init() {
  setLoadingStatus('Initializing Map...', 10);
  initMap();

  setLoadingStatus('Loading Date List...', 25);
  await loadDates();

  setLoadingStatus('Building Layer Panel...', 40);
  buildLayerPanel();

  setLoadingStatus('Loading Signal Data...', 55);
  await loadSignals();

  setLoadingStatus('Rendering Map Markers...', 75);
  renderSignals();

  setLoadingStatus('Starting System Clock...', 90);
  startClock();

  setLoadingStatus('System Ready', 100);
  setTimeout(() => {
    document.getElementById('loading-overlay').classList.add('hidden');
  }, 500);
}

function setLoadingStatus(msg, pct) {
  document.getElementById('loading-status').textContent = msg;
  document.getElementById('loading-bar').style.width = pct + '%';
}

// - Map ---------------------------
function initMap() {
  state.map = L.map('map', {
    center: [20, 10],
    zoom: 3,
    minZoom: 2,
    maxZoom: 16,
    zoomControl: false,
    attributionControl: true,
  });

  // Dark basemap
  L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
    attribution: '© CARTO © OpenStreetMap',
    subdomains: 'abcd',
    maxZoom: 19,
  }).addTo(state.map);

  L.control.zoom({ position: 'bottomright' }).addTo(state.map);

  // Signal Cluster Layer - Fallback to LayerGroup if plugin is missing
  if (typeof L.markerClusterGroup === 'function') {
    state.signalCluster = L.markerClusterGroup({
      maxClusterRadius: 40,
      disableClusteringAtZoom: 8,
      spiderfyOnMaxZoom: true,
    });
  } else {
    console.warn('MarkerCluster not loaded, falling back to basic LayerGroup');
    state.signalCluster = L.layerGroup();
  }
  state.map.addLayer(state.signalCluster);
}

// - Date ---------------------------
async function loadDates() {
  try {
    const dates = await fetch('/api/dates').then(r=>r.json());
    const sel = document.getElementById('date-select');
    dates.forEach(d => {
      const opt = document.createElement('option');
      opt.value = d; opt.textContent = d;
      sel.appendChild(opt);
    });
    if (dates.length) { sel.value = dates[0]; state.date = dates[0]; }
  } catch(e) { console.warn('Failed to load dates', e); }
}

// - Signal Data -------------------------
async function loadSignals() {
  try {
    const url = '/api/signals?limit=3000' + (state.date ? '&date='+state.date : '');
    const data = await fetch(url).then(r=>r.json());
    state.signals = data;

    // Collect all unique sources
    state.allSrcs.clear();
    data.forEach(s => state.allSrcs.add(s.source||'?'));
    if (state.activeSrcs.size === 0) {
      state.allSrcs.forEach(s => state.activeSrcs.add(s));
    }
    buildSourceChips();
    applyFilters();
  } catch(e) { console.warn('Failed to load signals', e); }
}

function applyFilters() {
  const keyword = document.getElementById('search-input').value.toLowerCase();
  state.date = document.getElementById('date-select').value;

  state.filtered = state.signals.filter(s => {
    if (!state.activeSevs.has(s.severity)) return false;
    if (!state.activeSrcs.has(s.source)) return false;
    if (keyword) {
      const text = (s.title+s.summary+s.country).toLowerCase();
      if (!text.includes(keyword)) return false;
    }
    return true;
  });

  renderFeed();
  renderSignals();
  updateStats();
}

// - Signal Rendering -------------------------
function renderSignals() {
  state.signalCluster.clearLayers();
  let mapCount = 0;

  // Only show signals if at least one signal layer is active
  const signalLayerDefs = LAYER_GROUPS[0].layers;
  const anySignalActive = signalLayerDefs.some(l => state.layers[l.key]?.active);

  state.filtered.forEach(s => {
    if (s.lat == null || s.lon == null) return;

    // If no signal layers are toggled on, don't show any markers
    if (!anySignalActive) return;

    // Check if the specific signal type layer is active
    const layerKey = signalToLayerKey(s);
    // If layerKey is null (unknown type), show it if at least one signal layer is active
    if (layerKey && !state.layers[layerKey]?.active) return;

    const color = SEV_COLOR[s.severity] || '#666';
    const r = SEV_RADIUS[s.severity] || 5;

    const marker = L.circleMarker([s.lat, s.lon], {
      radius: r, fillColor: color, color: color,
      weight: s.severity==='critical' ? 2 : 1,
      opacity: 0.9, fillOpacity: 0.7,
    });

    const time = s.time ? new Date(s.time).toLocaleString('en-US',{timeZone:'UTC'}) : '';
    marker.bindPopup(`
      <div class="popup-title">${escHtml(s.title)}</div>
      <div class="popup-meta">${s.source?.toUpperCase()} · ${s.severity?.toUpperCase()} · ${s.country||'Unknown'}</div>
      <div class="popup-summary">${escHtml((s.summary||'').slice(0,200))}</div>
      <div class="popup-meta" style="margin-top:4px">${time} (UTC)</div>
      ${s.url ? `<a class="popup-link" href="${s.url}" target="_blank">↗ Original Source</a>` : ''}
    `);

    marker.on('click', () => showDetail(s));
    marker.signalId = s.id;
    state.signalCluster.addLayer(marker);
    mapCount++;
  });

  document.getElementById('stat-map').textContent = mapCount;
}

function signalToLayerKey(s) {
  const src = s.source; const type = s.type;
  if (type==='conflict') return 'signal_conflict';
  if (type==='protest') return 'signal_protest';
  if (src==='usgs') return 'signal_earthquake';
  if (src==='nasa_firms') return 'signal_fire';
  if (src==='opensky') return 'signal_military';
  if (src==='noaa') return 'signal_weather';
  if (type==='internet_outage') return 'signal_outage';
  if (src==='usgs_volcano') return 'signal_volcano';
  return null;
}

// - Feed render ------------------------
function renderFeed() {
  const feed = document.getElementById('signal-feed');
  const items = state.filtered.slice().reverse().slice(0,300);
  if (!items.length) {
    feed.innerHTML = '<div class="no-data">// NO SIGNALS MATCH FILTER</div>';
    document.getElementById('feed-count').textContent = '0';
    return;
  }
  document.getElementById('feed-count').textContent = state.filtered.length;

  feed.innerHTML = items.map(s => {
    const time = s.time ? new Date(s.time).toISOString().slice(11,19)+' UTC' : '';
    return `<div class="signal-item sev-${s.severity}" data-id="${s.id}" onclick="clickSignal('${s.id}')">
      <div class="sig-title">${escHtml(s.title.slice(0,100))}</div>
      <div class="sig-meta">
        <span class="sig-badge src">${(s.source||'?').toUpperCase()}</span>
        <span class="sig-badge sev-${s.severity}">${(s.severity||'?').toUpperCase()}</span>
        ${s.country ? `<span class="sig-badge">${escHtml(s.country)}</span>` : ''}
        <span class="sig-time">${time}</span>
      </div>
    </div>`;
  }).join('');
}

function clickSignal(id) {
  const s = state.signals.find(x=>x.id===id);
  if (!s) return;
  state.selectedSignalId = id;
  document.querySelectorAll('.signal-item').forEach(el => el.classList.remove('active'));
  const el = document.querySelector(`.signal-item[data-id="${id}"]`);
  if (el) el.classList.add('active');
  if (s.lat && s.lon) state.map.flyTo([s.lat, s.lon], 7, {duration:1});
  showDetail(s);
}

// - statistics --------------------------─
function updateStats() {
  const sigs = state.filtered;
  document.getElementById('stat-total').textContent = sigs.length;
  document.getElementById('stat-crit').textContent = sigs.filter(s=>s.severity==='critical').length;
  document.getElementById('stat-high').textContent = sigs.filter(s=>s.severity==='high').length;
  document.getElementById('stat-med').textContent = sigs.filter(s=>s.severity==='medium').length;
}

// - Detail --------------------------─
function showDetail(s) {
  const panel = document.getElementById('detail-panel');
  const body = document.getElementById('detail-body');
  const time = s.time ? new Date(s.time).toLocaleString('zh-CN',{timeZone:'UTC'})+' UTC' : '-';
  body.innerHTML = `
    <div class="detail-row"><span class="detail-key">SOURCE</span><span class="detail-val">${escHtml(s.source||'?')}</span></div>
    <div class="detail-row"><span class="detail-key">TYPE</span><span class="detail-val">${escHtml(s.type||'?')}</span></div>
    <div class="detail-row"><span class="detail-key">SEVERITY</span><span class="detail-val" style="color:${SEV_COLOR[s.severity]||'#888'}">${(s.severity||'?').toUpperCase()}</span></div>
    <div class="detail-row"><span class="detail-key">TIME</span><span class="detail-val">${time}</span></div>
    <div class="detail-row"><span class="detail-key">COUNTRY</span><span class="detail-val">${escHtml(s.country||'-')}</span></div>
    ${s.lat ? `<div class="detail-row"><span class="detail-key">COORDS</span><span class="detail-val">${s.lat.toFixed(4)}, ${s.lon.toFixed(4)}</span></div>` : ''}
    <div class="detail-row"><span class="detail-key">TITLE</span><span class="detail-val">${escHtml(s.title||'')}</span></div>
    ${s.summary ? `<div class="detail-row"><span class="detail-key">SUMMARY</span><span class="detail-val">${escHtml(s.summary.slice(0,300))}</span></div>` : ''}
    ${s.url ? `<div class="detail-row"><span class="detail-key">URL</span><span class="detail-val url"><a href="${escHtml(s.url)}" target="_blank">↗ 原文链接</a></span></div>` : ''}
  `;
  panel.classList.add('open');
}

function closeDetail() {
  document.getElementById('detail-panel').classList.remove('open');
}

// - Source Chips -----------------------─
function buildSourceChips() {
  const container = document.getElementById('chips-source');
  container.innerHTML = '';
  const srcList = [...state.allSrcs].sort();
  srcList.forEach(src => {
    const chip = document.createElement('span');
    chip.className = 'chip active';
    chip.dataset.src = src;
    chip.textContent = src.toUpperCase().slice(0,8);
    chip.onclick = () => toggleChip(chip, 'src');
    container.appendChild(chip);
  });
}

function toggleChip(el, type) {
  if (type==='sev') {
    const sev = el.dataset.sev;
    if (state.activeSevs.has(sev)) { state.activeSevs.delete(sev); el.classList.remove('active'); }
    else { state.activeSevs.add(sev); el.classList.add('active'); }
  } else {
    const src = el.dataset.src;
    if (state.activeSrcs.has(src)) { state.activeSrcs.delete(src); el.classList.remove('active'); }
    else { state.activeSrcs.add(src); el.classList.add('active'); }
  }
  applyFilters();
}

// - Layer Panel ------------------------─
function buildLayerPanel() {
  const container = document.getElementById('layer-list');
  container.innerHTML = '';

  LAYER_GROUPS.forEach(group => {
    const groupEl = document.createElement('div');
    groupEl.className = 'layer-group';
    groupEl.innerHTML = `<div class="layer-group-title">${group.group}</div>`;

    group.layers.forEach(layerDef => {
      // Initialization status: The signal layer is fully open by default, and the static layer is turned off by default
      const isSignal = layerDef.api === 'signals';
      if (!state.layers[layerDef.key]) {
        state.layers[layerDef.key] = {
          active: isSignal,
          leafletLayer: null,
          data: null,
          status: 'idle', // idle | loading | loaded | error
          def: layerDef,
        };
      }

      const item = document.createElement('div');
      item.className = 'layer-item' + (state.layers[layerDef.key].active ? ' active' : '');
      item.id = 'layer-item-' + layerDef.key;
      item.innerHTML = `
        <div class="layer-toggle"></div>
        <div class="layer-icon">${layerDef.icon}</div>
        <div class="layer-name">${layerDef.name}<br><span style="font-size:9px;color:var(--text-dim)">${layerDef.desc}</span></div>
        <div class="layer-status" id="lstatus-${layerDef.key}"></div>
        <div class="layer-count" id="lcount-${layerDef.key}"></div>
      `;
      item.onclick = () => toggleLayer(layerDef.key);
      groupEl.appendChild(item);
    });

    container.appendChild(groupEl);
  });
}

async function toggleLayer(key) {
  const layer = state.layers[key];
  if (!layer) return;

  layer.active = !layer.active;

  const item = document.getElementById('layer-item-' + key);
  if (layer.active) {
    item.classList.add('active');
    await activateLayer(key);
  } else {
    item.classList.remove('active');
    deactivateLayer(key);
  }

  // The signal layer needs to be re rendered
  if (layer.def.api === 'signals') {
    renderSignals();
  }
}

async function activateLayer(key) {
  const layer = state.layers[key];
  const def = layer.def;

  if (def.api === 'signals') return; // The signal layer is processed by renderSignals

  // Built in layers (no API data required)
  if (def.api === 'builtin') {
    if (def.renderer === 'daynight') {
      layer.leafletLayer = renderDayNight();
      if (layer.leafletLayer && layer.active) state.map.addLayer(layer.leafletLayer);
      // Updated every minute
      layer._interval = setInterval(() => {
        if (layer.leafletLayer) state.map.removeLayer(layer.leafletLayer);
        layer.leafletLayer = renderDayNight();
        if (layer.active) state.map.addLayer(layer.leafletLayer);
      }, 60000);
      setLayerStatus(def.key, 'loaded');
    }
    return;
  }

  // If there is already data, display it directly
  if (layer.leafletLayer && layer.data) {
    state.map.addLayer(layer.leafletLayer);
    return;
  }

  // Load data
  setLayerStatus(key, 'loading');
  try {
    const resp = await fetch('/api/layer/' + def.layerFile);
    if (!resp.ok) throw new Error(`HTTP ${resp.status} for ${def.layerFile}`);
    const data = await resp.json();
    console.log(`Layer ${key} loaded successfully:`, Array.isArray(data) ? data.length + 'Rows' : typeof data);
    layer.data = data;
    layer.leafletLayer = buildLayerRenderer(def, data);
    if (layer.leafletLayer && layer.active) {
      state.map.addLayer(layer.leafletLayer);
      console.log('✅ Layer added to map:', key);
    } else if (!layer.leafletLayer) {
      console.error('❌ buildLayerRenderer return null:', key);
    }
    const count = Array.isArray(data) ? data.length : (data.features?.length || 0);
    setLayerStatus(key, 'loaded', count);
  } catch(e) {
    console.error('Layer loading failed', key, e);
    setLayerStatus(key, 'error');
    // Show error count as -1 to signal failure
    const cEl = document.getElementById('lcount-' + key);
    if (cEl) cEl.textContent = 'ERR';
  }
}

function deactivateLayer(key) {
  const layer = state.layers[key];
  if (layer.leafletLayer) {
    state.map.removeLayer(layer.leafletLayer);
  }
  if (layer._interval) {
    clearInterval(layer._interval);
    layer._interval = null;
  }
}

function setLayerStatus(key, status, count) {
  const el = document.getElementById('lstatus-' + key);
  const cEl = document.getElementById('lcount-' + key);
  if (el) { el.className = 'layer-status ' + status; }
  if (cEl && count != null) { cEl.textContent = count; }
}

// - Layer renderer -----------------------─
function buildLayerRenderer(def, data) {
  const r = def.renderer;
  if (!data || (Array.isArray(data) && !data.length)) {
    console.warn('buildLayerRenderer: empty data for', def.key);
    return null;
  }
  console.log('buildLayerRenderer:', def.key, 'renderer='+r, 'items='+(Array.isArray(data)?data.length:'object'));

  const renderers = {
    nuclear_plants:   () => renderNuclearPlants(data),
    nuclear_weapons:  () => renderNuclearWeapons(data),
    gamma_irradiators:() => renderGammaIrradiators(data),
    military_bases:   () => renderMilitaryBases(data),
    spaceports:       () => renderSpaceports(data),
    submarine_cables: () => renderSubmarineCables(data),
    lines:            () => renderLines(data, def),
    pipelines:        () => renderPipelines(data),
    chokepoints:      () => renderChokepoints(data),
    ports:            () => renderPorts(data),
    ucdp:             () => renderUCDP(data),
    unhcr:            () => renderUNHCR(data),
    economic:         () => renderEconomic(data),
    minerals:         () => renderMinerals(data),
    ai_dc:            () => renderAIDC(data),
  };
  if (!renderers[r]) {
    console.warn('buildLayerRenderer: unknown renderer', r, 'for', def.key);
    return null;
  }
  try {
    const layer = renderers[r]();
    const count = layer ? (layer.getLayers ? layer.getLayers().length : '?') : 0;
    console.log('buildLayerRenderer result:', def.key, '→', count, 'map objects');
    return layer;
  } catch(err) {
    console.error('buildLayerRenderer ERROR in', r, 'for', def.key, ':', err);
    return null;
  }
}

// - Each renderer implementation -----------------------

function svgIcon(svg, size=24) {
  return L.divIcon({ html: svg, className:'', iconSize:[size,size], iconAnchor:[size/2,size/2] });
}

function circleIcon(color, size=12, label='') {
  return L.divIcon({
    html: `<div style="width:${size}px;height:${size}px;border-radius:50%;background:${color};border:1.5px solid rgba(255,255,255,.4);display:flex;align-items:center;justify-content:center;font-size:8px;color:#fff">${label}</div>`,
    className:'', iconSize:[size,size], iconAnchor:[size/2,size/2]
  });
}

function renderNuclearPlants(data) {
  const group = L.layerGroup();
  data.forEach(p => {
    const lat = parseFloat(p.Latitude || p.lat);
    const lon = parseFloat(p.Longitude || p.lon);
    if (isNaN(lat) || isNaN(lon)) return;
    const status = p.Status || p.status || '';
    const color = status.includes('Operational') ? '#00ff88' : status.includes('Construction') ? '#ffcc00' : '#4a7a98';
    const m = L.circleMarker([lat,lon],{ radius:7, fillColor:color, color:color, weight:2, opacity:.9, fillOpacity:.6 });
    m.bindPopup(`<div class="popup-title">⚛️ ${p.Name || p.name}</div><div class="popup-meta">${p.Country || p.country} · ${status}</div><div class="popup-summary">Capacity: ${p.Capacity || p.capacity || 'N/A'} MWe<br>Type: ${p.ReactorType || p.type || 'N/A'}</div>`);
    group.addLayer(m);
  });
  return group;
}

function renderNuclearWeapons(data) {
  const group = L.layerGroup();
  data.forEach(p => {
    if (p.lat == null || p.lon == null) return;
    const typeColor = {
      weapons_storage:'#ff2244', production:'#ff7700', design_lab:'#ffcc00',
      enrichment:'#ff4466', test_site:'#888', assembly_disassembly:'#ff6600',
      enrichment_production:'#ff3355', former_test:'#555', research_reactor:'#00aaff',
      power_plant:'#00cc66', conversion:'#ffaa00',
    };
    const color = typeColor[p.type] || '#888';
    const m = L.circleMarker([p.lat,p.lon],{ radius:8, fillColor:color, color:color, weight:2, opacity:1, fillOpacity:.75 });
    m.bindPopup(`<div class="popup-title">💣 ${p.name}</div><div class="popup-meta">${p.country} · ${p.operator} · ${p.type}</div>${p.notes?`<div class="popup-summary">${p.notes}</div>`:''}`);
    group.addLayer(m);
  });
  return group;
}

function renderGammaIrradiators(data) {
  const group = L.layerGroup();
  data.forEach(p => {
    if (p.lat == null || p.lon == null) return;
    const m = L.circleMarker([p.lat,p.lon],{ radius:5, fillColor:'#ff44aa', color:'#ff44aa', weight:1, opacity:.8, fillOpacity:.5 });
    m.bindPopup(`<div class="popup-title">☢️ ${p.name||p.facility}</div><div class="popup-meta">${p.country} · ${p.operator||''}</div><div class="popup-summary">Purpose: ${p.use||'Industrial irradiation'}</div>`);
    group.addLayer(m);
  });
  return group;
}

function renderMilitaryBases(data) {
  const group = L.layerGroup();
  const opColor = { US:'#0088ff', NATO:'#00aaff', China:'#ff4444', Russia:'#ff6600', France:'#0055cc', UK:'#004499', Other:'#888' };
  data.forEach(b => {
    if (b.lat == null || b.lon == null) return;
    const color = opColor[b.operator] || '#888';
    const m = L.circleMarker([b.lat,b.lon],{ radius:5, fillColor:color, color:color, weight:1.5, opacity:.9, fillOpacity:.6 });
    m.bindPopup(`<div class="popup-title">🪖 ${b.name}</div><div class="popup-meta">${b.country} · ${b.operator} · ${b.type||''}</div>`);
    group.addLayer(m);
  });
  return group;
}

function renderSpaceports(data) {
  const group = L.layerGroup();
  data.forEach(s => {
    if (s.lat == null || s.lon == null) return;
    const active = s.active === true || s.active === 'true' || s.status === 'operational';
    const color = active ? '#00ff88' : '#888';
    const m = L.circleMarker([s.lat,s.lon],{ radius:7, fillColor:color, color:color, weight:2, opacity:1, fillOpacity:.7 });
    m.bindPopup(`<div class="popup-title">🚀 ${s.name}</div><div class="popup-meta">${s.country} · ${s.operator||''} · ${active?'Active':'Inactive'}</div><div class="popup-summary">${s.notes||''}</div>`);
    group.addLayer(m);
  });
  return group;
}

// - Submarine Cable Metadata renderer -------------------
// Landing point name → approx coords
const LANDING_COORDS = {
  'UK':[51.5,-0.1], 'France':[43.3,3.9], 'Italy':[41.9,12.5], 'Egypt':[31.2,29.9],
  'India':[13.0,80.3], 'Malaysia':[3.1,101.7], 'Singapore':[1.3,103.8], 'Japan':[34.7,139.0],
  'Saudi Arabia':[26.4,50.1], 'Thailand':[13.0,100.5], 'Turkey':[36.8,36.1],
  'Australia':[-33.8,151.2], 'China':[22.3,114.2], 'Pakistan':[25.1,62.3],
  'Kenya':[-4.0,39.7], 'Hong Kong':[22.3,114.2], 'Vietnam':[11.0,108.3],
  'Cambodia':[10.6,104.2], 'Oman':[17.0,54.1], 'Greece':[37.9,23.7],
  'USA':[34.0,-118.5], 'Philippines':[14.6,121.0], 'Guam':[13.4,144.7],
  'Indonesia':[-8.8,115.2], 'Spain':[36.1,-5.4], 'Denmark':[55.7,12.6],
  'Norway':[59.9,10.7], 'Ireland':[51.9,-8.5], 'Taiwan':[22.6,120.3],
  'South Korea':[35.2,129.1], 'UAE':[24.5,54.4], 'Maldives':[4.2,73.5],
  'Sri Lanka':[6.9,79.8], 'Sweden':[59.3,18.1], 'Alaska':[61.2,-149.9],
  'New Zealand':[-36.9,174.7], 'Brazil':[-23.0,-43.2],
};

function renderSubmarineCables(data) {
  const group = L.layerGroup();
  const colors = ['#00d4ff','#00ff88','#ff8800','#ff44aa','#8844ff','#44ffaa'];
  data.forEach((cable, idx) => {
    const color = colors[idx % colors.length];
    const lps = cable.landing_points || [];
    const coords = lps.map(lp => {
      // Try exact match, then partial match
      if (LANDING_COORDS[lp]) return LANDING_COORDS[lp];
      for (const [k,v] of Object.entries(LANDING_COORDS)) {
        if (lp.includes(k) || k.includes(lp)) return v;
      }
      return null;
    }).filter(Boolean);

    if (coords.length >= 2) {
      const line = L.polyline(coords, { color, weight:1.5, opacity:.55 });
      line.bindPopup(`<div class="popup-title">🔗 ${cable.name}</div><div class="popup-meta">${cable.year||''} · ${cable.length_km?cable.length_km.toLocaleString()+'km':''}</div><div class="popup-summary">登陆点: ${lps.join(', ')}<br>${cable.notes||''}</div>`);
      group.addLayer(line);
    }

    // Landing point dots
    coords.forEach((coord, i) => {
      const dot = L.circleMarker(coord, { radius:3, fillColor:color, color:color, weight:1, fillOpacity:.8 });
      group.addLayer(dot);
    });
  });
  return group;
}

// Chokepoint name → approximate coordinates lookup
const CHOKEPOINT_COORDS = {
  'Malacca': [2.5, 101.3], 'Hormuz': [26.6, 56.5], 'Suez': [30.5, 32.3],
  'Gibraltar': [35.97, -5.35], 'Pacific Ocean': [20, -150], 'Atlantic': [40, -40],
  'Dover': [51.04, 1.4], 'Cape of Good Hope': [-34.4, 18.5], 'Lombok': [-8.8, 115.7],
  'Taiwan Strait': [24.5, 119.5], 'South China Sea': [13, 113], 'Panama Canal': [9.1, -79.7],
  'Northern Sea Route': [76, 100], 'Indian Ocean': [-10, 75], 'Bab el-Mandeb': [12.6, 43.3],
};

const PORT_COORDS = {
  'Shanghai': [31.23, 121.47], 'Rotterdam': [51.92, 4.48], 'Los Angeles': [33.73, -118.26],
  'Singapore': [1.26, 103.82], 'Ningbo': [29.88, 121.55], 'Ras Tanura': [26.6, 50.16],
  'Jebel Ali': [25.01, 55.08], 'Durban': [-29.86, 31.02], 'Santos': [-23.96, -46.3],
};

function routeToCoords(route) {
  const points = [];
  // Add 'from' port
  const fromCoord = PORT_COORDS[route.from];
  if (fromCoord) points.push(fromCoord);
  // Add via chokepoints
  if (route.via) {
    route.via.forEach(v => {
      const c = CHOKEPOINT_COORDS[v] || PORT_COORDS[v];
      if (c) points.push(c);
    });
  }
  // Add 'to' port
  const toCoord = PORT_COORDS[route.to];
  if (toCoord) points.push(toCoord);
  return points;
}

function renderLines(data, def) {
  const group = L.layerGroup();
  // GeoJSON format
  if (data && data.type === 'FeatureCollection') {
    L.geoJSON(data, {
      style: { color:'#00d4ff', weight:1.5, opacity:.6 },
      onEachFeature: (feature, layer) => {
        if (feature.properties) {
          const p = feature.properties;
          layer.bindPopup(`<div class="popup-title">🔗 ${p.name||p.Name||'Submarine Cable'}</div><div class="popup-summary">${JSON.stringify(p).slice(0,200)}</div>`);
        }
      }
    }).addTo(group);
    return group;
  }
  // Array format - trade routes or other line data
  if (Array.isArray(data)) {
    // Check if items have path arrays (old format) or from/to/via (trade routes)
    data.forEach(r => {
      let latlngs = [];
      if (r.path && r.path.length) {
        latlngs = r.path.map(p => [p[0], p[1]]);
      } else if (r.from || r.to || r.via) {
        latlngs = routeToCoords(r);
      }
      if (latlngs.length < 2) return;
      const isOil = r.type === 'oil';
      const color = isOil ? '#ff8800' : '#00d4ff';
      const line = L.polyline(latlngs, { color, weight:1.5, opacity:.55, dashArray:'6,4' });
      const teu = r.teu_annual_m ? `${r.teu_annual_m}M TEU/YEAR` : r.mbpd ? `${r.mbpd} Mbpd` : '';
      line.bindPopup(`<div class="popup-title">🗺️ ${r.name||'Route'}</div><div class="popup-meta">${r.from||''} → ${r.to||''}</div><div class="popup-summary">${teu?teu+'<br>':''}${r.notes||''}</div>`);
      group.addLayer(line);
    });
  }
  return group;
}

function renderPipelines(data) {
  const group = L.layerGroup();
  const typeColor = { gas:'#ffaa00', oil:'#ff6600', oil_gas:'#ff8800' };
  data.forEach(p => {
    if (!p.lat_start || !p.lat_end) return;
    const color = typeColor[p.type] || '#ff7700';
    const isDamaged = p.status === 'damaged';
    const line = L.polyline([[p.lat_start,p.lon_start],[p.lat_end,p.lon_end]], {
      color: isDamaged ? '#ff2244' : color,
      weight: 2.5, opacity: isDamaged ? .5 : .75,
      dashArray: isDamaged ? '6,4' : p.status==='planned' ? '3,6' : null,
    });
    line.bindPopup(`<div class="popup-title">⛽ ${p.name}</div><div class="popup-meta">${p.from} → ${p.to} · ${p.type} · <span style="color:${isDamaged?'#ff2244':'#00cc66'}">${p.status}</span></div><div class="popup-summary">${p.capacity_bcm_y?'Capacity: '+p.capacity_bcm_y+' BCM/YEAR':''} ${p.capacity_mbpd?'Capacity: '+p.capacity_mbpd+' Mbpd':''}<br>${p.notes||''}</div>`);
    group.addLayer(line);

    // Endpoint marking
    [[[p.lat_start,p.lon_start],'start'],[[p.lat_end,p.lon_end],'end']].forEach(([ll, pos]) => {
      const dot = L.circleMarker(ll, { radius:4, fillColor:color, color:color, weight:1, fillOpacity:.8 });
      group.addLayer(dot);
    });
  });
  return group;
}

function renderChokepoints(data) {
  const group = L.layerGroup();
  data.forEach(c => {
    if (c.lat == null || c.lon == null) return;
    const m = L.circleMarker([c.lat,c.lon],{
      radius:10, fillColor:'#ff9900', color:'#ffcc00',
      weight:2, opacity:1, fillOpacity:.4,
    });
    m.bindPopup(`<div class="popup-title">⚓ ${c.name}</div><div class="popup-meta">${c.region||''}</div><div class="popup-summary">${c.daily_oil_mbpd?'Oil flux: '+c.daily_oil_mbpd+' Mbpd<br>':''} ${c.notes||''}</div>`);
    group.addLayer(m);

    const label = L.marker([c.lat,c.lon], {
      icon: L.divIcon({
        html:`<div style="font-family:'Share Tech Mono',monospace;font-size:9px;color:#ffcc00;white-space:nowrap;text-shadow:0 0 4px #000;margin-left:12px;margin-top:-4px">${c.name}</div>`,
        className:'', iconSize:[0,0]
      })
    });
    group.addLayer(label);
  });
  return group;
}

function renderPorts(data) {
  const group = L.layerGroup();
  data.forEach(p => {
    if (p.lat == null || p.lon == null) return;
    const rank = p.rank || p.strategic_rank || 99;
    const teu = p.teu_m || p.teu_million || 0;
    const size = rank === 1 ? 10 : rank <= 5 ? 8 : rank <= 15 ? 6 : 5;
    const m = L.circleMarker([p.lat, p.lon], {
      radius: size, fillColor:'#00aaff', color:'#0088ff',
      weight:1.5, opacity:.9, fillOpacity:.5,
    });
    m.bindPopup(`<div class="popup-title">🚢 ${p.name}</div><div class="popup-meta">${p.country}${rank?` · 排名: #${rank}`:''}</div><div class="popup-summary">Throughput: ${teu ? teu+'M TEU/YEAR' : 'N/A'}<br>${p.notes||''}</div>`);
    group.addLayer(m);
  });
  return group;
}

function renderUCDP(data) {
  const group = L.layerGroup();
  const items = Array.isArray(data) ? data : (data.Result || []);
  items.slice(0,2000).forEach(e => {
    const lat = parseFloat(e.latitude || e.lat);
    const lon = parseFloat(e.longitude || e.lon);
    if (isNaN(lat) || isNaN(lon)) return;
    const deaths = parseInt(e.best || e.deaths_best || 0);
    const color = deaths > 100 ? '#ff2244' : deaths > 10 ? '#ff7700' : '#ffcc00';
    const m = L.circleMarker([lat,lon],{ radius:5, fillColor:color, color:color, weight:1, opacity:.8, fillOpacity:.5 });
    m.bindPopup(`<div class="popup-title">📍 UCDP Conflict Event</div><div class="popup-meta">${e.country||''} · ${e.year||''}</div><div class="popup-summary">Estimated number of deaths: ${deaths}<br>${e.conflict_name||e.dyad_name||''}</div>`);
    group.addLayer(m);
  });
  return group;
}

function renderUNHCR(data) {
  const group = L.layerGroup();
  const items = Array.isArray(data) ? data : [];
  // Data is global summary - show top displacement origin regions as approximate markers
  const CRISIS_REGIONS = [
    {name:'Syria',lat:34.8,lon:38.9,refugees:6500000},
    {name:'Ukraine',lat:49.0,lon:32.0,refugees:6000000},
    {name:'Afghanistan',lat:33.9,lon:67.7,refugees:5700000},
    {name:'Venezuela',lat:8.0,lon:-66.0,refugees:5400000},
    {name:'South Sudan',lat:7.0,lon:30.0,refugees:2300000},
    {name:'Myanmar',lat:17.0,lon:96.0,refugees:1200000},
    {name:'Somalia',lat:6.0,lon:45.3,refugees:900000},
    {name:'DRC',lat:-4.0,lon:21.8,refugees:1000000},
    {name:'Sudan',lat:15.6,lon:32.5,refugees:800000},
    {name:'Ethiopia',lat:9.1,lon:40.5,refugees:600000},
  ];

  // Get latest year data for overlay
  const latest = items.length ? items[items.length-1] : null;

  CRISIS_REGIONS.forEach(r => {
    const radius = Math.min(Math.max(Math.sqrt(r.refugees/50000), 5), 22);
    const m = L.circleMarker([r.lat,r.lon],{ radius, fillColor:'#ff8800', color:'#ff6600', weight:1.5, opacity:.85, fillOpacity:.35 });
    const totalText = latest ? `Total number of refugees worldwide (${latest.year}): ${(latest.refugees/1e6).toFixed(1)}M<br>Displaced persons: ${(latest.idps/1e6).toFixed(1)}M IDPs` : '';
    m.bindPopup(`<div class="popup-title">🚶 ${r.name} The refugee crisis</div><div class="popup-summary">Escaping refugees: ~${(r.refugees/1e6).toFixed(1)}M<br>${totalText}</div>`);
    group.addLayer(m);
  });
  return group;
}

function renderEconomic(data) {
  const group = L.layerGroup();
  const typeIcon = { 'Stock Exchange':'📈', 'Central Bank':'🏛️', 'International Finance':'🌐', 'Commodities':'📦' };
  const typeColor = { 'Stock Exchange':'#00ff88', 'Central Bank':'#ffcc00', 'International Finance':'#00aaff', 'Commodities':'#ff8800' };
  data.forEach(e => {
    if (e.lat == null || e.lon == null) return;
    const color = typeColor[e.type] || '#888';
    const icon = typeIcon[e.type] || '💰';
    const m = L.circleMarker([e.lat,e.lon],{ radius:7, fillColor:color, color:color, weight:1.5, opacity:.9, fillOpacity:.5 });
    m.bindPopup(`<div class="popup-title">${icon} ${e.name}</div><div class="popup-meta">${e.country} · ${e.type}</div><div class="popup-summary">${e.market_cap_t?'Market Capitalization: $'+e.market_cap_t+'T':''} ${e.notes||''}</div>`);
    group.addLayer(m);
  });
  return group;
}

function renderMinerals(data) {
  const group = L.layerGroup();
  const minColor = {
    lithium:'#00aaff', cobalt:'#8800ff', rare_earth:'#ff00aa', copper:'#ff6600',
    uranium:'#00ff44', nickel:'#ffaa00', manganese:'#ff8844', platinum:'#dddddd',
    chromite:'#44aaff', tungsten:'#88ff00', coltan:'#ff4488', polysilicon:'#aaddff',
    'copper/gold':'#ffaa44', 'uranium/copper':'#88ff44', 'pgm/vanadium':'#ccddff',
    'iron ore/lithium':'#ff8844', 'cobalt/copper':'#aa44ff', 'nickel/cobalt':'#ffaa66',
    'nickel/palladium':'#ffccaa', 'rare earths/lithium':'#ff66cc', 'rare earths':'#ff00aa',
    'cobalt': '#8800ff',
  };
  data.forEach(m => {
    if (m.lat == null || m.lon == null) return;
    const color = minColor[(m.mineral||'').toLowerCase()] || '#888';
    const marker = L.circleMarker([m.lat,m.lon],{ radius:6, fillColor:color, color:color, weight:1.5, opacity:.9, fillOpacity:.6 });
    marker.bindPopup(`<div class="popup-title">💎 ${m.name}</div><div class="popup-meta">${m.country} · ${(m.mineral||'').toUpperCase()}</div><div class="popup-summary">${m.annual_kt?'Annual Production: '+m.annual_kt+'kt':''}${m.reserves?' Reserves: '+m.reserves:''}<br>${m.notes||''}</div>`);
    group.addLayer(marker);
  });
  return group;
}

// - End line of day and night -----------------------
function renderDayNight() {
  // Calculate the position of the sun and draw the endpoint line
  const group = L.layerGroup();
  const now = new Date();

  // Calculate solar declination and time angle
  const dayOfYear = Math.floor((now - new Date(now.getFullYear(),0,0)) / 86400000);
  const declination = -23.45 * Math.cos(2*Math.PI*(dayOfYear+10)/365) * Math.PI/180;
  const utcHour = now.getUTCHours() + now.getUTCMinutes()/60 + now.getUTCSeconds()/3600;
  const sunLon = -(utcHour - 12) * 15;

  // Draw the termination line
  const points = [];
  for (let lon = -180; lon <= 180; lon += 2) {
    const lat = Math.atan(-Math.cos((lon - sunLon)*Math.PI/180) / Math.tan(declination)) * 180/Math.PI;
    if (!isNaN(lat)) points.push([lat, lon]);
  }
  if (points.length > 1) {
    L.polyline(points, { color:'#ffcc00', weight:1.5, opacity:.6, dashArray:'4,4' }).addTo(group);
  }

  // Nighttime Hemisphere Coverage (Simplified: Using Translucent Polygons)
  // Build a polygon on the night side
  const nightPoly = [];
  const isSouthernDark = declination > 0;
  for (let lon = -180; lon <= 180; lon += 3) {
    const lat = Math.atan(-Math.cos((lon - sunLon)*Math.PI/180) / Math.tan(declination)) * 180/Math.PI;
    if (!isNaN(lat)) nightPoly.push([lat, lon]);
  }
  if (nightPoly.length > 1) {
    const edgeLat = isSouthernDark ? -90 : 90;
    const fullNight = [...nightPoly, [edgeLat, 180], [edgeLat, -180], nightPoly[0]];
    L.polygon(fullNight, { color:'transparent', fillColor:'#000033', fillOpacity:.35, weight:0 }).addTo(group);
  }

  return group;
}

function renderAIDC(data) {
  const group = L.layerGroup();
  data.forEach(d => {
    if (d.lat == null || d.lon == null) return;
    const gpus = d.gpu_est || 0;
    const radius = Math.min(Math.max(Math.log10(gpus)*4, 6), 18);
    const m = L.circleMarker([d.lat,d.lon],{ radius, fillColor:'#00ff88', color:'#00cc66', weight:1.5, opacity:.9, fillOpacity:.4 });
    m.bindPopup(`<div class="popup-title">🖥️ ${d.name}</div><div class="popup-meta">${d.country} · ${d.operator}</div><div class="popup-summary">GPU: ${gpus.toLocaleString()} × ${d.gpu_type||'?'}<br>${d.notes||''}</div>`);
    group.addLayer(m);
  });
  return group;
}

// - Clock --------------------------─
function startClock() {
  function tick() {
    const now = new Date();
    const h = String(now.getUTCHours()).padStart(2,'0');
    const m = String(now.getUTCMinutes()).padStart(2,'0');
    const s = String(now.getUTCSeconds()).padStart(2,'0');
    document.getElementById('clock').textContent = `${h}:${m}:${s} UTC`;
  }
  tick();
  setInterval(tick, 1000);
}

// - Auto Refresh ------------------------─
function toggleAuto() {
  const btn = document.getElementById('btn-auto');
  state.autoRefresh = !state.autoRefresh;
  btn.classList.toggle('on', state.autoRefresh);
  btn.textContent = state.autoRefresh ? '⟳ AUTO ON' : '⟳ AUTO';
  if (state.autoRefresh) {
    state.autoTimer = setInterval(async () => {
      await loadSignals();
    }, 15 * 60 * 1000);
  } else {
    clearInterval(state.autoTimer);
  }
}

// - Tools --------------------------─
function escHtml(str) {
  return String(str||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

// - Start --------------------------─
window.addEventListener('load', async () => {
  try {
    await window._mapsReady;
    await init();
  } catch(e) {
    document.getElementById('loading-status').textContent = 'Map library loading failed: ' + e.message;
    document.getElementById('loading-bar').style.background = '#ff2244';
    console.error('Map library loading failed:', e);
  }
});

// - diagnosis ----------------------------─
async function showDiag() {
  try {
    const d = await fetch('/api/debug').then(r=>r.json());
    let msg = '📂 Script directory: ' + d.script_dir + '\n';
    msg += '📁 Data directory: ' + d.data_dir + ' [' + (d.data_dir_exists?'✅':'❌') + ']\n';
    msg += '📁 Layer directory: ' + d.layers_dir + ' [' + (d.layers_dir_exists?'✅':'❌') + ']\n\n';
    msg += 'Layer file (' + d.layer_files.length + '):\n';
    d.layer_files.forEach(f => { msg += '  ✅ ' + f + '\n'; });
    const expected = ['military_bases.json','nuclear_weapons.json','gamma_irradiators.json',
      'spaceports.json','chokepoints.json','ports.json','trade_routes.json',
      'submarine_cables.json','pipelines.json','economic_centers.json',
      'minerals.json','ai_datacenters.json','unhcr_flows.json'];
    const missing = expected.filter(f => !d.layer_files.includes(f));
    if (missing.length) {
      msg += '\n❌ Missing file (' + missing.length + '):\n';
      missing.forEach(f => { msg += '  ✗ ' + f + '\n'; });
    } else {
      msg += '\n✅ All layer files are complete!';
    }
    msg += '\n\nSignal file: ' + d.signal_files.join(', ');
    alert(msg);
  } catch(e) { alert('Diagnosis failed: ' + e); }
}
</script>
</body>
</html>
"""

if __name__ == "__main__":
    print("=" * 60)
    print("  WorldMirror Global Situational Awareness Dashboard v1.0")
    print(f"  Vist: http://localhost:5000")
    print(f"  Data directory: {os.path.abspath(DATA_DIR)}")
    print(f"  Layer directory: {os.path.abspath(LAYERS_DIR)}")
    print("=" * 60)
    app.run(host="0.0.0.0", port=5000, debug=False)
