import os
import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QPalette, QColor
from PySide6.QtCore import Qt
from decompyler.window import DecompilerWindow, get_binary_path


def run_self_check() -> int:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QApplication(sys.argv)
    window = DecompilerWindow()

    missing = [name for name in ("pycdc", "pycdas") if not get_binary_path(name).exists()]
    if missing:
        print(f"Self-check failed: missing bundled binaries: {', '.join(missing)}", file=sys.stderr)
        return 1

    not_executable = [
        name for name in ("pycdc", "pycdas")
        if not os.access(get_binary_path(name), os.X_OK)
    ]
    if not_executable:
        print(f"Self-check failed: bundled binaries are not executable: {', '.join(not_executable)}", file=sys.stderr)
        return 1

    print("Self-check passed")
    return 0


if __name__ == "__main__":
    if "--self-check" in sys.argv:
        if sys.stdout is None:
            sys.stdout = open(os.devnull, "w")
        if sys.stderr is None:
            sys.stderr = open(os.devnull, "w")
        exit_code = run_self_check()
        sys.stdout.flush()
        sys.stderr.flush()
        # Skip Qt/Python teardown; some headless Qt builds crash during shutdown.
        os._exit(exit_code)

    app = QApplication(sys.argv)
    
    app.setStyle("Fusion")
    dark_palette = QPalette()
    dark_palette.setColor(QPalette.Window, QColor(30, 30, 30))
    dark_palette.setColor(QPalette.WindowText, QColor(220, 220, 220))
    dark_palette.setColor(QPalette.Base, QColor(20, 20, 20))
    dark_palette.setColor(QPalette.AlternateBase, QColor(35, 35, 35))
    dark_palette.setColor(QPalette.ToolTipBase, QColor(53, 53, 53))
    dark_palette.setColor(QPalette.ToolTipText, QColor(220, 220, 220))
    dark_palette.setColor(QPalette.Text, QColor(220, 220, 220))
    dark_palette.setColor(QPalette.Button, QColor(45, 45, 45))
    dark_palette.setColor(QPalette.ButtonText, QColor(220, 220, 220))
    dark_palette.setColor(QPalette.BrightText, Qt.red)
    dark_palette.setColor(QPalette.Link, QColor(42, 130, 218))
    dark_palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
    dark_palette.setColor(QPalette.HighlightedText, Qt.white)
    
    app.setPalette(dark_palette)

    window = DecompilerWindow()
    window.show()
    sys.exit(app.exec())
