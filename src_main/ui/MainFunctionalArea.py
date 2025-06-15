from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QSplitter, QTextEdit, QPlainTextEdit, 
    QGroupBox, QPushButton, QVBoxLayout, QWidget, QGridLayout
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
        top_area.setSizes([600, 200])
        
        # Bottom area (buttons and terminal)
        bottom_area = QSplitter(Qt.Horizontal)
        
        # Button panel
        button_panel = QGroupBox("工具链功能")
        button_layout = QGridLayout(button_panel)
        button_layout.setSpacing(5)  # 设置按钮间距
        button_layout.setContentsMargins(5, 5, 5, 5)  # 设置内边距
        
        # Create 8 tool buttons in 2 columns
        self.tool_buttons = []
        for i in range(1, 9):
            btn = QPushButton(f"func {i}")
            btn.setFixedSize(70, 25)  # 保持按钮尺寸
            self.tool_buttons.append(btn)
            # 计算行列位置（2列布局）
            row = (i-1) // 2
            col = (i-1) % 2
            button_layout.addWidget(btn, row, col)

        # 添加弹性空间，设置伸缩因子为2（保持底部栏占比小）
        button_layout.rowStretch(2)
        
        # Terminal placeholder
        terminal_placeholder = QWidget()
        terminal_placeholder.setStyleSheet("background-color: #2c3e50;")
        
        bottom_area.addWidget(button_panel)
        bottom_area.addWidget(terminal_placeholder)
        bottom_area.setSizes([150, 550])  # 调整按钮面板宽度 (原为[70, 630])
        
        # Add areas to vertical splitter
        vertical_splitter.addWidget(top_area)
        vertical_splitter.addWidget(bottom_area)
        vertical_splitter.setSizes([700, 100])  # 进一步减小底部区域高度 (原为[650, 150])
        
        main_layout.addWidget(vertical_splitter)

# Test
if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import QApplication
    app = QApplication(sys.argv)
    area = MainFunctionalArea()
    area.show()
    sys.exit(app.exec_())