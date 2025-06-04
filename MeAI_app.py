import sys
import requests
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QLineEdit, QPushButton, QLabel, QTabWidget, QFileDialog, QMessageBox, QProgressBar, QFrame, QCheckBox, QInputDialog, QListWidget, QListWidgetItem, QSplitter, QComboBox, QScrollArea, QGridLayout
)
from PyQt6.QtGui import QFont, QColor, QTextCharFormat, QTextCursor, QPalette, QLinearGradient, QGradient, QIcon
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, QPropertyAnimation, QEasingCurve, QSize, QFileSystemWatcher
import markdown2
import json
import subprocess
import os
import platform
import time
from datetime import datetime
from collections import defaultdict
import threading
import queue
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
import importlib
import logging

APP_NAME = "MeAI"
BRAND = "MeAI by Mesum Bin Shaukat\nOwner of World Of Tech"
SERVER_URL = "http://127.0.0.1:8000"

DARK_STYLE = """
QWidget { background-color: #181a1b; color: #e8eaed; font-family: 'Segoe UI', 'Arial', sans-serif; }
QTextEdit, QLineEdit { background-color: #23272a; color: #e8eaed; border: 1px solid #444; border-radius: 4px; }
QPushButton { background-color: #282c34; color: #e8eaed; border: 1px solid #444; border-radius: 4px; padding: 6px 12px; }
QPushButton:hover { background-color: #3a3f4b; }
QTabWidget::pane { border: 1px solid #444; }
QTabBar::tab { background: #23272a; color: #e8eaed; padding: 8px; border: 1px solid #444; border-bottom: none; }
QTabBar::tab:selected { background: #282c34; }
QLabel { color: #e8eaed; }
"""

try:
    import pyttsx3
    TTS_AVAILABLE = True
except ImportError:
    TTS_AVAILABLE = False
try:
    from vosk import Model, KaldiRecognizer
    import pyaudio
    STT_AVAILABLE = True
except ImportError:
    STT_AVAILABLE = False

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
                logger.info("Detected UI changes, reloading...")
                self.last_modified = current_modified
                
                # Reload the module
                importlib.reload(sys.modules[__name__])
                
                # Recreate the main window
                self.app.closeAllWindows()
                new_window = MeAIApp()
                new_window.show()
                
        except Exception as e:
            logger.error(f"Error reloading UI: {e}")

class ChatWorker(QThread):
    response_signal = pyqtSignal(str)
    error_signal = pyqtSignal(str)
    def __init__(self, history, user_input, cyber_mode=False):
        super().__init__()
        self.history = history
        self.user_input = user_input
        self.cyber_mode = cyber_mode
    def run(self):
        try:
            resp = requests.post(
                f"{SERVER_URL}/chat",
                json={"messages": self.history, "query": self.user_input, "use_rag": True, "cyber_mode": self.cyber_mode}, timeout=120
            )
            if resp.status_code == 200:
                response = resp.json()["response"]
                self.response_signal.emit(response)
            else:
                error = resp.json().get("error", str(resp.text))
                self.error_signal.emit(error)
        except Exception as e:
            self.error_signal.emit(str(e))

class StreamingChatWorker(QThread):
    partial_signal = pyqtSignal(str)
    done_signal = pyqtSignal(str)
    error_signal = pyqtSignal(str)
    def __init__(self, history, user_input, cyber_mode=False):
        super().__init__()
        self.history = history
        self.user_input = user_input
        self.cyber_mode = cyber_mode
        self.prefs = {}
    def run(self):
        try:
            payload = {
                "messages": self.history,
                "query": self.user_input,
                "use_rag": True,
                "cyber_mode": self.cyber_mode,
            }
            if self.prefs:
                payload["preferences"] = self.prefs
            with requests.post(
                f"{SERVER_URL}/chat/stream",
                json=payload,
                stream=True,
                timeout=180
            ) as resp:
                if resp.status_code == 200:
                    partial = ""
                    for chunk in resp.iter_content(chunk_size=1, decode_unicode=True):
                        if chunk:
                            partial += chunk
                            self.partial_signal.emit(partial)
                    self.done_signal.emit(partial)
                else:
                    error = resp.text
                    self.error_signal.emit(error)
        except Exception as e:
            self.error_signal.emit(str(e))

class ModernButton(QPushButton):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
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

class AnimatedProgressBar(QProgressBar):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            QProgressBar {
                border: 2px solid #4a90e2;
                border-radius: 5px;
                text-align: center;
                background-color: #f0f0f0;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                    stop:0 #4a90e2, stop:1 #67b26f);
                border-radius: 3px;
            }
        """)
        self.animation = QPropertyAnimation(self, b"value")
        self.animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.animation.setDuration(1000)

    def setValue(self, value):
        self.animation.setStartValue(self.value())
        self.animation.setEndValue(value)
        self.animation.start()

class CategoryCard(QFrame):
    def __init__(self, title, count, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, 
                    stop:0 #ffffff, stop:1 #f8f9fa);
                border-radius: 10px;
                border: 1px solid #e9ecef;
            }
        """)
        layout = QVBoxLayout()
        
        title_label = QLabel(title)
        title_label.setStyleSheet("""
            QLabel {
                color: #2c3e50;
                font-size: 16px;
                font-weight: bold;
            }
        """)
        
        count_label = QLabel(str(count))
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

class MeAIApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MeAI Desktop")
        self.setGeometry(100, 100, 1200, 800)
        
        # Initialize system information
        self.system_info = None
        self.update_system_info()
        
        # Initialize hot reloader
        self.hot_reloader = HotReloader(QApplication.instance())
        
        # Create main widget and layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)
        
        # Create tab widget
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
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
        layout.addWidget(self.tabs)
        
        # Initialize tabs
        self.init_chat_tab()
        self.init_dashboard_tab()
        
        # Initialize chat history with system context
        self.chat_history = [
            {
                "role": "system",
                "content": f"""You are a helpful, knowledgeable AI assistant with direct access to the user's system.
                You can execute system commands and access local resources.
                Current system information:
                Platform: {self.system_info.get('platform', 'Unknown')}
                Version: {self.system_info.get('platform_version', 'Unknown')}
                Architecture: {self.system_info.get('architecture', 'Unknown')}
                Available drives: {', '.join([d['drive'] for d in self.system_info.get('drives', [])])}
                
                You can directly execute commands like:
                - Opening applications (e.g., "open notepad", "open chrome")
                - Running system commands (e.g., "open command prompt", "open powershell")
                - Accessing files and directories
                
                Always execute commands directly when requested, don't just provide instructions.
                """
            }
        ]

        # Initialize data structures
        self.training_data = defaultdict(int)
        self.category_data = defaultdict(int)
        self.recent_activities = []
        self.data_queue = queue.Queue()
        
        # Start data collection thread
        self.start_data_collection()
        
        # Set up timer for UI updates
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_ui)
        self.update_timer.start(1000)  # Update every second

    def update_system_info(self):
        """Update system information from the server."""
        try:
            response = requests.post("http://localhost:8000/system/info")
            if response.status_code == 200:
                self.system_info = response.json()
        except Exception as e:
            print(f"Error updating system info: {e}")
            self.system_info = {}

    def is_task_request(self, user_input):
        """
        Enhanced detection of system-level task requests.
        """
        nl = user_input.strip().lower()
        
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

    def handle_user_input(self):
        """Handle user input with enhanced system command support."""
        user_input = self.input_field.text().strip()
        if not user_input:
            return
            
        self.input_field.clear()
        self.add_message("You", user_input)
        
        # Check if it's a system command
        if self.is_task_request(user_input):
            try:
                response = requests.post(
                    "http://localhost:8000/task/execute",
                    json={"instruction": user_input}
                )
                if response.status_code == 200:
                    result = response.json()
                    self.add_message("MeAI", f"Executed command: {result['command']}")
                else:
                    error = response.json().get("error", "Unknown error")
                    self.add_message("MeAI", f"Error executing command: {error}")
            except Exception as e:
                self.add_message("MeAI", f"Error: {str(e)}")
            return
            
        # Handle regular chat
        self.chat_history.append({"role": "user", "content": user_input})
        
        try:
            response = requests.post(
                "http://localhost:8000/chat",
                json={"messages": self.chat_history}
            )
            if response.status_code == 200:
                result = response.json()
                ai_response = result.get("response", "Sorry, I couldn't process that.")
                self.add_message("MeAI", ai_response)
                self.chat_history.append({"role": "assistant", "content": ai_response})
            else:
                self.add_message("MeAI", "Error: Could not get response from server.")
        except Exception as e:
            self.add_message("MeAI", f"Error: {str(e)}")

    def init_chat_tab(self):
        tab = QWidget()
        layout = QVBoxLayout()
        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        self.chat_display.setFrameStyle(QFrame.Shape.NoFrame)
        self.chat_input = QLineEdit()
        self.chat_input.setPlaceholderText("Type your message and press Enter...")
        self.chat_input.returnPressed.connect(self.send_chat)
        send_btn = QPushButton("Send")
        send_btn.clicked.connect(self.send_chat)
        clear_btn = QPushButton("Clear Chat")
        clear_btn.clicked.connect(self.clear_chat)
        # Voice input/output buttons
        mic_btn = QPushButton("🎤")
        mic_btn.setToolTip("Voice Input")
        mic_btn.clicked.connect(self.voice_input)
        mic_btn.setEnabled(STT_AVAILABLE)
        speaker_btn = QPushButton("🔊")
        speaker_btn.setToolTip("Read Last Answer")
        speaker_btn.clicked.connect(self.speak_last_answer)
        speaker_btn.setEnabled(TTS_AVAILABLE)
        self.loading_label = QLabel("")
        self.loading_label.setStyleSheet("color:#fbbc04;font-weight:bold;")
        # Cybersecurity Mode Checkbox
        self.cyber_checkbox = QCheckBox("Cybersecurity Mode (Expert)")
        self.cyber_checkbox.setChecked(False)
        self.cyber_checkbox.stateChanged.connect(self.toggle_cyber_mode)
        layout.addWidget(QLabel(f"<h2>{APP_NAME} Chat</h2>"))
        layout.addWidget(self.cyber_checkbox)
        layout.addWidget(self.chat_display)
        hbox = QHBoxLayout()
        hbox.addWidget(self.chat_input)
        hbox.addWidget(send_btn)
        hbox.addWidget(mic_btn)
        hbox.addWidget(speaker_btn)
        hbox.addWidget(clear_btn)
        layout.addLayout(hbox)
        layout.addWidget(self.loading_label)
        tab.setLayout(layout)
        self.tabs.addTab(tab, "Chat")
        self.chat_history = [
            {"role": "system", "content": "You are a helpful, knowledgeable AI assistant. Answer as helpfully as possible."}
        ]
    def toggle_cyber_mode(self):
        self.cyber_mode = self.cyber_checkbox.isChecked()
        # Optionally, reset chat history or update UI
    def is_task_request(self, user_input):
        """
        Detect if the user input is a system-level task request.
        This should match the backend's mapping logic.
        """
        nl = user_input.strip().lower()
        if (
            "open command prompt" in nl or "open cmd" in nl or "start command prompt" in nl or
            "open powershell" in nl or "open terminal" in nl or
            nl.startswith("run ") or nl.startswith("execute ")
        ):
            return True
        # Optionally, add more patterns here
        return False
    def send_chat(self):
        user_input = self.chat_input.text().strip()
        if not user_input:
            return
        self.add_chat_bubble(user_input, user=True)
        self.chat_history.append({"role": "user", "content": user_input})
        self.chat_input.clear()
        self.loading_label.setText("Thinking...")
        self.last_assistant_bubble_pos = None  # Reset for new response
        prefs = self.preferences.copy()
        try:
            requests.post(f"{SERVER_URL}/log_action", json={"action": "chat_query", "query": user_input, "preferences": prefs})
        except Exception:
            pass
        # --- NEW: Task execution logic ---
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
        # --- END NEW ---
        self.streaming_worker = StreamingChatWorker(self.chat_history, user_input, cyber_mode=self.cyber_mode)
        self.streaming_worker.prefs = prefs
        self.streaming_worker.partial_signal.connect(self.display_partial_response)
        self.streaming_worker.done_signal.connect(self.display_chat_response)
        self.streaming_worker.error_signal.connect(self.fallback_to_sync_worker)
        self.streaming_worker.start()
        self.add_to_recent_topics(user_input, "")
    def display_partial_response(self, partial):
        html = f"<div style='background:#23272a;padding:10px;border-radius:10px;margin:8px;max-width:70%;float:left;color:#f28b82;'><span style='font-weight:bold'>MeAI:</span><br>{markdown2.markdown(partial)}</div><div style='clear:both'></div>"
        cursor = self.chat_display.textCursor()
        doc = self.chat_display.document()
        if self.last_assistant_bubble_pos is None:
            # Insert new bubble and record its position
            cursor.movePosition(QTextCursor.MoveOperation.End)
            self.chat_display.setTextCursor(cursor)
            self.chat_display.insertHtml(html)
            self.chat_display.append("")  # Ensure new line after bubble
            self.last_assistant_bubble_pos = doc.characterCount() - 2  # -2 for trailing newline
        else:
            # Replace the last assistant bubble in place
            cursor.setPosition(self.last_assistant_bubble_pos)
            cursor.movePosition(QTextCursor.MoveOperation.End, QTextCursor.MoveMode.KeepAnchor)
            cursor.removeSelectedText()
            cursor.insertHtml(html)
        self.loading_label.setText("Thinking...")
    def fallback_to_sync_worker(self, error):
        # If streaming fails, fallback to old worker
        self.worker = ChatWorker(self.chat_history, self.chat_history[-1]["content"], cyber_mode=self.cyber_mode)
        self.worker.response_signal.connect(self.display_chat_response)
        self.worker.error_signal.connect(self.display_chat_error)
        self.worker.start()
    def display_chat_response(self, response):
        # Support both old and new server responses
        if isinstance(response, dict):
            llm_answer = response.get("llm_answer") or response.get("response")
            web_results = response.get("web_results", [])
            rag_results = response.get("rag_results", [])
            suggestions = response.get("suggestions", [])
        else:
            llm_answer = response
            web_results = []
            rag_results = []
            suggestions = []
        self.chat_history.append({"role": "assistant", "content": llm_answer})
        # LLM answer bubble
        self.add_chat_bubble(llm_answer, user=False, label="LLM Answer")
        # Web search fallback
        if web_results:
            html = "<div style='background:#23272a;padding:10px;border-radius:10px;margin:8px;max-width:70%;float:left;color:#fbbc04;'><b>Web Search Results:</b><ul>"
            for r in web_results:
                html += f"<li><a href='{r.get('href','')}' style='color:#8ab4f8'>{r.get('title','')}</a><br>{r.get('body','')}</li>"
            html += "</ul></div><div style='clear:both'></div>"
            self.chat_display.append(html)
        # RAG fallback
        if rag_results:
            html = "<div style='background:#23272a;padding:10px;border-radius:10px;margin:8px;max-width:70%;float:left;color:#34a853;'><b>Knowledge Base Results:</b><ul>"
            for r in rag_results:
                if isinstance(r, dict) and r.get("source"):
                    src = r.get("source", "unknown")
                    chunk = r.get("chunk", 0)
                    text = r.get("text", "")
                    html += f"<li>{text[:200]}... <button onclick=\"window.open('{src}', '_blank')\">View Source</button> <span style='color:#888'>(chunk {chunk})</span></li>"
                else:
                    html += f"<li>{r}</li>"
            html += "</ul></div><div style='clear:both'></div>"
            self.chat_display.append(html)
        # Suggestions (active follow-up)
        if suggestions:
            self.add_suggestion_buttons(suggestions)
        # Feedback buttons (interactive)
        self.add_feedback_buttons(self.chat_history[-2]["content"] if len(self.chat_history) > 1 else "", llm_answer, web_results, rag_results)
        self.loading_label.setText("")
        # Add to recent topics (update with assistant answer)
        if self.recent_topics:
            self.recent_topics[-1] = self.recent_topics[-1]  # Keep user input as topic
    def display_chat_error(self, error):
        self.loading_label.setText("")
        self.show_error_dialog(error)
    def add_chat_bubble(self, text, user=True, label=None):
        html = markdown2.markdown(text)
        color = "#8ab4f8" if user else "#f28b82"
        align = "right" if user else "left"
        label_html = f"<span style='font-size:10px;color:#aaa;'>{label}</span><br>" if label else ""
        bubble = f"<div style='background:#23272a;padding:10px;border-radius:10px;margin:8px;max-width:70%;float:{align};color:{color};'>{label_html}<span style='font-weight:bold'>{'You' if user else 'MeAI'}:</span><br>{html}</div><div style='clear:both'></div>"
        self.chat_display.append(bubble)
    def clear_chat(self):
        self.chat_display.clear()
        self.chat_history = [
            {"role": "system", "content": "You are a helpful, knowledgeable AI assistant. Answer as helpfully as possible."}
        ]
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
        # Attempt to restart the server in a new process (Windows only for now)
        try:
            if os.name == 'nt':
                subprocess.Popen(["cmd.exe", "/c", "start", "python", "main.py", "server"])
                QMessageBox.information(self, "Restart Server", "Attempted to restart the server. Please check the server window.")
            else:
                QMessageBox.information(self, "Restart Server", "Please restart the server manually in your terminal.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not restart server: {e}")
    def init_knowledge_tab(self):
        tab = QWidget()
        layout = QVBoxLayout()
        layout.addWidget(QLabel("<h2>Knowledge Base</h2>"))
        self.kb_status = QLabel("Drop PDFs or .txt files here or use the button below.")
        layout.addWidget(self.kb_status)
        add_btn = QPushButton("Add Document")
        add_btn.clicked.connect(self.add_document)
        ingest_btn = QPushButton("Ingest Knowledge Base")
        ingest_btn.clicked.connect(self.ingest_kb)
        layout.addWidget(add_btn)
        layout.addWidget(ingest_btn)
        tab.setLayout(layout)
        self.tabs.addTab(tab, "Knowledge Base")
    def add_document(self):
        file, _ = QFileDialog.getOpenFileName(self, "Add Document", "", "PDF Files (*.pdf);;Text Files (*.txt)")
        if file:
            import shutil
            shutil.copy(file, "./knowledge/")
            self.kb_status.setText(f"Added: {file}")
    def ingest_kb(self):
        try:
            import subprocess
            subprocess.check_output([sys.executable, "main.py", "ingest"])
            # Notify server to increment analytics
            import requests
            requests.post(f"{SERVER_URL}/ingest_kb")
            self.kb_status.setText("Knowledge base ingested!")
        except Exception as e:
            self.kb_status.setText(f"Error: {e}")
    def init_web_tab(self):
        tab = QWidget()
        layout = QVBoxLayout()
        layout.addWidget(QLabel("<h2>Web Search</h2>"))
        self.web_input = QLineEdit()
        self.web_input.setPlaceholderText("Enter your search query...")
        search_btn = QPushButton("Search")
        search_btn.clicked.connect(self.web_search)
        self.web_results = QTextEdit()
        self.web_results.setReadOnly(True)
        layout.addWidget(self.web_input)
        layout.addWidget(search_btn)
        layout.addWidget(self.web_results)
        tab.setLayout(layout)
        self.tabs.addTab(tab, "Web Search")
    def web_search(self):
        query = self.web_input.text().strip()
        if not query:
            return
        try:
            resp = requests.get(f"http://127.0.0.1:8000/search", params={"query": query})
            results = resp.json().get("results", [])
            html = ""
            for idx, r in enumerate(results, 1):
                html += f"<b>{idx}.</b> <a href='{r['href']}'>{r['title']}</a><br>{r['body']}<br><br>"
            self.web_results.setHtml(html)
        except Exception as e:
            self.web_results.setText(f"Error: {e}")
    def init_code_tab(self):
        tab = QWidget()
        layout = QVBoxLayout()
        layout.addWidget(QLabel("<h2>Python Code Execution</h2>"))
        self.code_input = QTextEdit()
        self.code_input.setPlaceholderText("Enter Python code to execute...")
        exec_btn = QPushButton("Run Code")
        exec_btn.clicked.connect(self.run_code)
        self.code_output = QTextEdit()
        self.code_output.setReadOnly(True)
        layout.addWidget(self.code_input)
        layout.addWidget(exec_btn)
        layout.addWidget(QLabel("<b>Output:</b>"))
        layout.addWidget(self.code_output)
        tab.setLayout(layout)
        self.tabs.addTab(tab, "Code Exec")
    def run_code(self):
        code = self.code_input.toPlainText()
        try:
            resp = requests.post(f"{SERVER_URL}/exec", json={"code": code})
            if resp.status_code == 200:
                self.code_output.setText(str(resp.json()["result"]))
            else:
                self.code_output.setText(str(resp.json()))
        except Exception as e:
            self.code_output.setText(f"Error: {e}")
    def init_task_tab(self):
        tab = QWidget()
        layout = QVBoxLayout()
        layout.addWidget(QLabel("<h2>Task Automation</h2>"))
        # Task chaining
        self.chain_input = QTextEdit()
        self.chain_input.setPlaceholderText("Enter one shell command per line for task chaining...")
        chain_btn = QPushButton("Run Task Chain")
        chain_btn.clicked.connect(self.run_task_chain)
        preview_chain_btn = QPushButton("Preview Chain")
        preview_chain_btn.clicked.connect(self.preview_task_chain)
        # Repo cloning
        self.repo_input = QLineEdit()
        self.repo_input.setPlaceholderText("Enter git repo URL to clone...")
        self.req_checkbox = QCheckBox("Install requirements.txt after clone")
        clone_btn = QPushButton("Clone Repo")
        clone_btn.clicked.connect(self.clone_repo)
        preview_clone_btn = QPushButton("Preview Clone Action")
        preview_clone_btn.clicked.connect(self.preview_clone_repo)
        # Output/logs
        self.task_output = QTextEdit()
        self.task_output.setReadOnly(True)
        logs_btn = QPushButton("View Automation Logs")
        logs_btn.clicked.connect(self.view_automation_logs)
        # Layout
        layout.addWidget(QLabel("<b>Task Chain:</b>"))
        layout.addWidget(self.chain_input)
        hbox1 = QHBoxLayout()
        hbox1.addWidget(chain_btn)
        hbox1.addWidget(preview_chain_btn)
        layout.addLayout(hbox1)
        layout.addWidget(QLabel("<b>Repo Cloning:</b>"))
        layout.addWidget(self.repo_input)
        layout.addWidget(self.req_checkbox)
        hbox2 = QHBoxLayout()
        hbox2.addWidget(clone_btn)
        hbox2.addWidget(preview_clone_btn)
        layout.addLayout(hbox2)
        layout.addWidget(QLabel("<b>Output/Logs:</b>"))
        layout.addWidget(self.task_output)
        layout.addWidget(logs_btn)
        tab.setLayout(layout)
        self.tabs.addTab(tab, "Automation")
    def run_task_chain(self):
        cmds = [line.strip() for line in self.chain_input.toPlainText().splitlines() if line.strip()]
        if not cmds:
            self.task_output.setText("No commands entered.")
            return
        # Confirm dangerous actions
        if any("rm " in c or "del " in c or "shutdown" in c for c in cmds):
            ok = QMessageBox.question(self, "Dangerous Action", "This chain contains potentially dangerous commands. Proceed?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if ok != QMessageBox.StandardButton.Yes:
                self.task_output.setText("Aborted by user.")
                return
        try:
            resp = requests.post(f"{SERVER_URL}/automation/chain", json=cmds)
            if resp.status_code == 200:
                results = resp.json().get("results", [])
                out = ""
                for r in results:
                    out += f"$ {r['command']}\nStatus: {r['status']}\n{r['result']}\n---\n"
                self.task_output.setText(out)
            else:
                self.task_output.setText("Error: " + str(resp.text))
        except Exception as e:
            self.task_output.setText(f"Error: {e}")
    def preview_task_chain(self):
        cmds = [line.strip() for line in self.chain_input.toPlainText().splitlines() if line.strip()]
        if not cmds:
            self.task_output.setText("No commands entered.")
            return
        try:
            resp = requests.post(f"{SERVER_URL}/automation/chain?preview=true", json=cmds)
            if resp.status_code == 200:
                preview = resp.json().get("preview", [])
                self.task_output.setText("Preview of actions:\n" + "\n".join(preview))
            else:
                self.task_output.setText("Error: " + str(resp.text))
        except Exception as e:
            self.task_output.setText(f"Error: {e}")
    def clone_repo(self):
        url = self.repo_input.text().strip()
        install_req = self.req_checkbox.isChecked()
        if not url:
            self.task_output.setText("No repo URL entered.")
            return
        # Confirm dangerous action
        if install_req:
            ok = QMessageBox.question(self, "Install Requirements", "Install requirements.txt after cloning? This may run arbitrary code.", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if ok != QMessageBox.StandardButton.Yes:
                self.task_output.setText("Aborted by user.")
                return
        try:
            resp = requests.post(f"{SERVER_URL}/automation/clone_repo", json={"repo_url": url, "install_requirements": install_req})
            if resp.status_code == 200:
                result = resp.json().get("result", "")
                req = resp.json().get("requirements", "")
                self.task_output.setText(f"Clone result:\n{result}\nRequirements install:\n{req}")
            else:
                self.task_output.setText("Error: " + str(resp.text))
        except Exception as e:
            self.task_output.setText(f"Error: {e}")
    def preview_clone_repo(self):
        url = self.repo_input.text().strip()
        install_req = self.req_checkbox.isChecked()
        if not url:
            self.task_output.setText("No repo URL entered.")
            return
        try:
            resp = requests.post(f"{SERVER_URL}/automation/clone_repo?preview=true", json={"repo_url": url, "install_requirements": install_req})
            if resp.status_code == 200:
                preview = resp.json().get("preview", [])
                self.task_output.setText("Preview of actions:\n" + "\n".join(preview))
            else:
                self.task_output.setText("Error: " + str(resp.text))
        except Exception as e:
            self.task_output.setText(f"Error: {e}")
    def view_automation_logs(self):
        try:
            resp = requests.get(f"{SERVER_URL}/automation/logs")
            if resp.status_code == 200:
                logs = resp.json().get("logs", [])
                out = ""
                for entry in logs:
                    out += f"[{entry['timestamp']}] {entry['action']}\nStatus: {entry['status']}\nResult: {entry['result']}\n---\n"
                self.task_output.setText(out)
            else:
                self.task_output.setText("Error: " + str(resp.text))
        except Exception as e:
            self.task_output.setText(f"Error: {e}")
    def add_feedback_buttons(self, query, llm_answer, web_results, rag_results):
        # Only allow one feedback per answer
        if hasattr(self, '_feedback_given') and self._feedback_given:
            return
        self._feedback_given = False
        feedback_widget = QWidget()
        layout = QHBoxLayout()
        layout.setContentsMargins(8, 8, 8, 8)
        up_btn = QPushButton("👍")
        down_btn = QPushButton("👎")
        correction_btn = QPushButton("Suggest Correction")
        label = QLabel("Was this helpful?")
        layout.addWidget(label)
        layout.addWidget(up_btn)
        layout.addWidget(down_btn)
        layout.addWidget(correction_btn)
        feedback_widget.setLayout(layout)
        self.chat_display.insertPlainText("\n")
        self.chat_display.setFocus()
        self.chat_display.append("")
        self.chat_display.viewport().setProperty("feedback_widget", feedback_widget)
        # Connect
        def send_feedback(up):
            self._feedback_given = True
            user_comment = ""
            if not up:
                # Ask for comment
                comment, ok = QInputDialog.getText(self, "Feedback", "How can we improve this answer? (optional)")
                if ok:
                    user_comment = comment
            try:
                requests.post(f"{SERVER_URL}/feedback", json={
                    "query": query,
                    "llm_answer": llm_answer,
                    "web_results": web_results,
                    "rag_results": rag_results,
                    "feedback": "up" if up else "down",
                    "user_comment": user_comment
                }, timeout=10)
                self.statusBar().showMessage("Thank you for your feedback!", 5000)
            except Exception as e:
                self.statusBar().showMessage(f"Feedback error: {e}", 5000)
            up_btn.setEnabled(False)
            down_btn.setEnabled(False)
            correction_btn.setEnabled(False)
            label.setText("Feedback received.")
        def send_correction():
            correction, ok = QInputDialog.getMultiLineText(self, "Suggest Correction", "Enter your correction or improved answer:")
            if ok and correction.strip():
                try:
                    requests.post(f"{SERVER_URL}/feedback/correction", json={
                        "query": query,
                        "llm_answer": llm_answer,
                        "correction": correction.strip(),
                        "web_results": web_results,
                        "rag_results": rag_results
                    }, timeout=10)
                    self.statusBar().showMessage("Correction submitted!", 5000)
                except Exception as e:
                    self.statusBar().showMessage(f"Correction error: {e}", 5000)
        up_btn.clicked.connect(lambda: send_feedback(True))
        down_btn.clicked.connect(lambda: send_feedback(False))
        correction_btn.clicked.connect(send_correction)
        # Show in chat (simulate by appending a line)
        self.chat_display.append("<div style='margin:8px;'><button>👍</button> <button>👎</button> <button>✏️</button> <span style='color:#888'>Was this helpful?</span></div>")

    def add_suggestion_buttons(self, suggestions):
        from PyQt6.QtWidgets import QWidget, QHBoxLayout, QPushButton
        suggestion_widget = QWidget()
        layout = QHBoxLayout()
        layout.setContentsMargins(8, 8, 8, 8)
        for s in suggestions:
            btn = QPushButton(s)
            btn.setStyleSheet("background:#444;color:#fff;border:none;border-radius:4px;padding:4px 8px;margin-right:8px;")
            btn.clicked.connect(lambda _, text=s: self.send_suggestion(text))
            layout.addWidget(btn)
        suggestion_widget.setLayout(layout)
        self.chat_display.append("<div style='margin:8px;'><b>Suggestions:</b></div>")
        self.chat_display.append("")
        self.chat_display.viewport().setProperty("suggestion_widget", suggestion_widget)

    def send_suggestion(self, text):
        self.chat_input.setText(text)
        self.send_chat()

    def sidebar_item_clicked(self, item):
        # Insert the selected topic into the chat input for follow-up
        self.chat_input.setText(item.text())
        self.chat_input.setFocus()

    def add_to_recent_topics(self, user_input, assistant_response):
        topic = user_input.strip()
        if topic and (not self.recent_topics or self.recent_topics[-1] != topic):
            self.recent_topics.append(topic)
            if len(self.recent_topics) > 20:
                self.recent_topics = self.recent_topics[-20:]
            self.sidebar.clear()
            for t in reversed(self.recent_topics):
                self.sidebar.addItem(QListWidgetItem(t))
            self.save_recent_topics()

    def load_preferences(self):
        try:
            resp = requests.get(f"{SERVER_URL}/preferences")
            if resp.status_code == 200:
                return resp.json().get("preferences", {"answer_style": "concise", "tech_depth": "basic", "language": "English"})
        except Exception:
            pass
        return {"answer_style": "concise", "tech_depth": "basic", "language": "English"}

    def save_preferences(self):
        try:
            requests.post(f"{SERVER_URL}/preferences", json={"preferences": self.preferences})
        except Exception:
            pass

    def clear_preferences(self):
        try:
            requests.post(f"{SERVER_URL}/preferences/clear")
            self.preferences = {"answer_style": "concise", "tech_depth": "basic", "language": "English"}
            self.save_preferences()
            self.statusBar().showMessage("Preferences cleared.", 3000)
        except Exception:
            pass

    def sync_recent_topics(self):
        try:
            resp = requests.get(f"{SERVER_URL}/memory/recent_topics")
            if resp.status_code == 200:
                self.recent_topics = resp.json().get("topics", [])
                self.sidebar.clear()
                for t in reversed(self.recent_topics):
                    self.sidebar.addItem(QListWidgetItem(t))
        except Exception:
            pass

    def save_recent_topics(self):
        try:
            requests.post(f"{SERVER_URL}/memory/recent_topics", json={"topics": self.recent_topics})
        except Exception:
            pass

    def clear_recent_topics(self):
        try:
            requests.post(f"{SERVER_URL}/memory/clear_recent_topics")
            self.recent_topics = []
            self.sidebar.clear()
            self.statusBar().showMessage("Recent topics cleared.", 3000)
        except Exception:
            pass

    def init_preferences_tab(self):
        tab = QWidget()
        layout = QVBoxLayout()
        layout.addWidget(QLabel("<h2>Preferences</h2>"))
        # Answer style
        layout.addWidget(QLabel("Answer Style:"))
        self.style_combo = QComboBox()
        self.style_combo.addItems(["concise", "detailed"])
        self.style_combo.setCurrentText(self.preferences.get("answer_style", "concise"))
        self.style_combo.currentTextChanged.connect(lambda v: self.set_pref("answer_style", v))
        layout.addWidget(self.style_combo)
        # Technical depth
        layout.addWidget(QLabel("Technical Depth:"))
        self.depth_combo = QComboBox()
        self.depth_combo.addItems(["basic", "advanced"])
        self.depth_combo.setCurrentText(self.preferences.get("tech_depth", "basic"))
        self.depth_combo.currentTextChanged.connect(lambda v: self.set_pref("tech_depth", v))
        layout.addWidget(self.depth_combo)
        # Language
        layout.addWidget(QLabel("Language:"))
        self.lang_combo = QComboBox()
        self.lang_combo.addItems(["English", "Urdu", "Transliteration"])
        self.lang_combo.setCurrentText(self.preferences.get("language", "English"))
        self.lang_combo.currentTextChanged.connect(lambda v: self.set_pref("language", v))
        layout.addWidget(self.lang_combo)
        # Clear buttons
        clear_prefs_btn = QPushButton("Clear Preferences")
        clear_prefs_btn.clicked.connect(self.clear_preferences)
        clear_topics_btn = QPushButton("Clear Recent Topics")
        clear_topics_btn.clicked.connect(self.clear_recent_topics)
        layout.addWidget(clear_prefs_btn)
        layout.addWidget(clear_topics_btn)
        tab.setLayout(layout)
        self.tabs.addTab(tab, "Preferences")

    def set_pref(self, key, value):
        self.preferences[key] = value
        self.save_preferences()

    def voice_input(self):
        if not STT_AVAILABLE:
            QMessageBox.warning(self, "Voice Input", "Speech-to-text is not available. Please install vosk and pyaudio.")
            return
        try:
            lang = self.preferences.get("language", "English")
            if lang == "Urdu":
                model_path = "vosk-model-small-ur-0.22"  # Path to Urdu model
            else:
                model_path = "vosk-model-small-en-us-0.15"  # Path to English model
            if not os.path.exists(model_path):
                QMessageBox.warning(self, "Voice Input", f"Vosk model not found: {model_path}")
                return
            model = Model(model_path)
            rec = KaldiRecognizer(model, 16000)
            p = pyaudio.PyAudio()
            stream = p.open(format=pyaudio.paInt16, channels=1, rate=16000, input=True, frames_per_buffer=8000)
            stream.start_stream()
            self.loading_label.setText("Listening...")
            import time
            result = ""
            start = time.time()
            while True:
                data = stream.read(4000, exception_on_overflow=False)
                if rec.AcceptWaveform(data):
                    res = rec.Result()
                    import json as _json
                    text = _json.loads(res).get("text", "")
                    if text:
                        result += text + " "
                        break
                if time.time() - start > 8:
                    break
            stream.stop_stream()
            stream.close()
            p.terminate()
            self.loading_label.setText("")
            if result.strip():
                if lang == "Transliteration":
                    result = self.transliterate_to_urdu(result.strip())
                self.chat_input.setText(result.strip())
                self.send_chat()
            else:
                QMessageBox.information(self, "Voice Input", "No speech detected.")
        except Exception as e:
            self.loading_label.setText("")
            QMessageBox.critical(self, "Voice Input Error", str(e))
    def speak_last_answer(self):
        if not TTS_AVAILABLE:
            QMessageBox.warning(self, "Text-to-Speech", "pyttsx3 is not available. Please install pyttsx3.")
            return
        try:
            last_answer = ""
            for msg in reversed(self.chat_history):
                if msg["role"] == "assistant":
                    last_answer = msg["content"]
                    break
            if not last_answer:
                QMessageBox.information(self, "Text-to-Speech", "No assistant answer to read.")
                return
            lang = self.preferences.get("language", "English")
            engine = pyttsx3.init()
            voices = engine.getProperty('voices')
            if lang == "Urdu":
                # Try to select an Urdu voice if available
                for v in voices:
                    if "urdu" in v.name.lower() or "urdu" in v.languages:
                        engine.setProperty('voice', v.id)
                        break
            elif lang == "Transliteration":
                last_answer = self.transliterate_to_urdu(last_answer)
            # Otherwise use default voice
            engine.say(last_answer)
            engine.runAndWait()
        except Exception as e:
            QMessageBox.critical(self, "Text-to-Speech Error", str(e))
    def transliterate_to_urdu(self, text):
        # Simple placeholder for transliteration logic
        # In production, use a proper transliteration library
        return text.replace('a', 'ا').replace('i', 'ی').replace('u', 'و').replace('e', 'ے').replace('o', 'و')

    def init_plugins_tab(self):
        tab = QWidget()
        layout = QVBoxLayout()
        self.plugin_list = QListWidget()
        refresh_btn = QPushButton("Refresh Plugin List")
        refresh_btn.clicked.connect(self.refresh_plugins)
        upload_btn = QPushButton("Upload Plugin")
        upload_btn.clicked.connect(self.upload_plugin)
        delete_btn = QPushButton("Delete Selected Plugin")
        delete_btn.clicked.connect(self.delete_plugin)
        run_btn = QPushButton("Run Selected Plugin")
        run_btn.clicked.connect(self.run_plugin)
        self.plugin_output = QTextEdit()
        self.plugin_output.setReadOnly(True)
        layout.addWidget(QLabel("<h2>Plugin Management</h2>"))
        layout.addWidget(self.plugin_list)
        hbox = QHBoxLayout()
        hbox.addWidget(refresh_btn)
        hbox.addWidget(upload_btn)
        hbox.addWidget(delete_btn)
        hbox.addWidget(run_btn)
        layout.addLayout(hbox)
        layout.addWidget(QLabel("Output:"))
        layout.addWidget(self.plugin_output)
        tab.setLayout(layout)
        self.tabs.addTab(tab, "Plugins")
        self.refresh_plugins()

    def refresh_plugins(self):
        try:
            resp = requests.get(f"{SERVER_URL}/plugins")
            if resp.status_code == 200:
                plugins = resp.json().get("plugins", [])
                self.plugin_list.clear()
                for p in plugins:
                    self.plugin_list.addItem(p)
            else:
                self.plugin_output.setText("Error loading plugins: " + str(resp.text))
        except Exception as e:
            self.plugin_output.setText(f"Error: {e}")

    def upload_plugin(self):
        fname, _ = QFileDialog.getOpenFileName(self, "Select Python Plugin", "", "Python Files (*.py)")
        if fname:
            try:
                with open(fname, "rb") as f:
                    files = {"file": (os.path.basename(fname), f, "text/x-python")}
                    resp = requests.post(f"{SERVER_URL}/plugin/upload", files=files)
                if resp.status_code == 200:
                    self.plugin_output.setText(f"Uploaded: {os.path.basename(fname)}")
                    self.refresh_plugins()
                else:
                    self.plugin_output.setText("Upload failed: " + str(resp.text))
            except Exception as e:
                self.plugin_output.setText(f"Error: {e}")

    def delete_plugin(self):
        item = self.plugin_list.currentItem()
        if item:
            plugin = item.text()
            try:
                resp = requests.delete(f"{SERVER_URL}/plugin/delete/{plugin}")
                if resp.status_code == 200:
                    self.plugin_output.setText(f"Deleted: {plugin}")
                    self.refresh_plugins()
                else:
                    self.plugin_output.setText("Delete failed: " + str(resp.text))
            except Exception as e:
                self.plugin_output.setText(f"Error: {e}")

    def run_plugin(self):
        item = self.plugin_list.currentItem()
        if item:
            plugin = item.text()
            user_input, ok = QInputDialog.getText(self, "Run Plugin", "Input for plugin:")
            if ok:
                try:
                    resp = requests.post(f"{SERVER_URL}/plugin/run", json={"plugin": plugin, "input": user_input})
                    if resp.status_code == 200:
                        out = resp.json().get("output", "")
                        err = resp.json().get("error", "")
                        self.plugin_output.setText(f"Output:\n{out}\nError:\n{err}")
                    else:
                        self.plugin_output.setText("Run failed: " + str(resp.text))
                except Exception as e:
                    self.plugin_output.setText(f"Error: {e}")

    def init_admin_tab(self):
        tab = QWidget()
        layout = QVBoxLayout()
        self.log_display = QTextEdit()
        self.log_display.setReadOnly(True)
        refresh_log_btn = QPushButton("Refresh Logs")
        refresh_log_btn.clicked.connect(self.refresh_logs)
        restart_btn = QPushButton("Restart Server")
        restart_btn.clicked.connect(self.restart_server_backend)
        export_logs_btn = QPushButton("Export Logs")
        export_logs_btn.clicked.connect(self.export_logs)
        export_feedback_btn = QPushButton("Export Feedback")
        export_feedback_btn.clicked.connect(self.export_feedback)
        export_knowledge_btn = QPushButton("Export Knowledge")
        export_knowledge_btn.clicked.connect(self.export_knowledge)
        layout.addWidget(QLabel("<h2>Admin Controls</h2>"))
        layout.addWidget(self.log_display)
        hbox = QHBoxLayout()
        hbox.addWidget(refresh_log_btn)
        hbox.addWidget(restart_btn)
        hbox.addWidget(export_logs_btn)
        hbox.addWidget(export_feedback_btn)
        hbox.addWidget(export_knowledge_btn)
        layout.addLayout(hbox)
        tab.setLayout(layout)
        self.tabs.addTab(tab, "Admin")
        self.refresh_logs()

    def refresh_logs(self):
        try:
            resp = requests.get(f"{SERVER_URL}/logs")
            if resp.status_code == 200:
                self.log_display.setText(resp.json().get("log", ""))
            else:
                self.log_display.setText("Error loading logs: " + str(resp.text))
        except Exception as e:
            self.log_display.setText(f"Error: {e}")

    def restart_server_backend(self):
        try:
            resp = requests.post(f"{SERVER_URL}/restart")
            if resp.status_code == 200:
                QMessageBox.information(self, "Restart", "Server is restarting. Please wait a few seconds and reconnect.")
            else:
                QMessageBox.warning(self, "Restart Failed", str(resp.text))
        except Exception as e:
            QMessageBox.warning(self, "Restart Failed", str(e))

    def export_logs(self):
        try:
            resp = requests.get(f"{SERVER_URL}/export/logs")
            if resp.status_code == 200:
                logs = resp.json()
                out = ""
                for fname, content in logs.items():
                    out += f"--- {fname} ---\n{content}\n\n"
                self.log_display.setText(out)
            else:
                self.log_display.setText("Error exporting logs: " + str(resp.text))
        except Exception as e:
            self.log_display.setText(f"Error: {e}")

    def export_feedback(self):
        try:
            resp = requests.get(f"{SERVER_URL}/export/feedback")
            if resp.status_code == 200:
                feedbacks = resp.json().get("feedback", [])
                out = json.dumps(feedbacks, indent=2, ensure_ascii=False)
                self.log_display.setText(out)
            else:
                self.log_display.setText("Error exporting feedback: " + str(resp.text))
        except Exception as e:
            self.log_display.setText(f"Error: {e}")

    def export_knowledge(self):
        try:
            resp = requests.get(f"{SERVER_URL}/export/knowledge")
            if resp.status_code == 200:
                knowledge = resp.json()
                out = json.dumps(knowledge, indent=2, ensure_ascii=False)
                self.log_display.setText(out)
            else:
                self.log_display.setText("Error exporting knowledge: " + str(resp.text))
        except Exception as e:
            self.log_display.setText(f"Error: {e}")

    def init_dashboard_tab(self):
        tab = QWidget()
        layout = QVBoxLayout()
        layout.addWidget(QLabel("<h2>Analytics Dashboard</h2>"))
        from pyqtgraph import PlotWidget
        self.plot_widget = PlotWidget()
        layout.addWidget(self.plot_widget)
        self.dashboard_stats = QTextEdit()
        self.dashboard_stats.setReadOnly(True)
        layout.addWidget(self.dashboard_stats)
        refresh_btn = QPushButton("Refresh Analytics")
        refresh_btn.clicked.connect(self.refresh_dashboard)
        layout.addWidget(refresh_btn)
        # Web scraping UI
        self.scrape_input = QLineEdit()
        self.scrape_input.setPlaceholderText("Enter URL to scrape...")
        scrape_btn = QPushButton("Scrape Website")
        scrape_btn.clicked.connect(self.run_scrape)
        self.scrape_output = QTextEdit()
        self.scrape_output.setReadOnly(True)
        layout.addWidget(QLabel("<b>Web Scraping</b>"))
        layout.addWidget(self.scrape_input)
        layout.addWidget(scrape_btn)
        layout.addWidget(self.scrape_output)
        # Pentesting UI
        self.pentest_input = QLineEdit()
        self.pentest_input.setPlaceholderText("Enter target (IP or URL) for pentest...")
        self.pentest_tool = QComboBox()
        self.pentest_tool.addItems(["nmap", "sqlmap"])
        pentest_btn = QPushButton("Run Pentest")
        pentest_btn.clicked.connect(self.run_pentest)
        self.pentest_output = QTextEdit()
        self.pentest_output.setReadOnly(True)
        layout.addWidget(QLabel("<b>Pentesting</b>"))
        layout.addWidget(self.pentest_input)
        layout.addWidget(self.pentest_tool)
        layout.addWidget(pentest_btn)
        layout.addWidget(self.pentest_output)
        tab.setLayout(layout)
        self.tabs.insertTab(1, tab, "Dashboard")
        self.refresh_dashboard()

    def refresh_dashboard(self):
        import requests
        try:
            stats = requests.get(f"{SERVER_URL}/analytics").json()
            mem_stats = requests.get(f"{SERVER_URL}/memory/usage").json()
            self.dashboard_stats.setText(
                f"Documents: {stats['docs']}\nRepos: {stats['repos']}\nTasks: {stats['tasks']}\nWeb Scrapes: {stats['scrapes']}\nPentest Runs: {stats['pentests']}\nRAM: {mem_stats['ram']}%\nCPU: {mem_stats['cpu']}%"
            )
            # Example plot: RAM usage
            self.plot_widget.clear()
            self.plot_widget.plot([mem_stats['ram'], mem_stats['cpu']], pen='g', symbol='o')
        except Exception as e:
            self.dashboard_stats.setText(f"Error: {e}")

    def run_scrape(self):
        import requests
        url = self.scrape_input.text().strip()
        if not url:
            self.scrape_output.setText("No URL entered.")
            return
        try:
            resp = requests.post(f"{SERVER_URL}/scrape", json={"url": url})
            if resp.status_code == 200:
                self.scrape_output.setText(resp.json().get("text", ""))
                self.refresh_dashboard()
            else:
                self.scrape_output.setText("Error: " + str(resp.text))
        except Exception as e:
            self.scrape_output.setText(f"Error: {e}")

    def run_pentest(self):
        import requests
        target = self.pentest_input.text().strip()
        tool = self.pentest_tool.currentText()
        if not target:
            self.pentest_output.setText("No target entered.")
            return
        try:
            resp = requests.post(f"{SERVER_URL}/pentest", json={"target": target, "tool": tool})
            if resp.status_code == 200:
                self.pentest_output.setText(resp.json().get("result", ""))
                self.refresh_dashboard()
            else:
                self.pentest_output.setText("Error: " + str(resp.text))
        except Exception as e:
            self.pentest_output.setText(f"Error: {e}")

    def start_data_collection(self):
        def collect_data():
            while True:
                try:
                    response = requests.get('http://localhost:8000/training/status')
                    if response.status_code == 200:
                        data = response.json()
                        self.data_queue.put(data)
                except:
                    pass
                time.sleep(1)
        
        thread = threading.Thread(target=collect_data, daemon=True)
        thread.start()

    def update_ui(self):
        try:
            while not self.data_queue.empty():
                data = self.data_queue.get_nowait()
                
                # Update training data
                self.training_data = data.get('training_data', {})
                self.category_data = data.get('categories', {})
                self.recent_activities = data.get('recent_activities', [])
                
                # Update stats
                total_data = sum(self.training_data.values())
                active_categories = len(self.category_data)
                training_speed = data.get('training_speed', 0)
                
                self.total_data_card.findChild(QLabel, "", Qt.FindChildOption.FindChildrenRecursively)[1].setText(str(total_data))
                self.active_categories_card.findChild(QLabel, "", Qt.FindChildOption.FindChildrenRecursively)[1].setText(str(active_categories))
                self.training_speed_card.findChild(QLabel, "", Qt.FindChildOption.FindChildrenRecursively)[1].setText(f"{training_speed}/s")
                
                # Update category grid
                self.update_category_grid()
                
                # Update activity list
                self.update_activity_list()
                
        except queue.Empty:
            pass

    def update_category_grid(self):
        # Clear existing widgets
        while self.category_grid.count():
            item = self.category_grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # Add new category cards
        row, col = 0, 0
        for category, count in self.category_data.items():
            card = CategoryCard(category, count)
            self.category_grid.addWidget(card, row, col)
            col += 1
            if col > 2:  # 3 cards per row
                col = 0
                row += 1

    def update_activity_list(self):
        self.activity_list.clear()
        for activity in self.recent_activities:
            self.activity_list.append(f"• {activity}")

    def closeEvent(self, event):
        """Handle window close event."""
        # Clean up resources
        self.update_timer.stop()
        event.accept()

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