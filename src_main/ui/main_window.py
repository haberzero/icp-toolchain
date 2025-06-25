from PyQt5.QtWidgets import QMainWindow, QMenuBar, QAction, QVBoxLayout, QWidget, QHBoxLayout

try:
    # 尝试相对导入（当作为包的一部分运行时）
    from .init_popup import InitPopup
    from .function_selector import FunctionSelector
    from .left_side_browser import LeftSideBrowser
    from .main_functional_area import MainFunctionalArea
except ImportError:
    # 回退到绝对导入（当直接运行时）
    from init_popup import InitPopup
    from function_selector import FunctionSelector
    from left_side_browser import LeftSideBrowser
    from main_functional_area import MainFunctionalArea

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MCCP Toolchain")
        self.setGeometry(100, 100, 1200, 800)
        
        # Initialize project state
        self.project_loaded = False
        self.project_path = ""
        
        # Create menu bar
        self.create_menu_bar()
        
        # Central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Function selector (left narrow panel)
        self.function_selector = FunctionSelector()
        main_layout.addWidget(self.function_selector, 5)
        
        # Left side browser (wider panel)
        self.left_side_browser = LeftSideBrowser()
        main_layout.addWidget(self.left_side_browser, 15)
        
        # Main functional area
        self.main_functional_area = MainFunctionalArea()
        main_layout.addWidget(self.main_functional_area, 80)
        
        # Show initialization popup
        self.show_init_popup()
    
    def create_menu_bar(self):
        """Create the menu bar with placeholder menus"""
        menu_bar = QMenuBar()
        
        # Create menus
        file_menu = menu_bar.addMenu("文件")
        edit_menu = menu_bar.addMenu("编辑")
        select_menu = menu_bar.addMenu("选择")
        view_menu = menu_bar.addMenu("查看")
        help_menu = menu_bar.addMenu("帮助")
        
        # Add placeholder actions
        file_menu.addAction("占位符")
        edit_menu.addAction("占位符")
        select_menu.addAction("占位符")
        view_menu.addAction("占位符")
        help_menu.addAction("占位符")
        
        self.setMenuBar(menu_bar)
    
    def show_init_popup(self):
        """Show the initialization popup"""
        self.popup = InitPopup(self)
        self.popup.exec_()
        
        # Handle popup result
        if self.popup.result() == InitPopup.Accepted:
            self.project_loaded = True
            self.project_path = self.popup.get_project_path()
            # self.project_path = self.popup.get_project_path().replace('\\', '/')
            self.load_project()
        else:
            # Keep window blank if canceled
            self.left_side_browser.setVisible(False)
            self.main_functional_area.setVisible(False)
    
    def load_project(self):
        """Load project after initialization"""
        # Show project-related components
        self.left_side_browser.setVisible(True)
        self.main_functional_area.setVisible(True)
        
        # Set project path in file browser
        self.left_side_browser.set_root_path(self.project_path)

# Test
if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import QApplication
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())