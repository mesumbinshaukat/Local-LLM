from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QLabel
from PyQt6.QtWebEngineWidgets import QWebEngineView
from components.ui.base_components import ModernButton
from components.utils.constants import DARK_MODE
import requests

class WebTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search DuckDuckGo...")
        self.search_button = ModernButton("Search")
        self.search_button.clicked.connect(self.perform_search)
        search_layout.addWidget(self.search_input)
        search_layout.addWidget(self.search_button)
        self.web_view = QWebEngineView()
        layout.addLayout(search_layout)
        layout.addWidget(self.web_view)

    def perform_search(self):
        query = self.search_input.text().strip()
        if not query:
            return
        url = f"https://duckduckgo.com/?q={query.replace(' ', '+')}"
        self.web_view.setUrl(url) 