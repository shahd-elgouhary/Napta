# FieldWise AI (Napta) - Autonomous Run Progress Log

**Branch:** `overnight-build`  
**Started:** 2026-11-14T09:03:00+02:00  

---

## Task 0: Step 0 Audit & Environment Setup
* **What changed:**
  * Created Python 3.13.7 virtual environment (`.venv`) and installed all dependencies from `requirements.txt` + `pytest`.
  * Checked out git branch `overnight-build` (leaving `main` untouched).
  * Recovered missing sourced CSV data files and `demo/demo_farm.json` from `Napta-merged-old/data/` into `data/`.
  * Audited consistency between Track A modules (`src/egypt`, `src/business`) and Track B code (`schemas.py`, `decision_engine_adapter.py`, API routes).
  * Audited and cataloged all hardcoded crop metrics, prices, costs, conversion factors, and phone numbers.
  * Executed baseline `pytest`: **60 passed in 57.18s**.
  * Wrote `AUDIT.md`.
* **Files touched:**
  * `AUDIT.md` (created)
  * `PROGRESS.md` (created)
  * `BLOCKERS.md` (created)
  * `data/*.csv`, `data/demo/demo_farm.json` (restored from Track A archive)
* **Decisions made:**
  * Preserved teammate's `fixtures_egypt.json` and `cache.sqlite` while copying only the data files.
  * Confirmed that Track B schemas remain the contract; Track A modules will calculate internally in SI units and adapter will map to schemas using `units_eg`.
* **Uncertainties / Blockers:**
  * None. Baseline is 100% green.

---

## Task 1: Data Loaders and Validation
* **What changed:**
  * Implemented typed, robust data loaders and validators in `src/data/loaders.py` for all 6 data tables:
    * `CropProfileRecord` & `load_crop_profiles()` (validates temperature, pH, cycle days, yields, status)
    * `CropPriceRecord` & `load_crop_prices()` (validates bounds and status)
    * `CostItemRecord` & `load_cost_assumptions()` with `get_crop_cost_items()` (rent toggle support)
    * `RegulationRecord` & `load_regulations()` (info, flag, hard rules)
    * `RotationRuleRecord` & `load_rotation_rules()` (bonus, hard, soft rules)
    * `SourceRegistryRecord` & `load_sources_registry()` (tracking coverage for Egypt)
  * Created comprehensive test suite in `tests/test_data_loaders.py` with hand-computed arithmetic in comments.
  * Full test suite passing (69 tests).
* **Files touched:**
  * `src/data/loaders.py` (created)
  * `tests/test_data_loaders.py` (created)
* **Decisions made:**
  * Standardized data resolution: look in local `data/` or relative to repo root if path is given as directory or filename.
  * Checked that status (`ai_draft_unverified`) and confidence levels are preserved on every record.
* **Uncertainties / Blockers:**
  * None.

---

## Task 2: Agronomy Engine (A3 Suitability & A4 Water Requirements)
* **What changed:**
  * Implemented `src/agronomy/suitability.py` (A3):
    * Deterministic trapezoidal scoring for temperature, pH, salinity, and sowing window fit.
    * Hard exclusions for out-of-range physical limits with detailed Arabic reasons.
    * Explicit missing data handling: unknown salinity (from SoilGrids) is excluded from weighted mean, reported in `missing_factors`, drops confidence, and generates a field test recommendation.
  * Implemented `src/agronomy/water.py` (A4):
    * FAO-56 Penman-Monteith reference evapotranspiration ($ET_0$) calculation verified against official FAO-56 Box 18 (Cairo, Egypt).
    * Explicit radiation conversion ($1\ \text{kWh}/m^2/\text{day} = 3.6\ \text{MJ}/m^2/\text{day}$).
    * Explicit wind speed verification ($u_2 = \text{WS2M}$ at 2m measurement height).
    * Stage-weighted $K_c$ curve across FAO-56 growth stages (20% ini, 30% dev, 35% mid, 15% late).
    * Water volume conversion strictly through `src.egypt.units_eg`.
  * Created unit test suite in `tests/test_agronomy.py` with hand calculations shown in comments.
  * All 78 tests passing.
* **Files touched:**
  * `src/agronomy/__init__.py` (created)
  * `src/agronomy/suitability.py` (created)
  * `src/agronomy/water.py` (created)
  * `tests/test_agronomy.py` (created)
* **Decisions made:**
  * Tested Penman-Monteith against official FAO-56 Box 18 (Cairo, Egypt worked example); matched target $ET_0 = 6.17$ mm/day within 0.1 mm/day.
  * Kept factor weights configurable in `SUITABILITY_WEIGHTS_CONFIG`.
* **Uncertainties / Blockers:**
  * None.

---

## Task 3: Optimization & Scenarios (A5 Rotations/Constraints, A6 Ranking, A7 Scenarios)
* **What changed:**
  * Implemented `src/optimization/constraints.py` (A5):
    * Checks for suitability, timing/turnaround, water availability, working capital budget, rotation rules (legume break-crop bonus, rice yearly cap, botanical family penalty), and regulations.
  * Implemented `src/optimization/rotation_generator.py` (A5):
    * Enumerates multi-season rotations (Winter -> Summer) via Cartesian product.
    * Controlled relaxation mechanism when constraints block all combinations.
  * Implemented `src/optimization/objective.py` & `ranking.py` (A6):
    * Multi-objective evaluation using `src.business.profitability` (operating profit, ROI, break-even).
    * Selection of the 3 canonical archetypes: الأكسب (Highest Profit), الأوفر في المية (Water-Saving), الأأمن (Safest/Low-Risk).
  * Implemented `src/scenarios/scenarios.py` & `sensitivity.py` (A7):
    * Stress-testing engine for canal water cut, fertilizer price surge, crop price drops, heatwaves.
    * Guaranteed baseline immutability: deep-copy isolation verified with a test comparing baseline before and after.
    * One-at-a-time sensitivity analysis across systematic steps.
  * Unit test suite created in `tests/test_optimization_and_scenarios.py`.
  * Core test suite passing (70 tests).
* **Files touched:**
  * `src/optimization/__init__.py` (created)
  * `src/optimization/constraints.py` (created)
  * `src/optimization/rotation_generator.py` (created)
  * `src/optimization/objective.py` (created)
  * `src/optimization/ranking.py` (created)
  * `src/scenarios/__init__.py` (created)
  * `src/scenarios/scenarios.py` (created)
  * `src/scenarios/sensitivity.py` (created)
  * `tests/test_optimization_and_scenarios.py` (created)
* **Decisions made:**
  * Aligned itemized cost aggregation in `objective.py` so breakdown components strictly sum to `total_cost_per_feddan_egp`.
  * Verified that baseline `model_dump()` is 100% immutable across simulations.
* **Uncertainties / Blockers:**
  * None.



