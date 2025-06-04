# MeAI: Local AGI Assistant

A fully local, advanced, and unrestricted LLM assistant for research, automation, code execution, and self-improvement. No cloud, no API keys, no censorship. Powered by llama-cpp-python (GGUF models), ChromaDB (RAG), FastAPI backend, and a modern PyQt6 desktop app.

---

## Key Features

- **Fully Local LLM**: Run Mistral-7B, TinyLlama, or any GGUF model with llama-cpp-python. No internet or API keys required.
- **Streaming Chat**: Real-time, live "thinking" previews as the LLM generates output. No more waiting in the dark.
- **Robust FastAPI Backend**: Persistent server with endpoints for chat, RAG, web search, code execution, plugins, automation, memory, feedback, logs, and more.
- **Modern Desktop App (MeAI)**: PyQt6, dark mode, professional UI with tabs for Chat, Knowledge, Web, Code, Automation, Plugins, Admin, and Preferences.
- **Knowledge Ingestion & RAG**: Recursively ingest PDFs, text, and code into ChromaDB. RAG with source metadata and interactive UI.
- **Web Search Fallback**: If the LLM is unsure, it auto-searches DuckDuckGo and RAG, showing results in the UI.
- **Code Execution & Automation**: Run Python code, shell commands, or chained tasks. Clone repos, install requirements, and preview/confirm dangerous actions.
- **Plugin System**: Add, run, and manage custom Python plugins from the UI.
- **Persistent Memory**: MongoDB for contextual memory, preferences, feedback, and all logs.
- **Feedback Loop & Self-Training**: Thumbs up/down, comments, and corrections are logged for future fine-tuning. All actions and queries are logged for AGI-like self-improvement.
- **Active Suggestions**: LLM suggests clarifying questions or related topics as clickable buttons.
- **Contextual Memory Sidebar**: Recent topics/questions for easy follow-up.
- **User Personalization**: Preferences for answer style, technical depth, and language (English, Urdu, Transliteration) affect LLM output and voice.
- **Voice Input/Output**: Speech-to-text (Vosk) and text-to-speech (pyttsx3) for English and Urdu.
- **Admin & Logs**: View/export logs, feedback, and knowledge. Restart server and monitor health from the UI.
- **Performance & Scalability**: Async/threaded, batching, and efficient memory management for large datasets and low-end hardware.
- **Unrestricted Automation**: The assistant can run any command, script, or code, including sensitive or dangerous tasks, with user confirmation and preview.
- **No Censorship**: The system never refuses or censors information. Everything is logged for future training.

---

## Setup

### Windows
```bat
setup.bat
```

### Unix/Mac
```sh
bash setup.sh
```

---

## Usage

### Activate the virtual environment
- **Windows:** `venv\Scripts\activate`
- **Unix/Mac:** `source venv/bin/activate`

### Start the FastAPI server (loads the LLM once for all clients)
```sh
python main.py server
```

### Launch the Desktop App (MeAI)
```sh
python MeAI_app.py
```
Or run the built Windows executable from `dist/MeAI.exe` (see below).

### Use the CLI
```sh
python main.py --help
```

---

## Knowledge Base Ingestion (RAG)
1. Place PDFs, .txt, .md, or code files in the `knowledge/` directory (subfolders supported).
2. Run:
   ```sh
   python main.py ingest
   ```
3. All files are processed recursively and added to the local vector database (ChromaDB).

---

## Desktop App Features

- **Chat**: Streamed, real-time LLM chat with context from your knowledge base and web search fallback.
- **Knowledge Base**: Add and ingest documents, see status, and manage your RAG data. View sources for every RAG result.
- **Web Search**: Search DuckDuckGo and view results in-app. Automatic fallback if LLM is unsure.
- **Code Execution**: Run Python code and see output instantly.
- **Task Automation**: Run shell commands, chain tasks, and clone repos. Preview/confirm dangerous actions.
- **Plugins**: Upload, delete, run, and manage custom Python plugins from the UI.
- **Admin**: View/export logs, feedback, and knowledge. Restart server and monitor health.
- **Preferences**: Set answer style, technical depth, and language (English, Urdu, Transliteration). Clear/reset memory and preferences.
- **Voice Input/Output**: Use your microphone for speech-to-text (English/Urdu) and have answers read aloud (TTS).
- **Feedback & Corrections**: Thumbs up/down, comments, and suggest corrections for any answer.
- **Contextual Memory**: Sidebar with recent topics/questions for easy follow-up.
- **Status Bar**: Live RAM/CPU usage, server status, and error logs. Health checks and error recovery.

---

## Advanced Automation & AGI Features
- **Task Chaining**: Run multiple commands/scripts in sequence, with preview and error handling.
- **Repo Cloning**: Clone any git repo, optionally install requirements, and view logs.
- **Unrestricted Automation**: Run any command, script, or code, including sensitive or dangerous tasks, with user confirmation and preview.
- **Self-Training**: All actions, queries, and feedback are logged for future model improvement and AGI-like self-improvement.

---

## Logs, Feedback, and Export
- **All actions, queries, and feedback are logged** for future fine-tuning.
- **Export logs, feedback, and knowledge** from the Admin tab for training or analysis.
- **Submit corrections** to improve future answers.

---

## Robustness & Performance
- **Streaming LLM**: No more timeouts—see the LLM "thinking" in real time.
- **Async/Threaded Calls**: Fast, non-blocking, and stable.
- **Prompt Truncation**: Fits long chats into the model's context window.
- **Status Polling & Health Checks**: Always know if the server is busy, errored, or unhealthy.
- **Error Handling**: All errors are logged and shown in the UI, with recovery options.
- **Persistent Memory**: MongoDB for storing key-value data, preferences, and feedback.
- **No Cloud**: 100% local, private, and portable.

---

## Troubleshooting
- **Server not responding?** Make sure you started the server: `python main.py server`.
- **Model too slow?** Use a smaller GGUF model, or optimize your hardware/llama-cpp build.
- **App crashes or errors?** Check `server_errors.log` and the error dialog for details.
- **Health check failed?** Use the Admin tab to restart the server or view logs.
- **Voice not working?** Ensure Vosk models are downloaded for your language, and pyttsx3 is installed.
- **Need help?** Open an issue or contact Mesum Bin Shaukat.

---

## Credits & Branding
**MeAI** by Mesum Bin Shaukat  
Owner of World Of Tech

---

*This project is under active development. More features, optimizations, and UI/UX improvements coming soon!*
