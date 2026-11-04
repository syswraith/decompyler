import contextlib
import io
import os
import platform
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import traceback
from pathlib import Path

from PySide6.QtCore import QThread, Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QPushButton, QFileDialog, 
    QHBoxLayout, QLabel, QComboBox, QCheckBox, QSplitter, QStackedWidget,
    QMessageBox, QDialog
)
from PySide6.QtGui import QFont, QKeySequence, QPixmap, QShortcut

from .config import CONFIG_FILE, DEFAULT_SETTINGS, load_settings, save_settings
from .highlighter import PygmentsSyntaxHighlighter
from .dialogs import SettingsDialog, FindDialog
from .resources import resource_path
from .widgets import CodeEditor


def get_binary_path(tool_name: str, settings: dict | None = None) -> Path:
    settings = settings or load_settings()
    key = "pycdc_path" if tool_name == "pycdc" else "pycdas_path"
    configured = settings.get(key) or DEFAULT_SETTINGS[key]
    return Path(configured).expanduser()


def find_system_python() -> str | None:
    candidates = ["py", "python", "python3"] if os.name == "nt" else ["python3", "python"]
    for name in candidates:
        path = shutil.which(name)
        if path:
            return path
    return None


def clean_subprocess_env() -> dict[str, str]:
    env = os.environ.copy()
    bundle_dir = os.environ.get("_PYI_APPLICATION_HOME_DIR") or getattr(sys, "_MEIPASS", None)
    if not bundle_dir:
        return env

    bundle_path = Path(bundle_dir).resolve()
    for key in ("LD_LIBRARY_PATH", "DYLD_LIBRARY_PATH"):
        value = env.get(key)
        if not value:
            continue

        entries = []
        for entry in value.split(os.pathsep):
            if not entry:
                continue
            try:
                entry_path = Path(entry).resolve()
            except OSError:
                entry_path = Path(entry)
            if entry_path == bundle_path or bundle_path in entry_path.parents:
                continue
            entries.append(entry)

        if entries:
            env[key] = os.pathsep.join(entries)
        else:
            env.pop(key, None)
    return env


EXTRA_STDLIB_MODULES = {"annotationlib", "compression", "_colorize", "_opcode_metadata"}
BOOTSTRAP_PREFIXES = ("pyimod", "pyiboot", "pyi_rth")
UUID_SUFFIX = re.compile(
    r"_[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


def module_top_level(pyc_path: Path, root: Path) -> str:
    try:
        rel = pyc_path.relative_to(root)
    except ValueError:
        rel = Path(pyc_path.name)
    parts = rel.parts
    if parts:
        first_part = parts[0].lower()
        if ".pyz" in first_part and first_part.endswith("_extracted"):
            parts = parts[1:]
    if not parts:
        return ""
    module_name = Path(parts[0]).stem if len(parts) == 1 else parts[0]
    return UUID_SUFFIX.sub("", module_name)


def should_hide_module(module_name: str) -> bool:
    if not module_name:
        return False
    return (
        module_name in sys.stdlib_module_names
        or module_name in EXTRA_STDLIB_MODULES
        or module_name.startswith(BOOTSTRAP_PREFIXES)
    )


class ExtractionWorker(QThread):
    finished_ok = Signal(object, object, str)
    failed = Signal(str)

    def __init__(self, binary: Path, work_dir: Path, parent=None):
        super().__init__(parent)
        self.binary = binary
        self.work_dir = work_dir

    def run(self):
        from pyinstxtractor_ng import PyInstArchive

        output = io.StringIO()
        error = io.StringIO()
        previous_cwd = os.getcwd()
        try:
            shutil.rmtree(self.work_dir, ignore_errors=True)
            self.work_dir.mkdir(parents=True, exist_ok=True)
            os.chdir(self.work_dir)
            archive = PyInstArchive(str(self.binary.resolve()))
            with contextlib.redirect_stdout(output), contextlib.redirect_stderr(error):
                if not archive.open():
                    raise RuntimeError(error.getvalue().strip() or "Could not open the selected binary.")
                try:
                    if not archive.checkFile():
                        raise RuntimeError(error.getvalue().strip() or "Unsupported or invalid PyInstaller archive.")
                    if not archive.getCArchiveInfo():
                        raise RuntimeError(error.getvalue().strip() or "Could not read the archive table of contents.")
                    archive.parseTOC()
                    archive.extractFiles(False)
                finally:
                    archive.close()
        except Exception as exc:
            details = error.getvalue().strip()
            self.failed.emit(f"{exc}\n\n{details}".strip())
            return
        finally:
            os.chdir(previous_cwd)

        extracted = self.work_dir / f"{self.binary.name}_extracted"
        if not extracted.exists():
            extracted = self.work_dir
        self.finished_ok.emit(extracted, sorted(extracted.rglob("*.pyc")), output.getvalue())


class DecompileWorker(QThread):
    finished_ok = Signal(object, str, str)

    def __init__(self, pyc_path: Path, settings: dict, parent=None):
        super().__init__(parent)
        self.pyc_path = pyc_path
        self.settings = settings

    def _run_tool(self, tool_name: str) -> str:
        binary = get_binary_path(tool_name, self.settings)
        label = "Disassembly" if tool_name == "pycdas" else "Decompilation"
        if not binary.exists():
            return (
                f"Error: {tool_name} binary not found at {binary}.\n"
                f"Set its path in Settings or in {CONFIG_FILE}."
            )
        try:
            result = subprocess.run(
                [str(binary), str(self.pyc_path)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=True,
                timeout=120,
                env=clean_subprocess_env(),
            )
            return result.stdout
        except subprocess.TimeoutExpired:
            return f"{label} Error:\nTimed out after 120 seconds."
        except subprocess.CalledProcessError as exc:
            return f"{label} Error:\n{exc.stderr or exc.stdout or exc}"
        except OSError as exc:
            return f"{label} Error:\n{exc}"

    def run(self):
        asm = self._run_tool("pycdas")
        code = self._run_tool("pycdc")
        self.finished_ok.emit(self.pyc_path, asm, code)


class RunBufferWorker(QThread):
    finished_ok = Signal(str)

    def __init__(self, code: str, script_path: Path, parent=None):
        super().__init__(parent)
        self.code = code
        self.script_path = script_path

    def run(self):
        output = io.StringIO()
        previous_cwd = os.getcwd()
        try:
            os.chdir(self.script_path.parent)
            with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
                globals_dict = {"__name__": "__main__", "__file__": str(self.script_path)}
                exec(compile(self.code, str(self.script_path), "exec"), globals_dict)
        except SystemExit as exc:
            if exc.code not in (None, 0):
                output.write(f"\nExited with status {exc.code}\n")
        except BaseException:
            output.write(traceback.format_exc())
        finally:
            os.chdir(previous_cwd)
        self.finished_ok.emit(output.getvalue() or "(no output)")


class DecompilerWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Decompyler")
        self.resize(1350, 850)

        self.settings = load_settings()

        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        self.init_welcome_page()
        self.init_workspace_page()

        self.selected_binary: Path | None = None
        self.extracted_dir: Path | None = None
        self.pyc_files: list[Path] = []

        # Setup Ctrl+F Find Shortcut
        self.find_shortcut = QShortcut(QKeySequence("Ctrl+F"), self)
        self.find_shortcut.activated.connect(self.open_find_dialog)

    def init_welcome_page(self):
        self.welcome_widget = QWidget()
        layout = QVBoxLayout(self.welcome_widget)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(15)

        logo_path = resource_path("assets/logo-rounded.png")
        if logo_path.exists():
            logo_label = QLabel()
            logo_label.setPixmap(
                QPixmap(str(logo_path)).scaled(
                    180, 180, Qt.KeepAspectRatio, Qt.SmoothTransformation
                )
            )
            logo_label.setAlignment(Qt.AlignCenter)
            layout.addWidget(logo_label, alignment=Qt.AlignCenter)

        title_label = QLabel("Decompyler")
        title_font = QFont()
        title_font.setPointSize(32)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)

        subtitle_label = QLabel("a tool to disassemble and decompile pyinstaller binaries")
        subtitle_label.setAlignment(Qt.AlignCenter)
        subtitle_label.setStyleSheet("color: #888888; font-size: 15px;")

        self.select_bin_btn = QPushButton("Select Compiled Binary (EXE/ELF)")
        self.select_bin_btn.setMinimumHeight(52)
        self.select_bin_btn.setMinimumWidth(350)
        self.select_bin_btn.clicked.connect(self.select_binary)

        settings_btn = QPushButton("⚙ Settings")
        settings_btn.setMinimumHeight(40)
        settings_btn.setMinimumWidth(350)
        settings_btn.clicked.connect(self.open_settings)

        footer_link = QLabel('<a href="https://github.com/syswraith/decompyler" style="color: #3daee9; text-decoration: none;">GitHub Repository</a>')
        footer_link.setAlignment(Qt.AlignCenter)
        footer_link.setOpenExternalLinks(True)
        footer_link.setStyleSheet("font-size: 14px;")

        footer_author = QLabel('made with ❤️ by <a href="https://syswraith.com" style="color: #3daee9; text-decoration: none;">syswraith</a>')
        footer_author.setAlignment(Qt.AlignCenter)
        footer_author.setOpenExternalLinks(True)
        footer_author.setStyleSheet("color: #777777; font-size: 14px;")

        layout.addWidget(title_label)
        layout.addWidget(subtitle_label)
        layout.addSpacing(20)
        layout.addWidget(self.select_bin_btn, alignment=Qt.AlignCenter)
        layout.addWidget(settings_btn, alignment=Qt.AlignCenter)
        layout.addSpacing(35)
        layout.addWidget(footer_link, alignment=Qt.AlignCenter)
        layout.addWidget(footer_author, alignment=Qt.AlignCenter)

        self.stack.addWidget(self.welcome_widget)

    def init_workspace_page(self):
        self.workspace_widget = QWidget()
        main_layout = QVBoxLayout(self.workspace_widget)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(12)

        top_bar = QHBoxLayout()
        top_bar.setSpacing(10)
        
        self.change_bin_btn = QPushButton("← Change Binary")
        self.change_bin_btn.clicked.connect(lambda: self.stack.setCurrentIndex(0))
        
        self.bin_info_label = QLabel("No binary selected")
        self.bin_info_label.setStyleSheet("font-weight: bold; color: #3daee9;")

        settings_btn = QPushButton("⚙ Settings")
        settings_btn.clicked.connect(self.open_settings)

        top_bar.addWidget(self.change_bin_btn)
        top_bar.addWidget(self.bin_info_label)
        top_bar.addWidget(settings_btn)
        top_bar.addStretch()

        top_bar.addWidget(QLabel("Module:"))
        self.pyc_selector = QComboBox()
        self.pyc_selector.setMinimumWidth(320)
        self.pyc_selector.setEnabled(False)
        self.pyc_selector.currentIndexChanged.connect(self.process_selected_pyc)
        top_bar.addWidget(self.pyc_selector)

        self.hide_stdlib_checkbox = QCheckBox("Hide stdlib")
        self.hide_stdlib_checkbox.setChecked(self.settings["hide_stdlib"])
        self.hide_stdlib_checkbox.toggled.connect(self.toggle_hide_stdlib)
        top_bar.addWidget(self.hide_stdlib_checkbox)

        main_layout.addLayout(top_bar)

        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(6)

        # Left Pane: Disassembler CodeEditor
        left_container = QWidget()
        left_layout = QVBoxLayout(left_container)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(6)
        
        left_label = QLabel("Disassembled Bytecode (pycdas)")
        left_label.setStyleSheet("font-weight: bold; color: #aaaaaa;")
        self.asm_view = CodeEditor()
        self.asm_view.setPlaceholderText("Disassembled bytecode assembly will appear here...")
        self.asm_view.setReadOnly(True)
        self.asm_highlighter = PygmentsSyntaxHighlighter(
            self.asm_view.document(), "asm", self.settings["theme"]
        )
        left_layout.addWidget(left_label)
        left_layout.addWidget(self.asm_view)

        # Right Pane: Decompiler CodeEditor + Action Buttons
        right_container = QWidget()
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(6)
        
        right_top_layout = QHBoxLayout()
        right_label = QLabel("Decompiled Python Code (Editable)")
        right_label.setStyleSheet("font-weight: bold; color: #aaaaaa;")
        right_top_layout.addWidget(right_label)
        right_top_layout.addStretch()

        self.run_btn = QPushButton("▶ Run Buffer")
        self.run_btn.setStyleSheet("background-color: #2b7a3e; color: white; font-weight: bold; padding: 6px 12px;")
        self.run_btn.clicked.connect(self.run_buffer_script)
        
        self.save_btn = QPushButton("💾 Save Script")
        self.save_btn.setStyleSheet("background-color: #1e5c8c; color: white; font-weight: bold; padding: 6px 12px;")
        self.save_btn.clicked.connect(self.save_script_file)

        right_top_layout.addWidget(self.run_btn)
        right_top_layout.addWidget(self.save_btn)

        self.code_view = CodeEditor()
        self.code_view.setPlaceholderText("Decompiled Python source will appear here...")
        self.code_view.setReadOnly(False)
        self.code_highlighter = PygmentsSyntaxHighlighter(
            self.code_view.document(), "python", self.settings["theme"]
        )
        
        right_layout.addLayout(right_top_layout)
        right_layout.addWidget(self.code_view)

        splitter.addWidget(left_container)
        splitter.addWidget(right_container)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([675, 675])
        
        main_layout.addWidget(splitter)

        self.apply_global_fonts()
        self.stack.addWidget(self.workspace_widget)

    def apply_global_fonts(self):
        font = QFont(self.settings["font_family"], self.settings["font_size"])
        font.setStyleHint(QFont.Monospace)
        
        QApplication.instance().setFont(font)
        self.code_view.setFont(font)
        self.asm_view.setFont(font)

    def open_settings(self):
        dialog = SettingsDialog(self.settings, self)
        if dialog.exec() == QDialog.Accepted:
            self.settings = dialog.get_settings()
            save_settings(self.settings)

            self.hide_stdlib_checkbox.blockSignals(True)
            self.hide_stdlib_checkbox.setChecked(self.settings["hide_stdlib"])
            self.hide_stdlib_checkbox.blockSignals(False)

            self.apply_global_fonts()
            self.code_highlighter.set_lexer_and_style("python", self.settings["theme"])
            self.asm_highlighter.set_lexer_and_style("asm", self.settings["theme"])
            self.populate_pyc_selector()

    def open_find_dialog(self):
        """Opens the find dialog targeting whichever code view currently has focus."""
        target_editor = self.code_view if self.code_view.hasFocus() else self.asm_view
        dialog = FindDialog(target_editor, self)
        dialog.show()

    def run_buffer_script(self):
        code_content = self.code_view.toPlainText()
        if not code_content.strip():
            QMessageBox.warning(self, "Empty Buffer", "The decompiled code buffer is empty.")
            return

        if not self.extracted_dir:
            QMessageBox.warning(self, "No Workspace", "No active extraction workspace directory found.")
            return

        target_script = self.extracted_dir / "run_buffer.py"
        try:
            target_script.write_text(code_content, encoding="utf-8")
        except OSError as exc:
            QMessageBox.critical(self, "Execution Error", f"Could not write the buffer to disk:\n{exc}")
            return

        interpreter = find_system_python()
        if interpreter is None:
            self._run_buffer_in_process(code_content, target_script)
            return

        try:
            self._launch_in_terminal(interpreter, target_script)
        except Exception as exc:
            QMessageBox.critical(self, "Execution Error", f"Failed to launch terminal:\n{exc}")

    def _run_buffer_in_process(self, code_content: str, target_script: Path):
        self._run_worker = RunBufferWorker(code_content, target_script, self)
        self._run_worker.finished_ok.connect(
            lambda output: QMessageBox.information(self, "Buffer Output", output)
        )
        self._run_worker.start()

    def _launch_in_terminal(self, interpreter: str, target_script: Path):
        system = platform.system().lower()
        script_path = str(target_script.resolve())
        work_dir = str(self.extracted_dir)
        env = clean_subprocess_env()

        if system == "windows":
            subprocess.Popen(["cmd", "/k", interpreter, script_path], cwd=work_dir, env=env)
            return

        if system == "darwin":
            command = (
                f"cd {shlex.quote(work_dir)} && "
                f"{shlex.quote(interpreter)} {shlex.quote(script_path)}; "
                'echo ""; echo "Press Enter to close..."; read'
            )
            escaped = command.replace("\\", "\\\\").replace('"', '\\"')
            subprocess.Popen(
                ["osascript", "-e", f'tell application "Terminal" to do script "{escaped}"'],
                env=env,
            )
            return

        command = (
            f"{shlex.quote(interpreter)} {shlex.quote(script_path)}; "
            'echo ""; echo "Press Enter to close terminal..."; read'
        )
        terminals = [
            ["gnome-terminal", "--", "bash", "-c", command],
            ["konsole", "-e", "bash", "-c", command],
            ["alacritty", "-e", "bash", "-c", command],
            ["xfce4-terminal", "-e", f'bash -c "{command}"'],
            ["xterm", "-hold", "-e", interpreter, script_path],
        ]
        for candidate in terminals:
            try:
                subprocess.Popen(candidate, cwd=work_dir, env=env)
                return
            except FileNotFoundError:
                continue
        raise RuntimeError("Could not find a supported terminal emulator.")

    def save_script_file(self):
        code_content = self.code_view.toPlainText()
        if not code_content.strip():
            QMessageBox.warning(self, "Empty Buffer", "There is no code in the buffer to save.")
            return

        default_name = "decompiled_script.py"
        if self.pyc_selector.currentIndex() != -1:
            current_text = self.pyc_selector.currentText()
            default_name = Path(current_text).stem + ".py"

        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Decompiled Script", default_name, "Python Files (*.py);;All Files (*)"
        )
        if file_path:
            try:
                Path(file_path).write_text(code_content, encoding="utf-8")
                QMessageBox.information(self, "Success", f"Script successfully saved to:\n{file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not save file:\n{str(e)}")

    def select_binary(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open Compiled Binary", "", "All Files (*)"
        )
        if file_path:
            self.selected_binary = Path(file_path)
            self.bin_info_label.setText(f"Target: {self.selected_binary.name}")
            # Defer extraction slightly so the UI renders and doesn't show "Not Responding"
            QTimer.singleShot(50, self.extract_binary)

    def extract_binary(self):
        self.pyc_files.clear()
        if not self.selected_binary:
            return

        self.pyc_selector.setEnabled(False)
        self.asm_view.setPlainText("Extracting selected binary, please wait...")
        self.code_view.setPlainText("")
        self.stack.setCurrentIndex(1)

        work_dir = Path(tempfile.gettempdir()) / f"decompyler-{self.selected_binary.stem}"
        self._extract_worker = ExtractionWorker(self.selected_binary, work_dir, self)
        self._extract_worker.finished_ok.connect(self._on_extraction_finished)
        self._extract_worker.failed.connect(self._on_extraction_failed)
        self._extract_worker.start()

    def _on_extraction_finished(self, extracted_dir, pyc_files, output):
        self.extracted_dir = Path(extracted_dir)
        self.pyc_files = sorted(list(pyc_files), key=lambda p: len(str(p)))

        if not self.pyc_files:
            msg = "Extraction complete, but no .pyc files were found.\n\n" + output
            self.asm_view.setPlainText(msg)
            self.code_view.setPlainText(msg)
            self.stack.setCurrentIndex(1)
            return

        self.stack.setCurrentIndex(1)
        self.populate_pyc_selector()

    def populate_pyc_selector(self):
        if not self.pyc_files or self.extracted_dir is None:
            return

        current = self.pyc_selector.currentData()
        visible_files = []
        for pyc in self.pyc_files:
            module_name = module_top_level(pyc, self.extracted_dir)
            if self.settings.get("hide_stdlib", True) and should_hide_module(module_name):
                continue
            visible_files.append(pyc)

        self.pyc_selector.blockSignals(True)
        self.pyc_selector.clear()
        for pyc in visible_files:
            rel_name = pyc.relative_to(self.extracted_dir)
            self.pyc_selector.addItem(str(rel_name), pyc)

        if not visible_files:
            self.pyc_selector.blockSignals(False)
            self.pyc_selector.setEnabled(False)
            message = (
                "All extracted modules are hidden by the standard-library filter.\n"
                'Uncheck "Hide stdlib" to show them.'
            )
            self.asm_view.setPlainText(message)
            self.code_view.setPlainText(message)
            return

        index = 0
        if current is not None:
            for i in range(self.pyc_selector.count()):
                if Path(self.pyc_selector.itemData(i)) == Path(current):
                    index = i
                    break
        self.pyc_selector.setCurrentIndex(index)
        self.pyc_selector.blockSignals(False)

        self.pyc_selector.setEnabled(True)
        self.process_selected_pyc()

    def toggle_hide_stdlib(self, checked: bool):
        self.settings["hide_stdlib"] = checked
        save_settings(self.settings)
        self.populate_pyc_selector()

    def _on_extraction_failed(self, message):
        self.extracted_dir = None
        self.pyc_files = []
        err_msg = f"Extraction Error:\n{message}"
        self.asm_view.setPlainText(err_msg)
        self.code_view.setPlainText(err_msg)
        self.stack.setCurrentIndex(1)

    def process_selected_pyc(self):
        if self.pyc_selector.currentIndex() == -1:
            return

        pyc_path = self.pyc_selector.currentData()
        if not pyc_path or not pyc_path.exists():
            return

        missing = [
            name for name in ("pycdc", "pycdas")
            if not get_binary_path(name, self.settings).exists()
        ]
        if missing:
            message = (
                "The following decompiler binaries could not be found: "
                f"{', '.join(missing)}.\n\n"
                "Set their paths in Settings or in "
                f"{CONFIG_FILE}."
            )
            self.asm_view.setPlainText(message)
            self.code_view.setPlainText(message)
            QMessageBox.warning(self, "Missing Binaries", message)
            return

        self.asm_view.setPlainText("Disassembling, please wait...")
        self.code_view.setPlainText("Decompiling, please wait...")

        self._decompile_worker = DecompileWorker(pyc_path, self.settings, self)
        self._decompile_worker.finished_ok.connect(self._on_decompile_finished)
        self._decompile_worker.start()

    def _on_decompile_finished(self, pyc_path, asm, code):
        current = self.pyc_selector.currentData()
        if current is None or Path(current) != Path(pyc_path):
            return
        self.asm_view.setPlainText(asm)
        self.code_view.setPlainText(code)
