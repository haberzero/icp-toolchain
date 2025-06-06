```python
# -*- coding: utf-8 -*-

"""
MCCP Toolchain - User Interface Module

This module provides the graphical user interface for the MCCP toolchain using PyQt.
It displays the project structure, allows triggering build processes,
and provides status updates.
"""

import os
import sys
import json
from typing import Dict, Any, Optional, List

# Import PyQt components
from PyQt5.QtWidgets import (
    QMainWindow, QTreeView, QPushButton, QStatusBar, QComboBox, QVBoxLayout,
    QHBoxLayout, QWidget, QApplication, QFileSystemModel, QFileDialog,
    QMessageBox, QLabel, QMenu, QAction, QSizePolicy
)
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt, QModelIndex, QDir

# Import MCCP Toolchain Modules (Forward declarations for type hinting)
# These will be properly imported below the class definitions
# import mccp_toolchain.mccp.config
# import mccp_toolchain.mccp.file_manager
# import mccp_toolchain.core.build
# import mccp_toolchain.mccp.symbols

# Define placeholders or mock classes for dependencies to satisfy type hints
# Real imports will be done later
class ConfigManager:
    """Placeholder for mccp_toolchain.mccp.config.ConfigManager."""
    def __init__(self, file_manager: 'FileManager'): pass
    def load_config(self, project_path: str) -> bool: pass
    def get_setting(self, key: str) -> Any: pass
    def get_layer_dir(self, layer_key: str) -> Optional[str]: pass
    def get_build_rule(self, rule_key: str) -> Optional[Dict]: pass
    def get_config_data(self) -> Dict: pass
    def get_project_root(self) -> Optional[str]: pass

class FileManager:
    """Placeholder for mccp_toolchain.mccp.file_manager.FileManager."""
    def __init__(self, config_manager: ConfigManager): pass
    def create_project_structure(self, project_path: str) -> bool: pass
    def read_file(self, file_path: str) -> Optional[str]: pass
    def write_file(self, file_path: str, content: str) -> bool: pass
    def get_file_path(self, project_path: str, layer_key: str, file_name: str) -> str: pass
    def list_files_in_layer(self, project_path: str, layer_key: str, extension: str) -> List[str]: pass
    def get_project_root_from_path(self, any_path_within_project: str) -> Optional[str]: pass

class BuildOrchestrator:
    """Placeholder for mccp_toolchain.core.build.BuildOrchestrator."""
    def __init__(self, config_manager: ConfigManager, file_manager: FileManager, symbol_manager: 'SymbolTableManager', llm_client: 'LLMClient', parsers: Dict): pass
    def run_forward_build(self, project_path: str, start_layer_key: str, end_layer_key: str) -> bool: pass
    def run_reverse_build(self, project_path: str, start_layer: str, end_layer: str) -> bool: pass

class SymbolTableManager:
    """Placeholder for mccp_toolchain.mccp.symbols.SymbolTableManager."""
    def __init__(self, file_manager: FileManager, config_manager: ConfigManager): pass
    def load_all_symbol_tables(self, project_path: str) -> None: pass
    def save_all_symbol_tables(self) -> None: pass
    def find_symbol(self, symbol_name: str, module_name: Optional[str]) -> Optional[Dict]: pass
    def update_symbol(self, symbol_data: Dict) -> bool: pass
    def get_module_symbols(self, module_name: str) -> Dict: pass
    def get_all_symbols(self) -> Dict: pass

class LLMClient:
    """Placeholder for mccp_toolchain.core.llm.LLMClient."""
    def __init__(self, config_manager: ConfigManager): pass
    def generate_content(self, prompt: str, context: Dict) -> str: pass
    def parse_response(self, response_text: str, target_format: str) -> Any: pass

# Now import the actual modules
try:
    from mccp_toolchain.mccp.config import ConfigManager
    from mccp_toolchain.mccp.file_manager import FileManager, get_project_root_from_path
    from mccp_toolchain.core.build import BuildOrchestrator, BUILD_LAYERS
    from mccp_toolchain.mccp.symbols import SymbolTableManager
    from mccp_toolchain.core.llm import LLMClient
except ImportError as e:
    print(f"Error importing MCCP Toolchain modules: {e}")
    print("Please ensure the mccp_toolchain package is correctly installed or in your PYTHONPATH.")
    # Exit or handle the error appropriately in a real application
    # For code generation purposes, we'll proceed assuming the structure is correct.
    # In a real app, you might show a critical error message and exit.


class MainWindow(QMainWindow):
    """
    主窗口类，继承自 PyQt 的 QMainWindow，包含文件树视图、按钮、状态栏等。
    """

    def __init__(
        self,
        config_manager: ConfigManager,
        file_manager: FileManager,
        build_orchestrator: BuildOrchestrator,
        symbol_manager: SymbolTableManager
    ):
        """
        初始化主窗口，设置布局和连接信号槽。

        Args:
            config_manager: 配置管理器实例。
            file_manager: 文件管理器实例。
            build_orchestrator: 构建协调器实例。
            symbol_manager: 符号表管理器实例。
        """
        super().__init__()

        # 存储注入的依赖服务
        self.config_manager: ConfigManager = config_manager
        self.file_manager: FileManager = file_manager
        self.build_orchestrator: BuildOrchestrator = build_orchestrator
        self.symbol_manager: SymbolTableManager = symbol_manager

        # 存储当前项目根目录
        self._current_project_root: Optional[str] = None

        # 设置窗口属性
        self.setWindowTitle("MCCP Toolchain")
        self.setGeometry(100, 100, 800, 600)

        # 构建 UI 元素和布局
        self.setup_ui()

        # 连接信号到槽
        self.connect_signals()

        # 设置初始状态栏消息
        self.log_message("MCCP Toolchain ready.")

    def setup_ui(self) -> None:
        """
        构建用户界面元素，如文件树视图、菜单、工具栏和状态栏。
        """
        # 创建中心控件和主布局
        central_widget = QWidget()
        main_layout = QVBoxLayout(central_widget)
        self.setCentralWidget(central_widget)

        # 创建文件树视图
        self.file_tree_view = QTreeView()
        self.file_tree_view.setHeaderHidden(True) # Hide headers like Name, Size, Type, Date Modified
        self.file_tree_view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        main_layout.addWidget(self.file_tree_view)

        # 创建按钮布局
        button_layout = QHBoxLayout()
        self.new_project_button = QPushButton("新建项目")
        self.open_project_button = QPushButton("打开项目")
        self.run_build_button = QPushButton("运行构建 (正向)")
        self.run_reverse_build_button = QPushButton("运行构建 (反向)") # Added reverse build button
        self.build_target_selector = QComboBox() # 用于选择构建目标层级
        # 填充构建目标层级选项 (从 BUILD_LAYERS 常量或配置获取)
        # 假设只需要构建到 pseudo_code 或 target_code
        # Possible target layers from mcbc onwards: mcpc, target_code
        # BUILD_LAYERS = ["requirements", "behavior_code", "pseudo_code", "target_code"]
        build_targets = BUILD_LAYERS[BUILD_LAYERS.index("behavior_code") + 1:] # Start from the layer after mcbc
        self.build_target_selector.addItems(build_targets)


        button_layout.addWidget(self.new_project_button)
        button_layout.addWidget(self.open_project_button)
        button_layout.addStretch(1) # Add stretchable space
        button_layout.addWidget(QLabel("目标层级:"))
        button_layout.addWidget(self.build_target_selector)
        button_layout.addWidget(self.run_build_button)
        button_layout.addWidget(self.run_reverse_build_button)

        main_layout.addLayout(button_layout)

        # 创建状态栏
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

    def connect_signals(self) -> None:
        """
        连接UI元素（如按钮、菜单项）的信号到槽函数。
        """
        # 连接按钮点击信号到处理方法
        self.new_project_button.clicked.connect(self.handle_new_project)
        self.open_project_button.clicked.connect(self.handle_open_project)
        # Pass the selected target layer when the build button is clicked
        self.run_build_button.clicked.connect(
            lambda: self.handle_run_build(self.build_target_selector.currentText())
        )
        # Reverse build handler (currently frozen)
        self.run_reverse_build_button.clicked.connect(self.handle_run_reverse_build_placeholder)

        # 连接文件树视图信号 (例如，文件选中事件)
        # self.file_tree_view.clicked.connect(self.handle_file_selected) # 示例：单击
        # self.file_tree_view.doubleClicked.connect(self.handle_file_double_clicked) # 示例：双击打开文件

        # 连接构建目标选择器信号 (可选，如果需要根据选择刷新UI或状态)
        # self.build_target_selector.currentTextChanged.connect(self.handle_build_target_changed) # Example

    def handle_run_reverse_build_placeholder(self) -> None:
        """Placeholder handler for the reverse build button."""
        QMessageBox.information(self, "功能待实现", "反向构建功能目前尚未完全实现。")
        self.log_message("Reverse build function is not yet fully implemented.")


    def update_file_tree(self, project_root: str) -> None:
        """
        刷新文件结构树视图，显示项目文件和目录。

        Args:
            project_root: 项目根目录路径。
        """
        # 使用 QFileSystemModel 来表示文件系统
        model = QFileSystemModel()
        # 设置过滤器，只显示目录和特定后缀的文件？ 或者显示所有文件？
        # 先显示所有文件，后续可以根据 MCCP 结构过滤
        # model.setFilter(QDir.NoDotAndDotDot | QDir.AllDirs | QDir.Files)
        # model.setNameFilters(["*.md", "*.mcbc", "*.mcpc", "*.py", "*.json"]) # Example filter
        # model.setNameFilterDisables(False)

        model.setRootPath(project_root)
        self.file_tree_view.setModel(model)
        # 设置文件树的根索引为项目根目录
        self.file_tree_view.setRootIndex(model.index(project_root))
        # 自动展开一些重要的目录，如 src_mcbc, src_mcpc, mccp_symbols
        self._expand_important_dirs(model, project_root)

    def _expand_important_dirs(self, model: QFileSystemModel, root_path: str) -> None:
        """Helper to expand key MCCP directories."""
        important_dirs = ["src_mcbc", "src_mcpc", "mccp_symbols", "config"]
        for dir_name in important_dirs:
            dir_path = os.path.join(root_path, dir_name)
            if os.path.isdir(dir_path):
                index = model.index(dir_path)
                if index.isValid():
                    self.file_tree_view.expand(index)

    def log_message(self, message: str) -> None:
        """
        在状态栏显示信息。

        Args:
            message: 要显示的消息字符串。
        """
        print(f"LOG: {message}") # Also print to console for debugging
        self.status_bar.showMessage(message)

    def handle_new_project(self) -> None:
        """
        处理创建新项目的用户操作。
        弹出对话框获取项目路径，调用 FileManager 创建结构。
        """
        # 提示用户选择项目目录
        project_path = QFileDialog.getExistingDirectory(
            self, "选择新项目目录", os.path.expanduser("~")
        )

        if project_path:
            self.log_message(f"尝试在 {project_path} 创建新项目...")
            # 实际的创建逻辑应该在 FileManager 中，这里只调用
            # 假设 create_project_structure 包含创建 config 文件和 requirements.md
            # 并且 create_project_structure 成功后，就可以视为项目已存在并打开它
            try:
                success = self.file_manager.create_project_structure(project_path)
                if success:
                    self.log_message(f"项目在 {project_path} 创建成功。")
                    # 创建成功后，自动打开这个新项目
                    self.open_project(project_path)
                else:
                    self.log_message(f"在 {project_path} 创建项目失败。")
                    QMessageBox.warning(self, "创建失败", f"无法在 {project_path} 创建项目结构。")
            except Exception as e:
                 self.log_message(f"创建项目过程中发生错误: {e}")
                 QMessageBox.critical(self, "创建错误", f"创建项目过程中发生错误: {e}")


    def handle_open_project(self) -> None:
        """
        处理打开现有项目的用户操作。
        弹出文件对话框选择项目目录，然后调用 open_project 加载并更新文件树。
        """
        # 提示用户选择项目目录 (MCCP 项目根目录)
        selected_path = QFileDialog.getExistingDirectory(
            self, "选择 MCCP 项目根目录", os.path.expanduser("~")
        )

        if selected_path:
            # 尝试加载并打开项目
            self.open_project(selected_path)

    def open_project(self, path: str) -> None:
        """
        加载并显示一个已存在的项目（配置、符号表）并更新UI。

        Args:
            path: 用户选择的项目路径，可能是项目根目录或其子目录。
        """
        # 尝试找到项目根目录 (通过查找 mccp_config.json)
        project_root = get_project_root_from_path(path) # Use the function directly

        if project_root:
            self.log_message(f"正在打开项目: {project_root}...")
            try:
                # 加载配置
                if not self.config_manager.load_config(project_root):
                    raise Exception("配置加载失败。")

                # 加载符号表
                self.symbol_manager.load_all_symbol_tables(project_root)
                self._current_project_root = project_root # 存储当前项目根目录

                # 更新文件树
                self.update_file_tree(project_root)

                self.log_message(f"项目 {project_root} 加载成功。")

            except Exception as e:
                self.log_message(f"加载项目时发生错误: {e}")
                QMessageBox.critical(self, "加载项目失败", f"无法加载项目 {project_root}: {e}\n请确保这是一个有效的MCCP项目目录。")
                self._current_project_root = None # Reset project root on failure
                self.update_file_tree("") # Clear file tree on failure

        else:
            self.log_message(f"在 {path} 或其父目录中未找到 MCCP 项目配置文件 (mccp_config.json)。")
            QMessageBox.warning(self, "不是 MCCP 项目", f"在 {path} 或其父目录中未找到有效的 MCCP 项目配置文件 (mccp_config.json)。")
            self._current_project_root = None # Reset project root
            self.update_file_tree("") # Clear file tree


    def handle_run_build(self, target_layer: str) -> None:
        """
        处理触发正向构建流程的用户操作，调用 BuildOrchestrator。

        Args:
            target_layer: 构建目标层级键 (e.g., 'mcpc', 'target_code').
        """
        project_root = self._current_project_root # 获取当前加载的项目根目录

        if not project_root:
            self.log_message("无法运行构建：未加载项目。")
            QMessageBox.warning(self, "构建错误", "请先打开一个 MCCP 项目。")
            return

        if not target_layer:
            self.log_message("无法运行构建：未选择目标层级。")
            QMessageBox.warning(self, "构建错误", "请选择构建目标层级。")
            return

        # Determine start layer - for UI triggered build, assume starting from behavior code
        start_layer = "behavior_code" # Based on SR.UI.3 and common workflow

        self.log_message(f"开始正向构建流程：从 '{start_layer}' 到 '{target_layer}' ...")
        # Disable buttons during build to prevent re-triggering
        self._set_buttons_enabled(False)

        try:
            # 调用构建协调器
            success = self.build_orchestrator.run_forward_build(
                project_root, start_layer, target_layer
            )

            if success:
                self.log_message("正向构建流程完成成功。")
                # 刷新文件树，因为可能生成了新文件
                self.update_file_tree(project_root)
            else:
                self.log_message("正向构建流程失败。请检查日志输出。")
                QMessageBox.warning(self, "构建失败", "正向构建流程未成功完成。请检查状态栏和控制台输出。")

        except Exception as e:
            self.log_message(f"构建过程中发生错误: {e}")
            QMessageBox.critical(self, "构建错误", f"构建过程中发生未预期的错误: {e}")

        finally:
             # Re-enable buttons after build finishes (or fails)
            self._set_buttons_enabled(True)


    def _set_buttons_enabled(self, enabled: bool) -> None:
        """Helper to enable/disable build-related buttons during process."""
        self.run_build_button.setEnabled(enabled)
        self.run_reverse_build_button.setEnabled(enabled)
        self.new_project_button.setEnabled(enabled)
        self.open_project_button.setEnabled(enabled)
        self.build_target_selector.setEnabled(enabled)

    # Example handler for file tree item selection (optional)
    # def handle_file_selected(self, index: QModelIndex) -> None:
    #     """处理文件树中文件被选中的事件."""
    #     model = self.file_tree_view.model() # type: QFileSystemModel
    #     file_path = model.filePath(index)
    #     if os.path.isfile(file_path):
    #         self.log_message(f"Selected file: {file_path}")
    #         # Optionally, open the file in an external editor or integrated view
    #         # self.open_file_in_editor(file_path) # Needs implementation


# Note: show_new_project_dialog and show_open_directory_dialog are conceptually
# represented by QFileDialog.getExistingDirectory in handle_new_project/handle_open_project.
# open_file_in_editor is an external action, not implemented here.
```

```python
# -*- coding: utf-8 -*-

"""
MCCP Toolchain - Core Build Module

This module contains the core logic for orchestrating the forward and reverse
build processes between different MCCP layers. It coordinates the use of
file management, symbol management, configuration, and LLM interaction services.
"""

import os
import pathlib
import json
from typing import Dict, Any, Optional, List

# Import MCCP Toolchain Modules (Forward declarations for type hinting)
# import mccp_toolchain.mccp.config
# import mccp_toolchain.mccp.file_manager
# import mccp_toolchain.mccp.symbols
# import mccp_toolchain.core.llm
# import mccp_toolchain.mccp.parsers
# import mccp_toolchain.utils

# Define placeholders or mock classes for dependencies to satisfy type hints
class ConfigManager:
    def __init__(self, file_manager: 'FileManager'): pass
    def load_config(self, project_path: str) -> bool: pass
    def get_setting(self, key: str) -> Any: pass
    def get_layer_dir(self, layer_key: str) -> Optional[str]: pass
    def get_build_rule(self, rule_key: str) -> Optional[Dict]: pass
    def get_config_data(self) -> Dict: pass
    def get_project_root(self) -> Optional[str]: pass

class FileManager:
    def __init__(self, config_manager: ConfigManager): pass
    def create_project_structure(self, project_path: str) -> bool: pass
    def read_file(self, file_path: str) -> Optional[str]: pass
    def write_file(self, file_path: str, content: str) -> bool: pass
    def get_file_path(self, project_path: str, layer_key: str, file_name: str) -> str: pass
    def list_files_in_layer(self, project_path: str, layer_key: str, extension: str) -> List[str]: pass
    def get_project_root_from_path(self, any_path_within_project: str) -> Optional[str]: pass

class SymbolTableManager:
    def __init__(self, file_manager: FileManager, config_manager: ConfigManager): pass
    def load_all_symbol_tables(self, project_path: str) -> None: pass
    def save_all_symbol_tables(self) -> None: pass
    def find_symbol(self, symbol_name: str, module_name: Optional[str]) -> Optional[Dict]: pass
    def update_symbol(self, symbol_data: Dict) -> bool: pass
    def get_module_symbols(self, module_name: str) -> Dict: pass
    def get_all_symbols(self) -> Dict: pass
    def derive_symbol_file_name(self, module_name: str) -> str: pass

class LLMClient:
    def __init__(self, config_manager: ConfigManager): pass
    def generate_content(self, prompt: str, context: Dict) -> str: pass
    def parse_response(self, response_text: str, target_format: str) -> Any: pass

class PromptGenerator:
     def __init__(self, config_manager: ConfigManager): pass
     def generate_prompt(self, build_rule_key: str, source_content: str, symbols: Dict, config: Dict) -> str: pass

# Assuming parsers module provides these classes
class RequirementsParser: pass
class McbcParser: pass
class McpcParser: pass
class TargetCodeParser: pass
class JsonParser: pass # JsonParser is specifically used by SymbolTableManager and ConfigManager

# Now import the actual modules
try:
    from mccp_toolchain.mccp.config import ConfigManager
    from mccp_toolchain.mccp.file_manager import FileManager
    from mccp_toolchain.mccp.symbols import SymbolTableManager
    from mccp_toolchain.core.llm import LLMClient, PromptGenerator
    from mccp_toolchain.mccp.parsers import (
        RequirementsParser, McbcParser, McpcParser, TargetCodeParser, JsonParser
    )
    from mccp_toolchain.utils import find_in_list_by_key
except ImportError as e:
    print(f"Error importing MCCP Toolchain modules in core/build: {e}")
    # In a real app, handle gracefully. For code generation, assume imports are correct.


# Define constants as per Symbol Table
BUILD_LAYERS: List[str] = ["requirements", "behavior_code", "pseudo_code", "target_code"]
BUILD_RULES: List[str] = ["md_to_mcbc", "mcbc_to_mcpc", "mcpc_to_py"]
# Note: reverse rules exist but are frozen/TBD


class BuildOrchestrator:
    """
    构建流程协调器类，管理整个构建流程的步骤和依赖。
    负责协调正向和反向构建流程，驱动层级转换。
    """

    def __init__(
        self,
        config_manager: ConfigManager,
        file_manager: FileManager,
        symbol_manager: SymbolTableManager,
        llm_client: LLMClient,
        parsers: Dict[str, Any] # Dictionary mapping parser names (str) to instances
    ):
        """
        初始化构建协调器，注入所需的依赖服务。

        Args:
            config_manager: 配置管理器实例。
            file_manager: 文件管理器实例。
            symbol_manager: 符号表管理器实例。
            llm_client: LLM 客户端实例。
            parsers: 包含各种解析器实例的字典。
        """
        self.config_manager: ConfigManager = config_manager
        self.file_manager: FileManager = file_manager
        self.symbol_manager: SymbolTableManager = symbol_manager
        self.llm_client: LLMClient = llm_client
        self.parsers: Dict[str, Any] = parsers # e.g., {"McbcParser": McbcParser_instance, ...}

        # Assuming logging is handled via print for now or a logging module
        self.log_info = print
        self.log_warning = print
        self.log_error = print


    def run_forward_build(self, project_path: str, start_layer_key: str, end_layer_key: str) -> bool:
        """
        执行从起始层级到结束层级的正向构建流程，协调各步骤。
        调用 LayerTransformer 进行具体的层级转换。

        Args:
            project_path: 项目根目录。
            start_layer_key: 起始层级键 (e.g., 'behavior_code')。
            end_layer_key: 结束层级键 ('mcpc', 'target_code')。

        Returns:
            bool: 构建流程是否完成成功。
        """
        self.log_info(f"BuildOrchestrator: Starting forward build from '{start_layer_key}' to '{end_layer_key}' in project: {project_path}")

        # 确保符号表已加载到内存，为构建提供上下文
        # Note: This might have been done during project open, but re-loading ensures freshness
        self.symbol_manager.load_all_symbol_tables(project_path)
        self.log_info("BuildOrchestrator: Symbol tables loaded.")

        # 获取构建层级序列
        # Use the constant defined in this module
        layer_sequence = BUILD_LAYERS

        try:
            start_index = layer_sequence.index(start_layer_key)
            end_index = layer_sequence.index(end_layer_key)
        except ValueError:
            self.log_error(f"BuildOrchestrator: Invalid start or end layer key: {start_layer_key} -> {end_layer_key}")
            return False

        if start_index >= end_index:
            self.log_error(f"BuildOrchestrator: Start layer '{start_layer_key}' is not before end layer '{end_layer_key}' in sequence.")
            return False

        # 遍历层级转换步骤
        for step_index in range(start_index, end_index):
            current_layer_key = layer_sequence[step_index]
            next_layer_key = layer_sequence[step_index + 1]

            self.log_info(f"BuildOrchestrator: Processing layer transition: {current_layer_key} -> {next_layer_key}")

            # 根据当前层级和目标层级找到对应的构建规则键
            rule_key = self.get_rule_key(current_layer_key, next_layer_key, "forward")
            if rule_key is None:
                self.log_error(f"BuildOrchestrator: No forward build rule found for {current_layer_key} to {next_layer_key}. Aborting build.")
                return False

            # 获取构建规则配置
            rule_config = self.config_manager.get_build_rule(rule_key)
            if rule_config is None:
                 # This should not happen if get_rule_key returned a key, but as a safeguard:
                 self.log_error(f"BuildOrchestrator: Rule configuration not found for key: {rule_key}. Aborting build.")
                 return False


            # 假设规则配置中包含输入/输出层级目录键和文件扩展名
            source_layer_dir_key = rule_config.get('input_layer_dir_key')
            target_layer_dir_key = rule_config.get('output_layer_dir_key')
            source_ext = rule_config.get('input_extension')
            target_ext = rule_config.get('output_extension')
            source_parser_key = rule_config.get('source_parser')
            target_parser_key = rule_config.get('target_parser') # Target parser might be optional or not used for validation

            if not all([source_layer_dir_key, target_layer_dir_key, source_ext, target_ext, source_parser_key]):
                 self.log_error(f"BuildOrchestrator: Incomplete rule configuration for {rule_key}. Missing directory keys, extensions, or source parser. Aborting build.")
                 return False


            # 获取当前层级的所有源文件
            # Note: "requirements" is likely a single file, not a directory. Handle this edge case.
            if current_layer_key == "requirements":
                 # Assuming requirements file name is fixed or in config
                 req_dir_key = self.config_manager.get_setting("layer_mapping.requirements_dir") # e.g., "requirements"
                 req_file_name = "requirements.md" # Or get from config
                 source_file_path = self.file_manager.get_file_path(project_path, req_dir_key, req_file_name)
                 # Check if requirements file exists
                 if not os.path.exists(source_file_path):
                      self.log_warning(f"BuildOrchestrator: Requirements file not found at {source_file_path}. Skipping md->mcbc transition.")
                      continue # Skip this transition, move to the next layer
                 source_files = [source_file_path]
            else:
                source_files = self.file_manager.list_files_in_layer(project_path, source_layer_dir_key, source_ext)
                if not source_files:
                    self.log_warning(f"BuildOrchestrator: No source files found in '{source_layer_dir_key}' with extension '{source_ext}' for rule '{rule_key}'. Skipping this transition.")
                    continue # Move to the next layer transition


            # 获取源解析器实例
            source_parser_instance = self.parsers.get(source_parser_key)
            if source_parser_instance is None:
               self.log_error(f"BuildOrchestrator: Source parser '{source_parser_key}' not found in injected parsers for rule '{rule_key}'. Aborting build.")
               return False

            # 获取目标解析器实例 (可能用于验证或结构化 LLM 输出)
            target_parser_instance = self.parsers.get(target_parser_key) # Can be None if not required


            # 对每个源文件执行转换
            for source_file_path in source_files:
                self.log_info(f"BuildOrchestrator: Transforming file {source_file_path}...")

                # 派生目标文件路径
                # Note: For md->mcbc, the output file name might be derived differently,
                # e.g., from requirements.md to a single mcbc file like project_behaviors.mcbc
                # For mcbc->mcpc and mcpc->code, usually same base name different ext/dir.
                # The derive_target_file_name needs logic considering the rule/layer.
                # Simplified derivation for now: replace extension and change directory.
                source_base_name = os.path.splitext(os.path.basename(source_file_path))[0]
                # Specific handling for md->mcbc if needed, e.g., hardcode target name
                if rule_key == "md_to_mcbc":
                     target_file_name = f"{self.config_manager.get_setting('project_name', 'project').replace('-', '_')}_behaviors{target_ext}"
                else:
                     target_file_name = f"{source_base_name}{target_ext}"


                target_file_path = self.file_manager.get_file_path(project_path, target_layer_dir_key, target_file_name)
                self.log_info(f"BuildOrchestrator: Target file path derived: {target_file_path}")


                # 创建 LayerTransformer 实例并执行转换
                transformer = LayerTransformer(
                    self.config_manager,
                    self.file_manager,
                    self.symbol_manager,
                    self.llm_client,
                    source_parser_instance,
                    target_parser_instance # Pass target parser instance
                )

                file_transform_success = transformer.transform(source_file_path, target_file_path, rule_key)

                if not file_transform_success:
                    self.log_error(f"BuildOrchestrator: Transformation failed for file {source_file_path}. Aborting build.")
                    return False # 任意文件转换失败则整个构建失败

            # 在一个层级的所有文件转换完成后保存符号表
            # 这是为了确保即使构建中断，部分完成的符号更新也不会丢失
            self.symbol_manager.save_all_symbol_tables()
            self.log_info(f"BuildOrchestrator: Symbols saved after {current_layer_key} -> {next_layer_key} transition.")


        # 所有层级转换成功完成
        self.log_info("BuildOrchestrator: Forward build process completed.")
        # 最终保存一次符号表
        self.symbol_manager.save_all_symbol_tables() # Redundant but safe
        return True

    def run_reverse_build(self, project_path: str, start_layer: str, end_layer: str) -> bool:
        """
        执行从起始层级到结束层级的反向构建流程（待实现）。
        此方法在符号表中被标记为 frozen。

        Args:
            project_path: 项目根目录。
            start_layer: 起始层级 ('code', 'mcpc', 'mcbc')。
            end_layer: 结束层级 ('mcpc', 'mcbc', 'md')。

        Returns:
            bool: 构建流程是否完成成功。
        """
        # 根据符号表的定义，这是一个待实现/冻结的方法
        self.log_warning("BuildOrchestrator: Reverse build is currently not fully implemented.")
        # Future implementation will mirror run_forward_build but use reverse rules and layer sequence.
        # It would involve parsing target code, extracting structure, comparing/updating symbols,
        # and generating higher-level representations (.mcpc, .mcbc, .md) via LLM calls with different prompts.

        # As a placeholder, always return False and indicate not implemented
        # CALL self.symbol_manager.load_all_symbol_tables(project_path) # Need to load symbols for context
        # ... Placeholder logic ...
        return False # Indicate not implemented or failed for now

    def get_rule_key(self, source_layer_key: str, target_layer_key: str, direction: str) -> Optional[str]:
      """
      根据源层、目标层和方向查找匹配的构建规则键。

      Args:
          source_layer_key: 源层级键。
          target_layer_key: 目标层级键。
          direction: 构建方向 ('forward' 或 'reverse')。

      Returns:
          str | None: 匹配的构建规则键，如果没有找到则返回 None。
      """
      # 从 config_manager 获取完整的配置数据
      full_config = self.config_manager.get_config_data()
      rules_config = {}
      if direction == "forward":
          rules_config = full_config.get("build_rules", {})
      elif direction == "reverse":
          rules_config = full_config.get("reverse_build_rules", {})
      else:
          self.log_error(f"BuildOrchestrator: Invalid build direction: {direction}")
          return None

      layer_mapping = full_config.get("layer_mapping", {})

      for rule_key, rule_config in rules_config.items():
          # Check if the rule's input/output layer keys match the requested transition
          # Note: The layer_mapping values (directory names) are used in the rule config,
          # but the layer_keys (like "behavior_code") are used in the sequence.
          # We need to match using the keys, not the directory names.
          # Assuming rule_config directly uses layer_keys:
          input_key_in_rule = rule_config.get('input_layer_key') # Assuming rule config stores keys directly
          output_key_in_rule = rule_config.get('output_layer_key') # Assuming rule config stores keys directly

          # --- Alternative: Rule config stores directory keys, match using layer_mapping ---
          # If rule config uses directory keys like 'behavior_code_dir',
          # need to find the layer_key corresponding to those directory keys.
          # This seems overly complex. Let's assume rule_config directly uses layer_keys defined in BUILD_LAYERS.

          # --- Re-evaluating based on MCPC comment: rule_config['input_layer_dir_key'] ---
          # The MCPC comment says 'input_layer_dir_key' and 'output_layer_dir_key'.
          # So we need to find the layer_keys corresponding to those directory keys from layer_mapping.
          # Let's invert the layer_mapping to easily find layer_key from dir_key.
          dir_to_layer_key = {v: k for k, v in layer_mapping.items()}

          rule_input_dir_key = rule_config.get('input_layer_dir_key')
          rule_output_dir_key = rule_config.get('output_layer_dir_key')

          input_layer_from_rule = dir_to_layer_key.get(rule_input_dir_key)
          output_layer_from_rule = dir_to_layer_key.get(rule_output_dir_key)


          if input_layer_from_rule == source_layer_key and output_layer_from_rule == target_layer_key:
               return rule_key

      # Special case for requirements.md which might not have a standard directory key
      if source_layer_key == "requirements" and target_layer_key == "behavior_code" and direction == "forward":
           # Check if there's a rule explicitly for this, e.g., "md_to_mcbc"
           if "md_to_mcbc" in rules_config:
                rule_config = rules_config["md_to_mcbc"]
                # Need to check if its output matches the target layer key
                # This rule might not use standard layer_dir_keys, but direct extension/parser config
                # Assuming "md_to_mcbc" rule implicitly means requirements -> behavior_code
                # And its output_layer_dir_key (e.g., 'behavior_code_dir') matches target_layer_key's mapping
                target_dir_for_target_key = layer_mapping.get(target_layer_key) # e.g. 'src_mcbc' for 'behavior_code'
                if rule_config.get('output_layer_dir_key') == target_dir_for_target_key:
                    return "md_to_mcbc"


      self.log_warning(f"BuildOrchestrator: Could not find rule key for {source_layer_key} -> {target_layer_key} ({direction}).")
      return None

    def derive_target_file_name(self, source_file_path: str, source_ext: str, target_ext: str) -> str:
      """
      根据源文件路径和扩展名，生成目标文件的文件名（替换扩展名）。

      Args:
          source_file_path: 源文件的完整路径。
          source_ext: 源文件的扩展名 (e.g., '.mcbc')。
          target_ext: 目标文件的扩展名 (e.g., '.mcpc')。

      Returns:
          str: 生成的目标文件名 (不包含路径)。
      """
      # 获取源文件的不带扩展名的基础名
      base_name = os.path.splitext(os.path.basename(source_file_path))[0]

      # 添加目标扩展名
      target_name = base_name + target_ext

      self.log_info(f"BuildOrchestrator: Derived target name for {os.path.basename(source_file_path)} ({source_ext} -> {target_ext}): {target_name}")
      return target_name


class LayerTransformer:
    """
    层级转换器类，负责执行具体的层级转换（如 .mcbc -> .mcpc），调用 LLM。
    """

    def __init__(
        self,
        config_manager: ConfigManager,
        file_manager: FileManager,
        symbol_manager: SymbolTableManager,
        llm_client: LLMClient,
        source_parser: Any, # Specific parser instance for source format
        target_parser: Optional[Any] # Specific parser instance for target format (Optional)
    ):
        """
        初始化层级转换器。

        Args:
            config_manager: 配置管理器实例。
            file_manager: 文件管理器实例。
            symbol_manager: 符号表管理器实例。
            llm_client: LLM 客户端实例。
            source_parser: 用于解析源文件内容的特定解析器实例。
            target_parser: 可选的，用于处理或验证目标文件内容的特定解析器实例。
        """
        self.config_manager: ConfigManager = config_manager
        self.file_manager: FileManager = file_manager
        self.symbol_manager: SymbolTableManager = symbol_manager
        self.llm_client: LLMClient = llm_client
        self.source_parser: Any = source_parser
        self.target_parser: Optional[Any] = target_parser # Can be None

        self.log_info = print
        self.log_warning = print
        self.log_error = print

    def transform(self, source_file_path: str, target_file_path: str, build_rule_key: str) -> bool:
        """
        执行从源文件到目标文件的转换。
        包括读取、解析、生成LLM提示词、调用LLM、处理响应、更新符号表和写入文件。

        Args:
            source_file_path: 源文件的完整路径。
            target_file_path: 目标文件的完整路径。
            build_rule_key: mccp_config.json 中的构建规则键 (e.g., 'mcbc_to_mcpc')。

        Returns:
            bool: 转换是否成功。
        """
        self.log_info(f"LayerTransformer: Transforming {source_file_path} to {target_file_path} using rule '{build_rule_key}'")

        # 读取源文件内容
        source_content = self.file_manager.read_file(source_file_path)
        if source_content is None:
            self.log_error(f"LayerTransformer: Failed to read source file: {source_file_path}")
            return False

        # 获取构建规则配置
        rule_config = self.config_manager.get_build_rule(build_rule_key)
        if rule_config is None:
           self.log_error(f"LayerTransformer: Build rule configuration not found for key: {build_rule_key}")
           return False

        # 获取所有符号表数据，作为LLM的上下文
        all_symbols_data = self.symbol_manager.get_all_symbols()

        # 获取完整的项目配置，作为LLM的上下文
        full_config = self.config_manager.get_config_data()

        # 生成 LLM 提示词
        # PromptGenerator 需要 ConfigManager 来获取提示词模板
        prompt_generator = PromptGenerator(self.config_manager)
        llm_prompt = prompt_generator.generate_prompt(
            build_rule_key,
            source_content,
            all_symbols_data,
            full_config
        )
        if not llm_prompt:
           self.log_error("LayerTransformer: Failed to generate LLM prompt.")
           return False

        # 调用 LLM
        self.log_info(f"LayerTransformer: Calling LLM for rule '{build_rule_key}'...")
        # Prepare context for LLM, can include file paths for LLM to reference
        llm_context = {
            "source_file": source_file_path,
            "target_file": target_file_path,
            "rule": build_rule_key,
            "config": full_config, # Pass full config as context too
            "symbols": all_symbols_data # Pass symbols as context
        }
        llm_response_text = self.llm_client.generate_content(llm_prompt, llm_context)

        if not llm_response_text:
            self.log_error("LayerTransformer: LLM returned empty response.")
            return False

        # 处理 LLM 响应
        # 假设 LLM 直接输出了目标文件的内容
        generated_content = llm_response_text

        # --- 符号更新逻辑 (复杂部分，待细化) ---
        # LLM 可能在生成目标内容时引入新的符号或修改现有符号的细节
        # 例如，mcbc->mcpc 时，LLM 可能为行为添加参数和类型提示
        # 或 mcpc->py 时，LLM 可能为伪代码中的变量确定具体类型
        # 这部分需要解析 generated_content 或 LLM 响应的特定结构来提取符号更新信息。
        # 然后调用 self.symbol_manager.update_symbol(symbol_update)
        # 并且必须检查符号的 'is_frozen' 属性，拒绝更新 frozen 的符号。
        # For now, this complex logic is represented by a placeholder comment.
        self.log_info("LayerTransformer: Symbol update logic from LLM response skipped (complex, requires detailed parser).")
        # Example placeholder:
        # try:
        #     # Assuming a method exists to extract symbol changes from the generated content
        #     suggested_symbol_updates = self._extract_symbol_updates_from_content(generated_content, target_file_path, build_rule_key)
        #     for symbol_update_data in suggested_symbol_updates:
        #         # The symbol update method should handle the 'is_frozen' check internally
        #         if not self.symbol_manager.update_symbol(symbol_update_data):
        #             self.log_warning(f"LayerTransformer: Failed to apply symbol update for {symbol_update_data.get('name')} in {symbol_update_data.get('module_name')}. Possibly frozen.")
        # except Exception as e:
        #     self.log_error(f"LayerTransformer: Error during symbol update extraction/application: {e}")
        #     # Decide if this error is fatal or just a warning


        # 如果目标解析器存在，可选地验证或处理生成的内容
        # IF self.target_parser IS NOT None THEN
        #    try:
        #        # Assuming target_parser has a validate or parse method
        #        # parsed_target_data = self.target_parser.parse(generated_content)
        #        self.log_info(f"LayerTransformer: Generated content validated/parsed by target parser {type(self.target_parser).__name__}.")
        #    except Exception as e:
        #        self.log_warning(f"LayerTransformer: Failed to validate/parse generated content with target parser: {e}")
        #        # Decide if parsing failure should fail the transformation
        #        # return False # Or log and continue?
        # END IF


        # 将生成的内容写入目标文件
        success = self.file_manager.write_file(target_file_path, generated_content)
        if not success:
            self.log_error(f"LayerTransformer: Failed to write target file: {target_file_path}")
            return False

        self.log_info(f"LayerTransformer: Successfully transformed {source_file_path} to {target_file_path}.")
        return True

    # Placeholder for complex symbol extraction logic
    def _extract_symbol_updates_from_content(self, content: str, file_path: str, rule_key: str) -> List[Dict]:
        """
        Placeholder: 从生成的内容中提取建议的符号更新。
        这是一个复杂的过程，依赖于生成内容的格式和构建规则。
        例如，解析生成的 .mcpc 或 .py 文件，识别新的或修改的函数签名、类属性等。
        """
        self.log_warning(f"LayerTransformer: Placeholder method _extract_symbol_updates_from_content called for {file_path}, rule {rule_key}.")
        # Implement parsing logic specific to the target format generated by the LLM for this rule
        # Example: If target is .mcpc, use McpcParser to get structure, compare with existing symbols,
        # and propose updates for non-frozen symbols.
        # If target is .py, use AST parser to get code structure and propose updates.
        return [] # Return empty list for now
```

```python
# -*- coding: utf-8 -*-

"""
MCCP Toolchain - LLM Integration Module

This module integrates with Large Language Models (LLMs) using the Langchain framework
to facilitate AI-driven transformations between MCCP layers.
It includes the client for interacting with the LLM and a generator for crafting prompts.
"""

import os
import json
from typing import Dict, Any, Optional, List

# Import Langchain components
# Note: Specific LLM import might depend on the configuration (e.g., ChatOpenAI, LlamaCpp)
# Using a generic Langchain interface like BaseChatModel or BaseLLM is preferred.
from langchain_core.prompts import ChatPromptTemplate, PromptTemplate
from langchain_core.output_parsers import StrOutputParser
# We might not need specific chains if we call the model directly, but LLMChain is common.
# from langchain.chains import LLMChain
from langchain_openai import ChatOpenAI # Example LLM implementation

# Import MCCP Toolchain Modules (Forward declarations for type hinting)
# import mccp_toolchain.mccp.config
# import mccp_toolchain.mccp.parsers # Needed by parse_response

# Define placeholders or mock classes for dependencies to satisfy type hints
class ConfigManager:
    """Placeholder for mccp_toolchain.mccp.config.ConfigManager."""
    def __init__(self, file_manager: 'FileManager'): pass
    def load_config(self, project_path: str) -> bool: pass
    def get_setting(self, key: str) -> Any: pass
    def get_layer_dir(self, layer_key: str) -> Optional[str]: pass
    def get_build_rule(self, rule_key: str) -> Optional[Dict]: pass
    def get_config_data(self) -> Dict: pass
    def get_project_root(self) -> Optional[str]: pass

# Assuming parsers module provides these classes/functions
class JsonParser:
    def parse(self, content: str) -> Dict: pass
    def generate(self, data: Dict) -> str: pass

# Now import the actual modules
try:
    from mccp_toolchain.mccp.config import ConfigManager
    from mccp_toolchain.mccp.parsers import JsonParser # Assuming JsonParser is in mccp.parsers
    # Add other specific parsers here if parse_response needs direct access
    # from mccp_toolchain.mccp.parsers import McbcParser, McpcParser, TargetCodeParser

except ImportError as e:
    print(f"Error importing MCCP Toolchain modules in core/llm: {e}")
    # In a real app, handle gracefully. For code generation, assume imports are correct.


class LLMClient:
    """
    LLM 客户端类，封装 Langchain 调用。
    负责连接和调用配置的大语言模型。
    """

    def __init__(self, config_manager: ConfigManager):
        """
        初始化 LLM 客户端，读取配置并设置 Langchain 模型。

        Args:
            config_manager: 配置管理器实例。
        """
        self.config_manager: ConfigManager = config_manager
        self.langchain_model: Any = None # Placeholder for Langchain model instance

        # 获取 LLM 设置
        model_name = self.config_manager.get_setting("llm_settings.model")
        api_url = self.config_manager.get_setting("llm_settings.api_url")
        api_key = self.config_manager.get_setting("llm_settings.api_key")
        # Add other potential settings like temperature, max_tokens etc.

        self.log_info = print
        self.log_warning = print
        self.log_error = print

        # 初始化 Langchain 模型
        # This part depends on the specific LLM configured.
        # Using ChatOpenAI as an example. More complex logic might be needed
        # to handle different model types based on config.
        if model_name and api_key: # Basic check if settings are available
             try:
                 # Configure environment variable for API key, or pass key directly
                 os.environ["OPENAI_API_KEY"] = api_key # Example for OpenAI

                 # Check if api_url suggests a specific endpoint (e.g., for local models)
                 # Note: ChatOpenAI might not support arbitrary API URLs directly in constructor
                 # For custom endpoints or other models, a different Langchain class would be needed.
                 if api_url and "openai.com" not in api_url:
                      self.log_warning(f"LLMClient: Configured API URL '{api_url}' might not be directly supported by ChatOpenAI. Using default endpoint.")
                      # For custom endpoints, consider models like ChatGroq, ChatLiteLLM, or custom integrations

                 self.log_info(f"LLMClient: Initializing Langchain model: {model_name}")
                 self.langchain_model = ChatOpenAI(model=model_name, openai_api_key=api_key) # Use specific model class
                 # Other potential parameters: temperature=..., base_url=api_url if supported

             except Exception as e:
                 self.log_error(f"LLMClient: Failed to initialize Langchain model {model_name}: {e}")
                 self.langchain_model = None # Ensure model is None if initialization fails
        else:
            self.log_warning("LLMClient: LLM model name or API key not configured. LLM calls will not function.")
            self.langchain_model = None # Ensure model is None if no config


    def generate_content(self, prompt: str, context: Dict) -> str:
        """
        根据提示词和上下文调用 LLM 生成内容。

        Args:
            prompt: 发送给 LLM 的提示词字符串。
            context: 包含上下文信息的字典 (e.g., source_file, target_file, rule, config, symbols)。

        Returns:
            str: LLM 返回的原始文本响应。如果模型未初始化或调用失败，返回空字符串。
        """
        if self.langchain_model is None:
            self.log_error("LLMClient: LLM model is not initialized. Cannot generate content.")
            return ""

        self.log_info("LLMClient: Sending prompt to LLM...")
        # Langchain models typically accept a prompt string directly or a list of message objects.
        # A simple prompt template can wrap the string.
        try:
            # Use a basic PromptTemplate for the raw string prompt generated by PromptGenerator
            # Or, if the prompt generator provides structured messages, pass them directly.
            # Assuming PromptGenerator provides a single string for now.
            # Simple invocation:
            response = self.langchain_model.invoke(prompt)

            # Langchain model.invoke() returns a Response object (like AIMessage from Chat models)
            # Extract the text content from the response.
            generated_text = response.content # For chat models

            self.log_info("LLMClient: Received response from LLM.")
            return generated_text

        except Exception as e:
            self.log_error(f"LLMClient: Error during LLM content generation: {e}")
            return ""


    def parse_response(self, response_text: str, target_format: str) -> Any:
        """
        解析 LLM 返回的文本，将其结构化或验证格式。

        Args:
            response_text: LLM 返回的原始文本。
            target_format: 期望的目标格式标识符 (e.g., 'mcbc', 'mcpc', 'python_code', 'json')。

        Returns:
            object: 结构化数据 (如 dict) 或原始文本，取决于格式和解析能力。
        """
        self.log_info(f"LLMClient: Parsing LLM response for target format: {target_format}")
        # Note: The specific parsing logic depends on the target format and expected LLM output structure.
        # This method might delegate to specific parsers or contain basic validation.

        if target_format == "json":
            try:
                # Assuming JsonParser is available and works
                json_parser = JsonParser() # Instantiate or get injected? Symbol suggests instantiate.
                parsed_data = json_parser.parse(response_text)
                self.log_info("LLMClient: Successfully parsed response as JSON.")
                return parsed_data
            except Exception as e:
                self.log_error(f"LLMClient: Failed to parse response as JSON: {e}")
                # Decide whether to return None, raise error, or return raw text on failure
                return response_text # Return raw text on JSON parsing failure for now
        elif target_format in ["mcbc", "mcpc", "python_code"]:
             # For structured text formats like MCBC, MCPC, or code,
             # the LayerTransformer might expect the raw text directly,
             # and use dedicated parsers (like McbcParser, McpcParser, TargetCodeParser)
             # *after* this step, or as part of symbol update logic.
             # Or, this method could instantiate and use those parsers if they have a `parse_text` equivalent.
             # Based on available symbols, parsers have a `parse(content: str)` method.
             # A dedicated `parse_response` method might not be the best place for full file parsing.
             # Let's return the raw text and leave the parsing to components that use the output.
             self.log_info(f"LLMClient: Returning raw text response for format: {target_format}. Parsing delegated elsewhere.")
             return response_text # Return raw text
        else:
            self.log_warning(f"LLMClient: Unknown target format for parsing: {target_format}. Returning raw text.")
            return response_text # Return raw text for unknown formats


class PromptGenerator:
    """
    提示词生成器类，根据源内容、目标格式、符号表和配置生成结构化的 LLM 提示词。
    """

    def __init__(self, config_manager: ConfigManager):
        """
        初始化提示词生成器。

        Args:
            config_manager: 配置管理器实例。
        """
        self.config_manager: ConfigManager = config_manager
        self.log_info = print
        self.log_error = print


    def generate_prompt(
        self,
        build_rule_key: str,
        source_content: str,
        symbols: Dict,
        config: Dict
    ) -> str:
        """
        结合基础提示词模板、源内容、符号表和配置生成完整的提示词。

        Args:
            build_rule_key: 构建规则键 (e.g., 'mcbc_to_mcpc')。
            source_content: 源文件内容的字符串。
            symbols: 相关的分布式符号表内容字典。
            config: mccp_config.json 配置字典。

        Returns:
            str: 生成的完整提示词字符串。如果模板未找到，返回空字符串。
        """
        self.log_info(f"PromptGenerator: Generating prompt for rule '{build_rule_key}'")

        # 从配置中获取基础提示词模板
        rule_config = self.config_manager.get_build_rule(build_rule_key)
        if rule_config is None:
             self.log_error(f"PromptGenerator: Rule config not found for key: {build_rule_key}")
             return ""

        base_template = rule_config.get('llm_prompt')

        if not base_template:
            self.log_error(f"PromptGenerator: Prompt template not found in config for rule: {build_rule_key}")
            return ""

        # 格式化模板，注入上下文信息
        # 提示词模板期望使用占位符，例如 {source_content}, {symbols}, {config}
        # 需要将 symbols 和 config 字典转换为 JSON 字符串，以便在文本提示中包含结构化数据
        try:
            symbols_json_str = json.dumps(symbols, indent=2, ensure_ascii=False)
            config_json_str = json.dumps(config, indent=2, ensure_ascii=False)

            # 使用 Langchain PromptTemplate 或 Python f-string 进行格式化
            # 使用 Python f-string 更直接，假设模板是标准的 Python format string
            # 或者使用 Langchain PromptTemplate.from_template(base_template).format(...)
            # Langchain approach:
            # prompt_template = PromptTemplate.from_template(base_template)
            # formatted_prompt = prompt_template.format(
            #     source_content=source_content,
            #     symbols=symbols_json_str,
            #     config=config_json_str
            # )

            # Python f-string approach (simpler if placeholders are consistent):
            # Need to be careful with f-string syntax if { } are used literally in prompt
            # Let's stick to Langchain's PromptTemplate as it's designed for this.
            # Ensure the base_template placeholders match {variable_name} format.

            # Langchain PromptTemplate requires variable names to be explicitly listed if not inferred
            # Or use a ChatPromptTemplate if the prompt is better structured as system/human messages
            # Assuming a simple string template for now, compatible with PromptTemplate.from_template
            # This might need adjustment based on actual prompt template content
            prompt_template = PromptTemplate.from_template(base_template)
            formatted_prompt = prompt_template.format(
                 source_content=source_content,
                 symbols=symbols_json_str,
                 config=config_json_str
                 # Add other potential variables needed by templates, e.g., target_format, conventions
            )


            self.log_info(f"PromptGenerator: Prompt generated successfully for rule '{build_rule_key}'.")
            return formatted_prompt

        except KeyError as e:
            self.log_error(f"PromptGenerator: Missing expected placeholder in template for rule '{build_rule_key}': {e}. Template: {base_template[:100]}...")
            return ""
        except Exception as e:
            self.log_error(f"PromptGenerator: Error formatting prompt for rule '{build_rule_key}': {e}")
            return ""

```

```python
# -*- coding: utf-8 -*-

"""
MCCP Toolchain - MCCP Parsers Module

This module provides classes for parsing and generating various MCCP-related
file formats, including requirements (.md), behavior code (.mcbc),
pseudo code (.mcpc), target code (e.g., .py), and configuration (.json).
"""

import json
import os
import re
import pathlib
import ast # Useful for parsing Python code

from typing import Dict, Any, Optional, List

# No external MCCP dependencies needed within these basic parser stubs
# import mccp_toolchain.utils # Needed by some parsing/generating logic potentially?
# from mccp_toolchain.utils import snake_to_pascal_case, pascal_to_snake_case # Example usage

class RequirementsParser:
    """
    解析 requirements.md 文件的类。
    将 Markdown 格式的需求文本解析为结构化数据。
    """
    def parse(self, content: str) -> Dict[str, Any]:
        """
        将 Markdown 格式的需求文本解析为结构化数据。

        Args:
            content: requirements.md 文件的文本内容。

        Returns:
            dict: 结构化表示的需求数据。
        """
        print("RequirementsParser: Placeholder parse method called.")
        # Logic to parse markdown headings, lists, and text into a structured dictionary.
        # Identify sections like "1. Project Vision", "2. Core Function Requirements", etc.
        # Extract requirement IDs (e.g., SR.Func.Build.Forward.1), descriptions, and hierarchical structure.
        # Example basic structure based on headings:
        data: Dict[str, Any] = {}
        current_section: Optional[str] = None
        lines = content.splitlines()
        for line in lines:
            line = line.strip()
            if line.startswith("# "):
                # Top level heading (e.g., # Software Requirements Document) - ignore or use as title
                pass
            elif line.startswith("## "):
                # Section heading (e.g., ## 1. Project Vision)
                current_section = line[3:].strip()
                data[current_section] = "" # Initialize as empty, could be list or dict
            elif line.startswith("### "):
                 # Sub-section heading
                 sub_section = line[4:].strip()
                 if current_section:
                     if isinstance(data[current_section], str):
                          data[current_section] = {sub_section: ""} # Convert to dict
                     else:
                          data[current_section][sub_section] = ""
                 # else: ignore sub-section if no parent section

            # Simple append logic - needs refinement for lists/details
            elif current_section:
                 if isinstance(data[current_section], str):
                      data[current_section] += line + "\n"
                 elif isinstance(data[current_section], dict):
                      # Append to the last sub-section or handle more structure
                       last_sub_section = list(data[current_section].keys())[-1] if data[current_section] else None
                       if last_sub_section:
                            data[current_section][last_sub_section] += line + "\n"


        # This is a very basic placeholder parse. A real implementation would need
        # a proper Markdown parser library and more sophisticated logic.
        print("RequirementsParser: Returning placeholder data.")
        return data

class McbcParser:
    """
    解析 .mcbc (Behavior Code) 文件的类。
    将 .mcbc 文本解析为结构化的行为描述对象，并能将结构化数据生成回 .mcbc 格式。
    """
    def parse(self, content: str) -> Dict[str, Any]:
        """
        将 .mcbc 文本解析为结构化的行为描述对象。

        Args:
            content: .mcbc 文件的文本内容。

        Returns:
            dict: 结构化的行为描述数据。
        """
        print("McbcParser: Placeholder parse method called.")
        # Logic to parse MCBC markdown format:
        # Identify "# Module:", "### Overview", "#### Class:", "### Components", etc.
        # Structure into dictionary: { "module_name": ..., "overview": {...}, "components": [{ "type": "class", "name": ..., "behaviors": [...] }] }
        # Requires sophisticated text processing, likely line-by-line with state tracking.
        # Example structure based on headings and key-value lines:
        data: Dict[str, Any] = {"module_name": None, "overview": {}, "components": []}
        current_component: Optional[Dict] = None
        current_behavior: Optional[Dict] = None
        current_section: Optional[str] = None # e.g., "overview", "component", "behavior"

        lines = content.splitlines()
        for line in lines:
             stripped_line = line.strip()

             if stripped_line.startswith("# Module: "):
                  data["module_name"] = stripped_line[len("# Module: "):].strip()
                  current_section = None # Reset section state
             elif stripped_line.startswith("### Overview"):
                  data["overview"] = {}
                  current_section = "overview"
                  current_component = None # Reset component state
                  current_behavior = None # Reset behavior state
             elif stripped_line.startswith("### Components"):
                  data["components"] = []
                  current_section = "components"
                  current_component = None # Reset component state
                  current_behavior = None # Reset behavior state
             elif stripped_line.startswith("#### Class: "):
                  component_name = stripped_line[len("#### Class: "):].strip()
                  current_component = {"type": "class", "name": component_name, "behaviors": []}
                  data["components"].append(current_component)
                  current_section = "component" # Inside a component
                  current_behavior = None # Reset behavior state
             elif stripped_line.startswith("- Description:") and current_component and current_section == "component":
                  current_component["description"] = stripped_line[len("- Description:"):].strip()
             elif stripped_line.startswith("- Behaviors:") and current_component and current_section == "component":
                 # Prepare for behavior list
                 pass # No specific action, subsequent lines are behaviors
             elif stripped_line.startswith("- ") and current_section == "component":
                 # This is likely a behavior definition line like "- Behavior Name (`method_name`):"
                 behavior_line = stripped_line[2:].strip()
                 if "(`" in behavior_line and "`):" in behavior_line:
                     parts = behavior_line.split("(`", 1)
                     behavior_name_display = parts[0].strip()
                     method_name_part = parts[1].split("`):", 1)
                     method_name = method_name_part[0].strip()
                     current_behavior = {
                         "name_display": behavior_name_display,
                         "method_name": method_name,
                         "description": "",
                         "purpose": "",
                         "process": "",
                         "input": "",
                         "output": "",
                         "dependencies": "",
                         "interactions": ""
                     }
                     if current_component:
                          current_component["behaviors"].append(current_behavior)
                     current_section = "behavior" # Inside a behavior
                 # Add other list items here if needed for component details outside behaviors?
             elif stripped_line.startswith("- Purpose:") and current_behavior and current_section == "behavior":
                 current_behavior["purpose"] = stripped_line[len("- Purpose:"):].strip()
             elif stripped_line.startswith("- Process:") and current_behavior and current_section == "behavior":
                 current_behavior["process"] = stripped_line[len("- Process:"):].strip()
             elif stripped_line.startswith("- Input:") and current_behavior and current_section == "behavior":
                 current_behavior["input"] = stripped_line[len("- Input:"):].strip()
             elif stripped_line.startswith("- Output:") and current_behavior and current_section == "behavior":
                 current_behavior["output"] = stripped_line[len("- Output:"):].strip()
             elif stripped_line.startswith("- Dependencies:") and current_behavior and current_section == "behavior":
                 current_behavior["dependencies"] = stripped_line[len("- Dependencies:"):].strip()
             elif stripped_line.startswith("- Interactions:") and current_behavior and current_section == "behavior":
                 current_behavior["interactions"] = stripped_line[len("- Interactions:"):].strip()
             elif stripped_line and current_section == "overview":
                 # Append lines to overview, sophisticated parsing needed for key-value pairs
                 # For now, just append (basic)
                 for key_prefix in ["- Purpose:", "- Responsibilities:", "- Interactions:"]:
                      if stripped_line.startswith(key_prefix):
                           key = key_prefix[2:].strip(":")
                           data["overview"][key] = stripped_line[len(key_prefix):].strip()
                           break
                 else:
                      # If it didn't match a known key prefix, maybe append to a generic overview text or ignore
                      pass # Ignoring unformatted lines in overview for this simple parser
             # Add logic to handle continuation lines (indented lines after a list item) - complex

        # This placeholder parser is very simplistic. A real one would handle
        # indentation for multiline values, different list types, comments, etc.
        print("McbcParser: Returning placeholder data.")
        return data

    def generate(self, data: Dict[str, Any]) -> str:
        """
        将结构化数据生成为 .mcbc 格式的文本。

        Args:
            data: 结构化的行为描述数据。

        Returns:
            str: .mcbc 格式的文本字符串。
        """
        print("McbcParser: Placeholder generate method called.")
        # Logic to format a dictionary of behavior code data into the MCBC markdown structure.
        # Iterate through modules, classes, and behaviors, formatting each section.
        lines: List[str] = []

        module_name = data.get("module_name", "unknown_module")
        lines.append(f"# MCCP Behavior Code\n")
        lines.append(f"## Module: {module_name}\n")

        overview = data.get("overview", {})
        if overview:
            lines.append("### Overview")
            for key, value in overview.items():
                 if value: # Only include if value is not empty
                    lines.append(f"- {key}: {value}")
            lines.append("") # Add a blank line after section


        components = data.get("components", [])
        if components:
            lines.append("### Components")
            for component in components:
                comp_type = component.get("type", "unknown_type")
                comp_name = component.get("name", "unknown_component")
                lines.append(f"#### {comp_type.capitalize()}: {comp_name}")
                comp_description = component.get("description")
                if comp_description:
                    lines.append(f"- Description: {comp_description}")

                behaviors = component.get("behaviors", [])
                if behaviors:
                    lines.append("- Behaviors:")
                    for behavior in behaviors:
                        name_display = behavior.get("name_display", "Unknown Behavior")
                        method_name = behavior.get("method_name", "unknown_method")
                        lines.append(f"  - {name_display} (`{method_name}`):") # Note 2 space indent for nested list
                        # Add behavior details (purpose, process, input, output, etc.) with further indentation
                        for detail_key in ["purpose", "process", "input", "output", "dependencies", "interactions"]:
                             detail_value = behavior.get(detail_key)
                             if detail_value:
                                  # Needs careful handling for multiline values - adding simple indentation
                                  indented_value = "\n    ".join(str(detail_value).splitlines())
                                  lines.append(f"    - {detail_key.capitalize()}: {indented_value}") # Note 4 space indent


                lines.append("") # Blank line after component

        # Remove trailing blank lines
        while lines and not lines[-1].strip():
             lines.pop()

        mcbc_text = "\n".join(lines)
        print("McbcParser: Returning placeholder MCBC text.")
        return mcbc_text


class McpcParser:
    """
    解析 .mcpc (Pseudo Code) 文件的类。
    将 .mcpc 文本解析为结构化的符号-伪代码对象，并能将结构化数据生成回 .mcpc 格式。
    """
    def parse(self, content: str) -> Dict[str, Any]:
        """
        将 .mcpc 文本解析为结构化的符号-伪代码对象。

        Args:
            content: .mcpc 文件的文本内容。

        Returns:
            dict: 结构化的符号-伪代码数据。
        """
        print("McpcParser: Placeholder parse method called.")
        # Logic to parse MCPC pseudo-code structure:
        # Identify "MODULE", "CLASS", "METHOD", "FUNCTION", "CONSTANT", "DESCRIPTION", "INHERITS", "ATTRIBUTE", "PARAMETERS", "RETURNS", keywords like "SET", "CALL", "IF", "ELSE", "LOOP", "RETURN", "CREATE".
        # Represent the parsed structure in a dictionary.
        # Example structure: { "module_name": ..., "classes": [{ "name": ..., "methods": [...] }], "functions": [...], "constants": [...] }
        data: Dict[str, Any] = {"module_name": None, "classes": [], "functions": [], "constants": []}
        current_class: Optional[Dict] = None
        current_method_or_function: Optional[Dict] = None
        current_constant: Optional[Dict] = None
        current_section_type: Optional[str] = None # "module", "class", "method", "function"

        lines = content.splitlines()
        indent_level = 0
        pseudo_code_lines: List[str] = []

        def add_pseudo_code_block():
             """Helper to add accumulated pseudocode lines to the current item."""
             nonlocal pseudo_code_lines
             if pseudo_code_lines and current_method_or_function:
                  current_method_or_function["pseudo_code"] = "\n".join(pseudo_code_lines)
             pseudo_code_lines = [] # Reset

        for line in lines:
             stripped_line = line.strip()
             current_indent = len(line) - len(line.lstrip())

             # Check for block changes based on indentation or keywords
             if stripped_line.startswith(("MODULE", "CLASS", "METHOD", "FUNCTION", "CONSTANT")):
                  add_pseudo_code_block() # Save any preceding pseudocode
                  pseudo_code_lines = [] # Start new block accumulation

                  if stripped_line.startswith("MODULE "):
                       module_name = stripped_line[len("MODULE "):].split(" ", 1)[0].strip()
                       data["module_name"] = module_name
                       current_section_type = "module"
                       current_class = None
                       current_method_or_function = None
                       current_constant = None
                       indent_level = 0 # Assume MODULE is at root indent
                  elif stripped_line.startswith("CLASS "):
                       class_name = stripped_line[len("CLASS "):].split(" ", 1)[0].strip()
                       current_class = {"name": class_name, "description": "", "inherits": None, "attributes": [], "methods": []}
                       data["classes"].append(current_class)
                       current_section_type = "class"
                       current_method_or_function = None
                       current_constant = None
                       indent_level = current_indent # Class indent
                  elif stripped_line.startswith("METHOD ") and current_class:
                       method_name = stripped_line[len("METHOD "):].split("(", 1)[0].strip()
                       parameters_str = stripped_line.split("PARAMETERS", 1)[1].split(")", 1)[0].strip() if "PARAMETERS" in stripped_line else ""
                       returns_str = stripped_line.split("RETURNS", 1)[1].strip() if "RETURNS" in stripped_line else None
                       current_method_or_function = {"name": method_name, "description": "", "parameters": parameters_str, "return_type": returns_str, "pseudo_code": ""}
                       current_class["methods"].append(current_method_or_function)
                       current_section_type = "method"
                       current_constant = None
                       indent_level = current_indent # Method indent
                  elif stripped_line.startswith("FUNCTION "):
                       function_name = stripped_line[len("FUNCTION "):].split("(", 1)[0].strip()
                       parameters_str = stripped_line.split("PARAMETERS", 1)[1].split(")", 1)[0].strip() if "PARAMETERS" in stripped_line else ""
                       returns_str = stripped_line.split("RETURNS", 1)[1].strip() if "RETURNS" in stripped_line else None
                       current_method_or_function = {"name": function_name, "description": "", "parameters": parameters_str, "return_type": returns_str, "pseudo_code": ""}
                       data["functions"].append(current_method_or_function)
                       current_section_type = "function"
                       current_class = None # Functions are top-level
                       current_constant = None
                       indent_level = current_indent # Function indent
                  elif stripped_line.startswith("CONSTANT "):
                       constant_name = stripped_line[len("CONSTANT "):].split(" ", 1)[0].strip()
                       current_constant = {"name": constant_name, "description": "", "value": None} # Value needs to be parsed from subsequent lines
                       data["constants"].append(current_constant)
                       current_section_type = "constant"
                       current_class = None
                       current_method_or_function = None
                       indent_level = current_indent # Constant indent
                  # Handle DESCRIPTION, INHERITS, ATTRIBUTE, PARAMETERS, RETURNS on definition line or subsequent lines

             elif stripped_line.startswith("DESCRIPTION "):
                 desc = stripped_line[len("DESCRIPTION "):].strip('"').strip("'") # Simple quote removal
                 if current_section_type == "module" and data["module_name"]: data["description"] = desc
                 elif current_class and current_section_type == "class": current_class["description"] = desc
                 elif current_method_or_function and current_section_type in ["method", "function"]: current_method_or_function["description"] = desc
                 elif current_constant and current_section_type == "constant": current_constant["description"] = desc

             elif stripped_line.startswith("INHERITS ") and current_class and current_section_type == "class":
                 inherits_class = stripped_line[len("INHERITS "):].strip()
                 current_class["inherits"] = inherits_class

             elif stripped_line.startswith("ATTRIBUTE ") and current_class and current_section_type == "class":
                 parts = stripped_line[len("ATTRIBUTE "):].strip().split(":", 1)
                 if len(parts) == 2:
                      attr_name = parts[0].strip()
                      attr_type = parts[1].strip()
                      current_class["attributes"].append({"name": attr_name, "type": attr_type})

             elif stripped_line.startswith("VALUE ") and current_constant and current_section_type == "constant":
                  # This is a very basic parsing of the VALUE line
                  value_str = stripped_line[len("VALUE "):].strip()
                  try:
                       # Attempt to evaluate simple Python literals
                       # WARNING: eval() is dangerous for untrusted input.
                       # A safer approach would be to parse specific literal types (strings, numbers, lists, dicts, bools, None).
                       current_constant["value"] = json.loads(value_str) # Use json.loads for common literals
                  except json.JSONDecodeError:
                       # Fallback to string if not valid JSON literal
                       current_constant["value"] = value_str
                  except Exception:
                       current_constant["value"] = value_str # Catch other errors


             elif stripped_line: # Any other non-empty, non-comment line is considered pseudo-code body
                  if current_method_or_function:
                       # Remove the base indent of the method/function block for cleaner pseudocode storage
                       # Assuming consistent indentation within the block
                       if current_indent > indent_level: # Check if it's indented inside the block
                           # This part is tricky without strict indentation rules in MCPC
                           # Simple approach: just store the stripped line
                           pseudo_code_lines.append(stripped_line)
                       elif current_indent == indent_level:
                            # This looks like a new block item at the same level? Or continuation?
                            # Need more sophisticated state tracking
                            # For now, assume it's part of the current block if we are in one
                             pseudo_code_lines.append(stripped_line)
                       # else: less indented, means block ended - should have been caught by keyword check

        add_pseudo_code_block() # Add any remaining pseudocode lines

        # This is a very basic placeholder parse. A real implementation would need
        # robust state tracking based on keywords and indentation, handling multiline
        # descriptions, parameters, and complex pseudo-code structures accurately.
        print("McpcParser: Returning placeholder data.")
        return data


    def generate(self, data: Dict[str, Any]) -> str:
        """
        将结构化数据生成为 .mcpc 格式的文本。

        Args:
            data: 结构化的符号-伪代码数据。

        Returns:
            str: .mcpc 格式的文本字符串。
        """
        print("McpcParser: Placeholder generate method called.")
        # Logic to format a dictionary of symbol-pseudo code data into the MCPC text format.
        # Iterate through modules, classes, methods, functions, constants, formatting each.
        lines: List[str] = []

        module_name = data.get("module_name", "unknown_module")
        lines.append(f"# MCCP Symbol-Pseudo Code\n")
        lines.append(f"MODULE {module_name}")
        module_description = data.get("description")
        if module_description:
            lines.append(f"  DESCRIPTION \"{module_description}\"") # Indent 2 spaces

        lines.append("") # Blank line

        constants = data.get("constants", [])
        for const in constants:
             const_name = const.get("name", "UNKNOWN_CONSTANT")
             const_desc = const.get("description")
             const_value = const.get("value")
             lines.append(f"CONSTANT {const_name}")
             if const_desc:
                 lines.append(f"  DESCRIPTION \"{const_desc}\"")
             # Need to format value correctly - JSON dump is an option for complex types
             # Use simple repr() for basic types, json.dumps for dicts/lists
             value_repr = json.dumps(const_value, ensure_ascii=False) if isinstance(const_value, (dict, list)) else repr(const_value)
             lines.append(f"  VALUE {value_repr}")
             lines.append("") # Blank line

        classes = data.get("classes", [])
        for cls in classes:
            cls_name = cls.get("name", "UnknownClass")
            cls_desc = cls.get("description")
            cls_inherits = cls.get("inherits")
            lines.append(f"CLASS {cls_name}")
            if cls_desc:
                 lines.append(f"  DESCRIPTION \"{cls_desc}\"")
            if cls_inherits:
                 lines.append(f"  INHERITS {cls_inherits}")

            attributes = cls.get("attributes", [])
            if attributes:
                 lines.append("  # Attributes")
                 for attr in attributes:
                      attr_name = attr.get("name", "unknown_attr")
                      attr_type = attr.get("type", "any")
                      lines.append(f"  ATTRIBUTE {attr_name}: {attr_type}")


            methods = cls.get("methods", [])
            for method in methods:
                method_name = method.get("name", "unknown_method")
                method_desc = method.get("description")
                # Reconstruct PARAMETERS string - requires structured parameter data, not just a string
                # Assuming method["parameters"] is a list of dicts like {"name": "p1", "type": "T1"} from symbol table
                # But the parse method above stores it as a raw string. Need consistency.
                # Let's assume generate method receives structured parameter data if available.
                # For now, using a placeholder string if only string is available.
                parameters_str = method.get("parameters", "") # Assuming it might be the raw string from parse or structured list
                if isinstance(parameters_str, list): # If structured parameter list is available
                     param_list_str = ", ".join([f'{p.get("name", "p")}: {p.get("type", "any")}' for p in parameters_str])
                     parameters_str = f"(PARAMETERS {param_list_str})" if param_list_str else "()"
                else: # Assume it's already a string or empty
                    parameters_str = f"(PARAMETERS {parameters_str})" if parameters_str else "()"

                return_type = method.get("return_type")
                return_str = f" RETURNS {return_type}" if return_type else ""

                lines.append(f"  METHOD {method_name}{parameters_str}{return_str}")
                if method_desc:
                     lines.append(f"    DESCRIPTION \"{method_desc}\"") # Indent 4 spaces

                pseudo_code_body = method.get("pseudo_code", "")
                if pseudo_code_body:
                     # Add pseudo-code lines, indented consistently
                     body_lines = pseudo_code_body.splitlines()
                     for body_line in body_lines:
                          # Simple indentation - does not preserve original pseudo-code indentation
                          lines.append(f"    {body_line}") # Indent 4 spaces

            lines.append("") # Blank line after class

        functions = data.get("functions", [])
        for func in functions:
             func_name = func.get("name", "unknown_function")
             func_desc = func.get("description")
             # Parameter/Return handling similar to methods
             parameters_str = func.get("parameters", "")
             if isinstance(parameters_str, list):
                  param_list_str = ", ".join([f'{p.get("name", "p")}: {p.get("type", "any")}' for p in parameters_str])
                  parameters_str = f"(PARAMETERS {param_list_str})" if param_list_str else "()"
             else:
                 parameters_str = f"(PARAMETERS {parameters_str})" if parameters_str else "()"

             return_type = func.get("return_type")
             return_str = f" RETURNS {return_type}" if return_type else ""

             lines.append(f"FUNCTION {func_name}{parameters_str}{return_str}")
             if func_desc:
                  lines.append(f"  DESCRIPTION \"{func_desc}\"") # Indent 2 spaces

             pseudo_code_body = func.get("pseudo_code", "")
             if pseudo_code_body:
                  body_lines = pseudo_code_body.splitlines()
                  for body_line in body_lines:
                       lines.append(f"  {body_line}") # Indent 2 spaces

             lines.append("") # Blank line after function


        # Remove trailing blank lines
        while lines and not lines[-1].strip():
             lines.pop()


        mcpc_text = "\n".join(lines)
        print("McpcParser: Returning placeholder MCPC text.")
        return mcpc_text


class TargetCodeParser:
    """
    解析目标语言源代码（如 Python .py 文件）的类。
    将源代码解析为结构化数据，并能将结构化数据生成回源代码格式。
    主要用于反向构建流程。
    """
    def parse(self, content: str, language: str) -> Dict[str, Any]:
        """
        将源代码解析为结构化数据（类、函数、变量等），用于反向构建。

        Args:
            content: 源代码文件的文本内容。
            language: 目标语言 (e.g., 'python')。

        Returns:
            dict: 结构化表示的代码数据。
        """
        print(f"TargetCodeParser: Placeholder parse method called for language: {language}.")
        # Logic to parse source code based on language.
        # For Python, use AST (Abstract Syntax Tree) module.
        # Extract class definitions, method/function definitions (names, parameters, return hints), variable assignments, etc.
        # Structure this into a dictionary suitable for reverse transformation.
        data: Dict[str, Any] = {"language": language, "classes": [], "functions": [], "constants": [], "variables": []}

        if language.lower() == "python":
            try:
                tree = ast.parse(content)
                # Walk the AST and extract information
                for node in ast.walk(tree):
                    if isinstance(node, ast.ClassDef):
                        class_info = {
                            "name": node.name,
                            "lineno": node.lineno,
                            "col_offset": node.col_offset,
                            "bases": [ast.unparse(b) for b in node.bases],
                            "methods": [],
                            "attributes": [], # AST doesn't directly list attributes, need to find assignments
                            "docstring": ast.get_docstring(node),
                        }
                        # Find methods within the class body
                        for item in node.body:
                            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                                method_info = {
                                    "name": item.name,
                                    "type": "method",
                                    "lineno": item.lineno,
                                    "col_offset": item.col_offset,
                                    "parameters": [], # Need to parse args
                                    "return_type": ast.unparse(item.returns) if item.returns else None,
                                    "docstring": ast.get_docstring(item),
                                    "pseudo_code_summary": "..." # Placeholder summary
                                }
                                # Parse function/method arguments
                                for arg in item.args.args:
                                     param_info = {"name": arg.arg, "type": ast.unparse(arg.annotation) if arg.annotation else None}
                                     method_info["parameters"].append(param_info)
                                # Add self parameter explicitly for methods if needed? AST includes it.

                                class_info["methods"].append(method_info)
                            # TODO: Find attribute assignments (self.x = ...) within methods or __init__

                        data["classes"].append(class_info)

                    elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        # Top-level function
                        function_info = {
                            "name": node.name,
                            "type": "function",
                            "lineno": node.lineno,
                            "col_offset": node.col_offset,
                            "parameters": [], # Need to parse args
                            "return_type": ast.unparse(node.returns) if node.returns else None,
                            "docstring": ast.get_docstring(node),
                            "pseudo_code_summary": "..." # Placeholder summary
                        }
                        for arg in node.args.args:
                             param_info = {"name": arg.arg, "type": ast.unparse(arg.annotation) if arg.annotation else None}
                             function_info["parameters"].append(param_info)
                        data["functions"].append(function_info)

                    elif isinstance(node, ast.Assign):
                        # Simple variable assignments (may need to filter top-level vs class/function level)
                        # This is a basic attempt, need to check context
                        if not (isinstance(node.targets[0], ast.Attribute) and isinstance(node.targets[0].value, ast.Name) and node.targets[0].value.id == 'self'):
                             for target in node.targets:
                                if isinstance(target, ast.Name):
                                    var_info = {
                                        "name": target.id,
                                        "type": "variable",
                                        "lineno": node.lineno,
                                        "col_offset": node.col_offset,
                                        "value_preview": ast.unparse(node.value), # Simple representation of value
                                        # Need to determine scope (global, class, local) - complex with AST
                                    }
                                    # Filter for top-level? Or constant-like names?
                                    if not ast.unparse(node).strip().startswith(('def ', 'class ')): # Crude check for top level
                                        if var_info["name"].isupper(): # Simple heuristic for CONSTANT
                                             data["constants"].append(var_info)
                                        # else: data["variables"].append(var_info) # Could be local var, harder to track scope

            except SyntaxError as e:
                print(f"TargetCodeParser: Failed to parse Python code due to SyntaxError: {e}")
                # Return partial data or raise error

        else:
            print(f"TargetCodeParser: Parsing for language '{language}' is not implemented.")

        # This is a starting point. Full AST parsing for reverse engineering
        # complex code structure, dependencies, and logic is a significant task.
        print(f"TargetCodeParser: Returning placeholder data for language: {language}.")
        return data


    def generate(self, data: Dict[str, Any], language: str) -> str:
        """
        将结构化数据生成为源代码格式的文本，遵循代码规范。

        Args:
            data: 结构化的代码数据。
            language: 目标语言 (e.g., 'python')。

        Returns:
            str: 生成的源代码文本。
        """
        print(f"TargetCodeParser: Placeholder generate method called for language: {language}.")
        # Logic to generate source code from structured data based on language.
        # For Python, generate code strings from the dictionary representation, adhering to PEP8.
        # Add docstrings, comments, follow naming conventions.
        generated_code = ""

        if language.lower() == "python":
             lines: List[str] = []
             # Add module docstring (if available in data, or from config?)
             lines.append(f'"""\n{data.get("module_docstring", "Generated Python code.")}\n"""')
             lines.append("")

             # Imports (need to determine based on dependencies in symbol table or inferred?)
             # This is a complex part - dependencies should drive imports.
             lines.append("# Placeholder imports (determine from symbols/logic)")
             # Example: from mccp_toolchain.mccp.config import ConfigManager
             lines.append("")


             # Constants
             constants = data.get("constants", [])
             for const in constants:
                  const_name = const.get("name", "UNKNOWN_CONSTANT")
                  const_value_repr = repr(const.get("value", None)) # Simple repr for value
                  # Docstring for constant? PEP8 doesn't require, but maybe a comment
                  lines.append(f"{const_name} = {const_value_repr}")
                  const_desc = const.get("description") # Assuming description is in data
                  if const_desc:
                       lines.append(f'# {const_desc}') # Simple comment
                  lines.append("")


             # Functions
             functions = data.get("functions", [])
             for func in functions:
                  func_name = func.get("name", "unknown_function")
                  func_docstring = func.get("docstring") # Assuming docstring is in data
                  # Reconstruct parameters string from structured parameter data
                  parameters: List[Dict] = func.get("parameters", []) # Assuming list of {"name": "p", "type": "T"}
                  param_strings = []
                  for p in parameters:
                      param_str = p.get("name", "arg")
                      param_type = p.get("type")
                      if param_type:
                          param_str += f": {param_type}"
                      param_strings.append(param_str)
                  params_declaration = ", ".join(param_strings)

                  return_type = func.get("return_type")
                  return_annotation = f" -> {return_type}" if return_type else ""

                  lines.append(f"def {func_name}({params_declaration}){return_annotation}:")
                  if func_docstring:
                       # Format docstring with indentation
                       docstring_lines = func_docstring.splitlines()
                       lines.append('    """')
                       for d_line in docstring_lines:
                            lines.append(f'    {d_line}')
                       lines.append('    """')

                  # Function body (placeholder - actual code generation from pseudocode is complex)
                  lines.append("    # TODO: Implement logic based on pseudo_code_summary or parsed logic")
                  lines.append("    pass # Placeholder")
                  lines.append("")


             # Classes
             classes = data.get("classes", [])
             for cls in classes:
                  cls_name = cls.get("name", "UnknownClass")
                  cls_docstring = cls.get("docstring") # Assuming docstring is in data
                  # Reconstruct base classes
                  bases = cls.get("bases", [])
                  bases_declaration = f"({', '.join(bases)})" if bases else ""

                  lines.append(f"class {cls_name}{bases_declaration}:")
                  if cls_docstring:
                       docstring_lines = cls_docstring.splitlines()
                       lines.append('    """')
                       for d_line in docstring_lines:
                            lines.append(f'    {d_line}')
                       lines.append('    """')


                  # Attributes (initialization in __init__ or class attributes?)
                  # Need to handle attributes extracted by parse or defined in symbols
                  # For simplicity, let's assume attributes need to be added to __init__ or class scope
                  attributes = cls.get("attributes", []) # Assuming list of {"name": "a", "type": "T"}
                  if attributes:
                       lines.append("    # Class attributes (or instance attributes in __init__)")
                       for attr in attributes:
                            attr_name = attr.get("name", "unknown_attr")
                            attr_type = attr.get("type")
                            # This needs context (class attribute vs instance attribute)
                            # For instance attributes, they belong in __init__
                            lines.append(f"    #{attr_name}: {attr_type} # Placeholder for attribute declaration/init")


                  # Methods
                  methods = cls.get("methods", [])
                  for method in methods:
                       method_name = method.get("name", "unknown_method")
                       method_docstring = method.get("docstring") # Assuming docstring is in data
                       parameters: List[Dict] = method.get("parameters", []) # Assuming list of {"name": "p", "type": "T"}
                       # Add 'self' explicitly if it's a method and not already in params?
                       # Or assume parse includes 'self' if it's there. Let's assume parse includes it.
                       param_strings = []
                       for p in parameters:
                            param_str = p.get("name", "arg")
                            param_type = p.get("type")
                            if param_type:
                                 param_str += f": {param_type}"
                            param_strings.append(param_str)
                       params_declaration = ", ".join(param_strings)

                       return_type = method.get("return_type")
                       return_annotation = f" -> {return_type}" if return_type else ""

                       lines.append(f"    def {method_name}({params_declaration}){return_annotation}:")
                       if method_docstring:
                            docstring_lines = method_docstring.splitlines()
                            lines.append('        """') # Indent +4 spaces
                            for d_line in docstring_lines:
                                 lines.append(f'        {d_line}') # Indent +4 spaces
                            lines.append('        """')

                       # Method body (placeholder)
                       lines.append("        # TODO: Implement logic based on pseudo_code_summary or parsed logic")
                       lines.append("        pass # Placeholder")
                       lines.append("") # Blank line after method


                  # If the class is empty or only has methods, add 'pass' or docstring at class level
                  if not methods and not attributes: # Crude check
                       lines.append("    pass") # Or include class docstring if only that exists
                  lines.append("") # Blank line after class


        else:
            generated_code = f"# Code generation for language '{language}' is not implemented.\n"
            print(f"TargetCodeParser: Code generation for language '{language}' is not implemented.")


        # Ensure PEP8 formatting - A real implementation might use a linter/formatter like Black
        # Simple formatting: ensure consistent indentation (already attempted), add blank lines.
        # Add comments explaining complex parts or generated sections.
        # Ensure correct imports are generated based on used types/symbols - very complex!

        generated_code = "\n".join(lines)
        print(f"TargetCodeParser: Returning placeholder generated code for language: {language}.")
        return generated_code


class JsonParser:
    """
    解析 JSON 配置文件的通用类。
    """
    def parse(self, content: str) -> Dict[str, Any]:
        """
        解析 JSON 文本为 Python 字典。

        Args:
            content: JSON 文件的文本内容。

        Returns:
            dict: 解析出的 Python 字典。

        Raises:
            json.JSONDecodeError: 如果内容不是有效的 JSON。
        """
        # Use built-in JSON library.
        print("JsonParser: Parsing JSON content.")
        return json.loads(content)

    def generate(self, data: Dict[str, Any]) -> str:
        """
        将 Python 字典生成为格式化的 JSON 文本。

        Args:
            data: 要序列化的 Python 字典。

        Returns:
            str: 格式化的 JSON 字符串。
        """
        # Use built-in JSON library with indentation for readability.
        print("JsonParser: Generating JSON content.")
        return json.dumps(data, indent=2, ensure_ascii=False)

```

```python
# -*- coding: utf-8 -*-

"""
MCCP Toolchain - MCCP File Manager Module

This module handles file system operations for the MCCP toolchain,
including project structure creation, file reading/writing, path resolution,
and listing files within project layers based on configuration.
"""

import os
import pathlib
import json
from typing import Dict, Any, Optional, List, Callable

# Import MCCP Toolchain Modules (Forward declarations for type hinting)
# import mccp_toolchain.mccp.config
# import mccp_toolchain.mccp.parsers # Needed for JsonParser in create_project_structure?

# Define placeholders or mock classes for dependencies to satisfy type hints
class ConfigManager:
    """Placeholder for mccp_toolchain.mccp.config.ConfigManager."""
    # Need __init__ to accept FileManager for circular dependency workaround in main.py
    def __init__(self, file_manager: Optional['FileManager'] = None):
        self.file_manager = file_manager # Store reference if passed
    def load_config(self, project_path: str) -> bool: pass
    def get_setting(self, key: str, default: Any = None) -> Any: pass
    def get_layer_dir(self, layer_key: str) -> Optional[str]: pass
    def get_build_rule(self, rule_key: str) -> Optional[Dict]: pass
    def get_config_data(self) -> Dict: pass
    def get_project_root(self) -> Optional[str]: pass
    # Add a method to get default config content for project creation
    def get_default_config_json(self) -> Dict:
         # Placeholder default config
         return {
             "project_name": "new_mccp_project",
             "project_version": "0.1.0",
             "target_language": "python",
             "layer_mapping": {
               "requirements_dir": ".", # requirements.md at root
               "behavior_code_dir": "src_mcbc",
               "pseudo_code_dir": "src_mcpc",
               "target_code_dir": "src_target", # Use src_target as default for code
               "symbol_table_root": "mccp_symbols",
               "config_dir": "config" # Added config dir mapping for consistency
             },
             "symbol_table_root": "mccp_symbols",
             "file_naming_convention": "snake_case",
             "build_rules": {}, # Empty rules initially
             "reverse_build_rules": {}, # Empty reverse rules initially
             "llm_settings": {
               "model": "your-preferred-llm-model",
               "api_url": "your-llm-api-endpoint",
               "api_key": "YOUR_API_KEY"
             }
         }

class JsonParser:
    """Placeholder for mccp_toolchain.mccp.parsers.JsonParser."""
    def parse(self, content: str) -> Dict: pass
    def generate(self, data: Dict) -> str: pass


# Now import the actual modules
try:
    from mccp_toolchain.mccp.config import ConfigManager # Import the real one after placeholder
    from mccp_toolchain.mccp.parsers import JsonParser # Assuming JsonParser is here
except ImportError as e:
    print(f"Error importing MCCP Toolchain modules in mccp/file_manager: {e}")
    # In a real app, handle gracefully. For code generation, assume imports are correct.


class FileManager:
    """
    文件管理器类，提供文件和目录操作的封装。
    负责处理项目目录结构、文件读写等文件系统操作。
    """

    def __init__(self, config_manager: ConfigManager):
        """
        初始化文件管理器。

        Args:
            config_manager: 配置管理器实例。
        """
        # Store config_manager. Due to circular dependency,
        # main.py might instantiate with None initially and set it later.
        self.config_manager: ConfigManager = config_manager

        # References to standard libraries
        self.os_module = os
        self.pathlib_module = pathlib

        self.log_info = print
        self.log_warning = print
        self.log_error = print


    def create_project_structure(self, project_path: str) -> bool:
        """
        根据 MCCP 规范和配置，创建标准的项目目录结构和初始文件（如 mccp_config.json）。

        Args:
            project_path: 新项目的根目录路径。

        Returns:
            bool: 如果结构创建成功返回 True，否则返回 False。
        """
        self.log_info(f"FileManager: Creating project structure at {project_path}")

        # Define standard directories (or get from config - but config needs to be created first)
        # Using hardcoded defaults and assuming config will load them later.
        # The default config data structure in ConfigManager placeholder is used.
        # A robust implementation would get these from a default config template.
        default_config_data = ConfigManager(None).get_default_config_json() # Use placeholder to get defaults
        layer_mapping = default_config_data.get("layer_mapping", {})
        # Exclude requirements_dir as it's often the root itself or a single file location
        # and config_dir which might not be mandatory to create initially if config is at root.
        directory_keys_to_create = [
            "behavior_code_dir", "pseudo_code_dir", "symbol_table_root", "target_code_dir"
        ]
        directory_names = [layer_mapping.get(key) for key in directory_keys_to_create if layer_mapping.get(key)]
        # Add config_dir if it's defined and not the root
        config_dir_name = layer_mapping.get("config_dir")
        if config_dir_name and config_dir_name != ".":
             directory_names.append(config_dir_name)

        success = True
        try:
            # Create root project directory
            self.os_module.makedirs(project_path, exist_ok=True)
            self.log_info(f"FileManager: Created root directory: {project_path}")

            # Create standard subdirectories
            for dir_name in directory_names:
                dir_path = self.os_module.path.join(project_path, dir_name)
                self.os_module.makedirs(dir_path, exist_ok=True)
                self.log_info(f"FileManager: Created subdirectory: {dir_path}")

            # Create initial mccp_config.json
            # Use the default config data from the ConfigManager placeholder
            config_file_name = "mccp_config.json" # Hardcoded standard name at root
            config_file_path = self.os_module.path.join(project_path, config_file_name)
            json_parser = JsonParser() # Assuming JsonParser is available
            default_config_content_json = json_parser.generate(default_config_data)

            if not self.write_file(config_file_path, default_config_content_json):
                self.log_error(f"FileManager: Failed to write initial config file: {config_file_path}")
                success = False

            # Create initial requirements.md
            # Assuming requirements.md goes into the requirements_dir, which defaults to "." (project root)
            req_dir_key = "requirements_dir"
            req_file_name = "requirements.md" # Standard name
            req_file_path = self.get_file_path(project_path, req_dir_key, req_file_name) # Use get_file_path

            # Define default requirements content
            default_requirements_content = (
                "# Project Requirements\n\n"
                "This is the initial requirements file for your MCCP project.\n"
                "Describe your project vision and core functionalities here in Markdown.\n\n"
                "## 1. Project Vision\n\n"
                "## 2. Core Function Requirements\n\n"
                "## 3. User Interface Requirements\n\n"
                "## 4. Non-Functional Requirements\n\n"
                "SR.Func.Example.1: Describe a core function here.\n"
                "SR.NonFunc.Example.1: Describe a non-functional aspect here.\n"
            )
            if not self.write_file(req_file_path, default_requirements_content):
                 self.log_error(f"FileManager: Failed to write initial requirements file: {req_file_path}")
                 success = False


            # Create initial symbols.json (minimal example)
            symbol_dir_key = "symbol_table_root"
            default_symbol_content_json = json_parser.generate({
                "module_name": "initial_symbols",
                "description": "Initial project symbols",
                "symbols": [
                    # Example symbol if needed
                    # {"name": "ExampleClass", "type": "class", "module_name": "initial_symbols", "is_frozen": False}
                ]
            })
            initial_symbol_file_name = "mccp_symbols_initial.json"
            initial_symbol_file_path = self.get_file_path(project_path, symbol_dir_key, initial_symbol_file_name)
            if not self.write_file(initial_symbol_file_path, default_symbol_content_json):
                 self.log_error(f"FileManager: Failed to write initial symbol file: {initial_symbol_file_path}")
                 success = False


        except Exception as e:
            self.log_error(f"FileManager: Error creating project structure: {e}")
            success = False

        return success

    def read_file(self, file_path: str) -> Optional[str]:
        """
        读取文件内容，返回字符串。文件不存在或读取失败返回 None。

        Args:
            file_path: 要读取的文件路径。

        Returns:
            str | None: 文件内容，如果读取失败则返回 None。
        """
        self.log_info(f"FileManager: Reading file: {file_path}")
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return content
        except FileNotFoundError:
            self.log_warning(f"FileManager: File not found: {file_path}")
            return None
        except Exception as e: # Catch other potential errors (permissions, encoding, etc.)
            self.log_error(f"FileManager: Failed to read file {file_path}: {e}")
            return None

    def write_file(self, file_path: str, content: str) -> bool:
        """
        将内容写入文件。如果父目录不存在则创建。写入成功返回 True，失败返回 False。

        Args:
            file_path: 要写入的文件路径。
            content: 要写入的文件内容。

        Returns:
            bool: 如果写入成功返回 True，否则返回 False。
        """
        self.log_info(f"FileManager: Writing to file: {file_path}")
        try:
            # Ensure parent directory exists
            parent_dir = self.os_module.path.dirname(file_path)
            if parent_dir: # Don't try to make dir if path is just a filename in current dir
                self.os_module.makedirs(parent_dir, exist_ok=True)

            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            self.log_info(f"FileManager: Successfully wrote to {file_path}")
            return True
        except Exception as e:
            self.log_error(f"FileManager: Failed to write file {file_path}: {e}")
            return False

    def get_file_path(self, project_path: str, layer_key: str, file_name: str) -> str:
        """
        根据配置的层级映射和文件名生成文件的完整路径。

        Args:
            project_path: 项目根目录。
            layer_key: 层级键 (e.g., 'behavior_code_dir', 'symbol_table_root').
            file_name: 文件名 (不含路径)。

        Returns:
            str: 生成的文件的完整路径。
        """
        # Ensure config_manager is set (handle circular dependency resolution)
        if self.config_manager is None:
             self.log_error("FileManager: ConfigManager not set. Cannot get file path.")
             return "" # Or raise error

        # Handle requirements_dir as a special case if it points to the root ('.')
        # This logic should be consistent with how layer_mapping is used.
        # get_layer_dir should return the directory name relative to project_path.
        layer_dir_name = self.config_manager.get_layer_dir(layer_key)

        if layer_dir_name is None:
            self.log_error(f"FileManager: Layer directory not found in config for key: {layer_key}")
            # Fallback or raise error
            # Fallback: Use layer_key itself as directory name? No, rely on config.
            return ""

        # Construct the full path
        full_path = self.os_module.path.join(project_path, layer_dir_name, file_name)
        # Normalize the path to handle '.' in requirements_dir etc.
        normalized_path = str(self.pathlib_module.Path(full_path).resolve())
        # print(f"FileManager: Generated path for key '{layer_key}', file '{file_name}': {normalized_path}") # Verbose logging
        return normalized_path


    def list_files_in_layer(self, project_path: str, layer_key: str, extension: str) -> List[str]:
        """
        列出指定层级目录下匹配扩展名的所有文件路径。

        Args:
            project_path: 项目根目录。
            layer_key: 层级键 (e.g., 'behavior_code_dir').
            extension: 文件扩展名 (e.g., '.mcbc', '.py').

        Returns:
            list[str]: 匹配文件的完整路径列表。
        """
        self.log_info(f"FileManager: Listing files in layer '{layer_key}' with extension '{extension}' for project {project_path}")

        # Get the full path to the layer directory
        # Use get_file_path with empty file_name to get the directory path
        # Note: this relies on get_file_path handling the trailing slash or pathlib joining correctly.
        # get_file_path(project_path, layer_key, "") should give the directory path.
        layer_dir_path = self.get_file_path(project_path, layer_key, "")
        # Need to handle the case where get_file_path returns "" due to config error
        if not layer_dir_path:
             self.log_error(f"FileManager: Could not determine directory path for layer key: {layer_key}")
             return []


        # Check if the directory exists
        if not self.os_module.path.isdir(layer_dir_path):
             self.log_warning(f"FileManager: Layer directory not found: {layer_dir_path}. Returning empty list.")
             return []

        # Use pathlib to list files with the specified extension
        path_object = self.pathlib_module.Path(layer_dir_path)
        file_paths: List[str] = []
        try:
            # Using glob() for pattern matching. /*.{extension} for recursive search if needed.
            # For now, assuming non-recursive list within the layer directory.
            glob_pattern = f'*{extension}'
            self.log_info(f"FileManager: Searching in {layer_dir_path} with pattern {glob_pattern}")
            for file_path_obj in path_object.glob(glob_pattern):
                 if file_path_obj.is_file():
                    file_paths.append(str(file_path_obj.resolve())) # Get absolute path

            self.log_info(f"FileManager: Found {len(file_paths)} files in {layer_dir_path}")
            return file_paths

        except Exception as e:
            self.log_error(f"FileManager: Error listing files in {layer_dir_path}: {e}")
            return []


def get_project_root_from_path(any_path_within_project: str) -> Optional[str]:
    """
    给定项目内的任意路径，向上查找 mccp_config.json 所在的目录作为项目根目录。
    这是一个独立的函数，不依赖 FileManager 实例。

    Args:
        any_path_within_project: 项目内的任意路径。

    Returns:
        str | None: 项目根目录路径，如果没有找到则返回 None。
    """
    print(f"FileManager: Searching for project root from: {any_path_within_project}")
    # Start with the given path, resolved to an absolute path
    current_path = os.path.abspath(any_path_within_project)

    # Loop upwards until root is reached or config file is found
    while True:
        config_file = os.path.join(current_path, "mccp_config.json")
        if os.path.exists(config_file):
            print(f"FileManager: Found project root: {current_path}")
            return current_path # Found the root

        # Move up one directory
        parent_path = os.path.dirname(current_path)

        # If parent_path is the same as current_path, we've reached the filesystem root
        if parent_path == current_path:
            print(f"FileManager: Reached filesystem root without finding mccp_config.json.")
            break # Reached the filesystem root

        current_path = parent_path

    # Config file not found in any parent directory
    print("FileManager: Could not find project root.")
    return None
```

```python
# -*- coding: utf-8 -*-

"""
MCCP Toolchain - Distributed Symbol Table Management Module

This module manages the project's distributed symbol tables, which store
structured definitions of code elements (classes, functions, variables, etc.)
and their metadata, including dependencies and frozen status.
"""

import os
import json
from typing import Dict, Any, Optional, List

# Import MCCP Toolchain Modules (Forward declarations for type hinting)
# import mccp_toolchain.mccp.file_manager
# import mccp_toolchain.mccp.config
# import mccp_toolchain.mccp.parsers # For JsonParser
# import mccp_toolchain.utils

# Define placeholders or mock classes for dependencies to satisfy type hints
class FileManager:
    """Placeholder for mccp_toolchain.mccp.file_manager.FileManager."""
    def __init__(self, config_manager: 'ConfigManager'): pass
    def create_project_structure(self, project_path: str) -> bool: pass
    def read_file(self, file_path: str) -> Optional[str]: pass
    def write_file(self, file_path: str, content: str) -> bool: pass
    def get_file_path(self, project_path: str, layer_key: str, file_name: str) -> str: pass
    def list_files_in_layer(self, project_path: str, layer_key: str, extension: str) -> List[str]: pass
    def get_project_root_from_path(self, any_path_within_project: str) -> Optional[str]: pass

class ConfigManager:
    """Placeholder for mccp_toolchain.mccp.config.ConfigManager."""
    def __init__(self, file_manager: FileManager): pass
    def load_config(self, project_path: str) -> bool: pass
    def get_setting(self, key: str, default: Any = None) -> Any: pass
    def get_layer_dir(self, layer_key: str) -> Optional[str]: pass
    def get_build_rule(self, rule_key: str) -> Optional[Dict]: pass
    def get_config_data(self) -> Dict: pass
    def get_project_root(self) -> Optional[str]: pass

class JsonParser:
    """Placeholder for mccp_toolchain.mccp.parsers.JsonParser."""
    def parse(self, content: str) -> Dict: pass
    def generate(self, data: Dict) -> str: pass

# Assuming utils module provides helper functions
def find_in_list_by_key(list_data: List[Dict], key_name: str, key_value: Any) -> Optional[Dict]:
    """Placeholder for mccp_toolchain.utils.find_in_list_by_key."""
    return None # Placeholder

def FIND_INDEX_OF_DICT_IN_LIST(list_data: List[Dict], key_name: str, key_value: Any) -> Optional[int]:
    """Placeholder for FIND_INDEX_OF_DICT_IN_LIST function."""
    return None # Placeholder


# Now import the actual modules
try:
    from mccp_toolchain.mccp.file_manager import FileManager
    from mccp_toolchain.mccp.config import ConfigManager
    from mccp_toolchain.mccp.parsers import JsonParser # Assuming JsonParser is here
    from mccp_toolchain.utils import find_in_list_by_key, FIND_INDEX_OF_DICT_IN_LIST # Assuming utils provides this
except ImportError as e:
    print(f"Error importing MCCP Toolchain modules in mccp/symbols: {e}")
    # In a real app, handle gracefully. For code generation, assume imports are correct.


class SymbolTableManager:
    """
    符号表管理器类，管理项目中的所有分布式符号表文件。
    负责加载、保存、查找和更新符号定义。
    """

    def __init__(self, file_manager: FileManager, config_manager: ConfigManager):
        """
        初始化符号表管理器，存储依赖。符号加载需调用 load_all_symbol_tables。

        Args:
            file_manager: 文件管理器实例。
            config_manager: 配置管理器实例。
        """
        self.file_manager: FileManager = file_manager
        self.config_manager: ConfigManager = config_manager
        self.json_parser: JsonParser = JsonParser() # Assuming JsonParser can be instantiated directly
        # Internal state: Dictionary mapping module_name to its symbol data (dict loaded from JSON)
        self._symbol_data_map: Dict[str, Dict] = {}

        self.log_info = print
        self.log_warning = print
        self.log_error = print


    def load_all_symbol_tables(self, project_path: str) -> None:
        """
        加载 mccp_symbols 目录下的所有 symbols.json 文件到内存。

        Args:
            project_path: 项目根目录。
        """
        self.log_info(f"SymbolTableManager: Loading all symbol tables for project: {project_path}")
        self._symbol_data_map = {} # Clear existing loaded data

        # Get the directory key for symbol tables from config
        symbol_dir_key = self.config_manager.get_setting("symbol_table_root", "mccp_symbols") # Default to 'mccp_symbols'
        symbol_file_extension = ".json" # Standard extension for symbols

        # List all symbol files in the designated directory
        symbol_file_paths = self.file_manager.list_files_in_layer(project_path, symbol_dir_key, symbol_file_extension)

        if not symbol_file_paths:
             self.log_warning(f"SymbolTableManager: No symbol files found in the '{symbol_dir_key}' directory.")

        for symbol_file_path in symbol_file_paths:
            self.log_info(f"SymbolTableManager: Reading symbol file: {symbol_file_path}")
            content = self.file_manager.read_file(symbol_file_path)
            if content is not None:
                try:
                    parsed_data = self.json_parser.parse(content)
                    if parsed_data and isinstance(parsed_data, dict) and "module_name" in parsed_data:
                        module_name = parsed_data["module_name"]
                        self._symbol_data_map[module_name] = parsed_data
                        self.log_info(f"SymbolTableManager: Loaded symbols for module: {module_name}")
                    else:
                        self.log_warning(f"SymbolTableManager: Failed to parse or found invalid format (missing 'module_name' or not a dict) in symbol file: {symbol_file_path}")
                except Exception as e: # Catch parsing errors
                     self.log_warning(f"SymbolTableManager: Failed to parse symbol file {symbol_file_path}: {e}")
            else:
                self.log_warning(f"SymbolTableManager: Could not read symbol file: {symbol_file_path}")

        self.log_info(f"SymbolTableManager: Finished loading {len(self._symbol_data_map)} symbol tables.")


    def save_all_symbol_tables(self) -> None:
        """
        将内存中的符号表数据保存回对应的 symbols.json 文件。
        """
        if not self._symbol_data_map:
             self.log_info("SymbolTableManager: No symbol data in memory to save.")
             return

        self.log_info("SymbolTableManager: Saving all symbol tables from memory.")

        # Get the directory key for symbol tables and the project root
        symbol_dir_key = self.config_manager.get_setting("symbol_table_root", "mccp_symbols")
        project_root = self.config_manager.get_project_root()

        if project_root is None:
             self.log_error("SymbolTableManager: Cannot save symbols: Project root not set in ConfigManager.")
             return

        for module_name, symbols_data in self._symbol_data_map.items():
             # Determine the expected file name for this module
             # Example: mccp_symbols/mccp_toolchain_ui.json
             file_name = self.derive_symbol_file_name(module_name)
             file_path = self.file_manager.get_file_path(project_root, symbol_dir_key, file_name)

             try:
                 json_content = self.json_parser.generate(symbols_data)
                 success = self.file_manager.write_file(file_path, json_content)
                 if success:
                    self.log_info(f"SymbolTableManager: Saved symbols for module {module_name} to {file_path}")
                 else:
                    self.log_error(f"SymbolTableManager: Failed to save symbols for module {module_name} to {file_path}")
             except Exception as e: # Catch JSON generation or file writing errors
                  self.log_error(f"SymbolTableManager: Error saving symbols for module {module_name} to {file_path}: {e}")


    def find_symbol(self, symbol_name: str, module_name: Optional[str] = None) -> Optional[Dict]:
        """
        在所有加载的符号表中查找指定符号。

        Args:
            symbol_name: 要查找的符号名。
            module_name: 可选：限定查找的模块名。

        Returns:
            dict | None: 找到的符号数据字典，如果没有找到则返回 None。
        """
        # self.log_info(f"SymbolTableManager: Searching for symbol '{symbol_name}' in module '{module_name or 'any'}'") # Too verbose

        if module_name is not None:
            # Check only the specified module's symbols
            module_symbols_data = self._symbol_data_map.get(module_name)
            if module_symbols_data and "symbols" in module_symbols_data and isinstance(module_symbols_data["symbols"], list):
               # Use the utility function to find the dictionary in the list
               return find_in_list_by_key(module_symbols_data["symbols"], "name", symbol_name)
            else:
               # self.log_info(f"SymbolTableManager: Module '{module_name}' not found or has no 'symbols' list.") # Too verbose
               return None # Module not found or has no symbols list
        else:
            # Search across all loaded modules
            for mod_name, mod_symbols_data in self._symbol_data_map.items():
               if "symbols" in mod_symbols_data and isinstance(mod_symbols_data["symbols"], list):
                    symbol = find_in_list_by_key(mod_symbols_data["symbols"], "name", symbol_name)
                    if symbol is not None:
                       # self.log_info(f"SymbolTableManager: Found symbol '{symbol_name}' in module '{mod_name}'.") # Too verbose
                       return symbol
            # self.log_info(f"SymbolTableManager: Symbol '{symbol_name}' not found in any loaded module.") # Too verbose
            return None # Symbol not found in any module


    def update_symbol(self, symbol_data: Dict) -> bool:
        """
        更新或添加一个符号到对应的模块符号表。
        如果符号已存在且 is_frozen 为 true，则拒绝更新。

        Args:
            symbol_data: 要更新或添加的符号数据字典 (必须包含 'name' 和 'module_name' 键)。

        Returns:
            bool: 如果更新成功 (包括添加新符号) 返回 True，如果更新被 frozen 标记拒绝则返回 False。
        """
        module_name = symbol_data.get("module_name")
        symbol_name = symbol_data.get("name")

        if not module_name or not symbol_name:
           self.log_error(f"SymbolTableManager: Invalid symbol data for update: Missing 'name' or 'module_name'. Data: {symbol_data}")
           return False

        # Ensure the module entry exists in the internal map
        if module_name not in self._symbol_data_map:
             self.log_info(f"SymbolTableManager: Creating new entry for module '{module_name}' in symbol map.")
             # Initialize with standard structure
             self._symbol_data_map[module_name] = {
                 "module_name": module_name,
                 "description": f"Symbols for module {module_name}.", # Default description
                 "symbols": []
             }
        # Ensure the 'symbols' list exists
        if "symbols" not in self._symbol_data_map[module_name] or not isinstance(self._symbol_data_map[module_name]["symbols"], list):
             self.log_warning(f"SymbolTableManager: 'symbols' key missing or not a list in module '{module_name}', initializing.")
             self._symbol_data_map[module_name]["symbols"] = []


        module_symbols_list = self._symbol_data_map[module_name]["symbols"]

        # Find if the symbol already exists using the utility function
        existing_symbol_index = FIND_INDEX_OF_DICT_IN_LIST(module_symbols_list, "name", symbol_name)

        if existing_symbol_index is not None:
             # Symbol exists, check if it's frozen
             existing_symbol = module_symbols_list[existing_symbol_index]
             if existing_symbol.get("is_frozen", False):
                self.log_warning(f"SymbolTableManager: Attempted to update frozen symbol: '{symbol_name}' in module '{module_name}'. Update rejected.")
                return False # Refuse update

             # Symbol exists and is not frozen, update it (merge data)
             # Simple merge: update existing keys with new data, new keys are added.
             # Keep the existing 'is_frozen' value if not provided in new data.
             is_frozen_status = existing_symbol.get('is_frozen', False) # Preserve existing frozen status
             module_symbols_list[existing_symbol_index].update(symbol_data)
             module_symbols_list[existing_symbol_index]['is_frozen'] = symbol_data.get('is_frozen', is_frozen_status) # Allow new data to set frozen, but default to existing

             self.log_info(f"SymbolTableManager: Updated symbol: '{symbol_name}' in module '{module_name}'.")

        else:
            # Symbol does not exist, add it
            # Ensure basic structure and default 'is_frozen' if not provided
            symbol_data['module_name'] = module_name # Ensure module_name is correct in the symbol data itself
            if 'is_frozen' not in symbol_data:
                 symbol_data['is_frozen'] = False # Default to not frozen
            module_symbols_list.append(symbol_data)
            self.log_info(f"SymbolTableManager: Added new symbol: '{symbol_name}' to module '{module_name}'.")

        # The list 'module_symbols_list' is a reference to the list inside _symbol_data_map,
        # so changes are reflected directly. No need to re-assign.

        return True # Update/add successful


    def get_module_symbols(self, module_name: str) -> Dict[str, Any]:
        """
        获取指定模块的符号表数据。

        Args:
            module_name: 模块名。

        Returns:
            dict: 指定模块的符号表数据字典。如果模块不存在，返回一个空的字典结构。
        """
        # Return the data for the specified module, or an empty structure if not found
        # Ensure the returned structure includes the 'symbols' list key for consistency
        return self._symbol_data_map.get(module_name, {"module_name": module_name, "description": f"Symbols for {module_name} (not loaded/found).", "symbols": []})

    def get_all_symbols(self) -> Dict[str, Dict]:
        """
        获取所有加载模块的符号表数据。

        Returns:
            dict: 包含所有模块符号表数据的字典。
        """
        # Return a copy of the internal map to prevent external modification
        return self._symbol_data_map.copy()


    def derive_symbol_file_name(self, module_name: str) -> str:
       """
       根据模块名生成对应的 symbols.json 文件名。
       格式: mccp_symbols_<module_name_snake_case>.json

       Args:
           module_name: 模块名 (e.g., 'mccp_toolchain.ui').

       Returns:
           str: 生成的 symbols.json 文件名 (e.g., 'mccp_symbols_mccp_toolchain_ui.json').
       """
       # Replace dots with underscores, prepend "mccp_symbols_", append ".json"
       # Use snake_case conversion if module_name might not be in perfect snake_case?
       # Assuming module_name from the symbol table is the canonical name.
       # Let's just replace dots with underscores.
       filename_base = module_name.replace(".", "_")
       return f"mccp_symbols_{filename_base}.json"


# Helper function implementation (matching the placeholder)
# Note: This was defined as a FUNCTION in MCPC, so it should be a standalone function,
# not a method of SymbolTableManager. It was also listed in utils.mcpc, which is a better place.
# Let's put the implementation in utils.py and import it.
# The placeholder here is kept for compatibility with the initial description, but the real
# implementation should be in utils.py.

# def FIND_INDEX_OF_DICT_IN_LIST(list_data: List[Dict], key_name: str, key_value: Any) -> Optional[int]:
#    """
#    在字典列表中按键值查找字典的索引。
#    """
#    for index, item in enumerate(list_data):
#       if isinstance(item, dict) and item.get(key_name) == key_value:
#          return index
#    return None

```

```python
# -*- coding: utf-8 -*-

"""
MCCP Toolchain - MCCP Configuration Module

This module manages the project's configuration data loaded from mccp_config.json.
It provides centralized access to settings that control the toolchain's behavior,
such as layer mappings, build rules, and LLM settings.
"""

import os
import json
from typing import Dict, Any, Optional, List

# Import MCCP Toolchain Modules (Forward declarations for type hinting)
# import mccp_toolchain.mccp.file_manager
# import mccp_toolchain.mccp.parsers # For JsonParser

# Define placeholders or mock classes for dependencies to satisfy type hints
class FileManager:
    """Placeholder for mccp_toolchain.mccp.file_manager.FileManager."""
    # Need __init__ to accept ConfigManager for circular dependency workaround in main.py
    def __init__(self, config_manager: Optional['ConfigManager'] = None):
         self.config_manager = config_manager # Store reference if passed
    def create_project_structure(self, project_path: str) -> bool: pass
    def read_file(self, file_path: str) -> Optional[str]: pass
    def write_file(self, file_path: str, content: str) -> bool: pass
    def get_file_path(self, project_path: str, layer_key: str, file_name: str) -> str: pass
    def list_files_in_layer(self, project_path: str, layer_key: str, extension: str) -> List[str]: pass
    def get_project_root_from_path(self, any_path_within_project: str) -> Optional[str]: pass


class JsonParser:
    """Placeholder for mccp_toolchain.mccp.parsers.JsonParser."""
    def parse(self, content: str) -> Dict: pass
    def generate(self, data: Dict) -> str: pass


# Now import the actual modules
try:
    from mccp_toolchain.mccp.file_manager import FileManager # Import the real one after placeholder
    from mccp_toolchain.mccp.parsers import JsonParser # Assuming JsonParser is here
except ImportError as e:
    print(f"Error importing MCCP Toolchain modules in mccp/config: {e}")
    # In a real app, handle gracefully. For code generation, assume imports are correct.


class ConfigManager:
    """
    配置管理器类，加载并提供 mccp_config.json 的配置数据。
    负责加载、解析和提供项目配置。
    """

    def __init__(self, file_manager: FileManager):
        """
        初始化配置管理器。

        Args:
            file_manager: 文件管理器实例。
        """
        # Store file_manager. Due to circular dependency,
        # main.py might instantiate with None initially and set it later.
        self.file_manager: FileManager = file_manager
        self.json_parser: JsonParser = JsonParser() # Assuming JsonParser can be instantiated directly
        # Internal state to hold loaded config and project root
        self._config_data: Dict[str, Any] = {}
        self._project_root: Optional[str] = None

        self.log_info = print
        self.log_warning = print
        self.log_error = print

    def load_config(self, project_path: str) -> bool:
        """
        从项目目录加载 mccp_config.json 文件并解析。

        Args:
            project_path: 项目根目录。

        Returns:
            bool: 如果配置加载成功返回 True，否则返回 False。
        """
        self.log_info(f"ConfigManager: Loading config from project root: {project_path}")
        self._project_root = project_path # Store the project root

        # Construct the full path to the config file (assuming it's at the project root)
        config_file_name = "mccp_config.json"
        config_file_path = os.path.join(project_path, config_file_name)

        # Ensure file_manager is set (handle circular dependency resolution)
        if self.file_manager is None:
             self.log_error("ConfigManager: FileManager not set. Cannot load config.")
             self._config_data = {}
             return False

        # Read file content using FileManager
        content = self.file_manager.read_file(config_file_path)
        if content is None:
            self.log_error(f"ConfigManager: Failed to read config file: {config_file_path}")
            self._config_data = {} # Reset config on failure
            return False

        # Parse JSON content using JsonParser
        try:
            parsed_data = self.json_parser.parse(content)
            if parsed_data and isinstance(parsed_data, dict):
                self._config_data = parsed_data
                self.log_info(f"ConfigManager: Config loaded successfully from {config_file_path}.")
                return True
            else:
                 self.log_error(f"ConfigManager: Config file {config_file_path} is not a valid JSON object or is empty.")
                 self._config_data = {} # Reset config
                 return False
        except Exception as e: # Catch parsing errors from JsonParser
            self.log_error(f"ConfigManager: Failed to parse JSON config file {config_file_path}: {e}")
            self._config_data = {} # Reset config on parsing failure
            return False


    def get_setting(self, key: str, default: Any = None) -> Any:
        """
        根据键路径获取配置值。支持嵌套路径访问。
        例如: "llm_settings.model"

        Args:
            key: 配置项的键路径 (点分隔)。
            default: 如果键不存在时返回的默认值。

        Returns:
            any: 配置值，或默认值。
        """
        # Walk through the dictionary using dot-separated key parts.
        parts = key.split(".")
        current_value = self._config_data

        try:
            for part in parts:
                if isinstance(current_value, dict) and part in current_value:
                    current_value = current_value[part]
                else:
                    # Key path not found
                    # self.log_warning(f"ConfigManager: Config setting not found for key path: {key}. Returning default.") # Too verbose
                    return default
            # Reached the end of the key path, return the value
            return current_value
        except Exception as e:
            # Handle potential errors during access (e.g., trying to access a key on a non-dict)
            self.log_error(f"ConfigManager: Error accessing config key path '{key}': {e}. Returning default.")
            return default

    def get_layer_dir(self, layer_key: str) -> Optional[str]:
        """
        获取指定层级对应的目录名。

        Args:
            layer_key: 层级键 (e.g., 'behavior_code_dir', 'symbol_table_root').

        Returns:
            str | None: 指定层级对应的目录名 (相对于项目根目录)，如果没有找到则返回 None。
        """
        # Get from 'layer_mapping' section using get_setting
        return self.get_setting(f"layer_mapping.{layer_key}", None)

    def get_build_rule(self, rule_key: str) -> Optional[Dict]:
        """
        获取指定构建规则的详细配置 (input_extension, output_extension, llm_prompt等)。
        检查 'build_rules' 和 'reverse_build_rules' 两个部分。

        Args:
            rule_key: 构建规则键 (e.g., 'mcbc_to_mcpc', 'py_to_mcpc').

        Returns:
            dict | None: 指定构建规则的配置字典，如果没有找到则返回 None。
        """
        # Check in 'build_rules' first
        build_rules = self.get_setting("build_rules", {})
        if rule_key in build_rules:
             return build_rules[rule_key]

        # Check in 'reverse_build_rules'
        reverse_rules = self.get_setting("reverse_build_rules", {})
        if rule_key in reverse_rules:
             return reverse_rules[rule_key]

        # Rule not found in either section
        self.log_warning(f"ConfigManager: Build rule not found for key: {rule_key}")
        return None

    def get_config_data(self) -> Dict[str, Any]:
       """
       获取完整的配置数据字典。

       Returns:
           dict: 当前加载的配置数据字典。
       """
       # Return a copy of the internal config data to prevent external modification
       return self._config_data.copy()

    def get_project_root(self) -> Optional[str]:
        """
        获取当前加载的项目根目录路径。

        Returns:
            str | None: 项目根目录路径，如果没有项目加载则返回 None。
        """
        return self._project_root

    def get_default_config_json(self) -> Dict[str, Any]:
         """
         提供一个默认的配置字典结构，用于创建新项目时的初始 mccp_config.json 文件。
         这个方法是为了解决 FileManager 创建项目时需要默认配置的问题。
         在实际应用中，这可能从一个独立的模板文件加载。

         Returns:
              Dict[str, Any]: 默认配置字典。
         """
         # This implementation was moved to the placeholder class definition
         # in file_manager.py to break the import cycle here.
         # Calling the placeholder's method directly is one way, or define defaults locally.
         # Let's define defaults locally to avoid relying on the placeholder.
         return {
             "project_name": "new_mccp_project",
             "project_version": "0.1.0",
             "target_language": "python",
             "layer_mapping": {
               "requirements_dir": ".", # requirements.md at root
               "behavior_code_dir": "src_mcbc",
               "pseudo_code_dir": "src_mcpc",
               "target_code_dir": "src_target", # Use src_target as default for code
               "symbol_table_root": "mccp_symbols",
               "config_dir": "config" # Added config dir mapping for consistency
             },
             "symbol_table_root": "mccp_symbols",
             "file_naming_convention": "snake_case",
             "build_rules": {
                  # Example default rules (minimal)
                 "md_to_mcbc": {
                      "input_layer_dir_key": "requirements_dir",
                      "output_layer_dir_key": "behavior_code_dir",
                      "input_extension": ".md",
                      "output_extension": ".mcbc",
                      "source_parser": "RequirementsParser",
                      "target_parser": "McbcParser",
                      "llm_prompt": "Default md_to_mcbc prompt template..."
                 },
                 "mcbc_to_mcpc": {
                      "input_layer_dir_key": "behavior_code_dir",
                      "output_layer_dir_key": "pseudo_code_dir",
                      "input_extension": ".mcbc",
                      "output_extension": ".mcpc",
                      "source_parser": "McbcParser",
                      "target_parser": "McpcParser",
                      "llm_prompt": "Default mcbc_to_mcpc prompt template..."
                 },
                  "mcpc_to_py": {
                      "input_layer_dir_key": "pseudo_code_dir",
                      "output_layer_dir_key": "target_code_dir",
                      "input_extension": ".mcpc",
                      "output_extension": ".py",
                      "source_parser": "McpcParser",
                      "target_parser": "TargetCodeParser",
                      "llm_prompt": "Default mcpc_to_py prompt template..."
                 }
             },
             "reverse_build_rules": {
                  # Default reverse rules (placeholders)
                 "py_to_mcpc": {
                     "input_layer_dir_key": "target_code_dir",
                     "output_layer_dir_key": "pseudo_code_dir",
                     "input_extension": ".py",
                     "output_extension": ".mcpc",
                     "source_parser": "TargetCodeParser",
                     "target_parser": "McpcParser",
                     "llm_prompt": "Default py_to_mcpc prompt template..."
                 },
                 "mcpc_to_mcbc": {
                     "input_layer_dir_key": "pseudo_code_dir",
                     "output_layer_dir_key": "behavior_code_dir",
                     "input_extension": ".mcpc",
                     "output_extension": ".mcbc",
                     "source_parser": "McpcParser",
                     "target_parser": "McbcParser",
                     "llm_prompt": "Default mcpc_to_mcbc prompt template..."
                 },
                 "mcbc_to_md": {
                     "input_layer_dir_key": "behavior_code_dir",
                     "output_layer_dir_key": "requirements_dir",
                     "input_extension": ".mcbc",
                     "output_extension": ".md",
                     "source_parser": "McbcParser",
                     "target_parser": "RequirementsParser",
                     "llm_prompt": "Default mcbc_to_md prompt template..."
                 }
             },
             "llm_settings": {
               "model": "gpt-4o-mini", # Example default model
               "api_url": "https://api.openai.com/v1", # Example default API URL
               "api_key": "YOUR_API_KEY" # Placeholder API Key
             }
         }

```

```python
# -*- coding: utf-8 -*-

"""
MCCP Toolchain - General Utilities Module

This module provides a collection of general-purpose helper functions
used across different parts of the MCCP toolchain.
"""

import os
import pathlib
import re
from typing import Any, Optional, List, Dict

class Utilities:
    """Placeholder for static methods."""
    pass

def normalize_path(path: str) -> str:
    """
    规范化文件路径，处理斜杠、相对路径等。

    Args:
        path: 待规范化的路径字符串。

    Returns:
        str: 规范化后的文件路径字符串。
    """
    # Use pathlib for robust path handling
    # Resolve() makes the path absolute and resolves symlinks and '..' components.
    # Using os.path.abspath is another option for just absolute path.
    # pathlib is generally more modern and robust.
    try:
        path_obj = pathlib.Path(path)
        normalized_path_obj = path_obj.resolve() # Resolves symlinks, .. components, makes absolute
        return str(normalized_path_obj)
    except Exception as e:
        print(f"Utils: Error normalizing path '{path}': {e}")
        # Return original path or handle error
        return path # Return original on error


def validate_file_name(file_name: str) -> bool:
    """
    验证文件名是否符合命名规范 (snake_case)。

    Args:
        file_name: 待验证的文件名字符串。

    Returns:
        bool: 如果文件名符合规范返回 True，否则返回 False。
    """
    # Use regular expression to check for snake_case pattern
    # Pattern explanation:
    # ^           - Start of string
    # [a-z0-9_]+  - One or more lowercase letters, numbers, or underscores (for the base name)
    # \.          - A literal dot (for the extension separator)
    # [a-z]+      - One or more lowercase letters (for the extension)
    # $           - End of string
    # This is a strict snake_case for the base name, followed by a dot and lowercase extension.
    pattern = r"^[a-z0-9_]+\.[a-z]+$"
    # Use re.fullmatch to ensure the entire string matches the pattern
    if re.fullmatch(pattern, file_name):
      return True
    else:
        # Optional: Log warning if validation fails
        # print(f"Utils: File name '{file_name}' does not match snake_case pattern.")
        return False

def snake_to_pascal_case(text: str) -> str:
    """
    将 snake_case 字符串转换为 PascalCase。

    Args:
        text: snake_case 字符串。

    Returns:
        str: PascalCase 字符串。
    """
    # Split the text by underscore, capitalize the first letter of each part, and join.
    parts = text.split("_")
    pascal_parts = [part.capitalize() for part in parts if part] # Ensure part is not empty
    return "".join(pascal_parts)

def pascal_to_snake_case(text: str) -> str:
    """
    将 PascalCase 字符串转换为 snake_case。

    Args:
        text: PascalCase 字符串。

    Returns:
        str: snake_case 字符串。
    """
    # Use regex to insert underscore before uppercase letters (except the first) and convert to lowercase.
    # s1: Find sequence of a non-uppercase char followed by an uppercase char (or an uppercase followed by lowercase) and insert underscore.
    # s2: Convert the result to lowercase.
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', text)
    s2 = re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()
    return s2

def find_in_list_by_key(list_data: List[Dict], key_name: str, key_value: Any) -> Optional[Dict]:
   """
   在字典列表中按键值查找第一个匹配的字典。

   Args:
       list_data: 待查找的字典列表。
       key_name: 用于匹配的键名。
       key_value: 待匹配的键值。

   Returns:
       dict | None: 找到的第一个匹配字典，如果没有找到则返回 None。
   """
   if not isinstance(list_data, list):
        # print(f"Utils: find_in_list_by_key requires a list, got {type(list_data)}") # Verbose
        return None

   for item in list_data:
      if isinstance(item, dict) and item.get(key_name) == key_value:
         return item
   return None

def FIND_INDEX_OF_DICT_IN_LIST(list_data: List[Dict], key_name: str, key_value: Any) -> Optional[int]:
   """
   在字典列表中按键值查找第一个匹配字典的索引。

   Args:
       list_data: 待查找的字典列表。
       key_name: 用于匹配的键名。
       key_value: 待匹配的键值。

   Returns:
       int | None: 找到的第一个匹配字典的索引，如果没有找到则返回 None。
   """
   if not isinstance(list_data, list):
        # print(f"Utils: FIND_INDEX_OF_DICT_IN_LIST requires a list, got {type(list_data)}") # Verbose
        return None

   for index, item in enumerate(list_data):
      if isinstance(item, dict) and item.get(key_name) == key_value:
         return index
   return None
```

```python
# -*- coding: utf-8 -*-

"""
MCCP Toolchain - Main Application Entry Point

This file is the main entry point for the MCCP Toolchain GUI application.
It initializes the core components and starts the PyQt event loop.
"""

import sys

# Import necessary PyQt components
from PyQt5.QtWidgets import QApplication, QMainWindow # Keep QMainWindow for type hint

# Import core modules
from mccp_toolchain.mccp.config import ConfigManager
from mccp_toolchain.mccp.file_manager import FileManager, get_project_root_from_path # get_project_root_from_path is a standalone function
from mccp_toolchain.mccp.symbols import SymbolTableManager
from mccp_toolchain.mccp.parsers import (
    JsonParser, RequirementsParser, McbcParser, McpcParser, TargetCodeParser
)
from mccp_toolchain.core.llm import LLMClient
from mccp_toolchain.core.build import BuildOrchestrator #, BUILD_LAYERS, BUILD_RULES # Constants might be needed

# Import the UI module's main window
from mccp_toolchain.ui import MainWindow

def main():
    """
    主函数，初始化应用并启动 GUI。
    """
    app = QApplication(sys.argv)

    # 1. Instantiate core dependencies
    # Handle circular dependency between ConfigManager and FileManager:
    # ConfigManager needs FileManager in __init__
    # FileManager needs ConfigManager in __init__
    # Create instances with None initially, then set the cross-references.
    # Alternatively, create one and pass it to the other's init, then set it back.
    # Let's create ConfigManager first, then FileManager passing ConfigManager,
    # and finally set FileManager on ConfigManager (requires public attribute or setter).
    # Based on MCPC/symbols, they expect it in __init__. So, let's instantiate with None first.

    # Instantiate parsers first, as they are simple and needed by others (JsonParser by Config/Symbols/File, others by Build)
    json_parser = JsonParser()
    requirements_parser = RequirementsParser()
    mcbc_parser = McbcParser()
    mcpc_parser = McpcParser()
    target_code_parser = TargetCodeParser()

    # Collect all specific parser instances in a dictionary for BuildOrchestrator
    parsers = {
        "JsonParser": json_parser,
        "RequirementsParser": requirements_parser,
        "McbcParser": mcbc_parser,
        "McpcParser": mcpc_parser,
        "TargetCodeParser": target_code_parser,
        # Add other parsers here if they are created
    }


    # Instantiate ConfigManager and FileManager with temporary None for circular dep
    # Note: This relies on the ConfigManager/FileManager classes being able to handle
    # a None dependency in their __init__ and having a way to set it later.
    # Based on the generated code, they store the reference but don't immediately use it in __init__.
    # However, using them later without the dependency being set will cause errors.
    # A robust pattern would be a factory or service locator.
    # For this generation, we'll instantiate and then immediately set the cross-reference.
    # This requires the attributes to be accessible (public or setters).
    # Assuming public attributes based on simple MCPC SET statements.

    # Instantiate ConfigManager (initially without FileManager)
    config_manager = ConfigManager(file_manager=None) # Pass None initially

    # Instantiate FileManager (pass the ConfigManager instance)
    file_manager = FileManager(config_manager=config_manager)

    # Now set the FileManager instance back on the ConfigManager instance
    # (This breaks the strict __init__-only dependency injection but resolves the cycle)
    # If attributes are public:
    config_manager.file_manager = file_manager
    # If setters were defined (not in MCPC, but better practice):
    # config_manager.set_file_manager(file_manager)


    # Instantiate other core managers/clients
    symbol_manager = SymbolTableManager(file_manager=file_manager, config_manager=config_manager)
    llm_client = LLMClient(config_manager=config_manager)

    # Instantiate Build Orchestrator, injecting all necessary services and parsers
    build_orchestrator = BuildOrchestrator(
        config_manager=config_manager,
        file_manager=file_manager,
        symbol_manager=symbol_manager,
        llm_client=llm_client,
        parsers=parsers # Pass the dictionary of parser instances
    )


    # 2. Instantiate the main UI window, injecting core services
    main_window = MainWindow(
        config_manager=config_manager,
        file_manager=file_manager,
        build_orchestrator=build_orchestrator,
        symbol_manager=symbol_manager
    )

    # 3. Show the main window
    main_window.show()

    # 4. Start the application event loop
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
```