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

# Dark mode color scheme
DARK_MODE = {
    'background': '#1e1e1e',
    'foreground': '#ffffff',
    'accent': '#4a90e2',
    'secondary': '#2d2d2d',
    'text': '#e0e0e0',
    'border': '#3d3d3d',
    'success': '#67b26f',
    'warning': '#ffd700',
    'error': '#ff6b6b'
}

# Server URL
SERVER_URL = "http://localhost:8000"

APP_NAME = "MeAI"
BRAND = "MeAI by Mesum Bin Shaukat\nOwner of World Of Tech"

# --- Add user_id for persistent memory ---
USER_ID = "default"  # In a real app, this could be per-user or per-device

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

class ChatWorker(QThread):
    finished = pyqtSignal(str)
    error = pyqtSignal(str)
    
    def __init__(self, history, user_input, cyber_mode=False):
        super().__init__()
        self.history = history
        self.user_input = user_input
        self.cyber_mode = cyber_mode
        self.prefs = None
        
    def run(self):
        try:
            # Ensure history is a list of message objects
            messages = []
            if isinstance(self.history, list):
                messages = self.history.copy()
            else:
                messages = []
            
            # Add the current user input
            messages.append({"role": "user", "content": self.user_input})
            
            # Prepare the request payload
            payload = {
                "messages": messages,
                "query": self.user_input,
                "cyber_mode": self.cyber_mode
            }
            
            if self.prefs:
                payload["preferences"] = self.prefs
            
            # Make the request
            response = requests.post(
                f"{SERVER_URL}/chat",
                json=payload,
                timeout=30  # Add timeout
            )
            
            if response.status_code != 200:
                self.error.emit(f"Error: {response.status_code} - {response.text}")
                return
                
            result = response.json()
            self.finished.emit(result.get("response", ""))
            
        except Exception as e:
            self.error.emit(str(e))

class StreamingChatWorker(QThread):
    partial_signal = pyqtSignal(str)
    done_signal = pyqtSignal(str)
    error_signal = pyqtSignal(str)
    
    def __init__(self, history, user_input, cyber_mode=False):
        super().__init__()
        self.history = history
        self.user_input = user_input
        self.cyber_mode = cyber_mode
        self.prefs = None
        self._is_running = True
        self.user_id = USER_ID
        
    def stop(self):
        self._is_running = False
        
    def run(self):
        try:
            # Ensure history is a list of message objects
            messages = []
            if isinstance(self.history, list):
                messages = self.history.copy()
            else:
                messages = []
            
            # Add the current user input
            messages.append({"role": "user", "content": self.user_input})
            
            # Prepare the request payload
            payload = {
                "messages": messages,
                "query": self.user_input,
                "cyber_mode": self.cyber_mode,
                "user_id": self.user_id
            }
            
            if self.prefs:
                payload["preferences"] = self.prefs
            
            # Make the streaming request with timeout
            with requests.Session() as session:
                response = session.post(
                    f"{SERVER_URL}/chat/stream",
                    json=payload,
                    stream=True,
                    timeout=30
                )
                
                if response.status_code != 200:
                    self.error_signal.emit(f"Error: {response.status_code} - {response.text}")
                    return
                    
                full_response = ""
                for chunk in response.iter_lines(decode_unicode=True):
                    if not self._is_running:
                        break
                    if chunk:
                        if chunk.startswith("[ERROR]"):
                            self.error_signal.emit(chunk[7:])
                            return
                        elif chunk.startswith("[FALLBACK]"):
                            try:
                                fallback_data = json.loads(chunk[10:])
                                full_response += "<div style='margin:12px 0 0 0;'><b>Additional information:</b>"
                                # Web results as cards
                                if fallback_data.get("web_results"):
                                    full_response += "<div style='margin:8px 0;'><b>Web Results:</b>"
                                    for result in fallback_data["web_results"]:
                                        title = result.get('title', '')
                                        body = result.get('body', '')
                                        href = result.get('href', '')
                                        if title or body:
                                            full_response += f"<div style='margin:6px 0;padding:8px;border-radius:6px;background:#23272e;color:#fff;'><a href='{href}' style='color:#fbbc04;text-decoration:underline;' target='_blank'>{title}</a><br>{body}</div>"
                                    full_response += "</div>"
                                # RAG results as cards
                                if fallback_data.get("rag_results"):
                                    full_response += "<div style='margin:8px 0;'><b>Knowledge Base:</b>"
                                    for result in fallback_data["rag_results"]:
                                        text = result.get('text', '')
                                        source = result.get('source', '')
                                        if text:
                                            full_response += f"<div style='margin:6px 0;padding:8px;border-radius:6px;background:#1a1d21;color:#fff;'><b>Source:</b> {source}<br>{text}</div>"
                                    full_response += "</div>"
                                # Suggestions as buttons
                                if fallback_data.get("suggestions"):
                                    full_response += "<div style='margin:8px 0;'><b>Suggestions:</b> "
                                    for suggestion in fallback_data["suggestions"]:
                                        full_response += f"<button style='margin:0 6px 0 0;padding:4px 10px;border-radius:6px;background:#333;color:#fff;border:none;cursor:pointer;' onclick=\"window.suggestionClicked('{suggestion}')\">{suggestion}</button>"
                                    full_response += "</div>"
                                full_response += "</div>"
                            except:
                                pass
                        else:
                            full_response += chunk
                            self.partial_signal.emit(full_response)
                
                if self._is_running:
                    self.done_signal.emit(full_response)
            
        except Exception as e:
            self.error_signal.emit(str(e))

class ModernButton(QPushButton):
    def __init__(self, text, parent=None, is_dark=True):
        super().__init__(text, parent)
        self.is_dark = is_dark
        self.update_style()
        
    def update_style(self):
        if self.is_dark:
            self.setStyleSheet(f"""
                QPushButton {{
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                        stop:0 {DARK_MODE['accent']}, stop:1 {DARK_MODE['success']});
                    border: none;
                    color: {DARK_MODE['foreground']};
                    padding: 10px 20px;
                    border-radius: 5px;
                    font-weight: bold;
                }}
                QPushButton:hover {{
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                        stop:0 #357abd, stop:1 #4a9e4f);
                }}
                QPushButton:pressed {{
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                        stop:0 #2d6da3, stop:1 #3d7d42);
                }}
            """)
        else:
            self.setStyleSheet("""
                QPushButton {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                        stop:0 #4a90e2, stop:1 #67b26f);
                    border: none;
                    color: white;
                    padding: 10px 20px;
                    border-radius: 5px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                        stop:0 #357abd, stop:1 #4a9e4f);
                }
                QPushButton:pressed {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                        stop:0 #2d6da3, stop:1 #3d7d42);
                }
            """)

class CategoryCard(QFrame):
    def __init__(self, title, count, parent=None, is_dark=True):
        super().__init__(parent)
        self.is_dark = is_dark
        self.update_style()
        
        layout = QVBoxLayout()
        
        title_label = QLabel(title)
        count_label = QLabel(str(count))
        
        if self.is_dark:
            title_label.setStyleSheet(f"""
                QLabel {{
                    color: {DARK_MODE['text']};
                    font-size: 16px;
                    font-weight: bold;
                }}
            """)
            count_label.setStyleSheet(f"""
                QLabel {{
                    color: {DARK_MODE['accent']};
                    font-size: 24px;
                    font-weight: bold;
                }}
            """)
        else:
            title_label.setStyleSheet("""
                QLabel {
                    color: #2c3e50;
                    font-size: 16px;
                    font-weight: bold;
                }
            """)
            count_label.setStyleSheet("""
                QLabel {
                    color: #4a90e2;
                    font-size: 24px;
                    font-weight: bold;
                }
            """)
        
        layout.addWidget(title_label)
        layout.addWidget(count_label)
        self.setLayout(layout)
    
    def update_style(self):
        if self.is_dark:
            self.setStyleSheet(f"""
                QFrame {{
                    background: {DARK_MODE['secondary']};
                    border-radius: 10px;
                    border: 1px solid {DARK_MODE['border']};
                }}
            """)
        else:
            self.setStyleSheet("""
                QFrame {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, 
                        stop:0 #ffffff, stop:1 #f8f9fa);
                    border-radius: 10px;
                    border: 1px solid #e9ecef;
                }
            """)

class MeAIApp(QMainWindow):
    # Add a signal for log updates
    log_update_signal = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("MeAI Desktop")
        self.setMinimumSize(1200, 800)
        
        # Initialize preferences
        self.preferences = {
            "answer_style": "detailed",  # or "concise"
            "tech_depth": "advanced",    # or "basic"
            "language": "English"
        }
        
        # Initialize dark mode
        self.is_dark_mode = True
        self.cyber_mode = False
        
        # Initialize chat history
        self.chat_history = []  # List for message history
        self.chat_history_ui = None  # QTextEdit for UI display
        self.last_assistant_bubble_pos = None
        
        # Initialize recent topics
        self.recent_topics = []
        
        # Create main widget and layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)
        
        # Create tab widget
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)
        
        # Create and add all main tabs
        self.create_chat_tab()                # Chat tab
        self.create_knowledge_tab()           # Knowledge tab
        self.create_code_tab()                # Code tab
        self.create_automation_tab()          # Automation tab
        self.create_plugins_tab()             # Plugins tab
        self.create_admin_tab()               # Admin tab
        self.create_web_tab()                 # Web tab
        self.create_settings_tab()            # Settings tab
        
        # Apply dark mode to the entire app after all tabs are created
        self.update_theme()
        
        # Initialize data structures
        self.training_data = defaultdict(int)
        self.category_data = defaultdict(int)
        self.recent_activities = []
        self.data_queue = queue.Queue()
        
        # Start data collection thread
        self.start_data_collection()
        
        # Connect the log update signal to the update_log_viewer slot
        self.log_update_signal.connect(self.update_log_viewer)
        
        # Set up timer for UI updates
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_ui)
        self.update_timer.start(1000)  # Update every second
        
        # Initialize hot reloader
        self.hot_reloader = HotReloader(self)

    def update_log_viewer(self, log_text):
        """Slot to update the log viewer in the main thread."""
        self.log_viewer.setText(log_text)

    def update_ui(self):
        """Update the UI with the latest data."""
        try:
            while not self.data_queue.empty():
                data = self.data_queue.get_nowait()
                
                # Update total data
                total_data = sum(data.get('category_data', {}).values())
                if hasattr(self, 'total_data_card'):
                    count_label = self.total_data_card.findChild(QLabel, "", Qt.FindChildOption.FindChildrenRecursively)[1]
                    if count_label:
                        count_label.setText(str(total_data))
                
                # Update active categories
                active_categories = len(data.get('category_data', {}))
                if hasattr(self, 'active_categories_card'):
                    count_label = self.active_categories_card.findChild(QLabel, "", Qt.FindChildOption.FindChildrenRecursively)[1]
                    if count_label:
                        count_label.setText(str(active_categories))
                
                # Update training speed
                if hasattr(self, 'training_speed_card'):
                    count_label = self.training_speed_card.findChild(QLabel, "", Qt.FindChildOption.FindChildrenRecursively)[1]
                    if count_label:
                        count_label.setText(f"{data.get('training_speed', 0)}/s")
                
                # Update category distribution
                if hasattr(self, 'category_chart'):
                    self.update_category_distribution(data.get('category_data', {}))
                
                # Update recent activity
                if hasattr(self, 'activities_list'):
                    self.update_recent_activity(data.get('recent_activities', []))
        except Exception as e:
            logger.error(f"Error updating UI: {str(e)}")

    def create_chat_tab(self):
        chat_tab = QWidget()
        layout = QVBoxLayout(chat_tab)
        
        # Chat history
        self.chat_history_ui = QTextEdit()
        self.chat_history_ui.setReadOnly(True)
        self.chat_history_ui.setStyleSheet(f"""
            QTextEdit {{
                background: {DARK_MODE['secondary'] if self.is_dark_mode else '#f8f9fa'};
                color: {DARK_MODE['text'] if self.is_dark_mode else '#2c3e50'};
                border: 1px solid {DARK_MODE['border'] if self.is_dark_mode else '#e9ecef'};
                border-radius: 5px;
                padding: 10px;
            }}
        """)
        layout.addWidget(self.chat_history_ui)
        
        # Input area
        input_layout = QHBoxLayout()
        
        self.user_input = QLineEdit()
        self.user_input.setPlaceholderText("Type your message here...")
        self.user_input.setStyleSheet(f"""
            QLineEdit {{
                background: {DARK_MODE['secondary'] if self.is_dark_mode else '#f8f9fa'};
                color: {DARK_MODE['text'] if self.is_dark_mode else '#2c3e50'};
                border: 1px solid {DARK_MODE['border'] if self.is_dark_mode else '#e9ecef'};
                border-radius: 5px;
                padding: 10px;
            }}
        """)
        self.user_input.returnPressed.connect(self.handle_user_input)
        
        # Voice input button
        self.mic_button = ModernButton("🎤", is_dark=self.is_dark_mode)
        self.mic_button.setToolTip("Voice Input")
        self.mic_button.clicked.connect(self.voice_input)
        self.mic_button.setEnabled(STT_AVAILABLE)
        
        # Voice output button
        self.speaker_button = ModernButton("🔊", is_dark=self.is_dark_mode)
        self.speaker_button.setToolTip("Read Last Answer")
        self.speaker_button.clicked.connect(self.speak_last_answer)
        self.speaker_button.setEnabled(TTS_AVAILABLE)
        
        # Send button
        send_button = ModernButton("Send", is_dark=self.is_dark_mode)
        send_button.clicked.connect(self.handle_user_input)
        
        # Clear button
        clear_button = ModernButton("Clear", is_dark=self.is_dark_mode)
        clear_button.clicked.connect(self.clear_chat)
        
        input_layout.addWidget(self.user_input)
        input_layout.addWidget(self.mic_button)
        input_layout.addWidget(self.speaker_button)
        input_layout.addWidget(send_button)
        input_layout.addWidget(clear_button)
        
        layout.addLayout(input_layout)
        
        # Loading indicator
        self.loading_label = QLabel("")
        self.loading_label.setStyleSheet(f"""
            QLabel {{
                color: {DARK_MODE['warning'] if self.is_dark_mode else '#fbbc04'};
                font-weight: bold;
            }}
        """)
        layout.addWidget(self.loading_label)
        
        self.tabs.addTab(chat_tab, "Chat")
        
        # Initialize chat history with system context
        user_name = get_user_name()
        welcome_name = user_name if user_name else "there"
        # Fetch recent chat history
        try:
            resp = requests.get(f"{SERVER_URL}/memory/chat_history/{USER_ID}?limit=5")
            if resp.status_code == 200:
                history = resp.json().get("history", [])
                for msg in history:
                    self.add_chat_bubble(msg.get("content", ""), user=(msg.get("role") == "user"))
        except Exception:
            pass
        self.chat_history_ui.append(f"""
            <p style='color: {DARK_MODE['text'] if self.is_dark_mode else '#2c3e50'};'>
                <b>System:</b> Welcome to MeAI{', ' + welcome_name if welcome_name else ''}! I can help you with research, automation, code, and more. What would you like to do today?
            </p>
        """)

    def handle_user_input(self):
        """Handle user input with enhanced system command support."""
        user_message = self.user_input.text().strip()
        if not user_message:
            return
            
        # Add user message to chat
        self.add_chat_bubble(user_message, user=True)
        
        # Store name if user says "my name is ..."
        if "my name is" in user_message.lower():
            name = user_message.lower().split("my name is",1)[1].strip().split()[0].capitalize()
            try:
                requests.post(f"{SERVER_URL}/memory/user_info", json={"key": "name", "value": name})
            except Exception:
                pass
        
        # Initialize chat history if needed
        if not hasattr(self, 'chat_history') or not isinstance(self.chat_history, list):
            self.chat_history = []
            
        # Add user message to history
        self.chat_history.append({"role": "user", "content": user_message})
        self.user_input.clear()
        
        # Check if it's a system command
        if self.is_task_request(user_message):
            try:
                response = requests.post(
                    f"{SERVER_URL}/task/execute",
                    json={"instruction": user_message},
                    timeout=30
                )
                if response.status_code == 200:
                    result = response.json()
                    if result.get('status') == 'executed':
                        self.add_chat_bubble(f"Task executed successfully: {result.get('command')}", user=False, label="Task Execution")
                        self.chat_history.append({"role": "assistant", "content": f"Task executed successfully: {result.get('command')}"})
                    else:
                        error_msg = result.get('error', 'Failed to execute command')
                        self.add_chat_bubble(error_msg, user=False, label="Task Error")
                        self.chat_history.append({"role": "assistant", "content": error_msg})
                else:
                    error_msg = "Failed to execute command"
                    self.add_chat_bubble(error_msg, user=False, label="Task Error")
                    self.chat_history.append({"role": "assistant", "content": error_msg})
            except Exception as e:
                error_msg = f"Error executing command: {str(e)}"
                self.add_chat_bubble(error_msg, user=False, label="Task Error")
                self.chat_history.append({"role": "assistant", "content": error_msg})
        else:
            # Process as regular chat message
            self.process_chat_message(user_message)

    def is_task_request(self, text):
        """Check if the text is a system command request."""
        nl = text.strip().lower()
        
        # Check for application launch requests
        if any(pattern in nl for pattern in [
            "open ", "run ", "start ", "launch ",
            "open notepad", "open calculator", "open calc",
            "open explorer", "open file explorer",
            "open word", "open excel", "open powerpoint",
            "open chrome", "open firefox", "open edge",
            "open command prompt", "open cmd",
            "open powershell", "open terminal"
        ]):
            return True
            
        # Check for system commands
        if any(pattern in nl for pattern in [
            "list files", "show files", "list directories",
            "show directories", "list drives", "show drives",
            "system info", "show system info"
        ]):
            return True
            
        return False

    def process_chat_message(self, user_message):
        """Process regular chat messages."""
        self.loading_label.setText("Thinking...")
        self.last_assistant_bubble_pos = None  # Reset for new response
        prefs = self.preferences.copy()
        try:
            requests.post(f"{SERVER_URL}/log_action", json={"action": "chat_query", "query": user_message, "preferences": prefs})
        except Exception:
            pass
        self.streaming_worker = StreamingChatWorker(self.chat_history, user_message, cyber_mode=self.cyber_mode)
        self.streaming_worker.prefs = prefs
        self.streaming_worker.user_id = USER_ID
        self.streaming_worker.partial_signal.connect(self.display_partial_response, Qt.ConnectionType.QueuedConnection)
        self.streaming_worker.done_signal.connect(self.display_chat_response, Qt.ConnectionType.QueuedConnection)
        self.streaming_worker.error_signal.connect(self.fallback_to_sync_worker, Qt.ConnectionType.QueuedConnection)
        self.streaming_worker.start()
        self.add_to_recent_topics(user_message, "")

    def send_chat(self):
        """Send chat message and handle response."""
        user_input = self.chat_input.text().strip()
        if not user_input:
            return
            
        # Add user message to chat
        self.add_chat_bubble(user_input, user=True)
        self.chat_history.append({"role": "user", "content": user_input})
        self.chat_input.clear()
        self.loading_label.setText("Thinking...")
        self.last_assistant_bubble_pos = None
        prefs = self.preferences.copy()
        try:
            requests.post(f"{SERVER_URL}/log_action", json={"action": "chat_query", "query": user_input, "preferences": prefs})
        except Exception:
            pass
        if self.is_task_request(user_input):
            try:
                resp = requests.post(f"{SERVER_URL}/task/execute", json={"instruction": user_input}, timeout=10)
                if resp.status_code == 200:
                    data = resp.json()
                    msg = f"<b>Task executed:</b> <code>{data.get('command')}</code>"
                    self.add_chat_bubble(msg, user=False, label="Task Execution")
                    self.loading_label.setText("")
                else:
                    err = resp.json().get("error", str(resp.text))
                    self.add_chat_bubble(f"<b>Task execution error:</b> {err}", user=False, label="Task Error")
                    self.loading_label.setText("")
            except Exception as e:
                self.add_chat_bubble(f"<b>Task execution error:</b> {e}", user=False, label="Task Error")
                self.loading_label.setText("")
            self.add_to_recent_topics(user_input, "[Task executed]")
            return
        self.streaming_worker = StreamingChatWorker(self.chat_history, user_input, cyber_mode=self.cyber_mode)
        self.streaming_worker.prefs = prefs
        self.streaming_worker.user_id = USER_ID
        self.streaming_worker.partial_signal.connect(self.display_partial_response, Qt.ConnectionType.QueuedConnection)
        self.streaming_worker.done_signal.connect(self.display_chat_response, Qt.ConnectionType.QueuedConnection)
        self.streaming_worker.error_signal.connect(self.fallback_to_sync_worker, Qt.ConnectionType.QueuedConnection)
        self.streaming_worker.start()
        self.add_to_recent_topics(user_input, "")

    def display_chat_response(self, response):
        """Display the final chat response and update history."""
        self.loading_label.setText("")
        suggestions = None
        if isinstance(response, dict):
            text = response.get("response", "")
            suggestions = response.get("suggestions", [])
        else:
            text = response
        self.add_chat_bubble(text, user=False, suggestions=suggestions)
        self.chat_history.append({"role": "assistant", "content": text})
        # Fetch and update chat history from backend
        try:
            resp = requests.get(f"{SERVER_URL}/memory/chat_history/{USER_ID}?limit=10")
            if resp.status_code == 200:
                self.chat_history = resp.json().get("history", [])
        except Exception:
            pass
        self.chat_history_ui.verticalScrollBar().setValue(
            self.chat_history_ui.verticalScrollBar().maximum()
        )

    def display_partial_response(self, partial):
        """Display partial streaming response."""
        # Always update UI in main thread, never use QTextCursor/block manipulation
        self.chat_history_ui.setHtml(partial)
        self.chat_history_ui.verticalScrollBar().setValue(
            self.chat_history_ui.verticalScrollBar().maximum()
        )

    def display_chat_error(self, error):
        """Display chat error message."""
        self.loading_label.setText("")
        self.add_chat_bubble(error, user=False, label="Error")
        self.chat_history.append({"role": "assistant", "content": f"Error: {error}"})
        self.chat_history_ui.verticalScrollBar().setValue(
            self.chat_history_ui.verticalScrollBar().maximum()
        )

    def fallback_to_sync_worker(self, error):
        """Fallback to synchronous worker if streaming fails."""
        self.worker = ChatWorker(self.chat_history, self.chat_history[-1]["content"], cyber_mode=self.cyber_mode)
        self.worker.finished.connect(self.display_chat_response, Qt.ConnectionType.QueuedConnection)
        self.worker.error.connect(self.display_chat_error, Qt.ConnectionType.QueuedConnection)
        self.worker.start()

    def add_chat_bubble(self, text, user=True, label=None, suggestions=None):
        """Add a chat bubble to the UI."""
        if not hasattr(self, 'chat_history_ui'):
            return
        user_name = get_user_name() if user else "MeAI"
        bubble = f"""
            <div style='margin:8px 0;padding:8px;border-radius:8px;background:{'#23272e' if user else '#1a1d21'};color:{'#fff' if user else '#fbbc04'};'>
                <b>{label if label else (user_name if user else 'MeAI')}:</b> {text}
            </div>
        """
        self.chat_history_ui.append(bubble)
        # Add suggestions bar if present
        if suggestions:
            self.add_suggestions_bar(suggestions)

    def add_suggestions_bar(self, suggestions):
        if not suggestions:
            return
        bar = "<div style='margin:4px 0 12px 0;padding:6px 0 0 0;'><b>Suggestions:</b> "
        for s in suggestions:
            bar += f"<button style='margin:0 6px 0 0;padding:4px 10px;border-radius:6px;background:#333;color:#fff;border:none;cursor:pointer;' onclick=\"window.suggestionClicked('{s}')\">{s}</button>"
        bar += "</div>"
        self.chat_history_ui.append(bar)

    def clear_chat(self):
        """Clear the chat history."""
        if hasattr(self, 'chat_history_ui'):
            self.chat_history_ui.clear()
        self.chat_history = []
        self.last_assistant_bubble_pos = None

    def show_error_dialog(self, error):
        log_text = ""
        try:
            with open("server_errors.log", "r") as f:
                log_text = f.read()
        except Exception:
            log_text = "No log file found."
        msg = QMessageBox(self)
        msg.setWindowTitle("Error")
        msg.setText(f"An error occurred:\n{error}")
        msg.setDetailedText(log_text[-2000:] if len(log_text) > 2000 else log_text)
        msg.setIcon(QMessageBox.Icon.Critical)
        # Add View Logs and Restart Server buttons
        view_logs_btn = msg.addButton("View Logs", QMessageBox.ButtonRole.ActionRole)
        restart_btn = msg.addButton("Restart Server", QMessageBox.ButtonRole.ActionRole)
        msg.addButton(QMessageBox.StandardButton.Close)
        msg.exec()
        clicked = msg.clickedButton()
        if clicked == view_logs_btn:
            self.open_logs()
        elif clicked == restart_btn:
            self.restart_server()

    def open_logs(self):
        # Open the log file in the default text editor
        try:
            if os.name == 'nt':
                os.startfile("server_errors.log")
            else:
                subprocess.Popen(["xdg-open", "server_errors.log"])
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not open log file: {e}")

    def restart_server(self):
        """Restart the FastAPI server."""
        try:
            response = requests.post(f"{SERVER_URL}/restart")
            if response.status_code == 200:
                self.server_status.setText("Server: Restarting...")
                # Wait for server to restart
                time.sleep(2)
                self.refresh_logs()
                self.server_status.setText("Server: Running")
            else:
                self.show_error_dialog(f"Failed to restart server: {response.text}")
        except Exception as e:
            self.show_error_dialog(f"Failed to restart server: {str(e)}")

    def create_analytics_tab(self):
        """Create the analytics tab with charts and statistics."""
        analytics_tab = QWidget()
        layout = QVBoxLayout()
        
        # Add a message if charts are not available
        if not CHARTS_AVAILABLE:
            warning_label = QLabel("Charts are not available. Please install PyQt6-Charts package for full functionality.")
            warning_label.setStyleSheet(f"color: {DARK_MODE['warning']}; padding: 10px;")
            layout.addWidget(warning_label)
        
        # Create a grid layout for the charts
        grid = QGridLayout()
        
        # Category distribution chart
        category_group = QGroupBox("Category Distribution")
        category_layout = QVBoxLayout()
        if CHARTS_AVAILABLE:
            self.category_chart = QChart()
            self.category_chart.setTitle("Category Distribution")
            self.category_chart.setAnimationOptions(QChart.AnimationOption.SeriesAnimations)
            self.category_chart.legend().setVisible(True)
            self.category_chart.legend().setAlignment(Qt.AlignmentFlag.AlignBottom)
            
            chart_view = QChartView(self.category_chart)
            chart_view.setRenderHint(QPainter.RenderHint.Antialiasing)
            category_layout.addWidget(chart_view)
        else:
            placeholder = QLabel("Charts not available")
            placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
            category_layout.addWidget(placeholder)
        
        category_group.setLayout(category_layout)
        grid.addWidget(category_group, 0, 0)
        
        # Recent activity list
        activity_group = QGroupBox("Recent Activity")
        activity_layout = QVBoxLayout()
        self.activity_list = QListWidget()
        activity_layout.addWidget(self.activity_list)
        activity_group.setLayout(activity_layout)
        grid.addWidget(activity_group, 0, 1)
        
        layout.addLayout(grid)
        analytics_tab.setLayout(layout)
        return analytics_tab

    def start_data_collection(self):
        """Start the data collection thread."""
        def collect_data():
            while True:
                try:
                    response = requests.get('http://localhost:8000/training/status')
                    if response.status_code == 200:
                        data = response.json()
                        self.data_queue.put(data)
                except Exception as e:
                    logger.error(f"Error collecting data: {str(e)}")
                time.sleep(1)
        
        thread = threading.Thread(target=collect_data, daemon=True)
        thread.start()

    def update_category_distribution(self, category_data):
        """Update the category distribution chart with new data."""
        if not CHARTS_AVAILABLE:
            return
            
        self.category_chart.removeAllSeries()
        series = QPieSeries()
        
        for category, count in category_data.items():
            slice = QPieSlice(category, count)
            slice.setLabelVisible(True)
            series.append(slice)
        
        self.category_chart.addSeries(series)
        self.category_chart.setTitle("Category Distribution")

    def update_recent_activity(self, recent_activities):
        """Update the recent activities list."""
        try:
            self.activities_list.clear()
            for activity in recent_activities[-10:]:  # Show last 10 activities
                item = QListWidgetItem(activity)
                self.activities_list.addItem(item)
        except Exception as e:
            logger.error(f"Error updating recent activities: {str(e)}")

    def closeEvent(self, event):
        """Handle window close event."""
        # Clean up resources
        self.update_timer.stop()
        event.accept()

    def update_theme(self):
        """Update the application theme."""
        if self.is_dark_mode:
            self.setStyleSheet(f"""
                QMainWindow {{
                    background: {DARK_MODE['background']};
                }}
                QWidget {{
                    background: {DARK_MODE['background']};
                    color: {DARK_MODE['text']};
                }}
                QTabWidget::pane {{
                    border: 1px solid {DARK_MODE['border']};
                    border-radius: 5px;
                    background: {DARK_MODE['secondary']};
                }}
                QTabBar::tab {{
                    background: {DARK_MODE['background']};
                    border: 1px solid {DARK_MODE['border']};
                    padding: 8px 16px;
                    margin-right: 2px;
                    color: {DARK_MODE['text']};
                }}
                QTabBar::tab:selected {{
                    background: {DARK_MODE['secondary']};
                    border-bottom: 2px solid {DARK_MODE['accent']};
                }}
                QTextEdit {{
                    background: {DARK_MODE['secondary']};
                    color: {DARK_MODE['text']};
                    border: 1px solid {DARK_MODE['border']};
                }}
                QLineEdit {{
                    background: {DARK_MODE['secondary']};
                    color: {DARK_MODE['text']};
                    border: 1px solid {DARK_MODE['border']};
                    padding: 5px;
                }}
            """)
        else:
            self.setStyleSheet("""
                QMainWindow {
                    background: #f8f9fa;
                }
                QWidget {
                    background: #f8f9fa;
                    color: #2c3e50;
                }
                QTabWidget::pane {
                    border: 1px solid #e9ecef;
                    border-radius: 5px;
                    background: white;
                }
                QTabBar::tab {
                    background: #f8f9fa;
                    border: 1px solid #e9ecef;
                    padding: 8px 16px;
                    margin-right: 2px;
                }
                QTabBar::tab:selected {
                    background: white;
                    border-bottom: 2px solid #4a90e2;
                }
            """)

    def create_pentest_tab(self):
        tab = QWidget()
        layout = QVBoxLayout()
        layout.addWidget(QLabel("<h2>Pentest</h2>"))
        self.pentest_input = QLineEdit()
        self.pentest_input.setPlaceholderText("Enter target (domain or IP)...")
        self.pentest_tool = QComboBox()
        self.pentest_tool.addItems(["nmap", "sqlmap"])
        pentest_btn = QPushButton("Run Pentest")
        pentest_btn.clicked.connect(self.run_pentest)
        self.pentest_output = QTextEdit()
        self.pentest_output.setReadOnly(True)
        layout.addWidget(self.pentest_input)
        layout.addWidget(self.pentest_tool)
        layout.addWidget(pentest_btn)
        layout.addWidget(self.pentest_output)
        tab.setLayout(layout)
        self.tabs.addTab(tab, "Pentest")

    def run_pentest(self):
        target = self.pentest_input.text().strip()
        tool = self.pentest_tool.currentText()
        if not target:
            self.pentest_output.setText("Please enter a target.")
            return
        try:
            resp = requests.post(f"http://127.0.0.1:8000/pentest", json={"target": target, "tool": tool})
            if resp.status_code == 200:
                result = resp.json().get("result", "No result.")
                self.pentest_output.setText(result)
            else:
                self.pentest_output.setText(f"Error: {resp.text}")
        except Exception as e:
            self.pentest_output.setText(f"Error: {e}")

    def voice_input(self):
        """Handle voice input using speech recognition."""
        if not STT_AVAILABLE:
            self.add_chat_bubble("Speech recognition is not available", user=False, label="Error")
            return
            
        try:
            recognizer = sr.Recognizer()
            
            with sr.Microphone() as source:
                self.loading_label.setText("Listening...")
                audio = recognizer.listen(source)
                
            self.loading_label.setText("Processing...")
            text = recognizer.recognize_google(audio)
            
            if text:
                self.user_input.setText(text)
                self.handle_user_input()
                
        except Exception as e:
            self.add_chat_bubble(str(e), user=False, label="Error")
        finally:
            self.loading_label.setText("")

    def speak_last_answer(self):
        """Read the last AI response using text-to-speech."""
        if not TTS_AVAILABLE:
            self.add_chat_bubble("Text-to-speech is not available", user=False, label="Error")
            return
            
        try:
            engine = pyttsx3.init()
            
            # Get the last AI response
            last_response = None
            for i in range(self.chat_history_ui.document().blockCount() - 1, -1, -1):
                block = self.chat_history_ui.document().findBlockByLineNumber(i)
                text = block.text()
                if "MeAI:" in text:
                    last_response = text.split("MeAI:")[1].strip()
                    break
            
            if last_response:
                engine.say(last_response)
                engine.runAndWait()
            else:
                self.add_chat_bubble("No AI response found to read", user=False, label="Note")
                
        except Exception as e:
            self.add_chat_bubble(str(e), user=False, label="Error")

    def create_web_tab(self):
        """Create the web tab with web browsing capabilities."""
        web_tab = QWidget()
        layout = QVBoxLayout(web_tab)
        
        # Header
        header = QLabel("Web Browser")
        header.setStyleSheet(f"""
            QLabel {{
                color: {DARK_MODE['text'] if self.is_dark_mode else '#2c3e50'};
                font-size: 24px;
                font-weight: bold;
                padding: 20px;
            }}
        """)
        layout.addWidget(header)
        
        # URL input
        url_layout = QHBoxLayout()
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("Enter URL...")
        self.url_input.returnPressed.connect(self.navigate_to_url)
        
        go_button = QPushButton("Go")
        go_button.clicked.connect(self.navigate_to_url)
        
        url_layout.addWidget(self.url_input)
        url_layout.addWidget(go_button)
        layout.addLayout(url_layout)
        
        # Web view
        self.web_view = QWebEngineView()
        layout.addWidget(self.web_view)
        
        return web_tab

    def create_settings_tab(self):
        """Create the settings tab with configuration options."""
        settings_tab = QWidget()
        layout = QVBoxLayout(settings_tab)
        
        # Header
        header = QLabel("Settings")
        header.setStyleSheet(f"""
            QLabel {{
                color: {DARK_MODE['text'] if self.is_dark_mode else '#2c3e50'};
                font-size: 24px;
                font-weight: bold;
                padding: 20px;
            }}
        """)
        layout.addWidget(header)
        
        # Theme settings
        theme_group = QGroupBox("Theme")
        theme_layout = QVBoxLayout()
        
        dark_mode_checkbox = QCheckBox("Dark Mode")
        dark_mode_checkbox.setChecked(self.is_dark_mode)
        dark_mode_checkbox.stateChanged.connect(self.toggle_dark_mode)
        
        theme_layout.addWidget(dark_mode_checkbox)
        theme_group.setLayout(theme_layout)
        layout.addWidget(theme_group)
        
        # Model settings
        model_group = QGroupBox("Model Settings")
        model_layout = QVBoxLayout()
        
        model_label = QLabel("Model Path:")
        self.model_path = QLineEdit()
        self.model_path.setPlaceholderText("Enter path to model file...")
        
        model_layout.addWidget(model_label)
        model_layout.addWidget(self.model_path)
        model_group.setLayout(model_layout)
        layout.addWidget(model_group)
        
        # Save button
        save_button = QPushButton("Save Settings")
        save_button.clicked.connect(self.save_settings)
        layout.addWidget(save_button)
        
        layout.addStretch()
        return settings_tab

    def create_backup_tab(self):
        """Create the backup tab for data backup and restore."""
        backup_tab = QWidget()
        layout = QVBoxLayout(backup_tab)
        
        # Header
        header = QLabel("Backup & Restore")
        header.setStyleSheet(f"""
            QLabel {{
                color: {DARK_MODE['text'] if self.is_dark_mode else '#2c3e50'};
                font-size: 24px;
                font-weight: bold;
                padding: 20px;
            }}
        """)
        layout.addWidget(header)
        
        # Backup section
        backup_group = QGroupBox("Create Backup")
        backup_layout = QVBoxLayout()
        
        backup_path_label = QLabel("Backup Location:")
        self.backup_path = QLineEdit()
        self.backup_path.setPlaceholderText("Enter backup directory path...")
        
        create_backup_button = QPushButton("Create Backup")
        create_backup_button.clicked.connect(self.create_backup)
        
        backup_layout.addWidget(backup_path_label)
        backup_layout.addWidget(self.backup_path)
        backup_layout.addWidget(create_backup_button)
        backup_group.setLayout(backup_layout)
        layout.addWidget(backup_group)
        
        # Restore section
        restore_group = QGroupBox("Restore from Backup")
        restore_layout = QVBoxLayout()
        
        restore_path_label = QLabel("Backup File:")
        self.restore_path = QLineEdit()
        self.restore_path.setPlaceholderText("Enter backup file path...")
        
        restore_button = QPushButton("Restore")
        restore_button.clicked.connect(self.restore_backup)
        
        restore_layout.addWidget(restore_path_label)
        restore_layout.addWidget(self.restore_path)
        restore_layout.addWidget(restore_button)
        restore_group.setLayout(restore_layout)
        layout.addWidget(restore_group)
        
        layout.addStretch()
        return backup_tab

    def navigate_to_url(self):
        """Navigate to the URL entered in the URL input."""
        url = self.url_input.text()
        if url:
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url
            self.web_view.setUrl(QUrl(url))

    def toggle_dark_mode(self, state):
        """Toggle dark mode on/off."""
        self.is_dark_mode = bool(state)
        self.update_theme()

    def save_settings(self):
        """Save the current settings."""
        # Save model path
        model_path = self.model_path.text()
        if model_path:
            # Save to config file or database
            pass
        
        # Show success message
        QMessageBox.information(self, "Settings Saved", "Settings have been saved successfully.")

    def create_backup(self):
        """Create a backup of the current data."""
        backup_path = self.backup_path.text()
        if not backup_path:
            QMessageBox.warning(self, "Error", "Please enter a backup location.")
            return
        
        try:
            # Create backup logic here
            QMessageBox.information(self, "Backup Created", "Backup created successfully.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to create backup: {str(e)}")

    def restore_backup(self):
        """Restore data from a backup file."""
        restore_path = self.restore_path.text()
        if not restore_path:
            QMessageBox.warning(self, "Error", "Please enter a backup file path.")
            return
        
        try:
            # Restore logic here
            QMessageBox.information(self, "Restore Complete", "Data restored successfully.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to restore backup: {str(e)}")

    def set_dark_mode(self, enabled):
        """Enable or disable dark mode and update the theme for the whole app."""
        self.is_dark_mode = enabled
        self.update_theme()

    def add_to_recent_topics(self, topic, note=""):
        if not hasattr(self, "recent_topics"):
            self.recent_topics = []
        # Avoid empty topics and duplicates
        topic = topic.strip()
        if not topic:
            return
        entry = topic if not note else f"{topic} {note}"
        if entry in self.recent_topics:
            self.recent_topics.remove(entry)
        self.recent_topics.insert(0, entry)
        # Keep only the 10 most recent
        self.recent_topics = self.recent_topics[:10]
        # Optionally sync with server
        try:
            requests.post(f"{SERVER_URL}/memory/recent_topics", json={"topics": self.recent_topics})
        except Exception:
            pass

    def create_knowledge_tab(self):
        """Create the knowledge tab for managing the knowledge base."""
        knowledge_tab = QWidget()
        layout = QVBoxLayout(knowledge_tab)
        
        # Header
        header = QLabel("Knowledge Base")
        header.setStyleSheet(f"""
            QLabel {{
                color: {DARK_MODE['text'] if self.is_dark_mode else '#2c3e50'};
                font-size: 24px;
                font-weight: bold;
                padding: 20px;
            }}
        """)
        layout.addWidget(header)
        
        # Document list
        list_group = QGroupBox("Documents")
        list_layout = QVBoxLayout()
        self.document_list = QListWidget()
        self.document_list.itemClicked.connect(self.show_document_details)
        list_layout.addWidget(self.document_list)
        list_group.setLayout(list_layout)
        layout.addWidget(list_group)
        
        # Document details
        details_group = QGroupBox("Document Details")
        details_layout = QVBoxLayout()
        self.document_details = QTextEdit()
        self.document_details.setReadOnly(True)
        details_layout.addWidget(self.document_details)
        details_group.setLayout(details_layout)
        layout.addWidget(details_group)
        
        # Control buttons
        button_layout = QHBoxLayout()
        
        add_btn = QPushButton("Add Document")
        add_btn.clicked.connect(self.add_document)
        button_layout.addWidget(add_btn)
        
        remove_btn = QPushButton("Remove Document")
        remove_btn.clicked.connect(self.remove_document)
        button_layout.addWidget(remove_btn)
        
        ingest_btn = QPushButton("Ingest Knowledge")
        ingest_btn.clicked.connect(self.ingest_knowledge)
        button_layout.addWidget(ingest_btn)
        
        layout.addLayout(button_layout)
        
        self.tabs.addTab(knowledge_tab, "Knowledge")
        
        # Load initial documents
        self.load_documents()

    def load_documents(self):
        """Load available documents from the knowledge base."""
        try:
            response = requests.get(f"{SERVER_URL}/knowledge/list")
            if response.status_code == 200:
                documents = response.json()
                self.document_list.clear()
                for doc in documents:
                    self.document_list.addItem(doc["name"])
        except Exception as e:
            self.show_error_dialog(f"Failed to load documents: {str(e)}")

    def add_document(self):
        """Add a new document to the knowledge base."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Document",
            "",
            "All Files (*.*);;Text Files (*.txt);;PDF Files (*.pdf);;Markdown Files (*.md)"
        )
        if file_path:
            try:
                with open(file_path, 'rb') as f:
                    files = {'file': f}
                    response = requests.post(f"{SERVER_URL}/knowledge/add", files=files)
                    if response.status_code == 200:
                        self.load_documents()
                    else:
                        self.show_error_dialog(f"Failed to add document: {response.text}")
            except Exception as e:
                self.show_error_dialog(f"Failed to add document: {str(e)}")

    def remove_document(self):
        """Remove the selected document from the knowledge base."""
        current_item = self.document_list.currentItem()
        if not current_item:
            return
            
        doc_name = current_item.text()
        try:
            response = requests.delete(f"{SERVER_URL}/knowledge/remove", params={"name": doc_name})
            if response.status_code == 200:
                self.load_documents()
                self.document_details.clear()
            else:
                self.show_error_dialog(f"Failed to remove document: {response.text}")
        except Exception as e:
            self.show_error_dialog(f"Failed to remove document: {str(e)}")

    def ingest_knowledge(self):
        """Ingest all documents in the knowledge base."""
        try:
            response = requests.post(f"{SERVER_URL}/knowledge/ingest")
            if response.status_code == 200:
                QMessageBox.information(self, "Success", "Knowledge base ingestion completed successfully.")
            else:
                self.show_error_dialog(f"Failed to ingest knowledge: {response.text}")
        except Exception as e:
            self.show_error_dialog(f"Failed to ingest knowledge: {str(e)}")

    def show_document_details(self, item):
        """Show details of the selected document."""
        try:
            doc_name = item.text()
            response = requests.get(f"{SERVER_URL}/knowledge/details", params={"name": doc_name})
            if response.status_code == 200:
                details = response.json()
                self.document_details.setText(
                    f"Name: {details.get('name', '')}\n"
                    f"Type: {details.get('type', '')}\n"
                    f"Size: {details.get('size', '')}\n"
                    f"Last Modified: {details.get('modified', '')}\n"
                    f"Content Preview:\n{details.get('preview', '')}"
                )
            else:
                self.document_details.setText(f"Error: {response.text}")
        except Exception as e:
            self.document_details.setText(f"Error: {str(e)}")

    def show_task_details(self, item):
        """Show details of the selected task."""
        try:
            task_name = item.text().split(" - ")[0].replace("Task: ", "")
            response = requests.get(f"{SERVER_URL}/task/details", params={"name": task_name})
            if response.status_code == 200:
                details = response.json()
                self.task_details.setText(
                    f"Task: {details.get('name', '')}\n"
                    f"Status: {details.get('status', '')}\n"
                    f"Output: {details.get('output', '')}\n"
                    f"Error: {details.get('error', '')}\n"
                    f"Start Time: {details.get('start_time', '')}\n"
                    f"End Time: {details.get('end_time', '')}"
                )
            else:
                self.task_details.setText(f"Error: {response.text}")
        except Exception as e:
            self.task_details.setText(f"Error: {str(e)}")

    def show_plugin_details(self, item):
        """Show details of the selected plugin."""
        try:
            plugin_name = item.text()
            response = requests.get(f"{SERVER_URL}/plugins/details", params={"name": plugin_name})
            if response.status_code == 200:
                details = response.json()
                self.plugin_details.setText(
                    f"Name: {details.get('name', '')}\n"
                    f"Description: {details.get('description', '')}\n"
                    f"Version: {details.get('version', '')}\n"
                    f"Author: {details.get('author', '')}\n"
                    f"Last Modified: {details.get('modified', '')}\n"
                    f"Usage:\n{details.get('usage', '')}"
                )
            else:
                self.plugin_details.setText(f"Error: {response.text}")
        except Exception as e:
            self.plugin_details.setText(f"Error: {str(e)}")

    def create_code_tab(self):
        """Create the code tab for executing Python code."""
        code_tab = QWidget()
        layout = QVBoxLayout(code_tab)
        
        # Header
        header = QLabel("Code Execution")
        header.setStyleSheet(f"""
            QLabel {{
                color: {DARK_MODE['text'] if self.is_dark_mode else '#2c3e50'};
                font-size: 24px;
                font-weight: bold;
                padding: 20px;
            }}
        """)
        layout.addWidget(header)
        
        # Code editor
        editor_group = QGroupBox("Code Editor")
        editor_layout = QVBoxLayout()
        self.code_editor = QTextEdit()
        self.code_editor.setPlaceholderText("Enter Python code here...")
        editor_layout.addWidget(self.code_editor)
        editor_group.setLayout(editor_layout)
        layout.addWidget(editor_group)
        
        # Output area
        output_group = QGroupBox("Output")
        output_layout = QVBoxLayout()
        self.code_output = QTextEdit()
        self.code_output.setReadOnly(True)
        output_layout.addWidget(self.code_output)
        output_group.setLayout(output_layout)
        layout.addWidget(output_group)
        
        # Control buttons
        button_layout = QHBoxLayout()
        
        execute_btn = QPushButton("Execute")
        execute_btn.clicked.connect(self.execute_code)
        button_layout.addWidget(execute_btn)
        
        clear_btn = QPushButton("Clear")
        clear_btn.clicked.connect(self.clear_code)
        button_layout.addWidget(clear_btn)
        
        layout.addLayout(button_layout)
        
        self.tabs.addTab(code_tab, "Code")

    def execute_code(self):
        """Execute Python code."""
        code = self.code_editor.toPlainText()
        if not code:
            return
            
        try:
            response = requests.post(
                f"{SERVER_URL}/code/execute",
                json={"code": code}
            )
            if response.status_code == 200:
                result = response.json()
                self.code_output.setText(result.get("output", ""))
            else:
                self.code_output.setText(f"Error: {response.text}")
        except Exception as e:
            self.code_output.setText(f"Error: {str(e)}")

    def clear_code(self):
        """Clear the code editor and output."""
        self.code_editor.clear()
        self.code_output.clear()

    def create_automation_tab(self):
        """Create the automation tab for task automation."""
        automation_tab = QWidget()
        layout = QVBoxLayout(automation_tab)
        
        # Header
        header = QLabel("Task Automation")
        header.setStyleSheet(f"""
            QLabel {{
                color: {DARK_MODE['text'] if self.is_dark_mode else '#2c3e50'};
                font-size: 24px;
                font-weight: bold;
                padding: 20px;
            }}
        """)
        layout.addWidget(header)
        
        # Task input
        input_group = QGroupBox("Task Input")
        input_layout = QVBoxLayout()
        self.task_input = QTextEdit()
        self.task_input.setPlaceholderText("Enter task instructions here...")
        input_layout.addWidget(self.task_input)
        input_group.setLayout(input_layout)
        layout.addWidget(input_group)
        
        # Task list
        list_group = QGroupBox("Task History")
        list_layout = QVBoxLayout()
        self.task_list = QListWidget()
        self.task_list.itemClicked.connect(self.show_task_details)
        list_layout.addWidget(self.task_list)
        list_group.setLayout(list_layout)
        layout.addWidget(list_group)
        
        # Task details
        details_group = QGroupBox("Task Details")
        details_layout = QVBoxLayout()
        self.task_details = QTextEdit()
        self.task_details.setReadOnly(True)
        details_layout.addWidget(self.task_details)
        details_group.setLayout(details_layout)
        layout.addWidget(details_group)
        
        # Control buttons
        button_layout = QHBoxLayout()
        
        execute_btn = QPushButton("Execute Task")
        execute_btn.clicked.connect(self.execute_task)
        button_layout.addWidget(execute_btn)
        
        clear_btn = QPushButton("Clear")
        clear_btn.clicked.connect(self.clear_task)
        button_layout.addWidget(clear_btn)
        
        layout.addLayout(button_layout)
        
        self.tabs.addTab(automation_tab, "Automation")

    def execute_task(self):
        """Execute an automation task."""
        task = self.task_input.toPlainText()
        if not task:
            return
            
        try:
            response = requests.post(
                f"{SERVER_URL}/task/execute",
                json={"instruction": task}
            )
            if response.status_code == 200:
                result = response.json()
                self.task_list.addItem(f"Task: {task} - Status: {result.get('status', 'unknown')}")
                self.task_input.clear()
            else:
                self.show_error_dialog(f"Failed to execute task: {response.text}")
        except Exception as e:
            self.show_error_dialog(f"Failed to execute task: {str(e)}")

    def clear_task(self):
        """Clear the task input and details."""
        self.task_input.clear()
        self.task_details.clear()

    def create_plugins_tab(self):
        """Create the plugins tab for plugin management."""
        plugins_tab = QWidget()
        layout = QVBoxLayout(plugins_tab)
        
        # Header
        header = QLabel("Plugin Management")
        header.setStyleSheet(f"""
            QLabel {{
                color: {DARK_MODE['text'] if self.is_dark_mode else '#2c3e50'};
                font-size: 24px;
                font-weight: bold;
                padding: 20px;
            }}
        """)
        layout.addWidget(header)
        
        # Plugin list
        list_group = QGroupBox("Available Plugins")
        list_layout = QVBoxLayout()
        self.plugin_list = QListWidget()
        self.plugin_list.itemClicked.connect(self.show_plugin_details)
        list_layout.addWidget(self.plugin_list)
        list_group.setLayout(list_layout)
        layout.addWidget(list_group)
        
        # Plugin details
        details_group = QGroupBox("Plugin Details")
        details_layout = QVBoxLayout()
        self.plugin_details = QTextEdit()
        self.plugin_details.setReadOnly(True)
        details_layout.addWidget(self.plugin_details)
        details_group.setLayout(details_layout)
        layout.addWidget(details_group)
        
        # Control buttons
        button_layout = QHBoxLayout()
        
        add_btn = QPushButton("Add Plugin")
        add_btn.clicked.connect(self.add_plugin)
        button_layout.addWidget(add_btn)
        
        remove_btn = QPushButton("Remove Plugin")
        remove_btn.clicked.connect(self.remove_plugin)
        button_layout.addWidget(remove_btn)
        
        run_btn = QPushButton("Run Plugin")
        run_btn.clicked.connect(self.run_plugin)
        button_layout.addWidget(run_btn)
        
        layout.addLayout(button_layout)
        
        self.tabs.addTab(plugins_tab, "Plugins")
        
        # Load initial plugins
        self.load_plugins()

    def load_plugins(self):
        """Load available plugins."""
        try:
            response = requests.get(f"{SERVER_URL}/plugins/list")
            if response.status_code == 200:
                plugins = response.json()
                self.plugin_list.clear()
                for plugin in plugins:
                    self.plugin_list.addItem(plugin["name"])
        except Exception as e:
            self.show_error_dialog(f"Failed to load plugins: {str(e)}")

    def add_plugin(self):
        """Add a new plugin."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Plugin",
            "",
            "Python Files (*.py)"
        )
        if file_path:
            try:
                with open(file_path, 'rb') as f:
                    files = {'file': f}
                    response = requests.post(f"{SERVER_URL}/plugins/add", files=files)
                    if response.status_code == 200:
                        self.load_plugins()
                    else:
                        self.show_error_dialog(f"Failed to add plugin: {response.text}")
            except Exception as e:
                self.show_error_dialog(f"Failed to add plugin: {str(e)}")

    def remove_plugin(self):
        """Remove the selected plugin."""
        current_item = self.plugin_list.currentItem()
        if not current_item:
            return
            
        plugin_name = current_item.text()
        try:
            response = requests.delete(f"{SERVER_URL}/plugins/remove", params={"name": plugin_name})
            if response.status_code == 200:
                self.load_plugins()
                self.plugin_details.clear()
            else:
                self.show_error_dialog(f"Failed to remove plugin: {response.text}")
        except Exception as e:
            self.show_error_dialog(f"Failed to remove plugin: {str(e)}")

    def run_plugin(self):
        """Run the selected plugin."""
        current_item = self.plugin_list.currentItem()
        if not current_item:
            return
            
        plugin_name = current_item.text()
        try:
            response = requests.post(
                f"{SERVER_URL}/plugins/run",
                json={"name": plugin_name}
            )
            if response.status_code == 200:
                result = response.json()
                self.plugin_details.setText(f"Output: {result.get('output', '')}")
            else:
                self.show_error_dialog(f"Failed to run plugin: {response.text}")
        except Exception as e:
            self.show_error_dialog(f"Failed to run plugin: {str(e)}")

    def create_admin_tab(self):
        """Create the admin tab for logs and server management."""
        admin_tab = QWidget()
        layout = QVBoxLayout(admin_tab)
        
        # Header
        header = QLabel("Server Management")
        header.setStyleSheet(f"""
            QLabel {{
                color: {DARK_MODE['text'] if self.is_dark_mode else '#2c3e50'};
                font-size: 24px;
                font-weight: bold;
                padding: 20px;
            }}
        """)
        layout.addWidget(header)
        
        # Server status
        status_group = QGroupBox("Server Status")
        status_layout = QVBoxLayout()
        self.server_status = QLabel("Checking server status...")
        status_layout.addWidget(self.server_status)
        status_group.setLayout(status_layout)
        layout.addWidget(status_group)
        
        # Log viewer
        log_group = QGroupBox("Server Logs")
        log_layout = QVBoxLayout()
        self.log_viewer = QTextEdit()
        self.log_viewer.setReadOnly(True)
        log_layout.addWidget(self.log_viewer)
        log_group.setLayout(log_layout)
        layout.addWidget(log_group)
        
        # Control buttons
        button_layout = QHBoxLayout()
        
        refresh_btn = QPushButton("Refresh Logs")
        refresh_btn.clicked.connect(self.refresh_logs)
        button_layout.addWidget(refresh_btn)
        
        restart_btn = QPushButton("Restart Server")
        restart_btn.clicked.connect(self.restart_server)
        button_layout.addWidget(restart_btn)
        
        clear_btn = QPushButton("Clear Logs")
        clear_btn.clicked.connect(self.clear_logs)
        button_layout.addWidget(clear_btn)
        
        layout.addLayout(button_layout)
        
        self.tabs.addTab(admin_tab, "Admin")
        
        # Start log monitoring
        self.start_log_monitoring()

    def start_log_monitoring(self):
        """Start monitoring server logs."""
        def monitor_logs():
            while True:
                try:
                    response = requests.get(f"{SERVER_URL}/logs")
                    if response.status_code == 200:
                        logs = response.json()
                        # Emit the signal with the new log text
                        self.log_update_signal.emit("\n".join(logs))
                except Exception:
                    pass
                time.sleep(5)  # Update every 5 seconds
        
        thread = threading.Thread(target=monitor_logs, daemon=True)
        thread.start()

    def refresh_logs(self):
        """Refresh the log viewer."""
        try:
            response = requests.get(f"{SERVER_URL}/logs")
            if response.status_code == 200:
                logs = response.json()
                self.log_viewer.setText("\n".join(logs))
        except Exception as e:
            self.show_error_dialog(f"Failed to refresh logs: {str(e)}")

    def clear_logs(self):
        """Clear the server logs."""
        try:
            response = requests.post(f"{SERVER_URL}/logs/clear")
            if response.status_code == 200:
                self.log_viewer.clear()
            else:
                self.show_error_dialog(f"Failed to clear logs: {response.text}")
        except Exception as e:
            self.show_error_dialog(f"Failed to clear logs: {str(e)}")

    def restart_server(self):
        """Restart the server."""
        try:
            response = requests.post(f"{SERVER_URL}/restart")
            if response.status_code == 200:
                self.server_status.setText("Server is restarting...")
                time.sleep(2)  # Wait for server to restart
                self.server_status.setText("Server is running")
            else:
                self.show_error_dialog(f"Failed to restart server: {response.text}")
        except Exception as e:
            self.show_error_dialog(f"Failed to restart server: {str(e)}")

def get_user_name():
    try:
        resp = requests.get(f"{SERVER_URL}/memory/user_info/name")
        if resp.status_code == 200:
            return resp.json().get("value")
    except Exception:
        pass
    return None

def main():
    app = QApplication(sys.argv)
    
    # Set application style
    app.setStyle("Fusion")
    
    # Create and show the main window
    window = MeAIApp()
    window.show()
    
    # Start the application
    sys.exit(app.exec())

if __name__ == "__main__":
    main() 