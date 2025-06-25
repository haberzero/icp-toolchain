from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QHBoxLayout, QLineEdit, 
    QPushButton, QTextEdit, QMessageBox, QLabel, QFileDialog
)
from PyQt5.QtCore import pyqtSignal
import json
import os

class ExistingProjectWidget(QWidget):
    validation_changed = pyqtSignal(bool)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        
        # Project selection
        form_layout = QFormLayout()
        
        self.existing_location = QLineEdit()
        self.existing_location.textChanged.connect(self.validate_form)
        
        self.existing_browse_button = QPushButton("浏览...")
        self.existing_browse_button.clicked.connect(self.browse_existing)
        
        location_layout = QHBoxLayout()
        location_layout.addWidget(self.existing_location)
        location_layout.addWidget(self.existing_browse_button)
        
        form_layout.addRow("项目位置:", location_layout)
        
        # Read-only config display
        self.config_display = QTextEdit()
        self.config_display.setReadOnly(True)
        self.config_display.setPlaceholderText("选择项目后将显示配置信息")
        
        layout.addLayout(form_layout)
        layout.addWidget(QLabel("项目配置:"))
        layout.addWidget(self.config_display)
        layout.addStretch()
    
    def browse_existing(self):
        """Browse for existing project"""
        path = QFileDialog.getExistingDirectory(self, "选择项目文件夹")
        if path:
            self.existing_location.setText(path)
            self.load_existing_config(path)
            self.validate_form()
    
    def load_existing_config(self, path):
        """Load and display config for existing project"""
        config_path = os.path.join(path, ".mccp_config", "mccp_config.json")
        try:
            with open(config_path, 'r') as f:
                self.config_data = json.load(f)
                self.config_display.setText(json.dumps(self.config_data, indent=2))
        except Exception as e:
            QMessageBox.warning(self, "错误", f"无法读取配置文件: {str(e)}")
            self.config_display.setText("")
    
    def validate_form(self):
        """Validate form inputs"""
        path = self.existing_location.text().strip()
        valid = bool(path and os.path.exists(path))
        self.validation_changed.emit(valid)
        return valid
    
    def is_valid(self):
        """Check if form is valid"""
        return self.validate_form()
    
    def get_project_path(self):
        """Get the project path"""
        if self.is_valid():
            return self.existing_location.text()
        return ""

# Test
if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import QApplication
    app = QApplication(sys.argv)
    widget = ExistingProjectWidget()
    widget.show()
    sys.exit(app.exec_())