from setuptools import setup
import os
import sys
import glob
import sysconfig

# Temporary pre-build cleanup: setuptools bundles a _vendor directory that
# contains copies of many packages. During py2app collection these vendored
# .dist-info directories can collide with the real site-packages metadata
# and produce "File exists" errors. To avoid that, temporarily rename any
# vendor .dist-info that also has a counterpart in the real site-packages.
# We'll restore them after setup() finishes.
renamed_vendor_distinfos = []
try:
    import setuptools as _setuptools
    vendor_dir = os.path.join(os.path.dirname(_setuptools.__file__), '_vendor')
    if os.path.isdir(vendor_dir):
        site_packages = sysconfig.get_paths().get('purelib') or sysconfig.get_paths().get('platlib')
        if site_packages and os.path.isdir(site_packages):
            # For each .dist-info in the vendor directory, if a same-named
            # package exists in site-packages, hide the vendor copy.
            for vendor_dist in glob.glob(os.path.join(vendor_dir, '*.dist-info')):
                base = os.path.basename(vendor_dist)
                # crude package name extraction: text before first '-' (works for common distributions)
                pkg_name = base.split('-')[0]
                matching = glob.glob(os.path.join(site_packages, f"{pkg_name}-*.dist-info"))
                if matching:
                    new_name = vendor_dist + '.hide'
                    try:
                        os.rename(vendor_dist, new_name)
                        renamed_vendor_distinfos.append((vendor_dist, new_name))
                        print(f'hid vendor dist-info: {vendor_dist}')
                    except OSError:
                        # ignore rename failures; py2app will try and we may still fail
                        pass
except Exception:
    # don't fail the build if this pre-step cannot run; just continue
    pass

APP = ['main.py']
DATA_FILES = []

# Locate a libffi dylib to bundle. _ctypes requires a libffi that
# provides the symbol _ffi_type_longdouble. Search common locations and
# pick the first lib that contains that symbol. Fall back to the
# sys.prefix libffi or the first existing candidate if none contain
# the symbol.
def _lib_exports_longdouble(path):
    # Use nm to check exported symbols; be tolerant of failures.
    try:
        import subprocess
        out = subprocess.check_output(['nm', '-gU', path], stderr=subprocess.DEVNULL, text=True)
        return 'ffi_type_longdouble' in out
    except Exception:
        return False

# candidate paths to try (ordered); include some common places
candidate_paths = [
    os.path.join(sys.prefix, 'lib', 'libffi.8.dylib'),
    '/Users/mabino/homebrew/Caskroom/miniconda/base/envs/macapp/lib/libffi.8.dylib',
    '/Users/mabino/homebrew/Caskroom/miniconda/base/lib/libffi.8.dylib',
    '/opt/homebrew/opt/libffi/lib/libffi.8.dylib',
    '/usr/local/opt/libffi/lib/libffi.8.dylib',
]

frameworks = []
chosen = None
# First prefer any candidate that both exists and exports the longdouble symbol.
for p in candidate_paths:
    if os.path.exists(p) and _lib_exports_longdouble(p):
        chosen = p
        break

# If none exported the symbol, prefer sys.prefix if it exists.
if not chosen:
    spath = os.path.join(sys.prefix, 'lib', 'libffi.8.dylib')
    if os.path.exists(spath):
        chosen = spath

# Otherwise fall back to the first existing candidate.
if not chosen:
    for p in candidate_paths:
        if os.path.exists(p):
            chosen = p
            break

if chosen:
    frameworks.append(chosen)
    print(f'Bundling libffi from: {chosen}')
else:
    print('No libffi candidate found to bundle; proceeding without explicit libffi')

# Add PySide6 and Qt6 dylibs to frameworks to ensure they are bundled
# These are required at runtime and may not be automatically included by py2app
pyside_dylibs = [
    '/Users/mabino/Downloads/macapp/venv/lib/python3.13/site-packages/shiboken6/libshiboken6.abi3.6.9.dylib',
    '/Users/mabino/Downloads/macapp/venv/lib/python3.13/site-packages/PySide6/libpyside6.abi3.6.9.dylib',
    '/Users/mabino/Downloads/macapp/venv/lib/python3.13/site-packages/PySide6/libpyside6qml.abi3.6.9.dylib',
]

qt_dylibs = [
    '/Users/mabino/homebrew/Caskroom/miniconda/base/envs/macapp/lib/libQt6Core.6.dylib',
    '/Users/mabino/homebrew/Caskroom/miniconda/base/envs/macapp/lib/libQt6Gui.6.dylib',
    '/Users/mabino/homebrew/Caskroom/miniconda/base/envs/macapp/lib/libQt6Widgets.6.dylib',
    '/Users/mabino/homebrew/Caskroom/miniconda/base/envs/macapp/lib/libicui18n.75.dylib',
    '/Users/mabino/homebrew/Caskroom/miniconda/base/envs/macapp/lib/libicuuc.75.dylib',
    '/Users/mabino/homebrew/Caskroom/miniconda/base/envs/macapp/lib/libicudata.75.dylib',
]

for dylib in pyside_dylibs + qt_dylibs:
    if os.path.exists(dylib):
        frameworks.append(dylib)
        print(f'Bundling required dylib: {dylib}')
    else:
        print(f'Warning: required dylib not found: {dylib}')

OPTIONS = {
    'argv_emulation': True,
    'iconfile': None,
    'frameworks': frameworks,
    # Ensure jaraco-related modules (used by setuptools/pkg_resources) are bundled.
    # jaraco is a namespace package; include the concrete submodules instead so
    # modulegraph can find them during the build.
    'includes': [
        'jaraco.text',
        'jaraco.context',
        'jaraco.functools',
        'autocommand',
        'more_itertools',
    ],
    # Exclude setuptools' bundled "_vendor" packages. setuptools vendores
    # copies of many libraries (including autocommand, more_itertools, etc.)
    # which can collide with the real packages in site-packages and cause
    # "File exists" errors during py2app's collection step. Excluding the
    # vendored namespace ensures only the real installed packages are bundled.
    # Exclude vendored setuptools._vendor packages AND optional, heavy
    # PySide6/Qt subsystems which are not required by this tiny demo.
    # NOTE: earlier versions accidentally defined 'excludes' twice which
    # caused the first list to be overwritten — merge them here.
    'excludes': [
        # setuptools vendored packages (avoid .dist-info collisions)
        'setuptools._vendor',
        'setuptools._vendor.autocommand',
        'setuptools._vendor.more_itertools',
        'setuptools._vendor.jaraco',
        'setuptools._vendor.jaraco.text',
        'setuptools._vendor.jaraco.context',
        'setuptools._vendor.jaraco.functools',
        'setuptools._vendor.packaging',
        'setuptools._vendor.typing_extensions',
        'setuptools._vendor.inflect',
        'setuptools._vendor.zipp',
        'setuptools._vendor.wheel',
        'setuptools._vendor.platformdirs',
        'setuptools._vendor.tomli',
        'setuptools._vendor.importlib_metadata',
        'setuptools._vendor.backports',
        'setuptools._vendor.typeguard',

        # Large optional PySide6 subsystems (remove if unused)
        'PySide6.QtWebEngineCore',
        'PySide6.QtWebEngineWidgets',
        'PySide6.QtWebEngine',
        'PySide6.QtQuick3D',
        'PySide6.QtQuick3D.*',
        'PySide6.QtPdf',
        'PySide6.QtDesigner',
        'PySide6.phonon',
        'PySide6.QtMultimedia',
        'PySide6.QtMultimediaWidgets',
        'PySide6.QtWebEngineCore.*',
        'PySide6.QtWebEngineWidgets.*',
        'PySide6.QtWebEngine.*',
        # Also exclude translation/build tools and developer binaries
        'PySide6.lupdate',
        'PySide6.lrelease',
        'PySide6.Linguist',
        'PySide6.Linguist.*',
        'PySide6.tools',
    ],
    'plist': {
        'CFBundleName': 'The Example',
        'CFBundleDisplayName': 'The Example',
        'CFBundleIdentifier': 'com.example.theexample',
        # Ensure the app is treated as GUI application
        'LSBackgroundOnly': False,
        'LSUIElement': False,
    },
}

# If running in GitHub Actions the macOS runner may not allow ad-hoc
# codesigning. Some py2app versions don't accept a 'codesign_identity'
# option, so instead detect the CI environment and monkey-patch py2app's
# codesign helper to a no-op to avoid build-time failures. This must run
# before setup() triggers the py2app build.
try:
    # Allow opting in to real codesigning by setting ENABLE_CODESIGN=1
    enable_codesign = os.environ.get('ENABLE_CODESIGN', '').lower() in ('1', 'true', 'yes')
    running_in_actions = os.environ.get('GITHUB_ACTIONS', '').lower() == 'true'
    if running_in_actions and not enable_codesign:
        try:
            import py2app.util as _py2u

            def _noop_codesign(bundle):
                print('GITHUB_ACTIONS: skipping ad-hoc codesign for', bundle)

            _py2u.codesign_adhoc = _noop_codesign
        except Exception:
            # If py2app isn't importable here or util API changes, just continue
            pass
    else:
        if running_in_actions and enable_codesign:
            print('GITHUB_ACTIONS: ENABLE_CODESIGN set — allowing codesign')
except Exception:
    pass

setup(
    app=APP,
    name='The Example',
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)

# (monkey-patch moved above setup())

# Restore any renamed vendor dist-info directories
try:
    for original, hidden in renamed_vendor_distinfos:
        if os.path.exists(hidden) and not os.path.exists(original):
            try:
                os.rename(hidden, original)
                print(f'restored vendor dist-info: {original}')
            except OSError:
                pass
except Exception:
    pass

# Post-build pruning: remove large optional Qt frameworks if present.
# This helps reduce the .app size for minimal apps that don't use
# WebEngine/Quick3D/PDF. Keep this best-effort and don't error if the
# files are missing.
try:
    import shutil

    def _safe_rmtree(path):
        try:
            if os.path.exists(path):
                shutil.rmtree(path)
                print(f'removed: {path}')
        except Exception:
            pass

    dist_root = os.path.join('dist', 'The Example.app', 'Contents', 'Resources')
    # Common PySide6/Qt locations inside the app bundle
    qlib = os.path.join(dist_root, 'lib', 'python3.13', 'PySide6', 'Qt', 'lib')
    # Pruning is opt-in. Control via PRUNE_BUNDLE and PRUNE_LEVEL env vars.
    # PRUNE_BUNDLE (truthy) enables pruning. PRUNE_LEVEL controls how
    # aggressive it is: 'moderate' (default) or 'aggressive'.
    prune_flag = os.environ.get('PRUNE_BUNDLE', '')
    prune_enabled = prune_flag.lower() in ('1', 'true', 'yes')
    prune_level = os.environ.get('PRUNE_LEVEL', 'moderate').lower()
    if os.path.isdir(qlib) and prune_enabled:
        print(f'PRUNE_BUNDLE enabled (level={prune_level}): running post-build pruning')
    elif os.path.isdir(qlib):
        print('PRUNE_BUNDLE not set: skipping post-build pruning')
    if os.path.isdir(qlib) and prune_enabled:
        # Remove WebEngine which is the biggest offender for size
        _safe_rmtree(os.path.join(qlib, 'QtWebEngineCore.framework'))
        _safe_rmtree(os.path.join(qlib, 'QtWebEngineProcess.app'))
        # Optional 3D runtime
        _safe_rmtree(os.path.join(qlib, 'QtQuick3DRuntimeRender.framework'))
        # PDF/Designer/other heavy modules
        _safe_rmtree(os.path.join(qlib, 'QtPdf.framework'))
        _safe_rmtree(os.path.join(qlib, 'QtDesigner.framework'))
        # Also try to remove any additional copies or nested layouts
        # Walk the tree and aggressively remove known large offenders.
        for root, dirs, files in os.walk(qlib):
            for d in list(dirs):
                if any(x in d for x in ('QtWebEngineCore', 'QtQuick3D', 'QtPdf', 'QtDesigner')):
                    target = os.path.join(root, d)
                    try:
                        # try to make files writable before removing (some shipped
                        # files may be read-only and block rmtree)
                        for subroot, subdirs, subfiles in os.walk(target):
                            for f in subfiles:
                                fp = os.path.join(subroot, f)
                                try:
                                    os.chmod(fp, 0o644)
                                except Exception:
                                    pass
                        _safe_rmtree(target)
                        # reflect change in the dirs list so walk doesn't recuse
                        dirs.remove(d)
                    except Exception:
                        pass
        # Remove some common large files used by WebEngine that may still be present
        maybe_files = [
            os.path.join(qlib, '..', 'PySide6', 'Qt', 'lib', 'icudtl.dat'),
            os.path.join(qlib, '..', 'PySide6', 'Qt', 'lib', 'qtwebengine_devtools_resources.pak'),
        ]
        for mf in maybe_files:
            try:
                if os.path.exists(mf):
                    os.remove(mf)
                    print(f'removed file: {mf}')
            except Exception:
                pass
        # Remove large PySide6 packaging/metadata and developer binaries
        extras_files = [
            os.path.join(qlib, '..', 'PySide6', 'PySide6_Essentials.json'),
            os.path.join(qlib, '..', 'PySide6', 'lrelease'),
            os.path.join(qlib, '..', 'PySide6', 'lupdate'),
            os.path.join(qlib, '..', 'PySide6', 'qmlls'),
            os.path.join(qlib, '..', 'PySide6', 'qmllint'),
            os.path.join(qlib, '..', 'PySide6', 'qmlformat'),
        ]
        for ef in extras_files:
            try:
                if os.path.exists(ef):
                    if os.path.isdir(ef):
                        shutil.rmtree(ef)
                        print(f'removed: {ef}')
                    else:
                        os.remove(ef)
                        print(f'removed file: {ef}')
            except Exception:
                pass
        # compute the PySide6 top directory inside the bundle reliably
        # qlib points to .../PySide6/Qt/lib, so stepping two levels up gives
        # the PySide6 root directory.
        pyside_root = os.path.normpath(os.path.join(qlib, '..', '..'))

        extras = [
            os.path.join(pyside_root, 'lupdate'),
            os.path.join(pyside_root, 'lrelease'),
            os.path.join(pyside_root, 'Linguist.app'),
            os.path.join(pyside_root, 'Assistant.app'),
            os.path.join(pyside_root, 'Designer.app'),
            # QML and qml plugins (safe to remove for non-QML apps)
            os.path.join(pyside_root, 'Qt', 'qml'),
            os.path.join(pyside_root, 'Qt', 'libexec'),
            os.path.join(pyside_root, 'Qt', 'translations'),
            os.path.join(pyside_root, 'Qt', 'tools'),
            os.path.join(pyside_root, 'Qt', 'examples'),
            os.path.join(pyside_root, 'Qt', 'doc'),
            os.path.join(pyside_root, 'balsam'),
        ]

        for target in extras:
            _safe_rmtree(target)

        # Remove ffmpeg/av libraries bundled by Qt (not needed for simple widgets apps)
        ffmpeg_like = ('libavcodec', 'libavformat', 'libavutil', 'libswresample', 'libswscale')
        for root, dirs, files in os.walk(qlib):
            for f in list(files):
                if any(f.startswith(name) and f.endswith('.dylib') for name in ffmpeg_like):
                    _safe_rmtree(os.path.join(root, f))

        # Moderate vs aggressive pruning:
        # - moderate: remove WebEngine, Quick3D, PDF, Designer, developer tools,
        #             lrelease/lupdate, ffmpeg libs, big packaging JSON, and QML examples
        # - aggressive: additionally remove QtQml/QtQuick frameworks and many plugins
        if prune_level == 'aggressive':
            # remove QtQml and QtQuick frameworks and their plugins
            _safe_rmtree(os.path.join(qlib, '..', 'PySide6', 'Qt', 'lib', 'QtQml.framework'))
            _safe_rmtree(os.path.join(qlib, '..', 'PySide6', 'Qt', 'lib', 'QtQuick.framework'))
            # remove qml plugins (many are safe to remove for pure widgets apps)
            _safe_rmtree(os.path.join(pyside_root, 'Qt', 'qml'))
except Exception:
    pass
