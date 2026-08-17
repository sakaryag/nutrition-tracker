# NutriTrack Android Build Guide (TWA)

This guide walks through building and publishing the NutriTrack Android app
using Trusted Web Activity (TWA) via Bubblewrap CLI.

## Prerequisites

- Node.js 18+ (`node --version`)
- Java JDK 11+ (`java -version`)
- Android SDK (via Android Studio or `sdkmanager`)
- Your Cloud Run domain (must be live before building)

## Step 1: Install Bubblewrap CLI

```bash
npm install -g @bubblewrap/cli
bubblewrap --version
```

## Step 2: Get your signing key SHA-256

```bash
keytool -genkey -v -keystore android.keystore -alias nutritrack \
  -keyalg RSA -keysize 2048 -validity 10000

keytool -list -v -keystore android.keystore | grep "SHA256:"
# Copy the SHA256 value — you need it for assetlinks.json
```

## Step 3: Update assetlinks.json

1. Replace `PLACEHOLDER_REPLACE_WITH_YOUR_SHA256_FINGERPRINT` in
   `static/.well-known/assetlinks.json` with the SHA256 value from Step 2.
2. Replace `REPLACE_WITH_YOUR_DOMAIN` in `twa-manifest.json` with your actual
   Cloud Run domain (e.g. `nutritrack-abc123-uc.a.run.app`).
3. Deploy the updated app (git push triggers the CD pipeline).
4. Verify the file is served correctly:

```bash
curl https://YOUR_DOMAIN/.well-known/assetlinks.json
```

## Step 4: Build the APK

```bash
bubblewrap build
# Answer prompts using values from twa-manifest.json
# Output: app-release-signed.apk and app-release-bundle.aab
```

## Step 5: Test on Android device

```bash
adb install app-release-signed.apk
# Open the app — should open your site without browser UI (address bar hidden)
```

## Step 6: Upload to Play Store

Use `app-release-bundle.aab` (not `.apk`) for Play Store submission.
`.aab` is required for new apps since August 2021.

---

## Checklist before submitting to Play Store

- [ ] `assetlinks.json` served at `https://YOUR_DOMAIN/.well-known/assetlinks.json`
- [ ] SHA256 fingerprint in `assetlinks.json` matches `android.keystore`
- [ ] App opens without browser address bar on a real Android device
- [ ] All icon sizes present in `static/icons/` (48, 72, 96, 144, 192, 512, 512-maskable)
- [ ] `manifest.json` served at `https://YOUR_DOMAIN/manifest.json`
- [ ] Privacy policy page live at `https://YOUR_DOMAIN/privacy`
- [ ] Terms of service page live at `https://YOUR_DOMAIN/terms`
