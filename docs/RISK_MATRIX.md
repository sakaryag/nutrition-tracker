# Technical Risk Matrix -- NutriTrack Cloud Deployment

> Created: 2026-08-17
> Status: DRAFT
> Review cycle: Update after each deployment milestone

---

## Risk Scoring

- **Severity**: H (High) = data loss, security breach, or app unusable; M (Medium) = degraded functionality; L (Low) = cosmetic or minor inconvenience
- **Probability**: H (High) = will happen without mitigation; M (Medium) = likely under certain conditions; L (Low) = unlikely but possible
- **Priority**: Severity x Probability -- HH/HM/MH are blockers; ML/LM/LL are tracked but not blocking

---

## Risk Register

### RISK-001: WAL Pragma Execution on PostgreSQL

| Field | Value |
|---|---|
| **ID** | RISK-001 |
| **Description** | SQLite WAL pragma statements (PRAGMA journal_mode=WAL, PRAGMA synchronous=NORMAL, PRAGMA wal_checkpoint) would cause errors if executed against PostgreSQL. PRAGMA is a SQLite-only command. |
| **Severity** | H -- Application would crash on every new database connection |
| **Probability** | L -- Code is already guarded with `if 'sqlite' in URI` check (app.py line 65) |
| **Current Status** | MITIGATED (already guarded) |
| **Mitigation** | The WAL pragma block at app.py:65-74 is inside `if 'sqlite' in app.config['SQLALCHEMY_DATABASE_URI']`. When DATABASE_URL is a postgresql:// string, the entire block (including _backup_db) is skipped. No code change needed. |
| **Verification** | Deploy with DATABASE_URL=postgresql://... and confirm no PRAGMA errors in logs. Add a unit test that creates the app with a Postgres URI and verifies no PRAGMA event listener is registered. |
| **Owner** | Backend team |

---

### RISK-002: Connection Pooling Exhaustion on Cloud Run

| Field | Value |
|---|---|
| **ID** | RISK-002 |
| **Description** | Cloud Run can scale to multiple instances, each running gunicorn with multiple workers. Each worker maintains its own connection pool. With pool_size=5 and max_overflow=2, a single instance could open 7 connections. 10 Cloud Run instances = 70 connections, which could exceed Neon free tier limits. |
| **Severity** | H -- Database connection refused = all requests fail with 500 |
| **Probability** | M -- Depends on traffic patterns. A personal nutrition tracker is unlikely to have 10 concurrent instances, but Cloud Run auto-scaling could spike during unusual traffic. |
| **Current Status** | PARTIALLY MITIGATED (pool settings exist but are oversized) |
| **Mitigation** | 1. Reduce pool_size from 5 to 2 and max_overflow from 2 to 1 (max 3 connections per instance). 2. Set Cloud Run max-instances=3 (caps at 9 connections total). 3. Use Neon pooled endpoint (port 6543, PgBouncer) which multiplexes connections server-side. 4. pool_pre_ping=True already handles stale connection recovery. |
| **Verification** | Load test with 50 concurrent requests. Monitor Neon dashboard for active connection count. Verify pool_pre_ping reconnects after Neon auto-suspend wake-up. |
| **Owner** | Backend + DevOps |

---

### RISK-003: valid_units JSON Stored as String Column

| Field | Value |
|---|---|
| **ID** | RISK-003 |
| **Description** | SavedFood.valid_units is defined as db.String(500) and stores JSON arrays as plain text (e.g., '["g","oz","serving"]'). PostgreSQL has native JSON/JSONB types that support indexing, validation, and querying. Using String means: (a) no DB-level JSON validation, (b) no JSON path queries, (c) 500-char limit could truncate large unit lists. |
| **Severity** | L -- Functionally correct. JSON string parsing works in Python regardless of DB column type. |
| **Probability** | L -- The 500-char limit is generous for unit arrays (typical arrays are 30-60 chars). No JSON queries are performed at the DB level. |
| **Current Status** | ACCEPTED (not a blocker for migration) |
| **Mitigation** | 1. No immediate action required. 2. Future improvement: migrate valid_units to db.JSON type (SQLAlchemy supports this portably). 3. Similarly, UserBadge.badge_meta (db.Text storing JSON) could be migrated to db.JSON. |
| **Verification** | After migration, verify that valid_units values round-trip correctly: insert a SavedFood with valid_units='["g","oz"]', read it back, confirm json.loads() succeeds. |
| **Owner** | Backend team |

---

### RISK-004: SECRET_KEY Stability Across Deployments

| Field | Value |
|---|---|
| **ID** | RISK-004 |
| **Description** | Flask cookie sessions are signed with SECRET_KEY. If the key changes between deployments, ALL existing user sessions are invalidated (users are logged out). The current default is the literal string 'dev-only-replace-in-production', which is (a) insecure and (b) hardcoded as a fallback. |
| **Severity** | H -- If SECRET_KEY is not set: sessions are signed with a known value (security vulnerability). If SECRET_KEY changes: mass logout of all users (poor UX). |
| **Probability** | H -- Without explicit configuration, the dev default will be used in production. Each redeployment that changes the key will log out users. |
| **Current Status** | NOT MITIGATED (critical action required) |
| **Mitigation** | 1. Generate a strong SECRET_KEY: `python -c "import secrets; print(secrets.token_hex(32))"`. 2. Store as a Cloud Run environment variable or Secret Manager secret. 3. NEVER change the key after initial deployment. 4. Remove the dev default fallback in production config (raise error if SECRET_KEY is not set). 5. Add a startup check: `if app.config['SECRET_KEY'] == 'dev-only-replace-in-production': raise ValueError('Set SECRET_KEY for production')`. |
| **Verification** | 1. Deploy, log in, verify cookie is set. 2. Redeploy (same SECRET_KEY), verify session persists. 3. Attempt to access /api/entries without login, verify 401. |
| **Owner** | DevOps + Security |

---

### RISK-005: spaCy Cold Start Latency

| Field | Value |
|---|---|
| **ID** | RISK-005 |
| **Description** | spaCy en_core_web_sm (~50 MB model, ~80 MB installed) adds 1-2 seconds to Python process startup. Combined with Cloud Run container startup (1-3s) and Neon DB wake-up (0.5-1s), total cold start could reach 5-8 seconds. |
| **Severity** | M -- First request after idle period is slow (5-8s). Subsequent requests are fast (<200ms). Not a data loss risk, but poor mobile UX. |
| **Probability** | H -- Cold starts WILL happen on Cloud Run with scale-to-zero (min-instances=0). With Neon auto-suspend after 5 minutes, both services need to wake up. |
| **Current Status** | PARTIALLY MITIGATED (spaCy is lazy-loaded in local_model.py) |
| **Mitigation** | 1. spaCy is already lazy-loaded (only loaded on first /api/chat call, not at import time). Non-chat requests avoid the spaCy load penalty. 2. Set min-instances=1 in Cloud Run for production ($0 CPU cost when idle with CPU-only billing). 3. Use Cloud Scheduler to send a warming request every 5 minutes to /api/chat/status (lightweight, does not load spaCy but keeps the container alive). 4. Consider a startup probe endpoint that preloads spaCy in the background after the first response. |
| **Verification** | Measure cold start time: stop all Cloud Run instances, send a request to /api/chat, measure response time. Target: under 8 seconds. |
| **Owner** | Backend + DevOps |

---

### RISK-006: ALTER TABLE Statements in _migrate_add_columns()

| Field | Value |
|---|---|
| **ID** | RISK-006 |
| **Description** | The _migrate_add_columns() function runs 30+ ALTER TABLE and CREATE TABLE statements on every application startup. On PostgreSQL, these use IF NOT EXISTS, which is safe. However: (a) running DDL on every cold start adds latency, (b) if a new ALTER fails unexpectedly, it could prevent app startup, (c) the function mixes schema creation (CREATE TABLE) with schema evolution (ALTER TABLE ADD COLUMN), which should be separate concerns. |
| **Severity** | M -- A failing ALTER could block app startup. DDL on every start adds 0.5-1s to cold start. |
| **Probability** | L -- IF NOT EXISTS makes ALTERs idempotent on Postgres. Individual transactions prevent cascade failures. But edge cases exist (e.g., column type mismatch, constraint conflicts). |
| **Current Status** | PARTIALLY MITIGATED (individual transactions, IF NOT EXISTS) |
| **Mitigation** | 1. Short-term: Keep _migrate_add_columns() as-is. The pattern works and is battle-tested on the SQLite deployment. 2. Medium-term: Migrate to Flask-Migrate (Alembic) for proper versioned migrations. Flask-Migrate is already installed (imported in app.py line 5). 3. Add the missing is_archived ALTER to the Postgres branch. 4. Add logging to each ALTER so failures are visible (currently silently caught). |
| **Verification** | Deploy to Neon, check application logs for any ALTER errors. Run the app twice to verify idempotency (second startup should complete without DDL changes). |
| **Owner** | Backend team |

---

### RISK-007: Data Migration Idempotency

| Field | Value |
|---|---|
| **ID** | RISK-007 |
| **Description** | When migrating data from SQLite to Neon, the migration script must be idempotent (safe to run multiple times). Risks include: (a) duplicate rows if run twice, (b) primary key conflicts if SERIAL sequences are not reset, (c) foreign key violations if tables are loaded out of order, (d) encoding issues (SQLite stores text as UTF-8, Postgres also UTF-8, but collation differences could surface). |
| **Severity** | H -- Duplicate data or FK violations corrupt the database |
| **Probability** | M -- Migration scripts are typically run once, but retries are common when debugging. Without idempotency, a partial failure + retry creates duplicates. |
| **Current Status** | NOT YET IMPLEMENTED |
| **Mitigation** | 1. Use UPSERT (INSERT ... ON CONFLICT DO NOTHING) for all data migration inserts. 2. Migrate tables in dependency order (Section 5 of MIGRATION_STRATEGY.md). 3. After each table import, reset the SERIAL sequence: `SELECT setval(pg_get_serial_sequence('table', 'id'), COALESCE(MAX(id), 0)) FROM table`. 4. Wrap the entire migration in a transaction with ROLLBACK on error. 5. Add row count verification: compare SQLite and Postgres counts per table. |
| **Verification** | Run the migration script twice. Verify row counts are identical after both runs. Verify no duplicate primary keys or FK violations. |
| **Owner** | Backend team |

---

### RISK-008: Reserved Word "user" as Table Name

| Field | Value |
|---|---|
| **ID** | RISK-008 |
| **Description** | The User model uses __tablename__ = 'user', which is a reserved word in PostgreSQL. All SQL references must quote it as "user". SQLAlchemy ORM handles this automatically, but raw SQL in _migrate_add_columns() and game_engine.py must explicitly quote the table name. |
| **Severity** | H -- Unquoted references to user in raw SQL will cause syntax errors on Postgres |
| **Probability** | L -- All raw SQL references in _migrate_add_columns() already use "user" (quoted). The game_engine.py _upsert_badge() function uses raw SQL but references user_badge, not user directly. |
| **Current Status** | MITIGATED (all current raw SQL is correctly quoted) |
| **Mitigation** | 1. Grep the entire codebase for unquoted raw SQL references to the user table. 2. Add a linting rule or code review check for raw SQL that references "user". 3. Consider renaming the table to "app_user" in a future migration (breaking change, requires careful FK updates). |
| **Verification** | Run: `grep -rn "user" routes/ utils/ --include="*.py"` and verify all raw SQL references use quoted "user". |
| **Owner** | Backend team |

---

### RISK-009: Boolean Column Semantics (SQLite INTEGER vs Postgres BOOLEAN)

| Field | Value |
|---|---|
| **ID** | RISK-009 |
| **Description** | SQLite stores booleans as INTEGER (0/1). PostgreSQL uses native BOOLEAN (true/false). During data migration, INTEGER values must be converted. The ORM handles this transparently for new writes, but migrated data could have issues if raw SQL comparisons use 0/1 instead of true/false. |
| **Severity** | M -- Incorrect boolean comparisons could hide/show wrong data |
| **Probability** | L -- SQLAlchemy ORM abstracts this. Only raw SQL is at risk. The _migrate_add_columns() function already uses correct Postgres defaults (DEFAULT FALSE vs DEFAULT 0). |
| **Current Status** | PARTIALLY MITIGATED (ORM handles conversion, raw SQL is correctly branched) |
| **Mitigation** | 1. Data migration script must cast INTEGER 0/1 to BOOLEAN when inserting into Postgres. 2. FeedVisibility.to_dict() already wraps values in bool() (line 20) -- good defensive practice. 3. Review all raw SQL for boolean comparisons. |
| **Verification** | After migration, query feed_visibility and verify show_in_feed returns proper Python True/False (not 0/1). |
| **Owner** | Backend team |

---

### RISK-010: Neon Auto-Suspend and First-Request Latency Stack

| Field | Value |
|---|---|
| **ID** | RISK-010 |
| **Description** | Both Cloud Run and Neon have auto-suspend features. If both are suspended simultaneously, the first request must: (a) start a Cloud Run instance (2-5s), (b) wake Neon database (0.5-1s), (c) establish a DB connection (0.2-0.5s). Total first-request latency could reach 4-8 seconds. |
| **Severity** | M -- Poor user experience on first app open after idle period. Not a data loss risk. |
| **Probability** | H -- Both services will suspend during overnight/idle periods for a personal tracker. |
| **Current Status** | NOT YET MITIGATED |
| **Mitigation** | 1. Cloud Scheduler: ping /api/chat/status every 5 minutes during 07:00-23:00 local time. Cost: $0 (Cloud Scheduler free tier covers this). 2. Cloud Run min-instances=1: keeps one container warm ($0 with CPU-only billing when idle). 3. pool_pre_ping=True handles Neon reconnection transparently (already configured). 4. Android app (TWA) can show a splash screen during initial load. |
| **Verification** | After deployment, measure cold start time at various times of day. Target: under 6 seconds even with both services suspended. |
| **Owner** | DevOps |

---

### RISK-011: datetime.utcnow Deprecation

| Field | Value |
|---|---|
| **ID** | RISK-011 |
| **Description** | Multiple models use `default=datetime.utcnow` and `onupdate=datetime.utcnow` for timestamp columns. In Python 3.12+, datetime.utcnow() is deprecated in favor of datetime.now(timezone.utc). While still functional, it produces deprecation warnings in logs. |
| **Severity** | L -- No functional impact. Deprecation warnings add log noise. |
| **Probability** | H -- The app uses Python 3.12 (per Dockerfile). Warnings will appear on every model create/update. |
| **Current Status** | ACCEPTED (not blocking, cosmetic) |
| **Mitigation** | Replace all `datetime.utcnow` with `lambda: datetime.now(timezone.utc)` across model files. This is a batch find-and-replace operation. Not blocking for migration but should be done before production to reduce log noise. |
| **Verification** | Run the app and check for DeprecationWarning in stderr/logs. After fix, verify timestamps are still UTC. |
| **Owner** | Backend team |

---

### RISK-012: Missing ORM Models for dietitian_access and dietitian_visit

| Field | Value |
|---|---|
| **ID** | RISK-012 |
| **Description** | The _migrate_add_columns() function creates dietitian_access and dietitian_visit tables via raw SQL, but no corresponding ORM model files exist in the models/ directory. This means: (a) SQLAlchemy is unaware of these tables for query purposes, (b) db.create_all() will not create them (only the raw SQL does), (c) relationships cannot be defined to/from these tables. |
| **Severity** | M -- Tables exist but are inaccessible via ORM. Routes in routes/dietitian.py must use raw SQL or the tables are unused. |
| **Probability** | H -- These tables are created on every startup but have no ORM integration. |
| **Current Status** | NOT MITIGATED |
| **Mitigation** | 1. Create models/dietitian_access.py and models/dietitian_visit.py with proper ORM definitions. 2. Import them in models/__init__.py. 3. This ensures db.create_all() handles them and ORM queries work. |
| **Verification** | After creating the models, run db.create_all() on a fresh database and verify both tables exist. Verify ORM queries work (e.g., DietitianAccess.query.all()). |
| **Owner** | Backend team |

---

### RISK-013: Seed Data Source Column Mismatch

| Field | Value |
|---|---|
| **ID** | RISK-013 |
| **Description** | seed_meals() in seed_data/meals.py sets source='usda' for curated meals, even though they are not from the USDA database. This means _auto_seed() in app.py (which checks `SavedFood.query.filter_by(source='usda').first() is None`) will detect meals as USDA data and skip re-seeding USDA foods if meals were seeded first but USDA foods were not. |
| **Severity** | M -- On a fresh Neon DB, if seed_meals() runs before seed_db(), the 751 USDA ingredient foods will never be seeded because the source='usda' check returns a meal row. |
| **Probability** | L -- In current code flow, _auto_seed() runs before seed_meals() could be called. But if the startup order changes or seed_meals() is called manually first, the bug triggers. |
| **Current Status** | LATENT BUG (not yet triggered in production) |
| **Mitigation** | 1. Change seed_meals() to use source='curated' or source='meal' instead of source='usda'. 2. Update _auto_seed() check to be more specific: filter by source='usda' AND food_type='ingredient'. 3. Or keep source='usda' but make _auto_seed() check for a specific known USDA food (e.g., usda_fdc_id of a common item). |
| **Verification** | On a fresh DB, run seed_meals() first, then _auto_seed(). Verify that both meals (72) and USDA foods (751) are present in saved_food. |
| **Owner** | Backend team |

---

### RISK-014: No HTTPS Enforcement in Flask App

| Field | Value |
|---|---|
| **ID** | RISK-014 |
| **Description** | Cloud Run terminates TLS at the load balancer and forwards HTTP to the container. The Flask app does not set Secure flag on session cookies or enforce HTTPS redirects. This is fine for Cloud Run (all external traffic is HTTPS), but the session cookie Secure flag should be set for defense-in-depth. |
| **Severity** | M -- Session cookies could be intercepted on non-HTTPS connections (unlikely on Cloud Run, but possible in dev/staging) |
| **Probability** | L -- Cloud Run enforces HTTPS for all external traffic. Risk is theoretical. |
| **Current Status** | NOT MITIGATED (low priority) |
| **Mitigation** | 1. Add to production config: `SESSION_COOKIE_SECURE = True` (only send cookie over HTTPS). 2. Add `SESSION_COOKIE_HTTPONLY = True` (prevent JavaScript access). 3. Add `SESSION_COOKIE_SAMESITE = 'Lax'` (CSRF protection). 4. Add ProxyFix middleware for correct HTTPS detection behind Cloud Run load balancer. |
| **Verification** | After deployment, inspect Set-Cookie header in browser DevTools. Verify Secure and HttpOnly flags are present. |
| **Owner** | Security |

---

## Risk Summary

| ID | Risk | Severity | Probability | Status |
|---|---|---|---|---|
| RISK-001 | WAL pragma on Postgres | H | L | MITIGATED |
| RISK-002 | Connection pool exhaustion | H | M | PARTIALLY MITIGATED |
| RISK-003 | valid_units as String not JSONB | L | L | ACCEPTED |
| RISK-004 | SECRET_KEY instability | H | H | NOT MITIGATED (BLOCKER) |
| RISK-005 | spaCy cold start latency | M | H | PARTIALLY MITIGATED |
| RISK-006 | ALTER TABLE on every startup | M | L | PARTIALLY MITIGATED |
| RISK-007 | Data migration idempotency | H | M | NOT YET IMPLEMENTED |
| RISK-008 | Reserved word "user" table | H | L | MITIGATED |
| RISK-009 | Boolean column semantics | M | L | PARTIALLY MITIGATED |
| RISK-010 | Neon + Cloud Run double cold start | M | H | NOT YET MITIGATED |
| RISK-011 | datetime.utcnow deprecation | L | H | ACCEPTED |
| RISK-012 | Missing ORM models for dietitian tables | M | H | NOT MITIGATED |
| RISK-013 | Seed data source column mismatch | M | L | LATENT BUG |
| RISK-014 | No HTTPS enforcement in Flask | M | L | NOT MITIGATED |

### Priority Actions (before deployment)

1. **RISK-004** (BLOCKER): Set production SECRET_KEY, add startup validation
2. **RISK-002**: Reduce pool_size to 2, use Neon pooled endpoint
3. **RISK-007**: Build idempotent migration script with UPSERT
4. **RISK-012**: Create ORM models for dietitian_access and dietitian_visit
5. **RISK-005 + RISK-010**: Configure Cloud Scheduler warming pings

---

*End of risk matrix. Next review after migration script is implemented.*