import os
from fastapi import FastAPI, Request
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

class ChatRequest(BaseModel):
    messages: list
    query: str = None
    use_rag: bool = False
    cyber_mode: bool = False

CYBERSEC_PROMPT = "You are MeAI, a world-class cybersecurity expert, penetration tester, and ethical hacker. Answer all questions with deep technical detail, practical examples, and advanced knowledge of hacking, networking, scripting, and cybersecurity. If the question is not about cybersecurity, answer as a helpful AI assistant."

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
            messages = truncate_history(req.messages)
            # If cyber_mode, prepend the cybersecurity system prompt
            if req.cyber_mode:
                messages = ([{"role": "system", "content": CYBERSEC_PROMPT}] + messages)
            if req.use_rag and req.query:
                context = retrieve_context(req.query)
                if context:
                    messages.append({"role": "user", "content": f"[Knowledge Base]\n{context}\n[User Question]\n{req.query}"})
                else:
                    messages.append({"role": "user", "content": req.query})
            output = llm.create_chat_completion(
                messages=messages,
                max_tokens=256,
                stop=["</s>"]
            )
            response = output["choices"][0]["message"]["content"].strip()
            server_status["processing"] = False
            server_status["last_error"] = None
            return {"response": response}
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
            messages = truncate_history(req.messages)
            if req.cyber_mode:
                messages = ([{"role": "system", "content": CYBERSEC_PROMPT}] + messages)
            if req.use_rag and req.query:
                context = retrieve_context(req.query)
                if context:
                    messages.append({"role": "user", "content": f"[Knowledge Base]\n{context}\n[User Question]\n{req.query}"})
                else:
                    messages.append({"role": "user", "content": req.query})
            # Stream tokens as they are generated
            partial = ""
            for chunk in llm.create_chat_completion(
                messages=messages,
                max_tokens=256,
                stop=["</s>"],
                stream=True
            ):
                # chunk is a dict with 'choices' -> [{ 'delta': { 'content': ... } }]
                delta = chunk["choices"][0].get("delta", {})
                content = delta.get("content", "")
                if content:
                    partial += content
                    yield content
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
    return "\n".join(docs)

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