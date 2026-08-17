# What to Do Manually — NutriTrack Launch

> Summary of human-only tasks. These cannot be automated by agents or CI/CD.
> Reference CLOUD_SETUP.md and ANDROID_BUILD.md for detailed steps.

---

## Before You Start

- [ ] **Time required:** 3–4 days including agent work
- [ ] **Skill level:** Intermediate (Google Cloud, Android basics, shell commands)
- [ ] **Cost:** $25 (Play Store developer account) + domain (~$12/year) = ~$37 one-time
- [ ] **Free services:** Google Cloud Run (2M req/mo), Neon Postgres (0.5 GB), Google Secret Manager, GitHub Actions
- [ ] **Read first:** CLOUD_SETUP.md and ANDROID_BUILD.md

---

## 1. Google Cloud Project Setup (30 min)

Steps that cannot be scripted (require manual browser actions):

1. Go to https://cloud.google.com
2. Sign in or create account with a valid payment method
3. Create new project: Cloud Console → "Create Project" → name: `nutritrack-prod`
4. Copy the Project ID (format: `nutritrack-prod-abc123`)
5. Enable billing: link a payment method (won't charge for free-tier usage)
6. Set monthly budget alert at $5 USD (optional but recommended)

**Time:** ~10 min

---

## 2. Neon Postgres Database (15 min)

These steps require manual browser signup and database creation:

1. Go to https://neon.tech → Sign Up
2. Verify email (check inbox, click verification link)
3. Create new project: name `nutritrack`, region closest to US, Postgres 16+
4. Go to "Connection String" in Neon console
5. Copy the **pooled connection** string (port 6543, ends with `?sslmode=require`)
   - Format: `postgresql://user:password@ep-xxxx-us-east-2.aws.neon.tech/neondb?sslmode=require`
6. **Save this string** — you'll paste it into Cloud Secret Manager

**Time:** ~15 min

---

## 3. GitHub Secrets Configuration (10 min)

Browser-only: add three secrets to your GitHub repository for CI/CD:

1. Go to your GitHub repo: https://github.com/sakaryag/nutrition-tracker
2. Settings → Secrets and variables → Actions
3. Click "New repository secret" and add these three (exact names required):

   | Secret | Value |
   |--------|-------|
   | `GCP_PROJECT_ID` | The project ID from step 1 (e.g., `nutritrack-prod-abc123`) |
   | `GCP_WIF_PROVIDER` | Will be printed by the agent after Workload Identity setup |
   | `GCP_SA_EMAIL` | Service account email (printed by agent, format: `nutritrack-sa@...iam.gserviceaccount.com`) |

   **Example values (replace with your actual values):**
   ```
   GCP_PROJECT_ID=nutritrack-prod-abc123
   GCP_WIF_PROVIDER=projects/123456789/locations/global/workloadIdentityPools/github-pool/providers/github-provider
   GCP_SA_EMAIL=nutritrack-sa@nutritrack-prod-abc123.iam.gserviceaccount.com
   ```

4. Save each secret. Do NOT share these values publicly.

**Time:** ~10 min

---

## 4. Generate Android Keystore (5 min)

One-time signing key for Play Store (NEVER LOSE THIS):

```bash
cd C:\Users\z004mvzt\nutrition-tracker

keytool -genkey -v -keystore android.keystore -alias nutritrack ^
  -keyalg RSA -keysize 2048 -validity 10000
```

You'll be prompted for:
- Keystore password (remember this)
- Key password (can be same as keystore password)
- Name, email, organization, city, state, country

**After it completes:**

```bash
keytool -list -v -keystore android.keystore | findstr "SHA256:"
```

Copy the SHA256 fingerprint (long hex string). You'll need this for `assetlinks.json`.

**Backup the keystore file immediately:** `android.keystore` is irreplaceable. Losing it means you cannot update your Play Store app forever. Store a copy in:
- Hardware security key (recommended)
- Encrypted cloud storage (Google Drive, OneDrive)
- Printed QR code in a safe

**Time:** ~5 min

---

## 5. Domain Purchase (Optional, 10 min)

Recommended for Play Store credibility but not required (can use Cloud Run domain):

1. Go to a registrar (Google Domains, Namecheap, GoDaddy)
2. Search and buy a domain (e.g., `nutritrack.app`, ~$12/year)
3. Save the domain registrar login details
4. **Do NOT change nameservers yet** — wait for Cloud Run mapping (see LAUNCH_CHECKLIST.md Phase E)

**Time:** ~10 min

---

## 6. Deploy to Production (Manual trigger + monitoring)

After the agents prepare all code and configuration:

```bash
cd C:\Users\z004mvzt\nutrition-tracker

# Commit all agent work
git add .
git commit -m "chore: add cloud deployment configuration"
git push origin master
```

Watch GitHub Actions (https://github.com/sakaryag/nutrition-tracker/actions):
- CI workflow runs tests (~2 min)
- Build workflow builds Docker image (~3 min)
- Deploy workflow deploys to Cloud Run (~2 min)

**If deployment fails:**
- Click the failed job → View logs
- Common errors: SECRET_KEY not set, DATABASE_URL invalid, service account permissions missing
- Check `gcloud run services logs read nutritrack --limit 50` for app errors

**Time:** ~10 min

---

## 7. Verify Database Migration (10 min)

After deployment succeeds:

```powershell
# Set your actual Neon connection string
$env:POSTGRES_URL = "postgresql://user:password@ep-xxx.us-east-2.aws.neon.tech/nutritrack?sslmode=require"

# Run migration
python scripts/migrate_to_postgres.py
```

Output should show:
```
Migrating users... (0 → 0)
Migrating saved_food... (823 → 823)  [751 USDA + 72 meals]
Migrating food_entry... (0 → 0)
...
Migration complete. All tables verified.
```

If it fails:
- Check DATABASE_URL is correct (copy from Neon dashboard)
- Ensure Neon database is awake (first request can take 30s after suspend)
- Run again if transient error

**Time:** ~10 min

---

## 8. Test the Live App (10 min)

```bash
# Get the Cloud Run service URL
gcloud run services describe nutritrack --platform managed --region us-central1 --format='value(status.url)'

# Test health endpoint
curl -s "https://XXXX-uc.a.run.app/health"

# Should return: {"status":"ok","db":"connected"}
```

Open the URL in your browser:
- [ ] Login page loads
- [ ] Register a test account
- [ ] Log a food entry
- [ ] Verify chart loads

**Time:** ~10 min

---

## 9. Android Keystore Setup and Build (30 min)

Bubblewrap build for Android:

```bash
cd C:\Users\z004mvzt\nutrition-tracker

# Install Bubblewrap (Node.js required)
npm install -g @bubblewrap/cli

# Replace placeholders in twa-manifest.json
# - Replace REPLACE_WITH_YOUR_DOMAIN with your Cloud Run domain
#   (e.g., nutritrack-abc123-us-central1.a.run.app)
# - Keep all other values as-is
notepad twa-manifest.json

# Replace SHA256 fingerprint in static/.well-known/assetlinks.json
# - Replace PLACEHOLDER_REPLACE_WITH_YOUR_SHA256_FINGERPRINT with the value from step 4
notepad static/.well-known/assetlinks.json

# Deploy updated files
git add static/ twa-manifest.json
git commit -m "chore: update assetlinks and TWA manifest for Android build"
git push origin master

# Wait 5 min for Cloud Run to redeploy, then verify assetlinks is served
curl -s "https://YOURDOMAIN/.well-known/assetlinks.json"

# Now build the APK/AAB
bubblewrap build

# Answer prompts (values come from twa-manifest.json)
# Output files:
#   - app-release-signed.apk (for local testing)
#   - app-release-bundle.aab (for Play Store submission)
```

**Test on Android device:**

```bash
adb install app-release-signed.apk
```

Open the app on your Android phone:
- [ ] App opens without browser address bar (TWA working)
- [ ] Can log in
- [ ] Can log a food entry
- [ ] Status bar shows "NutriTrack" (not "Chrome")

**Time:** ~30 min (including wait for deployment)

---

## 10. Google Play Store Submission (45 min)

Browser-only steps to publish on Play Store:

1. Go to https://play.google.com/console
2. Sign in with your Google account
3. Pay $25 USD developer fee (one-time)
4. Create new app:
   - Name: "NutriTrack — Calorie Tracker"
   - Category: Health & Fitness
   - Content rating: Take questionnaire (5 min)
5. Fill app listing:
   - Title: "NutriTrack — Calorie Tracker" (30 chars)
   - Short description: "Track calories, macros, and meals. Offline-first." (80 chars)
   - Full description: Copy from docs/PLAY_STORE_LISTING.md (4000 chars max)
   - Screenshots: Upload 2 phone screenshots (1080x1920 PNG each)
   - Feature graphic: 1024x500 PNG banner
   - App icon: 512x512 PNG (copy from static/icons/icon-512.png)
   - Privacy policy: https://YOUR_DOMAIN/privacy
   - Contact email: your-email@example.com
   - Keywords: nutrition, fitness, macro tracker, calorie counter
6. Upload app bundle:
   - Go to Release → Production
   - Click "Upload new bundle"
   - Select `app-release-bundle.aab` (NOT .apk)
   - Wait for upload (30 sec)
   - Review release notes and submit
7. Submit for review
8. Google will review (7 business days typical)
9. Once approved, app goes live on Play Store

**Check status:**
- Play Console → All apps → NutriTrack → View on Google Play
- Copy the link: `https://play.google.com/store/apps/details?id=com.nutritrack.app`

**Time:** ~45 min

---

## 11. AdMob Setup (Optional, 20 min)

To show ads and earn revenue:

1. Go to https://admob.google.com
2. Sign in with your Google account
3. Click "Sign up or sign in with AdSense" (may require AdSense approval)
4. Register the app:
   - Click "Apps" → "Add app"
   - Platform: Android
   - App name: NutriTrack
   - Category: Lifestyle
5. Create ad unit:
   - Ad format: Banner
   - Ad unit name: "NutriTrack Banner"
   - Copy the ad unit ID (format: `ca-pub-XXXXXXXXXXXXXXXX/YYYYYYYYYY`)
6. (Agent will add this to the app code)

**Time:** ~20 min

---

## 12. Post-Launch Monitoring (Ongoing)

After app goes live:

**Weekly:**
- Check Play Store reviews and ratings (reply to feedback)
- Monitor Cloud Run logs for errors: `gcloud run services logs read nutritrack --limit 100`
- Check Neon database storage usage (should stay <100 MB)

**Monthly:**
- Review AdMob earnings (if enabled)
- Check billing: should be $0–5 for a personal tracker

**When issues arise:**

```bash
# View recent errors
gcloud run services logs read nutritrack --limit 50

# Rollback to previous version if deployment broke
gcloud run deploy nutritrack --image=gcr.io/PROJECT_ID/nutritrack:previous-tag

# Check database connections (max ~10 for free tier)
PGPASSWORD=$DB_PASSWORD psql -h ep-xxx.us-east-2.aws.neon.tech \
  -U postgres -d nutritrack -c "SELECT datname, count(*) FROM pg_stat_activity GROUP BY datname;"
```

**Time:** ~10 min/week

---

## Estimated Total Time

| Step | Time |
|------|------|
| 1. Google Cloud project | 30 min |
| 2. Neon database | 15 min |
| 3. GitHub secrets | 10 min |
| 4. Android keystore | 5 min |
| 5. Domain (optional) | 10 min |
| 6. Deploy to production | 10 min |
| 7. Database migration | 10 min |
| 8. Test live app | 10 min |
| 9. Android build & test | 30 min |
| 10. Play Store submission | 45 min |
| 11. AdMob setup (optional) | 20 min |
| **TOTAL** | **~3.5 hours** |

Plus 7 business days for Google Play review.

---

## Checklist Before Each Step

Before starting each manual step, ensure:

- [ ] Agent tasks completed for that phase (check `LAUNCH_CHECKLIST.md`)
- [ ] Required files created and committed
- [ ] All prerequisite steps finished
- [ ] You have the correct credentials/URLs/passwords

---

## Common Issues

**"Permission denied: user@project.iam.gserviceaccount.com"**
→ Service account missing roles. Run the commands in CLOUD_SETUP.md Step 2.2 again.

**"Database connection refused"**
→ Neon database asleep. Wait 30s and retry (auto-wakes on first request).

**"Secret not found in Secret Manager"**
→ Check it was created: `gcloud secrets list`. Re-create if missing.

**"APK won't install on Android device"**
→ Uninstall old version: `adb uninstall com.nutritrack.app`. Then `adb install` again.

**"Play Store review rejected"**
→ Common reasons: missing privacy policy, broken app link, policy violations. Check email from Google Play for exact reason. Fix and resubmit.

---

## Next Steps After Launch

1. Monitor reviews and user feedback
2. Plan v1.1 features (user feedback, analytics)
3. Set up proper payment integration if AdMob revenue is significant
4. Create iOS version (future, not in scope for v1)

---

**Questions? See:**
- CLOUD_SETUP.md — GCP setup walkthrough
- ANDROID_BUILD.md — Bubblewrap build details
- LAUNCH_CHECKLIST.md — full checklist with all items
- RISK_MATRIX.md — known risks and mitigations