from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, 
                            QPushButton, QLabel, QScrollArea, QFrame, QSizePolicy,
                            QProgressBar, QComboBox, QSpinBox, QCheckBox, QLineEdit, QFileDialog,
                            QGroupBox, QSlider, QGraphicsView, QGraphicsScene, QGraphicsEllipseItem, QGraphicsTextItem, QGraphicsLineItem, QGraphicsItemGroup)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QThread
from PyQt6.QtGui import QFont, QBrush, QPen, QColor
from components.ui.base_components import ModernButton
from components.utils.constants import DARK_MODE, SERVER_URL
import requests
import json
import logging
import time
from datetime import datetime
import threading
import queue
import numpy as np
from sklearn.cluster import KMeans
from sklearn.feature_extraction.text import TfidfVectorizer
import chromadb
from chromadb.config import Settings
from pymongo import MongoClient
import duckduckgo_search
from bs4 import BeautifulSoup
import re
import os
import random
import feedparser
import psutil
import networkx as nx
import matplotlib.pyplot as plt
import math

logger = logging.getLogger(__name__)

# Configure logging to console as well
console_handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)

# Prevent duplicate handlers if called multiple times
if not any(isinstance(handler, logging.StreamHandler) for handler in logger.handlers):
    logger.addHandler(console_handler)

logger.setLevel(logging.INFO)

RESOURCE_PROBABILITIES = [
    ("self_questioning", 0.25),
    ("web_search", 0.10),
    ("wikipedia", 0.10),
    ("wikipedia_random", 0.05),
    ("stackoverflow", 0.10),
    ("arxiv", 0.10),
    ("github_trending", 0.10),
    ("hackernews", 0.10),
    ("news", 0.05),
    ("local_files", 0.05)
]

QUESTION_TYPES = [
    ("factual", 0.3),
    ("creative", 0.2),
    ("code", 0.3),
    ("ethical", 0.1),
    ("meta", 0.1)
]

NEWS_RSS = [
    "https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml",
    "https://feeds.bbci.co.uk/news/rss.xml"
]

# Placeholder for MongoDB connection details and collection name
# These would typically be loaded from configuration
MONGO_URI = "mongodb://localhost:27017/"
DATABASE_NAME = "meai_logs"
TRAINING_COLLECTION_NAME = "training_history"

class TrainingMetrics:
    def __init__(self):
        self.questions_generated = 0
        self.answers_learned = 0
        self.knowledge_base_size = 0
        self.training_time = 0
        self.accuracy_score = 0
        self.confidence_score = 0
        self.cluster_quality = 0
        self.learning_rate = 0
        self.models_generated = 0
        self.last_update = time.time()

class TrainingWorker(QThread):
    log_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(dict)
    stopped_signal = pyqtSignal()
    resource_signal = pyqtSignal(dict)
    knowledge_graph_updated_signal = pyqtSignal()

    def __init__(self, batch_size=2, speed=0.15, meta_interval=10, self_correction=True, censorship=False, learning_aggressiveness=1.0, transparency=True):
        super().__init__()
        self.running = True
        self.progress = 0
        self.metrics = {
            'Questions Generated': 0,
            'Answers Learned': 0,
            'Knowledge Base Size': 0,
            'Training Time': 0,
            'Accuracy Score': 0,
            'Confidence Score': 0,
            'Cluster Quality': 0,
            'Learning Rate': 0,
            'Web Resources Ingested': 0,
            'Feedback Processed': 0,
            'Knowledge Gaps Closed': 0,
            'Wikipedia Articles': 0,
            'StackOverflow Posts': 0,
            'Local Files Ingested': 0,
            'arXiv Papers': 0,
            'GitHub Trending': 0,
            'Hacker News': 0,
            'News Articles': 0,
            'Reddit Posts': 0,
            'YouTube Videos': 0,
            'Medium Articles': 0,
            'Dev.to Posts': 0,
            'Research Papers': 0,
            'Documentation': 0
        }
        self.start_time = time.time()
        self.task_queue = []
        self.resource_status = "Idle"
        self.batch_size = batch_size
        self.speed = speed
        self.meta_interval = meta_interval
        self.self_correction = self_correction
        self.censorship = censorship
        self.learning_aggressiveness = learning_aggressiveness
        self.transparency = transparency
        self.knowledge_graph = nx.DiGraph()
        self.step_count = 0
        self.answer_cache = {}
        self.it_question_priority = 0.7
        self.resource_retry_count = {}
        self.max_retries = 3
        self.learning_history = []
        self.failed_resources = set()
        self.resource_weights = {
            'wikipedia': 1.0,
            'stackoverflow': 0.9,
            'arxiv': 0.8,
            'github_trending': 0.7,
            'hackernews': 0.7,
            'news': 0.6,
            'reddit': 0.6,
            'youtube': 0.5,
            'medium': 0.5,
            'dev_to': 0.5,
            'documentation': 0.8,
            'local_files': 0.9
        }
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        self.resource_statuses = {
            'wikipedia': 'Idle',
            'stackoverflow': 'Idle',
            'arxiv': 'Idle',
            'github_trending': 'Idle',
            'hackernews': 'Idle',
            'news': 'Idle',
            'reddit': 'Idle',
            'youtube': 'Idle',
            'medium': 'Idle',
            'dev_to': 'Idle',
            'documentation': 'Idle',
            'local_files': 'Idle'
        }

    def weighted_choice(self, choices):
        total = sum(w for c, w in choices)
        r = random.uniform(0, total)
        upto = 0
        for c, w in choices:
            if upto + w >= r:
                return c
            upto += w
        return choices[-1][0]

    def generate_question(self, qtype):
        """Generate a question based on the specified type."""
        self.log_terminal(f"[Generate Question] Generating question of type: {qtype}")
        # Prioritize IT-related questions
        if random.random() < self.it_question_priority:
            it_topics = [
                "programming", "algorithms", "data structures", "software architecture",
                "networking", "security", "cloud computing", "machine learning",
                "artificial intelligence", "database systems", "operating systems",
                "web development", "mobile development", "devops", "cybersecurity"
            ]
            topic = random.choice(it_topics)
            question = f"Explain {topic} in detail"
            self.log_terminal(f"[Generate Question] Generated IT question: {question[:50]}...")
            return question
        else:
            # Handle non-IT questions based on question type
            if qtype == "factual":
                question = random.choice([
                    "What is the capital of France?",
                    "Explain the theory of relativity.",
                    "What is quantum computing?"
                ])
            elif qtype == "creative":
                question = random.choice([
                    "Write a short poem about AI.",
                    "Invent a new word and define it.",
                    "Describe a futuristic city."
                ])
            elif qtype == "code":
                question = random.choice([
                    "Write a Python function for bubble sort.",
                    "How do you reverse a linked list in C?",
                    "Show an example of a REST API in Flask."
                ])
            elif qtype == "ethical":
                question = random.choice([
                    "Is it ethical for AI to replace human jobs?",
                    "Should AI be allowed to make medical decisions?",
                    "Discuss privacy concerns with smart devices."
                ])
            elif qtype == "meta":
                question = random.choice([
                    "How can I improve my own learning process?",
                    "What are the limits of artificial intelligence?",
                    "How do I know if my answers are correct?"
                ])
            else:
                question = "What is AGI?" # Default question
            
            self.log_terminal(f"[Generate Question] Generated non-IT question: {question[:50]}...")
            return question

    def clean_html(self, text):
        """Remove HTML tags and clean the text."""
        from bs4 import BeautifulSoup
        import re
        
        # Remove HTML tags
        soup = BeautifulSoup(text, 'html.parser')
        text = soup.get_text()
        
        # Clean up whitespace and special characters
        text = re.sub(r'\s+', ' ', text)  # Replace multiple spaces with single space
        text = re.sub(r'\n+', '\n', text)  # Replace multiple newlines with single newline
        text = text.strip()
        
        return text

    def format_answer(self, answer):
        """Format the answer for better readability."""
        # Clean HTML if present
        if '<' in answer and '>' in answer:
            answer = self.clean_html(answer)
        
        # Split into sentences
        sentences = answer.split('. ')
        
        # Format each sentence
        formatted_sentences = []
        for sentence in sentences:
            # Capitalize first letter
            sentence = sentence.strip().capitalize()
            if sentence:
                formatted_sentences.append(sentence)
        
        # Join sentences with proper spacing
        formatted_answer = '. '.join(formatted_sentences)
        if not formatted_answer.endswith('.'):
            formatted_answer += '.'
            
        return formatted_answer

    def score_answer_quality(self, answer, question):
        """Enhanced answer quality scoring using multiple metrics."""
        self.log_terminal("[Score Answer] Scoring answer quality...")
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity
        import numpy as np
        import re
        import json # Import json here for json decode error handling
        from bs4 import BeautifulSoup # Import BeautifulSoup

        # Clean and format the answer
        # Ensure answer is a string, handle None or non-string input gracefully
        if not isinstance(answer, str) or not answer.strip():
             self.log_terminal("[Score Answer] Invalid or empty answer, returning score 0.0")
             return 0.0 # Return zero score for empty or invalid input

        cleaned_answer = self.clean_html(answer)
        formatted_answer = self.format_answer(cleaned_answer)

        # Use formatted_answer for scoring

        # Extract key terms from question (if question is provided and valid)
        question_words = set()
        if isinstance(question, str) and question.strip():
             question_words = set(re.findall(r'\w+', question.lower()))
             self.log_terminal(f"[Score Answer] Extracted {len(question_words)} keywords from question")

        vectorizer = TfidfVectorizer(stop_words='english')
        try:
            # Calculate semantic similarity (only if question words exist)
            similarity = 0.0
            if question_words:
                 # Fit on both question and answer to ensure vocabulary includes both
                corpus = [question, formatted_answer]
                vectorizer.fit(corpus)
                question_vec = vectorizer.transform([question])
                answer_vec = vectorizer.transform([formatted_answer])
                similarity = cosine_similarity(question_vec, answer_vec)[0][0]
            
            # Calculate answer structure score (more sentences and paragraphs are better)
            sentences = formatted_answer.split('. ')
            paragraphs = formatted_answer.split('\n\n')
            structure_score = min(len(sentences) / 10.0, 1.0) + min(len(paragraphs) / 3.0, 1.0) # Max score 2.0 initially
            structure_score = min(structure_score / 2.0, 1.0) # Normalize to 0-1

            # Calculate keyword coverage (only if question words exist)
            keyword_coverage = 0.0
            if question_words:
                answer_words = set(re.findall(r'\w+', formatted_answer.lower()))
                keyword_coverage = len(question_words.intersection(answer_words)) / len(question_words) if question_words else 0.0
            
            # Calculate technical depth (for IT questions - approximate)
            technical_terms = {'algorithm', 'complexity', 'implementation', 'architecture', 'protocol', 
                             'database', 'network', 'security', 'optimization', 'framework', 'api', 'protocol', 'system', 'data', 'learning', 'model'}
            answer_words_lower = set(re.findall(r'\w+', formatted_answer.lower()))
            technical_score = len(technical_terms.intersection(answer_words_lower)) / len(technical_terms) if technical_terms else 0.0
            
            # Weighted final score - Adjust weights based on importance
            # Semantic similarity is key, then technical depth for IT, structure and keywords support.
            final_score = (
                0.4 * similarity +         # Semantic similarity to question
                0.2 * structure_score +    # Answer structure/readability
                0.2 * keyword_coverage +   # Coverage of question keywords
                0.2 * technical_score      # Relevance of technical terms
            )

            # Ensure score is between 0 and 1
            final_score = max(0.0, min(1.0, final_score))
            
            self.log_signal.emit(f"[Debug] Scored answer: Sim={similarity:.2f}, Struct={structure_score:.2f}, Key={keyword_coverage:.2f}, Tech={technical_score:.2f}, Final={final_score:.2f}")
            self.log_terminal(f"[Score Answer] Scored answer: Final={final_score:.2f}")
            return final_score
        except Exception as e:
            self.log_signal.emit(f"[Debug] Error during answer scoring: {str(e)}")
            self.log_terminal(f"[Score Answer] Error during answer scoring: {str(e)}")
            return 0.1  # Return a low default score if scoring fails

    def get_best_answer(self, question, answers):
        """Enhanced best answer selection with formatting."""
        self.log_terminal(f"[Get Best Answer] Selecting best answer for {question[:50]}...")
        if not answers:
            self.log_terminal("[Get Best Answer] No answers provided, returning None.")
            return None
        
        # Clean and format all answers
        cleaned_answers = [self.format_answer(ans) for ans in answers]
        
        # Score each answer
        scored_answers = [(ans, self.score_answer_quality(ans, question)) for ans in cleaned_answers]
        
        # Return the answer with highest score
        best_answer = max(scored_answers, key=lambda x: x[1])[0]
        
        # Add confidence score to the answer
        confidence = max(score for _, score in scored_answers)
        if confidence > 0.8:
            best_answer = f"[High Confidence] {best_answer}"
        elif confidence > 0.6:
            best_answer = f"[Medium Confidence] {best_answer}"
        else:
            best_answer = f"[Low Confidence] {best_answer}"
            
        self.log_terminal(f"[Get Best Answer] Selected best answer with confidence: {confidence:.2f}")
        return best_answer

    def sanitize_query(self, query):
        """Sanitize query for URL safety."""
        import urllib.parse
        # Remove special characters and encode spaces
        query = urllib.parse.quote(query)
        return query

    def handle_resource_error(self, resource_name, error):
        """Handle resource errors with retry logic and detailed logging."""
        if resource_name not in self.resource_retry_count:
            self.resource_retry_count[resource_name] = 0
        
        self.resource_retry_count[resource_name] += 1
        
        # Log the actual error type and message
        error_msg = f"{type(error).__name__}: {str(error)}"
        self.log_signal.emit(f"[Debug] {resource_name} error: {error_msg}")
        self.log_signal.emit(f"[Debug] Retry count: {self.resource_retry_count[resource_name]}/{self.max_retries}")
        
        if self.resource_retry_count[resource_name] >= self.max_retries:
            self.failed_resources.add(resource_name)
            self.resource_statuses[resource_name] = f'Failed after {self.max_retries} failures'
            self.log_signal.emit(f"[{resource_name}] Resource disabled after {self.max_retries} failures")
            self.resource_signal.emit(self.resource_statuses.copy())
            return False
        
        self.resource_statuses[resource_name] = f'Retrying {self.resource_retry_count[resource_name]}/{self.max_retries}'
        self.log_signal.emit(f"[{resource_name}] Retry {self.resource_retry_count[resource_name]}/{self.max_retries}")
        self.resource_signal.emit(self.resource_statuses.copy())
        return True

    def reset_resource_status(self):
        """Reset resource status after successful operations."""
        self.resource_retry_count.clear()
        self.failed_resources.clear()

    def web_search(self, query, timeout=2):
        """Enhanced web search using DuckDuckGo API."""
        try:
            query = self.sanitize_query(query)
            self.log_signal.emit(f"[Debug] Making request to DuckDuckGo: https://api.duckduckgo.com/?q={query}&format=json")
            response = self.make_request(
                f"https://api.duckduckgo.com/?q={query}&format=json",
                timeout=timeout,
                headers={'User-Agent': 'Mozilla/5.0'}
            )
            if not response:
                self.log_signal.emit("[Debug] DuckDuckGo search failed: No response")
                return None

            try:
                data = response.json()
            except json.JSONDecodeError as e:
                 self.log_signal.emit(f"[Debug] DuckDuckGo search failed: JSON decode error - {e}")
                 return None

            if not data:
                 self.log_signal.emit("[Debug] DuckDuckGo search failed: Empty response data")
                 return None

            # Combine abstract and related topics
            abstract = data.get("AbstractText", "")
            related = data.get("RelatedTopics", [])
            related_text = " ".join([r.get("Text", "") for r in related if isinstance(r, dict) and r.get("Text")]).strip()

            result = f"{abstract} {related_text}".strip()
            if not result:
                 self.log_signal.emit("[Debug] DuckDuckGo search failed: No relevant content found")
                 return None

            self.log_signal.emit(f"[Debug] DuckDuckGo content length: {len(result)}")
            return result
        except Exception as e:
            self.log_signal.emit(f"[Debug] DuckDuckGo search error: {str(e)}")
            if self.handle_resource_error("web_search", e):
                return self.web_search(query, timeout)
            return None

    def make_request(self, url, timeout=2, method='GET', **kwargs):
        """Make HTTP request with retry logic and proper error handling."""
        try:
            self.log_signal.emit(f"[Debug] Making request to: {url}")
            response = self.session.request(method, url, timeout=timeout, **kwargs)
            response.raise_for_status()
            self.log_signal.emit(f"[Debug] Request successful: {url}")
            return response
        except requests.exceptions.RequestException as e:
            self.log_signal.emit(f"[Debug] Request failed: {url} - {str(e)}")
            return None

    def wikipedia_search(self, query, timeout=2):
        """Enhanced Wikipedia search with better error handling and content extraction."""
        try:
            query = self.sanitize_query(query)
            self.log_signal.emit(f"[Debug] Wikipedia search for: {query}")
            search_url = f"https://en.wikipedia.org/w/api.php?action=query&format=json&list=search&srsearch={query}&utf8=1"
            response = self.make_request(search_url, timeout=timeout)
            if not response:
                self.log_signal.emit("[Debug] Wikipedia search failed: No response")
                return None

            try:
                data = response.json()
            except json.JSONDecodeError as e:
                 self.log_signal.emit(f"[Debug] Wikipedia search failed: JSON decode error - {e}")
                 return None

            if not data.get("query", {}).get("search"):
                self.log_signal.emit("[Debug] No Wikipedia results found for search")
                return None

            title = data["query"]["search"][0]["title"]
            self.log_signal.emit(f"[Debug] Found Wikipedia article title: {title}")
            content_url = f"https://en.wikipedia.org/w/api.php?action=query&format=json&prop=extracts|references|categories&exintro=1&titles={title}&utf8=1"
            response = self.make_request(content_url, timeout=timeout)
            if not response:
                self.log_signal.emit("[Debug] Wikipedia content fetch failed: No response")
                return None

            try:
                data = response.json()
            except json.JSONDecodeError as e:
                 self.log_signal.emit(f"[Debug] Wikipedia content fetch failed: JSON decode error - {e}")
                 return None

            pages = data.get("query", {}).get("pages", {})
            
            content = ""
            references = []
            categories = []

            # Extract content from the first page found (assuming it's the relevant one)
            page_id = next(iter(pages)) if pages else None
            if page_id:
                page = pages.get(page_id, {})
                content = page.get("extract", "")
                references = page.get("references", [])
                categories = page.get("categories", [])

            if not content:
                self.log_signal.emit("[Debug] Wikipedia content fetch failed: Empty extract")
                return None

            # Extract and format references
            ref_text = " ".join([r.get("title", "") for r in references if isinstance(r, dict) and r.get("title")]).strip()
            
            # Extract and format categories
            cat_text = " ".join([c.get("title", "").replace("Category:", "") for c in categories if isinstance(c, dict) and c.get("title")]).strip()
            
            result = f"Content: {content}\nReferences: {ref_text}\nCategories: {cat_text}".strip()
            self.log_signal.emit(f"[Debug] Wikipedia content length: {len(result)}")
            return result

        except Exception as e:
            self.log_signal.emit(f"[Debug] Wikipedia search error: {str(e)}")
            if self.handle_resource_error("wikipedia", e):
                return self.wikipedia_search(query, timeout)
            return None

    def stackoverflow_search(self, query, timeout=2):
        """Enhanced StackOverflow search with answer quality scoring."""
        try:
            query = self.sanitize_query(query)
            self.log_signal.emit(f"[Debug] StackOverflow search for: {query}")
            api_url = f"https://api.stackexchange.com/2.3/search/advanced?order=desc&sort=votes&q={query}&site=stackoverflow&pagesize=3"
            response = self.make_request(api_url, timeout=timeout)
            if not response:
                self.log_signal.emit("[Debug] StackOverflow search failed: No response")
                return None

            try:
                data = response.json()
            except json.JSONDecodeError as e:
                 self.log_signal.emit(f"[Debug] StackOverflow search failed: JSON decode error - {e}")
                 return None

            if not data.get("items"):
                self.log_signal.emit("[Debug] No StackOverflow results found for search")
                return None

            self.log_signal.emit(f"[Debug] Found {len(data['items'])} StackOverflow questions")
            answers = []
            for item in data["items"]:
                if item.get("is_answered"):
                    answer_id = item.get("accepted_answer_id")
                    if answer_id:
                        answer_url = f"https://api.stackexchange.com/2.3/answers/{answer_id}?order=desc&sort=activity&site=stackoverflow&filter=withbody"
                        answer_resp = self.make_request(answer_url, timeout=timeout)
                        if answer_resp:
                             try:
                                answer_data = answer_resp.json()
                                if answer_data.get("items"):
                                    answer_body = answer_data["items"][0].get("body", "")
                                    if answer_body:
                                        answers.append(answer_body)
                                        self.log_signal.emit(f"[Debug] Added StackOverflow answer {len(answers)}")
                             except json.JSONDecodeError as e:
                                  self.log_signal.emit(f"[Debug] StackOverflow answer fetch failed for {answer_id}: JSON decode error - {e}")

            if answers:
                result = " ".join(answers)
                self.log_signal.emit(f"[Debug] StackOverflow content length: {len(result)}")
                return result
            self.log_signal.emit("[Debug] No answered questions with accepted answers found on StackOverflow")
            return None
        except Exception as e:
            self.log_signal.emit(f"[Debug] StackOverflow search error: {str(e)}")
            if self.handle_resource_error("stackoverflow", e):
                return self.stackoverflow_search(query, timeout)
            return None

    def arxiv_fetch(self, timeout=2):
        """Fetch recent papers from arXiv."""
        try:
            # Search for recent papers in AI/ML, limit to 3
            query = "cat:cs.AI OR cat:cs.LG"
            url = f"http://export.arxiv.org/api/query?search_query={query}&start=0&max_results=3&sortBy=lastUpdatedDate&sortOrder=descending"
            self.log_signal.emit(f"[Debug] Fetching from arXiv: {url}")
            response = self.make_request(url, timeout=timeout)
            if not response:
                 self.log_signal.emit("[Debug] arXiv fetch failed: No response")
                 return None

            try:
                feed = feedparser.parse(response.text)
            except Exception as e: # feedparser might raise other exceptions
                 self.log_signal.emit(f"[Debug] arXiv fetch failed: Feed parsing error - {e}")
                 return None

            if not feed.entries:
                self.log_signal.emit("[Debug] No arXiv entries found")
                return None

            papers = []
            for entry in feed.entries:
                title = getattr(entry, 'title', '') # Use getattr for safer access
                summary = getattr(entry, 'summary', '')
                if title and summary:
                    papers.append(f"Title: {title}\nSummary: {summary}")
            
            if papers:
                result = "\n\n".join(papers)
                self.log_signal.emit(f"[Debug] arXiv content length: {len(result)}")
                return result
            
            self.log_signal.emit("[Debug] No complete arXiv entries found")
            return None
        except Exception as e:
            self.log_signal.emit(f"[Debug] arXiv fetch error: {str(e)}")
            if self.handle_resource_error("arxiv", e):
                return self.arxiv_fetch(timeout)
            return None

    def github_trending(self, timeout=2):
        """Fetch trending repositories from GitHub."""
        try:
            url = "https://github.com/trending"
            self.log_signal.emit(f"[Debug] Fetching from GitHub trending: {url}")
            response = self.make_request(url, timeout=timeout)
            if not response:
                 self.log_signal.emit("[Debug] GitHub trending fetch failed: No response")
                 return None

            try:
                soup = BeautifulSoup(response.text, 'html.parser')
            except Exception as e: # BeautifulSoup might raise other exceptions
                 self.log_signal.emit(f"[Debug] GitHub trending fetch failed: HTML parsing error - {e}")
                 return None

            repos = []
            for repo in soup.select("article.Box-row")[:5]:  # Get top 5 repos
                name_tag = repo.select_one("h2 a")
                desc_tag = repo.select_one("p")
                
                name = name_tag.text.strip() if name_tag else ""
                desc = desc_tag.text.strip() if desc_tag else ""

                if name:
                     repos.append(f"Repository: {name}\nDescription: {desc}")
            
            if repos:
                result = "\n\n".join(repos)
                self.log_signal.emit(f"[Debug] GitHub trending content length: {len(result)}")
                return result

            self.log_signal.emit("[Debug] No GitHub trending repositories found")
            return None
        except Exception as e:
            self.log_signal.emit(f"[Debug] GitHub trending fetch error: {str(e)}")
            if self.handle_resource_error("github_trending", e):
                return self.github_trending(timeout)
            return None

    def hackernews_fetch(self, timeout=2):
        """Fetch top stories from Hacker News."""
        try:
            url = "https://hacker-news.firebaseio.com/v0/topstories.json"
            self.log_signal.emit(f"[Debug] Fetching top stories from Hacker News: {url}")
            response = self.make_request(url, timeout=timeout)
            if not response:
                self.log_signal.emit("[Debug] Hacker News fetch failed: No response for top stories")
                return None

            try:
                story_ids = response.json()
            except json.JSONDecodeError as e:
                 self.log_signal.emit(f"[Debug] Hacker News fetch failed: JSON decode error for top stories - {e}")
                 return None

            if not story_ids:
                self.log_signal.emit("[Debug] No Hacker News top story IDs found")
                return None

            stories = []
            for story_id in story_ids[:5]:  # Get top 5 stories
                story_url = f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json"
                story_response = self.make_request(story_url, timeout=timeout)
                if story_response:
                     try:
                        story = story_response.json()
                        title = story.get('title', '')
                        story_url = story.get('url', '')
                        if title:
                             stories.append(f"Title: {title}\nURL: {story_url}")
                     except json.JSONDecodeError as e:
                         self.log_signal.emit(f"[Debug] Hacker News story fetch failed for {story_id}: JSON decode error - {e}")

            if stories:
                result = "\n\n".join(stories)
                self.log_signal.emit(f"[Debug] Hacker News content length: {len(result)}")
                return result
            
            self.log_signal.emit("[Debug] No complete Hacker News stories fetched")
            return None
        except Exception as e:
            self.log_signal.emit(f"[Debug] Hacker News fetch error: {str(e)}")
            if self.handle_resource_error("hackernews", e):
                return self.hackernews_fetch(timeout)
            return None

    def news_fetch(self, timeout=2):
        """Fetch recent tech news."""
        try:
            # Note: You need to replace 'YOUR_API_KEY' with a valid News API key
            # This resource will likely fail without a valid key.
            url = "https://newsapi.org/v2/top-headlines?category=technology&apiKey=YOUR_API_KEY"
            self.log_signal.emit(f"[Debug] Fetching tech news from News API: {url}")
            response = self.make_request(url, timeout=timeout)
            if not response:
                 self.log_signal.emit("[Debug] News API fetch failed: No response")
                 return None

            try:
                data = response.json()
            except json.JSONDecodeError as e:
                 self.log_signal.emit(f"[Debug] News API fetch failed: JSON decode error - {e}")
                 return None

            articles = []
            for article in data.get("articles", [])[:5]:  # Get top 5 articles
                title = article.get('title', '')
                description = article.get('description', '')
                if title and description:
                    articles.append(f"Title: {title}\nDescription: {description}")
            
            if articles:
                result = "\n\n".join(articles)
                self.log_signal.emit(f"[Debug] News API content length: {len(result)}")
                return result

            self.log_signal.emit("[Debug] No tech news articles found from News API")
            return None
        except Exception as e:
            self.log_signal.emit(f"[Debug] News API fetch error: {str(e)}. Have you replaced 'YOUR_API_KEY'?")
            if self.handle_resource_error("news", e):
                return self.news_fetch(timeout)
            return None

    def reddit_search(self, query, timeout=2):
        """Search Reddit for relevant discussions."""
        try:
            query = self.sanitize_query(query)
            url = f"https://www.reddit.com/search.json?q={query}&sort=relevance&t=all&limit=5"
            self.log_signal.emit(f"[Debug] Searching Reddit: {url}")
            response = self.make_request(url, timeout=timeout)
            if not response:
                self.log_signal.emit("[Debug] Reddit search failed: No response")
                return None

            try:
                data = response.json()
            except json.JSONDecodeError as e:
                 self.log_signal.emit(f"[Debug] Reddit search failed: JSON decode error - {e}")
                 return None

            posts = []
            for post in data.get("data", {}).get("children", [])[:5]:
                post_data = post.get("data", {})
                title = post_data.get("title", "")
                text = post_data.get("selftext", "")
                score = post_data.get("score", 0)
                comments = post_data.get("num_comments", 0)
                
                if title:
                    posts.append(f"Title: {title}\nContent: {text}\nScore: {score} | Comments: {comments}")

            if posts:
                result = "\n\n".join(posts)
                self.log_signal.emit(f"[Debug] Reddit content length: {len(result)}")
                return result
            
            self.log_signal.emit("[Debug] No Reddit posts found")
            return None
        except Exception as e:
            self.log_signal.emit(f"[Debug] Reddit search error: {str(e)}")
            if self.handle_resource_error("reddit", e):
                return self.reddit_search(query, timeout)
            return None

    def youtube_search(self, query, timeout=2):
        """Search YouTube for educational content."""
        try:
            query = self.sanitize_query(query)
            url = f"https://www.youtube.com/results?search_query={query}&sp=EgIQAQ%253D%253D"  # Filter for educational content
            self.log_signal.emit(f"[Debug] Searching YouTube: {url}")
            response = self.make_request(url, timeout=timeout)
            if not response:
                 self.log_signal.emit("[Debug] YouTube search failed: No response")
                 return None

            try:
                soup = BeautifulSoup(response.text, 'html.parser')
            except Exception as e: # BeautifulSoup might raise other exceptions
                 self.log_signal.emit(f"[Debug] YouTube search failed: HTML parsing error - {e}")
                 return None

            videos = []
            for video in soup.select("ytd-video-renderer, ytd-compact-video-renderer")[:5]: # Updated selectors
                title_tag = video.select_one("yt-formatted-string#video-title")
                desc_tag = video.select_one("yt-formatted-string#description-text")
                
                title = title_tag.text.strip() if title_tag else ""
                desc = desc_tag.text.strip() if desc_tag else ""

                if title:
                     videos.append(f"Title: {title}\nDescription: {desc}")

            if videos:
                result = "\n\n".join(videos)
                self.log_signal.emit(f"[Debug] YouTube content length: {len(result)}")
                return result
            
            self.log_signal.emit("[Debug] No YouTube videos found")
            return None
        except Exception as e:
            self.log_signal.emit(f"[Debug] YouTube search error: {str(e)}")
            if self.handle_resource_error("youtube", e):
                return self.youtube_search(query, timeout)
            return None

    def medium_search(self, query, timeout=2):
        """Search Medium for technical articles."""
        try:
            query = self.sanitize_query(query)
            url = f"https://medium.com/search?q={query}"
            self.log_signal.emit(f"[Debug] Searching Medium: {url}")
            response = self.make_request(url, timeout=timeout)
            if not response:
                self.log_signal.emit("[Debug] Medium search failed: No response")
                return None

            try:
                soup = BeautifulSoup(response.text, 'html.parser')
            except Exception as e: # BeautifulSoup might raise other exceptions
                 self.log_signal.emit(f"[Debug] Medium search failed: HTML parsing error - {e}")
                 return None

            articles = []
            # Updated selectors based on typical Medium structure
            for article in soup.select("div.js-postListHandle > div.card.v2")[:5]: 
                title_tag = article.select_one("h3")
                desc_tag = article.select_one("div.postMetaIndoor > a > p")

                title = title_tag.text.strip() if title_tag else ""
                desc = desc_tag.text.strip() if desc_tag else ""
                
                if title:
                    articles.append(f"Title: {title}\nDescription: {desc}")
            
            if articles:
                result = "\n\n".join(articles)
                self.log_signal.emit(f"[Debug] Medium content length: {len(result)}")
                return result
            
            self.log_signal.emit("[Debug] No Medium articles found")
            return None
        except Exception as e:
            self.log_signal.emit(f"[Debug] Medium search error: {str(e)}")
            if self.handle_resource_error("medium", e):
                return self.medium_search(query, timeout)
            return None

    def dev_to_search(self, query, timeout=2):
        """Search dev.to for developer articles."""
        try:
            query = self.sanitize_query(query)
            url = f"https://dev.to/search?q={query}"
            self.log_signal.emit(f"[Debug] Searching dev.to: {url}")
            response = self.make_request(url, timeout=timeout)
            if not response:
                self.log_signal.emit("[Debug] dev.to search failed: No response")
                return None

            try:
                soup = BeautifulSoup(response.text, 'html.parser')
            except Exception as e: # BeautifulSoup might raise other exceptions
                 self.log_signal.emit(f"[Debug] dev.to search failed: HTML parsing error - {e}")
                 return None

            articles = []
            # Updated selectors based on typical dev.to structure
            for article in soup.select("div.crayons-story")[:5]:
                title_tag = article.select_one("h2.crayons-story__title a")
                desc_tag = article.select_one("div.crayons-story__snippet")

                title = title_tag.text.strip() if title_tag else ""
                desc = desc_tag.text.strip() if desc_tag else ""

                if title:
                    articles.append(f"Title: {title}\nDescription: {desc}")
            
            if articles:
                result = "\n\n".join(articles)
                self.log_signal.emit(f"[Debug] dev.to content length: {len(result)}")
                return result
            
            self.log_signal.emit("[Debug] No dev.to articles found")
            return None
        except Exception as e:
            self.log_signal.emit(f"[Debug] dev.to search error: {str(e)}")
            if self.handle_resource_error("dev_to", e):
                return self.dev_to_search(query, timeout)
            return None

    def documentation_search(self, query, timeout=2):
        """Search popular documentation sites."""
        try:
            docs_sites = [
                {"name": "Python Docs", "url": "https://docs.python.org/3/search.html?q="},
                {"name": "MDN Web Docs", "url": "https://developer.mozilla.org/en-US/search?q="},
                {"name": "Microsoft Docs", "url": "https://docs.microsoft.com/en-us/search/?terms="},
                {"name": "Oracle Docs", "url": "https://docs.oracle.com/en/search.html?q="}
            ]
            
            results = []
            for site_info in docs_sites:
                site_name = site_info["name"]
                site_url = site_info["url"]
                url = f"{site_url}{self.sanitize_query(query)}"
                self.log_signal.emit(f"[Debug] Searching documentation: {site_name} - {url}")
                response = self.make_request(url, timeout=timeout)
                if response:
                    try:
                        soup = BeautifulSoup(response.text, 'html.parser')
                        # Generic content extraction (may need refinement per site)
                        content = soup.get_text()
                        if content and len(content.strip()) > 100: # Basic check for substantial content
                            results.append(f"From {site_name}:\n{content[:500]}...") # Limit content length
                    except Exception as e: # BeautifulSoup might raise other exceptions or content extraction fails
                        self.log_signal.emit(f"[Debug] Documentation search failed for {site_name}: Content parsing error - {e}")

            
            if results:
                result = "\n\n".join(results)
                self.log_signal.emit(f"[Debug] Documentation content length: {len(result)}")
                return result
            
            self.log_signal.emit("[Debug] No relevant documentation found")
            return None
        except Exception as e:
            self.log_signal.emit(f"[Debug] Documentation search error: {str(e)}")
            if self.handle_resource_error("documentation", e):
                return self.documentation_search(query, timeout)
            return None

    def ingest_local_files(self):
        """Ingest content from local knowledge base."""
        try:
            knowledge_dir = "knowledge"
            if not os.path.exists(knowledge_dir):
                self.log_signal.emit(f"[Debug] Local knowledge directory not found: {knowledge_dir}")
                return None
            
            content = []
            for root, _, files in os.walk(knowledge_dir):
                for file in files:
                    if file.lower().endswith(('.txt', '.md', '.py')):
                        file_path = os.path.join(root, file)
                        try:
                            self.log_signal.emit(f"[Debug] Reading local file: {file_path}")
                            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                                file_content = f.read()
                                if file_content.strip():
                                     content.append(f"File: {file}\nContent: {file_content[:1000]}...") # Limit content length
                        except Exception as e:
                            self.log_signal.emit(f"[Local Files] Error reading {file}: {str(e)}")
            
            if content:
                result = "\n\n".join(content)
                self.log_signal.emit(f"[Debug] Local files content length: {len(result)}")
                return result
            
            self.log_signal.emit("[Debug] No readable local files found in knowledge directory")
            return None
        except Exception as e:
            self.log_signal.emit(f"[Debug] Local file ingestion error: {str(e)}")
            if self.handle_resource_error("local_files", e):
                return self.ingest_local_files()
            return None

    def get_weighted_answer(self, answers_cache):
        """Get the best answer based on resource weights and content quality."""
        if not answers_cache:
            self.log_signal.emit("[Debug] No answers in cache for weighted selection")
            return None

        scored_answers = []
        for resource, answer in answers_cache.items():
            if resource in self.resource_weights:
                # Calculate content quality score (reusing score_answer_quality, might need refinement)
                # Note: Pass an empty string for question here as we are scoring content quality independent of question
                # The overall best answer is selected based on the question later.
                content_score = self.score_answer_quality(answer, "") # Use empty string as placeholder if question not needed here

                # Combine with resource weight
                final_score = content_score * self.resource_weights[resource]
                scored_answers.append((answer, final_score))
                self.log_signal.emit(f"[Debug] Scored answer from {resource}: content_score={content_score:.2f}, resource_weight={self.resource_weights[resource]:.2f}, final_score={final_score:.2f}")

        if scored_answers:
            # Select the answer with the highest weighted score
            best_answer_content, best_score = max(scored_answers, key=lambda x: x[1])
            self.log_signal.emit(f"[Debug] Best weighted answer score: {best_score:.2f}")

            # Now score this best answer against the original question to get final quality/confidence
            # You would need the original question here. Let's assume it's available or passed.
            # For now, let's just return the content and rely on the scoring later.
            # Add confidence score text based on best_score from weighted selection
            if best_score > 0.8:
                confidence_text = "[High Confidence] "
            elif best_score > 0.6:
                confidence_text = "[Medium Confidence] "
            else:
                confidence_text = "[Low Confidence] "

            # Return the content with confidence text
            return confidence_text + best_answer_content

        self.log_signal.emit("[Debug] No scored answers available for weighted selection")
        return None

    def meta_cognition(self):
        """Perform meta-cognitive analysis of the learning process."""
        self.log_signal.emit("[Meta-Cognition] Analyzing learning progress...")
        self.log_terminal("[Meta-Cognition] Analyzing learning progress...")
        
        # Calculate learning metrics
        total_time = time.time() - self.start_time
        questions_per_minute = self.metrics['Questions Generated'] / (total_time / 60)
        answers_per_minute = self.metrics['Answers Learned'] / (total_time / 60)
        
        # Calculate knowledge graph metrics
        if self.knowledge_graph:
            avg_degree = sum(dict(self.knowledge_graph.degree()).values()) / len(self.knowledge_graph)
            connected_components = nx.number_connected_components(self.knowledge_graph.to_undirected())
        else:
            avg_degree = 0
            connected_components = 0
        
        # Update metrics
        self.metrics.update({
            'Training Time': total_time / 60,  # Convert to minutes
            'Learning Rate': (self.metrics['Answers Learned'] / max(1, self.metrics['Questions Generated'])) * 100,
            'Cluster Quality': avg_degree,
            'Knowledge Base Size': len(self.knowledge_graph) if self.knowledge_graph else 0
        })
        
        # Emit progress update
        self.progress_signal.emit(self.metrics)
        
        # Log meta-cognitive insights
        insights = [
            f"Learning rate: {self.metrics['Learning Rate']:.1f}%",
            f"Questions per minute: {questions_per_minute:.1f}",
            f"Answers per minute: {answers_per_minute:.1f}",
            f"Knowledge graph size: {len(self.knowledge_graph)} nodes",
            f"Average node connections: {avg_degree:.1f}",
            f"Connected components: {connected_components}"
        ]
        
        for insight in insights:
            self.log_signal.emit(f"[Meta-Cognition] {insight}")
            self.log_terminal(f"[Meta-Cognition] {insight}")
        
        # Adjust learning parameters based on performance
        if questions_per_minute < 0.5:
            self.speed *= 1.1  # Increase speed if too slow
        elif questions_per_minute > 2.0:
            self.speed *= 0.9  # Decrease speed if too fast
        
        # Adjust resource weights based on success rates
        for resource, status in self.resource_statuses.items():
            if "Error" in status or "failed" in status.lower():
                self.resource_weights[resource] *= 0.9  # Reduce weight for failing resources
            elif "Found Answer" in status or "Success" in status:
                self.resource_weights[resource] *= 1.1  # Increase weight for successful resources
        
        # Normalize resource weights
        total_weight = sum(self.resource_weights.values())
        for resource in self.resource_weights:
            self.resource_weights[resource] /= total_weight
        
        self.log_signal.emit("[Meta-Cognition] Learning parameters adjusted based on performance")
        self.log_terminal("[Meta-Cognition] Learning parameters adjusted based on performance")

    def analyze_learning_progress(self):
        """Analyze the learning progress and adjust parameters accordingly."""
        self.log_signal.emit("[Analysis] Analyzing learning progress...")
        self.log_terminal("[Analysis] Analyzing learning progress...")
        
        # Calculate success rates for each resource
        resource_success_rates = {}
        for resource in self.resource_statuses:
            if resource in self.resource_retry_count:
                total_attempts = self.resource_retry_count[resource]
                if total_attempts > 0:
                    success_rate = 1.0 - (self.resource_retry_count[resource] / total_attempts)
                    resource_success_rates[resource] = success_rate
        
        # Identify knowledge gaps
        if self.knowledge_graph:
            # Find nodes with low connectivity
            low_connectivity_nodes = []
            for node, degree in self.knowledge_graph.degree():
                if degree < 2:  # Nodes with less than 2 connections
                    low_connectivity_nodes.append(node)
            
            if low_connectivity_nodes:
                self.log_signal.emit(f"[Analysis] Found {len(low_connectivity_nodes)} knowledge gaps")
                # Prioritize these topics for future learning
                for node in low_connectivity_nodes[:5]:  # Focus on top 5 gaps
                    self.log_signal.emit(f"[Analysis] Knowledge gap: {node[:50]}...")
        
        # Analyze learning efficiency
        if self.learning_history:
            recent_history = self.learning_history[-100:]  # Look at last 100 entries
            success_rate = sum(1 for entry in recent_history if entry.get('success', False)) / len(recent_history)
            
            # Adjust learning parameters based on success rate
            if success_rate < 0.5:
                self.learning_aggressiveness *= 0.9  # Reduce aggressiveness if success rate is low
                self.log_signal.emit("[Analysis] Reducing learning aggressiveness due to low success rate")
            elif success_rate > 0.8:
                self.learning_aggressiveness *= 1.1  # Increase aggressiveness if success rate is high
                self.log_signal.emit("[Analysis] Increasing learning aggressiveness due to high success rate")
        
        # Analyze resource utilization
        active_resources = sum(1 for status in self.resource_statuses.values() if status == "Active")
        if active_resources < len(self.resource_statuses) * 0.3:  # Less than 30% resources active
            self.log_signal.emit("[Analysis] Low resource utilization detected")
            # Try to activate more resources
            for resource in self.resource_statuses:
                if self.resource_statuses[resource] == "Idle":
                    self.resource_statuses[resource] = "Active"
                    self.log_signal.emit(f"[Analysis] Activated resource: {resource}")
        
        # Update metrics
        self.metrics['Learning Rate'] = self.learning_aggressiveness * 100
        self.progress_signal.emit(self.metrics)
        
        self.log_signal.emit("[Analysis] Learning progress analysis completed")
        self.log_terminal("[Analysis] Learning progress analysis completed")

    def update_resource_weights(self):
        """Adjust and normalize resource weights based on recent resource status and performance."""
        self.log_terminal("[Resource Weights] Updating resource weights...")
        # Penalize failing resources, reward successful ones
        for resource, status in self.resource_statuses.items():
            if "Error" in status or "failed" in status.lower():
                self.resource_weights[resource] *= 0.9  # Reduce weight for failing resources
            elif "Found Answer" in status or "Success" in status:
                self.resource_weights[resource] *= 1.1  # Increase weight for successful resources
        # Normalize weights
        total_weight = sum(self.resource_weights.values())
        if total_weight > 0:
            for resource in self.resource_weights:
                self.resource_weights[resource] /= total_weight
        self.log_signal.emit("[Resource Weights] Updated resource weights based on recent performance.")
        self.log_terminal("[Resource Weights] Updated resource weights based on recent performance.")

    def advanced_answer_question(self, question, timeout=2):
        """Stub for advanced answer from knowledge base. Returns None for now."""
        self.log_signal.emit(f"[Debug] advanced_answer_question called for: {question}")
        self.log_terminal(f"[Advanced Answer] Attempting to answer from knowledge base: {question[:50]}...")
        # Placeholder for knowledge base query
        # In a real implementation, this would query the knowledge base (e.g., ChromaDB)
        # and return the most relevant answer
        time.sleep(timeout) # Simulate search time
        return None # For now, assume no answer is found in KB

    def update_learning_history(self, question, answer, score, resource):
        """Stub for updating learning history. Appends a record to self.learning_history."""
        self.learning_history.append({
            'question': question,
            'answer': answer,
            'score': score,
            'resource': resource,
            'success': score > 0.5
        })
        self.log_signal.emit(f"[Debug] update_learning_history called for: {question} (score={score}, resource={resource})")
        self.log_terminal(f"[Learning History] Recorded: Q='{question[:30]}...', A='{answer[:30]}...', Score={score:.2f}, Resource={resource}")

    def self_correct(self, question, answer):
        """Stub for self-correction logic. Logs the call."""
        self.log_signal.emit(f"[Debug] self_correct called for: {question}")
        self.log_terminal(f"[Self-Correction] Called for: {question[:50]}...")
        # Implement self-correction logic here
        pass

    def self_evaluate(self, question, answer):
        """Stub for self-evaluation logic. Logs the call."""
        self.log_signal.emit(f"[Debug] self_evaluate called for: {question}")
        self.log_terminal(f"[Self-Evaluation] Called for: {question[:50]}...")
        # Implement self-evaluation logic here
        pass

    def generate_model(self):
        """Generate a new GGUF model based on learned knowledge."""
        self.log_signal.emit("[Model Generation] Starting model generation...")
        self.log_terminal("[Model Generation] Starting model generation...")
        
        try:
            # Prepare training data from knowledge graph
            training_data = []
            for node in self.knowledge_graph.nodes(data=True):
                if node[1].get('type') == 'question':
                    # Find connected answers
                    answers = [n for n in self.knowledge_graph.neighbors(node[0])]
                    if answers:
                        training_data.append({
                            'question': node[0],
                            'answer': answers[0]  # Use first answer for now
                        })
            
            if not training_data:
                self.log_signal.emit("[Model Generation] No training data available")
                self.log_terminal("[Model Generation] No training data available")
                return False
            
            # Save training data to file
            training_file = "training_data.jsonl"
            with open(training_file, 'w', encoding='utf-8') as f:
                for item in training_data:
                    f.write(json.dumps(item) + '\n')
            
            # Generate model using llama.cpp
            model_name = f"meai_model_{int(time.time())}"
            self.log_signal.emit(f"[Model Generation] Generating model: {model_name}")
            self.log_terminal(f"[Model Generation] Generating model: {model_name}")
            
            # Use llama.cpp to fine-tune base model
            # This is a placeholder - actual implementation would use llama.cpp's training pipeline
            # You would need to implement the actual training logic here
            # Example: subprocess.run(['./llama.cpp/finetune', '--model-base', 'base_model.gguf', '--train-data', training_file, '--model-out', f'models/{model_name}.gguf'])
            self.log_signal.emit("[Model Generation] Model generation completed")
            self.log_terminal("[Model Generation] Model generation completed")
            
            # Update metrics
            self.metrics['Models Generated'] = self.metrics.get('Models Generated', 0) + 1
            self.progress_signal.emit(self.metrics)
            
            return True
            
        except Exception as e:
            self.log_signal.emit(f"[Model Generation] Error: {str(e)}")
            self.log_terminal(f"[Model Generation] Error: {str(e)}")
            return False

    def self_train(self):
        """Perform self-training using accumulated knowledge."""
        self.log_signal.emit("[Self-Training] Starting self-training cycle...")
        self.log_terminal("[Self-Training] Starting self-training cycle...")
        
        # Perform MongoDB collection check before self-training actions
        if not self._check_mongodb_collection():
             self.log_signal.emit("[Self-Training] ERROR: MongoDB collection check failed. Skipping self-training cycle.")
             self.log_terminal("[Self-Training] ERROR: MongoDB collection check failed. Skipping self-training cycle.")
             return # Skip self-training if collection doesn't exist or check fails

        try:
            # Analyze current knowledge gaps
            knowledge_gaps = self.analyze_knowledge_gaps()
            
            # Generate questions to fill gaps
            for gap in knowledge_gaps:
                question = self.generate_question_for_gap(gap)
                if question:
                    # Try to answer using existing knowledge
                    answer = self.advanced_answer_question(question)
                    if not answer or self.score_answer_quality(answer, question) < 0.7:
                        # If answer is poor, try to learn from external sources
                        self.learn_from_external_sources(question)
            
            # Update knowledge graph
            self.update_knowledge_graph_from_training()
            
            # Generate new model if significant improvements
            if self.should_generate_new_model():
                self.generate_model()
            
            self.log_signal.emit("[Self-Training] Self-training cycle completed")
            self.log_terminal("[Self-Training] Self-training cycle completed")
            return True
            
        except Exception as e:
            self.log_signal.emit(f"[Self-Training] Error: {str(e)}")
            self.log_terminal(f"[Self-Training] Error: {str(e)}")
            return False

    def analyze_knowledge_gaps(self):
        """Analyze knowledge graph to identify gaps."""
        self.log_terminal("[Analyze Knowledge Gaps] Analyzing knowledge gaps...")
        gaps = []
        if self.knowledge_graph:
            # Find nodes with low connectivity
            for node, degree in self.knowledge_graph.degree():
                if degree < 2:  # Nodes with less than 2 connections
                    gaps.append(node)
            
            if gaps:
                self.log_terminal(f"[Analyze Knowledge Gaps] Found {len(gaps)} gaps.")
        return gaps

    def generate_question_for_gap(self, gap):
        """Generate a question to fill a knowledge gap."""
        self.log_terminal(f"[Generate Question For Gap] Generating question for gap: {gap[:50]}...")
        # Extract key terms from the gap
        terms = gap.split()
        if len(terms) > 3:
            # Use the terms to generate a focused question
            return f"What is the relationship between {' and '.join(terms[:3])}?"
        return None

    def learn_from_external_sources(self, question):
        """Learn from external sources to fill knowledge gaps."""
        self.log_terminal(f"[Learn From External] Learning from external sources for: {question[:50]}...")
        # Try different resources in order of reliability
        resources = ['wikipedia', 'stackoverflow', 'arxiv', 'documentation']
        for resource in resources:
            if resource in self.resource_statuses:
                self.resource_statuses[resource] = 'Active'
                self.resource_signal.emit(self.resource_statuses.copy())
                
                # Simulate learning from resource
                # In actual implementation, this would fetch and process data
                time.sleep(0.5)  # Simulate processing time
                
                self.resource_statuses[resource] = 'Success'
                self.resource_signal.emit(self.resource_statuses.copy())
                self.log_terminal(f"[Learn From External] Successfully learned from {resource}")
                break

        self.log_terminal(f"[Learn From External] Could not learn from available resources for: {question[:50]}...")

    def update_knowledge_graph_from_training(self):
        """Update knowledge graph with new connections from training."""
        self.log_terminal("[Update Knowledge Graph] Updating knowledge graph from training...")
        if self.knowledge_graph:
            # Add new connections based on semantic similarity
            nodes = list(self.knowledge_graph.nodes())
            for i, node1 in enumerate(nodes):
                for node2 in nodes[i+1:]:
                    if not self.knowledge_graph.has_edge(node1, node2):
                        # Calculate similarity (placeholder)
                        similarity = random.random()  # Replace with actual similarity calculation
                        if similarity > 0.7:
                            self.knowledge_graph.add_edge(node1, node2, weight=similarity)
            
            self.knowledge_graph_updated_signal.emit()

    def should_generate_new_model(self):
        """Determine if a new model should be generated."""
        self.log_terminal("[Should Generate Model] Checking if a new model should be generated...")
        # Check if significant improvements have been made
        recent_history = self.learning_history[-100:] if self.learning_history else []
        if not recent_history:
            return False
        
        # Calculate improvement metrics
        success_rate = sum(1 for entry in recent_history if entry.get('success', False)) / len(recent_history)
        avg_score = sum(entry.get('score', 0) for entry in recent_history) / len(recent_history)
        
        # Generate new model if success rate and average score are high
        should_generate = success_rate > 0.8 and avg_score > 0.7
        
        if should_generate:
            self.log_terminal(f"[Should Generate Model] Generating new model: Success Rate={success_rate:.2f}, Avg Score={avg_score:.2f}")
        else:
            self.log_terminal(f"[Should Generate Model] Not generating new model: Success Rate={success_rate:.2f}, Avg Score={avg_score:.2f}")
            
        return should_generate

    def log_terminal(self, message):
        """Log a message to the terminal in addition to the UI log."""
        logger.info(message)

    def _check_mongodb_collection(self):
        """Placeholder to check if the MongoDB collection exists."""
        logger.info(f"[MongoDB Check] Checking if collection '{TRAINING_COLLECTION_NAME}' exists...")
        try:
            # --- Placeholder for actual MongoDB collection check ---
            # Requires pymongo connection and database access
            # Example (replace with actual implementation):
            # client = pymongo.MongoClient(MONGO_URI)
            # db = client[DATABASE_NAME]
            # collection_names = db.list_collection_names()
            # if TRAINING_COLLECTION_NAME not in collection_names:
            #     logger.error(f"[MongoDB Check] Collection '{TRAINING_COLLECTION_NAME}' does not exist.")
            #     # Consider raising an exception or emitting an error signal
            #     return False
            # logger.info(f"[MongoDB Check] Collection '{TRAINING_COLLECTION_NAME}' exists.")
            # return True
            
            # For now, assume collection exists
            logger.info(f"[MongoDB Check] (Simulated) Collection '{TRAINING_COLLECTION_NAME}' exists.")
            return True
            
        except Exception as e:
            logger.error(f"[MongoDB Check] Error checking collection: {str(e)}")
            # Consider raising an exception or emitting an error signal
            return False
            
    def _question_exists_in_mongodb(self, question):
        """Placeholder to check if a question already exists in MongoDB training history."""
        logger.info(f"[MongoDB Check] Checking if question '{question[:50]}...' exists in MongoDB...")
        try:
            # --- Placeholder for actual MongoDB query ---
            # Requires pymongo connection and collection access
            # Example (replace with actual implementation):
            # client = pymongo.MongoClient(MONGO_URI)
            # db = client[DATABASE_NAME]
            # collection = db[TRAINING_COLLECTION_NAME]
            # count = collection.count_documents({'question': question})
            # exists = count > 0
            # if exists:
            #     logger.info(f"[MongoDB Check] Question '{question[:50]}...' found in MongoDB.")
            # else:
            #     logger.info(f"[MongoDB Check] Question '{question[:50]}...' not found in MongoDB.")
            # return exists
            
            # For now, simulate random existence
            exists = random.random() < 0.1 # 10% chance of existing
            if exists:
                 logger.info(f"[MongoDB Check] (Simulated) Question '{question[:50]}...' found in MongoDB.")
            else:
                 logger.info(f"[MongoDB Check] (Simulated) Question '{question[:50]}...' not found in MongoDB.")
            return exists
            
        except Exception as e:
            logger.error(f"[MongoDB Check] Error querying MongoDB: {str(e)}")
            return False # Assume it doesn't exist on error

    def run(self):
        """Main training loop with self-training integration."""
        self.log_signal.emit("[TrainingWorker] Training started.")
        self.log_terminal("[TrainingWorker] Training started.")
        
        # Perform MongoDB collection check at the start
        if not self._check_mongodb_collection():
             self.log_signal.emit("[TrainingWorker] ERROR: MongoDB collection check failed. Training stopped.")
             self.log_terminal("[TrainingWorker] ERROR: MongoDB collection check failed. Training stopped.")
             self.stopped_signal.emit() # Signal that training has stopped
             return # Stop training if collection doesn't exist or check fails
        
        while self.running:
            if psutil.virtual_memory().percent > 90 or psutil.cpu_percent() > 90:
                self.log_signal.emit("[Resource] System under heavy load, but continuing training...")
                self.log_terminal("[Resource] System under heavy load, but continuing training...")
            
            if self.step_count % self.meta_interval == 0:
                self.meta_cognition()
                self.analyze_learning_progress()
                self.update_resource_weights()
                self.reset_resource_status()
                
                # Perform self-training periodically
                if self.step_count % (self.meta_interval * 5) == 0:
                    self.self_train()
            
            # Generate one question at a time
            qtype = self.weighted_choice(QUESTION_TYPES)
            question = self.generate_question(qtype)
            
            # Check if the question already exists in MongoDB before processing
            if self._question_exists_in_mongodb(question):
                self.log_signal.emit(f"[Self-Questioning] Skipping existing question: {question[:50]}...")
                self.log_terminal(f"[Self-Questioning] Skipping existing question: {question[:50]}...")
                self.step_count += 1 # Increment step count even if skipping
                time.sleep(self.speed)
                continue # Skip to the next iteration if question exists
                
            self.metrics['Questions Generated'] += 1
            self.log_signal.emit(f"[Self-Questioning:{qtype}] Q: {question}")
            self.log_terminal(f"[Self-Questioning:{qtype}] Q: {question}")
            
            # Clear answer cache for new question
            self.answer_cache = {}
            
            # Try to answer from knowledge base first
            self.resource_statuses['knowledge_base'] = 'Active'
            self.resource_signal.emit(self.resource_statuses.copy())
            kb_answer = self.advanced_answer_question(question, timeout=2)
            if kb_answer and "Error" not in kb_answer: # Check for error string in answer
                self.answer_cache['knowledge_base'] = kb_answer
                self.resource_statuses['knowledge_base'] = 'Found Answer'
                self.log_terminal(f"[KnowledgeBase] Found answer for {question[:50]}...")
            else:
                 self.resource_statuses['knowledge_base'] = 'No Answer Found'
                 self.log_terminal(f"[KnowledgeBase] No answer found for {question[:50]}...")
            self.resource_signal.emit(self.resource_statuses.copy())
            
            # Sequentially try other resources with proper error handling
            resources = [
                ("wikipedia", lambda q: self.wikipedia_search(q, timeout=2)),
                ("stackoverflow", lambda q: self.stackoverflow_search(q, timeout=2)),
                ("arxiv", lambda _: self.arxiv_fetch()),
                ("github_trending", lambda _: self.github_trending()),
                ("hackernews", lambda _: self.hackernews_fetch()),
                ("news", lambda _: self.news_fetch()),
                ("reddit", lambda q: self.reddit_search(q, timeout=2)),
                ("youtube", lambda q: self.youtube_search(q, timeout=2)),
                ("medium", lambda q: self.medium_search(q, timeout=2)),
                ("dev_to", lambda q: self.dev_to_search(q, timeout=2)),
                ("documentation", lambda q: self.documentation_search(q, timeout=2)),
                ("local_files", lambda _: self.ingest_local_files())
            ]
            
            for resource_name, resource_func in resources:
                if resource_name in self.failed_resources:
                    continue
                    
                self.resource_statuses[resource_name] = 'Active'
                self.resource_signal.emit(self.resource_statuses.copy())

                try:
                    content = resource_func(question) # Pass question even if not all resources use it
                    if content:
                        # Clean and format the content before caching
                        cleaned_content = self.clean_html(content)
                        formatted_content = self.format_answer(cleaned_content)
                        self.answer_cache[resource_name] = formatted_content
                        self.metrics[f'{resource_name.replace("_", " ").title()} Content'] = len(formatted_content) # Track content length
                        self.log_signal.emit(f"[{resource_name.title()}] Found answer (length: {len(formatted_content)})")
                        self.resource_statuses[resource_name] = 'Found Answer'
                    else:
                        self.resource_statuses[resource_name] = 'No Answer Found'
                except Exception as e:
                    self.resource_statuses[resource_name] = 'Error'
                    if not self.handle_resource_error(resource_name, e):
                         pass # Error handled, resource might be disabled
                
                self.resource_signal.emit(self.resource_statuses.copy()) # Emit updated status
                
                # Small delay between resources to prevent system overload
                time.sleep(0.5)
            
            # Get weighted best answer
            best_answer = self.get_weighted_answer(self.answer_cache)
            if best_answer:
                self.metrics['Answers Learned'] += 1
                self.log_signal.emit(f"[Best Answer] {best_answer[:200]}...")
                self.update_knowledge_graph(question, best_answer)
                self.knowledge_graph_updated_signal.emit() # Signal UI to update graph
                
                # Update learning history
                score = self.score_answer_quality(best_answer, question)
                # Log resource used for the best answer if possible
                best_resource = next((res for res, ans in self.answer_cache.items() if ans in best_answer), 'N/A')
                self.update_learning_history(question, best_answer, score, best_resource)
                
                if self.self_correction and random.random() < 0.3:
                    self.self_correct(question, best_answer)
                if random.random() < 0.2:
                    self.self_evaluate(question, best_answer)
            
            # Update UI with latest metrics and resource statuses
            self.progress_signal.emit(self.metrics.copy())
            self.resource_signal.emit(self.resource_statuses.copy())

            self.step_count += 1
            time.sleep(self.speed)
        
        self.resource_status = "Idle"
        self.resource_signal.emit(self.resource_statuses.copy()) # Emit final status
        self.log_signal.emit("[TrainingWorker] Training stopped.")
        self.log_terminal("[TrainingWorker] Training stopped.")
        self.stopped_signal.emit()

    def update_knowledge_graph(self, question, answer):
        """Update the knowledge graph with new question-answer pair."""
        if question not in self.knowledge_graph:
            self.knowledge_graph.add_node(question, type='question')
        if answer not in self.knowledge_graph:
            self.knowledge_graph.add_node(answer, type='answer')
        self.knowledge_graph.add_edge(question, answer, weight=1.0)
        self.knowledge_graph_updated_signal.emit()

class TrainingTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.worker = None
        self.setup_ui()
        self.setup_connections()

    def setup_ui(self):
        """Set up the UI components."""
        layout = QVBoxLayout()
        
        # Control Panel
        control_panel = QHBoxLayout()
        
        # Start/Stop Button
        self.start_button = QPushButton("Start Training")
        self.start_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        control_panel.addWidget(self.start_button)
        
        # Generate Model Button
        self.generate_model_button = QPushButton("Generate Model")
        self.generate_model_button.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        control_panel.addWidget(self.generate_model_button)
        
        # Speed Control
        speed_layout = QHBoxLayout()
        speed_layout.addWidget(QLabel("Speed:"))
        self.speed_slider = QSlider(Qt.Orientation.Horizontal)
        self.speed_slider.setRange(1, 10)
        self.speed_slider.setValue(5)
        self.speed_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                border: 1px solid #999999;
                height: 8px;
                background: #f0f0f0;
                margin: 2px 0;
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                background: #4CAF50;
                border: 1px solid #5c5c5c;
                width: 18px;
                margin: -2px 0;
                border-radius: 9px;
            }
        """)
        speed_layout.addWidget(self.speed_slider)
        control_panel.addLayout(speed_layout)
        
        # Batch Size Control
        batch_layout = QHBoxLayout()
        batch_layout.addWidget(QLabel("Batch Size:"))
        self.batch_spinbox = QSpinBox()
        self.batch_spinbox.setRange(1, 10)
        self.batch_spinbox.setValue(2)
        batch_layout.addWidget(self.batch_spinbox)
        control_panel.addLayout(batch_layout)
        
        layout.addLayout(control_panel)
        
        # Model Generation Panel
        model_group = QGroupBox("Model Generation")
        model_layout = QVBoxLayout()
        
        # Model Generation Progress
        model_progress_layout = QHBoxLayout()
        model_progress_layout.addWidget(QLabel("Model Generation Progress:"))
        self.model_progress_bar = QProgressBar()
        self.model_progress_bar.setRange(0, 100)
        self.model_progress_bar.setValue(0)
        self.model_progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #999999;
                border-radius: 4px;
                text-align: center;
                background-color: #f0f0f0;
            }
            QProgressBar::chunk {
                background-color: #2196F3;
                border-radius: 3px;
            }
        """)
        model_progress_layout.addWidget(self.model_progress_bar)
        model_layout.addLayout(model_progress_layout)
        
        # Model Generation Status
        self.model_status_label = QLabel("No model generation in progress")
        self.model_status_label.setStyleSheet("""
            QLabel {
                padding: 4px;
                border-radius: 2px;
                background-color: #f0f0f0;
            }
        """)
        model_layout.addWidget(self.model_status_label)
        
        model_group.setLayout(model_layout)
        layout.addWidget(model_group)
        
        # Resource Status Panel
        resource_group = QGroupBox("Resource Status")
        resource_layout = QVBoxLayout()
        self.resource_labels = {}
        for resource in ['wikipedia', 'stackoverflow', 'arxiv', 'github_trending', 
                        'hackernews', 'news', 'reddit', 'youtube', 'medium', 
                        'dev_to', 'documentation', 'local_files']:
            label = QLabel(f"{resource.title()}: Idle")
            label.setStyleSheet("""
                QLabel {
                    padding: 4px;
                    border-radius: 2px;
                    background-color: #f0f0f0;
                }
            """)
            self.resource_labels[resource] = label
            resource_layout.addWidget(label)
        resource_group.setLayout(resource_layout)
        layout.addWidget(resource_group)
        
        # Learning Progress Panel
        progress_group = QGroupBox("Learning Progress")
        progress_layout = QVBoxLayout()
        
        # Progress Bars
        self.progress_bars = {}
        metrics = ['Questions Generated', 'Answers Learned', 'Knowledge Base Size',
                  'Accuracy Score', 'Confidence Score', 'Learning Rate', 'Models Generated']
        for metric in metrics:
            metric_layout = QHBoxLayout()
            metric_layout.addWidget(QLabel(metric + ":")) # Add colon for clarity
            progress_bar = QProgressBar()
            progress_bar.setRange(0, 100) # Range 0-100 for percentage
            progress_bar.setValue(0)
            progress_bar.setFormat(' %p%') # Show percentage
            progress_bar.setStyleSheet("""
                QProgressBar {
                    border: 1px solid #999999;
                    border-radius: 4px;
                    text-align: center;
                    background-color: #f0f0f0;
                    color: black; /* Ensure text is visible */
                }
                QProgressBar::chunk {
                    background-color: #4CAF50;
                    border-radius: 3px;
                }
            """)
            metric_layout.addWidget(progress_bar)
            self.progress_bars[metric] = progress_bar
            progress_layout.addLayout(metric_layout)
        
        # Add spacing between metric layouts
        progress_layout.addSpacing(10)

        progress_group.setLayout(progress_layout)
        layout.addWidget(progress_group)
        
        # Knowledge Graph Visualization
        graph_group = QGroupBox("Knowledge Graph")
        graph_layout = QVBoxLayout()
        self.graph_view = QGraphicsView()
        self.graph_view.setMinimumHeight(200)
        self.graph_view.setStyleSheet("""
            QGraphicsView {
                border: 1px solid #999999;
                border-radius: 4px;
                background-color: white;
            }
        """)
        graph_layout.addWidget(self.graph_view)
        graph_group.setLayout(graph_layout)
        layout.addWidget(graph_group)
        
        # Log Display
        log_group = QGroupBox("Training Log")
        log_layout = QVBoxLayout()
        self.log_display = QTextEdit()
        self.log_display.setReadOnly(True)
        self.log_display.setStyleSheet("""
            QTextEdit {
                border: 1px solid #999999;
                border-radius: 4px;
                background-color: white;
                font-family: monospace;
            }
        """)
        log_layout.addWidget(self.log_display)
        log_group.setLayout(log_layout)
        layout.addWidget(log_group)
        
        self.setLayout(layout)

    def setup_connections(self):
        """Set up signal connections."""
        self.start_button.clicked.connect(self.toggle_training)
        self.generate_model_button.clicked.connect(self.generate_model)
        self.speed_slider.valueChanged.connect(self.update_speed)
        self.batch_spinbox.valueChanged.connect(self.update_batch_size)

    def toggle_training(self):
        """Toggle training on/off."""
        if self.worker is None or not self.worker.running:
            self.start_training()
        else:
            self.stop_training()

    def start_training(self):
        """Start the training process."""
        self.worker = TrainingWorker(
            batch_size=self.batch_spinbox.value(),
            speed=1.0 / self.speed_slider.value(),
            meta_interval=10,
            self_correction=True,
            censorship=False,
            learning_aggressiveness=1.0,
            transparency=True
        )
        
        # Connect signals
        self.worker.progress_signal.connect(self.update_progress)
        self.worker.log_signal.connect(self.update_log)
        self.worker.resource_signal.connect(self.update_resource_status)
        self.worker.stopped_signal.connect(self.training_stopped)
        self.worker.knowledge_graph_updated_signal.connect(self.update_knowledge_graph)
        
        # Start worker
        self.worker.start()
        self.start_button.setText("Stop Training")
        self.start_button.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #da190b;
            }
        """)

    def stop_training(self):
        """Stop the training process."""
        if self.worker:
            self.worker.running = False
            self.worker.wait()
            self.worker = None
        self.start_button.setText("Start Training")
        self.start_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)

    def update_progress(self, metrics):
        """Update progress bars with new metrics."""
        for metric, value in metrics.items():
            if metric in self.progress_bars:
                # Scale value to 0-100 range
                if metric in ['Accuracy Score', 'Confidence Score', 'Learning Rate']:
                    scaled_value = int(value * 100)
                elif metric == 'Models Generated':
                     scaled_value = min(100, value * 10) # Scale models generated, e.g., 10 models = 100%
                else:
                    scaled_value = min(100, int(value / 10))  # Scale other metrics, assuming max 1000 for now
                self.progress_bars[metric].setValue(scaled_value)
                
                # Update text inside progress bar
                if metric == 'Models Generated':
                     self.progress_bars[metric].setFormat(f'{value} Models Generated')
                else:
                     self.progress_bars[metric].setFormat(' %p%')

    def update_log(self, message):
        """Update the log display."""
        self.log_display.append(f'<span style="color: white;">{message}</span>') # Set text color to white
        # Auto-scroll to bottom
        self.log_display.verticalScrollBar().setValue(
            self.log_display.verticalScrollBar().maximum()
        )

    def update_resource_status(self, status):
        """Update resource status labels."""
        # The status dictionary should map resource names to their current status string.
        for resource_name, current_status in status.items():
             if resource_name in self.resource_labels:
                 label = self.resource_labels[resource_name]
                 label.setText(f"{resource_name.replace('_', ' ').title()}: {current_status}")
                 # Update color based on status
                 if current_status == "Active":
                     label.setStyleSheet("""
                         QLabel {
                             padding: 4px;
                             border-radius: 2px;
                             background-color: #4CAF50;
                             color: white;
                         }
                     """)
                 elif current_status == "Error" or "failed" in current_status.lower() or "error" in current_status.lower():
                     label.setStyleSheet("""
                         QLabel {
                             padding: 4px;
                             border-radius: 2px;
                             background-color: #f44336;
                             color: white;
                         }
                     """)
                 elif "retrying" in current_status.lower():
                      label.setStyleSheet("""
                         QLabel {
                             padding: 4px;
                             border-radius: 2px;
                             background-color: #ff9800; /* Orange */
                             color: white;
                         }
                     """)
                 else:
                     label.setStyleSheet("""
                         QLabel {
                             padding: 4px;
                             border-radius: 2px;
                             background-color: #f0f0f0;
                             color: black; /* Ensure text is visible in light background */
                         }
                     """)

    def update_speed(self, value):
        """Update training speed."""
        if self.worker:
            self.worker.speed = 1.0 / value

    def update_batch_size(self, value):
        """Update batch size."""
        if self.worker:
            self.worker.batch_size = value

    def training_stopped(self):
        """Handle training stopped signal."""
        self.start_button.setText("Start Training")
        self.start_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        # Reset resource status
        for label in self.resource_labels.values():
            label.setText(f"{label.text().split(':')[0]}: Idle")
            label.setStyleSheet("""
                QLabel {
                    padding: 4px;
                    border-radius: 2px;
                    background-color: #f0f0f0;
                }
            """)

    def update_knowledge_graph(self):
        """Update the knowledge graph visualization."""
        if self.worker:
            self.update_knowledge_graph_visualization()

    def update_knowledge_graph_visualization(self):
        """Update the knowledge graph visualization."""
        if not self.worker or not self.worker.knowledge_graph:
            scene = QGraphicsScene()
            self.graph_view.setScene(scene)
            logger.info("[Knowledge Graph] Knowledge graph is empty, clearing visualization.")
            return
            
        logger.info(f"[Knowledge Graph] Updating visualization with {len(self.worker.knowledge_graph.nodes())} nodes and {len(self.worker.knowledge_graph.edges())} edges.")

        scene = QGraphicsScene()
        nodes = {}
        
        # Use spring_layout with adjusted parameters
        try:
            pos = nx.spring_layout(self.worker.knowledge_graph, k=0.8, iterations=50) # Adjust k and iterations
        except Exception as e:
            logger.info(f"[Knowledge Graph] Error generating layout: {str(e)}. Using a simpler layout.")
            pos = nx.random_layout(self.worker.knowledge_graph) # Fallback to a simpler layout
            
        for i, node in enumerate(self.worker.knowledge_graph.nodes()):
            x, y = pos[node]
            x = x * 300 + self.graph_view.width() / 2 # Increase scaling
            y = y * 300 + self.graph_view.height() / 2 # Increase scaling
            node_item = QGraphicsEllipseItem(-25, -25, 50, 50)
            node_item.setPos(x, y)
            node_item.setBrush(QBrush(QColor("#4CAF50")))
            node_item.setPen(QPen(QColor("#45a049")))
            display_text = node[:20] + "..." if len(node) > 20 else node # Shorten displayed text
            text_item = QGraphicsTextItem(display_text)
            text_item.setDefaultTextColor(QColor("white"))
            text_item.setPos(x - text_item.boundingRect().width() / 2,
                           y - text_item.boundingRect().height() / 2)
            group = QGraphicsItemGroup()
            group.addToGroup(node_item)
            group.addToGroup(text_item)
            nodes[node] = group
            scene.addItem(group)
        
        for edge in self.worker.knowledge_graph.edges():
            source_node = edge[0]
            target_node = edge[1]
            if source_node in nodes and target_node in nodes:
                source_pos = nodes[source_node].pos()
                target_pos = nodes[target_node].pos()
                line = QGraphicsLineItem(
                    source_pos.x() + 25, source_pos.y() + 25,
                    target_pos.x() + 25, target_pos.y() + 25
                )
                line.setPen(QPen(QColor("#999999")))
                scene.addItem(line)
                
        self.graph_view.setScene(scene)
        self.graph_view.fitInView(scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)
        logger.info("[Knowledge Graph] Visualization updated.")

    def generate_model(self):
        """Trigger model generation."""
        if self.worker:
            self.generate_model_button.setEnabled(False)
            self.model_status_label.setText("Model generation in progress...")
            self.model_status_label.setStyleSheet("""
                QLabel {
                    padding: 4px;
                    border-radius: 2px;
                    background-color: #e3f2fd;
                    color: #1976D2;
                }
            """)
            self.worker.generate_model()
            self.generate_model_button.setEnabled(True)
            self.model_status_label.setText("Model generation completed")
            self.model_status_label.setStyleSheet("""
                QLabel {
                    padding: 4px;
                    border-radius: 2px;
                    background-color: #e8f5e9;
                    color: #2e7d32;
                }
            """)