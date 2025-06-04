# Architecture Overview

## High-Level Diagram

```
+-------------------+      +-------------------+      +-------------------+
|                   |      |                   |      |                   |
|   Desktop App     |<---->|   FastAPI Server  |<---->|   LLM (GGUF)      |
|   (PyQt6)         |      |                   |      |   llama-cpp-python|
+-------------------+      +-------------------+      +-------------------+
        |                        |                          |
        v                        v                          v
+-------------------+      +-------------------+      +-------------------+
|                   |      |                   |      |                   |
|  Knowledge Base   |      |   ChromaDB (RAG)  |      |   MongoDB         |
|  (PDFs, txt, etc) |      |                   |      |   (Memory, Logs)  |
+-------------------+      +-------------------+      +-------------------+
```

## Components

- **Desktop App (PyQt6):** Modern GUI for chat, knowledge, web search, code, automation, plugins, admin, and preferences.
- **FastAPI Server:** Handles all LLM, RAG, web search, code execution, and plugin requests. Exposes REST endpoints.
- **LLM (llama-cpp-python):** Runs GGUF models (Mistral-7B, TinyLlama, etc.) for local inference.
- **ChromaDB:** Local vector database for document retrieval and RAG.
- **Knowledge Base:** User documents (PDF, txt, md, code) ingested for RAG.
- **MongoDB:** (Optional) Stores persistent memory, preferences, feedback, and logs.
- **DuckDuckGo Search:** Local web search fallback.
- **Vosk & pyttsx3:** Speech-to-text and text-to-speech.

## Data Flow
1. User interacts via Desktop App or CLI.
2. Requests sent to FastAPI server.
3. Server handles LLM inference, RAG, web search, code execution, plugins.
4. Results streamed back to client with real-time status and error handling. 