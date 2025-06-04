# Usage Guide

## CLI Usage

- Show help:
  ```sh
  python main.py --help
  ```
- Chat with the LLM:
  ```sh
  python main.py chat --prompt "What is AGI?"
  ```
- Ingest knowledge:
  ```sh
  python main.py ingest
  ```

## Desktop App Usage

- Start the server:
  ```sh
  python main.py server
  ```
- Launch the app:
  ```sh
  python MeAI_app.py
  ```
- Use the tabs for Chat, Knowledge, Web Search, Code Execution, Automation, Plugins, Admin, and Preferences.
- View logs and server status in the Admin tab.

## Knowledge Ingestion (RAG)

- Place PDFs, `.txt`, `.md`, or code files in `knowledge/`.
- Run:
  ```sh
  python main.py ingest
  ```
- The app will use your knowledge base for RAG.

## Web Search
- Use the Web Search tab or `/search` endpoint for DuckDuckGo results.

## Code Execution
- Use the Code tab to run Python code and see output instantly.

## Task Automation
- Use the Automation tab to run shell commands, chain tasks, and clone repos.

## Plugins
- Place custom Python plugins in `plugins/` and manage them from the Plugins tab.

## Preferences
- Set answer style, technical depth, and language in the Preferences tab.

## Voice Input/Output
- Use your microphone for speech-to-text (Vosk) and have answers read aloud (pyttsx3). 