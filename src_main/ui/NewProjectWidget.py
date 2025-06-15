from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QHBoxLayout, QLineEdit, 
    QTextEdit, QPushButton, QFileDialog, QRadioButton, QGroupBox, 
    QLabel, QCheckBox
)
from PyQt5.QtCore import pyqtSignal
import os

class NewProjectWidget(QWidget):
    validation_changed = pyqtSignal(bool)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        
        # Project info form
        form_layout = QFormLayout()
        
        self.project_name = QLineEdit()
        self.project_name.textChanged.connect(self.validate_form)
        
        self.project_description = QTextEdit()
        self.project_description.setFixedHeight(80)
        
        self.project_location = QLineEdit()
        self.project_location.textChanged.connect(self.validate_form)
        
        self.browse_button = QPushButton("浏览...")
        self.browse_button.clicked.connect(self.browse_project_location)
        
        location_layout = QHBoxLayout()
        location_layout.addWidget(self.project_location)
        location_layout.addWidget(self.browse_button)
        
        form_layout.addRow("项目名称:", self.project_name)
        form_layout.addRow("项目描述:", self.project_description)
        form_layout.addRow("项目位置:", location_layout)
        
        # Build settings
        build_group = QGroupBox("构建设置")
        build_layout = QVBoxLayout(build_group)
        
        # Extra suffix
        suffix_layout = QHBoxLayout()
        self.suffix_yes = QRadioButton("是")
        self.suffix_no = QRadioButton("否")
        self.suffix_no.setChecked(True)
        
        suffix_layout.addWidget(QLabel("是否额外后缀:"))
        suffix_layout.addWidget(self.suffix_yes)
        suffix_layout.addWidget(self.suffix_no)
        suffix_layout.addStretch()
        
        # Bypass structure
        self.bypass_check = QCheckBox("使用旁路式文件夹结构")
        self.bypass_check.stateChanged.connect(self.toggle_bypass_fields)
        
        # Bypass fields (initially hidden)
        self.bypass_group = QGroupBox("旁路式设置")
        bypass_form = QFormLayout(self.bypass_group)
        
        self.bypass_group.setVisible(self.bypass_check.isChecked())

        build_layout.addLayout(suffix_layout)
        build_layout.addWidget(self.bypass_check)
        build_layout.addWidget(self.bypass_group)

        # MCBC位置选取
        mcbc_layout = QHBoxLayout()
        self.mcbc_path = QLineEdit()
        self.mcbc_browse = QPushButton("浏览")
        mcbc_layout.addWidget(self.mcbc_path)
        mcbc_layout.addWidget(self.mcbc_browse)
        bypass_form.addRow("MCBC位置:", mcbc_layout)
        
        # MCPC位置选取
        mcpc_layout = QHBoxLayout()
        self.mcpc_path = QLineEdit()
        self.mcpc_browse = QPushButton("浏览")
        mcpc_layout.addWidget(self.mcpc_path)
        mcpc_layout.addWidget(self.mcpc_browse)
        bypass_form.addRow("MCPC位置:", mcpc_layout)
        
        # Target位置选取
        target_layout = QHBoxLayout()
        self.target_path = QLineEdit()
        self.target_browse = QPushButton("浏览")
        target_layout.addWidget(self.target_path)
        target_layout.addWidget(self.target_browse)
        bypass_form.addRow("Target位置:", target_layout)

        # 连接点击事件
        self.mcbc_browse.clicked.connect(self.browse_mcbc_location)
        self.mcpc_browse.clicked.connect(self.browse_mcpc_location)
        self.target_browse.clicked.connect(self.browse_target_location)

        # Add to page layout
        layout.addLayout(form_layout)
        layout.addWidget(build_group)
        layout.addStretch()
    
    def browse_project_location(self):
        """浏览项目位置"""
        dir = QFileDialog.getExistingDirectory(self, "选择项目位置")
        if dir:
            self.project_location.setText(dir)
    
    def browse_mcbc_location(self):
        """浏览MCBC位置"""
        dir = QFileDialog.getExistingDirectory(self, "选择MCBC位置")
        if dir:
            self.mcbc_path.setText(dir)
    
    def browse_mcpc_location(self):
        """浏览MCPC位置"""
        dir = QFileDialog.getExistingDirectory(self, "选择MCPC位置")
        if dir:
            self.mcpc_path.setText(dir)
    
    def browse_target_location(self):
        """浏览Target位置"""
        dir = QFileDialog.getExistingDirectory(self, "选择Target位置")
        if dir:
            self.target_path.setText(dir)
    
    def toggle_bypass_fields(self, state):
        """Toggle visibility of bypass fields"""
        
        if self.bypass_check.isChecked():
            self.bypass_group.setVisible(True)
            pass
        else:
            self.bypass_group.setVisible(False)
            pass
    
    def validate_form(self):
        """Validate form inputs"""
        valid = bool(
            self.project_name.text().strip() and 
            self.project_location.text().strip()
        )
        self.validation_changed.emit(valid)
        return valid
    
    def is_valid(self):
        """Check if form is valid"""
        return self.validate_form()
    
    def get_project_path(self):
        """Get the project path"""
        if self.is_valid():
            # 只返回项目位置，不附加项目名称
            return self.project_location.text().replace('\\', '/')
        return ""

# Test
if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import QApplication
    app = QApplication(sys.argv)
    widget = NewProjectWidget()
    widget.show()
    sys.exit(app.exec_())