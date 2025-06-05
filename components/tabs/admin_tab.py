from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, 
                            QPushButton, QLabel, QTabWidget, QProgressBar)
from PyQt6.QtCore import Qt, pyqtSignal
from components.ui.base_components import ModernButton
from components.utils.workers import LogMonitorWorker
from components.utils.constants import DARK_MODE, SERVER_ERROR_LOG, ACTION_LOG
import requests
import logging
import os

logger = logging.getLogger(__name__)

class AdminTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.log_workers = {}
        self.setup_ui()
        self.start_log_monitoring()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Status section
        status_layout = QHBoxLayout()
        
        self.status_label = QLabel("Server Status: Checking...")
        self.status_label.setStyleSheet(f"color: {DARK_MODE['text']};")
        
        self.restart_button = ModernButton("Restart Server")
        self.restart_button.clicked.connect(self.restart_server)
        
        status_layout.addWidget(self.status_label)
        status_layout.addWidget(self.restart_button)
        
        # Log tabs
        self.log_tabs = QTabWidget()
        self.log_tabs.setStyleSheet(f"""
            QTabWidget::pane {{
                border: 1px solid {DARK_MODE['border']};
                background: {DARK_MODE['secondary']};
            }}
            QTabBar::tab {{
                background: {DARK_MODE['background']};
                color: {DARK_MODE['text']};
                padding: 8px 16px;
                border: 1px solid {DARK_MODE['border']};
            }}
            QTabBar::tab:selected {{
                background: {DARK_MODE['accent']};
            }}
        """)
        
        # Server errors log
        self.error_log = QTextEdit()
        self.error_log.setReadOnly(True)
        self.error_log.setStyleSheet(f"""
            QTextEdit {{
                background-color: {DARK_MODE['background']};
                color: {DARK_MODE['text']};
                border: none;
                padding: 10px;
            }}
        """)
        
        # User actions log
        self.action_log = QTextEdit()
        self.action_log.setReadOnly(True)
        self.action_log.setStyleSheet(f"""
            QTextEdit {{
                background-color: {DARK_MODE['background']};
                color: {DARK_MODE['text']};
                border: none;
                padding: 10px;
            }}
        """)
        
        self.log_tabs.addTab(self.error_log, "Server Errors")
        self.log_tabs.addTab(self.action_log, "User Actions")
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.clear_button = ModernButton("Clear Logs")
        self.clear_button.clicked.connect(self.clear_logs)
        
        self.refresh_button = ModernButton("Refresh")
        self.refresh_button.clicked.connect(self.refresh_logs)
        
        button_layout.addWidget(self.clear_button)
        button_layout.addWidget(self.refresh_button)
        
        # Add widgets to layout
        layout.addLayout(status_layout)
        layout.addWidget(self.log_tabs)
        layout.addLayout(button_layout)
        
    def start_log_monitoring(self):
        # Monitor server errors log
        self.log_workers['error'] = LogMonitorWorker(SERVER_ERROR_LOG)
        self.log_workers['error'].log_signal.connect(
            lambda text: self.error_log.append(text)
        )
        self.log_workers['error'].start()
        
        # Monitor user actions log
        self.log_workers['action'] = LogMonitorWorker(ACTION_LOG)
        self.log_workers['action'].log_signal.connect(
            lambda text: self.action_log.append(text)
        )
        self.log_workers['action'].start()
        
    def stop_log_monitoring(self):
        # Stop all log monitoring workers
        for worker in self.log_workers.values():
            worker.stop()
            worker.wait()
            
    def refresh_logs(self):
        # Clear and reload logs
        self.error_log.clear()
        self.action_log.clear()
        
        try:
            if os.path.exists(SERVER_ERROR_LOG):
                with open(SERVER_ERROR_LOG, 'r') as f:
                    self.error_log.setText(f.read())
                    
            if os.path.exists(ACTION_LOG):
                with open(ACTION_LOG, 'r') as f:
                    self.action_log.setText(f.read())
                    
        except Exception as e:
            logger.error(f"Error refreshing logs: {str(e)}")
            
    def clear_logs(self):
        try:
            if os.path.exists(SERVER_ERROR_LOG):
                open(SERVER_ERROR_LOG, 'w').close()
            if os.path.exists(ACTION_LOG):
                open(ACTION_LOG, 'w').close()
                
            self.error_log.clear()
            self.action_log.clear()
            
        except Exception as e:
            logger.error(f"Error clearing logs: {str(e)}")
            
    def restart_server(self):
        try:
            response = requests.post("http://localhost:8000/restart")
            if response.status_code == 200:
                self.status_label.setText("Server Status: Restarting...")
            else:
                raise Exception(response.text)
                
        except Exception as e:
            logger.error(f"Error restarting server: {str(e)}")
            self.status_label.setText("Server Status: Error")
            
    def closeEvent(self, event):
        # Stop log monitoring workers
        self.stop_log_monitoring()
        super().closeEvent(event) 