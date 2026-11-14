# Review of the overnight build (reviewed 2026-11-14)

Baseline received: 85 passed, 1 failed (test_api_endpoints::test_crop_suitability_check, 69.9 vs 70).
After this update: 88 passed, 0 failed.

## Fixed in this update
1. data/crop_profiles.csv: ph_abs_max relaxed (wheat 8.0 -> 8.5, maize 8.0 -> 8.5, rice 8.0 -> 8.5, onion 7.8 -> 8.3). The Kafr El-Sheikh fixture soil has pH 8.05, which hard-excluded wheat, maize, rice and onion, so only berseem/cotton survived and the three archetype plans were identical. Egyptian Delta soils are commonly pH 7.5-8.5. These are AI estimates, still ai_draft_unverified; the change is recorded in each row's notes column.
2. tests/test_regression_findings.py (new): the three plans must be three different rotations; staple crops must not be hard-excluded by the demo soil. Both tests fail on the old data (verified).

## Found but NOT fixed (next tasks, in this order)
1. decision_engine_adapter.calculate_plan_metrics still contains invented fallbacks: typical water demand per crop (1950 / 3100 / 5500 / 3800 / 1600 m3 per feddan), default price 15000 EGP per ton, cost-share fallbacks (20/35/15/20/10 percent), the water-stress yield curve (0.5 + 0.5 * multiplier / 0.8), and hardcoded risk levels per crop. Water demand should come from src/agronomy/water.py (FAO-56 ET), costs only from cost_assumptions.csv, price only from crop_prices.csv, and missing values must surface as "missing", not as defaults.
2. Budget behaviour: with the demo farm (3 feddan, EGP 60,000) wheat costs EGP 60,960 (rent excluded), so every winter crop except berseem is rejected by the budget constraint and all three plans start with berseem. With EGP 90,000 the plans are wheat+cotton / wheat+maize / wheat+rice. Decide whether the demo budget should be 90,000, or whether the budget check should compare cash needed before harvest (not total season cost). Do not tune cost data just to make wheat fit.
3. "الأأمن" selects rice (water-heavy, area-restricted by policy). Review the safety score so that policy-restricted and water-intensive crops are not rated safest. Document the safety formula.
4. Profit naming: schema fields say net_profit; the engine computes operating profit (rent excluded by default). Label it صافي الربح التشغيلي (تقديري) in the UI.
5. Duplicate names: the adapter appends a "fava_beans" alias profile next to "faba_bean" in get_all_crop_profiles(). Make sure the catalog endpoint does not list the same crop twice.
6. Hardcoded phone 19561 (apps/farmer_pwa/index.html:27, src/voice/dialog.py:112) and qirat fractions in src/voice/lexicon.py should come from settings and units_eg.
7. Not built yet: Farmer PWA changes (/farmer: ranges, draft badge, three cards), Expert mobile view (/expert with provenance on every number), voice number/unit parser hardening and WER script, limitations page, FINAL_REPORT.md.
