# Architecture Decision Records -- NutriTrack Cloud Deployment

> Maintained by: Architecture Team
> Created: 2026-08-17
> Status: All PROPOSED (pending team review)

---

## ADR-001: Google Cloud Run as Compute Platform

**Status:** PROPOSED
**Date:** 2026-08-17
**Deciders:** Architecture Team

### Context

NutriTrack needs a hosting platform for its Flask backend that supports:
- Docker container deployment (existing Dockerfile with gunicorn)
- HTTPS endpoints for the TWA (Android) wrapper
- Scale-to-zero for cost optimization (single-developer project)
- Managed TLS/SSL certificates
- Easy connection to a managed PostgreSQL service

Alternatives considered:
1. **Google Cloud Run** -- serverless containers
2. **Railway** -- PaaS (docker-compose deployment)
3. **Fly.io** -- edge containers with persistent volumes
4. **AWS App Runner** -- serverless containers on AWS
5. **Self-hosted VPS** (Hetzner, DigitalOcean)

### Decision

Use **Google Cloud Run** as the compute platform.

### Rationale

| Criterion | Cloud Run | Railway | Fly.io | App Runner | VPS |
|---|---|---|---|---|---|
| Free tier | 2M req/mo, 360K vCPU-sec | $5/mo credit (depletes fast) | $5/mo credit | 1M req/mo | None |
| Scale-to-zero | Yes | No (always-on) | Yes (but limited) | Yes | No |
| Docker support | Native | Native | Native | Native | Manual |
| Custom domain + TLS | Free managed | Free managed | Free managed | Free managed | Manual (certbot) |
| Cold start | 2-8s (acceptable) | N/A (always on) | 1-5s | 2-10s | N/A |
| Neon Postgres latency | us-central1 pairing | Variable | Variable | us-east-1 pairing | Variable |
| CI/CD integration | Cloud Build, GitHub Actions | Auto-deploy | flyctl | GitHub Actions | Manual |
| Complexity | Low | Low | Medium | Low | High |

**Key tradeoffs:**
- ACCEPTED: Cold starts of 2-8s (mitigated by min-instances=0 with warming via Cloud Scheduler)
- ACCEPTED: No persistent filesystem (forces proper DB migration away from SQLite)
- ACCEPTED: 15-minute request timeout (sufficient for all NutriTrack endpoints)
- REJECTED Railway: no scale-to-zero burns through free credit quickly for a side project
- REJECTED VPS: operational burden (patching, TLS renewal, monitoring) not justified

### Consequences

- Must migrate from SQLite to external managed database
- Dockerfile must be updated for Cloud Run port ($PORT env var)
- _backup_db() function in app.py becomes no-op (no local SQLite file)
- gunicorn worker count should be set to 1-2 (Cloud Run instances have 1 vCPU default)

---

## ADR-002: Neon Postgres as Managed Database

**Status:** PROPOSED
**Date:** 2026-08-17
**Deciders:** Architecture Team

### Context

Moving from SQLite to a managed PostgreSQL service for Cloud Run deployment. The database must:
- Support the existing SQLAlchemy ORM models without schema changes
- Offer a free tier sufficient for a single-developer nutrition tracker
- Provide low-latency connectivity from Cloud Run (us-central1)
- Handle connection pooling (serverless compute creates/destroys connections rapidly)

Alternatives considered:
1. **Neon** -- serverless Postgres with branching
2. **Supabase** -- Postgres + auth + storage platform
3. **Cloud SQL (GCP)** -- fully managed Postgres on GCP
4. **CockroachDB Serverless** -- distributed SQL
5. **PlanetScale** -- serverless MySQL (would require ORM dialect change)

### Decision

Use **Neon Postgres** (free tier) as the managed database.

### Rationale

| Criterion | Neon | Supabase | Cloud SQL | CockroachDB | PlanetScale |
|---|---|---|---|---|---|
| Free tier storage | 0.5 GB | 500 MB | None ($7/mo min) | 10 GB | 5 GB |
| Free tier compute | 190 hr/mo | Always-on | None | 250M RUs | Unlimited reads |
| Connection pooling | Built-in (PgBouncer) | Built-in (PgBouncer) | Cloud SQL Proxy | Built-in | Built-in |
| Auto-suspend | Yes (5 min idle) | No (always-on, pauses after 1 week inactivity) | No | Yes | Yes |
| Postgres version | 16+ | 15+ | 12-16 | Compat layer | MySQL only |
| Branching (dev/prod) | Yes (free) | No | No | No | Yes |
| SQLAlchemy compat | Native psycopg2 | Native psycopg2 | Native psycopg2 | Via cockroachdb:// | Requires MySQL dialect |
| Wake-up latency | ~0.5-1s | N/A | N/A | ~2s | ~1s |

**Free tier analysis (Neon):**
- 0.5 GB storage: NutriTrack with 751 USDA foods + 72 meals + 1000 food entries is less than 10 MB. Sufficient for 50x growth.
- 190 compute-hours/mo: With auto-suspend after 5 min idle, a personal tracker rarely exceeds 20 hr/mo.
- 10 branches: Enables dev/staging/prod isolation at no cost.
- Built-in PgBouncer: Critical for serverless (Cloud Run) where connections are short-lived and bursty.

**Key tradeoffs:**
- ACCEPTED: 0.5-1s wake-up latency on first request after idle (stacks with Cloud Run cold start)
- ACCEPTED: 0.5 GB storage limit (NutriTrack data is less than 10 MB for foreseeable usage)
- ACCEPTED: Vendor-specific branching feature (standard Postgres underneath, fully portable)
- REJECTED Cloud SQL: No free tier; minimum $7/mo for a side project
- REJECTED PlanetScale: MySQL dialect would require dialect adapter changes throughout ORM layer
- REJECTED Supabase: Heavier platform (auth, storage, realtime) when we only need Postgres

### Consequences

- DATABASE_URL in production will be postgresql://...@ep-xxx.us-east-2.aws.neon.tech/neondb
- Must use ?sslmode=require in connection string (Neon requires TLS)
- Connection pooling endpoint (port 5432 for direct, 6543 for pooled) must be configured correctly
- config.py already handles postgres:// to postgresql:// rewrite (line 13) -- no change needed
- pool_pre_ping: True already set in config.py -- handles Neon auto-suspend reconnection

---

## ADR-003: TWA (Trusted Web Activity) for Android Play Store

**Status:** PROPOSED
**Date:** 2026-08-17
**Deciders:** Architecture Team

### Context

NutriTrack needs to be published on the Google Play Store as an Android app. The app is currently a server-rendered Flask application with vanilla HTML/CSS/JS frontend (no SPA framework, no npm build step).

Approaches considered:
1. **TWA (Trusted Web Activity)** -- Chrome Custom Tab that runs a PWA in full-screen
2. **React Native** -- full native rewrite
3. **Flutter** -- full native rewrite with Dart
4. **Capacitor/Ionic** -- web wrapper with native bridge
5. **WebView wrapper** -- basic Android WebView app

### Decision

Use **TWA** to wrap the existing web application for the Play Store.

### Rationale

| Criterion | TWA | React Native | Flutter | Capacitor | WebView |
|---|---|---|---|---|---|
| Code reuse | 100% (existing Flask app) | 0% (full rewrite) | 0% (full rewrite) | ~80% (web code) | ~95% (web code) |
| Dev effort | 1-2 days | 3-6 months | 3-6 months | 2-4 weeks | 1 week |
| Performance | Chrome-native rendering | Native UI | Native UI | WebView + bridge | WebView |
| Play Store accepted | Yes (with assetlinks.json) | Yes | Yes | Yes | Yes (but flagged) |
| Offline support | Via Service Worker | Built-in | Built-in | Via Service Worker | Limited |
| Push notifications | Via Web Push API | FCM native | FCM native | Via plugin | Limited |
| App size | ~1 MB (shell only) | 20-50 MB | 10-30 MB | 5-15 MB | 2-5 MB |

**Why TWA wins for this project:**
1. **Zero frontend rewrite**: NutriTrack has 3000+ lines of vanilla JS across 8 files, 10 HTML templates, and mobile-first CSS. A React Native or Flutter rewrite would take months with a single developer.
2. **Already mobile-optimized**: CSS uses mobile-first design with CSS custom properties for theming.
3. **Feature parity**: All features (food logging, charts, chat, social) already work in mobile Chrome.
4. **Maintenance cost**: One codebase (Flask + vanilla JS) instead of two (backend + native app).
5. **Iterative path**: Can later migrate to Capacitor or native if TWA proves limiting.

**Key tradeoffs:**
- ACCEPTED: Requires Chrome/WebView on the device (99%+ Android devices have it)
- ACCEPTED: No access to native APIs (camera, accelerometer) -- not needed for a nutrition tracker
- ACCEPTED: Must serve valid assetlinks.json at /.well-known/assetlinks.json on the domain
- ACCEPTED: Requires HTTPS (Cloud Run provides this)
- REJECTED React Native/Flutter: 3-6 month rewrite for a single developer with no mobile dev experience

### Consequences

- Must add a manifest.json (PWA manifest) to the Flask app
- Must add a Service Worker for offline support and install prompt
- Must serve /.well-known/assetlinks.json with the app SHA-256 fingerprint
- Must generate a signed APK/AAB using Bubblewrap CLI or Android Studio
- Domain must have valid HTTPS (provided by Cloud Run)

---

## ADR-004: Flask Cookie-Based Sessions on Stateless Cloud Run

**Status:** PROPOSED
**Date:** 2026-08-17
**Deciders:** Architecture Team

### Context

NutriTrack uses Flask built-in cookie-based sessions (session[user_id]) for authentication. Cloud Run instances are stateless and can scale to zero, meaning no server-side session storage survives between requests to different instances.

Alternatives considered:
1. **Flask cookie sessions (current)** -- signed cookie stored client-side
2. **Redis-backed sessions (Flask-Session)** -- server-side session store
3. **JWT tokens** -- stateless auth via Authorization header
4. **Database-backed sessions** -- sessions stored in Postgres

### Decision

Keep **Flask built-in cookie-based sessions** (client-side, signed with SECRET_KEY).

### Rationale

Flask default session implementation stores the entire session payload in a signed cookie on the client. This is inherently stateless and requires no server-side session store.

**Why this works on Cloud Run:**
1. **No shared state needed**: The session cookie contains user_id (an integer). No server-side session object exists -- any Cloud Run instance can validate the cookie using the shared SECRET_KEY.
2. **PERMANENT_SESSION_LIFETIME = 30 days**: Already configured in config.py. Users stay logged in across instance restarts and scale-to-zero cycles.
3. **Scale-to-zero safe**: Unlike Redis or database sessions, there is nothing to warm up or reconnect to for session validation.
4. **Zero additional infrastructure**: No Redis instance ($0/mo saved), no session table, no session cleanup cron.

**Key tradeoffs:**
- ACCEPTED: Session payload limited to ~4KB (cookie size limit). NutriTrack stores only user_id (integer) and _permanent (bool) -- well within limits.
- ACCEPTED: Cannot server-side invalidate a specific session (must rotate SECRET_KEY to invalidate all). Acceptable for a personal nutrition tracker.
- CRITICAL: SECRET_KEY MUST be stable across deploys and identical across all instances. Currently defaults to dev-only-replace-in-production -- MUST set a proper secret via environment variable in production.
- REJECTED Redis: Adds $0-7/mo cost and operational complexity for no benefit at this scale.
- REJECTED JWT: Would require rewriting all auth checks from session[user_id] to token parsing, plus token refresh logic.

### Consequences

- SECRET_KEY must be set as a Cloud Run environment variable (not the dev default)
- SECRET_KEY must NEVER change between deploys (would log out all users)
- No code changes required -- current session implementation is already Cloud Run compatible
- session.permanent = True must continue to be set on login (already done in routes/auth.py)

---

## ADR-005: spaCy Model Bundled in Docker Image

**Status:** PROPOSED
**Date:** 2026-08-17
**Deciders:** Architecture Team

### Context

NutriTrack chat feature uses spaCy (en_core_web_sm, ~50 MB) for offline NLP food parsing. The model is downloaded at Docker build time (per CLAUDE.md). On Cloud Run, the Docker image is loaded on cold start.

Options considered:
1. **Bundle in Docker image (current)** -- downloaded at build time, always available
2. **Download at runtime** -- fetch from PyPI/GitHub on first request
3. **Move to Cloud Storage** -- load from GCS bucket on startup
4. **Remove spaCy** -- rely solely on Anthropic API + regex fallback

### Decision

Keep **spaCy bundled in the Docker image**, with a cold-start mitigation strategy.

### Rationale

**Cold start impact estimate:**

| Component | Size | Load Time Impact |
|---|---|---|
| Base Python 3.12-slim | ~150 MB | ~1-2s |
| Flask + dependencies | ~50 MB | ~0.5s |
| spaCy + en_core_web_sm | ~80 MB | ~1-2s |
| Total image | ~280 MB | ~3-5s cold start |

Cloud Run cold start breakdown:
- Image pull + decompress: 1-3s (image is cached after first pull in a region)
- Python interpreter startup: 0.5-1s
- spaCy model load (nlp = spacy.load en_core_web_sm): 1-2s
- Flask app initialization + DB connect: 0.5-1s
- **Total estimated cold start: 3-8s**

**Mitigation strategies:**
1. Set min-instances=1 in Cloud Run for the production revision ($0 when idle with CPU-only billing)
2. Use Cloud Scheduler to ping /api/chat/status every 5 minutes during waking hours (keeps instance warm)
3. Lazy-load spaCy only on first /api/chat request (not at module import time) -- local_model.py already does this

**Key tradeoffs:**
- ACCEPTED: ~280 MB image (well within Cloud Run 32 GB limit; GCR storage is $0.026/GB/mo)
- ACCEPTED: 3-8s cold start on very first request (mitigated by min-instances or warming pings)
- REJECTED runtime download: Adds 10-30s to first request, requires internet access from container, fragile
- REJECTED removing spaCy: Core offline chat feature, primary differentiator vs API-only solutions

### Consequences

- Dockerfile must include RUN python -m spacy download en_core_web_sm (already present)
- Consider multi-stage Docker build to reduce final image size
- Cloud Run service config should set --min-instances=1 for production workloads
- Alternatively, accept cold starts for dev/staging and only set min-instances in production

---

## ADR-006: Freemium Model Using Existing plan_feature_enabled Column

**Status:** PROPOSED
**Date:** 2026-08-17
**Deciders:** Architecture Team

### Context

NutriTrack needs a monetization strategy for the Play Store. The User model already has a plan_feature_enabled column (Boolean, default False) that was designed for dietitian plan features. This column can serve as a general freemium gate.

Approaches considered:
1. **Reuse plan_feature_enabled** as the freemium toggle
2. **Add a new subscription_tier column** (free/pro/enterprise)
3. **Google Play Billing integration** with server-side receipt validation
4. **Feature flags service** (LaunchDarkly, Flagsmith)

### Decision

Reuse the existing **plan_feature_enabled** column as the freemium gate for the initial launch. Plan for a subscription_tier migration if multiple tiers are needed later.

### Rationale

**Current column usage:**
- User.plan_feature_enabled (Boolean, default=False) exists in the user table
- Currently used to gate access to dietitian nutrition plans (/api/plans)
- Admin users can toggle it via /api/admin/users/<id> endpoint
- No payment integration exists yet

**Freemium split using this column:**

| Feature | Free (False) | Pro (True) |
|---|---|---|
| Food logging | Unlimited | Unlimited |
| Custom foods | Up to 20 | Unlimited |
| Meal templates | Up to 3 | Unlimited |
| Daily targets | Yes | Yes |
| History/charts | Last 7 days | Unlimited |
| Chat (local NLP) | Yes | Yes |
| Chat (Anthropic AI) | No | Yes (server key) |
| Social/friends | Yes | Yes |
| Nutrition plans | No | Yes |
| CSV export | No | Yes |
| Water + notes | Yes | Yes |

**Key tradeoffs:**
- ACCEPTED: Binary free/pro only (no middle tier). Sufficient for launch.
- ACCEPTED: No payment integration yet -- admin manually toggles the flag. Google Play Billing can be added later.
- ACCEPTED: Column name plan_feature_enabled is semantically narrow but avoids a schema migration.
- FUTURE: When Google Play Billing is integrated, add subscription_tier VARCHAR(20) and subscription_expires_at TIMESTAMP columns, deprecate the boolean.

### Consequences

- Route handlers must check plan_feature_enabled before allowing access to premium features
- Admin dashboard must expose the toggle (already partially implemented)
- No schema changes required for initial freemium launch
- Documentation should note that plan_feature_enabled serves as the pro-tier gate
- Future ADR needed for Google Play Billing integration

---

*End of ADR document. Next review scheduled after Day 2 implementation begins.*