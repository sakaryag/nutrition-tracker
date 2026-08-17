# Day 1 Maestro Kickoff -- NutriTrack Play Store Deployment

**Date:** 2026-08-17
**Author:** MAESTRO (Orchestrator)
**Project:** Deploy NutriTrack to Google Cloud Run + Neon Postgres, wrap as TWA Android app, publish to Google Play Store.
**Repository:** https://github.com/sakaryag/nutrition-tracker.git (branch: `main`)

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Codebase Snapshot](#2-codebase-snapshot)
3. [Work Breakdown Structure (WBS)](#3-work-breakdown-structure-wbs)
4. [Risk Register](#4-risk-register)
5. [Agent Briefs](#5-agent-briefs)
6. [Open Questions](#6-open-questions)
7. [Shared Vocabulary](#7-shared-vocabulary)

---

## 1. Executive Summary

NutriTrack is a production-grade Flask nutrition tracker with 14 SQLAlchemy models, 18 blueprints, 81 tests, bilingual i18n (EN/TR), offline NLP chat, and a social/gamification layer. The app currently runs on Railway with SQLite. We are migrating it to:

- **Backend:** Google Cloud Run (stateless containers, gunicorn)
- **Database:** Neon Postgres (serverless, free tier available)
- **Android:** Trusted Web Activity (TWA) via Bubblewrap
- **Distribution:** Google Play Store (Health & Fitness category)
- **Monetization:** Freemium (ads + premium tier, `plan_feature_enabled` column already exists)

The codebase is well-prepared for Postgres: `psycopg2-binary` is already in `requirements.txt`, the Dockerfile already uses `PORT` env var binding (`${PORT:-8080}`), the WAL pragma is already guarded behind a `sqlite` check in `app.py:65`, `_migrate_add_columns()` already has separate PostgreSQL (`IF NOT EXISTS`) and SQLite branches, and `config.py` already handles the `postgres://` to `postgresql://` URL rewrite. A `static/manifest.json` and `static/sw.js` service worker already exist.

**Key remaining work:** Cloud Run deployment config, Neon DB provisioning, data migration script, TWA wrapper (Bubblewrap), Digital Asset Links, Play Store assets and listing copy, AdMob integration, premium feature gates, legal pages, and end-to-end smoke tests.

---

## 2. Codebase Snapshot

### What Already Exists (reduces scope)

| Item | Status | File(s) |
|---|---|---|
| Postgres pool config | Done | `app.py:21-37` (pool_size, keepalives, pool_pre_ping) |
| WAL pragma guard | Done | `app.py:65` (`if 'sqlite' in ...`) |
| postgres:// URL rewrite | Done | `config.py:13-14` |
| `_migrate_add_columns` PG branch | Done | `app.py:131-229` (uses `IF NOT EXISTS`) |
| Dockerfile with PORT var | Done | `Dockerfile:20` (`${PORT:-8080}`) |
| `psycopg2-binary` in requirements | Done | `requirements.txt:5` |
| PWA manifest | Done (partial) | `static/manifest.json` -- only SVG icon, needs PNGs |
| Service worker | Done | `static/sw.js` -- cache-first static, network-first API |
| Docker compose with PG commented | Done | `docker-compose.yml:18-31` |
| CI workflow (pytest + docker) | Done | `.github/workflows/ci.yml` |

### What Does NOT Exist Yet

| Item | Owner | Priority |
|---|---|---|
| `/health` endpoint | DEV-1 | P0 |
| `cloudrun-service.yaml` | DEV-1 | P0 |
| `.github/workflows/deploy-cloudrun.yml` | DEV-1 | P0 |
| `scripts/migrate_to_postgres.py` | DEV-2 | P0 |
| `static/.well-known/assetlinks.json` | SENIOR-2 | P0 |
| `twa-manifest.json` | SENIOR-2 | P0 |
| PNG icons (48-512px) | DEV-3 | P0 |
| `templates/privacy.html` | DEV-3 | P1 |
| `templates/terms.html` | DEV-3 | P1 |
| Premium feature gate decorator | SENIOR-1 | P1 |
| AdMob integration | SENIOR-1 | P1 |
| Play Store listing copy | DEV-3 | P1 |
| `.env.production.example` | SENIOR-2 | P1 |
| `scripts/smoke_test.py` | SENIOR-2 | P2 |
| `LAUNCH_CHECKLIST.md` | DEV-1 | P2 |

### Git Branch Discrepancy

CI triggers on `main` (`.github/workflows/ci.yml:4`). CLAUDE.md git instructions reference `master`. The actual default branch is `main`. All agents MUST use `main` as the default branch name.

---

## 3. Work Breakdown Structure (WBS)

### Phase 0: Architecture & Kickoff (Day 1)

| ID | Task | Owner | Depends On | Deliverable |
|---|---|---|---|---|
| 0.1 | Codebase analysis, WBS, risk register, agent briefs | MAESTRO | -- | This document |
| 0.2 | Full architecture review (14 models, all blueprints) | ARCH | 0.1 | `docs/ADR.md` |
| 0.3 | Migration strategy (SQLite to Neon Postgres) | ARCH | 0.2 | `docs/MIGRATION_STRATEGY.md` |
| 0.4 | Risk matrix with mitigations | ARCH | 0.2 | `docs/RISK_MATRIX.md` |

### Phase 1: Google Cloud Infrastructure (Day 2)

| ID | Task | Owner | Depends On | Deliverable |
|---|---|---|---|---|
| 1.1 | gcloud project setup guide | DEV-1 | 0.2 | `docs/CLOUD_SETUP.md` |
| 1.2 | Cloud Run service YAML | DEV-1 | 0.2 | `cloudrun-service.yaml` |
| 1.3 | `/health` endpoint + tests | DEV-1 | 0.2 | `routes/health.py`, `tests/test_health.py` |
| 1.4 | Deploy CD pipeline (GH Actions) | DEV-1 | 1.1, 1.2 | `.github/workflows/deploy-cloudrun.yml` |
| 1.5 | Dockerfile review for Cloud Run | SENIOR-1 | 0.2 | Updated `Dockerfile` (review only -- already good) |

### Phase 2: Database Migration (Day 2-3)

| ID | Task | Owner | Depends On | Deliverable |
|---|---|---|---|---|
| 2.1 | Postgres schema compatibility audit | ARCH | 0.2 | `docs/POSTGRES_COMPAT.md` |
| 2.2 | `config.py` Postgres connection update | SENIOR-1 | 2.1 | Updated `config.py` |
| 2.3 | Data migration script | DEV-2 | 2.1 | `scripts/migrate_to_postgres.py` |
| 2.4 | Seed script Postgres verification | DEV-2 | 2.1 | Updated `seed_data/seed.py`, `seed_data/meals.py` |

### Phase 3: App Adaptation (Day 3)

| ID | Task | Owner | Depends On | Deliverable |
|---|---|---|---|---|
| 3.1 | Session management Cloud Run review | SENIOR-2 | 1.5 | Documentation in ADR |
| 3.2 | `.env.production.example` | SENIOR-2 | 2.2 | `.env.production.example` |
| 3.3 | Secret Manager setup commands | SENIOR-2 | 1.1 | In `docs/CLOUD_SETUP.md` |

### Phase 4: TWA Android Wrapper (Day 4)

| ID | Task | Owner | Depends On | Deliverable |
|---|---|---|---|---|
| 4.1 | TWA architecture design | ARCH | 0.2 | `docs/TWA_ARCHITECTURE.md` |
| 4.2 | Bubblewrap configuration | SENIOR-2 | 4.1 | `twa-manifest.json` |
| 4.3 | Digital Asset Links setup | SENIOR-2 | 4.1 | `static/.well-known/assetlinks.json`, route |
| 4.4 | PWA manifest update (add PNG icons) | SENIOR-2 | 4.5 | Updated `static/manifest.json` |
| 4.5 | Icon generation script + assets | DEV-3 | 4.1 | `scripts/generate_icons.py`, `static/icons/*.png` |
| 4.6 | Service worker update for offline page | DEV-3 | -- | Updated `static/sw.js` |

### Phase 5: Monetization (Day 4-5)

| ID | Task | Owner | Depends On | Deliverable |
|---|---|---|---|---|
| 5.1 | Freemium feature design | ARCH | 0.2 | In ADR |
| 5.2 | Premium feature gate decorator | SENIOR-1 | 5.1 | Updated `routes/auth.py` |
| 5.3 | Apply premium gates to routes | SENIOR-1 | 5.2 | Multiple route files |
| 5.4 | AdMob web banner integration | SENIOR-1 | 5.1 | Updated `templates/base.html` |
| 5.5 | Privacy policy page | DEV-3 | 5.1 | `templates/privacy.html`, route |
| 5.6 | Terms of service page | DEV-3 | 5.1 | `templates/terms.html`, route |
| 5.7 | Play Store listing copy | DEV-3 | 4.5 | `docs/PLAY_STORE_LISTING.md` |

### Phase 6: Testing & QA (Day 5)

| ID | Task | Owner | Depends On | Deliverable |
|---|---|---|---|---|
| 6.1 | Test suite Postgres compat review | SENIOR-1 | 2.2 | Documented in ADR |
| 6.2 | Cloud Run smoke test script | SENIOR-2 | 3.1 | `scripts/smoke_test.py` |
| 6.3 | Pre-launch checklist | DEV-1 | All | `LAUNCH_CHECKLIST.md` |

### Phase 7: Synthesis (Day 5)

| ID | Task | Owner | Depends On | Deliverable |
|---|---|---|---|---|
| 7.1 | Final handoff document | MAESTRO | All | `docs/HANDOFF.md` |

### Dependency Graph

```
Phase 0 (MAESTRO kickoff + ARCH architecture)
         |
    +----+----+
    v         v
Phase 1       Phase 2
(Cloud Run)   (DB migration)
    +----+----+
         |
    Phase 3 (App adaptation)
         |
    +----+----+
    v         v
Phase 4       Phase 5
(TWA/Android) (Monetization)
    +----+----+
         |
    Phase 6 (QA & smoke tests)
         |
    Phase 7 (MAESTRO synthesis)
```

---

## 4. Risk Register

### RISK-01 [HIGH]: SQLite WAL Pragma on Postgres

- **Description:** `PRAGMA journal_mode=WAL` and `PRAGMA synchronous=NORMAL` are SQLite-specific. If executed against Postgres, they will fail and crash the app on startup.
- **Current State:** ALREADY MITIGATED. The `app.py:65` guard `if 'sqlite' in app.config['SQLALCHEMY_DATABASE_URI']` prevents WAL pragmas from running on Postgres. Verified in codebase review.
- **Residual Risk:** Low. Any future contributor adding SQLite pragmas outside the guarded block could reintroduce this. ARCH should document this in ADR.
- **Owner:** ARCH (document), SENIOR-1 (verify in testing)
- **Mitigation:** Add a code comment at `app.py:65` explaining why the guard exists. Add a test that creates the app with a `postgresql://` URL and verifies no pragma errors.

### RISK-02 [HIGH]: Haiku Agents Touching Auth Files

- **Description:** DEV-1, DEV-2, DEV-3 (Haiku 4.5 models) have lower reasoning capacity and MUST NOT modify security-sensitive files without SENIOR review. Auth-related files: `routes/auth.py`, `models/user.py`, `config.py` (SECRET_KEY), session handling in `app.py`.
- **Current State:** No guardrails in place -- purely a process control.
- **Owner:** MAESTRO (enforce in briefs), SENIOR-1 (review gate)
- **Mitigation:** Each Haiku agent brief explicitly lists forbidden files. Any PR from a Haiku agent that touches `routes/auth.py`, `models/user.py`, or `config.py` must be reviewed by SENIOR-1 before merge.

### RISK-03 [HIGH]: SECRET_KEY Stability on Stateless Cloud Run

- **Description:** Cloud Run instances are ephemeral. If `SECRET_KEY` is generated randomly at startup, each new instance gets a different key, invalidating all existing user sessions (cookie signatures won't match). Users would be logged out on every cold start or scale-up event.
- **Current State:** `config.py:10` reads `SECRET_KEY` from env var with fallback `'dev-only-replace-in-production'`. This is safe IF the env var is set in Cloud Run. If forgotten, all instances share the hardcoded dev key (insecure but stable).
- **Owner:** SENIOR-1 (config), DEV-1 (Cloud Run YAML)
- **Mitigation:** (1) Store `SECRET_KEY` in Google Secret Manager. (2) Reference it in `cloudrun-service.yaml` via `secretKeyRef`. (3) Add startup check in `app.py` that logs a CRITICAL warning if `SECRET_KEY` equals the default dev value in production. (4) Add to `LAUNCH_CHECKLIST.md`.

### RISK-04 [HIGH]: `valid_units` Column as JSON String

- **Description:** `saved_food.valid_units` is a `VARCHAR(500)` storing JSON-encoded strings like `'["g","ml","piece"]'`. This works identically in SQLite and Postgres (both treat it as a plain string), but any code doing `json.loads(food.valid_units)` must handle `None` values (new foods may have NULL).
- **Current State:** Column exists, no filtering in food search UI yet (noted in CLAUDE.md known bugs). Postgres compatibility is fine since it is stored as a string, not a native JSON type.
- **Owner:** DEV-2 (verify in migration), ARCH (document in compat audit)
- **Mitigation:** Migration script must transfer `valid_units` as-is. No type change needed. Document that future refactoring to Postgres native `JSONB` is optional.

### RISK-05 [MEDIUM]: CI Branch Name Mismatch

- **Description:** `.github/workflows/ci.yml` triggers on `main` branch. CLAUDE.md git instructions reference `master`. The actual default branch is `main`.
- **Current State:** Active discrepancy in documentation.
- **Owner:** DEV-1 (fix in CLAUDE.md update)
- **Mitigation:** All agents use `main`. Update CLAUDE.md git section. New deploy workflow must also trigger on `main`.

### RISK-06 [MEDIUM]: Neon Postgres Connection Limits (Free Tier)

- **Description:** Neon free tier allows limited concurrent connections (typically 5-10). Cloud Run can scale to 10 instances with `pool_size=5` each = 50 connections, exceeding the limit.
- **Current State:** `app.py:24` sets `pool_size: 5, max_overflow: 2` -- up to 7 connections per instance.
- **Owner:** ARCH (design), SENIOR-1 (implement)
- **Mitigation:** (1) Use Neon connection pooler endpoint (PgBouncer). (2) Reduce pool_size to 2 with max_overflow 1 for free tier. (3) Document upgrade path. (4) `pool_pre_ping: True` already set -- handles stale connections.

### RISK-07 [MEDIUM]: Missing PNG Icons for Play Store

- **Description:** Play Store requires specific PNG icon sizes (48, 72, 96, 144, 192, 512px) plus adaptive icon layers. Currently only an SVG icon exists (`static/icon.svg`). The manifest references only the SVG.
- **Current State:** No PNG icons exist. `static/icons/` directory does not exist.
- **Owner:** DEV-3 (generate), SENIOR-2 (reference in TWA config)
- **Mitigation:** DEV-3 creates a Python script using Pillow to generate all sizes from a source image. Source image must be provided by user or designed.

### RISK-08 [MEDIUM]: Service Worker Cache Invalidation

- **Description:** The existing service worker (`static/sw.js`) uses a fixed cache name `nutritrack-v1`. After deployment, users may see stale cached content until the service worker updates. Cache-first strategy for static assets means old CSS/JS could persist.
- **Owner:** DEV-3 (update), SENIOR-2 (review)
- **Mitigation:** Implement versioned cache names (e.g., `nutritrack-v2` on each deploy). Consider a cache-busting query param strategy for static assets.

### RISK-09 [MEDIUM]: Docker Image Size (spaCy Model)

- **Description:** The spaCy `en_core_web_sm` model adds ~50MB to the Docker image. Cloud Run cold starts are slower with larger images. Image is already `python:3.12-slim` but spaCy adds significant weight.
- **Current State:** Model download is in Dockerfile line 13. Required for offline NLP chat.
- **Owner:** SENIOR-1 (evaluate)
- **Mitigation:** (1) Accept the size for MVP. (2) Consider lazy-loading spaCy model on first chat request rather than at import. (3) Future: move NLP to a separate Cloud Run service.

### RISK-10 [LOW]: `_migrate_add_columns` DDL on Every Startup

- **Description:** `_migrate_add_columns()` runs 20+ DDL statements on every app startup. On Postgres with `IF NOT EXISTS`, these are no-ops but add startup latency.
- **Current State:** Each statement runs in its own transaction. On Postgres, `IF NOT EXISTS` makes them safe and fast.
- **Owner:** SENIOR-1 (monitor)
- **Mitigation:** Acceptable for now. Future: migrate to Alembic-only schema management and remove `_migrate_add_columns()`.

### RISK-11 [LOW]: Railway TCP Keepalive Settings in Cloud Run

- **Description:** `app.py:26-33` has TCP keepalive settings (`keepalives_idle=60`, etc.) with a comment referencing Railway. These settings are harmless on Cloud Run but the comment is misleading.
- **Owner:** SENIOR-1 (cleanup)
- **Mitigation:** Update comment to be provider-agnostic. Settings are beneficial for any cloud environment.

### RISK-12 [LOW]: Play Store Rejection Risk (Content Policy)

- **Description:** Google Play Store review can reject apps for privacy policy issues, misleading descriptions, or content policy violations. Health & Fitness apps face extra scrutiny.
- **Owner:** DEV-3 (legal pages), MAESTRO (review)
- **Mitigation:** (1) GDPR-compliant privacy policy required. (2) No health claims in listing copy. (3) AdMob disclosure required. (4) Data safety section must be accurate.

---

## 5. Agent Briefs

---

### Brief: ARCH (Opus 4.6) -- Software Architect

**Role:** Produce all architecture decisions, schema compatibility audit, and migration strategy.

**Files to Read (in order):**

1. `app.py` (entire file -- factory pattern, `_migrate_add_columns`, `_auto_seed`, WAL guard, blueprint registration)
2. `config.py` (env var reading, `DATABASE_URL` handling, `SECRET_KEY`, session lifetime)
3. `models/__init__.py` + all 14 model files in `models/`
4. `seed_data/seed.py` and `seed_data/meals.py`
5. `routes/auth.py` (session handling, `login_required` decorator)
6. `static/manifest.json` (existing PWA manifest)
7. `static/sw.js` (existing service worker)
8. This kickoff document (for risk register context)

**Deliverables:**

1. **`docs/ADR.md`** -- Architecture Decision Record covering:
   - Cloud Run deployment model (stateless gunicorn, cookie sessions, PORT binding)
   - Postgres adapter choice (psycopg2-binary already present, connection pooling for Neon free tier)
   - Migration approach (fresh `db.create_all()` on Neon + one-time data migration script, vs. Alembic)
   - TWA architecture (Digital Asset Links flow, Chrome 72+ requirement, offline service worker strategy)
   - Freemium design (which features behind paywall, how `plan_feature_enabled` maps to gates)
   - Session management on Cloud Run (cookie-based is fine, SECRET_KEY from Secret Manager)

2. **`docs/MIGRATION_STRATEGY.md`** -- Step-by-step plan:
   - Neon DB provisioning
   - Schema creation approach
   - Data transfer order (respecting FK constraints: users first, then saved_foods, food_entries, etc.)
   - Row count verification (751 USDA + 5,259 meals + user data)
   - Rollback procedure

3. **`docs/RISK_MATRIX.md`** -- Detailed mitigations for all HIGH risks, confirming:
   - WAL pragma guard already exists (verify, document)
   - `valid_units` as VARCHAR(500) is Postgres-safe
   - SECRET_KEY must come from env var / Secret Manager
   - Connection pool sizing for Neon free tier

4. **`docs/POSTGRES_COMPAT.md`** -- Every model field confirmed or flagged:
   - All 14 models, all column types
   - `db.Float`, `db.String`, `db.Date`, `db.DateTime`, `db.Integer`, `db.Boolean` -- all portable
   - AUTOINCREMENT vs SERIAL (SQLAlchemy handles this)
   - `ON DELETE CASCADE` and `ON DELETE SET NULL` (Postgres supports both)
   - Unique constraints and indexes

**Acceptance Criteria:**
- [ ] ADR covers all 6 architecture topics with rationale and alternatives considered
- [ ] Migration strategy has a numbered step list that can be executed sequentially
- [ ] Every model in `models/` is listed in POSTGRES_COMPAT.md with a Compatible or Needs Change verdict
- [ ] Risk matrix addresses all HIGH risks from this kickoff document
- [ ] No architecture decision requires changes to the existing SQLAlchemy model definitions

---

### Brief: SENIOR-1 (Sonnet 4.6) -- Backend Developer

**Role:** Postgres migration configuration, Dockerfile review, premium feature gates, AdMob integration.

**Files to Read:**

1. `config.py` (env vars, pool settings)
2. `app.py` (full file -- WAL guard, `_migrate_add_columns`, pool settings at line 21-37)
3. `Dockerfile` (already uses PORT var -- verify, review for optimization)
4. `docker-compose.yml` (commented Postgres config)
5. `routes/auth.py` (for `premium_required` decorator placement)
6. `templates/base.html` (for AdMob banner placement)
7. `static/js/i18n.js` (for premium/upgrade translations)
8. `requirements.txt` (version pinning review)
9. This kickoff document (risks and acceptance criteria)
10. ARCH deliverables when available (ADR, POSTGRES_COMPAT.md)

**Deliverables:**

1. **Updated `config.py`** -- Neon Postgres optimizations:
   - Verify `pool_pre_ping: True` and `pool_recycle: 240` are suitable for Neon
   - Add `sslmode=require` to `connect_args` (already partially done in app.py, consolidate)
   - Reduce `pool_size` to 2 and `max_overflow` to 1 for Neon free tier compatibility
   - Update Railway-specific comments to be Cloud Run/Neon-aware

2. **Dockerfile review** -- Confirm suitability for Cloud Run:
   - `PORT` env var binding: ALREADY DONE (`${PORT:-8080}`)
   - `EXPOSE 8080`: ALREADY DONE
   - gunicorn workers: currently hardcoded to 2, evaluate if dynamic formula is better
   - HEALTHCHECK instruction (optional -- Cloud Run uses HTTP probe, not Docker HEALTHCHECK)
   - Document that no changes are needed OR produce updated Dockerfile

3. **`routes/auth.py` update** -- Add `premium_required` decorator:
   - Checks `session['user_id']` and `user.plan_feature_enabled`
   - Returns 402 with `{'error': 'Premium required', 'upgrade_url': '/upgrade'}` for non-premium users
   - Apply to: CSV export route, social routes (configurable), unlimited meal templates

4. **`templates/base.html` update** -- AdMob web banner:
   - Add AdMob script tag (with placeholder `ca-pub-XXXXXXXX`)
   - JS check: only show ads if NOT premium user and in TWA context
   - Placement: bottom banner, non-intrusive

5. **`static/js/i18n.js` update** -- Add premium/upgrade translations:
   - EN: "Upgrade to Premium", "Premium Feature", etc.
   - TR: "Premium'a Yuksel", "Premium Ozellik", etc.

**CONSTRAINTS:**
- Do NOT change SQLAlchemy model definitions (column types, table names)
- Do NOT modify `_migrate_add_columns()` logic (ARCH reviews this)
- Do NOT remove the SQLite WAL pragma guard
- All config changes must maintain backward compatibility with SQLite for local development

**Acceptance Criteria:**
- [ ] `config.py` handles both SQLite (local dev) and Postgres (production) cleanly
- [ ] Dockerfile runs on Cloud Run without modification (verify PORT, workers, health)
- [ ] `premium_required` decorator returns 402 with upgrade URL for non-premium users
- [ ] AdMob script has placeholder IDs clearly marked for replacement
- [ ] i18n translations cover all new premium-related UI strings in both EN and TR
- [ ] All 81 existing tests still pass (test with SQLite, no Postgres needed for tests)

---

### Brief: SENIOR-2 (Sonnet 4.6) -- Android/TWA Developer

**Role:** TWA wrapper configuration, Digital Asset Links, session review, smoke tests.

**Files to Read:**

1. `static/manifest.json` (existing PWA manifest -- needs PNG icons added)
2. `static/sw.js` (existing service worker -- review for TWA compatibility)
3. `routes/pages.py` (add assetlinks.json route)
4. `routes/auth.py` (session handling review)
5. `templates/base.html` (PWA meta tags, service worker registration)
6. `config.py` (SECRET_KEY handling for session stability)
7. This kickoff document (risks, especially RISK-03 SECRET_KEY)
8. ARCH deliverables when available (TWA_ARCHITECTURE.md)

**Deliverables:**

1. **`twa-manifest.json`** -- Complete Bubblewrap configuration:
   - `packageId`: placeholder `com.nutritrack.app` (user must confirm)
   - `host`: placeholder `nutritrack.yourdomain.com` (user must provide domain)
   - Theme/nav colors: `#2D7A4F` (green, matching nutrition theme)
   - Icon URLs pointing to `/static/icons/icon-512.png`
   - Signing key config (path, alias)
   - `minSdkVersion: 21`, `targetSdkVersion: 34`

2. **Updated `static/manifest.json`** -- Add PNG icon entries:
   - 192x192 and 512x512 PNG icons
   - Verify `display: standalone`, `start_url: /`
   - Update `theme_color` to match TWA config

3. **`static/.well-known/assetlinks.json`** -- Template with placeholder fingerprint

4. **Route in `routes/pages.py`** -- Serve assetlinks.json at `/.well-known/assetlinks.json`

5. **`.env.production.example`** -- All production env vars documented

6. **`scripts/smoke_test.py`** -- Cloud Run verification script:
   - Health check, login page, register page, dashboard redirect, API auth gate, assetlinks

7. **Session management documentation** -- Confirm cookie-based sessions are Cloud Run safe

**CONSTRAINTS:**
- Do NOT modify `routes/auth.py` session logic
- Do NOT change existing service worker caching strategy
- TWA config must use placeholders for user-specific values

**Acceptance Criteria:**
- [ ] `twa-manifest.json` is valid JSON and follows Bubblewrap schema
- [ ] `assetlinks.json` route returns correct `Content-Type: application/json`
- [ ] `manifest.json` has both SVG and PNG icon entries
- [ ] Smoke test script can be run with `python scripts/smoke_test.py <base_url>`
- [ ] `.env.production.example` lists every env var with descriptions
- [ ] Session review confirms no server-side session storage

---

### Brief: DEV-1 (Haiku 4.5) -- Infrastructure Developer

**Role:** Google Cloud setup guide, Cloud Run config, GitHub Actions deploy, health endpoint.

**Files to Read:**

1. `.github/workflows/ci.yml` (existing CI -- add deploy as SEPARATE workflow)
2. `Dockerfile` (understand build process)
3. `docker-compose.yml` (understand current config)
4. `app.py` lines 333-370 (blueprint registration pattern)
5. `routes/pages.py` (pattern for adding new routes)
6. This kickoff document (risks, especially RISK-05 branch name)

**Deliverables:**

1. **`docs/CLOUD_SETUP.md`** -- Copy-pasteable gcloud setup guide
2. **`cloudrun-service.yaml`** -- Knative service definition with Secret Manager refs
3. **`routes/health.py`** -- Health check endpoint (`GET /health`)
4. **`tests/test_health.py`** -- Tests for health endpoint
5. **`.github/workflows/deploy-cloudrun.yml`** -- CD pipeline on `main` branch
6. **`LAUNCH_CHECKLIST.md`** -- Pre-launch verification checklist

**FORBIDDEN FILES (do not modify):**
- `routes/auth.py`, `models/user.py`, `config.py`, any file in `models/`

**Acceptance Criteria:**
- [ ] `/health` returns 200 with JSON body including `status` and `db` keys
- [ ] Health endpoint test passes with `pytest tests/test_health.py -v`
- [ ] `deploy-cloudrun.yml` triggers only on `main` branch push
- [ ] `CLOUD_SETUP.md` commands are copy-pasteable
- [ ] `cloudrun-service.yaml` references Secret Manager for sensitive values
- [ ] `LAUNCH_CHECKLIST.md` has checkboxes for every critical item

---

### Brief: DEV-2 (Haiku 4.5) -- Database Migration Developer

**Role:** Write the one-time SQLite-to-Postgres migration script, verify seed scripts.

**Files to Read:**

1. `models/__init__.py` + all 14 model files (understand schema, FKs)
2. `seed_data/seed.py` and `seed_data/meals.py`
3. `app.py` lines 79-97 and 383-413 (`_create_all_if_needed`, `_auto_seed`, `_patch_name_tr`)
4. This kickoff document (RISK-04 valid_units, row counts)
5. ARCH deliverables when available (POSTGRES_COMPAT.md)

**Deliverables:**

1. **`scripts/migrate_to_postgres.py`** -- One-time data migration:
   - Env vars: `SQLITE_URL` and `POSTGRES_URL`
   - FK-ordered table migration (users first, then dependent tables)
   - Bulk insert in chunks of 500
   - Idempotent (skip existing PKs)
   - Row count verification output
   - `valid_units` transferred as-is, `name_tr` UTF-8 preserved

2. **Seed script verification** -- Review and document Postgres compatibility

**FORBIDDEN FILES (do not modify):**
- `routes/auth.py`, `models/user.py`, `config.py`, any model file in `models/`

**Acceptance Criteria:**
- [ ] Script runs without error when both URLs are valid
- [ ] Script prints table-by-table row counts
- [ ] Script is idempotent (no duplicates on re-run)
- [ ] `valid_units` and `name_tr` transfer correctly
- [ ] Seed scripts verified compatible with Postgres

---

### Brief: DEV-3 (Haiku 4.5) -- Assets & Copy Developer

**Role:** Generate app icons, write legal pages, create Play Store listing copy, update service worker.

**Files to Read:**

1. `static/manifest.json`, `static/sw.js`, `static/icon.svg`
2. `templates/base.html` (page structure)
3. `routes/pages.py` (for adding privacy/terms routes)
4. This kickoff document (RISK-07 icons, RISK-12 Play Store policies)

**Deliverables:**

1. **`scripts/generate_icons.py`** -- Pillow-based icon generator (6 sizes + maskable)
2. **`templates/privacy.html`** -- GDPR-compliant privacy policy (extends base.html)
3. **`templates/terms.html`** -- Terms of service (extends base.html)
4. **Routes in `routes/pages.py`** -- `/privacy` and `/terms`
5. **Updated `static/sw.js`** -- Offline fallback page, versioned cache name
6. **`docs/PLAY_STORE_LISTING.md`** -- Complete listing copy (title, descriptions, keywords)

**FORBIDDEN FILES (do not modify):**
- `routes/auth.py`, `models/user.py`, `config.py`, any file in `models/`, `app.py`

**Acceptance Criteria:**
- [ ] Icon script produces all 6 sizes when run
- [ ] Privacy policy covers GDPR requirements + AdMob disclosure
- [ ] Terms of service covers standard sections
- [ ] `/privacy` and `/terms` routes return 200
- [ ] Play Store copy fits within character limits
- [ ] Service worker shows offline page when network unavailable

---

## 6. Open Questions (Require User Input)

### OQ-1: Custom Domain Name
- **Question:** What domain will NutriTrack be hosted on?
- **Why:** Required for Digital Asset Links, TWA config, Play Store listing.
- **Default:** Use Cloud Run `.run.app` URL initially; add custom domain later.

### OQ-2: Android Package ID
- **Question:** What package ID for the TWA app? (e.g., `com.nutritrack.app`)
- **Why:** Permanent once published -- cannot be changed.
- **Default:** `com.nutritrack.app`

### OQ-3: AdMob Publisher ID and Ad Unit IDs
- **Question:** Do you have a Google AdMob account with publisher and ad unit IDs?
- **Why:** Required for ad integration.
- **Default:** Use placeholder IDs; replace before launch.

### OQ-4: Signing Keystore
- **Question:** Existing Android signing keystore, or generate new?
- **Why:** SHA-256 fingerprint needed for assetlinks.json. Loss = cannot update app.
- **Default:** Generate new with Bubblewrap.

### OQ-5: Google Cloud Project ID
- **Question:** What GCP project ID? (e.g., `nutritrack-prod`)
- **Why:** Used in all infra files.
- **Default:** `nutritrack-prod` as placeholder.

### OQ-6: Neon Postgres Region
- **Question:** Which Neon region? (e.g., `aws-eu-central-1` Frankfurt, `aws-us-east-1` Virginia)
- **Why:** Latency and GDPR data residency.
- **Default:** `aws-us-east-1` for free tier.

### OQ-7: Source App Icon (1024x1024 PNG)
- **Question:** High-res icon available, or generate from existing SVG?
- **Why:** All Play Store icon sizes derived from source.
- **Default:** Convert `static/icon.svg` to PNG.

### OQ-8: Theme Color Decision
- **Question:** Existing manifest uses `#4A90D9` (blue), plan specifies `#2D7A4F` (green). Which?
- **Why:** Affects TWA status bar, splash, branding.
- **Default:** `#2D7A4F` (green) -- better fit for health/nutrition.

### OQ-9: Privacy Policy Contact Email
- **Question:** What email for GDPR data requests?
- **Why:** Required by GDPR and Play Store.
- **Default:** `privacy@nutritrack.app`

### OQ-10: Premium Pricing
- **Question:** Confirm $2.99/month or $19.99/year?
- **Why:** Play Store IAP config and listing copy.
- **Default:** Use plan values as placeholders.

### OQ-11: Google Play Developer Account
- **Question:** Do you have one ($25 one-time)?
- **Why:** Required to publish. 48h identity verification.
- **Default:** Document as prerequisite.

---

## 7. Shared Vocabulary

| Term | Definition |
|---|---|
| **Cloud Run** | Google Cloud Run -- target hosting (stateless containers) |
| **Neon** | Neon Postgres -- managed serverless PostgreSQL |
| **TWA** | Trusted Web Activity -- Chrome wrapper for native-looking Android app |
| **Bubblewrap** | Google CLI for generating TWA Android projects from PWA |
| **DAL / assetlinks** | Digital Asset Links -- `.well-known/assetlinks.json` domain-app proof |
| **GCR** | Google Container Registry -- Docker image storage |
| **Secret Manager** | Google Secret Manager -- secure env var storage |
| **WAL** | Write-Ahead Logging -- SQLite journal mode, NOT used with Postgres |
| **cold start** | Cloud Run spinning up a new container from zero |
| **free tier** | Neon free tier: limited compute hours and connections |
| **premium gate** | Server-side check via `plan_feature_enabled` on User model |
| **USDA foods** | 751 pre-seeded nutrition entries |
| **meal foods** | 5,259 pre-seeded composite meal/dish entries |
| **main** | Default git branch (NOT `master`) |

---

## Appendix: Execution Timeline

| Day | Phase | Agents Active | Key Deliverables |
|---|---|---|---|
| Day 1 | Phase 0 | MAESTRO, ARCH | Kickoff, ADR, migration strategy, risk matrix |
| Day 2 | Phase 1+2 | DEV-1, SENIOR-1, DEV-2 | Cloud setup, health endpoint, config, migration script |
| Day 3 | Phase 2+3 | SENIOR-1, SENIOR-2, DEV-2 | Seed verification, session review, env template |
| Day 4 | Phase 4+5 | SENIOR-2, DEV-3, SENIOR-1, ARCH | TWA config, icons, AdMob, premium gates, legal pages |
| Day 5 | Phase 6+7 | All | Smoke tests, checklist, final synthesis |

---

*End of Day 1 Kickoff Document*
*MAESTRO -- NutriTrack Play Store Deployment Project*