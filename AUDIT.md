# Step 0 Audit: FieldWise AI (Napta) Repository

**Date:** 2026-11-14  
**Branch:** `overnight-build`  
**Auditor:** Antigravity Autonomous Engine  

---

## 1. Overview & Baseline State

This repository merges two tracks of work for the NASA Space Apps 2026 challenge:
* **Track A ("The Brain"):** Core agronomic and economic calculation modules:
  * `src/egypt/units_eg.py` (strict SI base units, Egyptian land & crop units via `data/crop_units.csv`)
  * `src/business/profitability.py` (pure financial calculations: revenue, costs with rent toggle, operating profit, ROI, break-even yield and price)
* **Track B ("The Body"):** Teammate Shahd's infrastructure:
  * FastAPI backend (`src/api/`)
  * Data clients for NASA POWER and SoilGrids with SQLite caching and offline fallback fixtures (`src/data/`)
  * Domain schemas and provenance models (`src/domain/schemas.py`, `src/domain/provenance.py`)
  * Services: `src/services/decision_engine_adapter.py`, `recommendation_service.py`, `comparison_service.py`
  * Egyptian Arabic voice modules (`src/voice/`: ASR, NLU, lexicon, dialog manager, phrase bank, TTS)
  * Farmer Mobile PWA (`apps/farmer_pwa/`) and Streamlit Expert Console (`apps/expert_console/`)
* **Data Files (`data/`):**
  * Sourced/draft CSV files were recovered from the Track A repository (`Napta-merged-old/data`) into `data/`:
    `crop_profiles.csv`, `crop_prices.csv`, `cost_assumptions.csv`, `crop_units.csv`, `price_candidates.csv`, `regulations.csv`, `rotation_rules.csv`, `sources_registry.csv`, and `demo/demo_farm.json`.

---

## 2. Baseline Test Results (`pytest`)

**Total Collected:** 60 tests  
**Status:** **60 PASSED**, 0 failed, 1 warning (Starlette DeprecationWarning for TestClient httpx)  
**Execution Environment:** Python 3.13.7 (win_amd64), pytest 9.2.0, pytest-asyncio 1.5.0  

### Test Suite Breakdown
| Test File | Tests Passed | Focus Area |
|---|---|---|
| `tests/test_units_eg.py` | 19 | Egyptian area/mass/volume/local unit conversions & loaders |
| `tests/test_profitability.py` | 16 | Operating profit, ROI, break-even, rent exclusion |
| `tests/test_api_health.py` | 3 | FastAPI health checks and settings validation |
| `tests/test_farmer_pwa.py` | 2 | Static file serving and manifest integrity |
| `tests/test_voice_ai.py` | 5 | Fellahi lexicon, NLU slot extraction, dialog states |
| `tests/test_environmental_data.py` | 8 | Coordinates, SoilGrids normalization, cache, fixtures |
| `tests/test_api_endpoints.py` | 7 | Farm profile, recommendations, scenarios, sources |
| **Total** | **60** | **100% Passing Baseline** |

---

## 3. Consistency Audit: Track A vs. Track B

### 3.1 Units and Conversions
* **Track A Standard (`CLAUDE.md`, `units_eg.py`):**
  * Strict SI units internally: area in $m^2$, mass in $\text{kg}$, volume in $m^3$, money in $\text{EGP}$, yield in $\text{kg}/m^2$, price in $\text{EGP}/\text{kg}$.
  * Feddan conversion factor ($4200.83\ m^2$) lives **ONLY** in `src/egypt/units_eg.py`.
  * Crop-specific mass units (ardab, qantar) are loaded from `data/crop_units.csv` with mandatory sources.
* **Track B Inconsistencies:**
  * `src/domain/schemas.py:59-60`: `FarmArea` specifies `1 Feddan = 4,200.83 m² = 24 Qirats` and `1 Qirat = 175.03 m² = 24 Sahms` in schema field descriptions. `FarmArea.total_feddans` uses inline division `qirats / 24.0` (line 65) instead of calling `units_eg.qirat_to_feddan()`.
  * `src/domain/schemas.py`: Crop and recommendation models define units at human/display scale rather than SI base:
    * `average_yield_ton_per_feddan` (ton/feddan vs internal $\text{kg}/m^2$)
    * `benchmark_selling_price_egp_per_ton` ($\text{EGP}/\text{ton}$ vs internal $\text{EGP}/\text{kg}$)
    * `typical_cost_per_feddan_egp` ($\text{EGP}/\text{feddan}$ vs internal $\text{EGP}/m^2$)
    * `water_demand_m3_per_feddan` ($m^3/\text{feddan}$ vs internal $m^3/m^2$ or $\text{mm}$)
  * `src/voice/lexicon.py:45-67`: Defines `AREA_UNITS` dictionary with hardcoded fractions (`1.0 / 24.0` for qirat, etc.) instead of referencing `src.egypt.units_eg`.
* **Resolution Path:**
  * Schemas are the external contract. Track A domain modules (`suitability`, `water`, `rotation_generator`, `profitability`) will calculate in strict SI base units.
  * The decision engine adapter converts internal SI results to the contract schemas using `src.egypt.units_eg` conversion functions.

### 3.2 Economic & Profitability Modeling
* **Track A Standard (`profitability.py`):**
  * Rule: Costs are **NEVER invented**. Only itemized costs passed by the caller are summed.
  * Rent is a toggleable item (`include_rent=True/False`).
  * Metric is named strictly **Operating Profit** (`operating_profit_egp`), never net profit (no tax/depreciation/financing).
  * ROI is undefined (`None`) when costs are 0.
* **Track B Inconsistencies:**
  * `src/services/decision_engine_adapter.py:230-235`: Invents arbitrary fixed percentage cost breakdowns:
    * `seeds_cost = base_cost * 0.20`
    * `fert_cost = base_cost * 0.35`
    * `fuel_cost = base_cost * 0.15 * water_multiplier`
    * `labor_cost = base_cost * 0.20`
    * `prep_cost = base_cost * 0.10`
  * `src/domain/schemas.py:174-175`: Uses the term `net_profit_egp_per_feddan` and `total_net_profit_egp`.
* **Resolution Path:**
  * Replace the percentage heuristic with real itemized costs from `data/cost_assumptions.csv`.
  * Map `operating_profit_egp` to the contract schema fields while labeling the Arabic descriptions as صافي الربح التشغيلي (تقديري).

### 3.3 Crop Catalog & Nomenclature Discrepancies
* **Track A Sourced Data (`data/crop_profiles.csv`):**
  * 8 verified crops: `wheat`, `berseem`, `faba_bean`, `sugar_beet`, `onion`, `maize`, `rice`, `cotton`.
  * Sowing months, min/opt/max temperatures, pH limits, salinity thresholds, cycle lengths.
* **Track B Hardcoded Catalog (`decision_engine_adapter.py:25-171`):**
  * 6 crops: `wheat`, `berseem`, `fava_beans`, `maize`, `cotton`, `tomatoes`.
  * Discrepancy 1: Uses key `fava_beans` instead of `faba_bean`.
  * Discrepancy 2: Includes `tomatoes` (not in `crop_profiles.csv`); omits `sugar_beet`, `onion`, `rice`.
  * `src/voice/dialog.py:26-33`: Hardcoded `CROP_AR_MAP` has `wheat`, `berseem`, `fava_beans`, `maize`, `cotton`, `tomatoes`.
* **Resolution Path:**
  * Support alias matching in `FellahiLexicon` so `fava_beans` and `faba_bean` both map cleanly.
  * Load crops from `data/crop_profiles.csv` dynamically in Step 1.

---

## 4. Audit Findings: Hardcoded Values, Prices, and Phone Numbers

### 4.1 Hardcoded Phone Numbers
| File | Line | Content | Violation / Note |
|---|---|---|---|
| `apps/farmer_pwa/index.html` | 27 | `<a href="tel:19561" class="help-btn" title="الاتصال بالإرشاد الزراعي">` | Agricultural extension hotline hardcoded as link |
| `src/voice/dialog.py` | 112 | `"تحت أمرك يا حاج. رقم الإرشاد الزراعي التابع لوزارتك: 19561، "` | Hotline hardcoded in spoken dialogue response |

*Recommendation:* Keep 19561 as configurable fallback in settings/phrase bank with disclaimer; prompt extension contact dynamically.

### 4.2 Hardcoded Unit Conversion Factors (Outside `units_eg.py`)
| File | Line | Content | Violation / Note |
|---|---|---|---|
| `src/domain/schemas.py` | 59 | `description="1 Feddan = 4,200.83 m² = 24 Qirats"` | Hardcoded documentation string |
| `src/domain/schemas.py` | 60 | `description="1 Qirat = 175.03 m² = 24 Sahms"` | Hardcoded documentation string |
| `src/domain/schemas.py` | 65 | `return round(self.feddans + (self.qirats / 24.0), 3)` | Inline conversion factor `24.0` |
| `src/voice/lexicon.py` | 61-66 | `"قيراط": 1.0 / 24.0`, `"قيراطين": 2.0 / 24.0`, etc. | Hardcoded qirat-to-feddan fractions |

### 4.3 Hardcoded Crop Agronomic Benchmarks & Prices
All found in `src/services/decision_engine_adapter.py`:
| Line | Crop | Hardcoded Parameter | Hardcoded Value |
|---|---|---|---|
| 33-44 | `wheat` | temp (5-32°C), pH (6.5-8.5), ECe (6.0), water (1950 $m^3$/fed), yield (2.7 t/fed), price (13,500 EGP/t), cost (14,500 EGP/fed) | Sourced from static comments |
| 57-69 | `berseem` | temp (7-30°C), pH (6.0-8.2), ECe (4.0), water (2400 $m^3$/fed), yield (28.0 t/fed), price (1,100 EGP/t), cost (11,000 EGP/fed) | Sourced from static comments |
| 82-93 | `fava_beans` | temp (8-30°C), pH (6.5-8.4), ECe (3.5), water (1600 $m^3$/fed), yield (1.4 t/fed), price (32,000 EGP/t), cost (13,800 EGP/fed) | Sourced from static comments |
| 106-117 | `maize` | temp (12-40°C), pH (6.0-8.3), ECe (3.0), water (3100 $m^3$/fed), yield (3.4 t/fed), price (12,000 EGP/t), cost (16,500 EGP/fed) | Sourced from static comments |
| 130-141 | `cotton` | temp (15-42°C), pH (6.5-8.5), ECe (7.7), water (3800 $m^3$/fed), yield (1.1 t/fed), price (70,000 EGP/t), cost (24,000 EGP/fed) | Sourced from static comments |
| 154-165 | `tomatoes` | temp (10-35°C), pH (6.0-7.8), ECe (2.5), water (2200 $m^3$/fed), yield (18.0 t/fed), price (5,500 EGP/t), cost (38,000 EGP/fed) | Sourced from static comments |
| 224 | Generic | Water stress yield penalty: `(0.5 + 0.5 * (water_multiplier / 0.8))` | Arbitrary heuristic curve |
| 230-234 | Generic | Fixed cost shares: 20% seed, 35% fertilizer, 15% fuel, 20% labor, 10% prep | Arbitrary cost partition |
| 320 | Plan 2 | Hardcoded water saving multiplier `water_multiplier=0.85` | Uncalibrated assumption |

---

## 5. Audit Conclusion & Next Steps

1. **Working Baseline:** The test environment is operational with all 60 tests passing cleanly.
2. **Track Separation:** The adapter currently uses stubbed dictionary lookups and heuristic percentages. Track A modules must be wired in sequentially without breaking existing endpoint contracts.
3. **Execution Plan for Step 1:**
   * Build validated, typed data loaders for `crop_profiles.csv`, `crop_prices.csv`, `cost_assumptions.csv`, `regulations.csv`, `rotation_rules.csv`, and `crop_units.csv` under `src/data/loaders.py`.
   * Ensure status (`ai_draft_unverified`) and confidence are captured and propagated.
