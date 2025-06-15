from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QSplitter, QTextEdit, QPlainTextEdit, 
    QGroupBox, QPushButton, QVBoxLayout, QWidget
)
from PyQt5.QtCore import Qt

class MainFunctionalArea(QWidget):
    def __init__(self):
        super().__init__()
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(5, 5, 5, 5)
        
        # Create vertical splitter for top and bottom
        vertical_splitter = QSplitter(Qt.Vertical)
        
        # Top area (editable text and output)
        top_area = QSplitter(Qt.Horizontal)
        
        # Editable text area
        self.editable_text = QPlainTextEdit()
        self.editable_text.setPlaceholderText("在此编辑文件内容...")
        
        # Output area
        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        self.output_text.setPlaceholderText("脚本输出将显示在这里...")
        
        top_area.addWidget(self.editable_text)
        top_area.addWidget(self.output_text)
        top_area.setSizes([400, 400])
        
        # Bottom area (buttons and terminal)
        bottom_area = QSplitter(Qt.Horizontal)
        
        # Button panel
        button_panel = QGroupBox("工具链功能")
        button_layout = QVBoxLayout(button_panel)
        
        # Create 8 tool buttons
        self.tool_buttons = []
        for i in range(1, 9):
            btn = QPushButton(f"工具 {i}")
            btn.setFixedSize(100, 30)  # 设置固定尺寸
            self.tool_buttons.append(btn)
            button_layout.addWidget(btn)

        # 添加弹性空间，设置伸缩因子为2（保持底部栏占比小）
        button_layout.addStretch(2)
        
        # Terminal placeholder
        terminal_placeholder = QWidget()
        terminal_placeholder.setStyleSheet("background-color: #2c3e50;")
        
        bottom_area.addWidget(button_panel)
        bottom_area.addWidget(terminal_placeholder)
        bottom_area.setSizes([100, 500])
        
        # Add areas to vertical splitter
        vertical_splitter.addWidget(top_area)
        vertical_splitter.addWidget(bottom_area)
        vertical_splitter.setSizes([500, 300])
        
        main_layout.addWidget(vertical_splitter)

# Test
if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import QApplication
    app = QApplication(sys.argv)
    area = MainFunctionalArea()
    area.show()
    sys.exit(app.exec_())