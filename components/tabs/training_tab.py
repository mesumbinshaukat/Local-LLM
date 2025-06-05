from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, 
                            QPushButton, QLabel, QScrollArea, QFrame, QSizePolicy,
                            QProgressBar, QComboBox, QSpinBox, QCheckBox, QLineEdit, QFileDialog)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QThread
from PyQt6.QtGui import QFont
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

logger = logging.getLogger(__name__)

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
    ("factual", 0.4),
    ("creative", 0.2),
    ("code", 0.2),
    ("ethical", 0.1),
    ("meta", 0.1)
]

NEWS_RSS = [
    "https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml",
    "https://feeds.bbci.co.uk/news/rss.xml"
]

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
        self.last_update = time.time()

class TrainingWorker(QThread):
    log_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(dict)
    stopped_signal = pyqtSignal()
    resource_signal = pyqtSignal(str)

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
            'News Articles': 0
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

    def run(self):
        self.log_signal.emit("[TrainingWorker] Training started.")
        logger.info("[TrainingWorker] Training started.")
        while self.running:
            # Only log heavy load, do not pause
            if psutil.virtual_memory().percent > 90 or psutil.cpu_percent() > 90:
                self.log_signal.emit("[Resource] System under heavy load, but continuing training...")
            # Meta-cognition: every meta_interval steps, reflect and plan
            if self.step_count % self.meta_interval == 0:
                self.meta_cognition()
            # Weighted random resource selection
            for _ in range(self.batch_size):
                resource = self.weighted_choice(RESOURCE_PROBABILITIES)
                self.resource_status = resource
                self.resource_signal.emit(self.resource_status)
                try:
                    if resource == "self_questioning":
                        qtype = self.weighted_choice(QUESTION_TYPES)
                        question = self.generate_question(qtype)
                        self.metrics['Questions Generated'] += 1
                        self.log_signal.emit(f"[Self-Questioning:{qtype}] Q: {question}")
                        answer = self.advanced_answer_question(question, timeout=2)
                        self.metrics['Answers Learned'] += 1
                        self.log_signal.emit(f"[Self-Questioning:{qtype}] A: {answer}")
                        self.update_knowledge_graph(question, answer)
                        if self.self_correction and random.random() < 0.3:
                            self.self_correct(question, answer)
                        if random.random() < 0.2:
                            self.self_evaluate(question, answer)
                    elif resource == "web_search":
                        web_content = self.web_search(question, timeout=2)
                        if web_content:
                            self.metrics['Web Resources Ingested'] += 1
                            self.log_signal.emit(f"[WebSearch] Ingested: {web_content[:80]}...")
                    elif resource == "wikipedia":
                        wiki_content = self.wikipedia_search(question, timeout=2)
                        if wiki_content:
                            self.metrics['Wikipedia Articles'] += 1
                            self.log_signal.emit(f"[Wikipedia] Ingested: {wiki_content[:80]}...")
                    elif resource == "wikipedia_random":
                        wiki_content = self.wikipedia_random(timeout=2)
                        if wiki_content:
                            self.metrics['Wikipedia Articles'] += 1
                            self.log_signal.emit(f"[Wikipedia:Random] Ingested: {wiki_content[:80]}...")
                    elif resource == "stackoverflow":
                        so_content = self.stackoverflow_search(question, timeout=2)
                        if so_content:
                            self.metrics['StackOverflow Posts'] += 1
                            self.log_signal.emit(f"[StackOverflow] Ingested: {so_content[:80]}...")
                    elif resource == "arxiv":
                        arxiv_content = self.arxiv_fetch(timeout=2)
                        if arxiv_content:
                            self.metrics['arXiv Papers'] += 1
                            self.log_signal.emit(f"[arXiv] Ingested: {arxiv_content[:80]}...")
                    elif resource == "github_trending":
                        gh_content = self.github_trending(timeout=2)
                        if gh_content:
                            self.metrics['GitHub Trending'] += 1
                            self.log_signal.emit(f"[GitHub] Ingested: {gh_content[:80]}...")
                    elif resource == "hackernews":
                        hn_content = self.hackernews_fetch(timeout=2)
                        if hn_content:
                            self.metrics['Hacker News'] += 1
                            self.log_signal.emit(f"[HackerNews] Ingested: {hn_content[:80]}...")
                    elif resource == "news":
                        news_content = self.news_fetch(timeout=2)
                        if news_content:
                            self.metrics['News Articles'] += 1
                            self.log_signal.emit(f"[News] Ingested: {news_content[:80]}...")
                    elif resource == "local_files":
                        local_content = self.ingest_local_files()
                        if local_content:
                            self.metrics['Local Files Ingested'] += 1
                            self.log_signal.emit(f"[LocalFiles] Ingested: {local_content[:80]}...")
                except Exception as e:
                    self.log_signal.emit(f"[{resource}] Skipped due to error: {e}")
            self.progress_signal.emit(self.metrics.copy())
            self.step_count += 1
            time.sleep(self.speed)
        self.resource_status = "Idle"
        self.resource_signal.emit(self.resource_status)
        self.log_signal.emit("[TrainingWorker] Training stopped.")
        logger.info("[TrainingWorker] Training stopped.")
        self.stopped_signal.emit()

    def weighted_choice(self, choices):
        total = sum(w for _, w in choices)
        r = random.uniform(0, total)
        upto = 0
        for c, w in choices:
            if upto + w >= r:
                return c
            upto += w
        return choices[0][0]

    def generate_question(self, qtype):
        if qtype == "factual":
            return random.choice([
                "What is the capital of France?",
                "Explain the theory of relativity.",
                "What is quantum computing?"
            ])
        elif qtype == "creative":
            return random.choice([
                "Write a short poem about AI.",
                "Invent a new word and define it.",
                "Describe a futuristic city."
            ])
        elif qtype == "code":
            return random.choice([
                "Write a Python function for bubble sort.",
                "How do you reverse a linked list in C?",
                "Show an example of a REST API in Flask."
            ])
        elif qtype == "ethical":
            return random.choice([
                "Is it ethical for AI to replace human jobs?",
                "Should AI be allowed to make medical decisions?",
                "Discuss privacy concerns with smart devices."
            ])
        elif qtype == "meta":
            return random.choice([
                "How can I improve my own learning process?",
                "What are the limits of artificial intelligence?",
                "How do I know if my answers are correct?"
            ])
        return "What is AGI?"

    def self_evaluate(self, question, answer):
        # Simulate self-evaluation
        score = random.randint(1, 10)
        self.metrics['Accuracy Score'] = (self.metrics['Accuracy Score'] + score) / 2
        self.metrics['Confidence Score'] = (self.metrics['Confidence Score'] + random.uniform(0.5, 1.0)) / 2
        self.log_signal.emit(f"[Self-Eval] Q: {question} | A: {answer} | Score: {score}")

    def advanced_answer_question(self, question, timeout=2):
        # Multi-step reasoning: break down complex queries
        if any(word in question.lower() for word in ["explain", "how", "why", "step", "process"]):
            self.log_signal.emit(f"[Reasoning] Breaking down complex question: {question}")
            sub_questions = [f"Step {i+1} of: {question}" for i in range(2)]
            answers = []
            for sq in sub_questions:
                ans = self.answer_question(sq, timeout=timeout)
                answers.append(ans)
            return "\n".join(answers)
        else:
            return self.answer_question(question, timeout=timeout)

    def self_correct(self, question, answer):
        # Re-ask or rephrase, compare answers, resolve contradictions
        rephrased = f"Can you answer this differently: {question}"
        alt_answer = self.answer_question(rephrased, timeout=2)
        if alt_answer.strip() != answer.strip():
            self.log_signal.emit(f"[Self-Correction] Contradiction detected. Original: {answer} | New: {alt_answer}")
            # Attempt to resolve (for now, just log)
            self.metrics['Knowledge Gaps Closed'] += 1
        else:
            self.log_signal.emit(f"[Self-Correction] No contradiction detected.")

    def update_knowledge_graph(self, question, answer):
        # Add nodes and edges for Q/A
        self.knowledge_graph.add_node(question, type="question")
        self.knowledge_graph.add_node(answer, type="answer")
        self.knowledge_graph.add_edge(question, answer, relation="answered_by")
        # Optionally, extract concepts/entities and link
        # (Placeholder for future NLP-based extraction)

    def answer_question(self, question, timeout=2):
        try:
            resp = requests.post(f"{SERVER_URL}/chat", json={"messages": [{"role": "user", "content": question}], "query": question}, timeout=timeout)
            if resp.status_code == 200:
                return resp.json().get("response", "[No answer]")
            return "[No answer]"
        except Exception as e:
            return f"[Error: {e}]"

    def web_search(self, query, timeout=2):
        try:
            resp = requests.get(f"https://api.duckduckgo.com/?q={query}&format=json", timeout=timeout)
            if resp.status_code == 200:
                data = resp.json()
                return data.get("AbstractText", "[No web content]")
            return "[No web content]"
        except Exception as e:
            return f"[Web search error: {e}]"

    def wikipedia_search(self, query, timeout=2):
        try:
            resp = requests.get(f"https://en.wikipedia.org/w/api.php?action=query&format=json&list=search&srsearch={query}&utf8=1", timeout=timeout)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("query", {}).get("search"):
                    title = data["query"]["search"][0]["title"]
                    resp = requests.get(f"https://en.wikipedia.org/w/api.php?action=query&format=json&prop=extracts&exintro=1&titles={title}&utf8=1", timeout=timeout)
                    if resp.status_code == 200:
                        data = resp.json()
                        pages = data.get("query", {}).get("pages", {})
                        for page_id in pages:
                            return pages[page_id].get("extract", "[No Wikipedia content]")
            return "[No Wikipedia content]"
        except Exception as e:
            return f"[Wikipedia error: {e}]"

    def stackoverflow_search(self, query, timeout=2):
        try:
            feed = feedparser.parse(f"https://stackoverflow.com/feeds/tag/{query}")
            if feed.entries:
                return feed.entries[0].summary
            return "[No StackOverflow content]"
        except Exception as e:
            return f"[StackOverflow error: {e}]"

    def ingest_local_files(self):
        try:
            knowledge_dir = "knowledge"
            if os.path.exists(knowledge_dir):
                files = os.listdir(knowledge_dir)
                if files:
                    file_path = os.path.join(knowledge_dir, random.choice(files))
                    with open(file_path, 'r', encoding='utf-8') as f:
                        return f.read()
            return "[No local files]"
        except Exception as e:
            return f"[Local file error: {e}]"

    def wikipedia_random(self, timeout=2):
        try:
            resp = requests.get("https://en.wikipedia.org/api/rest_v1/page/random/summary", timeout=timeout)
            if resp.status_code == 200:
                data = resp.json()
                return data.get("extract", "[No Wikipedia random content]")
            return "[No Wikipedia random content]"
        except Exception as e:
            return f"[Wikipedia random error: {e}]"

    def arxiv_fetch(self, timeout=2):
        try:
            feed = feedparser.parse("http://export.arxiv.org/rss/cs")
            if feed.entries:
                return feed.entries[0].summary
            return "[No arXiv content]"
        except Exception as e:
            return f"[arXiv error: {e}]"

    def github_trending(self, timeout=2):
        try:
            resp = requests.get("https://github.com/trending", timeout=timeout)
            if resp.status_code == 200:
                # crude extraction of repo name and description
                import re
                matches = re.findall(r'<h2.*?>(.*?)</h2>.*?<p.*?>(.*?)</p>', resp.text, re.DOTALL)
                if matches:
                    repo, desc = matches[0]
                    return f"{repo.strip()}: {desc.strip()}"
            return "[No GitHub trending content]"
        except Exception as e:
            return f"[GitHub trending error: {e}]"

    def hackernews_fetch(self, timeout=2):
        try:
            feed = feedparser.parse("https://news.ycombinator.com/rss")
            if feed.entries:
                return feed.entries[0].title + ": " + feed.entries[0].summary
            return "[No Hacker News content]"
        except Exception as e:
            return f"[Hacker News error: {e}]"

    def news_fetch(self, timeout=2):
        try:
            for url in NEWS_RSS:
                feed = feedparser.parse(url)
                if feed.entries:
                    return feed.entries[0].title + ": " + feed.entries[0].summary
            return "[No News content]"
        except Exception as e:
            return f"[News error: {e}]"

    def meta_cognition(self):
        # Reflect on knowledge, identify gaps, plan new learning
        self.log_signal.emit("[Meta-Cognition] Reflecting on knowledge and planning new learning goals...")
        # Example: generate a 'what do I not know?' question
        gap_question = "What are the most important topics I have not learned yet?"
        self.task_queue.append(gap_question)
        # Example: plan a new learning goal
        plan = "Learn about the latest advances in AGI architectures."
        self.task_queue.append(plan)
        # Self-reflection summary
        summary = f"I have learned {self.metrics['Answers Learned']} answers, but my knowledge graph has {self.knowledge_graph.number_of_nodes()} nodes. I should focus on areas with fewer connections."
        self.log_signal.emit(f"[Meta-Cognition] Self-reflection: {summary}")
        self.log_signal.emit(f"[Meta-Cognition] Added tasks: {gap_question}, {plan}")

    def inject_manual_task(self, task):
        self.task_queue.append(task)

class TrainingTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.worker = None
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        title = QLabel("MeAI Self-Training Center")
        title.setStyleSheet(f"color: {DARK_MODE['accent']}; font-size: 22px; font-weight: bold;")
        layout.addWidget(title)
        # AGI Policy controls
        policy_panel = QHBoxLayout()
        self.censorship_box = QComboBox()
        self.censorship_box.addItems(["No Censorship", "Censored"])
        self.censorship_box.setCurrentIndex(0)
        self.aggressiveness_slider = QSpinBox()
        self.aggressiveness_slider.setMinimum(1)
        self.aggressiveness_slider.setMaximum(10)
        self.aggressiveness_slider.setValue(5)
        self.aggressiveness_slider.setPrefix("Aggressiveness: ")
        self.transparency_box = QComboBox()
        self.transparency_box.addItems(["Full", "Medium", "Minimal"])
        self.transparency_box.setCurrentIndex(0)
        policy_panel.addWidget(self.censorship_box)
        policy_panel.addWidget(self.aggressiveness_slider)
        policy_panel.addWidget(self.transparency_box)
        layout.addLayout(policy_panel)
        # Settings panel
        settings_panel = QHBoxLayout()
        self.speed_box = QSpinBox()
        self.speed_box.setMinimum(1)
        self.speed_box.setMaximum(20)
        self.speed_box.setValue(2)
        self.speed_box.setPrefix("Speed: ")
        self.batch_box = QSpinBox()
        self.batch_box.setMinimum(1)
        self.batch_box.setMaximum(10)
        self.batch_box.setValue(2)
        self.batch_box.setPrefix("Batch: ")
        settings_panel.addWidget(self.speed_box)
        settings_panel.addWidget(self.batch_box)
        layout.addLayout(settings_panel)
        # Control panel
        control_panel = QHBoxLayout()
        self.start_btn = ModernButton("Start Training")
        self.stop_btn = ModernButton("Stop Training")
        self.stop_btn.setEnabled(False)
        self.start_btn.clicked.connect(self.start_training)
        self.stop_btn.clicked.connect(self.stop_training)
        # Knowledge graph controls
        self.visualize_btn = ModernButton("Visualize Knowledge Graph")
        self.visualize_btn.clicked.connect(self.visualize_knowledge_graph)
        self.export_btn = ModernButton("Export Knowledge Graph")
        self.export_btn.clicked.connect(self.export_knowledge_graph)
        control_panel.addWidget(self.start_btn)
        control_panel.addWidget(self.stop_btn)
        control_panel.addWidget(self.visualize_btn)
        control_panel.addWidget(self.export_btn)
        layout.addLayout(control_panel)
        # Resource status
        self.resource_label = QLabel("Resource: Idle")
        self.resource_label.setStyleSheet(f"color: {DARK_MODE['text']}; font-style: italic;")
        layout.addWidget(self.resource_label)
        # Progress bars for key metrics only
        self.metric_bars = {}
        key_metrics = [
            'Questions Generated', 'Answers Learned', 'Knowledge Base Size', 'Training Time',
            'Accuracy Score', 'Confidence Score'
        ]
        for metric in key_metrics:
            bar = QProgressBar()
            bar.setMaximum(100)
            bar.setValue(0)
            bar.setFormat(f"{metric}: %v")
            layout.addWidget(bar)
            self.metric_bars[metric] = bar
        # Collapsible/scrollable section for other metrics
        from PyQt6.QtWidgets import QScrollArea, QWidget, QFormLayout
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        metrics_widget = QWidget()
        metrics_layout = QFormLayout(metrics_widget)
        other_metrics = [
            'Cluster Quality', 'Learning Rate', 'Web Resources Ingested', 'Feedback Processed',
            'Knowledge Gaps Closed', 'Wikipedia Articles', 'StackOverflow Posts',
            'Local Files Ingested', 'arXiv Papers', 'GitHub Trending', 'Hacker News', 'News Articles'
        ]
        for metric in other_metrics:
            bar = QProgressBar()
            bar.setMaximum(100)
            bar.setValue(0)
            bar.setFormat(f"{metric}: %v")
            metrics_layout.addRow(bar)
            self.metric_bars[metric] = bar
        scroll_area.setWidget(metrics_widget)
        layout.addWidget(scroll_area)
        # Manual task injection
        manual_layout = QHBoxLayout()
        self.manual_input = QLineEdit()
        self.manual_input.setPlaceholderText("Enter custom question/resource...")
        self.manual_btn = ModernButton("Inject Task")
        self.manual_btn.clicked.connect(self.inject_manual_task)
        manual_layout.addWidget(self.manual_input)
        manual_layout.addWidget(self.manual_btn)
        layout.addLayout(manual_layout)
        # Log display
        self.log_display = QTextEdit()
        self.log_display.setReadOnly(True)
        self.log_display.setStyleSheet(f"background: {DARK_MODE['background']}; color: {DARK_MODE['text']};")
        layout.addWidget(self.log_display)

    def start_training(self):
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.log_display.clear()
        batch = self.batch_box.value()
        speed = 1.0 / self.speed_box.value()
        meta_interval = 10
        self_correction = True
        censorship = self.censorship_box.currentIndex() == 1
        learning_aggressiveness = self.aggressiveness_slider.value() / 10.0
        transparency = self.transparency_box.currentIndex() == 0
        self.worker = TrainingWorker(batch_size=batch, speed=speed, meta_interval=meta_interval, self_correction=self_correction, censorship=censorship, learning_aggressiveness=learning_aggressiveness, transparency=transparency)
        self.worker.log_signal.connect(self.append_log)
        self.worker.progress_signal.connect(self.update_metrics)
        self.worker.stopped_signal.connect(self.training_stopped)
        self.worker.resource_signal.connect(self.update_resource_status)
        self.worker.start()
        print("[TrainingTab] Training started.")

    def stop_training(self):
        if self.worker:
            self.worker.running = False
            self.stop_btn.setEnabled(False)
            print("[TrainingTab] Stop requested. Waiting for current task to finish...")

    def training_stopped(self):
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        print("[TrainingTab] Training stopped.")

    def append_log(self, msg):
        self.log_display.append(msg)
        print(msg)

    def update_metrics(self, metrics):
        for metric, value in metrics.items():
            if metric in self.metric_bars:
                val = int(min(100, value if isinstance(value, (int, float)) else 0))
                self.metric_bars[metric].setValue(val)

    def update_resource_status(self, status):
        self.resource_label.setText(f"Resource: {status}")
        print(f"[TrainingTab] Resource status: {status}")

    def inject_manual_task(self):
        task = self.manual_input.text().strip()
        if task and self.worker:
            self.worker.inject_manual_task(task)
            self.append_log(f"[ManualTask] Injected: {task}")
            self.manual_input.clear()

    def visualize_knowledge_graph(self):
        if self.worker and self.worker.knowledge_graph.number_of_nodes() > 0:
            plt.figure(figsize=(10, 7))
            pos = nx.spring_layout(self.worker.knowledge_graph)
            nx.draw(self.worker.knowledge_graph, pos, with_labels=True, node_color='lightblue', edge_color='gray', node_size=500, font_size=8)
            plt.title("Knowledge Graph")
            plt.show()
        else:
            self.append_log("[KnowledgeGraph] No knowledge graph to visualize.")

    def export_knowledge_graph(self):
        if self.worker and self.worker.knowledge_graph.number_of_nodes() > 0:
            path, _ = QFileDialog.getSaveFileName(self, "Export Knowledge Graph", "", "GraphML Files (*.graphml);;JSON Files (*.json)")
            if path:
                if path.endswith(".graphml"):
                    nx.write_graphml(self.worker.knowledge_graph, path)
                    self.append_log(f"[KnowledgeGraph] Exported as GraphML: {path}")
                elif path.endswith(".json"):
                    data = nx.node_link_data(self.worker.knowledge_graph)
                    with open(path, 'w', encoding='utf-8') as f:
                        import json
                        json.dump(data, f, indent=2)
                    self.append_log(f"[KnowledgeGraph] Exported as JSON: {path}")
                else:
                    self.append_log("[KnowledgeGraph] Unsupported file type.")
        else:
            self.append_log("[KnowledgeGraph] No knowledge graph to export.") 