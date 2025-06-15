from PyQt5.QtWidgets import QWidget, QVBoxLayout, QPushButton

class FunctionSelector(QWidget):
    def __init__(self):
        super().__init__()
        self.setMinimumWidth(80)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 10, 5, 10)
        layout.setSpacing(10)
        
        # Function buttons
        self.file_browser_btn = QPushButton("文件浏览")
        self.history_tracker_btn = QPushButton("修改历史")
        self.dependency_map_btn = QPushButton("依赖地图")
        
        # Style buttons
        for btn in [self.file_browser_btn, self.history_tracker_btn, self.dependency_map_btn]:
            btn.setCheckable(True)
            btn.setFixedHeight(40)
        
        # Set file browser as default selected
        self.file_browser_btn.setChecked(True)
        
        # Add to layout
        layout.addWidget(self.file_browser_btn)
        layout.addWidget(self.history_tracker_btn)
        layout.addWidget(self.dependency_map_btn)
        layout.addStretch()

# Test
if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import QApplication
    app = QApplication(sys.argv)
    selector = FunctionSelector()
    selector.show()
    sys.exit(app.exec_())