from PyQt6.QtWidgets import QPushButton, QFrame, QLabel, QVBoxLayout, QHBoxLayout
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QSize
from PyQt6.QtGui import QFont, QPalette, QColor, QLinearGradient, QGradient, QPainter
from components.utils.constants import DARK_MODE

class ModernButton(QPushButton):
    def __init__(self, text, parent=None, is_dark=True):
        super().__init__(text, parent)
        self.is_dark = is_dark
        self.setMinimumHeight(40)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.update_style()
        
    def update_style(self):
        if self.is_dark:
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: {DARK_MODE['accent']};
                    color: {DARK_MODE['foreground']};
                    border: none;
                    border-radius: 5px;
                    padding: 8px 16px;
                    font-weight: bold;
                }}
                QPushButton:hover {{
                    background-color: {DARK_MODE['accent']}dd;
                }}
                QPushButton:pressed {{
                    background-color: {DARK_MODE['accent']}aa;
                }}
            """)
        else:
            self.setStyleSheet("""
                QPushButton {
                    background-color: #4a90e2;
                    color: white;
                    border: none;
                    border-radius: 5px;
                    padding: 8px 16px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #357abd;
                }
                QPushButton:pressed {
                    background-color: #2a5f9e;
                }
            """)

class CategoryCard(QFrame):
    def __init__(self, title, count, parent=None, is_dark=True):
        super().__init__(parent)
        self.is_dark = is_dark
        self.setMinimumSize(200, 100)
        self.setMaximumSize(300, 150)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setFrameShadow(QFrame.Shadow.Raised)
        
        # Create layout
        layout = QVBoxLayout(self)
        
        # Title label
        self.title_label = QLabel(title)
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        
        # Count label
        self.count_label = QLabel(str(count))
        self.count_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.count_label.setFont(QFont("Arial", 24, QFont.Weight.Bold))
        
        # Add widgets to layout
        layout.addWidget(self.title_label)
        layout.addWidget(self.count_label)
        
        self.update_style()
        
    def update_style(self):
        if self.is_dark:
            self.setStyleSheet(f"""
                QFrame {{
                    background-color: {DARK_MODE['secondary']};
                    border: 1px solid {DARK_MODE['border']};
                    border-radius: 10px;
                }}
                QLabel {{
                    color: {DARK_MODE['text']};
                }}
            """)
        else:
            self.setStyleSheet("""
                QFrame {
                    background-color: #f5f5f5;
                    border: 1px solid #ddd;
                    border-radius: 10px;
                }
                QLabel {
                    color: #333;
                }
            """)
            
    def update_count(self, count):
        self.count_label.setText(str(count)) 