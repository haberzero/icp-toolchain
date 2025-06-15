from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGroupBox, QRadioButton, QButtonGroup,
    QPushButton, QWidget
)
from PyQt5.QtCore import Qt

try:
    from .NewProjectWidget import NewProjectWidget
    from .ExistingProjectWidget import ExistingProjectWidget
except ImportError:
    from NewProjectWidget import NewProjectWidget
    from ExistingProjectWidget import ExistingProjectWidget



class InitPopup(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("MCCP 项目初始化")
        self.setWindowModality(Qt.ApplicationModal)
        self.setFixedSize(600, 500)
        
        self.project_path = ""
        self.config_data = None
        self.current_widget = None
        
        # Main layout
        main_layout = QVBoxLayout(self)
        
        # Project type selection
        type_group = QGroupBox("项目类型")
        type_layout = QHBoxLayout(type_group)
        
        self.new_project_radio = QRadioButton("新建项目")
        self.existing_project_radio = QRadioButton("选择已有项目")
        self.new_project_radio.setChecked(True)
        
        type_layout.addWidget(self.new_project_radio)
        type_layout.addWidget(self.existing_project_radio)
        
        # Button group
        self.type_group = QButtonGroup(self)
        self.type_group.addButton(self.new_project_radio, 0)
        self.type_group.addButton(self.existing_project_radio, 1)
        self.type_group.buttonClicked.connect(self.switch_project_type)
        
        # Content area
        self.content_area = QWidget()
        self.content_layout = QVBoxLayout(self.content_area)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        
        # Bottom buttons
        button_layout = QHBoxLayout()
        self.cancel_button = QPushButton("取消")
        self.ok_button = QPushButton("确定")
        
        button_layout.addStretch()
        button_layout.addWidget(self.cancel_button)
        button_layout.addWidget(self.ok_button)
        
        # Connections
        self.cancel_button.clicked.connect(self.reject)
        self.ok_button.clicked.connect(self.validate_and_accept)
        
        # Add widgets to main layout
        main_layout.addWidget(type_group)
        main_layout.addWidget(self.content_area)
        main_layout.addLayout(button_layout)
        
        # Initialize with new project widget
        self.switch_project_type(self.new_project_radio)
    
    def switch_project_type(self, button):
        """Switch between new and existing project widgets"""
        # Remove current widget if exists
        if self.current_widget:
            # Disconnect all signals from current widget
            try:
                self.current_widget.validation_changed.disconnect()
            except TypeError:
                pass  # Not connected
            
            # Remove from layout and delete
            self.content_layout.removeWidget(self.current_widget)
            self.current_widget.deleteLater()
            self.current_widget = None
        
        # Create new widget based on selection
        if button == self.new_project_radio:
            self.current_widget = NewProjectWidget()
        else:
            self.current_widget = ExistingProjectWidget()
        
        # Add to layout
        self.content_layout.addWidget(self.current_widget)
        
        # Connect validation signal
        if hasattr(self.current_widget, 'validation_changed'):
            self.current_widget.validation_changed.connect(self.update_ok_button)
        
        # Update button state
        self.update_ok_button()
    
    def update_ok_button(self, valid=False):
        """Update OK button state based on current widget validation"""
        if self.current_widget and hasattr(self.current_widget, 'is_valid'):
            self.ok_button.setEnabled(self.current_widget.is_valid())
        else:
            self.ok_button.setEnabled(False)
    
    def validate_and_accept(self):
        """Validate inputs and accept dialog"""
        if self.current_widget:
            self.project_path = self.current_widget.get_project_path()
            if self.project_path:
                self.accept()
    
    def get_project_path(self):
        """Get the selected project path"""
        return self.project_path

# Test
if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import QApplication
    app = QApplication(sys.argv)
    dialog = InitPopup()
    dialog.show()
    sys.exit(app.exec_())