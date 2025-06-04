# Local LLM Assistant (MeAI)

A fully local, limitless LLM assistant for research, web search, task execution, code, and training on your own data. No cloud dependencies, no API keys, no telemetry. Portable, robust, and beautiful.

---

## Features

- **Fully Local LLM**: Runs Mistral-7B, TinyLlama, or any GGUF model via llama-cpp-python. No internet or API keys required.
- **FastAPI Server**: Loads the LLM once and serves all requests (chat, RAG, code, automation, memory) for instant responses.
- **Modern Desktop App (MeAI)**: PyQt6, dark mode, tabs for Chat, Knowledge Base, Web Search, Code Execution, and Task Automation. Inspired by Peices.ai.
- **Streaming Chat**: Real-time "thinking" preview as the LLM generates output. No more timeouts or waiting in the dark.
- **Robust Error Handling**: Error dialogs, logs, and status polling for a flawless user experience.
- **Knowledge Base (RAG)**: Ingest and search your own PDFs, text, markdown, and code using ChromaDB. Recursive, deduplicated, and robust.
- **Web Search**: DuckDuckGo search (no API key needed) from both CLI and desktop app.
- **Code Execution & Automation**: Run Python code or shell commands safely from the app.
- **Persistent Memory**: Store and retrieve key-value data using MongoDB.
- **Build System**: One-click build for a portable Windows .exe (PyInstaller).
- **Cybersecurity Mode**: Toggle in the app for expert, technical answers (hacking, networking, scripting, etc.).
- **CLI & GUI**: Use from the command line or the beautiful desktop app.
- **Portable & Private**: Everything runs in a virtual environment. No cloud, no telemetry, no vendor lock-in.

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
python main.py build
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

## Building a Windows Executable
To create a portable `MeAI.exe`:
```sh
python main.py build-exe
```
Find the result in the `dist/` folder.

---

## Features in the Desktop App
- **Chat**: Streamed, real-time LLM chat with context from your knowledge base.
- **Knowledge Base**: Add and ingest documents, see status, and manage your RAG data.
- **Web Search**: Search DuckDuckGo and view results in-app.
- **Code Execution**: Run Python code and see output instantly.
- **Task Automation**: Run shell commands and see results.
- **Cybersecurity Mode**: Checkbox in Chat tab for expert answers.
- **Status Bar**: Live RAM/CPU usage, server status, and error logs.
- **Error Dialogs**: See detailed logs if anything goes wrong.

---

## Robustness & Performance
- **Streaming LLM**: No more timeouts—see the LLM "thinking" in real time.
- **Async/Threaded Calls**: Fast, non-blocking, and stable.
- **Prompt Truncation**: Fits long chats into the model's context window.
- **Status Polling**: Always know if the server is busy or errored.
- **Error Handling**: All errors are logged and shown in the UI.
- **Persistent Memory**: MongoDB for storing key-value data.
- **No Cloud**: 100% local, private, and portable.

---

## Troubleshooting
- **Server not responding?** Make sure you started the server: `python main.py server`.
- **Model too slow?** Use a smaller GGUF model, or optimize your hardware/llama-cpp build.
- **App crashes or errors?** Check `server_errors.log` and the error dialog for details.
- **Need help?** Open an issue or contact Mesum Bin Shaukat.

---

## Credits & Branding
**MeAI** by Mesum Bin Shaukat  
Owner of World Of Tech

---

*This project is under active development. More features, optimizations, and UI/UX improvements coming soon!*
