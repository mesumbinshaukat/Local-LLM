from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QPushButton, QTextEdit, QLabel, QFileDialog, QMessageBox
from components.ui.base_components import ModernButton
from components.utils.constants import DARK_MODE, PLUGINS_DIR
import os
import importlib.util

class PluginsTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.load_plugins()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        self.plugin_list = QListWidget()
        self.add_button = ModernButton("Add Plugin")
        self.add_button.clicked.connect(self.add_plugin)
        self.remove_button = ModernButton("Remove Plugin")
        self.remove_button.clicked.connect(self.remove_plugin)
        self.run_button = ModernButton("Run Plugin")
        self.run_button.clicked.connect(self.run_plugin)
        self.input_area = QTextEdit()
        self.input_area.setPlaceholderText("Input for plugin...")
        self.output_area = QTextEdit()
        self.output_area.setReadOnly(True)
        btn_layout = QHBoxLayout()
        btn_layout.addWidget(self.add_button)
        btn_layout.addWidget(self.remove_button)
        btn_layout.addWidget(self.run_button)
        layout.addWidget(QLabel("Plugins"))
        layout.addWidget(self.plugin_list)
        layout.addLayout(btn_layout)
        layout.addWidget(QLabel("Input:"))
        layout.addWidget(self.input_area)
        layout.addWidget(QLabel("Output:"))
        layout.addWidget(self.output_area)

    def load_plugins(self):
        self.plugin_list.clear()
        if not os.path.exists(PLUGINS_DIR):
            os.makedirs(PLUGINS_DIR)
        for file in os.listdir(PLUGINS_DIR):
            if file.endswith(".py"):
                self.plugin_list.addItem(file)

    def add_plugin(self):
        file_dialog = QFileDialog()
        file_dialog.setFileMode(QFileDialog.FileMode.ExistingFile)
        file_dialog.setNameFilter("Python Files (*.py)")
        if file_dialog.exec():
            src = file_dialog.selectedFiles()[0]
            dst = os.path.join(PLUGINS_DIR, os.path.basename(src))
            try:
                with open(src, 'rb') as fsrc, open(dst, 'wb') as fdst:
                    fdst.write(fsrc.read())
                self.load_plugins()
            except Exception as e:
                QMessageBox.critical(self, 'Error', f'Failed to add plugin: {str(e)}')

    def remove_plugin(self):
        item = self.plugin_list.currentItem()
        if not item:
            return
        path = os.path.join(PLUGINS_DIR, item.text())
        try:
            os.remove(path)
            self.load_plugins()
        except Exception as e:
            QMessageBox.critical(self, 'Error', f'Failed to remove plugin: {str(e)}')

    def run_plugin(self):
        item = self.plugin_list.currentItem()
        if not item:
            return
        plugin_path = os.path.join(PLUGINS_DIR, item.text())
        input_text = self.input_area.toPlainText()
        try:
            spec = importlib.util.spec_from_file_location("plugin_module", plugin_path)
            plugin = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(plugin)
            if hasattr(plugin, 'run'):
                output = plugin.run(input_text)
            else:
                output = 'No run() function found.'
        except Exception as e:
            output = str(e)
        self.output_area.setText(str(output)) 