# Skill: add-feature

Use this skill when the user asks to add a new feature to NutriTrack.

## Steps

1. **Understand scope** — read CLAUDE.md, the relevant model/route/JS files, and TODO.md before writing anything.
2. **Plan first** — use EnterPlanMode to design the approach: DB changes, API routes, frontend JS, HTML, tests.
3. **Use agents for parallel work** — split independent work (e.g. backend route + frontend JS + CSS + tests) across parallel agents. Always use agents for multi-file features.
4. **DB changes** — if adding a new column to an existing table, add an ALTER TABLE guard in `app.py` (`_migrate_add_*` pattern). Never break existing data.
5. **Auth** — any new API blueprint needs a `before_request` auth check. Any new page route needs `@login_required`.
6. **Tests** — add a `Test<Feature>` class in `tests/test_api.py`. Run `pytest tests/ -v` and confirm all pass.
7. **Windows write workaround** — for files larger than ~100 lines, use PowerShell:
   ```powershell
   [System.IO.File]::WriteAllText('path', $content, (New-Object System.Text.UTF8Encoding $false))
   ```
8. **Update TODO.md** — mark the feature done or remove it from the bug list.

## Common patterns

- New API resource → new Blueprint in `routes/`, register in `app.py _register_blueprints()`
- New page → add route to `routes/pages.py`, add template, add nav link in `templates/base.html`, add JS file
- New model → create in `models/`, import in `models/__init__.py`
