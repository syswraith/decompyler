from PySide6.QtWidgets import (
    QDialog, QFormLayout, QComboBox, QFontComboBox, QSpinBox, QDialogButtonBox,
    QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QCheckBox,
    QFileDialog, QWidget
)
from PySide6.QtGui import QFont, QTextCursor
from PySide6.QtGui import QTextDocument

class SettingsDialog(QDialog):
    """Dialog for editing theme, font family, and font size."""
    def __init__(self, current_settings: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Preferences")
        self.resize(520, 360)

        layout = QFormLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        self.theme_combo = QComboBox()
        available_styles = ["monokai", "dracula", "solarized-dark", "vim", "default", "paraiso-dark", "nord"]
        self.theme_combo.addItems(available_styles)
        if current_settings["theme"] in available_styles:
            self.theme_combo.setCurrentText(current_settings["theme"])
        layout.addRow("Syntax Theme:", self.theme_combo)

        self.font_combo = QFontComboBox()
        self.font_combo.setFontFilters(QFontComboBox.MonospacedFonts)
        self.font_combo.setCurrentFont(QFont(current_settings["font_family"]))
        layout.addRow("Font Family:", self.font_combo)

        self.size_spin = QSpinBox()
        self.size_spin.setRange(8, 30)
        self.size_spin.setValue(current_settings["font_size"])
        layout.addRow("Font Size:", self.size_spin)

        self.hide_stdlib_checkbox = QCheckBox("Hide standard library modules")
        self.hide_stdlib_checkbox.setChecked(current_settings.get("hide_stdlib", True))
        layout.addRow("Module Filter:", self.hide_stdlib_checkbox)

        self.pycdc_edit = QLineEdit(current_settings.get("pycdc_path", ""))
        layout.addRow("pycdc Binary:", self._make_path_row(self.pycdc_edit))

        self.pycdas_edit = QLineEdit(current_settings.get("pycdas_path", ""))
        layout.addRow("pycdas Binary:", self._make_path_row(self.pycdas_edit))

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def _make_path_row(self, line_edit: QLineEdit) -> QWidget:
        container = QWidget()
        row = QHBoxLayout(container)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(6)

        browse_btn = QPushButton("Browse…")
        browse_btn.clicked.connect(lambda: self._browse_for_binary(line_edit))

        row.addWidget(line_edit)
        row.addWidget(browse_btn)
        return container

    def _browse_for_binary(self, line_edit: QLineEdit):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Binary", line_edit.text(), "All Files (*)"
        )
        if file_path:
            line_edit.setText(file_path)

    def get_settings(self) -> dict:
        return {
            "theme": self.theme_combo.currentText(),
            "font_family": self.font_combo.currentFont().family(),
            "font_size": self.size_spin.value(),
            "hide_stdlib": self.hide_stdlib_checkbox.isChecked(),
            "pycdc_path": self.pycdc_edit.text().strip(),
            "pycdas_path": self.pycdas_edit.text().strip(),
        }


class FindDialog(QDialog):
    """Find dialog for searching text in the editor (find only, no replace)."""
    def __init__(self, editor, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Find")
        self.resize(380, 130)
        self.editor = editor

        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

        h_layout = QHBoxLayout()
        h_layout.addWidget(QLabel("Find what:"))
        self.search_input = QLineEdit()
        self.search_input.returnPressed.connect(self.find_next)
        h_layout.addWidget(self.search_input)
        layout.addLayout(h_layout)

        self.case_checkbox = QCheckBox("Case sensitive")
        layout.addWidget(self.case_checkbox)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        self.find_prev_btn = QPushButton("Find Previous")
        self.find_prev_btn.clicked.connect(self.find_previous)
        btn_layout.addWidget(self.find_prev_btn)

        self.find_next_btn = QPushButton("Find Next")
        self.find_next_btn.clicked.connect(self.find_next)
        btn_layout.addWidget(self.find_next_btn)

        layout.addLayout(btn_layout)

    def find_next(self):
        text = self.search_input.text()
        if not text:
            return
        flags = QTextDocument.FindFlag(0)
        if self.case_checkbox.isChecked():
            flags |= QTextDocument.FindCaseSensitively

        found = self.editor.find(text, flags)
        if not found:
            cursor = self.editor.textCursor()
            cursor.movePosition(QTextCursor.Start)
            self.editor.setTextCursor(cursor)
            self.editor.find(text, flags)

    def find_previous(self):
        text = self.search_input.text()
        if not text:
            return
        flags = QTextDocument.FindBackward
        if self.case_checkbox.isChecked():
            flags |= QTextDocument.FindCaseSensitively

        found = self.editor.find(text, flags)
        if not found:
            cursor = self.editor.textCursor()
            cursor.movePosition(QTextCursor.End)
            self.editor.setTextCursor(cursor)
            self.editor.find(text, flags)
