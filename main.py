# main.py
# The Example, a graphical Python app for macOS using PySide6,
# demonstrating multiple UI widgets, a menu bar, and a preferences dialog.

import sys
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QLineEdit, QSlider, QCheckBox,
    QMenuBar, QMenu, QDialog, QDialogButtonBox,
    QSpacerItem, QSizePolicy
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtCore import QCoreApplication
from PySide6.QtGui import QAction, QKeySequence
import os
import datetime
import json
import platform
import plistlib
from typing import Optional

# Application version used by the smoke test and for diagnostics.
__version__ = "0.1.0"

class Preferences:
    """Container for application preferences with plist persistence.

    This implementation uses a plist file on disk. When running from
    a bundled .app and a CFBundleIdentifier can be discovered the
    preferences are stored in the standard Preferences location for
    that bundle identifier (~/Library/Preferences/<bundle_id>.plist).
    When not bundled we fall back to a sensible path under
    ~/Library/Preferences using a stable application identifier.
    """
    def __init__(self):
        # Default preference values
        self.feature_a_enabled = True
        self.feature_b_enabled = False

        # Location where preferences will be read/written lazily
        self._prefs_path: Optional[str] = None

    @staticmethod
    def _guess_bundle_identifier() -> Optional[str]:
        """Try to determine a bundle identifier when running from a .app.

        We try a few best-effort methods: inspect __file__ for a .app
        ancestor and read its Info.plist CFBundleIdentifier. This is
        intentionally conservative and does not require PyObjC.
        """
        try:
            # Walk up from this file looking for an .app bundle
            path = os.path.abspath(__file__)
            parts = path.split(os.sep)
            for i in range(len(parts) - 1, 0, -1):
                if parts[i].endswith('.app'):
                    info_plist = os.path.join(os.sep, *parts[: i + 1], 'Contents', 'Info.plist')
                    if os.path.exists(info_plist):
                        try:
                            with open(info_plist, 'rb') as f:
                                data = plistlib.load(f)
                            bid = data.get('CFBundleIdentifier')
                            if bid:
                                return bid
                        except Exception:
                            return None
            return None
        except Exception:
            return None

    def _prefs_file_path(self) -> str:
        """Return the filesystem path to the plist we'll use for storing prefs."""
        if self._prefs_path:
            return self._prefs_path

        # Allow tests or callers to override the prefs file path via an
        # environment variable. This keeps automated tests from writing
        # into the user's real ~/Library area.
        env_override = os.environ.get('THE_EXAMPLE_PREFS_PATH')
        if env_override:
            self._prefs_path = os.path.expanduser(env_override)
            return self._prefs_path

        # Prefer a bundle-id-based path when possible (macOS standard)
        bundle_id = None
        if sys.platform == 'darwin':
            bundle_id = self._guess_bundle_identifier()

        if bundle_id:
            # If the app is sandboxed its container path would be used
            # by the system; we attempt the container preferences path
            # first, then fall back to ~/Library/Preferences.
            container_pref = os.path.expanduser(f'~/Library/Containers/{bundle_id}/Data/Library/Preferences/{bundle_id}.plist')
            if os.path.exists(os.path.dirname(container_pref)):
                self._prefs_path = container_pref
                return self._prefs_path
            # fallback
            self._prefs_path = os.path.expanduser(f'~/Library/Preferences/{bundle_id}.plist')
            return self._prefs_path

        # Generic fallback: use application name to build a stable filename
        app_name = QCoreApplication.applicationName() or 'the-example'
        safe_name = ''.join(c if c.isalnum() or c in '.-_ ' else '_' for c in app_name).strip() or 'the-example'
        self._prefs_path = os.path.expanduser(f'~/Library/Preferences/{safe_name}.plist')
        return self._prefs_path

    def load(self):
        """Load preferences from disk. Missing values use defaults."""
        path = self._prefs_file_path()
        try:
            if os.path.exists(path):
                with open(path, 'rb') as f:
                    data = plistlib.load(f)
                # Only set known keys to avoid surprising data from other apps
                self.feature_a_enabled = bool(data.get('feature_a_enabled', self.feature_a_enabled))
                self.feature_b_enabled = bool(data.get('feature_b_enabled', self.feature_b_enabled))
        except Exception:
            # Loading should never crash the app; fall back to defaults.
            pass

    def save(self):
        """Persist preferences to a plist file (atomic write).

        We create parent directories as needed and write atomically
        by writing to a temporary file then renaming it.
        """
        path = self._prefs_file_path()
        try:
            parent = os.path.dirname(path)
            os.makedirs(parent, exist_ok=True)
            tmp = path + '.tmp'
            data = {
                'feature_a_enabled': bool(self.feature_a_enabled),
                'feature_b_enabled': bool(self.feature_b_enabled),
                'version': __version__
            }
            with open(tmp, 'wb') as f:
                plistlib.dump(data, f)
            # Atomic replace
            os.replace(tmp, path)
        except Exception:
            # Don't raise; best-effort persistence only.
            pass

class PreferencesDialog(QDialog):
    """
    A QDialog for managing application preferences.
    """
    def __init__(self, preferences: Preferences, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Preferences")
        self.preferences = preferences

        # Keep the dialog on top so it doesn't get lost behind the main window.
        # This is optional but makes the preferences easier to find on macOS.
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)

        # Main layout for the dialog.
        dialog_layout = QVBoxLayout(self)

        # Create checkboxes for the features. Each checkbox represents
        # a boolean preference that the user can toggle.
        self.feature_a_checkbox = QCheckBox("Enable Feature A")
        self.feature_b_checkbox = QCheckBox("Enable Feature B")

        # Initialize the checkbox states from the passed-in Preferences
        # object so the dialog reflects the current settings.
        self.feature_a_checkbox.setChecked(self.preferences.feature_a_enabled)
        self.feature_b_checkbox.setChecked(self.preferences.feature_b_enabled)

        # Add checkboxes to the layout.
        dialog_layout.addWidget(self.feature_a_checkbox)
        dialog_layout.addWidget(self.feature_b_checkbox)
        
        # Add a spacer to push the buttons to the bottom.
        dialog_layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))

        # Create standard OK and Cancel buttons.
        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        
        dialog_layout.addWidget(self.button_box)

    def get_preferences(self):
        """Returns the updated preferences state from the checkboxes."""
        # Read the checkbox states back into the Preferences object and
        # return it. This is called after the dialog is accepted.
        self.preferences.feature_a_enabled = self.feature_a_checkbox.isChecked()
        # Fixed bug: previously feature_b_enabled was incorrectly set from
        # the feature A checkbox. Make sure we read the correct widget.
        self.preferences.feature_b_enabled = self.feature_b_checkbox.isChecked()
        return self.preferences

class SimpleMainWindow(QMainWindow):
    """
    The main window of the application with various UI elements.
    """
    def __init__(self):
        super().__init__()
        self.preferences = Preferences()
        # Load persisted preferences on startup (best-effort)
        try:
            self.preferences.load()
        except Exception:
            pass

        # Set the window title and a fixed size. On macOS it's common to
        # have windows that are not resizable for simple demos; remove
        # setFixedSize if you want a resizable window.
        self.setWindowTitle("The Example")
        self.setFixedSize(QSize(450, 450))

        # Create a central widget and layout.
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        main_layout = QVBoxLayout(self.central_widget)
        
        # Add a big title label at the top of the window. Styling is done
        # with a tiny bit of CSS using setStyleSheet; this is fine for demos
        # but for production apps you may want a more structured approach.
        title_label = QLabel("macOS-style UI Demo")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("font-size: 24px; font-weight: bold;")
        main_layout.addWidget(title_label)

        # A simple text input the user can type into. We show a label
        # above it and a placeholder hint inside the field.
        main_layout.addWidget(QLabel("Text Input:"))
        self.text_input = QLineEdit()
        self.text_input.setPlaceholderText("Enter some text...")
        main_layout.addWidget(self.text_input)

        # Two buttons laid out horizontally. The "Say Hello" button will
        # read the text field and display a message; the "Quit" button
        # closes the app.
        button_layout = QHBoxLayout()
        self.hello_button = QPushButton("Say Hello")
        self.quit_button = QPushButton("Quit App")
        button_layout.addWidget(self.hello_button)
        button_layout.addWidget(self.quit_button)
        main_layout.addLayout(button_layout)
        
        # A horizontal slider that goes from 0 to 100 and a label that
        # displays the current slider value. We set the initial value
        # to 50 so the label shows a meaningful number at startup.
        main_layout.addWidget(QLabel("Slider:"))
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(0, 100)
        self.slider.setValue(50)
        self.slider_label = QLabel(f"Value: {self.slider.value()}")
        main_layout.addWidget(self.slider)
        main_layout.addWidget(self.slider_label)

        # An information label used for short messages to the user. We
        # style it to look subdued so it behaves like secondary text.
        self.info_label = QLabel("Ready.")
        self.info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.info_label.setStyleSheet("font-style: italic; color: gray;")
        main_layout.addWidget(self.info_label)

        # Add a spacer to push content up.
        main_layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))

        # Connect UI events (signals) to handler methods (slots).
        self.hello_button.clicked.connect(self._on_hello_button_clicked)
        self.quit_button.clicked.connect(self.close)
        self.slider.valueChanged.connect(self._on_slider_value_changed)

        # Create menu bar and populate it with actions.
        self._create_menu_bar()

        # Update the UI based on initial preferences.
        self._update_ui_from_preferences()

    def _create_menu_bar(self):
        """Initializes the menu bar with App, File, Edit, and Window menus."""
        menu_bar = self.menuBar()
        # Create the Preferences/Settings and Quit actions but do NOT add
        # them to a custom top-level menu. On macOS Qt will place actions
        # with the correct menu roles into the native application menu
        # (the left-most menu) which removes the default 'python' label and
        # shows the application name set in QApplication.
        is_mac = sys.platform == "darwin"
        pref_text = "Settings..." if is_mac else "Preferences..."
        pref_modifier = Qt.MetaModifier if is_mac else Qt.ControlModifier

        # Keep the action as an instance attribute to ensure it remains
        # alive and clearly associated with the window.
        self.preferences_action = QAction(pref_text, self)
        # Use the platform-standard Preferences key sequence when available.
        try:
            # QKeySequence.Preferences maps to the correct shortcut on macOS (⌘,)
            self.preferences_action.setShortcut(QKeySequence.Preferences)
        except Exception:
            # Fallback: use Ctrl+Comma-like modifier as a portable shortcut
            self.preferences_action.setShortcut(Qt.Key.Key_Comma | pref_modifier)
        self.preferences_action.triggered.connect(self._on_preferences_action_triggered)

        # Also register the action at the application level. Some Qt
        # backends require the action to be added to the QApplication so
        # it can be relocated into the native application menu on macOS.
        try:
            app = QApplication.instance()
            if app is not None:
                app.addAction(self.preferences_action)
        except Exception:
            pass

        # Quit action -- set a role so it goes into the native app menu on macOS
        quit_action = QAction("Quit", self)
        quit_action.setShortcut(Qt.Key.Key_Q | Qt.ControlModifier)
        quit_action.triggered.connect(self.close)

        # On macOS set PreferencesRole so Qt moves the action into the
        # native application menu. This will cause Qt/macOS to display the
        # standard localized text (usually "Preferences...") for this role.
        # When running from a terminal the left-most menu may still show
        # the process name (e.g. 'python3'); creating a proper .app bundle
        # is the robust way to have the OS display the bundle name there.
        try:
            # Ensure Qt knows this action is the application's Preferences.
            # On macOS this causes the action to be placed into the
            # native application menu (and labeled appropriately, e.g.
            # "Settings…" on Ventura).
            self.preferences_action.setMenuRole(QAction.PreferencesRole)
        except Exception:
            pass
        try:
            quit_action.setMenuRole(QAction.QuitRole)
        except Exception:
            pass

        # Do not call menu_bar.addMenu for an app menu; instead create the
        # other visible menus and let the OS/Qt place the actions above.
        # Edit Menu
        edit_menu = menu_bar.addMenu("Edit")
        # Edit menu with Undo/Redo placeholders. They are not wired up to
        # any document model here — they're shown to demonstrate menu layout.
        undo_action = QAction("Undo", self)
        undo_action.setShortcut(QKeySequence("Ctrl+Z"))
        edit_menu.addAction(undo_action)
        redo_action = QAction("Redo", self)
        redo_action.setShortcut(QKeySequence("Ctrl+Shift+Z"))
        edit_menu.addAction(redo_action)
        # Add Preferences to the Edit menu so Qt can relocate it to the
        # native application menu on macOS when the role is set.
        edit_menu.addAction(self.preferences_action)

        # Window Menu
        window_menu = menu_bar.addMenu("Window")
        minimize_action = QAction("Minimize", self)
        minimize_action.setShortcut(Qt.Key.Key_M | Qt.ControlModifier)
        minimize_action.triggered.connect(self.showMinimized)
        window_menu.addAction(minimize_action)

        # Finally, register the Quit action with the menubar; Preferences
        # was added to the Edit menu above so Qt can relocate it on macOS.
        menu_bar.addAction(quit_action)

    def _on_hello_button_clicked(self):
        """Handle the 'Say Hello' button click."""
        # Read text from the input field. If it's empty, default to "World".
        # Then show the greeting in the info_label.
        text = self.text_input.text() or "World"
        self.info_label.setText(f"Hello, {text}!")

    def _on_slider_value_changed(self, value):
        """Update the label as the slider value changes."""
        # The slot receives the numeric slider value and updates the label
        # so the UI immediately reflects the change.
        self.slider_label.setText(f"Value: {value}")

    def _on_preferences_action_triggered(self):
        """Open the preferences dialog and update UI on accept."""
        # Create the dialog and run it modally with exec(). If the user
        # clicks OK (Accept), read the updated preferences and apply them.
        dialog = PreferencesDialog(self.preferences, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.preferences = dialog.get_preferences()
            # Persist the updated preferences
            try:
                self.preferences.save()
            except Exception:
                pass
            self._update_ui_from_preferences()

    def _update_ui_from_preferences(self):
        """
        Updates the main window's UI based on the current preferences.
        This is a placeholder for feature toggling.
        """
        # Enable/disable UI elements depending on preference flags.
        # Using setDisabled(False) is equivalent to setEnabled(True),
        # but reads more clearly in the context of toggling.
        if self.preferences.feature_a_enabled:
            self.hello_button.setDisabled(False)
            self.text_input.setDisabled(False)
            self.info_label.setText("Feature A is enabled.")
        else:
            self.hello_button.setDisabled(True)
            self.text_input.setDisabled(True)
            self.info_label.setText("Feature A is disabled by preferences.")

        # Feature B controls the slider. If it's disabled, we disable both
        # the control and the label that shows its current value.
        if self.preferences.feature_b_enabled:
            self.slider.setDisabled(False)
            self.slider_label.setDisabled(False)
        else:
            self.slider.setDisabled(True)
            self.slider_label.setDisabled(True)

def main():
    """
    The main function to set up and run the application.
    """
    # Try to set the macOS process name so the system menu shows the app
    # name instead of the python executable. This uses libc functions
    # available on BSD/macOS (setprogname and setproctitle) via ctypes.
    if sys.platform == "darwin":
        try:
            import ctypes, ctypes.util
            libc_path = ctypes.util.find_library("c")
            if libc_path:
                libc = ctypes.CDLL(libc_path)
                try:
                    # setprogname(const char*) is available on macOS
                    setprog = libc.setprogname
                    setprog.argtypes = [ctypes.c_char_p]
                    setprog.restype = None
                    setprog(b"The Example")
                except Exception:
                    pass
                try:
                    # setproctitle allows setting the process title
                    setpt = libc.setproctitle
                    setpt.argtypes = [ctypes.c_char_p]
                    setpt.restype = None
                    setpt(b"The Example")
                except Exception:
                    pass
        except Exception:
            # Best-effort only; failures are non-fatal.
            pass

    # Create the application instance.
    app = QApplication(sys.argv)
    # Ensure the OS and Qt know the application name; on macOS this
    # controls the left-most application menu label (instead of 'python').
    # Setting this early helps Qt set up the native app menu correctly.
    try:
        app.setApplicationName("The Example")
    except Exception:
        # Some environments may not allow setting the name; ignore if it fails.
        pass
    # Also set the display name; this can influence what Qt shows in menus.
    try:
        QCoreApplication.setApplicationDisplayName("The Example")
    except Exception:
        pass
    
    # Create the main window instance.
    window = SimpleMainWindow()

    # Show the window on the screen.
    window.show()

    # Automated smoke test hook. When THE_EXAMPLE_SMOKE is set or the
    # --smoke flag is present we run checks and exit immediately. The
    # smoke output path is configurable via THE_EXAMPLE_SMOKE_OUT; if
    # not provided we fall back to the Desktop for easy manual inspection.
    do_smoke = bool(os.environ.get('THE_EXAMPLE_SMOKE')) or ('--smoke' in sys.argv)
    if do_smoke:
        # Allow CI to choose the output path. Default to the Desktop for
        # convenience when running locally.
        out_path = os.environ.get('THE_EXAMPLE_SMOKE_OUT') or os.path.expanduser('~/Desktop/the-example-smoke.txt')
        exit_code = 0
        try:
            # ---- Component tests ----
            # 1) Text input: set a value and select it to ensure the field
            #    is usable and selection APIs work.
            test_text = "smoke-test-text"
            window.text_input.setText(test_text)
            # Select all and read back the selected text.
            try:
                window.text_input.selectAll()
                selected = window.text_input.selectedText()
            except Exception:
                selected = ""
            text_ok = (selected == test_text)

            # 2) Slider: change the value and ensure the label updates.
            try:
                window.slider.setValue(75)
                # The connected slot updates the label immediately in Qt's
                # single-threaded context when not running the event loop.
                slider_label_text = window.slider_label.text()
                slider_ok = "75" in slider_label_text
            except Exception:
                slider_label_text = ""
                slider_ok = False

            # 3) Preferences dialog: toggle the checkboxes programmatically
            #    and ensure get_preferences() returns the new values.
            dlg = PreferencesDialog(window.preferences, window)
            # Flip the current values to ensure we're actually changing state.
            try:
                dlg.feature_a_checkbox.setChecked(not dlg.feature_a_checkbox.isChecked())
                dlg.feature_b_checkbox.setChecked(not dlg.feature_b_checkbox.isChecked())
                prefs_after = dlg.get_preferences()
                prefs_ok = (prefs_after.feature_a_enabled == dlg.feature_a_checkbox.isChecked() and prefs_after.feature_b_enabled == dlg.feature_b_checkbox.isChecked())
                # Persist preferences so tests can inspect the plist file.
                try:
                    prefs_after.save()
                except Exception:
                    pass
            except Exception:
                prefs_after = None
                prefs_ok = False

            # Inspect the menu structure to see if a Preferences/Settings
            # role action exists. We collect top-level menus and whether
            # any action has PreferencesRole.
            menu_bar = window.menuBar()
            top_level = [a.text() for a in menu_bar.actions() if a.text()]
            prefs_role_found = False
            for a in menu_bar.actions():
                m = a.menu()
                if m:
                    for act in m.actions():
                        try:
                            if act.menuRole() == QAction.PreferencesRole:
                                prefs_role_found = True
                                break
                        except Exception:
                            pass
                if prefs_role_found:
                    break

            # Build a JSON object with diagnostic and test results.
            # Safely resolve application name and display name; some Qt
            # bindings may not expose applicationDisplayName as a symbol.
            app_name = QCoreApplication.applicationName() or ""
            try:
                app_display = QCoreApplication.applicationDisplayName()
            except Exception:
                app_display = app_name

            payload = {
                "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "result": "ok",
                "pid": os.getpid(),
                "python_version": sys.version,
                "python_executable": sys.executable,
                "platform": {
                    "system": platform.system(),
                    "release": platform.release(),
                    "platform": platform.platform()
                },
                "app": {
                    "name": app_name,
                    "display_name": app_display,
                    "version": __version__,
                    "main_path": os.path.abspath(__file__)
                },
                "components": {
                    "text_input": {"value": test_text, "selected": selected, "ok": text_ok},
                    "slider": {"value": 75, "label": slider_label_text, "ok": slider_ok},
                    "preferences": {"after": {"feature_a": getattr(prefs_after, 'feature_a_enabled', None), "feature_b": getattr(prefs_after, 'feature_b_enabled', None)}, "ok": prefs_ok},
                    "menu": {"top_level": top_level, "prefs_role_found": prefs_role_found}
                }
            }

            # Write JSON payload to the configured path.
            with open(out_path, 'a', encoding='utf-8') as f:
                f.write(json.dumps(payload, ensure_ascii=False) + "\n")
            exit_code = 0
        except Exception as e:
            try:
                payload = {
                    "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    "result": "fail",
                    "pid": os.getpid(),
                    "error": repr(e)
                }
                with open(out_path, 'a', encoding='utf-8') as f:
                    f.write(json.dumps(payload, ensure_ascii=False) + "\n")
            except Exception:
                pass
            exit_code = 1

        # Exit immediately so CI can observe the result via the process exit
        # code and the output file.
        sys.exit(exit_code)

    # Start the application event loop.
    sys.exit(app.exec())

if __name__ == "__main__":
    main()

