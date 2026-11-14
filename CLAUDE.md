# FieldWise AI (Napta) - Project Rules for any AI coding tool

Read this file before every task. Full task specs are in ANTIGRAVITY_PROMPT.md.

## Units
- Internal SI units only: area m2, mass kg, volume m3, money EGP, yield kg/m2, price EGP/kg.
- Conversion to or from feddan, qirat, sahm, ha, tonne, ardab, qantar lives ONLY in src/egypt/units_eg.py. Never write a conversion factor anywhere else.
- Variable names carry the unit (area_m2, price_egp_per_kg).

## Code
- Python 3.11+, type hints on every function, pure functions, no domain logic in UI code.
- Every new function has tests with numbers computed by hand (show the arithmetic in a comment).

## Data honesty
- Never invent agronomic values, prices, costs or regulations.
- Data files in data/ carry source, date, status and confidence. Rows with status ai_draft_unverified were drafted by an AI, not an agronomist. Carry that status to the API and show a visible "draft, unverified" badge in both UIs. Do not change those values unless the user asks.
- Missing data stays missing (None or a clear error). It never becomes an ideal or default value.
- Salinity is unknown unless a user or lab value exists (SoilGrids has none). Unknown salinity lowers confidence.
- Do not build adapters for US-only datasets (OpenET, Web Soil Survey, NASS, LANDFIRE, NLCD, NAIP, CoCoRaHS).

## Never
- Never edit anything in tests/ just to make a test pass. If a test fails, explain why first.
- Never rewrite a whole file to fix a small bug.
- Never merge to main. One task per branch, one PR per task.
- Never commit secrets (.env). Keep .env.example updated.
- Never give pesticide or fertilizer dosage advice. Never promise profit or yield.
- Never hardcode a phone number or a regulation as a permanent fact.
- An LLM may only parse dialect input or paraphrase verified template text. It never supplies numbers or agronomic facts.

## Workflow
- Explain the plan before coding. Run pytest before every commit.
- After each task, stop and summarize changes and uncertainties, then wait for the user.
