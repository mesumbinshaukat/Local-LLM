from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QHBoxLayout, QProgressBar
from PyQt6.QtCore import QTimer
import requests
from components.utils.constants import DARK_MODE, SERVER_URL

class DashboardTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.refresh_dashboard()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh_dashboard)
        self.timer.start(5000)  # Refresh every 5 seconds

    def setup_ui(self):
        self.layout = QVBoxLayout(self)
        self.stats_labels = {}
        for key in ["Documents Ingested", "Repos Cloned", "Tasks Executed", "Web Scrapes", "Pentests"]:
            label = QLabel(f"{key}: ...")
            label.setStyleSheet(f"color: {DARK_MODE['text']}; font-size: 16px;")
            self.layout.addWidget(label)
            self.stats_labels[key] = label
        # Resource usage
        self.ram_label = QLabel("RAM Usage: ...")
        self.cpu_label = QLabel("CPU Usage: ...")
        self.layout.addWidget(self.ram_label)
        self.layout.addWidget(self.cpu_label)
        # Progress bars for resource usage
        self.ram_bar = QProgressBar()
        self.cpu_bar = QProgressBar()
        self.layout.addWidget(self.ram_bar)
        self.layout.addWidget(self.cpu_bar)

    def refresh_dashboard(self):
        try:
            analytics = requests.get(f"{SERVER_URL}/analytics").json()
            self.stats_labels["Documents Ingested"].setText(f"Documents Ingested: {analytics.get('docs', 0)}")
            self.stats_labels["Repos Cloned"].setText(f"Repos Cloned: {analytics.get('repos', 0)}")
            self.stats_labels["Tasks Executed"].setText(f"Tasks Executed: {analytics.get('tasks', 0)}")
            self.stats_labels["Web Scrapes"].setText(f"Web Scrapes: {analytics.get('scrapes', 0)}")
            self.stats_labels["Pentests"].setText(f"Pentests: {analytics.get('pentests', 0)}")
        except Exception:
            for key in self.stats_labels:
                self.stats_labels[key].setText(f"{key}: Error")
        try:
            usage = requests.get(f"{SERVER_URL}/memory/usage").json()
            ram = usage.get('ram', 0)
            cpu = usage.get('cpu', 0)
            self.ram_label.setText(f"RAM Usage: {ram}%")
            self.cpu_label.setText(f"CPU Usage: {cpu}%")
            self.ram_bar.setValue(int(ram))
            self.cpu_bar.setValue(int(cpu))
        except Exception:
            self.ram_label.setText("RAM Usage: Error")
            self.cpu_label.setText("CPU Usage: Error") 