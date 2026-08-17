# Google Cloud + Neon Postgres Setup Guide

> Complete manual setup instructions for deploying NutriTrack to Google Cloud Run + Neon Postgres

**Table of Contents:**
1. [Prerequisites](#prerequisites)
2. [Step 1: Google Cloud Project](#step-1-google-cloud-project)
3. [Step 2: Service Account & Workload Identity](#step-2-service-account--workload-identity-federation)
4. [Step 3: Google Container Registry](#step-3-google-container-registry)
5. [Step 4: Neon Postgres Database](#step-4-neon-postgres-setup)
6. [Step 5: Google Secret Manager](#step-5-google-secret-manager)
7. [Step 6: GitHub Secrets](#step-6-github-secrets-configuration)
8. [Step 7: First Deploy](#step-7-first-deploy)
9. [Monitoring & Troubleshooting](#monitoring--troubleshooting)

---

## Prerequisites

Before starting, ensure you have:

- **Google Account** with a valid payment method (required for Cloud Run, though billing limits prevent unexpected charges)
- **Google Cloud CLI** installed (`gcloud` command available)
  - Download: https://cloud.google.com/sdk/docs/install
  - Verify: `gcloud --version`
- **Docker Desktop** running (for local image testing)
  - Verify: `docker --version`
- **Node.js 18+** (optional, for Bubblewrap Android TWA packaging later)
- **GitHub account** with the NutriTrack repo cloned
- **Neon account** (free signup at https://neon.tech)

---

## Step 1: Google Cloud Project

### 1.1 Authenticate with Google Cloud

```bash
gcloud auth login
```

This opens a browser to sign in with your Google account. After authenticating, return to the terminal.

### 1.2 Create a Google Cloud Project

```bash
gcloud projects create nutritrack-prod \
  --name="NutriTrack Production" \
  --set-as-default
```

Note the Project ID (usually `nutritrack-prod-<random>`). You'll need this for all subsequent commands.

Verify the project was created:

```bash
gcloud config list
```

Look for `project = nutritrack-prod-...`.

### 1.3 Set Billing Alert (Optional but Recommended)

To prevent unexpected charges, set a monthly budget alert at $5 USD:

```bash
# First, get your billing account ID
BILLING_ACCOUNT=$(gcloud billing accounts list --format='value(name)' --limit=1)
echo "Billing Account: $BILLING_ACCOUNT"

# Link the project to billing
gcloud billing projects link nutritrack-prod --billing-account=$BILLING_ACCOUNT

# Create a $5 monthly budget alert
gcloud billing budgets create \
  --billing-account=$BILLING_ACCOUNT \
  --display-name="NutriTrack $5 Alert" \
  --budget-amount=5 \
  --threshold-rule=percent=50 \
  --threshold-rule=percent=100
```

### 1.4 Enable Required APIs

Enable the APIs needed for Cloud Run, Container Registry, Secret Manager, and Cloud Build:

```bash
gcloud services enable \
  run.googleapis.com \
  containerregistry.googleapis.com \
  cloudbuild.googleapis.com \
  secretmanager.googleapis.com \
  cloudresourcemanager.googleapis.com \
  iamcredentials.googleapis.com
```

Verify all APIs are enabled:

```bash
gcloud services list --enabled | grep -E "(run|container|secret|build)"
```

---

## Step 2: Service Account & Workload Identity Federation

### 2.1 Create Service Account

Create a service account for Cloud Run to use:

```bash
gcloud iam service-accounts create nutritrack-sa \
  --display-name="NutriTrack Cloud Run Service Account" \
  --project=nutritrack-prod
```

Verify:

```bash
gcloud iam service-accounts list --project=nutritrack-prod
```

### 2.2 Grant Permissions to Service Account

The service account needs access to Secret Manager (to fetch DATABASE_URL and SECRET_KEY):

```bash
# Get your project ID for use in the commands below
PROJECT_ID=$(gcloud config get-value project)
SA_EMAIL="nutritrack-sa@${PROJECT_ID}.iam.gserviceaccount.com"

# Grant Cloud Run invoker role (for manual testing / external calls)
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SA_EMAIL" \
  --role="roles/run.invoker"

# Grant Secret Manager access (to read DATABASE_URL and SECRET_KEY)
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SA_EMAIL" \
  --role="roles/secretmanager.secretAccessor"

# Grant Log Writer (for Cloud Run to emit logs)
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SA_EMAIL" \
  --role="roles/logging.logWriter"
```

### 2.3 Set Up Workload Identity Federation (for GitHub Actions)

Workload Identity Federation allows GitHub Actions to authenticate to GCP without storing long-lived service account keys.

#### 2.3.1 Create Workload Identity Pool

```bash
PROJECT_ID=$(gcloud config get-value project)
WORKLOAD_POOL_ID="github-pool"

gcloud iam workload-identity-pools create $WORKLOAD_POOL_ID \
  --project=$PROJECT_ID \
  --location=global \
  --display-name="GitHub Actions Pool"
```

#### 2.3.2 Create Workload Identity Provider

```bash
PROVIDER_ID="github-provider"

gcloud iam workload-identity-pools providers create-oidc $PROVIDER_ID \
  --project=$PROJECT_ID \
  --location=global \
  --workload-identity-pool=$WORKLOAD_POOL_ID \
  --display-name="GitHub OIDC Provider" \
  --attribute-mapping="google.subject=assertion.sub,attribute.actor=assertion.actor,attribute.environment=assertion.environment" \
  --issuer-uri="https://token.actions.githubusercontent.com"
```

#### 2.3.3 Grant GitHub Repository Access to Service Account

Link the GitHub repository to the service account so GitHub Actions can assume it:

```bash
PROJECT_ID=$(gcloud config get-value project)
WORKLOAD_POOL_ID="github-pool"
PROVIDER_ID="github-provider"
SA_EMAIL="nutritrack-sa@${PROJECT_ID}.iam.gserviceaccount.com"

# Replace with your actual GitHub username and repo name
GITHUB_REPO="sakaryag/nutrition-tracker"

gcloud iam service-accounts add-iam-policy-binding $SA_EMAIL \
  --project=$PROJECT_ID \
  --role="roles/iam.workloadIdentityUser" \
  --member="principalSet://iam.googleapis.com/projects/${PROJECT_ID}/locations/global/workloadIdentityPools/${WORKLOAD_POOL_ID}/attribute.repository/${GITHUB_REPO}"
```

#### 2.3.4 Save Workload Identity Provider and Service Account Email

You'll need these for GitHub Secrets:

```bash
PROJECT_ID=$(gcloud config get-value project)
WORKLOAD_POOL_ID="github-pool"
PROVIDER_ID="github-provider"
SA_EMAIL="nutritrack-sa@${PROJECT_ID}.iam.gserviceaccount.com"

# Format the WIF provider string
WIF_PROVIDER="projects/${PROJECT_ID}/locations/global/workloadIdentityPools/${WORKLOAD_POOL_ID}/providers/${PROVIDER_ID}"

echo "Store these as GitHub Secrets:"
echo "GCP_PROJECT_ID=$PROJECT_ID"
echo "GCP_WIF_PROVIDER=$WIF_PROVIDER"
echo "GCP_SA_EMAIL=$SA_EMAIL"
```

Save these values — you'll add them to GitHub Secrets in [Step 6](#step-6-github-secrets-configuration).

---

## Step 3: Google Container Registry

### 3.1 Configure Docker Authentication

Authenticate Docker to push images to Google Container Registry:

```bash
gcloud auth configure-docker gcr.io
```

### 3.2 Test Docker Setup

Verify that Docker can pull, tag, and push to GCR:

```bash
PROJECT_ID=$(gcloud config get-value project)

# Pull a public test image
docker pull hello-world

# Tag it for your GCR
docker tag hello-world gcr.io/$PROJECT_ID/hello-world:latest

# Push to GCR
docker push gcr.io/$PROJECT_ID/hello-world:latest

# List images in GCR
gcloud container images list --project=$PROJECT_ID
```

If the push succeeds, Docker is configured correctly. You can delete the test image:

```bash
gcloud container images delete gcr.io/$PROJECT_ID/hello-world:latest --quiet
```

---

## Step 4: Neon Postgres Setup

### 4.1 Create Neon Account

1. Go to **https://neon.tech**
2. Click **Sign Up** and create a free account
3. Verify your email

### 4.2 Create Neon Project

1. After sign-in, click **Create a new project**
2. Set:
   - **Project name:** `nutritrack`
   - **Region:** Choose the closest to `us-central1` (e.g., `us-east-2` in AWS)
   - **Postgres version:** `16` (latest)
3. Click **Create project**

### 4.3 Create Database

A default database `neondb` is created. You can use it or create a new one:

```
-- In the Neon console, under SQL Editor:
CREATE DATABASE nutritrack;
```

Or use the default `neondb` and skip this step.

### 4.4 Copy Connection String

In the Neon console:

1. Go to **Connection string** (usually on the dashboard)
2. Copy the **Pooled connection** string (port 6543 for connection pooling):
   ```
   postgresql://user:password@ep-xxxx-us-east-2.aws.neon.tech/nutritrack?sslmode=require
   ```
3. **Save this value** — you'll need it for Google Secret Manager in Step 5.

**Important notes:**
- **Free tier limits:**
  - Storage: 0.5 GB (sufficient for ~10M+ food entries; NutriTrack baseline is <10 MB)
  - Compute: 190 compute-hours/month (with auto-suspend after 5 min idle, a personal tracker uses 10-20 hr/month)
  - Branches: 10 free (great for dev/staging/prod isolation)
- **Auto-suspend:** After 5 minutes of idle time, the compute is suspended. First request after idle takes ~0.5-1s to wake up (stacks with Cloud Run cold start).
- **SSL required:** Note `?sslmode=require` in the connection string.

---

## Step 5: Google Secret Manager

Store sensitive values (DATABASE_URL and SECRET_KEY) in Google Secret Manager. Cloud Run will fetch these at startup.

### 5.1 Store DATABASE_URL Secret

```bash
PROJECT_ID=$(gcloud config get-value project)

# Replace with your actual Neon connection string from Step 4.4
DATABASE_URL="postgresql://user:password@ep-xxxx-us-east-2.aws.neon.tech/nutritrack?sslmode=require"

# Create the secret (it's stored securely; not logged)
echo -n "$DATABASE_URL" | gcloud secrets create nutritrack-db-url \
  --data-file=- \
  --project=$PROJECT_ID \
  --replication-policy="automatic"

# Verify
gcloud secrets list --project=$PROJECT_ID
```

### 5.2 Generate and Store SECRET_KEY

Generate a cryptographically random SECRET_KEY for Flask session signing:

```bash
PROJECT_ID=$(gcloud config get-value project)

# Generate a 32-byte hex string (common recommendation)
# On Linux/macOS:
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")

# On Windows PowerShell:
# $secretKey = [BitConverter]::ToString([byte[]](1..32 | ForEach-Object { Get-Random -Minimum 0 -Maximum 256 })) -replace '-'
# [Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes($secretKey))

echo "Generated SECRET_KEY (save this locally if you want to keep a backup):"
echo "$SECRET_KEY"

# Store in Secret Manager
echo -n "$SECRET_KEY" | gcloud secrets create nutritrack-secret \
  --data-file=- \
  --project=$PROJECT_ID \
  --replication-policy="automatic"

# Verify
gcloud secrets list --project=$PROJECT_ID
```

### 5.3 Grant Service Account Access to Secrets

The Cloud Run service account needs permission to read these secrets:

```bash
PROJECT_ID=$(gcloud config get-value project)
SA_EMAIL="nutritrack-sa@${PROJECT_ID}.iam.gserviceaccount.com"

# Grant access to DATABASE_URL secret
gcloud secrets add-iam-policy-binding nutritrack-db-url \
  --project=$PROJECT_ID \
  --member="serviceAccount:$SA_EMAIL" \
  --role="roles/secretmanager.secretAccessor"

# Grant access to SECRET_KEY secret
gcloud secrets add-iam-policy-binding nutritrack-secret \
  --project=$PROJECT_ID \
  --member="serviceAccount:$SA_EMAIL" \
  --role="roles/secretmanager.secretAccessor"
```

---

## Step 6: GitHub Secrets Configuration

Add the following secrets to your GitHub repository. GitHub Actions will use these to authenticate to GCP and deploy.

### 6.1 Add Secrets to GitHub

1. Go to your GitHub repository: **https://github.com/sakaryag/nutrition-tracker**
2. Click **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret** and add:

| Secret Name | Value |
|---|---|
| `GCP_PROJECT_ID` | The Project ID from Step 2.3.4 |
| `GCP_WIF_PROVIDER` | The WIF provider string from Step 2.3.4 |
| `GCP_SA_EMAIL` | The service account email from Step 2.3.4 |

Example values (replace with your actual values):
```
GCP_PROJECT_ID=nutritrack-prod-abc123
GCP_WIF_PROVIDER=projects/123456/locations/global/workloadIdentityPools/github-pool/providers/github-provider
GCP_SA_EMAIL=nutritrack-sa@nutritrack-prod-abc123.iam.gserviceaccount.com
```

### 6.2 Verify Secrets in CI Workflow

Your `.github/workflows/ci.yml` should reference these secrets. The workflow should:
1. Use Workload Identity Federation to authenticate
2. Build the Docker image
3. Push to GCR
4. Deploy to Cloud Run

Example workflow snippet (verify it exists in your repo):

```yaml
- name: Authenticate to Google Cloud
  uses: google-github-actions/auth@v2
  with:
    workload_identity_provider: ${{ secrets.GCP_WIF_PROVIDER }}
    service_account_email: ${{ secrets.GCP_SA_EMAIL }}

- name: Deploy to Cloud Run
  run: |
    gcloud run deploy nutritrack \
      --image gcr.io/${{ secrets.GCP_PROJECT_ID }}/nutritrack:latest \
      --platform managed \
      --region us-central1 \
      --service-account ${{ secrets.GCP_SA_EMAIL }} \
      --set-env-vars DATABASE_URL=... SECRET_KEY=...
```

---

## Step 7: First Deploy

### 7.1 Verify Dockerfile and Cloud Run Configuration

Before pushing, ensure your `Dockerfile` is ready:

```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && \
    python -m spacy download en_core_web_sm

COPY . .

# Cloud Run sets PORT env var; default to 5000 if not set
ENV PORT=5000
EXPOSE $PORT

CMD ["gunicorn", "--workers", "2", "--bind", "0.0.0.0:${PORT}", "--timeout", "120", "app:create_app()"]
```

### 7.2 Push to GitHub

Commit and push your code. The GitHub Actions workflow will trigger automatically:

```bash
git add .
git commit -m "chore: add cloud setup documentation"
git push origin main
```

Monitor the workflow in **Actions** tab on GitHub.

### 7.3 First Manual Deploy (if CI workflow not ready)

If your CI workflow isn't complete, deploy manually:

```bash
PROJECT_ID=$(gcloud config get-value project)

# Build and push the image
gcloud builds submit --tag gcr.io/$PROJECT_ID/nutritrack:latest

# Deploy to Cloud Run
gcloud run deploy nutritrack \
  --image gcr.io/$PROJECT_ID/nutritrack:latest \
  --platform managed \
  --region us-central1 \
  --service-account nutritrack-sa@${PROJECT_ID}.iam.gserviceaccount.com \
  --memory 512Mi \
  --cpu 1 \
  --min-instances 0 \
  --max-instances 100 \
  --allow-unauthenticated \
  --set-env-vars AUTH_ENABLED=true,ANTHROPIC_API_KEY="" \
  --set-secrets DATABASE_URL=nutritrack-db-url:latest,SECRET_KEY=nutritrack-secret:latest
```

This creates a Cloud Run service with:
- **Memory:** 512 MB (standard)
- **CPU:** 1 vCPU
- **Min instances:** 0 (scale to zero for cost savings; first request takes 2-8s cold start)
- **Max instances:** 100 (auto-scaling cap)
- **Secrets:** DATABASE_URL and SECRET_KEY from Secret Manager
- **Public endpoint:** HTTPS with managed TLS certificate

### 7.4 Get the Service URL

After deployment, retrieve the service URL:

```bash
gcloud run services describe nutritrack \
  --platform managed \
  --region us-central1 \
  --format='value(status.url)'
```

Example output:
```
https://nutritrack-xxx-us-central1.a.run.app
```

### 7.5 Test the Deployment

```bash
SERVICE_URL=$(gcloud run services describe nutritrack \
  --platform managed \
  --region us-central1 \
  --format='value(status.url)')

# Test health endpoint
curl -s "$SERVICE_URL/health" | jq .

# Test login page (should return HTML)
curl -s "$SERVICE_URL/login" | head -n 20
```

---

## Monitoring & Troubleshooting

### View Cloud Run Logs

```bash
gcloud run services logs read nutritrack \
  --platform managed \
  --region us-central1 \
  --limit 50 \
  --follow
```

### View Service Details

```bash
gcloud run services describe nutritrack \
  --platform managed \
  --region us-central1
```

### Check Secret Values (for debugging)

Never log secrets, but you can verify they exist:

```bash
gcloud secrets versions list nutritrack-db-url --project=$(gcloud config get-value project)
gcloud secrets versions list nutritrack-secret --project=$(gcloud config get-value project)
```

### Common Issues

**"Permission denied: Could not access secret..."**
- Ensure the Cloud Run service account has `roles/secretmanager.secretAccessor` role on both secrets (see Step 5.3).

**"Connection refused (Postgres)"**
- Check DATABASE_URL is correctly formatted: `postgresql://user:pass@host/db?sslmode=require`
- Ensure Neon project is awake (first request after idle takes ~1s)
- Check firewall: Neon allows connections from anywhere by default

**"Cold start is slow"**
- Normal: Cloud Run + Neon auto-suspend = 2-8s + 0.5-1s = 3-9s on first request after idle
- Mitigate with `--min-instances=1` (costs ~$7/mo; always-on instance)
- Or use Cloud Scheduler to ping `/health` every 5 minutes during business hours

### Cost Estimate (Monthly)

| Component | Free Tier | Overage Cost |
|---|---|---|
| Cloud Run | 2M requests/mo, 360K vCPU-sec | $0.00015 per request, $0.00002400 per vCPU-sec |
| Neon (free) | 0.5 GB storage, 190 hr/mo compute, 10 branches | $0 (auto-scale, capped) |
| Secret Manager | First 6 secrets free | $0.06 per secret/month |
| GCR Storage | $0.026 per GB/month (images cached) | ~$0.01/month for small image |
| **Total Estimate** | | **$0-5/month for a personal tracker** |

---

## Next Steps

1. **Local Testing:** Before production, test locally:
   ```bash
   docker build -t nutritrack:latest .
   docker run -it -p 5000:5000 \
     -e DATABASE_URL="postgresql://..." \
     -e SECRET_KEY="your-secret" \
     -e AUTH_ENABLED=true \
     nutritrack:latest
   ```

2. **Domain Configuration:** Add a custom domain (optional):
   ```bash
   gcloud run domain-mappings create \
     --service=nutritrack \
     --domain=nutritrack.example.com
   ```

3. **Android TWA Deployment:** After Cloud Run is live, use Bubblewrap to build the TWA for Play Store.

4. **Monitoring:** Set up Cloud Monitoring alerts for high error rates or high latency.

---

**Setup completed!** Your NutriTrack backend is now live on Google Cloud Run with a Neon Postgres database. The app is accessible at the Cloud Run service URL.