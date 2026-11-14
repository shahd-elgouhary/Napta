# FieldWise AI (Napta) - Blockers & Incomplete Tasks Log

**Branch:** `overnight-build`  
**Last Updated:** 2026-11-14T09:17:00+02:00  

---

## Active Blockers
*None currently.*

---

## Resolved or Mitigated Items
* **Missing `data/*.csv` files:** Found in `Napta-merged-old/data/` and restored cleanly without overwriting teammate's fixtures or cache.
* **Test timeout latency:** API endpoint tests call live environmental APIs with a 12s timeout before gracefully falling back to offline regional fixtures. All tests pass successfully.
