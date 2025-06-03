# Local LLM CLI Assistant

A fully local, personal LLM assistant for research, web search, task execution, and training on your own data. No cloud dependencies. Runs anywhere after cloning.

## Setup

### Windows
```
setup.bat
```

### Unix/Mac
```
bash setup.sh
```

## Usage

Activate the virtual environment:

- **Windows:** `venv\Scripts\activate`
- **Unix/Mac:** `source venv/bin/activate`

Run the CLI:
```
python main.py --help
```

## Features
- Local LLM chat
- Web search
- Task execution
- Train/fine-tune on your data
- **Cybersecurity Mode:** Toggle in the desktop app to make MeAI answer as a world-class cybersecurity expert (hacking, networking, scripting, etc.).
- **Recursive Knowledge Ingestion:** Ingest all PDFs, .txt, and .md files (including subfolders) from the `knowledge/` folder into the local knowledge base for RAG.
- **Build Windows Executable:**
    - Run `python main.py build_exe` to create a portable MeAI.exe in the `dist/` folder (requires PyInstaller).

## Knowledge Base Ingestion
To feed MeAI with your own data:
1. Place PDFs, .txt, or .md files (including folders) in the `knowledge/` directory.
2. Run:
   ```
   python main.py ingest
   ```
3. All files will be processed recursively and added to the knowledge base.

## Cybersecurity Mode
- In the MeAI desktop app, enable the "Cybersecurity Mode (Expert)" checkbox in the Chat tab for advanced, technical cybersecurity answers.
- When off, MeAI behaves as a general-purpose assistant.

*More features coming soon!*
