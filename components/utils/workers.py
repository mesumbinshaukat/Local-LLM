from PyQt6.QtCore import QThread, pyqtSignal
import requests
import logging
from components.utils.constants import SERVER_URL, USER_ID
import json
import time

logger = logging.getLogger(__name__)

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
                "cyber_mode": self.cyber_mode,
                "user_id": USER_ID
            }
            
            if self.prefs:
                payload["preferences"] = self.prefs
            
            # Make the request
            response = requests.post(
                f"{SERVER_URL}/chat",
                json=payload,
                timeout=30
            )
            
            if response.status_code != 200:
                self.error.emit(f"Error: {response.status_code} - {response.text}")
                return
                
            result = response.json()
            self.finished.emit(result.get("response", ""))
            
        except Exception as e:
            logger.error(f"Chat worker error: {str(e)}")
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
                for line in response.iter_lines():
                    if not self._is_running:
                        break
                        
                    if line:
                        try:
                            data = line.decode('utf-8')
                            # Handle SSE format
                            if data.startswith('data: '):
                                data = data[6:]  # Remove 'data: ' prefix
                            if data.strip() == '[DONE]':
                                break
                                
                            # Handle fallback data
                            if data.startswith('[FALLBACK]'):
                                try:
                                    fallback_data = json.loads(data[10:])
                                    if 'web_results' in fallback_data:
                                        full_response += "\n\nWeb search results:\n"
                                        for result in fallback_data['web_results']:
                                            full_response += f"- {result.get('title', '')}: {result.get('body', '')}\n"
                                    if 'rag_results' in fallback_data:
                                        full_response += "\n\nKnowledge base results:\n"
                                        for result in fallback_data['rag_results']:
                                            full_response += f"- {result.get('text', '')}\n"
                                    if 'suggestions' in fallback_data:
                                        full_response += "\n\nSuggestions:\n"
                                        for suggestion in fallback_data['suggestions']:
                                            full_response += f"- {suggestion}\n"
                                    continue
                                except json.JSONDecodeError:
                                    pass
                                    
                            # Handle error data
                            if data.startswith('[ERROR]'):
                                self.error_signal.emit(data[8:])
                                return
                                
                            # Handle normal content
                            if data:
                                full_response += data
                                self.partial_signal.emit(data)
                                
                        except Exception as e:
                            logger.error(f"Error processing stream: {str(e)}")
                            continue
                
                if self._is_running:
                    self.done_signal.emit(full_response)
                    
        except requests.exceptions.Timeout:
            self.error_signal.emit("Request timed out. Please try again.")
        except requests.exceptions.ConnectionError:
            self.error_signal.emit("Could not connect to server. Please check if the server is running.")
        except Exception as e:
            logger.error(f"Streaming chat worker error: {str(e)}")
            self.error_signal.emit(str(e))

class LogMonitorWorker(QThread):
    log_signal = pyqtSignal(str)
    def __init__(self, server_url):
        super().__init__()
        self.server_url = server_url
        self.running = True
    def run(self):
        while self.running:
            try:
                resp = requests.get(f"{self.server_url}/status/live").json()
                log = resp.get("log", "")
                self.log_signal.emit(log)
            except Exception:
                self.log_signal.emit("Error fetching logs.")
            time.sleep(5)
    def stop(self):
        self.running = False
        self.quit()

class ResourceMonitorWorker(QThread):
    resource_signal = pyqtSignal(dict)
    def __init__(self, server_url):
        super().__init__()
        self.server_url = server_url
        self.running = True
    def run(self):
        while self.running:
            try:
                usage = requests.get(f"{self.server_url}/memory/usage").json()
                self.resource_signal.emit(usage)
            except Exception:
                self.resource_signal.emit({"ram": -1, "cpu": -1})
            time.sleep(2)
    def stop(self):
        self.running = False
        self.quit() 