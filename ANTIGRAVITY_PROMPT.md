# MASTER PROMPT FOR ANTIGRAVITY: FieldWise AI (Napta), Egypt Edition

Read this whole file first. Then read `CLAUDE.md` and follow it. Work in the order given in section 12. Do not skip the rules in section 2.

---

## 1. What this project is

NASA Space Apps 2026 challenge "Field Shift: Adapting Farms with NASA Data". We are building a crop-rotation and farm-business planner for Egyptian farmers.

Principle: **one deterministic decision engine, two presentations.**
- A **Farmer app** (mobile, voice-first, Egyptian Arabic) that proposes up to three plans: الأكسب (highest profit), الأوفر في المية (most water-saving), الأأمن (safest under stress).
- An **Expert app** (mobile-friendly) for agronomists that shows the data behind every plan: sources, constraints, costs, assumptions.

Every number comes from the engine. The farmer UI never calculates or invents anything. An LLM may be used only as a dialect parser for input, never for numbers or agronomic facts.

This is a hackathon MVP. Prefer a complete working end-to-end flow over extra features.

## 2. Non-negotiable rules

1. **Units.** Internal units are SI: area in **m2**, mass in **kg**, volume in **m3**, money in **EGP**, yield in **kg/m2**, price in **EGP/kg**. Conversion to feddan / qirat / sahm / ha / ardab / qantar happens ONLY in `src/egypt/units_eg.py`. Never write `4200.83` or any conversion factor anywhere else. Import from `units_eg`.
2. **No invented values.** Do not make up agronomic values, prices, costs or regulations. Data comes from files in `data/`. If a value is missing, return `None` / raise a clear error / show "missing data". Never substitute a default that looks plausible.
3. **AI-drafted data must be labelled.** `data/crop_profiles.csv` was drafted by an AI (not an agronomist) and every row has `status=ai_draft_unverified`. Read that column and carry it through: the API response and both UIs must show a visible "draft, unverified" badge wherever those values influence a result. Do not edit values in that file unless the user asks. Do not remove the status column.
4. **Do not edit anything in `tests/` just to make a test pass.** If a test fails, explain why first. If the test itself is wrong, say so and ask.
5. **Pure functions, type hints everywhere.** Domain logic lives in `src/`, never inside UI code.
6. **Small changes.** Do not rewrite a whole file to fix a small bug. One task per branch, one PR per task. Never merge to `main` yourself.
7. **Explain before you code.** For every task write a short plan (what, why, which files), then implement.
8. **No secrets in the repo.** Use `.env` (gitignored) and keep `.env.example` updated.
9. **Honest claims only.** Estimates stay estimates. No guaranteed profit or yield. Suitability score is a relative compatibility index, not a probability. Scenarios are stress tests, not forecasts.
10. **Safety scope.** Crop and rotation planning only. No pesticide or fertilizer dosage advice. Always offer "talk to an extension engineer" (كلّم مهندس). Never hardcode a phone number unless the user confirms it.

## 3. Repository state (what already exists)

Two people's work is being merged into one repo.

**Track A (the "brain", written by the user):**
- `src/egypt/units_eg.py` with tests in `tests/test_units_eg.py`. Area base unit is m2. Ardab/qantar are crop-specific and are read from `data/crop_units.csv` (columns: crop, unit, kg_per_unit, source); empty rows are skipped, a value without a source raises an error, a missing crop raises `MissingUnitError`.
- `src/business/profitability.py` with tests in `tests/test_profitability.py`: `revenue_egp`, `total_cost_egp` (rent toggle), `operating_profit_egp`, `roi_percent` (None if cost is 0), `break_even_yield_kg_per_m2`, `break_even_price_egp_per_kg`, `per_feddan`, and `calculate_economics` returning a `PlanEconomics` dataclass.
- `pytest.ini` sets `pythonpath = .`.

**Track B (the "body", written by teammate Shahd, repo `shahd-elgouhary/Napta`):**
- FastAPI backend (`src/api/`), NASA POWER and SoilGrids clients with SQLite cache and offline fixtures (`src/data/`), `src/domain/schemas.py` and `provenance.py`, voice modules (`src/voice/`: asr, nlu, lexicon, dialog, phrase_bank, tts), services (`decision_engine_adapter.py`, `recommendation_service.py`, `comparison_service.py`), the Farmer PWA in `apps/farmer_pwa/`, and a Streamlit Expert Console in `apps/expert_console/`.

**Step 0 (do this first, before writing anything):**
1. Inspect the merged repo. If Track A and Track B are not yet in one repo, tell the user and help merge them on a branch (do not overwrite either side).
2. Read `src/domain/schemas.py` and `src/services/decision_engine_adapter.py`. The schemas are the contract: **adapt Track A code to them, not the other way round**, unless the user agrees to a change.
3. Search the whole repo for hardcoded crop numbers, prices, costs, conversion factors, and phone numbers. Report each one with file and line. Move values into `data/` files with a source and status, or flag them. Do not silently keep unsourced "benchmarks".
4. Run `pytest` and report the baseline result.

## 4. Data files (`data/`) are already created

All files below exist. They were drafted by an AI plus web research, not by an agronomist, so most rows carry `status` (`ai_draft_unverified`, `needs_verification`, `conflicting`) and `confidence`. Carry status and confidence into every API response and show them in both UIs. Do not change values unless the user asks.

| File | Content | Notes |
|---|---|---|
| `crop_profiles.csv` | 8 crops: wheat, berseem, faba_bean, sugar_beet, onion, maize, rice, cotton | Temperature, pH, salinity threshold, Kc, cycle, sowing months, yield range (t per feddan). Validate min <= opt_min <= opt_max <= max. Sowing months can wrap a year boundary. |
| `crop_prices.csv` | price range per kg per crop, with date and source | Only wheat has a medium-confidence source. Others are drafts. Use low/high as a range, never a single number, in the farmer UI. |
| `cost_assumptions.csv` | itemized EGP per feddan per season for each crop | AI drafts calibrated against sourced wage (EGP 196/day) and diesel. `rent` has `default_included=false` (toggle). All costs are visible and user-overridable. |
| `crop_units.csv` | ardab and qantar weights | Loader rule: value needs a source, blank rows skipped. Unit keys match `local_sale_unit` in crop_profiles. |
| `price_candidates.csv` | dated, sourced reference prices | Reference only; includes fertilizer (subsidized ~EGP 6,000 per ton vs free market ~EGP 26,000-28,000 per ton) and diesel. |
| `regulations.csv` | wheat procurement info, rice and cotton warnings, sugar beet contract | `rule_type` is info, flag, or hard. Flags show warnings; the user may enter a feddan limit that becomes hard. |
| `rotation_rules.csv` | legume bonus, hard and soft repetition rules | hard rules reject plans; soft rules apply a penalty. |
| `sources_registry.csv` | which datasets cover Egypt and which do not | Several US datasets do NOT cover Egypt; do not build adapters for them. |
| `demo/demo_farm.json` | fictional demo farm | Adapt the field names to `src/domain/schemas.py`. Use as the golden end-to-end test input. |

Known data issues to surface in the UI, not hide: wheat national average yield sources conflict (about 19.6 vs 24 ardab per feddan); sugar beet supply price conflicts (EGP 2,000 vs 2,400 per ton); onion and rice price readings are uncertain; yields for faba, onion, sugar beet and cotton are AI estimates.

## 5. Track A tasks to implement (in this order)

For each task: write the spec in the PR description, write tests with **numbers computed by hand and shown in comments**, implement, run tests, and keep functions pure.

### A3 `src/agronomy/suitability.py`
- Inputs: a crop profile, an environment summary for the season, the farm profile.
- For each factor (temperature, pH, salinity, planting-window fit) compute a 0 to 100 score using a trapezoid: 0 outside the absolute range, 100 inside the optimal range, linear in between.
- **Hard exclusion** when a value is outside the absolute range, with the reason.
- **Missing data is never ideal.** A missing factor is flagged `missing`, excluded from the weighted mean with its weight reported, and lowers a `confidence` field. Unknown salinity (SoilGrids has none) must lower confidence and show a warning.
- Salinity: use `salinity_threshold_ece_dsm` only if a measured/entered value exists. Otherwise flag unknown.
- Combine with documented weights stored in config (not buried in code). Return component scores, exclusions, missing fields, sources, and the draft status.
- Tests: suitable case, threshold fail, missing critical variable, unknown salinity.

### A4 `src/agronomy/water.py`
- ET0 by FAO-56 Penman-Monteith from NASA POWER inputs (T2M, T2M_MAX, T2M_MIN if available, RH2M, WS2M, ALLSKY_SFC_SW_DWN). Check the wind-height assumption (2 m) and radiation unit conversion (MJ/m2/day) explicitly in code comments.
- `ETc = Kc x ET0`, with Kc by growth stage (ini, mid, end) from the crop profile. Stage lengths: split the cycle in a documented way (config), and say it is an approximation.
- Output seasonal crop water need in mm and in m3 per m2 (use `units_eg`). Rainfall is a minor term. **Never infer irrigation availability from NASA data.**
- Test against a worked example from the FAO-56 document itself. Fetch the example and its expected result from the document; do not trust memory for expected values.
- Water cost = pumping fuel or electricity plus fees, from `cost_assumptions.csv`.

### A5 `src/optimization/rotation_generator.py` and `constraints.py`
- Enumerate rotations over the configured horizon (default two agricultural years: winter / summer / nili seasons) using `itertools.product` for a small crop set.
- Hard constraints, each returning a reason when violated: crop not excluded by suitability; sowing window respected; harvest of the previous crop does not push the next past its window (use `cycle_days` and `sow_*_month`); seasonal water within the farm's availability category (reliable canal / shortage at canal end / well only) and optional volume; cash within budget; legume or break-crop rule and same-family repetition from `rotation_rules`; regulatory rules from `regulations.csv`; harvest-to-planting gap.
- Water category is user-entered. Do not derive it.
- If no plan is feasible: return which constraints blocked it and offer a controlled relaxation of non-essential ones only.
- Tests: every plan marked feasible satisfies every hard constraint (property-style test over generated plans); infeasible plans carry reasons.

### A6 `src/optimization/objective.py` and `ranking.py`
- Objectives: profit, water use, soil-health proxy (labelled as a proxy: legume in rotation), climate resilience (labelled, simple, documented).
- Weighted score plus Pareto front. Select exactly the three farmer archetypes: highest profit, most water-efficient, safest (lowest downside under the adverse scenario, favouring procurement-backed crops). If fewer than three distinct plans exist, return fewer and say why.
- Changing priorities must change ranking only through the defined objective weights.

### A7 `src/scenarios/scenarios.py` and `sensitivity.py`
- `ScenarioSpec` presets: canal water cut, fertilizer price rise or subsidy unavailable, harvest-time price drop, heat-wave yield reduction (user-defined), general input inflation, and a "crowding" price-drop stress test for perishable crops (onion). Label all as stress tests.
- **The baseline is never mutated.** Use frozen dataclasses and return a new result plus a delta. Add a test that deep-compares the baseline before and after.
- One-at-a-time sensitivity plus labelled combined scenarios.

### A8 Streamlit pages (optional if time is short; the mobile Expert view in section 7 has priority)
- Rotation Explorer, Business Analysis, Scenario Lab, calling the functions above.

### Economics integration
Use `calculate_economics` per crop per season, sum undiscounted profit per rotation in nominal EGP with the price date shown. Add a **cash view**: money needed before harvest and the delay between harvest and payment (48 hours for wheat procurement per `price_candidates.csv`). Call it "operating profit", never "net profit".

## 6. Integration with the backend

- Replace the stubs in `decision_engine_adapter.py` with real calls to the functions above, one by one, keeping the API response shape stable. After each swap run the API tests.
- Every response value carries: value, unit, source, retrieval/price date, and status in {source, user_entered, farmer_said, estimated, simulated, ai_draft_unverified}.
- Endpoints must return structured plan data (crops per season, metrics, constraints passed/failed, score decomposition, missing-data flags, provenance). The farmer view derives its spoken text from the same payload.
- Add a golden end-to-end test: one fixture farm goes from profile to environment to plans to economics to one scenario, and the result is saved and compared on every run.
- External APIs must fail gracefully to cache or fixtures. The demo must work with no network.

## 7. Mobile UI: two interfaces on one API

Deliver as an installable **PWA** (manifest, service worker, offline fallback, works on a low-end Android phone and weak connectivity). Do not build a native app. Keep Arabic RTL, large touch targets (minimum 48 px, mic button about 100 px), high contrast for sunlight.

### 7.1 Farmer interface `/farmer`
- Voice first, tap second, text last. Large mic button; tap/icon fallback for every voice step so the full flow works without speech.
- Flow: speech to slots (location, area, water type, last crops, budget, goal), then **read-back confirmation** ("فهمت إن عندك ... صح كده؟") and wait for أيوه / لأ before computing anything.
- Show at most three plan cards, named الأكسب / الأوفر في المية / الأأمن, with crop icons and traffic-light colours.
- Money is always a rounded range ("تقريبًا من كذا لكذا") per feddan, never a percentage or score, and always with the spoken disclaimer "ده تقدير مش ضمان".
- 1 or 2 plain reasons per plan from the verified phrase bank, filled with engine values. Templates first. An LLM may only paraphrase template text and its output must be validated against the structured result.
- Spoken scenario question: "لو المية قلت؟" recomputes via the scenario API and answers.
- Commands available at any time: كرر، أبطأ، كمّل، لأ مش كده، كلّم مهندس.
- Assisted mode: a cooperative worker or family member can run the phone.
- If speech recognition fails or a term is unknown: re-ask, never guess. Log unknown terms (with consent) for lexicon review.
- Privacy: ask consent, do not store audio by default (delete after transcription unless the user opts in), collect no unnecessary identifying data.
- Show the "draft data" notice in simple Arabic when AI-drafted crop values influenced a plan.

### 7.2 Expert interface `/expert` (responsive, designed for a phone first)
- Farm overview: location, area (feddan/ha toggle), soil with depth/unit/source/uncertainty, seasonal climate, water category, budget, history, data-status panel.
- Plan list with the full ranked set. Each plan opens into an expandable "why this plan" view: season timeline, per-crop suitability decomposition, constraints passed/failed (including regulatory), itemized costs, revenue, operating profit, ROI, break-even, cash view, water demand.
- **Provenance on every number:** source, date, unit, status badge. Distinct badges for source / user-entered / farmer-said / estimated / simulated / ai_draft_unverified. Missing data is shown explicitly.
- Scenario Lab: baseline vs scenario side by side with deltas and a stress-test warning.
- Voice Review: conversation log, parsed slots (correctable), unknown-term queue, lexicon editor with version history, measured ASR/NLU accuracy.
- Export a plan report (Arabic and English).
- The existing Streamlit console may stay as a desktop companion, but the phone-friendly `/expert` view is the deliverable.

## 8. Voice pipeline requirements

Pipeline: speech, then ASR (Egyptian Arabic), dialect normalizer (Fellahi lexicon), intent and slot parser (deterministic number/unit parser plus optional LLM with JSON schema validation), read-back confirmation, engine API, phrase-bank composer, TTS (ar-EG).

- Deterministic parsing of Egyptian numbers and units, for example "تلات فدادين و٦ قراريط" becomes 3 feddan 6 qirat (convert via `units_eg.fqs_to_m2`), and "٥٠ ألف" becomes 50,000 EGP.
- Parser output that fails schema validation triggers a re-ask.
- Pre-generate and cache audio for the demo flow. Provide a pre-recorded fallback so the demo never depends on a live service.
- Spoken plan fidelity test: crops and numbers spoken equal the engine output exactly.
- Do not claim dialect "training" or accuracy beyond what a measured test set shows. Provide a script that reports word error rate and slot accuracy on a recorded test set.

## 9. Testing and quality gates

- Every calculation has a unit test with hand-computed numbers.
- Any plan marked feasible passes all hard constraints (including regulatory).
- Suitability is never presented as yield probability.
- Baseline is unchanged after any scenario.
- Missing data never becomes an ideal value anywhere.
- Every displayed price, yield and cost has unit, date, and source or assumption label.
- The app still works if an external service fails.
- Run `pytest` before every commit. Report failures honestly.

## 10. Git workflow

- Branch per task (`a3-suitability`, `a4-water`, `a5-rotations`, `a6-ranking`, `a7-scenarios`, `ui-farmer`, `ui-expert`, `integration`).
- Small commits with clear messages. Push the branch and describe the PR. Do not merge to `main`.
- The user explains each function to a teammate in two sentences before merging, so keep functions small and readable, with a one-line docstring stating the formula and units.

## 11. Definition of done (MVP)

- Farm created by form and by voice with validated location, area, budget, water category, history.
- Environment data loaded or loaded from identified fixtures.
- Crop knowledge base loaded with draft status visible.
- Suitability with components, missing-data warnings, exclusions.
- Rotations generated or infeasibility explained, with regulatory constraints.
- Economics with itemized costs, ROI, break-even and cash view.
- Three plans compared consistently; scenarios do not overwrite the baseline.
- Farmer PWA: voice in, read-back, three spoken plans, one spoken scenario, tap fallback.
- Expert mobile view: provenance on every number, constraints, scenarios.
- Offline or pre-recorded demo path.
- A limitations page stating: crop profiles are AI-drafted and unverified, prices are dated and need verification, SoilGrids has no salinity, ET0 is modelled, estimates are not guarantees.

## 12. Order of work

0. Step 0 audit (section 3).
1. Data loaders and validation for `crop_profiles.csv`, `cost_assumptions.csv`, `regulations.csv`.
2. A3, A4.
3. A5, A6.
4. A7.
5. Swap stubs for real functions in the adapter, with the golden end-to-end test.
6. Farmer PWA changes.
7. Expert mobile view.
8. Voice test set script, pre-generated audio, fallback.
9. Limitations page and final test run.

After each step, stop, summarize what changed, list anything uncertain, and wait for the user's go-ahead before the next branch.
