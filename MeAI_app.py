import sys
import requests
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QLineEdit, QPushButton, QLabel, QTabWidget, QFileDialog, QMessageBox, QProgressBar, QFrame, QCheckBox
)
from PyQt6.QtGui import QFont, QColor, QTextCharFormat, QTextCursor
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
import markdown2

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
    def run(self):
        try:
            with requests.post(
                f"{SERVER_URL}/chat/stream",
                json={"messages": self.history, "query": self.user_input, "use_rag": True, "cyber_mode": self.cyber_mode},
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
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)
        self.cyber_mode = False
        self.init_chat_tab()
        self.init_knowledge_tab()
        self.init_web_tab()
        self.init_code_tab()
        self.init_task_tab()
        self.statusBar().showMessage(BRAND)
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self.poll_status)
        self.status_timer.start(2000)
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
        # Try streaming worker first
        self.streaming_worker = StreamingChatWorker(self.chat_history, user_input, cyber_mode=self.cyber_mode)
        self.streaming_worker.partial_signal.connect(self.display_partial_response)
        self.streaming_worker.done_signal.connect(self.display_chat_response)
        self.streaming_worker.error_signal.connect(self.fallback_to_sync_worker)
        self.streaming_worker.start()
    def display_partial_response(self, partial):
        # Show partial output in the chat window (replace last assistant bubble)
        if self.chat_display.toPlainText().endswith("[thinking...]") or not self.chat_display.toPlainText().endswith("MeAI:"):
            # Add a new bubble if not present
            self.add_chat_bubble("[thinking...]", user=False)
        # Remove last assistant bubble and add updated one
        cursor = self.chat_display.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.chat_display.moveCursor(QTextCursor.MoveOperation.End)
        # Remove last bubble (hack: clear and re-add all except last, then add updated)
        # For simplicity, just append for now
        self.chat_display.append("")
        self.chat_display.append(f"<div style='background:#23272a;padding:10px;border-radius:10px;margin:8px;max-width:70%;float:left;color:#f28b82;'><span style='font-weight:bold'>MeAI:</span><br>{markdown2.markdown(partial)}</div><div style='clear:both'></div>")
        self.loading_label.setText("Thinking...")
    def fallback_to_sync_worker(self, error):
        # If streaming fails, fallback to old worker
        self.worker = ChatWorker(self.chat_history, self.chat_history[-1]["content"], cyber_mode=self.cyber_mode)
        self.worker.response_signal.connect(self.display_chat_response)
        self.worker.error_signal.connect(self.display_chat_error)
        self.worker.start()
    def display_chat_response(self, response):
        self.chat_history.append({"role": "assistant", "content": response})
        self.add_chat_bubble(response, user=False)
        self.loading_label.setText("")
    def display_chat_error(self, error):
        self.loading_label.setText("")
        self.show_error_dialog(error)
    def add_chat_bubble(self, text, user=True):
        html = markdown2.markdown(text)
        color = "#8ab4f8" if user else "#f28b82"
        align = "right" if user else "left"
        bubble = f"<div style='background:#23272a;padding:10px;border-radius:10px;margin:8px;max-width:70%;float:{align};color:{color};'><span style='font-weight:bold'>{'You' if user else 'MeAI'}:</span><br>{html}</div><div style='clear:both'></div>"
        self.chat_display.append(bubble)
    def clear_chat(self):
        self.chat_display.clear()
        self.chat_history = [
            {"role": "system", "content": "You are a helpful, knowledgeable AI assistant. Answer as helpfully as possible."}
        ]
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
        msg.exec()
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

def main():
    app = QApplication(sys.argv)
    window = MeAIApp()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main() 