# Installation Guide

## Prerequisites
- Windows 10/11, Linux, or macOS
- Python 3.11+
- Git
- 8GB+ RAM (16GB+ recommended for large models)

## 1. Clone the Repository

```sh
git clone https://github.com/yourusername/MeAI.git
cd MeAI
```

## 2. Setup the Environment

### Windows
```bat
setup.bat
```

### Unix/Mac
```sh
bash setup.sh
```

This will:
- Create a Python 3.11 virtual environment (`venv/`)
- Install all dependencies
- Prompt you to place GGUF models in `models/`

## 3. Download a GGUF Model
- Download a GGUF model (e.g., Mistral-7B, TinyLlama) from HuggingFace or other sources.
- Place the `.gguf` file in the `models/` directory.

## 4. Activate the Virtual Environment
- **Windows:** `venv\Scripts\activate`
- **Unix/Mac:** `source venv/bin/activate`

## 5. Start the Server
```sh
python main.py server
```

## 6. Launch the Desktop App
```sh
python MeAI_app.py
```

## Troubleshooting
- See `docs/FAQ.md` and `docs/README.md` for help. 