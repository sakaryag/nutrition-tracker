# NutriTrack Play Store Deployment — Multi-Agent Workflow Plan

**Scope: Project Preparation Phase Only (No Production Execution)**
Target: Migrate from Railway → Google Cloud Run + Neon Postgres, wrap as TWA Android app, prepare Play Store submission.

---

## Team Roster

| Agent | Model | Role | Why this model |
|---|---|---|---|
| **MAESTRO** | `claude-fable-5` | Orchestrator / Team Manager | Best long-horizon reasoning for complex coordination, makes architectural judgment calls |
| **ARCH** | `claude-opus-5` | Software Architect | Deep reasoning for design decisions, lower cost than Fable 5 |
| **SENIOR-1** | `claude-sonnet-5` | Senior Developer (backend) | Near-Opus quality for implementation tasks at 40% of Opus cost |
| **SENIOR-2** | `claude-sonnet-5` | Senior Developer (Android/TWA) | Same tier, specialized prompt for Android/web |
| **DEV-1** | `claude-haiku-4-5` | Developer (infra & config) | Cheap, fast for boilerplate, YAML, shell scripts |
| **DEV-2** | `claude-haiku-4-5` | Developer (DB migration scripts) | Cheap for repetitive scripting tasks |
| **DEV-3** | `claude-haiku-4-5` | Developer (store assets & copy) | Cheap for content generation, checklists, policy docs |

---

## Phase 0: Kickoff & Codebase Analysis (Day 1, ~2 hours)

### MAESTRO — Orchestrator Initialization

**Reads:**
- `CLAUDE.md` (full project guide)
- `requirements.txt`
- `Dockerfile`, `docker-compose.yml`
- `.github/workflows/ci.yml`

**Produces:**
- Master work breakdown structure (WBS)
- Dependency graph between all 6 phases
- Risk register
- Agent assignment matrix
- Shared vocabulary doc

**Key risks MAESTRO must flag:**
1. `valid_units` column in `saved_food` is a JSON string — Postgres needs same behavior
2. SQLite WAL mode is enabled at connect time — incompatible with Postgres pooler
3. Haiku agents must NOT touch auth-related files without SENIOR review

---

### ARCH — Full Architecture Review

**Reads:**
- `app.py` (factory, blueprints, `_migrate_add_columns`, `_auto_seed`)
- `config.py` (env var reading, DATABASE_URL logic)
- `models/__init__.py` + all 14 model files
- `seed_data/seed.py`, `seed_data/meals.py`

**Task:** Produce Architecture Decision Record (ADR) covering:

1. **Cloud Run deployment model** — stateless gunicorn, how Flask sessions work (cookies, not server-side), impact on existing 30-day session persistence
2. **Postgres adapter choice** — `psycopg2-binary` (already in requirements.txt), connection pooling strategy for Cloud Run cold starts
3. **Migration approach** — `flask db upgrade` via Alembic vs fresh `db.create_all()` for new Neon DB
4. **TWA architecture** — Digital Asset Links flow, minimum Chrome version, offline behavior
5. **Monetization design** — freemium: which features behind paywall, `plan_feature_enabled` column already exists on User model

**Produces:**
- `ADR.md` — architecture decisions with rationale
- `MIGRATION_STRATEGY.md` — step-by-step data transfer plan
- `RISK_MATRIX.md` — mitigations for 3 high risks

---

## Phase 1: Google Cloud Infrastructure (Day 2, ~3 hours)

### DEV-1 — Google Cloud Project Setup Guide

**Task:** Write complete, copy-pasteable setup guide for:

```
gcloud projects create nutritrack-prod
gcloud services enable run.googleapis.com
gcloud services enable containerregistry.googleapis.com
gcloud services enable cloudbuild.googleapis.com
gcloud iam service-accounts create nutritrack-run-sa
```

Also: Neon Postgres account setup, free tier confirmation, connection string format.

**Produces:** `docs/CLOUD_SETUP.md`

---

### DEV-1 — Cloud Run Service Configuration

**Task:** Write `cloudrun-service.yaml`:

```yaml
apiVersion: serving.knative.dev/v1
kind: Service
metadata:
  name: nutritrack
spec:
  template:
    spec:
      containers:
      - image: gcr.io/PROJECT_ID/nutritrack:latest
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: neon-db-url
              key: url
        - name: AUTH_ENABLED
          value: "true"
        - name: SECRET_KEY
          valueFrom:
            secretKeyRef:
              name: flask-secret
              key: key
        resources:
          limits:
            memory: "512Mi"
            cpu: "1"
      minScale: 0
      maxScale: 10
```

Also: Google Secret Manager setup commands for sensitive env vars.

---

### DEV-2 — GitHub Actions CD Pipeline

**Task:** Write `.github/workflows/deploy-cloudrun.yml` that:
1. Triggers on push to `master`
2. Builds Docker image
3. Pushes to Google Container Registry
4. Deploys to Cloud Run via `gcloud run deploy`
5. Runs smoke test (GET /health returns 200)

Note: Existing `.github/workflows/ci.yml` runs pytest — keep that, add deploy as a separate workflow.

---

### SENIOR-1 — Dockerfile Optimization for Cloud Run

**Task:** Review existing Dockerfile and optimize:
- Must use `PORT` env var (Cloud Run sets this, not 5000)
- Remove `EXPOSE 5000` hardcoding → `EXPOSE ${PORT:-8080}`
- gunicorn workers: `$((2 * $(nproc) + 1))` formula
- spaCy model download: already in Dockerfile, verify `en_core_web_sm` download command
- Add `/health` endpoint check as Docker HEALTHCHECK

**Produces:**
- Updated `Dockerfile`
- Updated `app.py` — add `@app.route('/health')` returning `{"status": "ok", "db": "connected"}`

---

## Phase 2: Database Migration (Day 2-3, ~4 hours)

### ARCH — Schema Compatibility Audit

**Task:** Methodically audit all 14 models for Postgres compatibility:

| Model | Issue | Fix |
|---|---|---|
| `saved_food.valid_units` | JSON string in SQLite | `db.String` works in Postgres too — no change needed |
| `food_entry.date` | `db.Date` | Compatible |
| WAL mode pragma | `PRAGMA journal_mode=WAL` in `app.py` | Wrap in `if 'sqlite' in DATABASE_URL:` guard |
| `db.session.execute(db.text('ALTER TABLE...'))` | Works in Postgres | Compatible |
| Auto-increment IDs | SQLite ROWID vs Postgres sequences | SQLAlchemy handles this automatically |

**Produces:** `POSTGRES_COMPAT.md` — every model field confirmed/flagged

---

### SENIOR-1 — config.py Postgres Update

**Task:** Update `config.py` to:
1. Handle Neon Postgres URL format: `postgresql://user:pass@host/db?sslmode=require`
2. Disable SQLite WAL mode when using Postgres
3. Add connection pool settings for Cloud Run

```python
if DATABASE_URL.startswith('postgresql'):
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
        'pool_size': 5,
        'max_overflow': 2,
        'connect_args': {'sslmode': 'require'},
    }
```

Also update `app.py` WAL pragma — wrap in SQLite check:
```python
if 'sqlite' in app.config['SQLALCHEMY_DATABASE_URI']:
    db.engine.execute("PRAGMA journal_mode=WAL")
```

---

### DEV-2 — Data Migration Script

**Task:** Write `scripts/migrate_to_postgres.py`:

```
One-time migration: SQLite nutritrack.db → Neon Postgres

Usage:
  export SQLITE_URL=sqlite:///nutritrack.db
  export POSTGRES_URL=postgresql://...
  python scripts/migrate_to_postgres.py
```

Script steps:
1. Connect to both databases via SQLAlchemy
2. Create all tables on Postgres (`db.create_all()`)
3. Migrate in dependency order (users → saved_foods → food_entries → daily_targets → etc.)
4. Print row counts before/after for verification
5. Idempotent: skip existing rows by primary key

Special handling:
- 751 USDA foods + 5,259 meal foods = big batch, use `bulk_insert_mappings()` in chunks of 500

---

### DEV-2 — Seed Script Update

**Task:** Update `seed_data/seed.py` and `seed_data/meals.py` to work with Postgres (they already use SQLAlchemy — verify and document any issues).

---

## Phase 3: App Adaptation (Day 3, ~3 hours)

### SENIOR-2 — Session Management Review

**Task:** Review Flask session behavior on Cloud Run:
- Current: `session.permanent = True`, 30-day lifetime
- Cloud Run is stateless — Flask cookie sessions are fine (cookies stored client-side)
- Fix: Ensure `SECRET_KEY` comes from env var (already done in config.py), NOT generated randomly at startup

Review `routes/auth.py`: Confirm session uses Flask cookie sessions (not server-side). Document that this is fine for Cloud Run.

---

### SENIOR-2 — Environment Variables Template

**Task:** Create `.env.production.example`:

```
AUTH_ENABLED=true
SECRET_KEY=<generate-with-python-secrets>
DATABASE_URL=postgresql://user:pass@host/nutritrack?sslmode=require
DEFAULT_PROTEIN_TARGET=150
DEFAULT_FAT_TARGET=65
DEFAULT_CARBS_TARGET=250
DEFAULT_CALORIES_TARGET=2200
ANTHROPIC_API_KEY=<optional-enables-chat-backend>
```

Also: Google Secret Manager commands to store each secret.

---

### DEV-1 — Health Check Endpoint

**Task:** Add to `routes/pages.py` (or create `routes/health.py`):

```python
@bp.route('/health')
def health_check():
    try:
        db.session.execute(db.text('SELECT 1'))
        return jsonify({'status': 'ok', 'db': 'connected'}), 200
    except Exception as e:
        return jsonify({'status': 'error', 'db': str(e)}), 500
```

Register blueprint in `app.py`.

---

## Phase 4: TWA Android Wrapper (Day 4, ~5 hours)

### ARCH — TWA Architecture Design Session

**Consults with MAESTRO on:**

1. **Digital Asset Links requirements:**
   - App needs SHA-256 fingerprint of signing key
   - Web domain needs `/.well-known/assetlinks.json`
   - Custom domain strongly recommended for Play Store credibility

2. **Minimum Chrome version for TWA:** Chrome 72+ (all modern Android)

3. **Required assets:**
   - 512x512 PNG icon (mandatory for Play Store)
   - Adaptive icon (foreground + background layers)
   - Feature graphic 1024x500
   - At least 2 screenshots (phone) + 2 (tablet)

4. **Offline behavior decision:**
   - TWA shows Chrome offline page if server down
   - Recommendation: Add service worker with offline page

5. **AdMob integration architecture:**
   - Option A: Google AdMob web (banner in HTML, easiest)
   - Option B: TWA passthrough to native AdMob SDK (complex)
   - Recommendation: Option A for MVP

**Produces:** `docs/TWA_ARCHITECTURE.md`

---

### SENIOR-2 — Bubblewrap Configuration

**Task:** Generate complete TWA project configuration.

Write `twa-manifest.json`:

```json
{
  "packageId": "com.nutritrack.app",
  "host": "nutritrack.yourdomain.com",
  "name": "NutriTrack — Calorie & Macro Tracker",
  "launcherName": "NutriTrack",
  "themeColor": "#2D7A4F",
  "navigationColor": "#2D7A4F",
  "backgroundColor": "#ffffff",
  "startUrl": "/",
  "iconUrl": "https://nutritrack.yourdomain.com/static/icons/icon-512.png",
  "maskableIconUrl": "https://nutritrack.yourdomain.com/static/icons/icon-512-maskable.png",
  "splashScreenFadeOutDuration": 300,
  "signingKey": {
    "path": "./android.keystore",
    "alias": "nutritrack"
  },
  "minSdkVersion": 21,
  "targetSdkVersion": 34,
  "orientation": "default",
  "enableNotifications": false,
  "shortcuts": [],
  "webManifestUrl": "https://nutritrack.yourdomain.com/manifest.json"
}
```

Write `static/manifest.json` (PWA web manifest):

```json
{
  "name": "NutriTrack",
  "short_name": "NutriTrack",
  "start_url": "/",
  "display": "standalone",
  "theme_color": "#2D7A4F",
  "background_color": "#ffffff",
  "icons": [
    {"src": "/static/icons/icon-192.png", "sizes": "192x192", "type": "image/png"},
    {"src": "/static/icons/icon-512.png", "sizes": "512x512", "type": "image/png"}
  ]
}
```

Also: Bubblewrap installation and build commands guide.

---

### SENIOR-2 — Digital Asset Links Setup

**Task:**
1. Write `static/.well-known/assetlinks.json` template:

```json
[{
  "relation": ["delegate_permission/common.handle_all_urls"],
  "target": {
    "namespace": "android_app",
    "package_name": "com.nutritrack.app",
    "sha256_cert_fingerprints": ["<YOUR_SHA256_FINGERPRINT>"]
  }
}]
```

2. Add route in Flask to serve this file (in `routes/pages.py`)

3. Write keystore generation commands:

```bash
keytool -genkey -v -keystore android.keystore -alias nutritrack \
  -keyalg RSA -keysize 2048 -validity 10000
keytool -list -v -keystore android.keystore | grep "SHA256:"
```

---

### DEV-3 — Service Worker for Offline Support

**Task:** Write `static/sw.js` (minimal service worker):
- Cache app shell on install
- Show offline page when network unavailable
- Cache nutrition data for offline viewing (read-only)

Register in `templates/base.html`.

---

### DEV-3 — App Icons & Assets

**Task:** Write specifications and Python script using Pillow to generate all required icon sizes from a source 1024x1024 PNG:
- 48, 72, 96, 144, 192, 512px PNG icons
- Maskable icon variant
- Splash screen dimensions

---

## Phase 5: Monetization Setup (Day 4-5, ~3 hours)

### ARCH — Freemium Feature Design

**Proposed freemium tiers:**
- **Free:** Food logging, macro tracking, daily history (7 days), basic reports
- **Premium (~2.99/month or ~19.99/year):**
  - Unlimited history
  - Social/family features (friends, feed, leaderboard)
  - Meal templates (>5)
  - CSV export
  - AI chat (BYOK stays free — user's own key)
  - Advanced reports

Note: `plan_feature_enabled` column already exists on `User` model — use this as the premium flag.

---

### SENIOR-1 — AdMob Web Integration

**Task:** Add Google AdMob web banner to `templates/base.html`:

```html
<!-- AdMob — only shown in TWA/Android context -->
<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-XXXXXXXXXXXXXXXX"></script>
<ins class="adsbygoogle"
     style="display:block"
     data-ad-client="ca-pub-XXXXXXXXXXXXXXXX"
     data-ad-slot="YYYYYYYYYY"
     data-ad-format="auto"
     data-full-width-responsive="true"></ins>
<script>(adsbygoogle = window.adsbygoogle || []).push({});</script>
```

Add JS check to show ads only in TWA context.
Add to `i18n.js` — Turkish translations for "Upgrade to Premium" UI.

---

### SENIOR-1 — Premium Feature Gates

**Task:** Add server-side feature gate decorator in `routes/auth.py`:

```python
def premium_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.plan_feature_enabled:
            return jsonify({'error': 'Premium required', 'upgrade_url': '/upgrade'}), 402
        return f(*args, **kwargs)
    return decorated
```

Apply to: social routes, export route, unlimited templates.

---

### DEV-3 — Legal Pages

**Task:** Create:
1. `templates/privacy.html` — GDPR-compliant privacy policy (required for Play Store)
2. `templates/terms.html` — Terms of service
3. Routes for both in `routes/pages.py`

Both must cover:
- Data collected (food logs, user account)
- Data storage location (Neon Postgres, EU or US)
- GDPR rights
- AdMob data sharing disclosure
- In-app purchases disclosure

---

### DEV-3 — Play Store Listing Content

**Task:** Write all Play Store listing copy:
- App title (30 chars max): "NutriTrack — Calorie Tracker"
- Short description (80 chars): "Track macros, calories & meals. Offline-first. Family mode. Free."
- Full description (4000 chars): Feature-rich description with keywords
- Content rating questionnaire answers
- Category: Health & Fitness
- Keywords list

---

## Phase 6: Testing & Pre-Launch QA (Day 5, ~2 hours)

### SENIOR-1 — Test Suite Postgres Compatibility

**Task:** Review `tests/conftest.py`:
- Tests use in-memory SQLite — this is fine, keep it for speed
- Verify all 81 tests pass with current SQLite config
- Document that production uses Postgres but tests use SQLite

Write `tests/test_health.py` — integration test for health endpoint.

---

### SENIOR-2 — Cloud Run Smoke Test Script

**Task:** Write `scripts/smoke_test.py`:

```python
TESTS = [
    ("Health check",              "GET", "/health", 200),
    ("Login page",                "GET", "/login",    200),
    ("Register page",             "GET", "/register", 200),
    ("Dashboard redirect (unauth)","GET", "/",        302),
    ("Foods API (unauth)",        "GET", "/api/foods", 401),
]
```

---

### DEV-1 — Pre-Launch Checklist

**Task:** Write `LAUNCH_CHECKLIST.md`:

**Cloud Run:**
- [ ] Health endpoint returns 200
- [ ] DATABASE_URL points to Neon Postgres
- [ ] SECRET_KEY set in Secret Manager
- [ ] AUTH_ENABLED=true
- [ ] All seed data migrated (751 USDA + 5,259 meals)
- [ ] Custom domain configured

**Play Store:**
- [ ] Signing keystore backed up securely
- [ ] assetlinks.json accessible at domain
- [ ] All icon sizes generated
- [ ] Privacy policy URL in app
- [ ] Content rating completed
- [ ] Tested on Android 8.0+ (API 26+)

---

## Phase 7: Deliverables Summary (MAESTRO Synthesis)

MAESTRO compiles final handoff document listing:
- All files created/modified
- Deployment steps in order
- One-command deployment sequence
- Rollback procedure

---

## Token Cost Estimates

### Pricing Reference (2026-08-17)

| Model | Input $/MTok | Output $/MTok |
|---|---|---|
| Claude Fable 5 | $10.00 | $50.00 |
| Claude Opus 5 | $5.00 | $25.00 |
| Claude Sonnet 5 | $2.00* | $10.00* |
| Claude Haiku 4.5 | $1.00 | $5.00 |

*Sonnet 5 introductory pricing through 2026-08-31 (normally $3/$15)

---

### Per-Agent Cost Breakdown

**MAESTRO (Fable 5) — Orchestration**
- ~10 calls across all phases
- Avg: 20K input / 6K output per call
- Total: 200K input + 60K output
- Cost: (200K × $10 + 60K × $50) / 1,000,000 = **$5.00**

**ARCH (Opus 5) — Architecture**
- ~5 calls (ADR, schema audit, TWA design, freemium design, final review)
- Avg: 30K input / 10K output per call
- Total: 150K input + 50K output
- Cost: (150K × $5 + 50K × $25) / 1,000,000 = **$2.00**

**SENIOR-1 (Sonnet 5) — Backend Senior Dev**
- ~8 calls (config.py, Dockerfile, DB migration, health check, feature gates, test review)
- Avg: 12K input / 7K output per call
- Total: 96K input + 56K output
- Cost (intro): (96K × $2 + 56K × $10) / 1,000,000 = **$0.75**

**SENIOR-2 (Sonnet 5) — Android/TWA Senior Dev**
- ~7 calls (session review, Bubblewrap config, assetlinks, service worker, smoke test)
- Avg: 12K input / 8K output per call
- Total: 84K input + 56K output
- Cost (intro): (84K × $2 + 56K × $10) / 1,000,000 = **$0.73**

**DEV-1 (Haiku 4.5) — Infra Dev**
- ~7 calls (gcloud guide, Cloud Run YAML, GH Actions, health endpoint, requirements, checklist)
- Avg: 6K input / 4K output per call
- Total: 42K input + 28K output
- Cost: (42K × $1 + 28K × $5) / 1,000,000 = **$0.18**

**DEV-2 (Haiku 4.5) — DB Migration Dev**
- ~5 calls (migration script, seed update, schema compat check)
- Avg: 7K input / 5K output per call
- Total: 35K input + 25K output
- Cost: (35K × $1 + 25K × $5) / 1,000,000 = **$0.17**

**DEV-3 (Haiku 4.5) — Assets & Copy Dev**
- ~6 calls (service worker, icons script, privacy policy, terms, Play Store listing, checklist)
- Avg: 5K input / 5K output per call
- Total: 30K input + 30K output
- Cost: (30K × $1 + 30K × $5) / 1,000,000 = **$0.18**

---

### Total Cost Summary

| Agent | Model | Cost |
|---|---|---|
| MAESTRO (orchestrator) | Fable 5 | $5.00 |
| ARCH (architect) | Opus 5 | $2.00 |
| SENIOR-1 (backend) | Sonnet 5 | $0.75 |
| SENIOR-2 (Android) | Sonnet 5 | $0.73 |
| DEV-1 (infra) | Haiku 4.5 | $0.18 |
| DEV-2 (database) | Haiku 4.5 | $0.17 |
| DEV-3 (assets) | Haiku 4.5 | $0.18 |
| **TOTAL** | | **~$9.01** |

**Cost optimization options:**
- Swap MAESTRO Fable 5 → Opus 5: saves ~$3.20 (total ~$5.80), slight coordination quality drop
- Swap ARCH Opus 5 → Sonnet 5: saves ~$1.25, may miss subtle architecture issues
- Run before 2026-08-31 to use Sonnet 5 intro pricing (already included above)

---

## Files Created/Modified by End of Project

**New files:**
- `docs/ADR.md`, `docs/MIGRATION_STRATEGY.md`, `docs/TWA_ARCHITECTURE.md`
- `docs/CLOUD_SETUP.md`, `LAUNCH_CHECKLIST.md`
- `cloudrun-service.yaml`
- `.github/workflows/deploy-cloudrun.yml`
- `scripts/migrate_to_postgres.py`, `scripts/smoke_test.py`
- `static/manifest.json`, `static/sw.js`
- `static/.well-known/assetlinks.json`
- `twa-manifest.json`
- `templates/privacy.html`, `templates/terms.html`
- `routes/health.py`
- Icon PNGs (8 sizes in `static/icons/`)

**Modified files:**
- `Dockerfile` (PORT env var, health check)
- `config.py` (Postgres pool settings, SQLite guard)
- `app.py` (WAL pragma guard, health blueprint, premium decorator)
- `requirements.txt` (version pinning review)
- `routes/auth.py` (premium_required decorator)
- `routes/pages.py` (new routes: privacy, terms, assetlinks, manifest)
- `templates/base.html` (AdMob, service worker registration, PWA meta tags)
- `static/js/i18n.js` (upgrade/premium translations)

---

## Execution Order & Dependencies

```
Phase 0 (MAESTRO kickoff + ARCH architecture review)
         |
    +----+----+
    v         v
Phase 1       Phase 2
(Infra setup) (DB migration)
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
    Phase 6 (QA + smoke tests)
         |
    Phase 7 (MAESTRO final synthesis)
         |
    USER: Manual steps (domain, keystore, Play Store submission)
```

---

## What This Plan Does NOT Include (Out of Scope)

- Actual code execution (plan only — start a new session to execute)
- The $25 Google Play developer account registration (manual, one-time)
- Domain purchase and DNS setup (~$12/year)
- APK signing and keystore creation (manual, done once with Bubblewrap)
- Actual Neon account creation (browser-based, manual)
- AdMob account setup and ad unit ID generation (manual)
- Play Store submission review process (7-day Google review)

These are all manual one-time tasks you do yourself after the agents prepare all the code and configuration.
---

## Appendix: Bugs Found by ARCH (Day 1 Audit)

ARCH (Opus 4.6) discovered these issues during the Day 1 codebase audit.
All are being fixed by SENIOR-1 in Day 2.

### Critical — Will Break Postgres Migration

| # | Bug | Location | Fix |
|---|---|---|---|
| 1 | `saved_food.is_archived` column exists in ORM but missing from `_migrate_add_columns()` | `app.py` | Add ALTER TABLE for both SQLite and Postgres branches |
| 2 | `dietitian_access` and `dietitian_visit` tables created via raw SQL in `_migrate_add_columns()` but have no ORM model files | `app.py` | Create `models/dietitian_access.py` and `models/dietitian_visit.py` |

### High — Fix Before Deploy

| # | Bug | Location | Fix |
|---|---|---|---|
| 3 | `WaterLog` and `DailyNote` lack `ForeignKey` constraint to `user` table | `models/water_log.py`, `models/daily_note.py` | Add `db.ForeignKey('user.id')` if missing |
| 4 | `datetime.utcnow` used as column default across all models — deprecated in Python 3.12 | All model files | Replace with `lambda: datetime.now(timezone.utc)` |
| 5 | `pool_size=5` oversized for Cloud Run + Neon free tier | `config.py` (to be added) | Set `pool_size=2, max_overflow=3` |

### Medium — Latent Issues

| # | Bug | Location | Fix |
|---|---|---|---|
| 6 | `seed_meals()` sets `source='usda'` for curated meals — may cause `_auto_seed()` to skip USDA seeding on fresh DB | `seed_data/meals.py` | Change to `source='custom'` or `source='meal'` |
| 7 | `valid_units` stored as `db.String(500)` — functional but not native Postgres JSONB | `models/saved_food.py` | Low priority; works correctly as TEXT in Postgres |

### Confirmed OK (No Action Needed)

| # | Finding | Status |
|---|---|---|
| A | WAL pragma already guarded with SQLite check at `app.py:65` | No change needed |
| B | `_migrate_add_columns()` already has SQLite/Postgres branching with `IF NOT EXISTS` | No change needed |
| C | All column types (`db.Float`, `db.String`, `db.Date`, `db.Integer`) are Postgres portable | No change needed |
| D | `Boolean` columns use `DEFAULT 0/1` (SQLite) vs `DEFAULT FALSE/TRUE` (Postgres) — correctly handled | No change needed |
| E | `INTEGER PRIMARY KEY` auto-increment handled correctly by SQLAlchemy for both databases | No change needed |

