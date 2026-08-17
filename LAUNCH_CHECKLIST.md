# Launch Checklist — NutriTrack to Production

> Complete ordered checklist for deploying NutriTrack to Google Cloud Run + Neon Postgres + Play Store.
> Follow in order. Each item must be completed and verified before moving to the next phase.

---

## Phase A: Google Cloud Infrastructure Setup

### GCP Project and Billing

- [ ] Google Cloud account created at https://cloud.google.com with valid payment method
- [ ] Google Cloud CLI installed (verify: `gcloud --version`)
- [ ] Docker installed and running (verify: `docker --version`)
- [ ] Authenticated to GCP: `gcloud auth login`
- [ ] New GCP project created: `gcloud projects create nutritrack-prod`
- [ ] Project set as default: `gcloud config set project nutritrack-prod-<id>`
- [ ] Billing account linked to project
- [ ] Billing alert configured at $5 USD/month (see CLOUD_SETUP.md Step 1.3)

### APIs Enabled

- [ ] Cloud Run API enabled: `gcloud services enable run.googleapis.com`
- [ ] Container Registry API enabled: `gcloud services enable containerregistry.googleapis.com`
- [ ] Cloud Build API enabled: `gcloud services enable cloudbuild.googleapis.com`
- [ ] Secret Manager API enabled: `gcloud services enable secretmanager.googleapis.com`
- [ ] Cloud Resource Manager API enabled: `gcloud services enable cloudresourcemanager.googleapis.com`
- [ ] IAM Credentials API enabled: `gcloud services enable iamcredentials.googleapis.com`
- [ ] Verify all APIs are enabled: `gcloud services list --enabled`

### Service Account Configuration

- [ ] Service account created: `gcloud iam service-accounts create nutritrack-sa`
- [ ] Service account email recorded (format: `nutritrack-sa@PROJECT_ID.iam.gserviceaccount.com`)
- [ ] Cloud Run Invoker role granted
- [ ] Secret Manager Secret Accessor role granted
- [ ] Log Writer role granted
- [ ] Docker authentication configured: `gcloud auth configure-docker gcr.io`
- [ ] Docker push test passed: `docker push gcr.io/PROJECT_ID/hello-world:latest`

### Workload Identity Federation (GitHub Actions)

- [ ] Workload Identity Pool created: `gcloud iam workload-identity-pools create github-pool`
- [ ] Workload Identity Provider created with GitHub OIDC issuer
- [ ] GitHub repository linked to service account (see CLOUD_SETUP.md Step 2.3.3)
- [ ] WIF provider string recorded (format: `projects/PROJECT_ID/locations/global/workloadIdentityPools/github-pool/providers/github-provider`)

---

## Phase B: Database Setup (Neon Postgres)

### Neon Account and Database

- [ ] Neon account created at https://neon.tech
- [ ] Email verified
- [ ] Neon project created with name `nutritrack`
- [ ] Postgres version selected: 16+
- [ ] Database created (or use default `neondb`)
- [ ] Neon connection string obtained (pooled endpoint, port 6543)
- [ ] Connection string format verified: `postgresql://user:password@ep-xxx.us-east-2.aws.neon.tech/nutritrack?sslmode=require`

### Cloud Secret Manager

- [ ] SECRET_KEY generated: `python -c "import secrets; print(secrets.token_hex(32))"`
- [ ] SECRET_KEY stored in Secret Manager: `gcloud secrets create nutritrack-secret --data-file=-`
- [ ] DATABASE_URL stored in Secret Manager: `gcloud secrets create nutritrack-db-url --data-file=-`
- [ ] Service account given access to both secrets (secretmanager.secretAccessor role)
- [ ] Secrets listed and verified: `gcloud secrets list`

---

## Phase C: GitHub Secrets and CI/CD Configuration

### GitHub Repository Secrets

- [ ] Repository secrets page accessed: GitHub Settings → Secrets and variables → Actions
- [ ] `GCP_PROJECT_ID` secret added with actual project ID
- [ ] `GCP_WIF_PROVIDER` secret added with WIF provider string from Phase A
- [ ] `GCP_SA_EMAIL` secret added with service account email
- [ ] Secrets verified (do not print values, just confirm they exist)

### GitHub Actions Workflow

- [ ] `.github/workflows/ci.yml` exists and includes:
  - [ ] Pytest on Python 3.11 and 3.12
  - [ ] Docker build step
  - [ ] Push to Google Container Registry
- [ ] `.github/workflows/deploy-cloudrun.yml` created with:
  - [ ] Workload Identity Federation authentication
  - [ ] gcloud run deploy command
  - [ ] Smoke test step (curl /health)
- [ ] Workflows trigger on push to main/master branch

---

## Phase D: Cloud Run Deployment (First Deploy)

### Dockerfile and Application

- [ ] Dockerfile uses Python 3.12-slim base
- [ ] spaCy model download step present: `python -m spacy download en_core_web_sm`
- [ ] PORT environment variable used: `gunicorn --bind 0.0.0.0:${PORT}`
- [ ] Application tested locally with Docker:
  ```bash
  docker build -t nutritrack:latest .
  docker run -it -p 5000:5000 \
    -e DATABASE_URL="postgresql://..." \
    -e SECRET_KEY="..." \
    -e AUTH_ENABLED=true \
    nutritrack:latest
  ```

### Health Check Endpoint

- [ ] `/health` endpoint exists in Flask app returning `{"status": "ok", "db": "connected"}`
- [ ] Tested locally: `curl http://localhost:5000/health`

### Initial Deployment

- [ ] Code committed and pushed to main branch
- [ ] GitHub Actions workflow triggered automatically
- [ ] Docker build completes successfully (check Actions tab)
- [ ] Image pushed to GCR (verify: `gcloud container images list`)
- [ ] Cloud Run deployment succeeds
- [ ] Service URL obtained: `gcloud run services describe nutritrack --format='value(status.url)'`

### Post-Deploy Verification

- [ ] Health endpoint accessible and returns 200: `curl https://SERVICE_URL/health`
- [ ] Login page loads: `curl -s https://SERVICE_URL/login | head`
- [ ] No permission errors in Cloud Run logs: `gcloud run services logs read nutritrack --limit 50`
- [ ] Database connection working (verified by /health endpoint)

---

## Phase E: Domain Configuration (Optional but Recommended)

### Domain Purchase and Setup

- [ ] Domain purchased (e.g., nutritrack.app, ~$12/year)
- [ ] Domain registrar access confirmed
- [ ] Nameservers ready to be updated

### Google Cloud Domain Mapping

- [ ] Custom domain mapped to Cloud Run service
  ```bash
  gcloud run domain-mappings create \
    --service=nutritrack \
    --domain=yourdomain.com
  ```
- [ ] DNS records provided by GCP added to registrar (CNAME record)
- [ ] DNS propagated (wait 15-30 minutes)
- [ ] Domain resolves to Cloud Run: `nslookup yourdomain.com`
- [ ] HTTPS certificate auto-provisioned by Cloud Run
- [ ] Health check passes on custom domain: `curl https://yourdomain.com/health`

---

## Phase F: Data Migration (SQLite → Neon)

### Pre-Migration Setup

- [ ] Migration script `scripts/migrate_to_postgres.py` created with:
  - [ ] UPSERT logic for idempotent inserts
  - [ ] Dependency-order table migration (users → foods → entries)
  - [ ] Row count verification before/after
  - [ ] SERIAL sequence resets
- [ ] Script tested locally with a test Neon database (create via Neon branching)
- [ ] Backup of local SQLite database created

### Running the Migration

- [ ] Set environment variables:
  ```bash
  export SQLITE_URL=sqlite:///nutritrack.db
  export POSTGRES_URL=postgresql://...@neon.tech/...?sslmode=require
  ```
- [ ] Migration script executed: `python scripts/migrate_to_postgres.py`
- [ ] No errors in migration output
- [ ] Row counts match (USDA: 751, meals: 72+, users: 0+)

### Post-Migration Verification

- [ ] Cloud Run app still running and healthy
- [ ] Test login/register on live Cloud Run instance
- [ ] Test food search returns USDA foods
- [ ] Test logging a food entry
- [ ] Test meal templates load
- [ ] Verify row counts in production database match migration output
- [ ] Smoke test passes: `python scripts/smoke_test.py`

---

## Phase G: PWA and Web Manifest

### Web Manifest and Service Worker

- [ ] `static/manifest.json` created with app metadata and icons
- [ ] Service Worker created at `static/sw.js` with offline caching
- [ ] Service Worker registered in `templates/base.html`
- [ ] `/.well-known/assetlinks.json` template created in `static/`

### App Icons

- [ ] Source icon (1024x1024) created or sourced
- [ ] Python icon generation script (`scripts/generate_icons.py`) created
- [ ] Icons generated for all sizes:
  - [ ] 48x48, 72x72, 96x96, 144x144 (Android)
  - [ ] 192x192, 512x512 (Web)
  - [ ] 512x512-maskable (Android Adaptive Icon)
- [ ] All icons placed in `static/icons/`
- [ ] Icons deployed to production (git push)

---

## Phase H: Android TWA Build

### Signing Key (Keystore)

- [ ] Java JDK 11+ installed (verify: `java -version`)
- [ ] Android keystore generated:
  ```bash
  keytool -genkey -v -keystore android.keystore -alias nutritrack \
    -keyalg RSA -keysize 2048 -validity 10000
  ```
- [ ] Keystore password recorded securely (NEVER LOSE THIS)
- [ ] SHA-256 fingerprint extracted:
  ```bash
  keytool -list -v -keystore android.keystore | grep "SHA256:"
  ```
- [ ] SHA-256 fingerprint recorded (copy the full hex string)
- [ ] Keystore backed up securely in a safe location

### Bubblewrap Configuration

- [ ] Node.js 18+ installed (verify: `node --version`)
- [ ] Bubblewrap CLI installed: `npm install -g @bubblewrap/cli`
- [ ] `twa-manifest.json` created with:
  - [ ] packageId: `com.nutritrack.app`
  - [ ] host: YOUR_DOMAIN (e.g., nutritrack.yourdomain.com or nutritrack-xxx.a.run.app)
  - [ ] name: "NutriTrack — Calorie & Macro Tracker"
  - [ ] iconUrl: https://YOUR_DOMAIN/static/icons/icon-512.png
  - [ ] themeColor: #2D7A4F
  - [ ] minSdkVersion: 21
  - [ ] targetSdkVersion: 34

### Digital Asset Links

- [ ] `static/.well-known/assetlinks.json` updated with:
  - [ ] package_name: `com.nutritrack.app`
  - [ ] sha256_cert_fingerprints: [replaced with actual SHA-256 from keystore]
- [ ] assetlinks.json deployed to production (git push)
- [ ] Verify file is accessible:
  ```bash
  curl https://YOUR_DOMAIN/.well-known/assetlinks.json
  ```
- [ ] Output shows correct sha256_cert_fingerprints (no PLACEHOLDER)

### APK/AAB Build

- [ ] Bubblewrap initialized in project directory: `bubblewrap init`
- [ ] All prompts answered correctly (uses twa-manifest.json values)
- [ ] Build completed: `bubblewrap build`
- [ ] Output files verified:
  - [ ] `app-release-signed.apk` created (~5-10 MB)
  - [ ] `app-release-bundle.aab` created (~5-10 MB)
- [ ] AAB file is the correct format for Play Store (APK is for testing only)

### Local Android Testing

- [ ] Android device connected via USB or Android emulator running
- [ ] Android SDK tools installed (or via Android Studio)
- [ ] APK installed on device: `adb install app-release-signed.apk`
- [ ] App opens without browser address bar (TWA working correctly)
- [ ] Test login/register on device
- [ ] Test food logging on device
- [ ] Test offline mode (turn off Wi-Fi, open app, verify splash screen or offline page)

---

## Phase I: Play Store Submission

### Play Store Account and Developer Setup

- [ ] Google Play developer account created at https://play.google.com/console
- [ ] One-time developer fee ($25 USD) paid
- [ ] Merchant account set up for in-app purchases (if monetization enabled)
- [ ] Payment method verified

### Play Store App Listing

- [ ] New app created in Play Console
- [ ] App title (≤30 chars): "NutriTrack — Calorie Tracker"
- [ ] Short description (≤80 chars): "Track calories, macros, and meals. Offline-first. Free."
- [ ] Full description (≤4000 chars) filled from `docs/PLAY_STORE_LISTING.md`
- [ ] App icon uploaded (512x512 PNG)
- [ ] Feature graphic uploaded (1024x500 PNG)
- [ ] Screenshots uploaded (minimum 2 phone screenshots, 1080x1920)
- [ ] Category selected: Health & Fitness
- [ ] Content rating questionnaire completed
- [ ] Privacy policy URL set: https://YOUR_DOMAIN/privacy
- [ ] Terms of service URL set: https://YOUR_DOMAIN/terms (if applicable)
- [ ] Contact email provided
- [ ] Metadata keywords added (nutrition, fitness, macro tracker, calorie counter, etc.)

### App Signing and Upload

- [ ] App Bundle (AAB) prepared: `app-release-bundle.aab`
- [ ] App uploaded to Play Store via Release tab:
  - [ ] Production release created
  - [ ] AAB file uploaded
  - [ ] Release notes provided
  - [ ] Release name set (e.g., "v1.0.0")
- [ ] App submitted for review
- [ ] Submission receipt confirmed (email from Google Play)

### Review and Launch

- [ ] App under review status checked regularly (7 business days typical)
- [ ] Review feedback checked (rejection criteria: policy violations, broken links, missing privacy policy)
- [ ] If rejected, issues fixed and resubmitted
- [ ] Once approved, app released to production
- [ ] App link verified: https://play.google.com/store/apps/details?id=com.nutritrack.app
- [ ] Installation tested on a fresh Android device (via Play Store)

---

## Phase J: Post-Launch Monitoring (AdMob Monetization)

### AdMob Account Setup

- [ ] AdMob account created at https://admob.google.com
- [ ] Google AdSense account linked
- [ ] NutriTrack app registered in AdMob
- [ ] Banner ad unit created
  - [ ] Ad format: Banner/Interstitial
  - [ ] Placement: In-app (above main content)
  - [ ] Ad unit ID obtained (format: `ca-pub-XXXXXXXXXXXXXXXX/YYYYYYYYYY`)

### App Integration

- [ ] Ad unit IDs stored in Secret Manager or environment variables
- [ ] Google AdMob script added to `templates/base.html`:
  ```html
  <script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-XXXXXXXXXXXXXXXX"></script>
  ```
- [ ] Banner ad markup added to base.html
- [ ] TWA context detection added (ads shown only in TWA, not in browser)
- [ ] App redeployed with ad integration
- [ ] Test device ID registered in AdMob (for safe testing)
- [ ] Ads verified on live TWA app (not in browser)
- [ ] Click fraud monitoring enabled in AdMob

### Post-Launch Monitoring

- [ ] Cloud Run logs monitored for errors: `gcloud run services logs read nutritrack --follow`
- [ ] Error budget checked (target: <1% error rate)
- [ ] Cold start times monitored (target: <8 seconds)
- [ ] Database connection pool monitored (target: <10 active connections)
- [ ] User feedback monitored (Play Store reviews)
- [ ] AdMob earnings monitored (target: >$0/day once volume ramps)

---

## Phase K: Backup and Disaster Recovery

### Regular Backups

- [ ] Neon database automated backups enabled (Neon free tier includes backups)
- [ ] Weekly export of production database to backup storage (optional)
  ```bash
  PGPASSWORD=$DB_PASSWORD pg_dump \
    -h ep-xxx.us-east-2.aws.neon.tech \
    -U postgres -d nutritrack > backup-$(date +%Y%m%d).sql
  ```
- [ ] Backup verified: restore to a Neon branch and test
- [ ] Keystore backup verified in secure location (hardware key, encrypted cloud storage, etc.)

### Disaster Recovery Plan

- [ ] Rollback procedure documented:
  - [ ] Previous Cloud Run revision available (GCP keeps last 100 revisions)
  - [ ] Rollback command: `gcloud run deploy nutritrack --image=<previous-image>`
- [ ] Database rollback procedure documented:
  - [ ] Neon point-in-time recovery available (21-day retention free)
  - [ ] Command to restore: via Neon console under Branches → Restore
- [ ] Incident response playbook created with escalation contacts

---

## Summary: Critical Path

**Minimum steps to launch (MUST DO):**

1. Phase A: GCP project, APIs, service account, WIF
2. Phase B: Neon database, Secret Manager secrets
3. Phase C: GitHub secrets
4. Phase D: Cloud Run deployment and health check
5. Phase F: Data migration with row count verification
6. Phase G: PWA manifest and service worker
7. Phase H: Android build and local testing
8. Phase I: Play Store submission

**Optional but recommended:**

- Phase E: Custom domain for credibility and brand
- Phase J: AdMob monetization for revenue
- Phase K: Automated backups and disaster recovery

---

**Total estimated time: 3-4 days with all optional steps**

**Questions? See:**
- `docs/CLOUD_SETUP.md` — detailed GCP setup instructions
- `docs/ANDROID_BUILD.md` — Bubblewrap build walkthrough
- `docs/ADR.md` — architecture decisions and rationale
- `docs/RISK_MATRIX.md` — known risks and mitigations