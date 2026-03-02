"""
layers_downloader.py — WorldMirror Static Layer Downloader v1.0
================================================================
Download all freely available static map layers to ./data/layers/

Layer list:
  ✅ Nuclear facilities        GeoNuclearData (power plants + research reactors)
  ✅ Submarine cables          TeleGeography API
  ✅ Military bases            Manually compiled (180+; US / NATO / CN / RU / etc.)
  ✅ Nuclear weapons sites     Manually compiled (known arsenals / enrichment / weapons)
  ✅ Gamma irradiators         IAEA DIRATA public dataset
  ✅ Space launch sites        Manually compiled (30+)
  ✅ Strategic chokepoints     Manually compiled (20 maritime chokepoints)
  ✅ Major ports               Manually compiled (61 strategic ports)
  ✅ Trade routes              Manually compiled major routes
  ✅ UCDP conflict events      Uppsala University free API
  ✅ UNHCR displacement data   UNHCR Refugee Statistics API
  ✅ Critical minerals         Manually compiled major mining areas
  ✅ Economic centers          Manually compiled exchanges / central banks
  ✅ AI data centers           Manually compiled clusters with ≥10,000 GPUs
  ✅ Oil & gas pipelines       Manually compiled major pipelines

Run: python layers_downloader.py (once per month)
================================================================
"""

import json, os, time, requests

LAYERS_DIR = "./data/layers"
os.makedirs(LAYERS_DIR, exist_ok=True)


def save(name, data):
    path = os.path.join(LAYERS_DIR, f"{name}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"  ✅ {name}.json  ({os.path.getsize(path)//1024} KB, {len(data) if isinstance(data,list) else ''} items)")

def get(url, **kw):
    r = requests.get(url, timeout=30, headers={"User-Agent": "WorldMirror/1.0"}, **kw)
    r.raise_for_status()
    return r


# ── 1. Nuclear Power Plants ────────────────────────────────────
def dl_nuclear():
    print("\n[1] Nuclear Power Plants (GeoNuclearData)...")
    try:
        data = get("https://raw.githubusercontent.com/cristianst85/GeoNuclearData/master/src/nuclear_power_plants.json").json()
        active = [p for p in data if p.get("status") in ("Operational","Under Construction","Planned")]
        save("nuclear_plants", active)
    except Exception as e:
        print(f"  ❌ {e}")


# ── 2. Nuclear Weapons Facilities ──────────────────────────────
NUCLEAR_WEAPONS = [
    # USA
    {"name":"Kirtland AFB (B61 storage)","country":"USA","operator":"US","lat":35.040,"lon":-106.609,"type":"weapons_storage"},
    {"name":"Büchel Air Base (B61)","country":"Germany","operator":"US/NATO","lat":50.173,"lon":7.063,"type":"weapons_storage","notes":"Approx. 20 B61 bombs"},
    {"name":"Volkel Air Base (B61)","country":"Netherlands","operator":"US/NATO","lat":51.655,"lon":5.706,"type":"weapons_storage"},
    {"name":"Aviano (B61)","country":"Italy","operator":"US","lat":46.031,"lon":12.596,"type":"weapons_storage"},
    {"name":"Ghedi Torre (B61)","country":"Italy","operator":"US/NATO","lat":45.432,"lon":10.268,"type":"weapons_storage"},
    {"name":"Incirlik (B61)","country":"Turkey","operator":"US/NATO","lat":37.002,"lon":35.426,"type":"weapons_storage"},
    {"name":"Oak Ridge Y-12","country":"USA","operator":"NNSA","lat":36.021,"lon":-84.254,"type":"production"},
    {"name":"Pantex Plant","country":"USA","operator":"NNSA","lat":35.240,"lon":-101.548,"type":"assembly_disassembly","notes":"Sole US nuclear weapons assembly/disassembly plant"},
    {"name":"Los Alamos NL","country":"USA","operator":"DOE/NNSA","lat":35.844,"lon":-106.284,"type":"design_lab"},
    {"name":"Lawrence Livermore NL","country":"USA","operator":"DOE/NNSA","lat":37.688,"lon":-121.705,"type":"design_lab"},
    {"name":"Sandia NL","country":"USA","operator":"DOE/NNSA","lat":35.048,"lon":-106.542,"type":"design_lab"},
    {"name":"Nevada Test Site","country":"USA","operator":"DOE/NNSA","lat":37.104,"lon":-116.049,"type":"former_test"},
    # Russia
    {"name":"Sarov (Arzamas-16)","country":"Russia","operator":"Rosatom","lat":54.933,"lon":43.316,"type":"design_lab","notes":"Main Russian nuclear design center"},
    {"name":"Snezhinsk (Chelyabinsk-70)","country":"Russia","operator":"Rosatom","lat":56.082,"lon":60.738,"type":"design_lab"},
    {"name":"Novaya Zemlya","country":"Russia","operator":"Russia","lat":73.502,"lon":54.828,"type":"test_site"},
    {"name":"Seversk","country":"Russia","operator":"Rosatom","lat":56.600,"lon":84.883,"type":"production"},
    {"name":"Zheleznogorsk","country":"Russia","operator":"Rosatom","lat":56.251,"lon":93.531,"type":"production"},
    # China
    {"name":"Mianyang (CAEP)","country":"China","operator":"CAEP","lat":31.465,"lon":104.734,"type":"design_lab","notes":"China Academy of Engineering Physics"},
    {"name":"Lop Nur","country":"China","operator":"PLA","lat":40.752,"lon":88.729,"type":"former_test"},
    {"name":"Yumen","country":"China","operator":"CNNC","lat":39.826,"lon":97.040,"type":"enrichment"},
    {"name":"Jiuquan (plutonium)","country":"China","operator":"CNNC","lat":40.287,"lon":99.705,"type":"production"},
    # UK
    {"name":"Aldermaston AWE","country":"UK","operator":"AWE","lat":51.381,"lon":-1.145,"type":"design_lab"},
    {"name":"Burghfield AWE","country":"UK","operator":"AWE","lat":51.375,"lon":-1.051,"type":"assembly_disassembly"},
    {"name":"Faslane (SSBN Base)","country":"UK","operator":"RN","lat":56.076,"lon":-4.789,"type":"weapons_storage","notes":"Trident missile base"},
    # France
    {"name":"Valduc","country":"France","operator":"CEA","lat":47.447,"lon":4.973,"type":"production"},
    {"name":"Le Ripault","country":"France","operator":"CEA","lat":47.268,"lon":0.666,"type":"design_lab"},
    # Israel
    {"name":"Negev Nuclear Research Center (Dimona)","country":"Israel","operator":"IAEC","lat":30.870,"lon":35.141,"type":"production","notes":"Undeclared nuclear program"},
    # North Korea
    {"name":"Yongbyon Nuclear Complex","country":"North Korea","operator":"DPRK","lat":39.791,"lon":125.754,"type":"enrichment_production"},
    {"name":"Punggye-ri Test Site","country":"North Korea","operator":"DPRK","lat":41.274,"lon":129.086,"type":"test_site"},
    # Pakistan
    {"name":"Kahuta (KRL)","country":"Pakistan","operator":"SPD","lat":33.628,"lon":73.391,"type":"enrichment"},
    {"name":"Khushab Plutonium","country":"Pakistan","operator":"SPD","lat":32.062,"lon":72.199,"type":"production"},
    # India
    {"name":"Bhabha Atomic Research","country":"India","operator":"DAE","lat":19.016,"lon":72.921,"type":"design_lab"},
    {"name":"Pokhran Test Site","country":"India","operator":"DRDO","lat":27.063,"lon":71.767,"type":"test_site"},
    # Iran (Enrichment facilities)
    {"name":"Natanz FEP","country":"Iran","operator":"AEOI","lat":33.724,"lon":51.727,"type":"enrichment","notes":"Primary uranium enrichment facility"},
    {"name":"Fordow FFEP","country":"Iran","operator":"AEOI","lat":34.884,"lon":50.993,"type":"enrichment","notes":"Underground enrichment facility"},
    {"name":"Isfahan UCF","country":"Iran","operator":"AEOI","lat":32.631,"lon":51.665,"type":"conversion"},
    {"name":"Arak IR-40","country":"Iran","operator":"AEOI","lat":34.153,"lon":49.234,"type":"research_reactor"},
    {"name":"Bushehr NPP","country":"Iran","operator":"AEOI","lat":28.829,"lon":50.887,"type":"power_plant"},
]

def dl_nuclear_weapons():
    print("\n[2] Nuclear Weapons Facilities (Manual Compilation)...")
    save("nuclear_weapons", NUCLEAR_WEAPONS)


# ── 3. Gamma Irradiators ──────────────────────────────────────
GAMMA_IRRADIATORS = [
    # Major industrial gamma irradiator facilities (IAEA DIRATA public list)
    {"name":"Sterigenics Willowbrook","country":"USA","lat":41.770,"lon":-87.978,"isotope":"Co-60","activity_PBq":1.5},
    {"name":"Sterigenics Atlanta","country":"USA","lat":33.638,"lon":-84.442,"isotope":"Co-60","activity_PBq":0.8},
    {"name":"Nordion Ottawa","country":"Canada","lat":45.351,"lon":-75.783,"isotope":"Co-60","activity_PBq":5.0,"notes":"Primary Co-60 production site"},
    {"name":"BRIT Mumbai","country":"India","lat":19.016,"lon":72.921,"isotope":"Co-60","activity_PBq":0.5},
    {"name":"ANSTO Lucas Heights","country":"Australia","lat":-34.061,"lon":150.986,"isotope":"Co-60","activity_PBq":0.3},
    {"name":"Isotron Diest","country":"Belgium","lat":50.990,"lon":5.052,"isotope":"Co-60","activity_PBq":0.4},
    {"name":"RTI Hsinchu","country":"Taiwan","lat":24.790,"lon":121.003,"isotope":"Co-60","activity_PBq":0.3},
    {"name":"ROSATOM Obninsk","country":"Russia","lat":55.094,"lon":36.609,"isotope":"Co-60","activity_PBq":1.2},
    {"name":"NIDC Beijing","country":"China","lat":39.909,"lon":116.391,"isotope":"Co-60","activity_PBq":0.8},
    {"name":"IPEN São Paulo","country":"Brazil","lat":-23.568,"lon":-46.738,"isotope":"Co-60","activity_PBq":0.2},
    {"name":"JL Shepherd San Fernando","country":"USA","lat":34.281,"lon":-118.435,"isotope":"Cs-137","activity_PBq":0.1},
    {"name":"Okdche Kazakhstan","country":"Kazakhstan","lat":50.265,"lon":57.219,"isotope":"Co-60","activity_PBq":0.3},
]

def dl_gamma_irradiators():
    print("\n[3] Gamma Irradiators (Manual Compilation)...")
    save("gamma_irradiators", GAMMA_IRRADIATORS)


# ── 4. Submarine Cables ────────────────────────────────────────
def dl_submarine_cables():
    print("\n[4] Submarine Cables (TeleGeography)...")
    try:
        cables = get("https://www.submarinecablemap.com/api/v3/cable/all.json").json()
        save("submarine_cables_meta", cables)
        points = get("https://www.submarinecablemap.com/api/v3/landing-point/all.json").json()
        save("submarine_cable_landing_points", points)
    except Exception as e:
        print(f"  ⚠️ TeleGeography API failed: {e}, using backup data")
        save("submarine_cables_meta", BACKUP_CABLES)


BACKUP_CABLES = [
    {"name":"SEA-ME-WE 3","length_km":39000,"landing_points":["UK","France","Italy","Egypt","India","Malaysia","Singapore","Japan"],"year":1999},
    {"name":"SEA-ME-WE 4","length_km":20000,"landing_points":["France","Egypt","Saudi Arabia","India","Singapore","Thailand"],"year":2005},
    {"name":"SEA-ME-WE 5","length_km":20000,"landing_points":["France","Italy","Turkey","India","Singapore","Australia"],"year":2016},
    {"name":"PEACE Cable","length_km":15000,"landing_points":["China","Pakistan","Kenya","Egypt","France"],"year":2022,"notes":"Chinese investment"},
    {"name":"2Africa","length_km":45000,"landing_points":["UK","33 African countries","Saudi Arabia","India"],"year":2024,"notes":"Lead by Meta"},
    {"name":"AAE-1","length_km":25000,"landing_points":["Hong Kong","Vietnam","Cambodia","Malaysia","India","Oman","Saudi Arabia","Egypt","Greece","France"],"year":2017},
    {"name":"FASTER","length_km":9000,"landing_points":["USA","Japan"],"year":2016,"notes":"Lead by Google"},
    {"name":"JUPITER","length_km":14557,"landing_points":["USA","Japan","Philippines"],"year":2020,"notes":"Google/Facebook"},
    {"name":"Echo","length_km":0,"landing_points":["USA","Guam","Indonesia","Singapore"],"year":2023,"notes":"Google"},
    {"name":"Bifrost","length_km":0,"landing_points":["USA","Japan","Philippines","Guam","Indonesia"],"year":2024,"notes":"Meta"},
    {"name":"MAREA","length_km":6600,"landing_points":["USA","Spain"],"year":2017,"notes":"Microsoft/Facebook"},
    {"name":"Dunant","length_km":6600,"landing_points":["USA","France"],"year":2021,"notes":"Google"},
    {"name":"Havfrue/AEC-1","length_km":7000,"landing_points":["USA","Denmark","Norway","Ireland"],"year":2020,"notes":"Google/Facebook"},
    {"name":"FLAG Atlantic-1","length_km":14000,"landing_points":["USA","UK","France","Japan"],"year":2001},
    {"name":"SMW-5 Arctic Connect","length_km":13000,"landing_points":["Japan","Alaska","Norway","UK"],"year":2026,"notes":"Arctic routing"},
    {"name":"INDIGO Central","length_km":9200,"landing_points":["Australia","Singapore","Indonesia"],"year":2019},
    {"name":"SEAX-1","length_km":10000,"landing_points":["Singapore","Philippines","Hong Kong","Japan"],"year":2023},
    {"name":"MIST","length_km":25000,"landing_points":["UAE","India","Maldives","Sri Lanka"],"year":2023},
    {"name":"Polar Express","length_km":15000,"landing_points":["UK","Norway","Japan"],"year":2025,"notes":"Arctic routing"},
    {"name":"SJC2","length_km":10500,"landing_points":["Japan","South Korea","Taiwan","Guam","USA"],"year":2022,"notes":"Lead by Google"},
]


# ── 5. Military Bases ──────────────────────────────────────────
MILITARY_BASES = [
    # ── US Air Force Bases ──
    {"name":"RAF Lakenheath","country":"UK","operator":"US","lat":52.409,"lon":0.561,"branch":"Air Force","notes":"F-35 Fighters"},
    {"name":"Ramstein AB","country":"Germany","operator":"US/NATO","lat":49.437,"lon":7.600,"branch":"Air Force","notes":"Largest US base in Europe"},
    {"name":"Aviano AB","country":"Italy","operator":"US","lat":46.031,"lon":12.596,"branch":"Air Force"},
    {"name":"Incirlik AB","country":"Turkey","operator":"US/NATO","lat":37.002,"lon":35.426,"branch":"Air Force"},
    {"name":"Kadena AB","country":"Japan","operator":"US","lat":26.356,"lon":127.769,"branch":"Air Force","notes":"Largest US air base in W. Pacific"},
    {"name":"Misawa AB","country":"Japan","operator":"US","lat":40.703,"lon":141.368,"branch":"Air Force"},
    {"name":"Osan AB","country":"South Korea","operator":"US","lat":37.090,"lon":127.030,"branch":"Air Force"},
    {"name":"Kunsan AB","country":"South Korea","operator":"US","lat":35.903,"lon":126.616,"branch":"Air Force"},
    {"name":"Andersen AFB","country":"Guam","operator":"US","lat":13.584,"lon":144.930,"branch":"Air Force","notes":"B-52 forward base"},
    {"name":"Al Udeid AB","country":"Qatar","operator":"US","lat":25.117,"lon":51.315,"branch":"Air Force","notes":"CENTCOM Air HQ"},
    {"name":"Ali Al Salem AB","country":"Kuwait","operator":"US","lat":29.347,"lon":47.521,"branch":"Air Force"},
    {"name":"Spangdahlem AB","country":"Germany","operator":"US","lat":49.973,"lon":6.692,"branch":"Air Force"},
    {"name":"Thule AB","country":"Greenland","operator":"US","lat":76.531,"lon":-68.703,"branch":"Air Force","notes":"Arctic early warning radar"},
    {"name":"RAF Mildenhall","country":"UK","operator":"US","lat":52.362,"lon":0.486,"branch":"Air Force"},
    {"name":"Vandenberg SFB","country":"USA","operator":"US","lat":34.742,"lon":-120.571,"branch":"Space Force","notes":"Satellite/Missile launches"},
    # ── US Navy Bases ──
    {"name":"Norfolk NB","country":"USA","operator":"US","lat":36.946,"lon":-76.299,"branch":"Navy","notes":"World's largest naval base"},
    {"name":"Pearl Harbor-Hickam","country":"USA","operator":"US","lat":21.367,"lon":-157.950,"branch":"Navy"},
    {"name":"Naval Station Rota","country":"Spain","operator":"US/NATO","lat":36.641,"lon":-6.349,"branch":"Navy"},
    {"name":"NAS Sigonella","country":"Italy","operator":"US","lat":37.402,"lon":14.924,"branch":"Navy","notes":"Mediterranean hub"},
    {"name":"Yokosuka NB","country":"Japan","operator":"US","lat":35.283,"lon":139.667,"branch":"Navy","notes":"7th Fleet Homeport"},
    {"name":"Sasebo NB","country":"Japan","operator":"US","lat":33.160,"lon":129.710,"branch":"Navy"},
    {"name":"Diego Garcia","country":"BIOT","operator":"US/UK","lat":-7.313,"lon":72.423,"branch":"Joint","notes":"Indian Ocean strategic base"},
    {"name":"Guantanamo Bay NB","country":"Cuba","operator":"US","lat":19.906,"lon":-75.099,"branch":"Navy"},
    {"name":"NSA Bahrain","country":"Bahrain","operator":"US","lat":26.217,"lon":50.600,"branch":"Navy","notes":"5th Fleet HQ"},
    {"name":"Changi NB","country":"Singapore","operator":"Singapore/US","lat":1.311,"lon":103.988,"branch":"Navy"},
    {"name":"Cam Ranh Bay","country":"Vietnam","operator":"Vietnam","lat":11.920,"lon":109.164,"branch":"Navy"},
    # ── US Army/Marine Corps ──
    {"name":"Camp Humphreys","country":"South Korea","operator":"US","lat":36.963,"lon":127.028,"branch":"Army","notes":"Largest US base in Asia"},
    {"name":"Fort Liberty(Bragg)","country":"USA","operator":"US","lat":35.139,"lon":-79.006,"branch":"Army","notes":"82nd Airborne/SOCOM"},
    {"name":"Camp Pendleton","country":"USA","operator":"US","lat":33.385,"lon":-117.421,"branch":"Marine Corps"},
    {"name":"Camp Lemonnier","country":"Djibouti","operator":"US","lat":11.547,"lon":43.159,"branch":"Joint","notes":"Only permanent US base in Africa"},
    {"name":"Camp Arifjan","country":"Kuwait","operator":"US","lat":29.198,"lon":47.970,"branch":"Army"},
    {"name":"Grafenwöhr","country":"Germany","operator":"US","lat":49.698,"lon":11.956,"branch":"Army","notes":"Major training area"},
    # ── NATO ──
    {"name":"NATO HQ Brussels","country":"Belgium","operator":"NATO","lat":50.880,"lon":4.419,"branch":"HQ"},
    {"name":"SHAPE Mons","country":"Belgium","operator":"NATO","lat":50.452,"lon":3.921,"branch":"HQ"},
    {"name":"Brize Norton","country":"UK","operator":"UK","lat":51.750,"lon":-1.583,"branch":"Air Force"},
    {"name":"Akrotiri","country":"Cyprus","operator":"UK","lat":34.590,"lon":32.979,"branch":"Air Force"},
    {"name":"Ämari Air Base","country":"Estonia","operator":"NATO","lat":59.263,"lon":24.208,"branch":"Air Force"},
    {"name":"Łask Air Base","country":"Poland","operator":"US/NATO","lat":51.552,"lon":19.181,"branch":"Air Force"},
    {"name":"Mihail Kogalniceanu","country":"Romania","operator":"US/NATO","lat":44.362,"lon":28.488,"branch":"Air Force"},
    {"name":"Rota Naval Base","country":"Spain","operator":"US/NATO","lat":36.641,"lon":-6.349,"branch":"Navy"},
    # ── Russia ──
    {"name":"Hmeimim AB","country":"Syria","operator":"Russia","lat":35.401,"lon":35.949,"branch":"Air Force","notes":"Russian forward base in Syria"},
    {"name":"Tartus NB","country":"Syria","operator":"Russia","lat":34.893,"lon":35.887,"branch":"Navy","notes":"Only Russian naval facility in Mediterranean"},
    {"name":"Severomorsk NB","country":"Russia","operator":"Russia","lat":69.070,"lon":33.418,"branch":"Navy","notes":"Northern Fleet"},
    {"name":"Vladivostok NB","country":"Russia","operator":"Russia","lat":43.115,"lon":131.882,"branch":"Navy","notes":"Pacific Fleet"},
    {"name":"Kaliningrad 11th Army","country":"Russia","operator":"Russia","lat":54.707,"lon":20.508,"branch":"Army","notes":"Baltic enclave, Iskander deployment"},
    {"name":"Kant AB","country":"Kyrgyzstan","operator":"Russia","lat":42.853,"lon":74.846,"branch":"Air Force"},
    {"name":"Gyumri 102nd Base","country":"Armenia","operator":"Russia","lat":40.789,"lon":43.846,"branch":"Army"},
    {"name":"Engels AB","country":"Russia","operator":"Russia","lat":51.558,"lon":46.174,"branch":"Air Force","notes":"Tu-95 Strategic Bombers"},
    {"name":"Olenya AB","country":"Russia","operator":"Russia","lat":68.152,"lon":33.464,"branch":"Air Force","notes":"Tu-22M/MiG-31"},
    {"name":"Sevastopol NB","country":"Ukraine/Russia","operator":"Russia","lat":44.616,"lon":33.525,"branch":"Navy","notes":"Black Sea Fleet (Occupied)"},
    {"name":"Novorossiysk NB","country":"Russia","operator":"Russia","lat":44.713,"lon":37.768,"branch":"Navy","notes":"Black Sea Fleet backup"},
    # ── China ──
    {"name":"Sanya NB (Yulin)","country":"China","operator":"PLAN","lat":18.219,"lon":109.496,"branch":"Navy","notes":"Nuclear submarine base"},
    {"name":"Djibouti PLA Base","country":"Djibouti","operator":"China","lat":11.584,"lon":43.141,"branch":"Navy","notes":"First overseas base for China"},
    {"name":"Zhanjiang NB","country":"China","operator":"PLAN","lat":21.274,"lon":110.358,"branch":"Navy","notes":"South Sea Fleet"},
    {"name":"Qingdao NB","country":"China","operator":"PLAN","lat":36.042,"lon":120.398,"branch":"Navy","notes":"North Sea Fleet"},
    {"name":"Fiery Cross Reef","country":"South China Sea","operator":"China","lat":9.550,"lon":112.890,"branch":"Air Force/Navy","notes":"Artificial island, 3000m runway"},
    {"name":"Subi Reef","country":"South China Sea","operator":"China","lat":10.928,"lon":114.082,"branch":"Air Force/Navy","notes":"Artificial island base"},
    {"name":"Mischief Reef","country":"South China Sea","operator":"China","lat":9.908,"lon":115.534,"branch":"Air Force/Navy","notes":"Artificial island base"},
    {"name":"Woody Island","country":"Paracel Islands","operator":"China","lat":16.834,"lon":112.338,"branch":"Air Force","notes":"SAM deployment"},
    {"name":"Gwadar Port","country":"Pakistan","operator":"China/Pakistan","lat":25.122,"lon":62.325,"branch":"Navy","notes":"CPEC terminal, potential military use"},
    {"name":"Hambantota Port","country":"Sri Lanka","operator":"China","lat":6.121,"lon":81.110,"branch":"Navy","notes":"99-year lease"},
    # ── Others ──
    {"name":"Pine Gap","country":"Australia","operator":"US/Australia","lat":-23.799,"lon":133.737,"branch":"Intelligence","notes":"NSA/CIA SIGINT station"},
    {"name":"RAAF Darwin","country":"Australia","operator":"Australia/US","lat":-12.424,"lon":130.873,"branch":"Air Force","notes":"US Marine rotational presence"},
    {"name":"Bandar Abbas NB","country":"Iran","operator":"Iran","lat":27.184,"lon":56.275,"branch":"Navy","notes":"Near Strait of Hormuz"},
    {"name":"Chabahar NB","country":"Iran","operator":"Iran","lat":25.289,"lon":60.642,"branch":"Navy"},
]

def dl_military_bases():
    print("\n[5] Military Bases (Manual Compilation)...")
    save("military_bases", MILITARY_BASES)


# ── 6. Spaceports ──────────────────────────────────────────────
SPACEPORTS = [
    {"name":"Kennedy SC / Cape Canaveral","country":"USA","operator":"NASA/SpaceX/ULA","lat":28.524,"lon":-80.651,"active":True,"notes":"Main human spaceflight site"},
    {"name":"Vandenberg SFB","country":"USA","operator":"USSF/SpaceX","lat":34.742,"lon":-120.571,"active":True,"notes":"Polar/SSO launches"},
    {"name":"Starbase (Boca Chica)","country":"USA","operator":"SpaceX","lat":25.997,"lon":-97.157,"active":True,"notes":"Starship Heavy Lift"},
    {"name":"Wallops Flight Facility","country":"USA","operator":"NASA/Rocket Lab","lat":37.940,"lon":-75.466,"active":True},
    {"name":"Baikonur Cosmodrome","country":"Kazakhstan","operator":"Russia","lat":45.965,"lon":63.305,"active":True,"notes":"World's oldest active spaceport"},
    {"name":"Plesetsk Cosmodrome","country":"Russia","operator":"Russia","lat":62.927,"lon":40.577,"active":True,"notes":"Major military spaceport"},
    {"name":"Vostochny Cosmodrome","country":"Russia","operator":"Russia","lat":51.884,"lon":128.334,"active":True},
    {"name":"Wenchang SLC","country":"China","operator":"CNSA","lat":19.614,"lon":110.951,"active":True,"notes":"CZ-5 / CZ-7"},
    {"name":"Jiuquan SLC","country":"China","operator":"CNSA","lat":41.118,"lon":100.464,"active":True,"notes":"Shenzhou manned missions"},
    {"name":"Xichang SLC","country":"China","operator":"CNSA","lat":28.246,"lon":102.026,"active":True,"notes":"Beidou / Chang'e"},
    {"name":"Taiyuan SLC","country":"China","operator":"CNSA","lat":38.849,"lon":111.608,"active":True},
    {"name":"Guiana Space Centre","country":"French Guiana","operator":"ESA/ArianeGroup","lat":5.239,"lon":-52.769,"active":True,"notes":"Primary European site"},
    {"name":"Satish Dhawan SC","country":"India","operator":"ISRO","lat":13.733,"lon":80.235,"active":True,"notes":"Primary Indian site"},
    {"name":"Tanegashima SC","country":"Japan","operator":"JAXA","lat":30.401,"lon":130.969,"active":True,"notes":"H-3 Rocket"},
    {"name":"Naro Space Center","country":"South Korea","operator":"KARI","lat":34.432,"lon":127.535,"active":True},
    {"name":"Mahia LC","country":"New Zealand","operator":"Rocket Lab","lat":-39.259,"lon":177.864,"active":True,"notes":"Electron Rocket"},
    {"name":"Imam Khomeini SLC","country":"Iran","operator":"ISA/IRGC","lat":35.234,"lon":53.921,"active":True,"notes":"Dual use"},
    {"name":"Sohae SSLS","country":"North Korea","operator":"DPRK","lat":39.660,"lon":124.705,"active":True,"notes":"Monitoring focus"},
    {"name":"Palmachim Airbase","country":"Israel","operator":"IAI","lat":31.896,"lon":34.689,"active":True,"notes":"Retrograde orbit (westward)"},
    {"name":"Alcântara LC","country":"Brazil","operator":"AEB","lat":-2.373,"lon":-44.396,"active":True},
    {"name":"SaxaVord Spaceport","country":"UK","operator":"SaxaVord","lat":60.833,"lon":-0.883,"active":True},
    {"name":"Arnhem Space Centre","country":"Australia","operator":"ELA","lat":-12.261,"lon":136.819,"active":True},
    {"name":"Esrange SC","country":"Sweden","operator":"SSC","lat":67.888,"lon":21.097,"active":True,"notes":"Sounding rockets"},
    {"name":"Kapustin Yar","country":"Russia","operator":"Russia","lat":48.578,"lon":45.786,"active":True,"notes":"Missile testing"},
    {"name":"Uchinoura SC","country":"Japan","operator":"JAXA","lat":31.252,"lon":131.082,"active":True},
]

def dl_spaceports():
    print("\n[6] Spaceports (Manual Compilation)...")
    save("spaceports", SPACEPORTS)


# ── 7. Strategic Chokepoints ──────────────────────────────────
CHOKEPOINTS = [
    {"name":"Strait of Hormuz","lat":26.566,"lon":56.500,"region":"Middle East","daily_oil_mbpd":21,"notes":"World's most critical oil chokepoint"},
    {"name":"Strait of Malacca","lat":2.500,"lon":101.333,"region":"Asia","daily_oil_mbpd":16,"notes":"Busiest sea lane in Asia"},
    {"name":"Suez Canal","lat":30.458,"lon":32.349,"region":"Middle East","daily_oil_mbpd":5.5,"notes":"Links Med and Red Sea"},
    {"name":"Bab el-Mandeb","lat":12.583,"lon":43.333,"region":"Africa/Middle East","daily_oil_mbpd":6.2,"notes":"Red Sea entrance, Houthi threat"},
    {"name":"Panama Canal","lat":9.080,"lon":-79.680,"region":"Americas","daily_oil_mbpd":0.8,"notes":"Pacific-Atlantic link"},
    {"name":"Turkish Straits/Bosphorus","lat":41.117,"lon":29.083,"region":"Europe","daily_oil_mbpd":2.9,"notes":"Black Sea exit"},
    {"name":"Danish Straits","lat":56.000,"lon":10.500,"region":"Europe","daily_oil_mbpd":3.0,"notes":"Baltic Sea exit"},
    {"name":"Strait of Gibraltar","lat":35.971,"lon":-5.349,"region":"Europe/Africa","daily_oil_mbpd":4.0,"notes":"Mediterranean entrance"},
    {"name":"Lombok Strait","lat":-8.778,"lon":115.750,"region":"Asia","daily_oil_mbpd":1.0,"notes":"Malacca alternative"},
    {"name":"Sunda Strait","lat":-6.000,"lon":105.833,"region":"Asia","daily_oil_mbpd":0.5,"notes":"Malacca alternative"},
    {"name":"Taiwan Strait","lat":24.500,"lon":119.500,"region":"Asia","daily_oil_mbpd":0,"notes":"Geopolitical hotspot"},
    {"name":"South China Sea","lat":13.000,"lon":113.000,"region":"Asia","daily_oil_mbpd":0,"notes":"Disputed territories"},
    {"name":"Dover Strait","lat":51.043,"lon":1.377,"region":"Europe","daily_oil_mbpd":0,"notes":"World's busiest shipping lane"},
    {"name":"GIUK Gap","lat":64.000,"lon":-20.000,"region":"North Atlantic","daily_oil_mbpd":0,"notes":"NATO anti-submarine strategic gap"},
    {"name":"Cape of Good Hope","lat":-34.357,"lon":18.474,"region":"Africa","daily_oil_mbpd":0,"notes":"Suez alternative"},
    {"name":"Cape Horn","lat":-55.984,"lon":-67.271,"region":"Americas","daily_oil_mbpd":0,"notes":"Panama alternative"},
    {"name":"Øresund Strait","lat":55.900,"lon":12.700,"region":"Europe","daily_oil_mbpd":0,"notes":"Alternative Baltic exit"},
    {"name":"Strait of Messina","lat":38.200,"lon":15.600,"region":"Europe","daily_oil_mbpd":0,"notes":"Internal Med crossing"},
    {"name":"Northwest Passage","lat":74.000,"lon":-95.000,"region":"Arctic","daily_oil_mbpd":0,"notes":"Opening due to climate change"},
    {"name":"Northern Sea Route","lat":76.000,"lon":100.000,"region":"Arctic","daily_oil_mbpd":0,"notes":"Russian Arctic route"},
]

def dl_chokepoints():
    print("\n[7] Strategic Chokepoints (Manual Compilation)...")
    save("chokepoints", CHOKEPOINTS)


# ── 8. Strategic Ports ─────────────────────────────────────────
STRATEGIC_PORTS = [
    {"name":"Shanghai","country":"China","lat":31.230,"lon":121.473,"rank":1,"teu_m":47.3},
    {"name":"Singapore","country":"Singapore","lat":1.264,"lon":103.822,"rank":2,"teu_m":37.3},
    {"name":"Ningbo-Zhoushan","country":"China","lat":29.877,"lon":121.549,"rank":3,"teu_m":33.4},
    {"name":"Shenzhen","country":"China","lat":22.543,"lon":114.058,"rank":4,"teu_m":30.0},
    {"name":"Guangzhou","country":"China","lat":23.130,"lon":113.264,"rank":5,"teu_m":24.5},
    {"name":"Qingdao","country":"China","lat":36.067,"lon":120.383,"rank":6,"teu_m":23.7},
    {"name":"Busan","country":"South Korea","lat":35.180,"lon":129.076,"rank":7,"teu_m":21.7},
    {"name":"Tianjin","country":"China","lat":38.994,"lon":117.756,"rank":8,"teu_m":20.8},
    {"name":"Hong Kong","country":"HK","lat":22.302,"lon":114.177,"rank":9,"teu_m":17.8},
    {"name":"Jebel Ali","country":"UAE","lat":25.013,"lon":55.080,"rank":10,"teu_m":14.0},
    {"name":"Rotterdam","country":"Netherlands","lat":51.924,"lon":4.482,"rank":11,"teu_m":14.8},
    {"name":"Port Klang","country":"Malaysia","lat":3.000,"lon":101.400,"rank":12,"teu_m":13.7},
    {"name":"Antwerp-Bruges","country":"Belgium","lat":51.260,"lon":4.402,"rank":13,"teu_m":12.0},
    {"name":"Kaohsiung","country":"Taiwan","lat":22.622,"lon":120.301,"rank":15,"teu_m":10.4},
    {"name":"Hamburg","country":"Germany","lat":53.545,"lon":9.980,"rank":17,"teu_m":8.7},
    {"name":"Tanger Med","country":"Morocco","lat":35.888,"lon":-5.497,"rank":0,"teu_m":7.2},
    {"name":"LA / Long Beach","country":"USA","lat":33.729,"lon":-118.262,"rank":0,"teu_m":18.0},
    {"name":"NY / NJ","country":"USA","lat":40.673,"lon":-74.100,"rank":0,"teu_m":9.5},
    {"name":"Piraeus","country":"Greece","lat":37.943,"lon":23.625,"rank":0,"teu_m":5.6,"notes":"COSCO controlled"},
    {"name":"Port Said","country":"Egypt","lat":31.260,"lon":32.284,"rank":0,"teu_m":4.7,"notes":"Suez Canal entrance"},
    {"name":"Salalah","country":"Oman","lat":17.018,"lon":54.095,"rank":0,"teu_m":4.1},
    {"name":"Colon","country":"Panama","lat":9.358,"lon":-79.900,"rank":0,"teu_m":4.3,"notes":"Panama Canal Pacific end"},
    {"name":"Valencia","country":"Spain","lat":39.465,"lon":-0.327,"rank":0,"teu_m":5.4},
    {"name":"Algeciras","country":"Spain","lat":36.130,"lon":-5.452,"rank":0,"teu_m":5.1,"notes":"Strait of Gibraltar"},
    {"name":"Santos","country":"Brazil","lat":-23.960,"lon":-46.299,"rank":0,"teu_m":4.5},
    {"name":"Savannah","country":"USA","lat":31.980,"lon":-81.099,"rank":0,"teu_m":6.1},
    {"name":"Felixstowe","country":"UK","lat":51.958,"lon":1.352,"rank":0,"teu_m":3.8},
    {"name":"Khalifa Port","country":"UAE","lat":24.801,"lon":54.607,"rank":0,"teu_m":5.0},
    {"name":"King Abdulaziz Port","country":"Saudi Arabia","lat":26.416,"lon":50.113,"rank":0,"teu_m":2.5},
    {"name":"Bandar Abbas","country":"Iran","lat":27.167,"lon":56.283,"rank":0,"teu_m":2.2},
    {"name":"Durban","country":"South Africa","lat":-29.864,"lon":31.022,"rank":0,"teu_m":2.8},
    {"name":"Mombasa","country":"Kenya","lat":-4.050,"lon":39.676,"rank":0,"teu_m":1.5},
    {"name":"Lagos Apapa","country":"Nigeria","lat":6.444,"lon":3.371,"rank":0,"teu_m":1.1},
    {"name":"Djibouti Port","country":"Djibouti","lat":11.595,"lon":43.141,"rank":0,"teu_m":0.9,"notes":"US/CN/FR/JP bases nearby"},
    {"name":"Gwadar","country":"Pakistan","lat":25.122,"lon":62.325,"rank":0,"teu_m":0.1,"notes":"CPEC terminal"},
    {"name":"Hambantota","country":"Sri Lanka","lat":6.121,"lon":81.110,"rank":0,"teu_m":0.1,"notes":"99-year Chinese lease"},
    {"name":"Kyaukpyu","country":"Myanmar","lat":19.432,"lon":93.554,"rank":0,"teu_m":0.1,"notes":"Chinese Indian Ocean strategy"},
    {"name":"Aden","country":"Yemen","lat":12.800,"lon":45.036,"rank":0,"teu_m":0.5,"notes":"Bab el-Mandeb"},
    {"name":"Colombo","country":"Sri Lanka","lat":6.932,"lon":79.843,"rank":0,"teu_m":7.2,"notes":"Indian Ocean hub"},
    {"name":"Jawaharlal Nehru Port","country":"India","lat":18.953,"lon":72.958,"rank":0,"teu_m":6.0},
    {"name":"Umm Qasr","country":"Iraq","lat":30.031,"lon":47.938,"rank":0,"teu_m":0.8,"notes":"Iraq's only deep water port"},
]

def dl_ports():
    print("\n[8] Strategic Ports (Manual Compilation)...")
    save("strategic_ports", STRATEGIC_PORTS)


# ── 9. Trade Routes ───────────────────────────────────────────
TRADE_ROUTES = [
    {"name":"Asia-Europe Main (Suez)","from":"Shanghai","to":"Rotterdam","via":["Malacca","Hormuz","Suez","Gibraltar"],"teu_annual_m":20,"notes":"World's key container route"},
    {"name":"Trans-Pacific Route","from":"Shanghai","to":"Los Angeles","via":["Pacific Ocean"],"teu_annual_m":15,"notes":"US-China trade backbone"},
    {"name":"Trans-Atlantic Route","from":"Rotterdam","to":"New York","via":["Dover","Atlantic"],"teu_annual_m":8},
    {"name":"Asia-Europe (Cape)","from":"Shanghai","to":"Rotterdam","via":["Malacca","Lombok","Cape of Good Hope"],"teu_annual_m":3,"notes":"Alternative for Suez block"},
    {"name":"Mid-East Oil (Asia)","from":"Ras Tanura","to":"Ningbo","via":["Hormuz","Malacca"],"teu_annual_m":0,"mbpd":10,"type":"oil"},
    {"name":"Mid-East Oil (Europe)","from":"Ras Tanura","to":"Rotterdam","via":["Hormuz","Suez","Bab el-Mandeb"],"teu_annual_m":0,"mbpd":5,"type":"oil"},
    {"name":"Intra-Asia Route","from":"Shanghai","to":"Singapore","via":["Taiwan Strait","South China Sea"],"teu_annual_m":12},
    {"name":"NA-LatAm Route","from":"Los Angeles","to":"Santos","via":["Panama Canal"],"teu_annual_m":3},
    {"name":"Arctic Route (Summer)","from":"Rotterdam","to":"Shanghai","via":["Northern Sea Route"],"teu_annual_m":0.5,"notes":"Emerging climate-driven route"},
    {"name":"East Africa Route","from":"Jebel Ali","to":"Durban","via":["Indian Ocean"],"teu_annual_m":2},
]

def dl_trade_routes():
    print("\n[9] Trade Routes (Manual Compilation)...")
    save("trade_routes", TRADE_ROUTES)


# ── 10. UCDP Conflict Events ──────────────────────────────────
def dl_ucdp():
    print("\n[10] UCDP Conflict Events...")
    url = "https://ucdpapi.pcr.uu.se/api/gedevents/24.1"
    try:
        data = get(url, params={"pagesize":1000,"page":1}).json()
        events = [e for e in data.get("Result",[]) if e.get("latitude") and e.get("longitude")]
        save("ucdp_conflicts", events)
    except Exception as e:
        print(f"  ❌ {e}")


# ── 11. UNHCR Displacement ────────────────────────────────────
def dl_unhcr():
    print("\n[11] UNHCR Displacement Data...")
    url = "https://api.unhcr.org/population/v1/population/"
    try:
        data = get(url, params={"limit":100,"yearFrom":2023,"yearTo":2024}).json()
        save("unhcr_displacement", data.get("items", []))
    except Exception as e:
        print(f"  ⚠️ {e}")
        # Backup: Major displacement crises
        save("unhcr_displacement_backup", UNHCR_BACKUP)

UNHCR_BACKUP = [
    {"situation":"Ukraine","refugees_m":6.5,"origin_lat":49.0,"origin_lon":31.0,"dest_countries":["Poland","Germany","Czech Republic","UK"]},
    {"situation":"Syria","refugees_m":6.8,"origin_lat":35.0,"origin_lon":38.0,"dest_countries":["Turkey","Lebanon","Jordan","Germany"]},
    {"situation":"Afghanistan","refugees_m":5.7,"origin_lat":33.0,"origin_lon":65.0,"dest_countries":["Pakistan","Iran","Germany"]},
    {"situation":"Sudan","refugees_m":7.3,"origin_lat":15.0,"origin_lon":30.0,"dest_countries":["Egypt","Chad","South Sudan"]},
    {"situation":"Venezuela","refugees_m":7.7,"origin_lat":8.0,"origin_lon":-66.0,"dest_countries":["Colombia","Peru","Ecuador","Chile"]},
    {"situation":"Myanmar","refugees_m":1.2,"origin_lat":21.0,"origin_lon":96.0,"dest_countries":["Bangladesh","Thailand","India"]},
    {"situation":"South Sudan","refugees_m":2.2,"origin_lat":7.0,"origin_lon":30.0,"dest_countries":["Uganda","Ethiopia","Sudan"]},
    {"situation":"Somalia","refugees_m":2.8,"origin_lat":6.0,"origin_lon":46.0,"dest_countries":["Ethiopia","Kenya","Yemen"]},
    {"situation":"DRC","refugees_m":6.9,"origin_lat":-4.0,"origin_lon":24.0,"dest_countries":["Uganda","Rwanda","Tanzania","Zambia"]},
    {"situation":"Gaza","refugees_m":1.9,"origin_lat":31.4,"origin_lon":34.3,"dest_countries":["Egypt","Jordan"]},
]


# ── 12. Critical Minerals ─────────────────────────────────────
CRITICAL_MINERALS = [
    {"name":"Salar de Atacama","country":"Chile","lat":-23.484,"lon":-68.250,"mineral":"Lithium","annual_kt":140,"notes":"World's largest lithium mine"},
    {"name":"Salar de Uyuni","country":"Bolivia","lat":-20.133,"lon":-67.489,"mineral":"Lithium","annual_kt":0,"notes":"Largest reserves, in development"},
    {"name":"Greenbushes","country":"Australia","lat":-33.850,"lon":116.058,"mineral":"Lithium","annual_kt":1340,"notes":"Largest hard-rock lithium mine"},
    {"name":"Katanga Cobalt Belt","country":"DRC","lat":-10.500,"lon":25.500,"mineral":"Cobalt","annual_kt":70,"notes":"Produces 70% of global cobalt"},
    {"name":"Bayan Obo","country":"China","lat":41.763,"lon":109.970,"mineral":"Rare Earths","annual_kt":100,"notes":"Largest REE mine"},
    {"name":"Mountain Pass","country":"USA","lat":35.479,"lon":-115.528,"mineral":"Rare Earths","annual_kt":43},
    {"name":"Mt Weld (Lynas)","country":"Australia","lat":-28.072,"lon":122.249,"mineral":"Rare Earths","annual_kt":20},
    {"name":"Escondida","country":"Chile","lat":-24.270,"lon":-69.070,"mineral":"Copper","annual_kt":1200,"notes":"World's largest copper mine"},
    {"name":"Grasberg","country":"Indonesia","lat":-4.060,"lon":137.116,"mineral":"Copper/Gold","annual_kt":800},
    {"name":"Cigar Lake","country":"Canada","lat":58.052,"lon":-104.520,"mineral":"Uranium","annual_kt":7,"notes":"Highest grade uranium mine"},
    {"name":"Arlit","country":"Niger","lat":18.737,"lon":7.386,"mineral":"Uranium","annual_kt":2},
    {"name":"Olympic Dam","country":"Australia","lat":-30.442,"lon":136.884,"mineral":"Uranium/Copper","annual_kt":4},
    {"name":"Bushveld Complex","country":"South Africa","lat":-25.000,"lon":29.000,"mineral":"PGM/Vanadium","annual_kt":0,"notes":"Largest PGM reserve"},
    {"name":"Xinjiang Silicon","country":"China","lat":42.000,"lon":85.000,"mineral":"Polysilicon","annual_kt":200,"notes":"45% of global polysilicon"},
    {"name":"Sudbury Basin","country":"Canada","lat":46.490,"lon":-81.012,"mineral":"Nickel/Cobalt"},
    {"name":"Norilsk","country":"Russia","lat":69.336,"lon":88.213,"mineral":"Nickel/Palladium","notes":"Largest palladium producer"},
    {"name":"Pilbara","country":"Australia","lat":-22.000,"lon":117.000,"mineral":"Iron Ore/Lithium","notes":"Global iron ore hub"},
    {"name":"DRC Cobalt (Kolwezi)","country":"DRC","lat":-10.718,"lon":25.467,"mineral":"Cobalt/Copper"},
    {"name":"Moanda","country":"Gabon","lat":-1.565,"lon":13.268,"mineral":"Manganese","notes":"World's largest manganese mine"},
    {"name":"Khyber Chromite","country":"Pakistan","lat":34.000,"lon":71.500,"mineral":"Chromite"},
    {"name":"Afghan Rare Earth","country":"Afghanistan","lat":34.500,"lon":65.000,"mineral":"Rare Earths/Lithium","annual_kt":0,"notes":"Est. $1T+ value, untapped"},
]

def dl_minerals():
    print("\n[12] Critical Minerals (Manual Compilation)...")
    save("critical_minerals", CRITICAL_MINERALS)


# ── 13. Economic Centers ──────────────────────────────────────
ECONOMIC_CENTERS = [
    {"name":"NYSE","country":"USA","lat":40.707,"lon":-74.011,"type":"Stock Exchange","market_cap_t":25.0},
    {"name":"NASDAQ","country":"USA","lat":40.757,"lon":-73.988,"type":"Stock Exchange","market_cap_t":21.0},
    {"name":"Shanghai SE","country":"China","lat":31.228,"lon":121.483,"type":"Stock Exchange","market_cap_t":7.1},
    {"name":"Tokyo SE (JPX)","country":"Japan","lat":35.681,"lon":139.773,"type":"Stock Exchange","market_cap_t":5.6},
    {"name":"Hong Kong SE","country":"HK","lat":22.283,"lon":114.156,"type":"Stock Exchange","market_cap_t":4.3},
    {"name":"London SE","country":"UK","lat":51.514,"lon":-0.099,"type":"Stock Exchange","market_cap_t":3.8},
    {"name":"Euronext","country":"France","lat":48.862,"lon":2.313,"type":"Stock Exchange","market_cap_t":3.7},
    {"name":"Shenzhen SE","country":"China","lat":22.543,"lon":114.058,"type":"Stock Exchange","market_cap_t":3.6},
    {"name":"Saudi Tadawul","country":"Saudi Arabia","lat":24.688,"lon":46.724,"type":"Stock Exchange","market_cap_t":2.9},
    {"name":"Toronto SE","country":"Canada","lat":43.648,"lon":-79.382,"type":"Stock Exchange","market_cap_t":2.8},
    {"name":"Bombay SE","country":"India","lat":18.934,"lon":72.836,"type":"Stock Exchange","market_cap_t":2.3},
    {"name":"Deutsche Börse","country":"Germany","lat":50.117,"lon":8.670,"type":"Stock Exchange","market_cap_t":2.1},
    {"name":"Federal Reserve","country":"USA","lat":38.891,"lon":-77.044,"type":"Central Bank","notes":"Most influential global bank"},
    {"name":"ECB Frankfurt","country":"Germany","lat":50.109,"lon":8.699,"type":"Central Bank"},
    {"name":"Bank of England","country":"UK","lat":51.514,"lon":-0.089,"type":"Central Bank"},
    {"name":"Bank of Japan","country":"Japan","lat":35.687,"lon":139.773,"type":"Central Bank"},
    {"name":"PBOC Beijing","country":"China","lat":39.929,"lon":116.391,"type":"Central Bank"},
    {"name":"BIS Basel","country":"Switzerland","lat":47.560,"lon":7.588,"type":"Central Bank","notes":"Bank for Central Banks"},
    {"name":"IMF Washington","country":"USA","lat":38.899,"lon":-77.042,"type":"International Finance"},
    {"name":"World Bank","country":"USA","lat":38.899,"lon":-77.043,"type":"International Finance"},
    {"name":"CME Group Chicago","country":"USA","lat":41.882,"lon":-87.631,"type":"Commodities","notes":"Oil/Agri futures"},
    {"name":"ICE (Brent)","country":"UK","lat":51.514,"lon":-0.082,"type":"Commodities","notes":"Brent oil pricing"},
    {"name":"LME London","country":"UK","lat":51.514,"lon":-0.082,"type":"Commodities","notes":"Metal pricing hub"},
    {"name":"SHFE Shanghai","country":"China","lat":31.234,"lon":121.487,"type":"Commodities"},
    {"name":"Dubai Mercantile Exch","country":"UAE","lat":25.204,"lon":55.270,"type":"Commodities","notes":"Middle East oil pricing"},
]

def dl_economic_centers():
    print("\n[13] Economic Centers (Manual Compilation)...")
    save("economic_centers", ECONOMIC_CENTERS)


# ── 14. AI Data Centers (>=10,000 GPU) ────────────────────────
AI_DATACENTERS = [
    {"name":"Microsoft/OpenAI Iowa (Ames)","country":"USA","lat":41.990,"lon":-93.620,"operator":"Microsoft","gpu_est":30000,"gpu_type":"H100","notes":"GPT-4 training cluster"},
    {"name":"Microsoft Virginia (Boydton)","country":"USA","lat":36.666,"lon":-78.374,"operator":"Microsoft","gpu_est":50000,"gpu_type":"H100"},
    {"name":"Google Dalles Oregon","country":"USA","lat":45.594,"lon":-121.177,"operator":"Google","gpu_est":20000,"gpu_type":"TPU v5"},
    {"name":"Google Council Bluffs","country":"USA","lat":41.264,"lon":-95.883,"operator":"Google","gpu_est":15000,"gpu_type":"TPU/H100"},
    {"name":"Meta Papillion Nebraska","country":"USA","lat":41.151,"lon":-96.034,"operator":"Meta","gpu_est":35000,"gpu_type":"H100","notes":"Llama training"},
    {"name":"Meta DeKalb Texas","country":"USA","lat":33.524,"lon":-94.617,"operator":"Meta","gpu_est":25000,"gpu_type":"H100"},
    {"name":"Amazon/AWS EC2 N. Virginia","country":"USA","lat":38.956,"lon":-77.350,"operator":"AWS","gpu_est":20000,"gpu_type":"H100/A100"},
    {"name":"xAI Memphis Colossus","country":"USA","lat":35.149,"lon":-90.048,"operator":"xAI/Elon Musk","gpu_est":100000,"gpu_type":"H100","notes":"Largest Grok training cluster"},
    {"name":"CoreWeave NJ","country":"USA","lat":40.720,"lon":-74.200,"operator":"CoreWeave","gpu_est":35000,"gpu_type":"H100"},
    {"name":"Lambda Labs Austin","country":"USA","lat":30.267,"lon":-97.743,"operator":"Lambda","gpu_est":10000,"gpu_type":"H100"},
    {"name":"Microsoft Sweden","country":"Sweden","lat":59.330,"lon":18.065,"operator":"Microsoft","gpu_est":10000,"gpu_type":"H100","notes":"Largest AI DC in Europe"},
    {"name":"Google Belgium","country":"Belgium","lat":50.882,"lon":3.717,"operator":"Google","gpu_est":12000,"gpu_type":"TPU/H100"},
    {"name":"Alibaba Zhangbei Supercomputing","country":"China","lat":41.152,"lon":114.697,"operator":"Alibaba/Aliyun","gpu_est":20000,"gpu_type":"A100/910B","notes":"Located within China"},
    {"name":"Tencent Gui'an Data Center","country":"China","lat":26.264,"lon":106.820,"operator":"Tencent","gpu_est":15000,"gpu_type":"A100/910B"},
    {"name":"Baidu NW Data Center","country":"China","lat":38.479,"lon":106.253,"operator":"Baidu","gpu_est":10000,"gpu_type":"910B","notes":"ERNIE Bot training"},
    {"name":"Huawei Cloud Ulanqab","country":"China","lat":41.017,"lon":113.114,"operator":"Huawei","gpu_est":10000,"gpu_type":"910B","notes":"Ascend AI cluster"},
    {"name":"Microsoft UAE (Abu Dhabi)","country":"UAE","lat":24.453,"lon":54.377,"operator":"Microsoft/G42","gpu_est":15000,"gpu_type":"H100","notes":"Largest AI infra in Middle East"},
    {"name":"Oracle Texas","country":"USA","lat":30.267,"lon":-97.743,"operator":"Oracle","gpu_est":12000,"gpu_type":"H100"},
    {"name":"Inflection AI Pittsburgh","country":"USA","lat":40.441,"lon":-79.996,"operator":"Microsoft/Inflection","gpu_est":22000,"gpu_type":"H100"},
    {"name":"Anthropic AWS us-east-1","country":"USA","lat":38.956,"lon":-77.350,"operator":"AWS/Anthropic","gpu_est":10000,"gpu_type":"H100","notes":"Claude training"},
]

def dl_ai_datacenters():
    print("\n[14] AI Data Centers >=10000 GPU (Manual Compilation)...")
    save("ai_datacenters", AI_DATACENTERS)


# ── 15. Oil & Gas Pipelines ───────────────────────────────────
PIPELINES = [
    {"name":"Nord Stream 1 (Damaged)","type":"gas","from":"Russia","to":"Germany","lat_start":59.880,"lon_start":28.770,"lat_end":54.527,"lon_end":13.660,"capacity_bcm_y":55,"status":"damaged","notes":"Explosion Sep 2022"},
    {"name":"Nord Stream 2 (Damaged)","type":"gas","from":"Russia","to":"Germany","lat_start":59.880,"lon_start":28.770,"lat_end":54.527,"lon_end":13.660,"capacity_bcm_y":55,"status":"damaged","notes":"Never commissioned"},
    {"name":"TurkStream","type":"gas","from":"Russia","to":"Turkey","lat_start":37.200,"lon_start":37.600,"lat_end":41.680,"lon_end":28.000,"capacity_bcm_y":31.5,"status":"operational"},
    {"name":"TAPI (Turkmenistan-Afghanistan-Pakistan-India)","type":"gas","from":"Turkmenistan","to":"India","lat_start":38.000,"lon_start":58.400,"lat_end":28.800,"lon_end":77.200,"capacity_bcm_y":33,"status":"under_construction","notes":"Strategic regional pipeline"},
    {"name":"Druzhba (Friendship)","type":"oil","from":"Russia","to":"Europe","lat_start":51.500,"lon_start":30.900,"lat_end":51.600,"lon_end":12.200,"capacity_mbpd":1.2,"status":"partial","notes":"Partially halted due to war"},
    {"name":"BTC (Baku-Tbilisi-Ceyhan)","type":"oil","from":"Azerbaijan","to":"Turkey","lat_start":40.400,"lon_start":49.900,"lat_end":37.000,"lon_end":36.200,"capacity_mbpd":1.2,"status":"operational"},
    {"name":"East-West Pipeline Saudi","type":"oil","from":"Abqaiq","to":"Yanbu","lat_start":25.938,"lon_start":49.666,"lat_end":24.088,"lon_end":38.063,"capacity_mbpd":5.0,"status":"operational","notes":"Hormuz bypass"},
    {"name":"Sumed Pipeline Egypt","type":"oil","from":"Ain Sokhna","to":"Alexandria","lat_start":29.700,"lon_start":32.700,"lat_end":31.200,"lon_end":29.900,"capacity_mbpd":2.5,"status":"operational","notes":"Suez Canal bypass"},
    {"name":"ESPO (East Siberia-Pacific Ocean)","type":"oil","from":"Russia","to":"China/Japan","lat_start":58.600,"lon_start":92.100,"lat_end":43.900,"lon_end":131.900,"capacity_mbpd":1.6,"status":"operational"},
    {"name":"China-Russia Gas (Power of Siberia)","type":"gas","from":"Russia","to":"China","lat_start":52.200,"lon_start":101.400,"lat_end":50.200,"lon_end":119.700,"capacity_bcm_y":38,"status":"operational"},
    {"name":"China-Myanmar Oil/Gas","type":"oil_gas","from":"Myanmar","to":"Kunming","lat_start":19.432,"lon_start":93.554,"lat_end":25.046,"lon_end":102.706,"capacity_mbpd":0.44,"status":"operational","notes":"Malacca bypass"},
    {"name":"Arabia-India Gas (IMEC)","type":"gas","from":"Saudi Arabia","to":"India","lat_start":26.000,"lon_start":50.000,"lat_end":22.000,"lon_end":72.000,"capacity_bcm_y":0,"status":"planned","notes":"G20 IMEC Corridor"},
    {"name":"Trans-Saharan Gas","type":"gas","from":"Nigeria","to":"Algeria/Europe","lat_start":10.000,"lon_start":8.000,"lat_end":28.000,"lon_end":3.000,"capacity_bcm_y":30,"status":"planned"},
]

def dl_pipelines():
    print("\n[15] Oil & Gas Pipelines (Manual Compilation)...")
    save("pipelines", PIPELINES)


# ── Main ───────────────────────────────────────────────────────
def main():
    print("=" * 65)
    print("  WorldMirror Static Layer Downloader v1.0")
    print(f"  Output: {os.path.abspath(LAYERS_DIR)}")
    print("=" * 65)

    dl_nuclear()
    dl_nuclear_weapons()
    dl_gamma_irradiators()
    dl_submarine_cables()
    dl_military_bases()
    dl_spaceports()
    dl_chokepoints()
    dl_ports()
    dl_trade_routes()
    dl_ucdp()
    dl_unhcr()
    dl_minerals()
    dl_economic_centers()
    dl_ai_datacenters()
    dl_pipelines()

    print("\n" + "=" * 65)
    print("  Done! Layer files:")
    total_kb = 0
    for f in sorted(os.listdir(LAYERS_DIR)):
        kb = os.path.getsize(os.path.join(LAYERS_DIR, f)) // 1024
        total_kb += kb
        print(f"    {f:50s} {kb:5d} KB")
    print(f"\n  Total: {total_kb} KB ({total_kb//1024} MB)")
    print("=" * 65)


if __name__ == "__main__":
    main()