import sys
import requests
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QLineEdit, QPushButton, QLabel, QTabWidget, QFileDialog, QMessageBox, QProgressBar, QFrame, QCheckBox, QInputDialog, QListWidget, QListWidgetItem, QSplitter, QComboBox
)
from PyQt6.QtGui import QFont, QColor, QTextCharFormat, QTextCursor
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
import markdown2
import json
import subprocess
import os

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

class MeAIApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.setMinimumSize(1000, 750)
        self.setStyleSheet(DARK_STYLE)
        self.recent_topics = []  # Track recent topics/questions
        self.tabs = QTabWidget()
        # Add a sidebar for recent topics
        self.splitter = QSplitter()
        self.sidebar = QListWidget()
        self.sidebar.setMaximumWidth(260)
        self.sidebar.setStyleSheet("background:#23272a;color:#e8eaed;border-right:1px solid #444;")
        self.sidebar.itemClicked.connect(self.sidebar_item_clicked)
        self.splitter.addWidget(self.sidebar)
        self.splitter.addWidget(self.tabs)
        self.setCentralWidget(self.splitter)
        self.cyber_mode = False
        self.preferences = self.load_preferences()
        self.init_chat_tab()
        self.init_knowledge_tab()
        self.init_web_tab()
        self.init_code_tab()
        self.init_task_tab()
        self.init_preferences_tab()
        self.statusBar().showMessage(BRAND)
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self.poll_status)
        self.status_timer.start(2000)
        self.last_assistant_bubble_pos = None  # Track the last assistant bubble position
    def poll_status(self):
        try:
            resp = requests.get(f"{SERVER_URL}/status", timeout=2)
            status = resp.json()
            msg = f"RAM: {status['ram_usage']}% | CPU: {status['cpu_usage']}% | Processing: {'Yes' if status['processing'] else 'No'}"
            if status.get('last_error'):
                msg += f" | Last Error: {status['last_error']}"
            self.statusBar().showMessage(f"{BRAND} | {msg}")
        except Exception:
            self.statusBar().showMessage(f"{BRAND} | [Server Offline]")
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
    def send_chat(self):
        user_input = self.chat_input.text().strip()
        if not user_input:
            return
        self.add_chat_bubble(user_input, user=True)
        self.chat_history.append({"role": "user", "content": user_input})
        self.chat_input.clear()
        self.loading_label.setText("Thinking...")
        self.last_assistant_bubble_pos = None  # Reset for new response
        # Add preferences to the request
        prefs = self.preferences.copy()
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
        self.task_input = QLineEdit()
        self.task_input.setPlaceholderText("Enter a shell command to run...")
        run_btn = QPushButton("Run Command")
        run_btn.clicked.connect(self.run_task)
        self.task_output = QTextEdit()
        self.task_output.setReadOnly(True)
        layout.addWidget(self.task_input)
        layout.addWidget(run_btn)
        layout.addWidget(QLabel("<b>Output:</b>"))
        layout.addWidget(self.task_output)
        tab.setLayout(layout)
        self.tabs.addTab(tab, "Automation")
    def run_task(self):
        cmd = self.task_input.text().strip()
        try:
            resp = requests.post(f"{SERVER_URL}/shell", json={"cmd": cmd})
            if resp.status_code == 200:
                self.task_output.setText(str(resp.json()["result"]))
            else:
                self.task_output.setText(str(resp.json()))
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
        label = QLabel("Was this helpful?")
        layout.addWidget(label)
        layout.addWidget(up_btn)
        layout.addWidget(down_btn)
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
            label.setText("Feedback received.")
        up_btn.clicked.connect(lambda: send_feedback(True))
        down_btn.clicked.connect(lambda: send_feedback(False))
        # Show in chat (simulate by appending a line)
        self.chat_display.append("<div style='margin:8px;'><button>👍</button> <button>👎</button> <span style='color:#888'>Was this helpful?</span></div>")

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
        # Add user question and assistant answer as a topic
        topic = user_input.strip()
        if topic and (not self.recent_topics or self.recent_topics[-1] != topic):
            self.recent_topics.append(topic)
            if len(self.recent_topics) > 20:
                self.recent_topics = self.recent_topics[-20:]
            self.sidebar.clear()
            for t in reversed(self.recent_topics):
                self.sidebar.addItem(QListWidgetItem(t))

    def load_preferences(self):
        try:
            with open("meai_prefs.json", "r") as f:
                return json.load(f)
        except Exception:
            return {"answer_style": "concise", "tech_depth": "basic", "language": "English"}

    def save_preferences(self):
        try:
            with open("meai_prefs.json", "w") as f:
                json.dump(self.preferences, f)
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
        self.lang_combo.addItems(["English", "Other"])
        self.lang_combo.setCurrentText(self.preferences.get("language", "English"))
        self.lang_combo.currentTextChanged.connect(lambda v: self.set_pref("language", v))
        layout.addWidget(self.lang_combo)
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
            model = Model("vosk-model-small-en-us-0.15")  # Path to Vosk model
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
            engine = pyttsx3.init()
            engine.say(last_answer)
            engine.runAndWait()
        except Exception as e:
            QMessageBox.critical(self, "Text-to-Speech Error", str(e))

def main():
    app = QApplication(sys.argv)
    window = MeAIApp()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main() 