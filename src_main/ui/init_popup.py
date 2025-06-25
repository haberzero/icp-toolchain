from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGroupBox, QRadioButton, QButtonGroup,
    QPushButton, QWidget
)
from PyQt5.QtCore import Qt

try:
    from .new_project_widget import NewProjectWidget
    from .existing_project_widget import ExistingProjectWidget
except ImportError:
    from new_project_widget import NewProjectWidget
    from existing_project_widget import ExistingProjectWidget


class InitPopup(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("MCCP 项目初始化")
        self.setWindowModality(Qt.ApplicationModal)
        self.setFixedSize(600, 500)
        
        self.project_path = ""
        self.config_data = None
        self.current_widget = None
        
        # 主布局
        main_layout = QVBoxLayout(self)
        
        # 项目类型选择组
        type_group = QGroupBox("项目类型")
        type_layout = QHBoxLayout(type_group)
        
        self.new_project_radio = QRadioButton("新建项目")
        self.existing_project_radio = QRadioButton("选择已有项目")
        self.new_project_radio.setChecked(True)
        
        type_layout.addWidget(self.new_project_radio)
        type_layout.addWidget(self.existing_project_radio)
        
        # 按钮组管理单选按钮
        self.type_group = QButtonGroup(self)
        self.type_group.addButton(self.new_project_radio, 0)
        self.type_group.addButton(self.existing_project_radio, 1)
        self.type_group.buttonClicked.connect(self.switch_project_type)
        
        # 内容区域
        self.content_area = QWidget()
        self.content_layout = QVBoxLayout(self.content_area)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        
        # 底部按钮
        button_layout = QHBoxLayout()
        self.cancel_button = QPushButton("取消")
        self.ok_button = QPushButton("确定")
        
        button_layout.addStretch()
        button_layout.addWidget(self.ok_button)
        button_layout.addWidget(self.cancel_button)
        
        # 连接按钮信号
        self.cancel_button.clicked.connect(self.reject)
        self.ok_button.clicked.connect(self.validate_and_accept)
        
        # 添加组件到主布局
        main_layout.addWidget(type_group)
        main_layout.addWidget(self.content_area)
        main_layout.addLayout(button_layout)
        
        # 初始化显示新建项目部件
        self.switch_project_type(self.new_project_radio)
    
    def switch_project_type(self, button):
        """切换项目类型"""
        # 移除当前部件（如果存在）
        if self.current_widget:
            # 断开信号连接
            try:
                self.current_widget.validation_changed.disconnect(self.update_ok_button)
            except TypeError:
                pass  # 没有连接时忽略
            
            # 从布局中移除并删除部件
            self.content_layout.removeWidget(self.current_widget)
            self.current_widget.deleteLater()
            self.current_widget = None
        
        # 根据选择的单选按钮创建新部件
        if button == self.new_project_radio:
            self.current_widget = NewProjectWidget()
        else:
            self.current_widget = ExistingProjectWidget()
        
        # 添加新部件到布局
        self.content_layout.addWidget(self.current_widget)
        
        # 连接验证信号 - 直接传递验证结果
        if hasattr(self.current_widget, 'validation_changed'):
            self.current_widget.validation_changed.connect(self.update_ok_button)
        
        # 初始化按钮状态
        if hasattr(self.current_widget, 'is_valid'):
            self.update_ok_button(self.current_widget.is_valid())
    
    def update_ok_button(self, valid):
        """使用提供的验证状态更新确定按钮"""
        self.ok_button.setEnabled(valid)
    
    def validate_and_accept(self):
        """验证输入并接受对话框"""
        if self.current_widget:
            self.project_path = self.current_widget.get_project_path()
            if self.project_path:
                self.accept()
    
    def get_project_path(self):
        """获取项目路径"""
        return self.project_path

# 测试代码
if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import QApplication
    app = QApplication(sys.argv)
    dialog = InitPopup()
    dialog.show()
    sys.exit(app.exec_())