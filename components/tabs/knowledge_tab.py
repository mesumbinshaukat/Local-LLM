from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                            QListWidget, QListWidgetItem, QLabel, QFileDialog,
                            QMessageBox, QProgressBar)
from PyQt6.QtCore import Qt, pyqtSignal
from components.ui.base_components import ModernButton
from components.utils.constants import DARK_MODE
import os
import requests
import logging

logger = logging.getLogger(__name__)

class KnowledgeTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.load_documents()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Document list
        self.doc_list = QListWidget()
        self.doc_list.setStyleSheet(f"""
            QListWidget {{
                background-color: {DARK_MODE['secondary']};
                color: {DARK_MODE['text']};
                border: 1px solid {DARK_MODE['border']};
                border-radius: 5px;
                padding: 10px;
            }}
            QListWidget::item {{
                padding: 5px;
                border-bottom: 1px solid {DARK_MODE['border']};
            }}
            QListWidget::item:selected {{
                background-color: {DARK_MODE['accent']};
            }}
        """)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.add_button = ModernButton("Add Document")
        self.add_button.clicked.connect(self.add_document)
        
        self.remove_button = ModernButton("Remove Document")
        self.remove_button.clicked.connect(self.remove_document)
        
        self.ingest_button = ModernButton("Ingest Knowledge")
        self.ingest_button.clicked.connect(self.ingest_knowledge)
        
        button_layout.addWidget(self.add_button)
        button_layout.addWidget(self.remove_button)
        button_layout.addWidget(self.ingest_button)
        
        # Progress bar
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        self.progress.setStyleSheet(f"""
            QProgressBar {{
                background-color: {DARK_MODE['secondary']};
                color: {DARK_MODE['text']};
                border: 1px solid {DARK_MODE['border']};
                border-radius: 5px;
                text-align: center;
            }}
            QProgressBar::chunk {{
                background-color: {DARK_MODE['accent']};
            }}
        """)
        
        # Add widgets to layout
        layout.addWidget(QLabel("Knowledge Base"))
        layout.addWidget(self.doc_list)
        layout.addLayout(button_layout)
        layout.addWidget(self.progress)
        
    def load_documents(self):
        self.doc_list.clear()
        knowledge_dir = "./knowledge"
        if os.path.exists(knowledge_dir):
            for root, _, files in os.walk(knowledge_dir):
                for file in files:
                    if file.endswith(('.txt', '.md', '.pdf')):
                        path = os.path.join(root, file)
                        item = QListWidgetItem(os.path.relpath(path, knowledge_dir))
                        item.setData(Qt.ItemDataRole.UserRole, path)
                        self.doc_list.addItem(item)
                        
    def add_document(self):
        file_dialog = QFileDialog()
        file_dialog.setFileMode(QFileDialog.FileMode.ExistingFiles)
        file_dialog.setNameFilter("Documents (*.txt *.md *.pdf)")
        
        if file_dialog.exec():
            files = file_dialog.selectedFiles()
            knowledge_dir = "./knowledge"
            os.makedirs(knowledge_dir, exist_ok=True)
            
            for file in files:
                try:
                    filename = os.path.basename(file)
                    dest = os.path.join(knowledge_dir, filename)
                    if os.path.exists(dest):
                        reply = QMessageBox.question(
                            self, 'File Exists',
                            f'{filename} already exists. Overwrite?',
                            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                        )
                        if reply == QMessageBox.StandardButton.No:
                            continue
                            
                    with open(file, 'rb') as src, open(dest, 'wb') as dst:
                        dst.write(src.read())
                        
                except Exception as e:
                    logger.error(f"Error adding document: {str(e)}")
                    QMessageBox.critical(self, 'Error', f'Failed to add {filename}: {str(e)}')
                    
            self.load_documents()
            
    def remove_document(self):
        current_item = self.doc_list.currentItem()
        if not current_item:
            return
            
        path = current_item.data(Qt.ItemDataRole.UserRole)
        try:
            os.remove(path)
            self.load_documents()
        except Exception as e:
            logger.error(f"Error removing document: {str(e)}")
            QMessageBox.critical(self, 'Error', f'Failed to remove document: {str(e)}')
            
    def ingest_knowledge(self):
        try:
            self.progress.setVisible(True)
            self.progress.setValue(0)
            
            response = requests.post("http://localhost:8000/ingest_kb")
            if response.status_code == 200:
                self.progress.setValue(100)
                QMessageBox.information(self, 'Success', 'Knowledge base ingested successfully!')
            else:
                raise Exception(response.text)
                
        except Exception as e:
            logger.error(f"Error ingesting knowledge: {str(e)}")
            QMessageBox.critical(self, 'Error', f'Failed to ingest knowledge: {str(e)}')
            
        finally:
            self.progress.setVisible(False) 