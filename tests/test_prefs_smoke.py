import os
import json
import plistlib
import subprocess
import sys
import tempfile
import time


def test_prefs_smoke(tmp_path):
    """Run the application in smoke mode and verify preferences are persisted.

    The test sets THE_EXAMPLE_PREFS_PATH to a temporary plist path and
    runs the app with THE_EXAMPLE_SMOKE to exercise the preferences
    dialog flow. The app's smoke mode will write a JSON diagnostics file
    containing a snapshot of the preferences; additionally we assert the
    plist exists and contains the expected keys.
    """
    repo_root = os.path.dirname(os.path.dirname(__file__)) if __file__ else os.getcwd()
    # Ensure we use the workspace python executable
    py = sys.executable

    prefs_path = tmp_path / "the-example-test.plist"
    out_path = tmp_path / "smoke_out.json"

    env = os.environ.copy()
    env['THE_EXAMPLE_SMOKE'] = '1'
    env['THE_EXAMPLE_SMOKE_OUT'] = str(out_path)
    # Override prefs path so we don't touch the user's Library
    env['THE_EXAMPLE_PREFS_PATH'] = str(prefs_path)

    # Run the app; it will exit after smoke mode completes.
    proc = subprocess.run([py, os.path.join(repo_root, 'main.py')], env=env, capture_output=True, text=True, timeout=20)
    assert proc.returncode == 0, f"App exited with {proc.returncode}; stdout={proc.stdout}; stderr={proc.stderr}"

    # Verify the smoke output file exists and contains JSON lines.
    assert out_path.exists(), f"Smoke output file not created: {out_path}"
    with open(out_path, 'r', encoding='utf-8') as f:
        lines = [l.strip() for l in f if l.strip()]
    assert lines, "Smoke output file is empty"
    payload = json.loads(lines[-1])
    # Basic assertions about the payload shape
    assert payload.get('result') == 'ok'
    components = payload.get('components', {})
    prefs = components.get('preferences', {})
    assert 'after' in prefs

    # Finally assert the plist file was created and contains the keys
    assert prefs_path.exists(), f"Preferences plist was not created at {prefs_path}"
    with open(prefs_path, 'rb') as f:
        data = plistlib.load(f)
    assert 'feature_a_enabled' in data and 'feature_b_enabled' in data
