from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton

class FunctionalWidget(QWidget):

    def __init__(self):
        super().__init__()
        self.top_layout = QVBoxLayout()
        self.text_editor = QTextEdit()
        self.output_display = QTextEdit()
        self.output_display.setReadOnly(True)
        self.script_buttons_layout = QVBoxLayout()

        for i in range(8):
            button = QPushButton(f"Script {i+1}")
            self.script_buttons_layout.addWidget(button)

        self.terminal_display = QTextEdit()
        self.terminal_display.setReadOnly(True)
        self.main_view_top_layout = QHBoxLayout()
        self.main_view_top_layout.addWidget(self.text_editor)
        self.main_view_top_layout.addWidget(self.output_display)
        self.main_view_bottom_layout = QHBoxLayout()
        self.main_view_bottom_layout.addLayout(self.script_buttons_layout)
        self.main_view_bottom_layout.addWidget(self.terminal_display)
        self.top_layout.addLayout(self.main_view_top_layout)
        self.top_layout.addLayout(self.main_view_bottom_layout)
        self.setLayout(self.top_layout)




