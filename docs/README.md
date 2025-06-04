# MeAI: Local AGI Assistant

## Table of Contents

1. [Overview](#overview)
2. [Features](#features)
3. [System Requirements](#system-requirements)
4. [Installation](#installation)
5. [Usage](#usage)
    - [CLI](#cli)
    - [Desktop App](#desktop-app)
    - [Knowledge Ingestion (RAG)](#knowledge-ingestion-rag)
6. [Architecture](#architecture)
7. [Configuration & Customization](#configuration--customization)
8. [Troubleshooting](#troubleshooting)
9. [FAQ](#faq)
10. [Contributing](#contributing)
11. [Credits & Branding](#credits--branding)
12. [License](#license)

---

## Overview

**MeAI** is a fully local, advanced, and unrestricted LLM assistant for research, automation, code execution, and self-improvement. It is designed for privacy, performance, and extensibility—no cloud, no API keys, no censorship. MeAI combines a local LLM (Mistral-7B, TinyLlama, or any GGUF model), a robust FastAPI backend, a modern PyQt6 desktop app, and a local vector database (ChromaDB) for knowledge retrieval and RAG.

---

## Features

- **Fully Local LLM**: No internet or API keys required. Supports Mistral-7B, TinyLlama, and other GGUF models via llama-cpp-python.
- **Streaming Chat**: Real-time, live output as the LLM generates responses.
- **FastAPI Backend**: Persistent server with endpoints for chat, RAG, web search, code execution, plugins, automation, memory, feedback, and logs.
- **Modern Desktop App**: PyQt6, dark mode, professional UI with tabs for Chat, Knowledge, Web, Code, Automation, Plugins, Admin, and Preferences.
- **Knowledge Ingestion & RAG**: Recursively ingest PDFs, text, and code into ChromaDB. RAG with source metadata and interactive UI.
- **Web Search Fallback**: Automatic DuckDuckGo search if the LLM is unsure.
- **Code Execution & Automation**: Run Python code, shell commands, or chained tasks. Preview/confirm dangerous actions.
- **Plugin System**: Add, run, and manage custom Python plugins from the UI.
- **Persistent Memory**: MongoDB for contextual memory, preferences, feedback, and logs.
- **Feedback Loop & Self-Training**: All actions and queries are logged for future fine-tuning.
- **Personalization**: Preferences for answer style, technical depth, and language (English, Urdu, Transliteration).
- **Voice Input/Output**: Speech-to-text (Vosk) and text-to-speech (pyttsx3) for English and Urdu.
- **Admin & Logs**: View/export logs, feedback, and knowledge. Restart server and monitor health from the UI.
- **Performance & Scalability**: Async/threaded, batching, and efficient memory management for large datasets and low-end hardware.
- **Unrestricted Automation**: The assistant can run any command, script, or code, including sensitive or dangerous tasks, with user confirmation and preview.
- **No Censorship**: The system never refuses or censors information. Everything is logged for future training.

---

## System Requirements

- **OS**: Windows 10/11, Linux, or macOS
- **Python**: 3.11+
- **RAM**: 8GB minimum (16GB+ recommended for large models)
- **CPU**: Modern x86_64 with AVX2 support (for optimal llama.cpp performance)
- **Disk**: 10GB+ free (for models, vector DB, and knowledge base)
- **GPU**: Optional (llama-cpp-python can use CPU or GPU if built accordingly)

---

## Installation

### 1. Clone the Repository

```sh
git clone https://github.com/yourusername/MeAI.git
cd MeAI
```

### 2. Setup the Environment

#### Windows

```bat
setup.bat
```

#### Unix/Mac

```sh
bash setup.sh
```

This will:
- Create a Python 3.11 virtual environment (`venv/`)
- Install all required dependencies (see `requirements.txt`)
- Download or prompt you to place GGUF models in `models/`

---

## Usage

### Activate the Virtual Environment

- **Windows:**  
  `venv\Scripts\activate`
- **Unix/Mac:**  
  `source venv/bin/activate`

### Start the FastAPI Server

```sh
python main.py server
```
- Loads the LLM once for all clients.
- Exposes REST endpoints for chat, RAG, web search, code execution, etc.

### Launch the Desktop App (MeAI)

```sh
python MeAI_app.py
```
- Or run the built Windows executable from `dist/MeAI.exe` (see build instructions).

### Use the CLI

```sh
python main.py --help
```
- Supports chat, knowledge ingestion, and more.

---

### Knowledge Ingestion (RAG)

1. Place PDFs, `.txt`, `.md`, or code files in the `knowledge/` directory (subfolders supported).
2. Run:
   ```sh
   python main.py ingest
   ```
3. All files are processed recursively and added to the local vector database (ChromaDB).

---

## Architecture

**MeAI** is composed of the following main components:

- **llama-cpp-python**: Local LLM inference using GGUF models (Mistral-7B, TinyLlama, etc.).
- **ChromaDB**: Local vector database for document retrieval and RAG.
- **FastAPI Backend**: Persistent server for all LLM, RAG, web search, code execution, and plugin requests.
- **PyQt6 Desktop App**: Modern, dark-mode GUI with tabs for all major features.
- **MongoDB**: (Optional) For persistent memory, preferences, feedback, and logs.
- **DuckDuckGo Search**: Local web search via DuckDuckGo (no API keys required).
- **Vosk & pyttsx3**: For speech-to-text and text-to-speech (English/Urdu).

**Data Flow:**
1. User interacts via Desktop App or CLI.
2. Requests are sent to the FastAPI server.
3. The server handles LLM inference, RAG, web search, code execution, and plugins.
4. Results are streamed back to the client, with real-time status and error handling.

---

## Configuration & Customization

- **Model Selection**: Place your GGUF models in the `models/` directory. Configure which model to use in the app or via CLI.
- **Knowledge Base**: Add documents to `knowledge/` and run ingestion.
- **Preferences**: Set answer style, technical depth, and language in the Preferences tab.
- **Voice**: Download Vosk models for your language and ensure `pyttsx3` is installed for TTS.
- **Plugins**: Place custom Python plugins in the `plugins/` directory.

---

## Troubleshooting

- **Server not responding?**  
  Ensure the server is running: `python main.py server`
- **Model too slow?**  
  Use a smaller GGUF model, or optimize your hardware/llama-cpp build.
- **App crashes or errors?**  
  Check `server_errors.log` and the error dialog for details.
- **Health check failed?**  
  Use the Admin tab to restart the server or view logs.
- **Voice not working?**  
  Ensure Vosk models are downloaded for your language, and pyttsx3 is installed.
- **Web search not working?**  
  Ensure the `/search` endpoint is available and the server is running.
- **Need help?**  
  Open an issue or contact Mesum Bin Shaukat.

---

## FAQ

**Q: Is everything really local?**  
A: Yes. All LLM inference, knowledge storage, and search are 100% local. No data leaves your machine.

**Q: Can I use my own documents?**  
A: Yes. Place them in `knowledge/` and run `python main.py ingest`.

**Q: How do I add new models?**  
A: Download GGUF models and place them in `models/`. Select the model in the app or CLI.

**Q: Can I run this on a low-end laptop?**  
A: Yes, but use a smaller model (e.g., TinyLlama) for best performance.

**Q: How do I update the app?**  
A: Pull the latest code and rerun `setup.bat` or `setup.sh` if dependencies changed.

**Q: Is there a web UI?**  
A: Not yet, but the FastAPI backend makes it possible to add one in the future.

**Q: How do I contribute?**  
A: See [Contributing](#contributing) below.

---

## Contributing

1. Fork the repository and create your branch.
2. Make your changes (code, docs, UI, etc.).
3. Test thoroughly (all platforms if possible).
4. Submit a pull request with a clear description.
5. All contributions are welcome—code, docs, UI/UX, plugins, and more!

---

## Credits & Branding

**MeAI** by Mesum Bin Shaukat  
Owner of World Of Tech

---

## License

This project is under active development. See `LICENSE` for details.

---

**For more information, feature requests, or support, please open an issue or contact Mesum Bin Shaukat.** 