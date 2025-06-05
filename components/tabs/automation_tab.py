from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QLabel
from components.ui.base_components import ModernButton
from components.utils.constants import DARK_MODE
import subprocess

class AutomationTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        self.cmd_input = QTextEdit()
        self.cmd_input.setPlaceholderText("Enter shell command(s) to run...")
        self.run_button = ModernButton("Run")
        self.run_button.clicked.connect(self.run_command)
        self.output_display = QTextEdit()
        self.output_display.setReadOnly(True)
        layout.addWidget(QLabel("Task Automation"))
        layout.addWidget(self.cmd_input)
        layout.addWidget(self.run_button)
        layout.addWidget(QLabel("Output:"))
        layout.addWidget(self.output_display)

    def run_command(self):
        cmd = self.cmd_input.toPlainText()
        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=20)
            output = result.stdout + ("\n" + result.stderr if result.stderr else "")
        except Exception as e:
            output = str(e)
        self.output_display.setText(output) 