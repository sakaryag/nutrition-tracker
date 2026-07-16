# Skill: fix-bug

Use this skill when the user reports a bug in NutriTrack.

## Steps

1. **Reproduce first** — identify exactly which file and function is responsible. Read the relevant JS, route, and model before touching anything.
2. **Check known bugs** — read TODO.md to see if the bug is already documented.
3. **Minimal fix** — change only what's needed. Don't refactor surrounding code.
4. **Test** — run `pytest tests/ -v` after any backend change. For frontend bugs, verify via curl or browser.
5. **Windows write workaround** — for large files use PowerShell WriteAllText (see CLAUDE.md).
6. **Update TODO.md** — remove the bug entry if fixed.

## Common bug locations

| Symptom | Where to look |
|---|---|
| Macros not scaling | `static/js/dashboard.js` openModal / prefillFromFood / serving input listener |
| Template item macros wrong | `static/js/meal_templates.js` scaleItem, renderItemsList |
| Custom foods not showing | `routes/foods.py` source filter, `static/js/foods.js` loadCustomFoods URL |
| Auth redirect loop | `routes/auth.py` login_required, `.env` AUTH_ENABLED value, load_dotenv path |
| Summary totals wrong | `routes/summary.py` aggregation query |
| Chart not rendering | `static/js/dashboard.js` renderDonut, Chart.js CDN loaded in base.html |
