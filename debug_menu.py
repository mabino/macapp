# debug_menu.py
# Inspect the QMenuBar, actions, and roles without starting the event loop.
import sys
from PySide6.QtWidgets import QApplication
from main import SimpleMainWindow

app = QApplication(sys.argv)
# Try setting the application name here too
try:
    app.setApplicationName("The Example")
except Exception:
    pass

print("platform:", sys.platform)
print("applicationName:", app.applicationName())

win = SimpleMainWindow()
menu_bar = win.menuBar()
actions = menu_bar.actions()
print(f"Top-level actions: {len(actions)}")
for i, a in enumerate(actions):
    try:
        role = a.menuRole()
    except Exception:
        role = None
    menu = a.menu()
    menu_title = menu.title() if menu is not None else None
    print(f"[{i}] text={a.text()!r}, menu_title={menu_title!r}, is_separator={a.isSeparator()}, role={role}")
    # If this action has a menu, list its sub-actions
    if menu is not None:
        sub = menu.actions()
        for j, sa in enumerate(sub):
            try:
                srole = sa.menuRole()
            except Exception:
                srole = None
            print(f"    - sub[{j}] text={sa.text()!r}, is_separator={sa.isSeparator()}, role={srole}")

# Print the raw window title for inspection
print("window title:", win.windowTitle())

# Don't exec app.exec(); just exit
app.quit()
