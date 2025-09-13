The Example — build & test guide
================================

This repo contains a tiny PySide6 app (`main.py`) and `setup.py` for
creating a macOS `.app` using `py2app`.

Two build modes
----------------
- Testing build (default): creates a full bundle suitable for running
  locally and for CI validation. This build does NOT remove optional
  Qt artifacts so runtime behavior is fully preserved.

- Release build (pruned): creates a smaller bundle by removing
  optional developer/QML/WebEngine artifacts. Pruning is opt-in and
  controlled via the `PRUNE_BUNDLE` environment variable. Use
  `PRUNE_LEVEL` to control aggressiveness (`moderate` (default) or
  `aggressive`).

How to build (recommended: inside a venv)
-----------------------------------------
1) Create and activate a venv and install dependencies:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

2) Testing build (no pruning):

```bash
rm -rf build dist
python3 setup.py py2app
```

3) Release build (pruned):

```bash
# moderate pruning (recommended)
rm -rf build dist
PRUNE_BUNDLE=1 PRUNE_LEVEL=moderate python3 setup.py py2app

# aggressive pruning (may remove additional QML/QtQuick pieces)
rm -rf build dist
PRUNE_BUNDLE=1 PRUNE_LEVEL=aggressive python3 setup.py py2app
```

Note: pruning removes optional frameworks/plugins (QtWebEngine,
Quick3D, QML examples, translation tools, ffmpeg libs, etc.). Run the
smoke test described below after building to ensure your app still
works with the pruning you selected.

Smoke test (validate runtime)
-----------------------------
The app contains a built-in smoke-mode that performs basic UI checks
and writes a newline-delimited JSON diagnostic line to a file.

- Run the smoke mode against the built bundle:

```bash
# produce JSON at dist/smoke.json
THE_EXAMPLE_SMOKE=1 THE_EXAMPLE_SMOKE_OUT=dist/smoke.json ./dist/The\ Example.app/Contents/MacOS/The\ Example

# check result
cat dist/smoke.json
```

- On success the process exits with code 0 and `dist/smoke.json` will
  contain a JSON object with `components` test results. On failure the
  process exits non-zero and the JSON will contain `result: "fail"`.

Developer notes
---------------
- `setup.py` now only prunes if `PRUNE_BUNDLE` is truthy. This keeps
  testing builds portable and reproducible while still letting you
  create smaller release bundles when you explicitly ask for them.

If you'd like, I can:
- Run the smoke test now and report the result;
- Rebuild the app in either testing or release mode and re-run smoke
  tests automatically in CI.
The Example — macOS PySide6 demo

Overview
--------
"The Example" is a small PySide6 GUI demo intended to be packaged as a macOS .app using py2app. It demonstrates a main window, a Preferences dialog, a few basic widgets (text input, slider, checkboxes) and includes an automated smoke test useful for CI.

Repository layout
-----------------
- `main.py` — application entrypoint and UI.
- `setup.py` — py2app packaging helper and build-time logic (libffi selection, vendored metadata handling).
- `requirements.txt` — runtime / packaging dependencies.
- `.gitignore` — recommended ignores (venv, build/artifacts).

Quick start (local, development)
--------------------------------
1. Create a clean virtualenv and activate it (recommended; do not use system Python):

```bash
python3 -m venv venv
source venv/bin/activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
# If you run into missing modules reported by py2app, `pip install jaraco.text` in the venv.
```

3. Run the app directly (dev):

```bash
python3 main.py
```

Build a macOS .app with py2app
-----------------------------
These are the supported, tested steps used when developing this project. They assume you're on macOS and using a fresh virtualenv.

1. Activate your venv and clean previous builds:

```bash
source venv/bin/activate
rm -rf build dist
```

2. Build with py2app:

```bash
python3 setup.py py2app
```

3. The resulting bundle will be in `dist/` (e.g. `dist/The Example.app`).

Important packaging notes (read before building)
------------------------------------------------
- Use an isolated venv: building with system Python often causes permission and dependency mismatches. The project was developed and tested using Python 3.13 in a venv.

- libffi / ctypes: `_ctypes.so` requires a libffi that exports `ffi_type_longdouble`. The included `setup.py` contains detection logic and will attempt to bundle a suitable `libffi` from your environment (for example the venv or a conda/homebrew location). If py2app fails at runtime with an `_ctypes` dlopen error, rebuild after ensuring a libffi with `ffi_type_longdouble` is available in your environment.

- setuptools vendored metadata collisions: some versions of `setuptools` include a `setuptools._vendor` namespace that can duplicate `.dist-info` metadata, causing py2app to fail during collection. `setup.py` implements a temporary hide/restore workaround for conflicting vendor `.dist-info` files and sets useful `includes`/`excludes` for the py2app collector. If you see `.dist-info` collision errors, use a clean venv and re-run the build.

- Application name and Preferences placement: `setup.py` sets `CFBundleName`/`CFBundleDisplayName` to "The Example" so macOS places the app menu correctly. `main.py` registers the Preferences action with `QAction.PreferencesRole` and adds it to the Edit menu so Qt/macOS relocates it under the app menu.

Smoke test (CI-friendly)
-------------------------
The app contains a built-in smoke test useful for CI and local verification. It exercises basic components:
- text input selection
- slider update
- preferences checkboxes
- menu / PreferencesRole presence

Controls:
- Enable smoke test: set `THE_EXAMPLE_SMOKE=1` or pass `--smoke` on the command line.
- Configure output path: set `THE_EXAMPLE_SMOKE_OUT` to a writable path. Default: `~/Desktop/the-example-smoke.txt`.
- Output format: newline-delimited JSON ({timestamp, result, pid, python_version, app, components, ...}). Example run (local):

```bash
THE_EXAMPLE_SMOKE=1 THE_EXAMPLE_SMOKE_OUT=/tmp/the-example-smoke-ci.json python3 main.py
# The process will exit with 0 on success, 1 on failure for CI detection.
```

Packaging notes for CI
----------------------
- Run builds in a hermetic builder (fresh venv). Install `py2app` and `PySide6` inside the venv.
- Make sure the builder provides a libffi that exports `ffi_type_longdouble` or point `setup.py` to a candidate path if necessary.
- After building, you can run the smoke test against the built binary by launching the executable inside the .app with the same env vars. Example:

```bash
THE_EXAMPLE_SMOKE=1 THE_EXAMPLE_SMOKE_OUT=/tmp/the-example-smoke-ci.json /path/to/dist/The\ Example.app/Contents/MacOS/The\ Example
```

CI notes
-------

- Use a fresh virtualenv on the CI runner and `pip install -r requirements.txt`.
- If you want the smaller release artifact in CI, set `PRUNE_BUNDLE=1` and `PRUNE_LEVEL` when running `setup.py`.
- Example CI snippet (macOS runner):

  rm -rf build dist
  python3 -m venv venv && source venv/bin/activate
  pip install -r requirements.txt
  PRUNE_BUNDLE=1 PRUNE_LEVEL=moderate python3 setup.py py2app
  THE_EXAMPLE_SMOKE=1 THE_EXAMPLE_SMOKE_OUT=$GITHUB_WORKSPACE/dist/smoke.json $GITHUB_WORKSPACE/dist/The\ Example.app/Contents/MacOS/The\ Example

Releases via tags
-----------------
This repository only creates a GitHub Release when the workflow runs for a tag push that starts with `v` (for example `v1.2.0`). The CI will still run on branch pushes and PRs for validation, but only version tags produce an official Release with attached pruned artifacts.

How to create a release (locally):

1. Create an annotated tag (must start with `v`) and push it:

```bash
# create tag for version v1.2.0
git tag -a v1.2.0 -m "release v1.2.0"
git push origin v1.2.0
```

2. The GitHub Actions workflow will run for this tag and, on success, create a Release named `Pruned macOS build v1.2.0` and attach:

- `The-Example-macos-pruned.zip`
- `The-Example-macos-pruned.zip.sha256`

Verifying the checksum locally
-----------------------------
After downloading the zip and the `.sha256` file you can verify the checksum on macOS/Linux with:

```bash
# verify the file; the tool will print OK if the checksum matches
shasum -a 256 -c The-Example-macos-pruned.zip.sha256
```

If you prefer manual checking, run:

```bash
shasum -a 256 The-Example-macos-pruned.zip
# compare output to contents of The-Example-macos-pruned.zip.sha256
cat The-Example-macos-pruned.zip.sha256
```

Code signing & notarization (distribution)
------------------------------------------
- This repo does NOT perform code signing or notarization. For distribution outside your machine you should:
  - codesign --timestamp --options runtime --sign "Developer ID Application: <Your Identity>" "dist/The Example.app"
  - Use `altool` or `notarytool` to submit and staple notarization as required by Apple.

Troubleshooting tips
--------------------
- If py2app fails to collect modules, install the missing package into the venv and re-run the build.
- If you see `_ctypes` or libffi-related errors when launching the .app, the bundled libffi is incompatible; ensure `setup.py` can find a suitable libffi or adjust your environment.
- For AppleScript-based integration tests that read the macOS menu bar, macOS will require Accessibility permissions for the runner (System Settings → Privacy & Security → Accessibility). Tests that use System Events will fail until permission is granted.

Contributing
------------
- Please open issues for build/runtime problems and include the smoke test output where possible (`THE_EXAMPLE_SMOKE_OUT` file) and the output of `otool -L` on the built `libffi*.dylib` if you hit native linking issues.

License & contact
------------------
This is a small demo for packaging and UI patterns; add a license file if you intend to redistribute. If you want me to initialize a git repo and make an initial commit, say the word and I'll run it for you.
