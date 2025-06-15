from PyQt5.QtWidgets import QWidget, QVBoxLayout, QTreeView, QFileSystemModel
from PyQt5.QtCore import QDir

class LeftSideBrowser(QWidget):
    def __init__(self):
        super().__init__()
        self.setMinimumWidth(200)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # File system tree view
        self.tree_view = QTreeView()
        self.file_model = QFileSystemModel()
        self.file_model.setRootPath("")
        self.tree_view.setModel(self.file_model)
        
        # Hide unnecessary columns
        self.tree_view.setHeaderHidden(False)
        self.tree_view.hideColumn(1)  # Size
        self.tree_view.hideColumn(2)  # Type
        self.tree_view.hideColumn(3)  # Date modified
        
        layout.addWidget(self.tree_view)
    
    def set_root_path(self, path):
        """Set the root path for the file browser"""
        if path:
            self.tree_view.setRootIndex(self.file_model.index(path))
            self.tree_view.setColumnWidth(0, 250)

# Test
if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import QApplication
    app = QApplication(sys.argv)
    browser = LeftSideBrowser()
    browser.set_root_path(QDir.homePath())
    browser.show()
    sys.exit(app.exec_())