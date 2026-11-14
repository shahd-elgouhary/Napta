# Handoff checklist (for the user)

1. Unzip fieldwise_handoff.zip into the root of the merged repo. It adds: CLAUDE.md, ANTIGRAVITY_PROMPT.md, and the data/ files. It does NOT contain code, so it cannot overwrite your units_eg.py or profitability.py. If CLAUDE.md already exists, replace it with this one.
2. Open the repo in Antigravity and paste this single message:

   Read CLAUDE.md, then ANTIGRAVITY_PROMPT.md completely. Start with Step 0 (audit the repo, merge Track A and Track B on a branch, report hardcoded values, run pytest). Stop after Step 0 and report before doing anything else.

3. After each step the agent stops and summarizes. Reply "go" to continue, or paste any error.
4. Before the demo: open the limitations page in the app and confirm it says that crop data is AI-drafted and unverified.
