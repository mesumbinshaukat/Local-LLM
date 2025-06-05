import sys
import os
import json
import requests
import time
from datetime import datetime
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QTextEdit, QPushButton, QLabel, 
                            QTabWidget, QLineEdit, QComboBox, QProgressBar,
                            QFrame, QScrollArea, QGridLayout, QFileDialog,
                            QMessageBox, QCheckBox, QInputDialog, QListWidget,
                            QListWidgetItem, QSplitter, QGroupBox, QTabBar)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, QPropertyAnimation, QEasingCurve, QSize, QFileSystemWatcher, QUrl, QMetaObject, Q_ARG
from PyQt6.QtGui import QFont, QPalette, QColor, QLinearGradient, QGradient, QIcon, QTextCharFormat, QTextCursor, QPainter
from PyQt6.QtWebEngineWidgets import QWebEngineView

import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Try to import QtCharts, but make it optional
try:
    from PyQt6.QtCharts import QChart, QChartView, QPieSeries, QPieSlice
    CHARTS_AVAILABLE = True
except ImportError:
    CHARTS_AVAILABLE = False
    logger.warning("QtCharts not available. Charts will be disabled.")

import markdown2
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from collections import defaultdict
import threading
import queue
import importlib

# Check for voice functionality
try:
    import speech_recognition as sr
    STT_AVAILABLE = True
except ImportError:
    STT_AVAILABLE = False
    logger.warning("Speech recognition not available. Install speech_recognition package for voice input.")

try:
    import pyttsx3
    TTS_AVAILABLE = True
except ImportError:
    TTS_AVAILABLE = False
    logger.warning("Text-to-speech not available. Install pyttsx3 package for voice output.")

# Import components
from components.ui.base_components import ModernButton, CategoryCard
from components.utils.workers import ChatWorker, StreamingChatWorker, LogMonitorWorker, ResourceMonitorWorker
from components.utils.constants import DARK_MODE, SERVER_URL, APP_NAME, BRAND, USER_ID
from components.tabs.chat_tab import ChatTab
from components.tabs.knowledge_tab import KnowledgeTab
from components.tabs.admin_tab import AdminTab
from components.tabs.web_tab import WebTab
from components.tabs.code_tab import CodeTab
from components.tabs.automation_tab import AutomationTab
from components.tabs.plugins_tab import PluginsTab
from components.tabs.preferences_tab import PreferencesTab
from components.tabs.dashboard_tab import DashboardTab

class HotReloader:
    def __init__(self, app):
        self.app = app
        self.watcher = QFileSystemWatcher()
        self.watcher.addPath(os.path.abspath(__file__))
        self.watcher.fileChanged.connect(self.reload_ui)
        self.last_modified = os.path.getmtime(__file__)
        
    def reload_ui(self, path):
        """Reload the UI when the file changes."""
        try:
            current_modified = os.path.getmtime(path)
            if current_modified > self.last_modified:
                self.last_modified = current_modified
                logger.info("Reloading UI...")
                
                # Reload the module
                importlib.reload(sys.modules[__name__])
                
                # Recreate the UI
                self.app.close()
                new_app = MeAIApp()
                new_app.show()
                
        except Exception as e:
            logger.error(f"Error reloading UI: {str(e)}")

class MeAIApp(QMainWindow):
    # Add a signal for log updates
    log_update_signal = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.setMinimumSize(1200, 800)
        self.setup_ui()
        self.set_dark_mode(True)
        self.setup_status_bar()
        self.start_resource_monitor()
        
    def setup_ui(self):
        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet(f"""
            QTabWidget::pane {{
                border: 1px solid {DARK_MODE['border']};
                background: {DARK_MODE['background']};
            }}
            QTabBar::tab {{
                background: {DARK_MODE['secondary']};
                color: {DARK_MODE['text']};
                padding: 8px 16px;
                border: 1px solid {DARK_MODE['border']};
                border-bottom: none;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }}
            QTabBar::tab:selected {{
                background: {DARK_MODE['accent']};
                color: {DARK_MODE['foreground']};
            }}
        """)
        
        # Add tabs
        self.dashboard_tab = DashboardTab()
        self.chat_tab = ChatTab()
        self.knowledge_tab = KnowledgeTab()
        self.web_tab = WebTab()
        self.code_tab = CodeTab()
        self.automation_tab = AutomationTab()
        self.plugins_tab = PluginsTab()
        self.preferences_tab = PreferencesTab()
        self.admin_tab = AdminTab()
        
        self.tab_widget.addTab(self.dashboard_tab, "Dashboard")
        self.tab_widget.addTab(self.chat_tab, "Chat")
        self.tab_widget.addTab(self.knowledge_tab, "Knowledge")
        self.tab_widget.addTab(self.web_tab, "Web Search")
        self.tab_widget.addTab(self.code_tab, "Code")
        self.tab_widget.addTab(self.automation_tab, "Automation")
        self.tab_widget.addTab(self.plugins_tab, "Plugins")
        self.tab_widget.addTab(self.preferences_tab, "Preferences")
        self.tab_widget.addTab(self.admin_tab, "Admin")
        
        layout.addWidget(self.tab_widget)
        
    def set_dark_mode(self, enabled):
        if enabled:
            self.setStyleSheet(f"""
                QMainWindow {{
                    background-color: {DARK_MODE['background']};
                }}
                QWidget {{
                    background-color: {DARK_MODE['background']};
                    color: {DARK_MODE['text']};
                }}
            """)
        else:
            self.setStyleSheet("")
            
    def update_log_viewer(self, log_text):
        self.admin_tab.update_log_viewer(log_text)
        
    def update_ui(self):
        self.chat_tab.update_ui()
        self.knowledge_tab.update_ui()
        self.admin_tab.update_ui()
        
    def closeEvent(self, event):
        # Clean up any resources
        self.admin_tab.stop_log_monitoring()
        event.accept()
        
    def setup_status_bar(self):
        self.status_bar = self.statusBar()
        self.status_label = QLabel("Idle")
        self.ram_label = QLabel("RAM: ...")
        self.cpu_label = QLabel("CPU: ...")
        self.status_bar.addWidget(self.status_label)
        self.status_bar.addWidget(self.ram_label)
        self.status_bar.addWidget(self.cpu_label)
        # Connect chat tab status updates
        self.chat_tab.status_changed.connect(self.status_label.setText)

    def start_resource_monitor(self):
        self.resource_monitor = ResourceMonitorWorker(SERVER_URL)
        self.resource_monitor.resource_signal.connect(self.update_resource_usage)
        self.resource_monitor.start()

    def update_resource_usage(self, usage):
        ram = usage.get('ram', 0)
        cpu = usage.get('cpu', 0)
        self.ram_label.setText(f"RAM: {ram}%")
        self.cpu_label.setText(f"CPU: {cpu}%")

def get_user_name():
    try:
        return os.getlogin()
    except:
        return "User"
        
def main():
    app = QApplication(sys.argv)
    window = MeAIApp()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main() 