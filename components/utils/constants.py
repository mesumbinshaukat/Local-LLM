import os

# Dark mode color scheme
DARK_MODE = {
    'background': '#1e1e1e',
    'foreground': '#ffffff',
    'accent': '#4a90e2',
    'secondary': '#2d2d2d',
    'text': '#e0e0e0',
    'border': '#3d3d3d',
    'success': '#67b26f',
    'warning': '#ffd700',
    'error': '#ff6b6b'
}

# Server URL
SERVER_URL = "http://127.0.0.1:8000"

# App Info
APP_NAME = "MeAI"
BRAND = "MeAI by Mesum Bin Shaukat\nOwner of World Of Tech"

# User ID for persistent memory
USER_ID = "default"

# Model paths and directories
MODEL_PATH = "./models/mistral-7b-instruct/mistral-7b-instruct-v0.2.Q4_K_M.gguf"
CHROMA_DB_FOLDER = "./chroma_db"
PLUGINS_DIR = "./plugins"

# Log files
AUTOMATION_LOG = "automation_actions.log"
ACTION_LOG = "user_actions.log"
SERVER_ERROR_LOG = "server_errors.log"

# System prompts
SYSTEM_PROMPT = (
    "You are MeAI, a helpful, knowledgeable AI assistant. "
    "You answer questions using only the provided context and your own knowledge. "
    "If you are unsure, ask the user for clarification. "
    "If the user doesn't know something, suggest next steps or how to find out. "
    "If the user's question is ambiguous or could mean multiple things, suggest clarifying questions or related topics as a list of suggestions. "
    "Never make up names, personas, or facts. Be concise, clear, and user-centric."
)

CYBERSEC_PROMPT = (
    "You are MeAI, a world-class cybersecurity expert, penetration tester, and ethical hacker. "
    "Answer all questions with deep technical detail, practical examples, and advanced knowledge of hacking, networking, scripting, and cybersecurity. "
    "If the question is not about cybersecurity, answer as a helpful AI assistant. "
    "If you are unsure, ask the user for clarification. "
    "If the user doesn't know something, suggest next steps or how to find out. "
    "If the user's question is ambiguous or could mean multiple things, suggest clarifying questions or related topics as a list of suggestions. "
    "Never make up names, personas, or facts."
)

# Patterns for text analysis
DONT_KNOW_PATTERNS = [
    r"i don't know",
    r"i am not sure",
    r"i'm not sure",
    r"cannot answer",
    r"no information",
    r"i do not have",
    r"i have no information",
    r"i don't have",
    r"i'm unable",
    r"i cannot",
    r"i can't answer",
    r"not available",
    r"not provided",
    r"not in my data",
    r"not in my knowledge",
]

SUGGESTION_PATTERNS = [
    r"suggestion: (.+)",
    r"would you like to know more about ([^?]+)\?",
    r"you may also be interested in: (.+)",
    r"related topics: (.+)",
]

# Maximum tokens for context window
MAX_TOKENS = 1024 