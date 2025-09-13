Notarization & CI guide
=======================

This document walks through a practical, secure approach to codesigning and notarizing a macOS `.app` in CI.

Overview
--------
- Use a macOS runner for signing and notarization (codesign requires macOS tools).
- Import your Developer ID certificate into a temporary keychain inside the job, set `ENABLE_CODESIGN=1` for the build step, run `py2app`, then notarize with `notarytool` (preferred) or `altool` (fallback).
- Use GitHub Secrets (or your CI provider's secrets store) to hold base64-encoded certificate blobs and API keys. Never store raw certs or plaintext passwords in the repo.

Required secrets
----------------
Create the following secrets in your repository (names used by the sample workflow):

- `SIGNING_CERT_P12` — base64 of Developer ID Application `.p12`
- `SIGNING_CERT_PASSWORD` — password for the `.p12`
- `KEYCHAIN_PASSWORD` — temporary keychain password used in CI
- `APPLE_API_KEY` — base64 of App Store Connect API key `.p8` (for `notarytool`)
- `APPLE_API_KEY_ID` — App Store Connect key id (kid)
- `APPLE_API_ISSUER` — App Store Connect issuer id (iss)
- `APPLE_ID` — Apple ID (for `altool` fallback)
- `APP_SPECIFIC_PASSWORD` — app-specific password for `altool` fallback

Preparing secrets locally (quick)
---------------------------------
Encode files to base64 and copy the output into GitHub Secrets.

```bash
# base64-encode Developer ID p12
base64 -w0 DeveloperID.p12 > DeveloperID.p12.b64
# base64-encode App Store Connect key (.p8)
base64 -w0 AuthKey_ABC123XYZ.p8 > AuthKey_ABC123XYZ.p8.b64
```

Sample job steps (macOS runner)
-------------------------------
This is a condensed step sequence. See `.github/workflows/notarize-sample.yml` for a working example.

1) Create a temporary keychain and import the certificate

```bash
# create keychain and unlock
security create-keychain -p "$KEYCHAIN_PASSWORD" build-keychain-db
security default-keychain -s build-keychain-db
security unlock-keychain -p "$KEYCHAIN_PASSWORD" build-keychain-db

# write and import the p12
echo "$SIGNING_CERT_P12" | base64 --decode > /tmp/ci-signing.p12
security import /tmp/ci-signing.p12 -k build-keychain-db -P "$SIGNING_CERT_PASSWORD" -T /usr/bin/codesign -T /usr/bin/productbuild

# ensure codesign can find the identity (list to verify)
security find-identity -v -p codesigning build-keychain-db
```

2) Build with codesigning enabled

```bash
export ENABLE_CODESIGN=1
source venv/bin/activate
rm -rf build dist
python3 setup.py py2app
```

3) Zip the app and notarize

```bash
# create zip suitable for notarization
pushd dist
zip -r ../The-Example-macos-pruned.zip "The Example.app"
popd

# preferred: notarytool (uses App Store Connect API key)
notarytool submit The-Example-macos-pruned.zip --key /tmp/AuthKey.p8 --key-id "$APPLE_API_KEY_ID" --issuer "$APPLE_API_ISSUER" --wait

# fallback: altool (uses Apple ID + app-specific password)
xcrun altool --notarize-app -f The-Example-macos-pruned.zip --primary-bundle-id com.example.theexample -u "$APPLE_ID" -p "$APP_SPECIFIC_PASSWORD"

# staple the notarization result into the app
xcrun stapler staple "dist/The Example.app"
```

4) Clean up

```bash
# remove temporary files and keychain
rm -f /tmp/ci-signing.p12 /tmp/AuthKey.p8
security delete-keychain build-keychain-db
```

Security notes
--------------
- Use a temporary keychain created in the job and delete it at the end; this prevents leaving certificates behind on hosted runners.
- Prefer `notarytool` with App Store Connect API keys over `altool` (App Specific Passwords are less convenient and `altool` is deprecated).
- Do not echo secrets to logs.

Troubleshooting
---------------
- If codesign fails with "no identity found", ensure the certificate was imported and the keychain was unlocked and set as the default for the build step.
- If notarization fails with "invalid signature" then double-check the app was codesigned with the Developer ID Application identity and that the zip contains the signed app.

References
----------
- Apple's notarytool documentation: https://developer.apple.com/documentation/notaryservice
- Sample workflow in this repo: `.github/workflows/notarize-sample.yml`
