from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, 
                            QPushButton, QLabel, QScrollArea, QFrame, QSizePolicy, QProgressBar)
from PyQt6.QtCore import Qt, pyqtSignal, QUrl, QVariant, QTimer, QObject
from PyQt6.QtGui import QFont, QTextCursor, QTextDocument
from components.ui.base_components import ModernButton
from components.utils.workers import ChatWorker, StreamingChatWorker
from components.utils.constants import DARK_MODE, SERVER_URL, USER_ID
from pymongo import MongoClient
import markdown2
import logging
import requests

logger = logging.getLogger(__name__)

class BouncingDotsLoader(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.label = QLabel("Thinking", self)
        self.label.setStyleSheet("color: #aaa; font-style: italic; font-size: 16px;")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.addWidget(self.label)
        self.dots = 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.animate)
        self.timer.start(400)
        self.setStyleSheet("background: transparent; border: none;")
    def animate(self):
        self.dots = (self.dots + 1) % 4
        self.label.setText("Thinking" + "." * self.dots)
    def stop(self):
        self.timer.stop()

class ChatTab(QWidget):
    message_sent = pyqtSignal(str)
    status_changed = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.chat_history = []
        self.current_worker = None
        try:
            self.client = MongoClient('mongodb://localhost:27017/')
            self.db = self.client['meai']
            self.chat_collection = self.db['chat_history']
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            self.db = None
            self.chat_collection = None
        # NOTE: Always check self.db and self.chat_collection for None before use, as MongoDB may be unavailable.
        self.setup_ui()
        # Load chat history after UI setup
        QTimer.singleShot(100, self.load_chat_history)
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Status label
        self.status_label = QLabel("Idle")
        self.status_label.setStyleSheet(f"color: {DARK_MODE['accent']}; font-weight: bold;")
        layout.addWidget(self.status_label)
        
        # Chat display area (refactored)
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet(f"background-color: {DARK_MODE['background']}; border: 1px solid {DARK_MODE['border']}; border-radius: 5px;")
        self.chat_container = QWidget()
        self.chat_layout = QVBoxLayout(self.chat_container)
        self.chat_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.scroll_area.setWidget(self.chat_container)
        layout.addWidget(self.scroll_area, stretch=1)
        
        # Input area
        input_layout = QHBoxLayout()
        
        self.input_field = QTextEdit()
        self.input_field.setPlaceholderText("Type your message here...")
        self.input_field.setMaximumHeight(100)
        self.input_field.setStyleSheet(f"""
            QTextEdit {{
                background-color: {DARK_MODE['secondary']};
                color: {DARK_MODE['text']};
                border: 1px solid {DARK_MODE['border']};
                border-radius: 5px;
                padding: 10px;
            }}
        """)
        
        self.send_button = ModernButton("Send")
        self.send_button.clicked.connect(self.send_message)
        
        input_layout.addWidget(self.input_field)
        input_layout.addWidget(self.send_button)
        
        # Add widgets to main layout
        layout.addLayout(input_layout)
        
    def send_message(self):
        message = self.input_field.toPlainText().strip()
        if not message:
            print("[ChatTab] No message to send.")
            return
        print(f"[ChatTab] Sending message: {message}")
        self.input_field.clear()
        self.add_chat_bubble(message, user=True)
        self.message_sent.emit(message)
        # Show animated bouncing dots loader as a bubble
        self.loader_bubble = BouncingDotsLoader()
        self.chat_layout.addWidget(self.loader_bubble)
        # Calculate and display estimated_time immediately
        estimated_time = max(2, min(10, len(message.split()) / 8))
        progress = QProgressBar()
        progress.setMaximum(100)
        progress.setValue(0)
        progress.setTextVisible(True)
        progress.setFormat("Estimated: %.1fs" % estimated_time)
        self.chat_layout.addWidget(progress)
        # Animate the progress bar
        def update_progress(val=0):
            if val <= 100:
                progress.setValue(val)
                QTimer.singleShot(int(estimated_time * 10), lambda: update_progress(val+10))
            else:
                progress.setValue(100)
        update_progress(0)
        QTimer.singleShot(100, lambda: self.scroll_area.verticalScrollBar().setValue(self.scroll_area.verticalScrollBar().maximum()))
        self.status_label.setText("Thinking...")
        self.status_changed.emit("Thinking...")
        # Start streaming worker
        self.current_worker = StreamingChatWorker(self.chat_history, message)
        self.current_worker.partial_signal.connect(self.display_partial_response)
        self.current_worker.done_signal.connect(self.display_chat_response)
        self.current_worker.error_signal.connect(self.display_chat_error)
        self.current_worker.start()
        print("[ChatTab] Started StreamingChatWorker.")
        
    def add_chat_bubble(self, text, user=True, label=None, suggestions=None, from_cache=False, estimated_time=None):
        # Do not add a bubble for empty or whitespace-only text
        if not text or not str(text).strip():
            print(f"[ChatTab] Skipping empty bubble: user={user} label={label}")
            logger.info(f"Skipping empty bubble: user={user} label={label}")
            return
        if user:
            self.chat_history.append({"role": "user", "content": text})
        else:
            self.chat_history.append({"role": "assistant", "content": text})
        # Create bubble
        bubble = QFrame()
        bubble.setFrameShape(QFrame.Shape.StyledPanel)
        bubble.setFrameShadow(QFrame.Shadow.Raised)
        bubble.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        # Style based on user/assistant
        if user:
            bubble.setStyleSheet(f"""
                QFrame {{
                    background-color: {DARK_MODE['accent']};
                    border-radius: 10px;
                    padding: 10px;
                    margin: 5px;
                }}
            """)
        else:
            bubble.setStyleSheet(f"""
                QFrame {{
                    background-color: {DARK_MODE['secondary']};
                    border-radius: 10px;
                    padding: 10px;
                    margin: 5px;
                }}
            """)
        bubble_layout = QVBoxLayout(bubble)
        # Add label if provided
        if label:
            label_widget = QLabel(label)
            label_widget.setStyleSheet(f"color: {DARK_MODE['text']}; font-weight: bold;")
            bubble_layout.addWidget(label_widget)
        # Add message text as QLabel (not QTextEdit)
        message_label = QLabel()
        message_label.setTextFormat(Qt.TextFormat.RichText)
        message_label.setWordWrap(True)
        message_label.setText(markdown2.markdown(text))
        message_label.setStyleSheet("""
            QLabel {
                background: transparent;
                border: none;
                color: white;
            }
        """)
        bubble_layout.addWidget(message_label)
        # Add cache/live indicator
        if not user and from_cache is not None:
            cache_label = QLabel("<i>From cache</i>" if from_cache else "<i>Generated live</i>")
            cache_label.setStyleSheet("color: #7ec699; font-size: 11px; margin-top: 2px;")
            bubble_layout.addWidget(cache_label)
        # Add progress bar if not from cache (always show, use default if needed)
        if not user and not from_cache:
            if estimated_time is None:
                estimated_time = 5.0
            progress = QProgressBar()
            progress.setMaximum(100)
            progress.setValue(0)
            progress.setTextVisible(True)
            progress.setFormat("Estimated: %.1fs" % estimated_time)
            bubble_layout.addWidget(progress)
            # Animate the progress bar
            def update_progress(val=0):
                if val <= 100:
                    progress.setValue(val)
                    QTimer.singleShot(int(estimated_time * 10), lambda: update_progress(val+10))
                else:
                    progress.setValue(100)
            update_progress(0)
        # Add suggestions if provided
        if suggestions:
            suggestions_layout = QHBoxLayout()
            for suggestion in suggestions:
                suggestion_btn = ModernButton(suggestion)
                suggestion_btn.clicked.connect(lambda s=suggestion: self.handle_suggestion(s))
                suggestions_layout.addWidget(suggestion_btn)
            bubble_layout.addLayout(suggestions_layout)
        # Add bubble to chat layout
        self.chat_layout.addWidget(bubble)
        # Scroll to bottom
        QTimer.singleShot(100, lambda: self.scroll_area.verticalScrollBar().setValue(self.scroll_area.verticalScrollBar().maximum()))
        print(f"[ChatTab] Added chat bubble: {'user' if user else 'assistant'} | label: {label} | text: {text[:60]} | from_cache: {from_cache} | estimated_time: {estimated_time}")
        logger.info(f"Added chat bubble: {'user' if user else 'assistant'} | label: {label} | text: {text[:60]} | from_cache: {from_cache} | estimated_time: {estimated_time}")
        
    def remove_loader_bubble(self):
        # Remove the loader bubble if it exists
        if hasattr(self, 'loader_bubble') and self.loader_bubble:
            self.loader_bubble.setParent(None)
            self.loader_bubble.deleteLater()
            self.loader_bubble = None
            print("[ChatTab] Removed loader bubble.")

    def display_partial_response(self, partial):
        print(f"[ChatTab] Displaying partial response: {repr(partial)}")
        logger.info(f"Displaying partial response: {repr(partial)}")
        # Remove loader bubble on first partial response
        self.remove_loader_bubble()
        # Update the last assistant message with the partial response
        if self.chat_history and self.chat_history[-1]["role"] == "assistant":
            self.chat_history[-1]["content"] += partial
            # Update the last assistant bubble widget (QLabel)
            idx = self.chat_layout.count() - 1
            if idx >= 0:
                bubble = self.chat_layout.itemAt(idx).widget()
                if bubble:
                    for i in range(bubble.layout().count()):
                        w = bubble.layout().itemAt(i).widget()
                        if isinstance(w, QLabel) and (not w.text() or w.text() == markdown2.markdown(self.chat_history[-1]["content"][:-len(partial)])):
                            w.setText(markdown2.markdown(self.chat_history[-1]["content"]))
                            break
        else:
            self.add_chat_bubble(partial, user=False, label="Preview")
        self.status_label.setText("Thinking...")
        self.status_changed.emit("Thinking...")
        
    def display_chat_response(self, response):
        print(f"[ChatTab] Displaying final response: {repr(response)}")
        logger.info(f"Displaying final response: {repr(response)}")
        # Final update of the assistant's message
        if self.chat_history and self.chat_history[-1]["role"] == "assistant":
            self.chat_history[-1]["content"] = response
            idx = self.chat_layout.count() - 1
            if idx >= 0:
                bubble = self.chat_layout.itemAt(idx).widget()
                if bubble:
                    for i in range(bubble.layout().count()):
                        w = bubble.layout().itemAt(i).widget()
                        if isinstance(w, QLabel):
                            w.setText(markdown2.markdown(response))
                            break
        self.status_label.setText("Idle")
        self.status_changed.emit("Idle")
        
    def display_chat_error(self, error):
        error_msg = f"Error: {error}"
        print(f"[ChatTab] Displaying error: {error_msg}")
        logger.error(error_msg)
        # Show the full error message in the chat bubble
        self.add_chat_bubble(error_msg, user=False, label="Error")
        self.status_label.setText("Idle")
        self.status_changed.emit("Idle")
        
    def handle_suggestion(self, suggestion):
        self.input_field.setText(suggestion)
        self.send_message()
        
    def clear_chat(self):
        self.chat_history = []
        # Remove all widgets from chat_layout
        while self.chat_layout.count():
            item = self.chat_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        self.status_label.setText("Idle")
        print("[ChatTab] Cleared chat history and UI.")
        logger.info("Cleared chat history and UI.")
        
    def load_chat_history(self):
        print("[ChatTab] Loading chat history from backend...")
        logger.info("Loading chat history from backend...")
        try:
            resp = requests.get(f"{SERVER_URL}/memory/chat_history/{USER_ID}", timeout=10)
            logger.debug(f"Chat history response: {resp.status_code} {resp.text}")
            if resp.status_code == 200:
                data = resp.json()
                history = data.get("history", [])
                self.clear_chat()
                for msg in history:
                    role = msg.get("role", "user")
                    content = msg.get("content", "")
                    # Skip system messages and empty content
                    if role == "system" or not content or not str(content).strip():
                        continue
                    # Only display user and assistant messages
                    if role in ("user", "assistant"):
                        self.add_chat_bubble(content, user=(role=="user"))
                print(f"[ChatTab] Loaded {len(history)} messages from backend.")
                logger.info(f"Loaded {len(history)} messages from backend.")
            else:
                error_msg = f"Failed to load chat history from server: {resp.status_code} {resp.text}"
                self.add_chat_bubble(error_msg, user=False, label="Error")
                logger.error(error_msg)
                print(f"[ChatTab] {error_msg}")
        except Exception as e:
            error_msg = f"Error loading chat history: {e}"
            self.add_chat_bubble(error_msg, user=False, label="Error")
            logger.error(error_msg)
            print(f"[ChatTab] {error_msg}") 