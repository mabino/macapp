#!/usr/bin/env python3
"""
Small helper to prune the built app bundle (dist/The Example.app) to remove
developer tools, QML, translations, and other large optional Qt artifacts.
Run from the project root after a py2app build.
"""
import os
import shutil
from pathlib import Path
import argparse


def _safe_rmtree(p: Path):
    if not p.exists():
        print('not present:', p)
        return
    # Ensure directories and files are writable to avoid permission errors
    for entry in p.rglob('*'):
        try:
            if entry.is_dir():
                entry.chmod(0o755)
            else:
                entry.chmod(0o644)
        except Exception:
            pass
    try:
        if p.is_dir():
            shutil.rmtree(p)
            print('removed:', p)
        else:
            p.unlink()
            print('removed file:', p)
    except Exception as e:
        print('failed to remove', p, e)


def du_h(path: Path):
    try:
        import subprocess
        out = subprocess.check_output(['du', '-sh', str(path)], text=True)
        return out.strip()
    except Exception:
        return 'unknown'


def main():
    p = Path('dist') / 'The Example.app'
    if not p.exists():
        print('App bundle not found at', p)
        return
    before = du_h(p)
    print('Before:', before)

    qlib = p / 'Contents' / 'Resources' / 'lib' / 'python3.13' / 'PySide6' / 'Qt' / 'lib'
    if not qlib.exists():
        print('Qt lib not found at', qlib)
    else:
        pyside_root = qlib.parent.parent
        extras = [
            pyside_root / 'lupdate',
            pyside_root / 'lrelease',
            pyside_root / 'Linguist.app',
            pyside_root / 'Assistant.app',
            pyside_root / 'Designer.app',
            pyside_root / 'Qt' / 'qml',
            pyside_root / 'Qt' / 'libexec',
            pyside_root / 'Qt' / 'translations',
            pyside_root / 'Qt' / 'tools',
            pyside_root / 'Qt' / 'examples',
            pyside_root / 'Qt' / 'doc',
            pyside_root / 'balsam',
        ]
        for ex in extras:
            _safe_rmtree(ex)

        for name in ('qml', 'examples', 'doc', 'tools', 'translations'):
            _safe_rmtree(pyside_root / 'Qt' / name)

        maybe_files = [
            qlib.parent.parent / 'PySide6' / 'Qt' / 'lib' / 'icudtl.dat',
            qlib.parent.parent / 'PySide6' / 'Qt' / 'lib' / 'qtwebengine_devtools_resources.pak',
        ]
        for mf in maybe_files:
            if mf.exists():
                try:
                    mf.unlink()
                    print('removed file:', mf)
                except Exception:
                    pass
    # Remove large PySide6 artifacts
    big_files = [
        pyside_root / 'PySide6_Essentials.json',
        pyside_root / 'lrelease',
        pyside_root / 'lupdate',
        pyside_root / 'qmlls',
        pyside_root / 'qmllint',
        pyside_root / 'qmlformat',
    ]
    for bf in big_files:
        _safe_rmtree(bf)

    # Remove ffmpeg-like libs
    ffmpeg_like = ('libavcodec', 'libavformat', 'libavutil', 'libswresample', 'libswscale')
    for f in pyside_root.rglob('*.dylib'):
        if any(f.name.startswith(name) for name in ffmpeg_like):
            _safe_rmtree(f)

    after = du_h(p)
    print('After:', after)

if __name__ == '__main__':
    main()
