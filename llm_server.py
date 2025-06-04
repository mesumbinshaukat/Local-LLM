import os
from fastapi import FastAPI, Request, UploadFile
from pydantic import BaseModel
from llama_cpp import Llama
import chromadb
from chromadb.config import Settings
from fastapi.responses import JSONResponse, StreamingResponse
import subprocess
import traceback
from pymongo import MongoClient
import pickle
import threading
import time
import psutil
import logging
from duckduckgo_search import DDGS
import re
import glob
import sys

MODEL_PATH = "./models/mistral-7b-instruct/mistral-7b-instruct-v0.2.Q4_K_M.gguf"
CHROMA_DB_FOLDER = "./chroma_db"
MONGO_URI = "mongodb://localhost:27017/"
DB_NAME = "Local-LLM"
CACHE_FILE = "./llm_cache.pkl"

app = FastAPI()
llm = None

# Setup error logging
logging.basicConfig(filename='server_errors.log', level=logging.ERROR, format='%(asctime)s %(levelname)s %(message)s')

# Global status
server_status = {"processing": False, "last_error": None, "last_request_time": None, "ram_usage": 0, "cpu_usage": 0}

# Helper: Truncate chat history to fit context window
MAX_TOKENS = 1024

# Helper: Detect 'I don't know' or uncertainty in LLM output
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
def is_dont_know(text):
    text = text.lower()
    return any(re.search(pat, text) for pat in DONT_KNOW_PATTERNS)

class ChatRequest(BaseModel):
    messages: list
    query: str = None
    use_rag: bool = False
    cyber_mode: bool = False
    preferences: dict = None

# Update the system prompt for all modes
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

# Helper: Extract suggestions from LLM output
SUGGESTION_PATTERNS = [
    r"suggestion: (.+)",
    r"would you like to know more about ([^?]+)\?",
    r"you may also be interested in: (.+)",
    r"related topics: (.+)",
]
def extract_suggestions(text):
    suggestions = []
    for pat in SUGGESTION_PATTERNS:
        for match in re.findall(pat, text, re.IGNORECASE):
            # Split by common delimiters
            if isinstance(match, tuple):
                match = match[0]
            for s in re.split(r"[;,.\n]", match):
                s = s.strip()
                if s and s.lower() not in [x.lower() for x in suggestions]:
                    suggestions.append(s)
    return suggestions

@app.on_event("startup")
def load_model():
    global llm
    if not os.path.exists(MODEL_PATH):
        raise RuntimeError(f"Model file not found at {MODEL_PATH}")
    llm = Llama(model_path=MODEL_PATH, n_ctx=2048)
    print("LLM loaded and ready.")

@app.post("/chat")
def chat_endpoint(req: ChatRequest):
    def run_llm():
        try:
            server_status["processing"] = True
            server_status["last_request_time"] = time.time()
            # Phase 5: Personalization
            preferences = getattr(req, 'preferences', None)
            sys_prompt = CYBERSEC_PROMPT if req.cyber_mode else SYSTEM_PROMPT
            if preferences:
                if preferences.get("answer_style") == "concise":
                    sys_prompt += " Always be concise."
                elif preferences.get("answer_style") == "detailed":
                    sys_prompt += " Always be detailed and thorough."
                if preferences.get("tech_depth") == "basic":
                    sys_prompt += " Use basic, beginner-friendly explanations."
                elif preferences.get("tech_depth") == "advanced":
                    sys_prompt += " Use advanced, technical explanations."
                if preferences.get("language") and preferences["language"] != "English":
                    sys_prompt += f" Answer in {preferences['language']}."
            messages = truncate_history(req.messages)
            if not messages or messages[0].get("role") != "system":
                messages = ([{"role": "system", "content": sys_prompt}] + messages)
            else:
                messages[0]["content"] = sys_prompt
            if req.use_rag and req.query:
                context = retrieve_context(req.query)
                if context:
                    messages.append({
                        "role": "user",
                        "content": (
                            "Use the following context to answer the user's question. "
                            "If you are unsure, ask the user for clarification. "
                            "If the user doesn't know something, suggest next steps.\n\n"
                            f"Context:\n---\n{context}\n---\n\n"
                            f"User Question: {req.query}\nAnswer:"
                        )
                    })
                else:
                    messages.append({"role": "user", "content": req.query})
            output = llm.create_chat_completion(
                messages=messages,
                max_tokens=256,
                stop=["</s>"]
            )
            response = output["choices"][0]["message"]["content"].strip()
            # Phase 1: Detect 'I don't know' and fallback
            web_results = []
            rag_results = []
            if is_dont_know(response):
                # Web search fallback
                try:
                    with DDGS() as ddgs:
                        web_results = list(ddgs.text(req.query, max_results=3))
                except Exception as e:
                    web_results = [{"title": "Web search failed", "body": str(e), "href": ""}]
                # RAG fallback (if not already used)
                if not req.use_rag:
                    try:
                        rag_chunks = retrieve_context(req.query)
                        rag_results = rag_chunks
                    except Exception as e:
                        rag_results = [{"text": f"RAG failed: {e}", "source": "", "chunk": 0}]
            # Phase 3: Extract suggestions
            suggestions = extract_suggestions(response)
            server_status["processing"] = False
            server_status["last_error"] = None
            # Backward compatible: 'response' for old clients, all fields for new
            return {
                "response": response,
                "llm_answer": response,
                "web_results": web_results,
                "rag_results": rag_results,
                "suggestions": suggestions
            }
        except Exception as e:
            logging.error("LLM error: %s", str(e), exc_info=True)
            server_status["processing"] = False
            server_status["last_error"] = str(e)
            return JSONResponse(status_code=500, content={"error": str(e)})
    # Run LLM in a thread for non-blocking
    result = {}
    thread = threading.Thread(target=lambda: result.update(run_llm()))
    thread.start()
    thread.join()
    return result

@app.post("/chat/stream")
def chat_stream_endpoint(req: ChatRequest):
    def chat_stream_generator():
        try:
            server_status["processing"] = True
            server_status["last_request_time"] = time.time()
            preferences = getattr(req, 'preferences', None)
            sys_prompt = CYBERSEC_PROMPT if req.cyber_mode else SYSTEM_PROMPT
            if preferences:
                if preferences.get("answer_style") == "concise":
                    sys_prompt += " Always be concise."
                elif preferences.get("answer_style") == "detailed":
                    sys_prompt += " Always be detailed and thorough."
                if preferences.get("tech_depth") == "basic":
                    sys_prompt += " Use basic, beginner-friendly explanations."
                elif preferences.get("tech_depth") == "advanced":
                    sys_prompt += " Use advanced, technical explanations."
                if preferences.get("language") and preferences["language"] != "English":
                    sys_prompt += f" Answer in {preferences['language']}."
            messages = truncate_history(req.messages)
            if not messages or messages[0].get("role") != "system":
                messages = ([{"role": "system", "content": sys_prompt}] + messages)
            else:
                messages[0]["content"] = sys_prompt
            if req.use_rag and req.query:
                context = retrieve_context(req.query)
                if context:
                    messages.append({
                        "role": "user",
                        "content": (
                            "Use the following context to answer the user's question. "
                            "If you are unsure, ask the user for clarification. "
                            "If the user doesn't know something, suggest next steps.\n\n"
                            f"Context:\n---\n{context}\n---\n\n"
                            f"User Question: {req.query}\nAnswer:"
                        )
                    })
                else:
                    messages.append({"role": "user", "content": req.query})
            partial = ""
            dont_know_triggered = False
            for chunk in llm.create_chat_completion(
                messages=messages,
                max_tokens=256,
                stop=["</s>"],
                stream=True
            ):
                delta = chunk["choices"][0].get("delta", {})
                content = delta.get("content", "")
                if content:
                    partial += content
                    yield content
                    if not dont_know_triggered and is_dont_know(partial):
                        dont_know_triggered = True
            # At the end, if 'I don't know' was detected, send fallback
            suggestions = extract_suggestions(partial)
            if dont_know_triggered or suggestions:
                # Web search fallback
                try:
                    with DDGS() as ddgs:
                        web_results = list(ddgs.text(req.query, max_results=3))
                except Exception as e:
                    web_results = [{"title": "Web search failed", "body": str(e), "href": ""}]
                # RAG fallback (if not already used)
                rag_results = []
                if not req.use_rag:
                    try:
                        rag_chunks = retrieve_context(req.query)
                        rag_results = rag_chunks
                    except Exception as e:
                        rag_results = [{"text": f"RAG failed: {e}", "source": "", "chunk": 0}]
                # Send as a JSON block at the end
                import json
                yield "\n[FALLBACK]" + json.dumps({"web_results": web_results, "rag_results": rag_results, "suggestions": suggestions})
            server_status["processing"] = False
            server_status["last_error"] = None
        except Exception as e:
            logging.error("LLM stream error: %s", str(e), exc_info=True)
            server_status["processing"] = False
            server_status["last_error"] = str(e)
            yield f"\n[ERROR]: {str(e)}"
    return StreamingResponse(chat_stream_generator(), media_type="text/plain")

def retrieve_context(query, top_k=3):
    client = chromadb.PersistentClient(path=CHROMA_DB_FOLDER)
    collection = client.get_or_create_collection("knowledge")
    results = collection.query(query_texts=[query], n_results=top_k)
    docs = [doc for doc in results.get("documents", [[]])[0]]
    metadatas = results.get("metadatas", [[]])[0]
    # Return both text and metadata for interactive RAG
    rag_chunks = []
    for i, doc in enumerate(docs):
        meta = metadatas[i] if i < len(metadatas) else {}
        rag_chunks.append({
            "text": doc,
            "source": meta.get("source", "unknown"),
            "chunk": meta.get("chunk", 0)
        })
    return rag_chunks

# MongoDB client for persistent memory
def get_mongo():
    return MongoClient(MONGO_URI)[DB_NAME]

# Cache management
def save_cache(data):
    with open(CACHE_FILE, "wb") as f:
        pickle.dump(data, f)

def load_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "rb") as f:
            return pickle.load(f)
    return None

@app.post("/exec")
def exec_code(request: dict):
    code = request.get("code", "")
    try:
        # Security: restrict builtins, globals, etc.
        local_vars = {}
        exec(code, {"__builtins__": {}}, local_vars)
        return {"result": str(local_vars)}
    except Exception as e:
        return JSONResponse(status_code=400, content={"error": str(e), "traceback": traceback.format_exc()})

@app.post("/shell")
def exec_shell(request: dict):
    cmd = request.get("cmd", "")
    try:
        result = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT, timeout=30, encoding="utf-8")
        return {"result": result}
    except Exception as e:
        return JSONResponse(status_code=400, content={"error": str(e), "traceback": traceback.format_exc()})

@app.post("/memory/save")
def save_memory(request: dict):
    key = request.get("key")
    value = request.get("value")
    db = get_mongo()
    db.memory.update_one({"key": key}, {"$set": {"value": value}}, upsert=True)
    return {"status": "ok"}

@app.get("/memory/load/{key}")
def load_memory(key: str):
    db = get_mongo()
    doc = db.memory.find_one({"key": key})
    return {"value": doc["value"] if doc else None}

@app.post("/cache/save")
def save_cache_endpoint(request: dict):
    save_cache(request.get("data"))
    return {"status": "ok"}

@app.get("/cache/load")
def load_cache_endpoint():
    data = load_cache()
    return {"data": data}

@app.get("/status")
def status():
    server_status["ram_usage"] = psutil.virtual_memory().percent
    server_status["cpu_usage"] = psutil.cpu_percent(interval=0.1)
    return server_status

# Helper: Truncate chat history to fit context window
def truncate_history(messages):
    # Only keep the last N messages to fit in context
    truncated = []
    token_count = 0
    for msg in reversed(messages):
        token_count += len(msg.get('content', '')) // 4  # rough estimate: 1 token ~ 4 chars
        if token_count > MAX_TOKENS:
            break
        truncated.insert(0, msg)
    return truncated

@app.get("/search")
def search_endpoint(query: str):
    try:
        with DDGS() as ddgs:
            results = ddgs.text(query, max_results=5)
            out = []
            for r in results:
                out.append({
                    "title": r.get("title", ""),
                    "href": r.get("href", ""),
                    "body": r.get("body", "")
                })
        return {"results": out}
    except Exception as e:
        logging.error("Web search error: %s", str(e), exc_info=True)
        return {"results": [], "error": str(e)}

@app.post("/feedback")
def feedback_endpoint(request: dict):
    """
    Accepts feedback on LLM answers and fallbacks.
    Fields: query, llm_answer, web_results, rag_results, feedback ('up'/'down'), user_comment (optional)
    Stores in MongoDB for future analysis/fine-tuning.
    """
    try:
        db = get_mongo()
        doc = {
            "query": request.get("query"),
            "llm_answer": request.get("llm_answer"),
            "web_results": request.get("web_results"),
            "rag_results": request.get("rag_results"),
            "feedback": request.get("feedback"),
            "user_comment": request.get("user_comment"),
            "timestamp": time.time(),
        }
        db.feedback.insert_one(doc)
        return {"status": "ok"}
    except Exception as e:
        logging.error("Feedback error: %s", str(e), exc_info=True)
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/plugins")
def list_plugins():
    """List available plugins (Python scripts in plugins/ folder)."""
    try:
        plugin_files = glob.glob("plugins/*.py")
        plugins = [os.path.basename(f) for f in plugin_files]
        return {"plugins": plugins}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/plugin/run")
def run_plugin(request: dict):
    """
    Run a selected plugin with user input.
    Fields: plugin (filename), input (string)
    Returns: output, error
    """
    plugin = request.get("plugin")
    user_input = request.get("input", "")
    if not plugin or not plugin.endswith(".py") or "/" in plugin or ".." in plugin:
        return JSONResponse(status_code=400, content={"error": "Invalid plugin name."})
    plugin_path = os.path.join("plugins", plugin)
    if not os.path.exists(plugin_path):
        return JSONResponse(status_code=404, content={"error": "Plugin not found."})
    try:
        import subprocess
        result = subprocess.run([
            sys.executable, plugin_path, user_input
        ], capture_output=True, text=True, timeout=30)
        return {
            "output": result.stdout,
            "error": result.stderr
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)}) 