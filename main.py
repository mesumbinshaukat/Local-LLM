import click
from rich.console import Console
from transformers import AutoModelForCausalLM, AutoTokenizer
import torch
import os
import shutil
import time
import datetime
from llama_cpp import Llama
from duckduckgo_search import DDGS
import glob
import chromadb
from chromadb.config import Settings
from chromadb.errors import InternalError
from pypdf import PdfReader
import requests
import sys
import traceback
from pathlib import Path
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("local_llm.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("local-llm")

console = Console()

MODEL_PATH = "./models/mistral-7b-instruct/mistral-7b-instruct-v0.2.Q4_K_M.gguf"
KNOWLEDGE_FOLDER = "./knowledge"
CHROMA_DB_FOLDER = "./chroma_db"
BACKUP_FOLDER = "./chroma_db_backups"

def backup_chroma_db(reason="manual"):
    """
    Create a backup of the ChromaDB database
    
    Args:
        reason: String describing the reason for backup (e.g., "pre-ingestion", "post-ingestion")
    
    Returns:
        str: Path to the backup directory or None if backup failed
    """
    if not os.path.exists(CHROMA_DB_FOLDER):
        console.print(f"[yellow]No ChromaDB folder found at {CHROMA_DB_FOLDER}. Skipping backup.[/yellow]")
        return None
    
    try:
        # Create backup directory if it doesn't exist
        os.makedirs(BACKUP_FOLDER, exist_ok=True)
        
        # Create a timestamp for the backup folder
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = os.path.join(BACKUP_FOLDER, f"chroma_db_backup_{reason}_{timestamp}")
        
        # Create the backup
        shutil.copytree(CHROMA_DB_FOLDER, backup_path)
        console.print(f"[green]Successfully created ChromaDB backup at: {backup_path}[/green]")
        logger.info(f"ChromaDB backup created: {backup_path}")
        
        # Clean up old backups (keep only the 5 most recent)
        backups = sorted([os.path.join(BACKUP_FOLDER, d) for d in os.listdir(BACKUP_FOLDER) 
                         if os.path.isdir(os.path.join(BACKUP_FOLDER, d))], 
                         key=os.path.getmtime)
        
        if len(backups) > 5:
            for old_backup in backups[:-5]:
                try:
                    shutil.rmtree(old_backup)
                    logger.info(f"Removed old backup: {old_backup}")
                except Exception as e:
                    logger.warning(f"Failed to remove old backup {old_backup}: {e}")
        
        return backup_path
    except Exception as e:
        console.print(f"[bold red]Failed to create ChromaDB backup: {e}[/bold red]")
        logger.error(f"Backup failed: {e}")
        return None

def restore_chroma_db_from_backup(backup_path=None):
    """
    Restore ChromaDB from a backup
    
    Args:
        backup_path: Path to the backup directory. If None, will use the most recent backup.
    
    Returns:
        bool: True if restoration was successful, False otherwise
    """
    try:
        if backup_path is None:
            # Find the most recent backup
            backups = sorted([os.path.join(BACKUP_FOLDER, d) for d in os.listdir(BACKUP_FOLDER) 
                             if os.path.isdir(os.path.join(BACKUP_FOLDER, d))], 
                             key=os.path.getmtime)
            
            if not backups:
                console.print("[bold red]No backups found to restore from.[/bold red]")
                return False
            
            backup_path = backups[-1]  # Most recent backup
        
        if not os.path.exists(backup_path):
            console.print(f"[bold red]Backup path does not exist: {backup_path}[/bold red]")
            return False
        
        # If the chroma_db directory exists, rename it first as a precaution
        if os.path.exists(CHROMA_DB_FOLDER):
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            corrupted_db_path = f"{CHROMA_DB_FOLDER}_corrupted_{timestamp}"
            shutil.move(CHROMA_DB_FOLDER, corrupted_db_path)
            console.print(f"[yellow]Moved existing (potentially corrupted) database to: {corrupted_db_path}[/yellow]")
        
        # Restore from backup
        shutil.copytree(backup_path, CHROMA_DB_FOLDER)
        console.print(f"[bold green]Successfully restored ChromaDB from: {backup_path}[/bold green]")
        logger.info(f"Restored ChromaDB from backup: {backup_path}")
        return True
    except Exception as e:
        console.print(f"[bold red]Failed to restore ChromaDB from backup: {e}[/bold red]")
        logger.error(f"Restore failed: {e}")
        return False

def get_chroma_client(attempt_recovery=True):
    """
    Get a ChromaDB client with robust settings and error handling
    
    Args:
        attempt_recovery: Whether to attempt recovery if the database is corrupted
    
    Returns:
        chromadb.PersistentClient: A ChromaDB client instance
    
    Raises:
        Exception: If the client cannot be created and recovery fails
    """
    try:
        # More robust settings for ChromaDB
        settings = Settings(
            allow_reset=True,
            anonymized_telemetry=False,
            persist_directory=CHROMA_DB_FOLDER
        )
        
        # Try to create the client
        client = chromadb.PersistentClient(path=CHROMA_DB_FOLDER, settings=settings)
        # Test the client with a simple operation
        collections = client.list_collections()
        logger.info(f"ChromaDB client created successfully. Found {len(collections)} collections.")
        return client
    except Exception as e:
        logger.error(f"Error creating ChromaDB client: {e}")
        
        if attempt_recovery and isinstance(e, InternalError) and "database disk image is malformed" in str(e):
            console.print("[bold yellow]ChromaDB database appears to be corrupted. Attempting recovery...[/bold yellow]")
            
            # Try to restore from backup
            if restore_chroma_db_from_backup():
                console.print("[bold green]Recovery successful! Trying to create client again...[/bold green]")
                # Try again, but don't attempt recovery to avoid infinite recursion
                return get_chroma_client(attempt_recovery=False)
            else:
                # If restore fails, recreate the database from scratch
                console.print("[bold yellow]Backup restoration failed. Creating a new database...[/bold yellow]")
                try:
                    if os.path.exists(CHROMA_DB_FOLDER):
                        shutil.rmtree(CHROMA_DB_FOLDER)
                    os.makedirs(CHROMA_DB_FOLDER, exist_ok=True)
                    
                    # Try again with a fresh database
                    return get_chroma_client(attempt_recovery=False)
                except Exception as e2:
                    logger.error(f"Failed to create new database: {e2}")
                    raise Exception(f"Failed to recover or create new ChromaDB database: {e2}")
        else:
            raise

def check_chroma_db_integrity():
    """
    Perform a simple integrity check on the ChromaDB database.
    Returns True if the DB is healthy, False otherwise.
    """
    try:
        client = get_chroma_client(attempt_recovery=False)
        # Try a simple operation
        _ = client.list_collections()
        return True
    except Exception as e:
        logger.error(f"ChromaDB integrity check failed: {e}")
        return False

@click.group()
def cli():
    """Personal LLM CLI Assistant"""
    pass

@cli.command()
def server():
    """Start the LLM server (loads model once and serves chat/RAG requests)."""
    os.system("uvicorn llm_server:app --host 127.0.0.1 --port 8000")

@cli.command()
def chat():
    """Chat with the local LLM (via server, with knowledge base)."""
    system_prompt = "You are a helpful, knowledgeable AI assistant. Answer as helpfully as possible."
    chat_history = [
        {"role": "system", "content": system_prompt}
    ]
    console.print("[bold green]Chat client started. Type 'exit' to quit.[/bold green]")
    while True:
        user_input = console.input("[bold cyan]You:[/bold cyan] ")
        if user_input.strip().lower() in ["exit", "quit"]:
            console.print("[bold yellow]Exiting chat. Goodbye![/bold yellow]")
            break
        chat_history.append({"role": "user", "content": user_input})
        try:
            resp = requests.post(
                "http://127.0.0.1:8000/chat",
                json={"messages": chat_history, "query": user_input, "use_rag": True}
            )
            response = resp.json()["response"]
        except Exception as e:
            console.print(f"[bold red]Error communicating with LLM server: {e}[/bold red]")
            break
        chat_history.append({"role": "assistant", "content": response})
        console.print(f"[bold magenta]LLM:[/bold magenta] {response}", markup=False)

@cli.command()
@click.argument('query')
def search(query):
    """Search the web using DuckDuckGo (no API key required)."""
    console.print(f"[bold blue]Searching DuckDuckGo for:[/bold blue] {query}")
    with DDGS() as ddgs:
        results = ddgs.text(query, max_results=5)
        for idx, result in enumerate(results, 1):
            console.print(f"[bold]{idx}.[/bold] [cyan]{result['title']}[/cyan]")
            console.print(f"    [green]{result['href']}[/green]")
            console.print(f"    {result['body']}", markup=False)

@cli.command()
def train(data_path: str = None):
    """Guide for local fine-tuning (scaffold)."""
    if not data_path:
        console.print("[bold yellow]To fine-tune, provide a path to your training data (e.g., JSONL or CSV). Example: python main.py train --data-path ./mydata.jsonl[/bold yellow]")
        return
    if not os.path.exists(data_path):
        console.print(f"[bold red]Data file not found: {data_path}[/bold red]")
        return
    console.print(f"[bold green]Preparing data from {data_path} for fine-tuning...[/bold green]")
    # Placeholder: Add data loading, preprocessing, and call to fine-tuning pipeline here
    console.print("[bold yellow]Local fine-tuning is a resource-intensive process. This feature is under development.[/bold yellow]")

@cli.command()
def ingest():
    """Recursively ingest all PDFs, text, markdown, and code files in the knowledge folder into the local vector DB."""
    console.print(f"[bold blue]Recursively ingesting documents and code from {KNOWLEDGE_FOLDER}...[/bold blue]")
    
    # Create a backup before ingestion
    pre_backup_path = backup_chroma_db("pre-ingestion")
    if not check_chroma_db_integrity():
        console.print("[bold red]ChromaDB integrity check failed before ingestion. Aborting.[/bold red]")
        return
    try:
        # Get a robust ChromaDB client with recovery mechanisms
        client = get_chroma_client()
        collection = client.get_or_create_collection("knowledge")
        # Fetch all existing IDs for deduplication
        existing_ids = set(collection.get()["ids"])
        # File extensions to ingest
        doc_exts = [".pdf", ".txt", ".md"]
        code_exts = [
            ".py", ".sh", ".bat", ".ps1", ".c", ".cpp", ".go", ".js", ".rb", ".pl", ".php", ".java", ".cs", ".yaml", ".yml", ".json", ".toml", ".ini", ".conf", ".xml", ".html", ".ts"
        ]
        all_exts = doc_exts + code_exts
        doc_files = []
        code_files = []
        for p in Path(KNOWLEDGE_FOLDER).rglob("*"):
            if p.is_file():
                ext = p.suffix.lower()
                if ext in doc_exts:
                    doc_files.append(p)
                elif ext in code_exts:
                    code_files.append(p)
        total_chunks = 0
        code_chunks = 0
        failed_files = []
        # Ingest document files
        for file_path in doc_files:
            file_path = str(file_path)
            try:
                if file_path.lower().endswith(".pdf"):
                    reader = PdfReader(file_path)
                    text = "\n".join(page.extract_text() or "" for page in reader.pages)
                else:
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        text = f.read()
                # Split into chunks for embedding
                chunks = [text[i:i+1000] for i in range(0, len(text), 1000) if text[i:i+1000].strip()]
                new_chunks = 0
                for idx, chunk in enumerate(chunks):
                    chunk_id = f"{file_path}-{idx}"
                    if chunk_id in existing_ids:
                        continue  # Skip already ingested chunk
                    collection.add(
                        documents=[chunk],
                        metadatas=[{"source": file_path, "chunk": idx}],
                        ids=[chunk_id]
                    )
                    existing_ids.add(chunk_id)
                    new_chunks += 1
                total_chunks += new_chunks
                if new_chunks > 0:
                    console.print(f"[green]Ingested:[/green] {file_path} ([cyan]{new_chunks} new chunks[/cyan])")
                else:
                    console.print(f"[yellow]Skipped (already ingested):[/yellow] {file_path}")
            except Exception as e:
                failed_files.append(file_path)
                console.print(f"[red]Failed to ingest:[/red] {file_path} - {e}")
                traceback.print_exc()
        # Ingest code files
        for file_path in code_files:
            file_path = str(file_path)
            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    text = f.read()
                # Split into chunks for embedding
                chunks = [text[i:i+1000] for i in range(0, len(text), 1000) if text[i:i+1000].strip()]
                new_chunks = 0
                for idx, chunk in enumerate(chunks):
                    chunk_id = f"{file_path}-{idx}"
                    if chunk_id in existing_ids:
                        continue  # Skip already ingested chunk
                    collection.add(
                        documents=[chunk],
                        metadatas=[{"source": file_path, "chunk": idx, "type": "code"}],
                        ids=[chunk_id]
                    )
                    existing_ids.add(chunk_id)
                    new_chunks += 1
                code_chunks += new_chunks
                total_chunks += new_chunks
                if new_chunks > 0:
                    console.print(f"[blue]Ingested code:[/blue] {file_path} ([cyan]{new_chunks} new chunks[/cyan])")
                else:
                    console.print(f"[yellow]Skipped code (already ingested):[/yellow] {file_path}")
            except Exception as e:
                failed_files.append(file_path)
                console.print(f"[red]Failed to ingest code:[/red] {file_path} - {e}")
                traceback.print_exc()
        console.print(f"[bold green]Ingestion complete. {len(doc_files)} document files, {len(code_files)} code files processed, {total_chunks} new chunks ({code_chunks} new code chunks) added.[/bold green]")
        if failed_files:
            console.print(f"[bold red]Failed files ({len(failed_files)}):[/bold red]")
            for f in failed_files:
                console.print(f"  - {f}")
        
        # Create a backup after successful ingestion
        post_backup_path = backup_chroma_db("post-ingestion")
        # Check DB integrity after ingestion and backup
        if not check_chroma_db_integrity():
            console.print("[bold red]ChromaDB integrity check failed after ingestion! Attempting to restore from pre-ingestion backup...[/bold red]")
            if pre_backup_path and restore_chroma_db_from_backup(pre_backup_path):
                console.print("[bold yellow]Restored ChromaDB from pre-ingestion backup due to integrity failure.[/bold yellow]")
            else:
                console.print("[bold red]Automatic restore failed. Manual intervention required.[/bold red]")
        else:
            console.print("[bold green]ChromaDB integrity verified after ingestion and backup.[/bold green]")
    except Exception as e:
        console.print(f"[bold red]Error during ingestion: {e}[/bold red]")
        logger.error(f"Ingestion error: {e}")
        traceback.print_exc()
        # On catastrophic failure, restore from pre-ingestion backup
        if pre_backup_path and restore_chroma_db_from_backup(pre_backup_path):
            console.print("[bold yellow]Restored ChromaDB from pre-ingestion backup due to ingestion error.[/bold yellow]")
        else:
            console.print("[bold red]Automatic restore failed. Manual intervention required.[/bold red]")

@cli.command()
def repair_db():
    """Attempt to repair a corrupted ChromaDB database by restoring from backup."""
    console.print("[bold blue]Attempting to repair ChromaDB database...[/bold blue]")
    
    if restore_chroma_db_from_backup():
        console.print("[bold green]ChromaDB repair successful![/bold green]")
    else:
        console.print("[bold red]ChromaDB repair failed. Try creating a new database.[/bold red]")
        if click.confirm("Do you want to create a new empty database?", default=True):
            try:
                if os.path.exists(CHROMA_DB_FOLDER):
                    # Backup the corrupted DB first
                    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                    corrupted_db_path = f"{CHROMA_DB_FOLDER}_corrupted_{timestamp}"
                    shutil.move(CHROMA_DB_FOLDER, corrupted_db_path)
                    console.print(f"[yellow]Moved corrupted database to: {corrupted_db_path}[/yellow]")
                
                # Create a new client, which will initialize a fresh database
                client = get_chroma_client(attempt_recovery=False)
                client.get_or_create_collection("knowledge")
                console.print("[bold green]Created new empty ChromaDB database.[/bold green]")
                console.print("[yellow]You will need to run 'ingest' again to populate the database.[/yellow]")
            except Exception as e:
                console.print(f"[bold red]Failed to create new database: {e}[/bold red]")

@cli.command()
def backup():
    """Create a backup of the ChromaDB database."""
    backup_path = backup_chroma_db("manual")
    if backup_path:
        console.print(f"[bold green]Backup created at: {backup_path}[/bold green]")
    else:
        console.print("[bold red]Backup failed.[/bold red]")

@cli.command()
def build():
    """Build and launch the MeAI desktop app."""
    exe = sys.executable
    if ' ' in exe:
        exe = f'"{exe}"'
    os.system(f"{exe} MeAI_app.py")

@cli.command()
def build_exe():
    """Build a Windows executable for MeAI using PyInstaller."""
    console.print("[bold blue]Building Windows executable with PyInstaller...[/bold blue]")
    import subprocess
    try:
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", "pyinstaller"
        ])
        subprocess.check_call([
            sys.executable, "-m", "PyInstaller",
            "--onefile", "--windowed", "--name", "MeAI", "MeAI_app.py"
        ])
        console.print("[bold green]Build complete! Check the dist/ folder for MeAI.exe.[/bold green]")
    except Exception as e:
        console.print(f"[bold red]Build failed: {e}[/bold red]")

# Helper: Retrieve context from ChromaDB
def retrieve_context(query, top_k=3):
    try:
        client = get_chroma_client()
        collection = client.get_or_create_collection("knowledge")
        results = collection.query(query_texts=[query], n_results=top_k)
        docs = [doc for doc in results.get("documents", [[]])[0]]
        return "\n".join(docs)
    except Exception as e:
        logger.error(f"Error retrieving context: {e}")
        console.print(f"[bold red]Error retrieving context: {e}[/bold red]")
        return "Error retrieving context from knowledge base."

if __name__ == "__main__":
    cli() 