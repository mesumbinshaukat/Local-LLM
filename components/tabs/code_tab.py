from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QLabel
from components.ui.base_components import ModernButton
from components.utils.constants import DARK_MODE
import subprocess

class CodeTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        self.code_input = QTextEdit()
        self.code_input.setPlaceholderText("Enter Python code to execute...")
        self.run_button = ModernButton("Run")
        self.run_button.clicked.connect(self.run_code)
        self.output_display = QTextEdit()
        self.output_display.setReadOnly(True)
        layout.addWidget(QLabel("Python Code Execution"))
        layout.addWidget(self.code_input)
        layout.addWidget(self.run_button)
        layout.addWidget(QLabel("Output:"))
        layout.addWidget(self.output_display)

    def run_code(self):
        code = self.code_input.toPlainText()
        try:
            result = subprocess.run(["python", "-c", code], capture_output=True, text=True, timeout=10)
            output = result.stdout + ("\n" + result.stderr if result.stderr else "")
        except Exception as e:
            output = str(e)
        self.output_display.setText(output) 