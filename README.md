# Napta (نَبْتَة) — Egypt Edition
## Track B (The Body): Backend, Data Engineering, Voice AI & Expert Console
**NASA Space Apps Challenge 2026** — *Challenge: "Field Shift: Adapting Farms with NASA Data"*

---

## 1. Overview & Vision

**FieldWise AI (نَبْتَة)** is a climate-smart crop rotation and farm business planning platform engineered specifically for Egyptian farmers and agricultural advisers.

It combines:
- **NASA POWER** satellite agroclimatology data (temperatures, relative humidity, solar radiation, wind speed, precipitation).
- **ISRIC SoilGrids v2.0** spatial soil physical and chemical profiles (pH, organic carbon, clay/silt/sand texture, bulk density, CEC).
- **Deterministic Agricultural Decision Engine** calibrated to Egyptian Ministry of Agriculture (MALR) and FAO-56 benchmarks.
- **FastAPI Core Backend** exposing clean REST endpoints with strict provenance tracking.
- **Lightweight, Voice-First Farmer PWA** in Egyptian Arabic dialect (اللهجة الفلاحية المصرية) with large touch targets and tap fallback.
- **Expert Console (Streamlit)** for agronomists, researchers, and challenge judges.

### Guiding Principle: One Decision Engine, Two Presentations
All agronomic and financial calculations originate from the **same deterministic calculation engine**.
- The **Farmer PWA** communicates these results in accessible, spoken Egyptian Arabic.
- The **Expert Console** presents raw physics, layer depth-weighting, uncertainty intervals, and data provenance.

---

## 2. Architecture & Directory Layout

```text
Napta/
├── apps/
│   ├── expert_console/             # Streamlit Expert Agronomist Console
│   │   ├── pages/
│   │   │   ├── 1_🌾_Farm_Overview.py
│   │   │   ├── 2_🔬_Sources.py
│   │   │   └── 3_🎙️_Voice_Review.py
│   │   └── app.py
│   │
│   └── farmer_pwa/                 # Egyptian Arabic Voice-First Farmer PWA
│       ├── index.html
│       ├── manifest.json
│       ├── sw.js                   # Service worker for offline caching
│       ├── src/app.js
│       └── styles/main.css
│
├── src/
│   ├── api/
│   │   ├── main.py                 # FastAPI application entrypoint & static mount
│   │   ├── config.py               # Pydantic Settings
│   │   ├── dependencies.py
│   │   └── routes/
│   │       ├── farm.py             # Farm profile CRUD
│   │       ├── environment.py      # NASA POWER & SoilGrids endpoint
│   │       ├── recommendations.py  # 3 Recommendation archetypes & suitability
│   │       ├── scenarios.py        # Scenario stress simulation & plan comparison
│   │       ├── sources.py          # Data source metadata & provenance
│   │       └── voice.py            # Voice AI utterance parsing & confirmation
│   │
│   ├── data/
│   │   ├── nasa_power_client.py    # NASA POWER Climatology point client
│   │   ├── soilgrids_client.py     # ISRIC SoilGrids v2 client
│   │   ├── normalize.py            # USDA texture classification & unit conversions
│   │   ├── validation.py           # Egyptian bounding box & physical bounds validation
│   │   ├── cache.py                # Persistent SQLite cache with TTL
│   │   └── environment_service.py  # Composite environmental orchestrator
│   │
│   ├── domain/
│   │   ├── schemas.py              # Domain Pydantic models (FarmProfile, Plan, etc.)
│   │   └── provenance.py           # Data provenance and lineage classification
│   │
│   ├── voice/
│   │   ├── asr.py                  # Egyptian Arabic acoustic normalizer
│   │   ├── nlu.py                  # Deterministic Fellahi slot & number parser
│   │   ├── lexicon.py              # Versioned Fellahi lexicon & unverified term logger
│   │   ├── dialog.py               # Confirmation state machine
│   │   ├── phrase_bank.py          # Egyptian response templates & disclaimers
│   │   └── tts.py                  # Text-to-speech prosody & audio playback spec
│   │
│   └── services/
│       ├── decision_engine_adapter.py # Track A contract adapter & crop benchmarks
│       ├── recommendation_service.py  # 3-archetype recommendation pipeline
│       └── comparison_service.py      # Plan comparison and stress testing
│
├── data/
│   ├── demo/
│   │   └── fixtures_egypt.json     # Calibrated offline regional fixtures (Delta, Upper Egypt, Oases)
│   ├── lexicon/
│   │   └── unrecognized_terms.json # Dynamic log of unrecognized dialect words
│   └── processed/
│       └── cache.sqlite            # SQLite environmental cache
│
├── tests/
│   ├── test_api_health.py          # Backend initialization & health tests
│   ├── test_environmental_data.py  # NASA & SoilGrids clients, cache & normalization tests
│   ├── test_api_endpoints.py       # Full API integration test suite
│   ├── test_voice_ai.py            # Voice AI pipeline, NLU & confirmation dialog tests
│   └── test_farmer_pwa.py          # PWA static serving and manifest tests
│
├── .env.example
├── requirements.txt
└── README.md
```

---

## 3. Key Implementation Highlights

### B1 — Repository & FastAPI Foundation
- Clean, modular FastAPI architecture with strict typing (`Pydantic v2`).
- Audit logging middleware recording request duration (`X-Response-Time-Ms`).
- Centralized exception handlers for `RequestValidationError` and unhandled exceptions.
- Health check endpoint at `GET /health`.

### B2 — NASA POWER & SoilGrids Data Engineering
- **NASA POWER Client:** Fetches `T2M`, `RH2M`, `WS2M`, `ALLSKY_SFC_SW_DWN`, and `PRECTOTCORR`.
- **SoilGrids Client:** Fetches `phh2o`, `soc`, `clay`, `silt`, `sand`, `bdod`, `cec`, and derives USDA Soil Texture Triangle classes (Clay, Clay Loam, Sandy Loam).
- **Depth-Weighting:** Computes depth-weighted averages for the top 0-30cm root zone.
- **Salinity Integrity Rule:** ISRIC SoilGrids does **NOT** measure salinity (ECe). FieldWise AI **never fabricates** safe salinity values; salinity is marked strictly as `UNKNOWN`, with explicit warnings presented to experts and farmers.
- **Resilience & Caching:** Persistent SQLite cache (`cache.sqlite`) with configurable TTL; automatic fallback to calibrated Egyptian fixtures (`Kafr El-Sheikh`, `Minya`, `New Valley`) when external APIs are unreachable.

### B3 — Decision Engine Integration (Track A Contract)
- Exposes complete agricultural decision endpoints while keeping business logic separate from API routes.
- Generates exactly three distinct plan archetypes:
  1. **الأكسب (Highest Net Profit):** Maximizes financial returns.
  2. **الأوفر في المية (Most Water Efficient):** Minimizes irrigation consumption and pumping costs.
  3. **الأأمن (Safest / Lowest Risk):** Focuses on strategic crops with guaranteed state procurement prices (e.g. Wheat).
- Scenario simulation endpoint (`POST /api/scenarios/simulate`) evaluating water shortages, fertilizer cost inflation, and temperature anomalies.

### B4 — Egyptian Arabic Voice AI Pipeline
- **Pipeline:** Farmer Speech → ASR Normalization → Fellahi Dialect NLU → Confirmation Dialogue → Decision Engine → Response Templates → TTS.
- **Fellahi Agricultural Lexicon (`v1.2.0`):** Egyptian land units (فدان، فدانين، قيراط، سهم), irrigation terminology (ترعة، مناوبة، ارتوازي), crop aliases (قمح، غلة، برسيم، فول بلدي، ذرة)، and priority phrases.
- **Deterministic Number Parsing:** Accurately converts "عندي تلات فدادين و ٦ قراريط" into `3.25` feddans, and "معايا ٥٠ ألف جنيه" into `50,000` EGP.
- **Confirmation Dialogue:** Repeats the understood details ("تمام يا حاج، فهمت إن أرضك في كفر الشيخ ومساحتها ٣.٠ فدان والمية من الترعة بالمناوبة. صح كده يا حاج؟") and waits for explicit affirmation ("أيوه") before triggering calculations.
- **Safety & Disclaimers:** Every financial figure includes the mandatory disclaimer: *"ده تقدير استرشادي مش ضمان"* (Estimate, not guarantee), with a direct option to speak to an agricultural engineer (`19561`).

### B5 — Farmer Voice Assistant PWA
- Arabic RTL layout (`dir="rtl"`), bold Cairo typography, and high-contrast colors suitable for outdoor sunlight.
- Huge circular microphone button (100px) with recording pulse state.
- Web Speech API integration for zero-latency, local-device transcription.
- Complete tap-based fallback for every single voice interaction.

### B6 — Expert Console (Streamlit)
- **Page 1: Farm Overview:** Interactive diagnostic of plot GPS, soil chemistry/texture donut chart, NASA thermal profile, and missing-data indicators.
- **Page 2: Sources:** Full provenance ledger, units and transformation matrix, and uncertainty quantification.
- **Page 3: Voice Review:** Agronomist audit table for farmer dialogue sessions, slot correction interface, unrecognized dialect term log, and lexicon curation tools.

---

## 4. Setup & Running Instructions

### Prerequisites
- Python 3.10+ (tested on Python 3.13)
- Windows / Linux / macOS
- Git

### 1. Environment Setup
```powershell
# Clone or navigate to the repository
cd d:\Projects\Napta

# Create and activate virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1   # On Windows PowerShell
# source .venv/bin/activate    # On Linux/macOS

# Install dependencies
pip install -r requirements.txt
```

### 2. Configuration
Copy the configuration template:
```powershell
cp .env.example .env
```

### 3. Launch the FastAPI Backend
```powershell
.\.venv\Scripts\uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```
- **API Documentation (Swagger UI):** [http://localhost:8000/docs](http://localhost:8000/docs)
- **Health Check:** [http://localhost:8000/health](http://localhost:8000/health)
- **Farmer PWA:** [http://localhost:8000/farmer/](http://localhost:8000/farmer/)

### 4. Launch the Expert Console (Streamlit)
In a separate terminal:
```powershell
.\.venv\Scripts\streamlit run apps/expert_console/app.py --server.port 8501
```
- **Expert Console Dashboard:** [http://localhost:8501](http://localhost:8501)

---

## 5. Automated Test Suite

FieldWise AI includes automated test suites covering backend health, data engineering clients, SQLite caching, API routes, voice AI, and PWA static mounting.

Run all tests:
```powershell
.\.venv\Scripts\pytest -v
```

Test Results: **25 passed in ~1.2 minutes (100% pass rate)**:
- `tests/test_api_health.py` (3 tests passed)
- `tests/test_environmental_data.py` (8 tests passed)
- `tests/test_api_endpoints.py` (7 tests passed)
- `tests/test_voice_ai.py` (5 tests passed)
- `tests/test_farmer_pwa.py` (2 tests passed)

---

## 6. Scientific Data Sources & Citations

1. **NASA POWER Agroclimatology:**
   *NASA Langley Research Center (LaRC) Prediction of Worldwide Energy Resources.* [power.larc.nasa.gov](https://power.larc.nasa.gov/)
2. **ISRIC SoilGrids v2.0:**
   *Poggio, L., et al. (2021). SoilGrids 2.0: producing soil information for the globe with quantified spatial uncertainty. SOIL, 7, 217–240.* [isric.org/explore/soilgrids](https://www.isric.org/explore/soilgrids)
3. **Egyptian Ministry of Agriculture and Land Reclamation (MALR):**
   *Economic Affairs Sector, Annual Agricultural Statistics Bulletins (2023-2025).*
4. **FAO Irrigation & Drainage Paper No. 56:**
   *Allen, R. G., et al. Crop evapotranspiration - Guidelines for computing crop water requirements.*
