from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QPushButton
from components.ui.base_components import ModernButton
from components.utils.constants import DARK_MODE

class PreferencesTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        self.style_combo = QComboBox()
        self.style_combo.addItems(["Concise", "Detailed", "Technical"])
        self.depth_combo = QComboBox()
        self.depth_combo.addItems(["Beginner", "Intermediate", "Expert"])
        self.lang_combo = QComboBox()
        self.lang_combo.addItems(["English", "Urdu", "Transliteration"])
        save_btn = ModernButton("Save Preferences")
        save_btn.clicked.connect(self.save_preferences)
        layout.addWidget(QLabel("Answer Style:"))
        layout.addWidget(self.style_combo)
        layout.addWidget(QLabel("Technical Depth:"))
        layout.addWidget(self.depth_combo)
        layout.addWidget(QLabel("Language:"))
        layout.addWidget(self.lang_combo)
        layout.addWidget(save_btn)

    def save_preferences(self):
        # Save preferences logic here
        pass 