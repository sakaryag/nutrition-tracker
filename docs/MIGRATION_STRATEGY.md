# SQLite to Neon Postgres Migration Strategy

> Created: 2026-08-17
> Status: DRAFT
> Scope: Full schema audit, data migration plan, and runtime compatibility fixes

---

## Table of Contents

1. [Schema Compatibility Audit](#1-schema-compatibility-audit)
2. [WAL Pragma Fix](#2-wal-pragma-fix)
3. [_migrate_add_columns() Compatibility](#3-_migrate_add_columns-compatibility)
4. [Connection Pool Settings for Cloud Run](#4-connection-pool-settings-for-cloud-run)
5. [Data Migration Order (Dependency Graph)](#5-data-migration-order-dependency-graph)
6. [Seed Data Re-Import](#6-seed-data-re-import)
7. [Migration Execution Checklist](#7-migration-execution-checklist)

---

## 1. Schema Compatibility Audit

Every model file in `models/` has been reviewed against PostgreSQL compatibility. The project uses only portable SQLAlchemy types (`db.Integer`, `db.Float`, `db.String`, `db.Date`, `db.DateTime`, `db.Time`, `db.Text`, `db.Boolean`), which is excellent.

### 1.1 Model-by-Model Review

#### models/food_entry.py -- FoodEntry
- **Status: COMPATIBLE**
- All column types are portable (Integer, String, Float, Date, Time, DateTime)
- `db.ForeignKey('saved_food.id')` and `db.ForeignKey('user.id')` -- valid on Postgres
- `index=True` on `entry_date` and `user_id` -- works on both
- `datetime.utcnow` as default -- works on Postgres (Python-side default, not DB default)
- **No issues found**

#### models/daily_target.py -- DailyTarget
- **Status: COMPATIBLE**
- Portable types: Integer, Float, Date, DateTime
- `db.ForeignKey('user.id')` -- valid
- `water_goal_ml` (Float, nullable) -- no issues
- **No issues found**

#### models/saved_food.py -- SavedFood
- **Status: COMPATIBLE WITH NOTES**
- `usda_fdc_id` has `unique=True` -- Postgres handles this natively
- `valid_units = db.Column(db.String(500))` -- stores JSON as a plain string. This works on Postgres but is not optimal. **Recommendation**: consider migrating to `db.JSON` or `JSONB` column type in a future iteration. For now, String storage is functionally correct.
- `__table_args__` with named indexes -- fully compatible
- `is_archived = db.Column(db.Boolean, default=False)` -- Postgres uses native BOOLEAN (not INTEGER 0/1 like SQLite)
- **FLAG**: `is_archived` column is defined in the ORM model but NOT present in `_migrate_add_columns()`. If the column does not exist in an older DB, `db.create_all()` will add it only on fresh databases. On existing SQLite DBs upgraded to Postgres, this column might be missing. **Action**: Add ALTER TABLE for `is_archived` to the migration list.

#### models/user.py -- User
- **Status: COMPATIBLE**
- `pw_hash = db.Column(db.String(256))` -- werkzeug password hashes are ~120 chars, 256 is sufficient
- `is_admin` and `plan_feature_enabled` are Boolean -- Postgres native BOOLEAN, no issues
- `__tablename__ = 'user'` -- "user" is a reserved word in PostgreSQL. SQLAlchemy already quotes it as `"user"` in the migrations (confirmed in _migrate_add_columns). **Must verify** all raw SQL references quote the table name.
- **No issues found** (quoting is already handled)

#### models/meal_template.py -- MealTemplate
- **Status: COMPATIBLE**
- Standard portable types
- `cascade='all, delete-orphan'` on items relationship -- works on both
- **No issues found**

#### models/meal_template_item.py -- MealTemplateItem
- **Status: COMPATIBLE**
- `db.ForeignKey('meal_template.id')` and `db.ForeignKey('saved_food.id')` -- valid
- `lazy='joined'` on saved_food relationship -- works on Postgres
- **No issues found**

#### models/water_log.py -- WaterLog
- **Status: COMPATIBLE WITH NOTE**
- `user_id` is Integer but has **no ForeignKey constraint** to user table in the ORM model
- The raw SQL in `_migrate_add_columns()` also does not add a FK constraint for this table
- **Not a blocker** but worth noting: orphaned water_log rows possible if a user is deleted
- **No issues found for migration**

#### models/daily_note.py -- DailyNote
- **Status: COMPATIBLE WITH NOTE**
- Same as WaterLog: `user_id` has no FK constraint in ORM model
- `db.Text` maps to TEXT on both SQLite and Postgres -- no issues
- **No issues found for migration**

#### models/friend_connection.py -- FriendConnection
- **Status: COMPATIBLE**
- Both ForeignKeys properly defined
- `UniqueConstraint('requester_id', 'recipient_id', name='uq_friend_connection')` -- portable
- Two relationship definitions with `foreign_keys=` disambiguation -- works on Postgres
- **No issues found**

#### models/feed_visibility.py -- FeedVisibility
- **Status: COMPATIBLE**
- `user_id` with `unique=True` -- Postgres handles this natively
- Boolean columns -- Postgres native BOOLEAN
- **No issues found**

#### models/user_badge.py -- UserBadge
- **Status: COMPATIBLE**
- `UniqueConstraint('user_id', 'badge_key', name='uq_user_badge')` -- portable
- `badge_meta = db.Column(db.Text)` -- stores JSON as text, same consideration as valid_units
- **No issues found**

#### models/shared_entry.py -- SharedEntry
- **Status: COMPATIBLE**
- `ondelete='SET NULL'` on entry_id FK -- Postgres supports this natively (better than SQLite which requires `PRAGMA foreign_keys=ON`)
- Multiple ForeignKeys to food_entry and user -- properly disambiguated with `foreign_keys=`
- **No issues found**

#### models/nutrition_plan.py -- NutritionPlan
- **Status: COMPATIBLE**
- `order_by='PlanTask.day_offset, PlanTask.id'` in relationship -- works on Postgres
- `cascade='all, delete-orphan'` -- works on both
- **No issues found**

#### models/plan_task.py -- PlanTask
- **Status: COMPATIBLE**
- Standard portable types
- `repeat_days = db.Column(db.String(100))` -- stores comma-separated days as string
- **No issues found**

#### models/plan_task_completion.py -- PlanTaskCompletion
- **Status: COMPATIBLE**
- Three ForeignKeys (user, nutrition_plan, plan_task) -- all valid on Postgres
- **No issues found**

#### models/user_plan_assignment.py -- UserPlanAssignment
- **Status: COMPATIBLE**
- `assigned_by` FK to user.id -- valid
- `is_active` Boolean -- Postgres native BOOLEAN
- **No issues found**

### 1.2 Summary of Schema Flags

| Issue | Severity | Model | Action Required |
|---|---|---|---|
| valid_units stored as String not JSONB | Low | SavedFood | Future optimization, not a blocker |
| badge_meta stored as Text not JSONB | Low | UserBadge | Future optimization, not a blocker |
| is_archived not in _migrate_add_columns | Medium | SavedFood | Add ALTER TABLE statement |
| WaterLog.user_id lacks FK constraint | Low | WaterLog | Cosmetic; add FK in future cleanup |
| DailyNote.user_id lacks FK constraint | Low | DailyNote | Cosmetic; add FK in future cleanup |
| "user" is a Postgres reserved word | Info | User | Already quoted in raw SQL; verify all references |

---

## 2. WAL Pragma Fix

### Current Code (app.py lines 65-74)

```python
if 'sqlite' in app.config['SQLALCHEMY_DATABASE_URI']:
    _backup_db(app)
    with app.app_context():
        @event.listens_for(db.engine, 'connect')
        def _set_sqlite_pragma(dbapi_conn, connection_record):
            cursor = dbapi_conn.cursor()
            cursor.execute('PRAGMA journal_mode=WAL')
            cursor.execute('PRAGMA synchronous=NORMAL')
            cursor.execute('PRAGMA wal_checkpoint(PASSIVE)')
            cursor.close()
```

### Assessment

**ALREADY GUARDED.** The WAL pragma block is wrapped in `if 'sqlite' in app.config['SQLALCHEMY_DATABASE_URI']`. When `DATABASE_URL` points to a Postgres connection string (`postgresql://...`), this block is skipped entirely.

**No code change required** for the WAL pragma itself.

### Additional Note

The `_backup_db()` call on line 66 is also inside the same `if` block, so the SQLite file backup logic is correctly skipped for Postgres. This function would fail on Postgres anyway (no local DB file to copy), but the guard prevents it from being called.

---

## 3. _migrate_add_columns() Compatibility

### Current State

The function already has full SQLite/Postgres branching (app.py lines 131-330):

```python
is_pg = 'postgresql' in app.config.get('SQLALCHEMY_DATABASE_URI', '')
if is_pg:
    # PostgreSQL: uses IF NOT EXISTS -- clean, no errors
    migrations = [...]
else:
    # SQLite: uses try/except (no IF NOT EXISTS for ALTER TABLE)
    migrations = [...]
```

### Assessment: MOSTLY COMPATIBLE

The Postgres branch uses:
- `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` -- correct Postgres syntax (9.6+)
- `CREATE TABLE IF NOT EXISTS` -- correct for new tables
- `CREATE INDEX IF NOT EXISTS` -- correct
- `SERIAL PRIMARY KEY` instead of `INTEGER PRIMARY KEY AUTOINCREMENT` -- correct
- `BOOLEAN` instead of `INTEGER` for boolean columns -- correct
- `TIMESTAMP` instead of `DATETIME` -- correct
- Proper quoting of `"user"` table name -- correct

### Issues Found

1. **Missing is_archived ALTER**: The `saved_food.is_archived` column (defined in the ORM model) is not in the migrations list for either SQLite or Postgres. If deploying to a fresh Neon DB via `db.create_all()`, it will be created. But if somehow the table exists without this column, it will be missing. **Action**: Add to both migration branches.

2. **Transaction-per-statement pattern**: Each ALTER runs in its own `with db.engine.connect()` block with individual try/except. This is correct for Postgres where `IF NOT EXISTS` prevents errors, and the individual transactions prevent one failure from aborting others. **No change needed.**

3. **dietitian_access and dietitian_visit tables**: These tables are created in `_migrate_add_columns()` but have NO corresponding ORM model files in the `models/` directory. They exist only as raw SQL. **Action**: Create ORM model files for these tables, or remove the raw SQL if they are not yet needed.

### Required Changes

```python
# Add to Postgres migrations list:
'ALTER TABLE saved_food ADD COLUMN IF NOT EXISTS is_archived BOOLEAN DEFAULT FALSE',

# Add to SQLite migrations list:
'ALTER TABLE saved_food ADD COLUMN is_archived BOOLEAN DEFAULT 0',
```

---

## 4. Connection Pool Settings for Cloud Run

### Current Settings (config.py + app.py)

**config.py** (applies to all DB backends):
```python
SQLALCHEMY_ENGINE_OPTIONS = {
    'pool_pre_ping': True,   # Reconnect stale connections (critical for Neon auto-suspend)
    'pool_recycle': 240,      # Recycle connections every 4 minutes
}
```

**app.py** (Postgres-only, lines 21-37):
```python
if 'postgresql' in app.config.get('SQLALCHEMY_DATABASE_URI', ''):
    opts.update({
        'pool_size': 5,
        'max_overflow': 2,
        'connect_args': {
            'connect_timeout': 10,
            'keepalives': 1,
            'keepalives_idle': 60,
            'keepalives_interval': 10,
            'keepalives_count': 5,
        },
    })
```

### Assessment and Recommendations

The current settings are reasonable but need tuning for Cloud Run + Neon:

| Setting | Current | Recommended | Reason |
|---|---|---|---|
| pool_size | 5 | **2** | Cloud Run default is 1 vCPU. With gunicorn workers=2, each worker gets 1 connection. 5 connections per instance wastes Neon free tier limits. |
| max_overflow | 2 | **1** | Limit burst connections. Neon free tier has a connection limit. |
| pool_pre_ping | True | **True** | Critical: Neon suspends after 5 min idle. pre_ping detects dead connections. |
| pool_recycle | 240 | **300** | 5 minutes matches Neon auto-suspend. Recycling too fast wastes connection setup. |
| connect_timeout | 10 | **10** | Good. Neon wake-up can take 1-2s; 10s gives plenty of buffer. |
| keepalives | Enabled | **Enabled** | Good. Prevents Neon from killing idle connections inside the pool. |

### Required Changes

```python
opts.update({
    'pool_size': 2,       # Reduced: Cloud Run has 1 vCPU, 2 gunicorn workers
    'max_overflow': 1,    # Reduced: limit burst connections on Neon free tier
    'connect_args': {
        'connect_timeout': 10,
        'keepalives': 1,
        'keepalives_idle': 60,
        'keepalives_interval': 10,
        'keepalives_count': 5,
        'sslmode': 'require',  # NEW: Neon requires TLS
    },
})
```

### Neon-Specific: Pooled vs Direct Connection

Neon offers two endpoints:
- **Direct** (port 5432): Full Postgres protocol, supports prepared statements, transactions
- **Pooled** (port 6543, via PgBouncer): Connection multiplexing, lower latency for short queries

**Recommendation**: Use the **pooled endpoint** for Cloud Run. Flask-SQLAlchemy uses short-lived transactions (autocommit mode), which is ideal for PgBouncer transaction-mode pooling. Set `DATABASE_URL` to the pooled endpoint URL.

---

## 5. Data Migration Order (Dependency Graph)

### Table Dependencies (based on ForeignKey analysis)

```
Level 0 (no dependencies -- migrate first):
  user

Level 1 (depends on user):
  daily_target        (user_id -> user.id)
  meal_template       (user_id -> user.id)
  feed_visibility     (user_id -> user.id)
  user_badge          (user_id -> user.id)
  nutrition_plan      (created_by -> user.id)
  friend_connection   (requester_id, recipient_id -> user.id)
  dietitian_access    (dietitian_id, client_id -> user.id)
  dietitian_visit     (dietitian_id, client_id -> user.id)
  water_log           (user_id -- no FK constraint, but logically depends on user)
  daily_note          (user_id -- no FK constraint, but logically depends on user)

Level 2 (depends on Level 0-1):
  saved_food          (no FK dependencies -- can be Level 0, but logically independent)
  plan_task           (plan_id -> nutrition_plan.id)
  user_plan_assignment (user_id -> user.id, plan_id -> nutrition_plan.id)

Level 3 (depends on Level 0-2):
  food_entry          (saved_food_id -> saved_food.id, user_id -> user.id)
  meal_template_item  (template_id -> meal_template.id, saved_food_id -> saved_food.id)
  plan_task_completion (user_id -> user.id, plan_id -> nutrition_plan.id, task_id -> plan_task.id)

Level 4 (depends on Level 3):
  shared_entry        (entry_id -> food_entry.id, shared_by_id -> user.id, shared_to_id -> user.id)
```

### Migration Execution Order

1. **user** -- all other tables reference this
2. **saved_food** -- referenced by food_entry and meal_template_item
3. **daily_target**, **feed_visibility**, **user_badge**, **water_log**, **daily_note** -- user dependents, no cross-deps
4. **nutrition_plan** -- depends on user only
5. **meal_template** -- depends on user only
6. **friend_connection**, **dietitian_access**, **dietitian_visit** -- user-to-user relationships
7. **plan_task** -- depends on nutrition_plan
8. **user_plan_assignment** -- depends on user + nutrition_plan
9. **food_entry** -- depends on user + saved_food
10. **meal_template_item** -- depends on meal_template + saved_food
11. **plan_task_completion** -- depends on user + nutrition_plan + plan_task
12. **shared_entry** -- depends on food_entry + user (last due to deepest FK chain)

### Migration Script Approach

Use `pgloader` or a custom Python script:

```python
# Pseudocode for data migration
import sqlite3
import psycopg2

MIGRATION_ORDER = [
    'user', 'saved_food', 'daily_target', 'feed_visibility',
    'user_badge', 'water_log', 'daily_note', 'nutrition_plan',
    'meal_template', 'friend_connection', 'dietitian_access',
    'dietitian_visit', 'plan_task', 'user_plan_assignment',
    'food_entry', 'meal_template_item', 'plan_task_completion',
    'shared_entry',
]

for table in MIGRATION_ORDER:
    rows = sqlite_cursor.execute(f'SELECT * FROM {table}')
    # Insert into Postgres, preserving primary key values
    # Reset Postgres sequences after insert:
    #   SELECT setval(pg_get_serial_sequence('table', 'id'), MAX(id)) FROM table;
```

**Critical**: After inserting rows with explicit IDs, reset Postgres SERIAL sequences to avoid primary key conflicts on new inserts.

---

## 6. Seed Data Re-Import

### Current Seeding Logic

1. **USDA Foods** (`seed_data/seed.py`): Reads `foods.csv` (751 rows), inserts as `SavedFood` with `source='usda'`. Idempotent check: `SavedFood.query.filter_by(source='usda').first() is None`.

2. **Meals** (`seed_data/meals.py`): 72 curated meals hardcoded in Python. Inserts as `SavedFood` with `food_type='meal'`. Idempotent check: per-row `filter_by(name=..., food_type='meal')`.

3. **Turkish names** (`app.py _patch_name_tr()`): Back-fills `name_tr` from CSV for USDA foods with NULL `name_tr`. Idempotent.

### Strategy for Neon

**Option A: Fresh seed on empty Neon DB (RECOMMENDED for initial deployment)**

If no user data exists yet in the SQLite DB:
1. Deploy to Cloud Run with `DATABASE_URL` pointing to Neon
2. `create_app()` detects empty DB, calls `db.create_all()`
3. `_auto_seed()` inserts 751 USDA foods from CSV
4. `_patch_name_tr()` back-fills Turkish names
5. Run `seed_meals()` to insert 72 meals
6. Done -- no data migration needed

**Option B: Migrate existing SQLite data to Neon**

If user data (food entries, custom foods, templates) exists:
1. Create schema on Neon: run `db.create_all()` via Flask shell or migration
2. Run `_migrate_add_columns()` to add all ALTER columns
3. Export SQLite data using the migration script (Section 5)
4. Import into Neon in dependency order
5. Reset all SERIAL sequences
6. Verify: run `seed_meals()` (idempotent, fills gaps only)
7. Verify: run `_patch_name_tr()` (idempotent, fills gaps only)

### Seed Data Compatibility Notes

- `seed_db()` uses `db.session.bulk_save_objects()` -- works on Postgres
- `seed_meals()` uses individual `db.session.add()` -- works on Postgres
- `_patch_name_tr()` reads CSV file from filesystem -- CSV must be in Docker image (it is, under `seed_data/`)
- `valid_units` in meals.py is stored as a JSON string literal (e.g., `'["g","oz","serving"]'`) -- works as String column on Postgres

---

## 7. Migration Execution Checklist

### Pre-Migration

- [ ] Create Neon project in us-east-2 (or us-central-1 for Cloud Run proximity)
- [ ] Note both direct and pooled connection strings
- [ ] Verify psycopg2-binary is in requirements.txt
- [ ] Set DATABASE_URL in .env to Neon pooled endpoint with ?sslmode=require
- [ ] Generate a production SECRET_KEY: `python -c "import secrets; print(secrets.token_hex(32))"`

### Schema Migration

- [ ] Step 1: Run create_app() against Neon -- creates all tables via db.create_all()
- [ ] Step 2: Verify _migrate_add_columns() runs clean (check logs for errors)
- [ ] Step 3: Add missing is_archived ALTER to _migrate_add_columns() Postgres branch
- [ ] Step 4: Verify all 17 tables exist: user, saved_food, food_entry, daily_target, meal_template, meal_template_item, water_log, daily_note, friend_connection, shared_entry, feed_visibility, user_badge, nutrition_plan, plan_task, plan_task_completion, user_plan_assignment, dietitian_access, dietitian_visit

### Data Migration (if existing data)

- [ ] Step 5: Run migration script in dependency order (Section 5)
- [ ] Step 6: Reset all SERIAL sequences
- [ ] Step 7: Verify row counts match between SQLite and Postgres
- [ ] Step 8: Run seed_meals() to fill any missing meal entries
- [ ] Step 9: Run _patch_name_tr() to fill any missing Turkish names

### Validation

- [ ] Step 10: Run full test suite with DATABASE_URL pointing to Neon branch (not prod)
- [ ] Step 11: Verify WAL pragma is NOT executed (check logs)
- [ ] Step 12: Verify connection pooling works (check for pool_pre_ping reconnections)
- [ ] Step 13: Test API endpoints: /api/foods, /api/entries, /api/summary
- [ ] Step 14: Test auth flow: /login, /register, session persistence
- [ ] Step 15: Test chat pipeline: /api/chat/status, /api/chat

### Post-Migration

- [ ] Step 16: Update Dockerfile for Cloud Run ($PORT env var)
- [ ] Step 17: Deploy to Cloud Run with production DATABASE_URL and SECRET_KEY
- [ ] Step 18: Run smoke tests against production URL
- [ ] Step 19: Set up Cloud Scheduler warming ping (optional, for min cold starts)
- [ ] Step 20: Monitor Neon dashboard for connection count and storage usage

---

*End of migration strategy document.*