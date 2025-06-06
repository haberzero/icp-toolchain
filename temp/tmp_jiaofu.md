# MCCP Toolchain 项目交付文档

本文档作为 `mccp-toolchain` 项目的交付清单与说明，旨在提供一个完整的项目文件集概览、结构、运行指南及所有文件的详细内容，以便于项目的部署、使用和后续维护。

## 1. 项目概述

`mccp-toolchain` 是一个基于 MCCP (Model Context Code Protocol) 理论的开源工具集，致力于通过结构化的层级转换和分布式符号管理，实现基于大型语言模型 (LLM) 的可控化、精确化软件开发。其核心目标是将人类的需求文档 (.md) 转换为结构化的行为描述代码 (.mcbc)，再通过符号表引导，逐步生成符号-伪代码 (.mcpc) 和最终的目标语言代码 (如 .py)。工具链提供图形用户界面 (GUI) 以简化操作，并封装了文件系统、配置管理、符号管理和 LLM 交互等核心功能。

核心功能包括：

*   正向构建: 从需求 (`.md`) 驱动生成行为代码 (`.mcbc`)、伪代码 (`.mcpc`) 直至目标代码 (`.py`)。
*   反向构建 (待实现): 从目标代码逆向提炼伪代码和行为描述。
*   LLM 集成: 使用 Langchain 框架与可配置的 LLM 交互，驱动各层级转换。
*   文件管理: 管理 MCCP 项目的标准目录结构、文件读写及配置、符号文件。
*   分布式符号管理: 维护跨模块的符号定义，支持冻结 (Frozen) 标记，确保 LLM 不随意修改关键代码结构。
*   图形用户界面 (GUI): 基于 PyQt 提供可视化操作界面，展示项目结构、触发构建流程和显示状态信息。

## 2. 自动化构建过程回顾

MCCP 工具链的核心在于其自动化、多层级的构建流程。整个过程从人类可读的需求文档出发，通过一系列由 LLM 辅助的转换步骤，最终生成可执行的代码。

1.  需求层 (`.md`): 工程师撰写详细的需求文档，通常为 Markdown 格式 (`requirements.md`)。
2.  行为描述层 (`.mcbc`): 工具链解析需求文档，并利用 LLM 将非结构化的需求转化为结构化的行为描述代码 (`src_mcbc/*.mcbc`)，定义模块、组件、类、方法及其职责和高层行为。
3.  符号-伪代码层 (`.mcpc`): 基于行为描述和项目分布式符号表 (`mccp_symbols_*.json`)，工具链通过 LLM 将行为进一步细化为符号化的伪代码 (`src_mcpc/*.mcpc`)，包含函数签名、数据结构和更具体的逻辑流程描述。
4.  符号表 (`.json`): 符号表在整个流程中作为核心上下文和约束，记录代码元素的符号定义、类型、依赖关系和 `is_frozen` 状态。在 `.mcbc` 到 `.mcpc` 和 `.mcpc` 到目标代码的转换中，LLM 必须参考并更新符号表（非冻结部分）。
5.  配置 (`mccp_config.json`): 配置文件定义了项目结构、层级映射、命名规范、构建规则 (包括 LLM 提示词模板) 和 LLM 连接设置，指导工具链的各项操作。
6.  目标代码层 (`.py` 等): 最后，工具链根据符号-伪代码和符号表，通过 LLM 生成符合目标语言规范 (`src_target/*`) 的高质量源代码。

这个流程确保了 LLM 在严格的结构和符号约束下工作，提高了代码生成的可控性和准确性。

## 3. 最终项目结构

根据 `dir_struct.json` 文件，项目的最终文件结构如下所示：

```tree
.
├── .gitignore
├── README.md
├── dir_struct.json
├── main.py
├── mccp_config.json
├── mccp_symbols
│   ├── mccp_symbols_mccp_toolchain_config.json
│   ├── mccp_symbols_mccp_toolchain_core_build.json
│   ├── mccp_symbols_mccp_toolchain_core_llm.json
│   ├── mccp_symbols_mccp_toolchain_mccp_file_manager.json
│   ├── mccp_symbols_mccp_toolchain_mccp_parsers.json
│   ├── mccp_symbols_mccp_toolchain_mccp_symbols.json
│   ├── mccp_symbols_mccp_toolchain_ui.json
│   └── mccp_symbols_mccp_toolchain_utils.json
├── mccp_toolchain
│   ├── __init__.py
│   ├── core
│   │   ├── __init__.py
│   │   ├── build.py
│   │   └── llm.py
│   ├── mccp
│   │   ├── __init__.py
│   │   ├── config.py
│   │   ├── file_manager.py
│   │   ├── parsers.py
│   │   └── symbols.py
│   ├── ui
│   │   ├── __init__.py
│   │   └── main_window.py
│   └── utils
│       ├── __init__.py
│       └── utils.py
├── requirements
│   └── requirements.md
├── requirements.txt
├── src_mcbc
│   ├── config.mcbc
│   ├── build.mcbc
│   ├── file_manager.mcbc
│   ├── llm.mcbc
│   ├── parsers.mcbc
│   ├── symbols.mcbc
│   ├── ui.mcbc
│   └── utils.mcbc
└── src_mcpc
    ├── config.mcpc
    ├── build.mcpc
    ├── file_manager.mcpc
    ├── llm.mcpc
    ├── parsers.mcpc
    ├── symbols.mcpc
    ├── ui.mcpc
    └── utils.mcpc
```

*Note: `requirements` directory will contain `requirements.md` upon project creation via the toolchain. `src_target` and `temp` directories are also part of the MCCP structure but are typically created during project initialization or build processes if they don't exist.*

## 4. 运行与测试指南

以下步骤指导用户如何运行 `mccp-toolchain` GUI 应用。

1.  环境准备: 确保系统中安装了 Python 3.8 或更高版本。
2.  安装依赖:
    导航到项目根目录，找到 `requirements.txt` 文件。使用 pip 安装所需的库：

    ```bash
    pip install -r requirements.txt
    ```

    `requirements.txt` 文件内容如下：
    ```
    PyQt5
    langchain
    langchain-openai
    ```
3.  启动程序:
    在项目根目录命令行中执行主程序文件 `main.py`：

    ```bash
    python main.py
    ```

    这将启动 `mccp-toolchain` 的 PyQt 图形用户界面。
4.  创建或打开项目:
    在 GUI 中，使用 "新建项目" 按钮创建一个新的 MCCP 项目结构，或使用 "打开项目" 按钮加载一个现有项目。新项目将在指定位置生成标准的 MCCP 目录结构和初始配置文件 (`mccp_config.json`, `requirements/requirements.md`, `mccp_symbols/mccp_symbols_initial.json`)。
5.  运行构建:
    打开项目后，编辑 `requirements/requirements.md` 或 `src_mcbc/*.mcbc` 文件。在 GUI 中选择目标层级，然后点击 "运行构建 (正向)" 按钮触发构建流程。状态栏将显示构建进度和结果。

## 5. 项目文件清单与完整内容

以下列出了项目中所有文件的相对路径及其完整内容。

文件: `/.gitignore`
```gitignore
__pycache__/
*.pyc
.env
.venv
venv/
.vscode/
*.log
*.tmp
temp/
mccp_toolchain/.pytest_cache/
mccp_toolchain/.mypy_cache/
mccp_toolchain/.ipynb_checkpoints/
dist/
build/
*.egg-info/
.DS_Store
.qt/
```

文件: `/README.md`
```markdown
# MCCP Toolchain

A toolchain implementing the Model Context Code Protocol (MCCP) for AI-assisted software development. This tool helps transform requirements into code through structured intermediate layers (.mcbc, .mcpc) guided by Large Language Models (LLMs) and managed by distributed symbol tables.

## Features

- GUI based on PyQt
- Forward build process (Requirements -> MCBC -> MCPC -> Target Code)
- Distributed Symbol Table Management
- Configurable LLM integration (via Langchain)
- Project structure management

## Getting Started

1.  Clone the repository:
    ```bash
    git clone <repository_url>
    cd mccp-toolchain
    ```
2.  Install dependencies:
    Ensure you have Python 3.8+ installed. Then install the required libraries:
    ```bash
    pip install -r requirements.txt
    ```
3.  Configure LLM:
    Edit `mccp_config.json` to set up your preferred LLM model, API URL, and API Key.
4.  Run the application:
    ```bash
    python main.py
    ```
5.  Create or Open a Project:
    Use the GUI buttons to create a new MCCP project or open an existing one.
6.  Start Building:
    Edit your requirements (`requirements/requirements.md`) or behavior code (`src_mcbc/*.mcbc`), select a target layer in the GUI, and click "Run Build".

## Project Structure

The project follows the structure defined in `dir_struct.json`, including directories for source code (`mccp_toolchain`), MCCP layer files (`src_mcbc`, `src_mcpc`, `requirements`), symbol tables (`mccp_symbols`), and configuration (`mccp_config.json`).

## Development

Follow the MCCP workflow to extend the toolchain itself, starting from requirements and behavior descriptions in the respective layers.
```

文件: `/dir_struct.json`
```json
{
    ".gitignore": null,
    "README.md": null,
    "main.py": null,
    "requirements": {},
    "src_mcbc": {},
    "src_mcpc": {},
    "mccp_symbols": {},
    "mccp_config": {},
    "mccp_toolchain": {
        "ui": {},
        "core": {
            "build": {},
            "llm": {}
        },
        "mccp": {
            "parsers": {},
            "symbols": {},
            "file_manager": {},
            "config": {}
        },
        "utils": {}
    },
    "tests": {
        "mccp_toolchain": {
            "ui": {},
            "core": {
                "build": {},
                "llm": {}
            },
            "mccp": {
                "parsers": {},
                "symbols": {},
                "file_manager": {},
                "config": {}
            },
            "utils": {}
        }
    },
    "temp": {}
}
```

文件: `/main.py`
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
# Using relative imports within the package
from mccp_toolchain.mccp.config import ConfigManager
from mccp_toolchain.mccp.file_manager import FileManager, get_project_root_from_path # get_project_root_from_path is a standalone function
from mccp_toolchain.mccp.symbols import SymbolTableManager
from mccp_toolchain.mccp.parsers import (
    JsonParser, RequirementsParser, McbcParser, McpcParser, TargetCodeParser
)
from mccp_toolchain.core.llm import LLMClient
from mccp_toolchain.core.build import BuildOrchestrator #, BUILD_LAYERS, BUILD_RULES # Constants might be needed

# Import the UI module's main window
from mccp_toolchain.ui.main_window import MainWindow

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

文件: `/mccp_config.json`
```json
{
  "project_name": "mccp-toolchain",
  "project_version": "0.1.0",
  "target_language": "python",
  "layer_mapping": {
    "requirements_dir": "requirements",
    "behavior_code_dir": "src_mcbc",
    "pseudo_code_dir": "src_mcpc",
    "target_code_dir": "mccp_toolchain"
  },
  "symbol_table_root": "mccp_symbols",
  "file_naming_convention": "snake_case",
  "build_rules": {
    "md_to_mcbc": {
      "input_layer_dir_key": "requirements_dir",
      "output_layer_dir_key": "behavior_code_dir",
      "input_extension": ".md",
      "output_extension": ".mcbc",
      "source_parser": "RequirementsParser",
      "target_parser": "McbcParser",
      "llm_prompt": "你是一个专业的软件需求分析师和结构化语言专家。你的任务是将用户提供的自然语言软件需求文档（Markdown格式）转换为MCCP行为描述代码（.mcbc格式）。从Markdown文档中提取核心功能、模块划分、每个模块或组件的职责、关键行为以及非功能性需求。将这些信息结构化地组织到.mcbc文件中。\n\n.mcbc文件应该清晰地描述系统的各个组成部分（模块、组件）以及它们的功能或行为。\n\n关注点：\n1.  模块/组件识别: 根据需求文档识别主要的功能区或技术组件（如UI、核心逻辑、解析器、符号管理器等）。\n2.  行为/功能描述: 为每个模块或组件提炼出具体的行为或功能点。描述应该清晰、简洁。\n3.  输入/输出（初步）: 如果需求文档中暗示了某个行为的输入或输出，请在描述中初步提及。\n4.  非功能性需求: 识别性能、安全性、代码规范、可维护性等非功能性需求，并在适当的部分或单独列出。\n5.  结构化: 按照.mcbc预期的结构进行组织。保持一致性。\n6.  命名: 遵循 snake_case 命名约定。\n\n提供源Markdown内容作为输入，输出结构化的.mcbc内容。"
    },
    "mcbc_to_mcpc": {
      "input_layer_dir_key": "behavior_code_dir",
      "output_layer_dir_key": "pseudo_code_dir",
      "input_extension": ".mcbc",
      "output_extension": ".mcpc",
      "source_parser": "McbcParser",
      "target_parser": "McpcParser",
      "llm_prompt": "你是一个高级软件设计师和符号逻辑专家。你的任务是将用户提供的MCCP行为描述代码（.mcbc格式）转换为MCCP符号-伪代码（.mcpc格式）。此过程需要严格参考并利用分布式符号表。\n\n从.mcbc文件中提取行为描述，并将其转化为更接近代码结构的伪代码。\n\n关键要求：\n1.  符号集成: 查阅提供的符号表（`mccp_symbols_*.json`）。如果某个行为、数据类型、变量或函数在符号表中已有定义（特别是已标记 `is_frozen: true` 的符号），必须优先使用其对应的符号名。如果需要新的符号，请在伪代码中明确表示其意图，以便后续工具更新符号表。\n2.  符号定义: 在伪代码中清晰地表达函数签名（使用符号名）、数据结构（使用符号名）和关键变量（使用符号名）。新的概念或结构应使用临时的、描述性的符号名，或在伪代码中明确标注需要新符号。\n3.  逻辑流程: 将行为描述转化为明确的伪代码步骤，包括条件判断、循环、函数调用、对象交互等。确保逻辑流程清晰、易于理解。\n4.  错误处理: 根据.mcbc中可能暗示的错误处理需求，在伪代码中设计基本的错误处理机制（如检查输入、处理异常情况）。\n5.  结构化: 按照.mcpc预期的结构进行组织，通常对应模块、类、函数等层级。保持与.mcbc模块结构的对应关系。\n6.  命名: 遵循 snake_case 命名约定，尤其是在定义新的符号或伪代码结构时。\n\n提供源.mcbc内容、相关的符号表内容（JSON格式）作为输入，输出结构化的.mcpc内容。"
    },
    "mcpc_to_py": {
      "input_layer_dir_key": "pseudo_code_dir",
      "output_layer_dir_key": "target_code_dir",
      "input_extension": ".mcpc",
      "output_extension": ".py",
      "source_parser": "McpcParser",
      "target_parser": "TargetCodeParser",
      "llm_prompt": "你是一个资深的Python软件工程师。你的任务是将用户提供的MCCP符号-伪代码（.mcpc格式）转换为高质量、符合规范的Python源代码。此过程需要严格参考分布式符号表，并且必须遵守Python的最佳实践和规范。\n\n关键要求：\n1.  代码翻译: 将.mcpc中的伪代码逻辑精确地翻译成功能性的Python代码。\n2.  符号使用: 正确使用符号表中定义的符号来命名函数、变量、类、常量等。确保符号与代码中的实现一致。\n3.  代码规范: 严格遵循PEP8规范。代码必须格式整洁、可读性强、符合Python习惯用法。\n4.  注释与文档: 为生成的Python代码添加详细、准确的Docstrings（针对模块、类、函数）和必要的行内注释，解释复杂的逻辑或关键的设计选择。Docstrings应遵循 reST 或 Google 风格。\n5.  模块化与可测试性: 按照.mcpc和符号表中体现的结构，将Python代码组织为独立的模块和类，以提高可维护性和可测试性。考虑单元测试的设计。\n6.  符号冻结: 绝对不能修改符号表中标记为 `is_frozen: true` 的符号对应的现有代码段。只生成或修改非冻结部分的代码，并确保与冻结代码的接口兼容。\n7.  文件结构: 根据.mcpc和mccp_config.json中的文件映射（`layer_mapping` -> `target_code_dir`）和命名约定（`file_naming_convention`，即 snake_case），确定生成的Python代码应放置的文件和文件名。\n\n提供源.mcpc内容、相关的符号表内容（JSON格式）以及mccp_config.json配置作为输入，输出Python源代码。"
    }
  },
  "reverse_build_rules": {
    "py_to_mcpc": {
      "input_layer_dir_key": "target_code_dir",
      "output_layer_dir_key": "pseudo_code_dir",
      "input_extension": ".py",
      "output_extension": ".mcpc",
      "source_parser": "TargetCodeParser",
      "target_parser": "McpcParser",
      "llm_prompt": "将Python源代码反向转换为MCCP符号-伪代码（.mcpc格式）。从Python代码结构中提取函数/方法、类、数据结构的定义、核心逻辑流程和关键变量。使用符号表示这些元素，并尝试匹配和更新符号表中的现有符号。关注代码功能而非具体实现细节。"
    },
    "mcpc_to_mcbc": {
      "input_layer_dir_key": "pseudo_code_dir",
      "output_layer_dir_key": "behavior_code_dir",
      "input_extension": ".mcpc",
      "output_extension": ".mcbc",
      "source_parser": "McpcParser",
      "target_parser": "McbcParser",
      "llm_prompt": "将MCCP符号-伪代码（.mcpc格式）反向转换为MCCP行为描述代码（.mcbc格式）。从伪代码结构和符号信息中提炼出更抽象的行为描述、模块职责和功能点。更新或创建对应的行为描述条目。忽略具体的实现细节，专注于'做什么'而不是'如何做'。"
    },
    "mcbc_to_md": {
      "input_layer_dir_key": "behavior_code_dir",
      "output_layer_dir_key": "requirements_dir",
      "input_extension": ".mcbc",
      "output_extension": ".md",
      "source_parser": "McbcParser",
      "target_parser": "RequirementsParser",
      "llm_prompt": "将MCCP行为描述代码（.mcbc格式）反向转换为自然语言描述（Markdown格式）。总结模块功能、关键行为和已实现的功能点，用于更新或生成需求文档摘要。确保描述清晰、准确地反映.mcbc中的内容。"
    }
  },
  "llm_settings": {
    "model": "your-preferred-llm-model",
    "api_url": "your-llm-api-endpoint",
    "api_key": "your-llm-api-key"
  }
}
```

文件: `/mccp_symbols/mccp_symbols_mccp_toolchain_config.json`
```json
{
  "module_name": "mccp_toolchain.mccp.config",
  "description": "MCCP 配置管理模块，负责加载、解析和提供项目配置。",
  "symbols": [
    {
      "name": "ConfigManager",
      "type": "class",
      "description": "配置管理器类，加载并提供 mccp_config.json 的配置数据。",
      "methods": [
        {
          "name": "__init__",
          "parameters": [
            {"name": "file_manager", "type": "mccp_toolchain.mccp.file_manager.FileManager", "description": "文件管理器实例"}
          ],
          "return_type": "None",
          "description": "初始化配置管理器。",
          "dependencies": ["mccp_toolchain.mccp.file_manager.FileManager", "mccp_toolchain.mccp.parsers.JsonParser"]
        },
        {
          "name": "load_config",
          "parameters": [
            {"name": "project_path", "type": "str", "description": "项目根目录"}
          ],
          "return_type": "bool",
          "description": "从项目目录加载 mccp_config.json 文件并解析。",
          "dependencies": ["mccp_toolchain.mccp.file_manager.FileManager.read_file", "mccp_toolchain.mccp.parsers.JsonParser.parse"]
        },
        {
          "name": "get_setting",
          "parameters": [
            {"name": "key", "type": "str", "description": "配置项的键路径 (e.g., 'llm_settings.model')"},
            {"name": "default", "type": "any", "description": "如果键不存在时返回的默认值"}
          ],
          "return_type": "any",
          "description": "根据键路径获取配置值。支持嵌套路径访问。",
          "dependencies": []
        },
         {
          "name": "get_layer_dir",
          "parameters": [
            {"name": "layer_key", "type": "str", "description": "层级键 (e.g., 'behavior_code_dir')"}
          ],
          "return_type": "str | None",
          "description": "获取指定层级对应的目录名。",
          "dependencies": ["mccp_toolchain.mccp.config.ConfigManager.get_setting"]
        },
        {
            "name": "get_build_rule",
            "parameters": [
                {"name": "rule_key", "type": "str", "description": "构建规则键 (e.g., 'mcbc_to_mcpc')"}
            ],
            "return_type": "dict | None",
            "description": "获取指定构建规则的详细配置 (input_extension, output_extension, llm_prompt等)。",
            "dependencies": ["mccp_toolchain.mccp.config.ConfigManager.get_setting"]
        },
        {
            "name": "get_config_data",
            "type": "method",
            "parameters": [],
            "return_type": "dict",
            "description": "获取完整的配置数据字典。",
            "dependencies": []
        },
        {
           "name": "get_project_root",
           "type": "method",
           "parameters": [],
           "return_type": "str | None",
           "description": "获取当前加载的项目根目录路径。",
           "dependencies": []
        }
      ]
    }
  ]
}
```

文件: `/mccp_symbols/mccp_symbols_mccp_toolchain_core_build.json`
```json
{
  "module_name": "mccp_toolchain.core.build",
  "description": "核心构建模块，负责协调正向和反向构建流程，驱动层级转换。",
  "symbols": [
    {
      "name": "BuildOrchestrator",
      "type": "class",
      "description": "构建流程协调器类，管理整个构建流程的步骤和依赖。",
      "methods": [
        {
          "name": "__init__",
          "parameters": [
            {"name": "config_manager", "type": "mccp_toolchain.mccp.config.ConfigManager", "description": "配置管理器实例"},
            {"name": "file_manager", "type": "mccp_toolchain.mccp.file_manager.FileManager", "description": "文件管理器实例"},
            {"name": "symbol_manager", "type": "mccp_toolchain.mccp.symbols.SymbolTableManager", "description": "符号表管理器实例"},
            {"name": "llm_client", "type": "mccp_toolchain.core.llm.LLMClient", "description": "LLM 客户端实例"},
            {"name": "parsers", "type": "dict", "description": "包含各种解析器实例的字典"}
          ],
          "return_type": "None",
          "description": "初始化构建协调器，注入所需的依赖服务。",
          "dependencies": [
            "mccp_toolchain.mccp.config.ConfigManager",
            "mccp_toolchain.mccp.file_manager.FileManager",
            "mccp_toolchain.mccp.symbols.SymbolTableManager",
            "mccp_toolchain.core.llm.LLMClient",
            "mccp_toolchain.mccp.parsers"
          ]
        },
        {
          "name": "run_forward_build",
          "parameters": [
            {"name": "project_path", "type": "str", "description": "项目根目录"},
            {"name": "start_layer_key", "type": "str", "description": "起始层级键 (e.g., 'behavior_code')"},
            {"name": "end_layer_key", "type": "str", "description": "结束层级键 ('mcpc', 'target_code')"}
          ],
          "return_type": "bool",
          "description": "执行从起始层级到结束层级的正向构建流程，协调各步骤，调用 LayerTransformer。",
          "dependencies": [
             "mccp_toolchain.mccp.symbols.SymbolTableManager.load_all_symbol_tables",
             "mccp_toolchain.mccp.symbols.SymbolTableManager.save_all_symbol_tables",
             "mccp_toolchain.mccp.config.ConfigManager.get_build_rule",
             "mccp_toolchain.mccp.file_manager.FileManager.list_files_in_layer",
             "mccp_toolchain.mccp.file_manager.FileManager.get_file_path",
             "mccp_toolchain.core.build.LayerTransformer",
             "mccp_toolchain.core.build.BuildOrchestrator.get_rule_key",
             "mccp_toolchain.core.build.BuildOrchestrator.derive_target_file_name"
          ]
        },
        {
          "name": "run_reverse_build",
          "parameters": [
            {"name": "project_path", "type": "str", "description": "项目根目录"},
            {"name": "start_layer", "type": "str", "description": "起始层级 ('code', 'mcpc', 'mcbc')"},
            {"name": "end_layer", "type": "str", "description": "结束层级 ('mcpc', 'mcbc', 'md')"}
          ],
          "return_type": "bool",
          "description": "执行从起始层级到结束层级的反向构建流程（待实现）。",
          "is_frozen": true,
           "dependencies": ["mccp_toolchain.core.build.LayerTransformer"]
        },
        {
           "name": "get_rule_key",
           "type": "method",
           "parameters": [
              {"name": "source_layer_key", "type": "str"},
              {"name": "target_layer_key", "type": "str"},
              {"name": "direction", "type": "str", "description": "'forward' or 'reverse'"}
           ],
           "return_type": "str | None",
           "description": "根据源层、目标层和方向查找匹配的构建规则键。",
           "dependencies": ["mccp_toolchain.mccp.config.ConfigManager.get_build_rule"]
        },
        {
           "name": "derive_target_file_name",
           "type": "method",
           "parameters": [
              {"name": "source_file_path", "type": "str"},
              {"name": "source_ext", "type": "str"},
              {"name": "target_ext", "type": "str"}
           ],
           "return_type": "str",
           "description": "根据源文件路径和扩展名，生成目标文件的文件名（替换扩展名）。",
           "dependencies": []
        }
      ]
    },
    {
      "name": "LayerTransformer",
      "type": "class",
      "description": "层级转换器类，负责执行具体的层级转换（如 .mcbc -> .mcpc），调用 LLM。",
      "methods": [
        {
          "name": "__init__",
          "parameters": [
            {"name": "config_manager", "type": "mccp_toolchain.mccp.config.ConfigManager"},
            {"name": "file_manager", "type": "mccp_toolchain.mccp.file_manager.FileManager"},
            {"name": "symbol_manager", "type": "mccp_toolchain.mccp.symbols.SymbolTableManager"},
            {"name": "llm_client", "type": "mccp_toolchain.core.llm.LLMClient"},
            {"name": "source_parser", "type": "object", "description": "源文件解析器实例"},
            {"name": "target_parser", "type": "object | None", "description": "目标文件解析器实例 (用于验证或结构化), 可选"}
          ],
          "return_type": "None",
          "description": "初始化层级转换器。",
          "dependencies": [
            "mccp_toolchain.mccp.config.ConfigManager",
            "mccp_toolchain.mccp.file_manager.FileManager",
            "mccp_toolchain.mccp.symbols.SymbolTableManager",
            "mccp_toolchain.core.llm.LLMClient",
            "mccp_toolchain.mccp.parsers"
          ]
        },
        {
          "name": "transform",
          "parameters": [
            {"name": "source_file_path", "type": "str"},
            {"name": "target_file_path", "type": "str"},
            {"name": "build_rule_key", "type": "str", "description": "mccp_config.json 中的构建规则键 (e.g., 'mcbc_to_mcpc')"}
          ],
          "return_type": "bool",
          "description": "执行从源文件到目标文件的转换，包括读取、生成LLM提示词、调用LLM、处理响应、更新符号表和写入文件。",
          "dependencies": [
             "mccp_toolchain.mccp.file_manager.FileManager.read_file",
             "mccp_toolchain.mccp.file_manager.FileManager.write_file",
             "mccp_toolchain.mccp.config.ConfigManager.get_build_rule",
             "mccp_toolchain.mccp.config.ConfigManager.get_config_data",
             "mccp_toolchain.mccp.symbols.SymbolTableManager.get_all_symbols",
             "mccp_toolchain.mccp.symbols.SymbolTableManager.update_symbol",
             "mccp_toolchain.core.llm.PromptGenerator",
             "mccp_toolchain.core.llm.LLMClient.generate_content",
             "mccp_toolchain.core.llm.LLMClient.parse_response"
          ]
        }
      ]
    },
    {
        "name": "BUILD_LAYERS",
        "type": "constant",
        "description": "定义构建流程的层级顺序键，与 mccp_config.json 中的 layer_mapping 相关。",
        "value": ["requirements", "behavior_code", "pseudo_code", "target_code"]
    },
    {
        "name": "BUILD_RULES",
        "type": "constant",
        "description": "定义构建规则的键，如 md_to_mcbc, mcbc_to_mcpc, mcpc_to_py，与 mccp_config.json 中的 build_rules 相关。",
        "value": ["md_to_mcbc", "mcbc_to_mcpc", "mcpc_to_py"]
    }
  ]
}
```

文件: `/mccp_symbols/mccp_symbols_mccp_toolchain_core_llm.json`
```json
{
  "module_name": "mccp_toolchain.core.llm",
  "description": "大语言模型集成模块，使用 Langchain 与 LLM 交互，生成和处理文本。",
  "symbols": [
    {
      "name": "LLMClient",
      "type": "class",
      "description": "LLM 客户端类，封装 Langchain 调用。",
      "methods": [
        {
          "name": "__init__",
          "parameters": [
            {"name": "config_manager", "type": "mccp_toolchain.mccp.config.ConfigManager", "description": "配置管理器实例"}
          ],
          "return_type": "None",
          "description": "初始化 LLM 客户端，读取配置并设置 Langchain 模型。",
          "dependencies": ["langchain.llms", "langchain_openai.ChatOpenAI", "os", "mccp_toolchain.mccp.config.ConfigManager.get_setting"]
        },
        {
          "name": "generate_content",
          "parameters": [
            {"name": "prompt", "type": "str", "description": "发送给 LLM 的提示词"},
            {"name": "context", "type": "dict", "description": "包含上下文信息的字典 (e.g., source_content, config, symbols)"}
          ],
          "return_type": "str",
          "description": "根据提示词和上下文调用 LLM 生成内容，返回原始文本响应。",
          "dependencies": ["langchain_core.prompts", "langchain_core.output_parsers"]
        },
         {
          "name": "parse_response",
          "parameters": [
            {"name": "response_text", "type": "str", "description": "LLM 返回的原始文本"},
            {"name": "target_format", "type": "str", "description": "期望的目标格式标识符 (e.g., 'mcbc', 'mcpc', 'python_code', 'json')"}
          ],
          "return_type": "object",
          "description": "解析 LLM 返回的文本，将其结构化或验证格式。可能委托给特定的解析器。",
          "dependencies": ["mccp_toolchain.mccp.parsers.JsonParser"]
        }
      ]
    },
    {
      "name": "PromptGenerator",
      "type": "class",
      "description": "提示词生成器类，根据源内容、目标格式、符号表和配置生成结构化的 LLM 提示词。",
      "methods": [
        {
          "name": "__init__",
          "parameters": [
             {"name": "config_manager", "type": "mccp_toolchain.mccp.config.ConfigManager", "description": "配置管理器实例"}
          ],
          "return_type": "None",
          "description": "初始化提示词生成器。",
          "dependencies": ["mccp_toolchain.mccp.config.ConfigManager"]
        },
        {
          "name": "generate_prompt",
          "parameters": [
            {"name": "build_rule_key", "type": "str", "description": "构建规则键 (e.g., 'mcbc_to_mcpc')"},
            {"name": "source_content", "type": "str", "description": "源文件内容"},
            {"name": "symbols", "type": "dict", "description": "相关的分布式符号表内容"},
            {"name": "config", "type": "dict", "description": "mccp_config.json 配置"}
          ],
          "return_type": "str",
          "description": "结合基础提示词模板、源内容、符号表和配置生成完整的提示词。",
           "dependencies": ["mccp_toolchain.mccp.config.ConfigManager.get_build_rule", "langchain_core.prompts", "json"]
        }
      ]
    }
  ]
}
```

文件: `/mccp_symbols/mccp_symbols_mccp_toolchain_mccp_file_manager.json`
```json
{
  "module_name": "mccp_toolchain.mccp.file_manager",
  "description": "文件管理模块，负责处理项目目录结构、文件读写等文件系统操作。",
  "symbols": [
    {
      "name": "FileManager",
      "type": "class",
      "description": "文件管理器类，提供文件和目录操作的封装。",
      "methods": [
        {
          "name": "__init__",
          "parameters": [
             {"name": "config_manager", "type": "mccp_toolchain.mccp.config.ConfigManager", "description": "配置管理器实例"}
          ],
          "return_type": "None",
          "description": "初始化文件管理器。",
          "dependencies": ["mccp_toolchain.mccp.config.ConfigManager", "os", "pathlib"]
        },
         {
          "name": "create_project_structure",
          "parameters": [
            {"name": "project_path", "type": "str", "description": "新项目的根目录路径"}
          ],
          "return_type": "bool",
          "description": "根据 MCCP 规范和配置，创建标准的项目目录结构和初始文件（如 mccp_config.json）。",
          "dependencies": ["mccp_toolchain.mccp.config.ConfigManager.get_default_config_json", "mccp_toolchain.mccp.parsers.JsonParser", "os", "mccp_toolchain.mccp.file_manager.FileManager.write_file", "mccp_toolchain.mccp.file_manager.FileManager.get_file_path"]
        },
        {
          "name": "read_file",
          "parameters": [
            {"name": "file_path", "type": "str", "description": "要读取的文件路径"}
          ],
          "return_type": "str | None",
          "description": "读取文件内容，返回字符串。文件不存在或读取失败返回 None。",
          "dependencies": ["os"]
        },
        {
          "name": "write_file",
          "parameters": [
            {"name": "file_path", "type": "str", "description": "要写入的文件路径"},
            {"name": "content", "type": "str", "description": "要写入的文件内容"}
          ],
          "return_type": "bool",
          "description": "将内容写入文件。如果父目录不存在则创建。写入成功返回 True，失败返回 False。",
          "dependencies": ["os"]
        },
         {
          "name": "get_file_path",
          "parameters": [
            {"name": "project_path", "type": "str", "description": "项目根目录"},
            {"name": "layer_key", "type": "str", "description": "层级键 (e.g., 'behavior_code_dir')"},
            {"name": "file_name", "type": "str", "description": "文件名 (不含路径)"}
          ],
          "return_type": "str",
          "description": "根据配置的层级映射和文件名生成文件的完整路径。",
          "dependencies": ["mccp_toolchain.mccp.config.ConfigManager.get_layer_dir", "pathlib", "os"]
        },
        {
          "name": "list_files_in_layer",
          "parameters": [
            {"name": "project_path", "type": "str", "description": "项目根目录"},
            {"name": "layer_key", "type": "str", "description": "层级键 (e.g., 'behavior_code_dir')"},
             {"name": "extension", "type": "str", "description": "文件扩展名"}
          ],
          "return_type": "list[str]",
          "description": "列出指定层级目录下匹配扩展名的所有文件路径。",
          "dependencies": ["mccp_toolchain.mccp.file_manager.FileManager.get_file_path", "pathlib", "os"]
        }
      ]
    },
    {
        "name": "get_project_root_from_path",
        "type": "function",
        "parameters": [
            {"name": "any_path_within_project", "type": "str"}
        ],
        "return_type": "str | None",
        "description": "给定项目内的任意路径，向上查找 mccp_config.json 所在的目录作为项目根目录。",
        "dependencies": ["os"]
    }
  ]
}
```

文件: `/mccp_symbols/mccp_symbols_mccp_toolchain_mccp_parsers.json`
```json
{
  "module_name": "mccp_toolchain.mccp.parsers",
  "description": "MCCP 文件解析器模块，负责读取、解析和验证不同格式的 MCCP 相关文件。",
  "symbols": [
    {
      "name": "RequirementsParser",
      "type": "class",
      "description": "解析 requirements.md 文件的类。",
      "methods": [
        {
          "name": "parse",
          "parameters": [
            {"name": "content", "type": "str", "description": "requirements.md 文件的文本内容"}
          ],
          "return_type": "dict",
          "description": "将 Markdown 格式的需求文本解析为结构化数据。"
        }
      ]
    },
    {
      "name": "McbcParser",
      "type": "class",
      "description": "解析 .mcbc (Behavior Code) 文件的类。",
      "methods": [
        {
          "name": "parse",
          "parameters": [
            {"name": "content", "type": "str", "description": ".mcbc 文件的文本内容"}
          ],
          "return_type": "dict",
          "description": "将 .mcbc 文本解析为结构化的行为描述对象。"
        },
        {
          "name": "generate",
          "parameters": [
             {"name": "data", "type": "dict", "description": "结构化的行为描述数据"}
          ],
          "return_type": "str",
          "description": "将结构化数据生成为 .mcbc 格式的文本。"
        }
      ]
    },
    {
      "name": "McpcParser",
      "type": "class",
      "description": "解析 .mcpc (Pseudo Code) 文件的类。",
      "methods": [
         {
          "name": "parse",
          "parameters": [
            {"name": "content", "type": "str", "description": ".mcpc 文件的文本内容"}
          ],
          "return_type": "dict",
          "description": "将 .mcpc 文本解析为结构化的符号-伪代码对象。"
        },
        {
          "name": "generate",
          "parameters": [
             {"name": "data", "type": "dict", "description": "结构化的符号-伪代码数据"}
          ],
          "return_type": "str",
          "description": "将结构化数据生成为 .mcpc 格式的文本。"
        }
      ]
    },
    {
      "name": "TargetCodeParser",
      "type": "class",
      "description": "解析目标语言源代码（如 Python .py 文件）的类。",
      "methods": [
        {
          "name": "parse",
          "parameters": [
            {"name": "content", "type": "str", "description": "源代码文件的文本内容"},
             {"name": "language", "type": "str", "description": "目标语言 (e.g., 'python')"}
          ],
          "return_type": "dict",
          "description": "将源代码解析为结构化数据（类、函数、变量等），用于反向构建。"
        },
         {
          "name": "generate",
          "parameters": [
             {"name": "data", "type": "dict", "description": "结构化的代码数据"},
             {"name": "language", "type": "str", "description": "目标语言 (e.g., 'python')"}
          ],
          "return_type": "str",
          "description": "将结构化数据生成为源代码格式的文本，遵循代码规范。"
        }
      ]
    },
     {
      "name": "JsonParser",
      "type": "class",
      "description": "解析 JSON 配置文件的通用类。",
      "methods": [
        {
          "name": "parse",
          "parameters": [
            {"name": "content", "type": "str", "description": "JSON 文件的文本内容"}
          ],
          "return_type": "dict",
          "description": "解析 JSON 文本为 Python 字典。",
          "dependencies": ["json"]
        },
        {
          "name": "generate",
          "parameters": [
            {"name": "data", "type": "dict", "description": "Python 字典数据"}
          ],
          "return_type": "str",
          "description": "将 Python 字典生成为格式化的 JSON 文本。",
          "dependencies": ["json"]
        }
      ]
    }
  ]
}
```

文件: `/mccp_symbols/mccp_symbols_mccp_toolchain_mccp_symbols.json`
```json
{
  "module_name": "mccp_toolchain.mccp.symbols",
  "description": "分布式符号表管理模块，负责加载、保存、查找和更新符号定义。",
  "symbols": [
    {
      "name": "SymbolTableManager",
      "type": "class",
      "description": "符号表管理器类，管理项目中的所有分布式符号表文件。",
      "methods": [
        {
          "name": "__init__",
          "parameters": [
            {"name": "file_manager", "type": "mccp_toolchain.mccp.file_manager.FileManager", "description": "文件管理器实例"},
            {"name": "config_manager", "type": "mccp_toolchain.mccp.config.ConfigManager", "description": "配置管理器实例"}
          ],
          "return_type": "None",
          "description": "初始化符号表管理器，存储依赖。符号加载需要调用 load_all_symbol_tables。",
          "dependencies": ["mccp_toolchain.mccp.file_manager.FileManager", "mccp_toolchain.mccp.config.ConfigManager", "mccp_toolchain.mccp.parsers.JsonParser"]
        },
         {
          "name": "load_all_symbol_tables",
          "parameters": [
            {"name": "project_path", "type": "str", "description": "项目根目录"}
          ],
          "return_type": "None",
          "description": "加载 mccp_symbols 目录下的所有 symbols.json 文件到内存。",
          "dependencies": ["mccp_toolchain.mccp.file_manager.FileManager.list_files_in_layer", "mccp_toolchain.mccp.file_manager.FileManager.read_file", "mccp_toolchain.mccp.config.ConfigManager.get_layer_dir", "mccp_toolchain.mccp.parsers.JsonParser.parse"]
        },
        {
          "name": "save_all_symbol_tables",
          "parameters": [],
          "return_type": "None",
          "description": "将内存中的符号表数据保存回对应的 symbols.json 文件。",
           "dependencies": ["mccp_toolchain.mccp.config.ConfigManager.get_layer_dir", "mccp_toolchain.mccp.config.ConfigManager.get_project_root", "mccp_toolchain.mccp.file_manager.FileManager.write_file", "mccp_toolchain.mccp.parsers.JsonParser.generate", "mccp_toolchain.mccp.symbols.SymbolTableManager.derive_symbol_file_name"]
        },
        {
          "name": "find_symbol",
          "parameters": [
            {"name": "symbol_name", "type": "str", "description": "要查找的符号名"},
            {"name": "module_name", "type": "str | None", "description": "可选：限定查找的模块名"}
          ],
          "return_type": "dict | None",
          "description": "在所有加载的符号表中查找指定符号。",
           "dependencies": ["mccp_toolchain.utils.find_in_list_by_key"]
        },
         {
          "name": "update_symbol",
          "parameters": [
            {"name": "symbol_data", "type": "dict", "description": "要更新或添加的符号数据 (包含 'name', 'module_name')"}
          ],
          "return_type": "bool",
          "description": "更新或添加一个符号到对应的模块符号表。如果符号已存在且 is_frozen 为 true，则拒绝更新。",
          "dependencies": ["mccp_toolchain.utils.FIND_INDEX_OF_DICT_IN_LIST"]
        },
         {
          "name": "get_module_symbols",
          "parameters": [
            {"name": "module_name", "type": "str", "description": "模块名"}
          ],
          "return_type": "dict",
          "description": "获取指定模块的符号表数据。",
          "dependencies": []
        },
         {
           "name": "get_all_symbols",
           "type": "method",
           "parameters": [],
           "return_type": "dict",
           "description": "获取所有加载模块的符号表数据。",
           "dependencies": []
         },
         {
           "name": "derive_symbol_file_name",
           "type": "method",
           "parameters": [
             {"name": "module_name", "type": "str", "description": "模块名"}
           ],
           "return_type": "str",
           "description": "根据模块名生成对应的 symbols.json 文件名。",
           "dependencies": []
         }
      ]
    },
     {
      "name": "Symbol",
      "type": "class",
      "description": "表示一个符号的简单数据结构。",
      "attributes": [
        {"name": "name", "type": "str", "description": "符号名称"},
        {"name": "type", "type": "str", "description": "符号类型 ('class', 'function', 'variable', 'constant')"},
        {"name": "description", "type": "str", "description": "符号描述"},
        {"name": "module_name", "type": "str", "description": "符号所属模块名"},
        {"name": "dependencies", "type": "list[str]", "description": "依赖的其他符号名或模块名"},
        {"name": "is_frozen", "type": "bool", "description": "标记该符号是否被冻结，不可由 LLM 修改。"},
        {"name": "parameters", "type": "list", "description": "函数或方法的参数列表"},
        {"name": "return_type", "type": "str | None", "description": "函数或方法的返回类型"},
        {"name": "attributes", "type": "list", "description": "类的属性列表"},
        {"name": "value", "type": "any", "description": "常量的值"}
      ],
      "dependencies": []
    }
  ]
}
```

文件: `/mccp_symbols/mccp_symbols_mccp_toolchain_ui.json`
```json
{
  "module_name": "mccp_toolchain.ui",
  "description": "用户界面模块，基于 PyQt 框架，提供与用户交互的图形界面。",
  "symbols": [
    {
      "name": "MainWindow",
      "type": "class",
      "description": "主窗口类，继承自 PyQt 的 QMainWindow，包含文件树视图、按钮、状态栏等。",
      "methods": [
        {
          "name": "__init__",
          "parameters": [
            {"name": "config_manager", "type": "mccp_toolchain.mccp.config.ConfigManager", "description": "配置管理器实例"},
            {"name": "file_manager", "type": "mccp_toolchain.mccp.file_manager.FileManager", "description": "文件管理器实例"},
            {"name": "build_orchestrator", "type": "mccp_toolchain.core.build.BuildOrchestrator", "description": "构建协调器实例"},
            {"name": "symbol_manager", "type": "mccp_toolchain.mccp.symbols.SymbolTableManager", "description": "符号表管理器实例"}
          ],
          "return_type": "None",
          "description": "初始化主窗口，设置布局和连接信号槽。",
          "dependencies": ["mccp_toolchain.core.build.BuildOrchestrator", "mccp_toolchain.mccp.file_manager.FileManager", "mccp_toolchain.mccp.symbols.SymbolTableManager", "mccp_toolchain.mccp.config.ConfigManager"]
        },
        {
          "name": "setup_ui",
          "parameters": [],
          "return_type": "None",
          "description": "构建用户界面元素，如文件树视图、菜单、工具栏和状态栏。",
          "dependencies": ["PyQt5.QtWidgets", "PyQt5.QtGui", "PyQt5.QtCore"]
        },
        {
          "name": "connect_signals",
          "parameters": [],
          "return_type": "None",
          "description": "连接UI元素（如按钮、菜单项）的信号到槽函数。",
          "dependencies": []
        },
        {
          "name": "update_file_tree",
          "parameters": [
            {"name": "project_root", "type": "str", "description": "项目根目录路径"}
          ],
          "return_type": "None",
          "description": "刷新文件结构树视图，显示项目文件和目录。",
          "dependencies": ["PyQt5.QtWidgets.QFileSystemModel", "os", "PyQt5.QtCore.QDir"]
        },
        {
          "name": "log_message",
          "parameters": [
            {"name": "message", "type": "str", "description": "要显示在状态栏或日志区域的消息"}
          ],
          "return_type": "None",
          "description": "在状态栏或日志区域显示信息。"
        },
        {
          "name": "handle_new_project",
          "parameters": [],
          "return_type": "None",
          "description": "处理创建新项目的用户操作，可能弹出对话框获取项目信息，调用 FileManager 创建结构。",
          "dependencies": ["PyQt5.QtWidgets.QFileDialog", "os", "mccp_toolchain.mccp.file_manager.FileManager.create_project_structure", "mccp_toolchain.ui.main_window.MainWindow.open_project", "mccp_toolchain.ui.main_window.MainWindow.log_message", "PyQt5.QtWidgets.QMessageBox"]
        },
        {
          "name": "handle_open_project",
          "parameters": [],
          "return_type": "None",
          "description": "处理打开现有项目的用户操作，弹出文件对话框选择项目目录，然后调用 open_project 加载并更新文件树。",
          "dependencies": ["PyQt5.QtWidgets.QFileDialog", "os", "mccp_toolchain.ui.main_window.MainWindow.open_project"]
        },
         {
          "name": "open_project",
          "type": "method",
          "parameters": [
            {"name": "path", "type": "str", "description": "用户选择的项目路径"}
          ],
          "return_type": "None",
          "description": "加载一个已存在的项目（配置、符号表）并更新UI。",
          "dependencies": [
             "mccp_toolchain.mccp.file_manager.get_project_root_from_path",
             "mccp_toolchain.mccp.config.ConfigManager.load_config",
             "mccp_toolchain.mccp.symbols.SymbolTableManager.load_all_symbol_tables",
             "mccp_toolchain.ui.main_window.MainWindow.update_file_tree",
             "mccp_toolchain.ui.main_window.MainWindow.log_message",
             "PyQt5.QtWidgets.QMessageBox"
          ]
        },
        {
          "name": "handle_run_build",
          "parameters": [
            {"name": "target_layer", "type": "str", "description": "构建目标层级 ('mcbc', 'mcpc', 'code')"}
          ],
          "return_type": "None",
          "description": "处理触发构建流程的用户操作，调用 BuildOrchestrator。",
          "dependencies": ["mccp_toolchain.core.build.BuildOrchestrator.run_forward_build", "mccp_toolchain.ui.main_window.MainWindow.log_message", "mccp_toolchain.ui.main_window.MainWindow.update_file_tree", "PyQt5.QtWidgets.QMessageBox"]
        },
         {
           "name": "handle_run_reverse_build_placeholder",
           "type": "method",
           "parameters": [],
           "return_type": "None",
           "description": "Placeholder handler for the reverse build button.",
           "dependencies": ["PyQt5.QtWidgets.QMessageBox", "mccp_toolchain.ui.main_window.MainWindow.log_message"]
         },
         {
           "name": "_expand_important_dirs",
           "type": "method",
           "parameters": [
              {"name": "model", "type": "PyQt5.QtWidgets.QFileSystemModel"},
              {"name": "root_path", "type": "str"}
           ],
           "return_type": "None",
           "description": "Helper to expand key MCCP directories in the file tree.",
           "dependencies": ["os"]
         },
          {
           "name": "_set_buttons_enabled",
           "type": "method",
           "parameters": [
             {"name": "enabled", "type": "bool"}
           ],
           "return_type": "None",
           "description": "Helper to enable/disable build-related buttons during process.",
           "dependencies": []
         }
      ]
    }
  ]
}
```

文件: `/mccp_symbols/mccp_symbols_mccp_toolchain_utils.json`
```json
{
  "module_name": "mccp_toolchain.utils",
  "description": "通用工具模块，提供各种辅助函数。",
  "symbols": [
    {
      "name": "normalize_path",
      "type": "function",
      "parameters": [
        {"name": "path", "type": "str", "description": "待规范化的路径"}
      ],
      "return_type": "str",
      "description": "规范化文件路径，处理斜杠、相对路径等。",
      "dependencies": ["os", "pathlib"]
    },
    {
      "name": "validate_file_name",
      "type": "function",
      "parameters": [
        {"name": "file_name", "type": "str", "description": "待验证的文件名"}
      ],
      "return_type": "bool",
      "description": "验证文件名是否符合命名规范 (snake_case)。",
      "dependencies": ["re"]
    },
     {
      "name": "snake_to_pascal_case",
      "type": "function",
      "parameters": [
        {"name": "text", "type": "str", "description": "snake_case 字符串"}
      ],
      "return_type": "str",
      "description": "将 snake_case 字符串转换为 PascalCase。"
    },
     {
      "name": "pascal_to_snake_case",
      "type": "function",
      "parameters": [
        {"name": "text", "type": "str", "description": "PascalCase 字符串"}
      ],
      "return_type": "str",
      "description": "将 PascalCase 字符串转换为 snake_case。"
    },
     {
       "name": "find_in_list_by_key",
       "type": "function",
       "parameters": [
         {"name": "list_data", "type": "list[dict]", "description": "待查找的字典列表"},
         {"name": "key_name", "type": "str", "description": "用于匹配的键名"},
         {"name": "key_value", "type": "any", "description": "待匹配的键值"}
       ],
       "return_type": "dict | None",
       "description": "在字典列表中按键值查找字典。",
       "dependencies": []
     },
     {
        "name": "FIND_INDEX_OF_DICT_IN_LIST",
        "type": "function",
        "parameters": [
          {"name": "list_data", "type": "list[dict]"},
          {"name": "key_name", "type": "str"},
          {"name": "key_value", "type": "any"}
        ],
        "return_type": "int | None",
        "description": "在字典列表中按键值查找第一个匹配字典的索引。",
        "dependencies": []
     }
  ]
}
```

文件: `/mccp_toolchain/__init__.py`
```python
# This file makes the 'mccp_toolchain' directory a Python package.
```

文件: `/mccp_toolchain/core/__init__.py`
```python
# This file makes the 'core' directory a Python package.
```

文件: `/mccp_toolchain/core/build.py`
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

# Import MCCP Toolchain Modules
# Use relative imports within the package
from ..mccp.config import ConfigManager
from ..mccp.file_manager import FileManager
from ..mccp.symbols import SymbolTableManager
from .llm import LLMClient, PromptGenerator # PromptGenerator might be instantiated locally or injected
from ..mccp.parsers import (
    RequirementsParser, McbcParser, McpcParser, TargetCodeParser, JsonParser
)
from ..utils.utils import find_in_list_by_key # Assuming utils provides this helper


# Define constants as per Symbol Table and MCBC
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

        # Ensure symbols are loaded to memory for context
        # Note: This might have been done during project open, but re-loading ensures freshness
        self.symbol_manager.load_all_symbol_tables(project_path)
        self.log_info("BuildOrchestrator: Symbol tables loaded.")

        # Get the defined build layer sequence
        layer_sequence = BUILD_LAYERS # Use the constant defined in this module

        try:
            start_index = layer_sequence.index(start_layer_key)
            end_index = layer_sequence.index(end_layer_key)
        except ValueError:
            self.log_error(f"BuildOrchestrator: Invalid start or end layer key: {start_layer_key} -> {end_layer_key}")
            return False

        if start_index >= end_index:
            self.log_error(f"BuildOrchestrator: Start layer '{start_layer_key}' is not before end layer '{end_layer_key}' in sequence.")
            return False

        # Iterate through the layer transition steps
        for step_index in range(start_index, end_index):
            current_layer_key = layer_sequence[step_index]
            next_layer_key = layer_sequence[step_index + 1]

            self.log_info(f"BuildOrchestrator: Processing layer transition: {current_layer_key} -> {next_layer_key}")

            # Find the corresponding build rule key based on current and next layer
            rule_key = self.get_rule_key(current_layer_key, next_layer_key, "forward")
            if rule_key is None:
                self.log_error(f"BuildOrchestrator: No forward build rule found for {current_layer_key} to {next_layer_key}. Aborting build.")
                return False

            # Get build rule configuration
            rule_config = self.config_manager.get_build_rule(rule_key)
            if rule_config is None:
                 # This should not happen if get_rule_key returned a key, but as a safeguard:
                 self.log_error(f"BuildOrchestrator: Rule configuration not found for key: {rule_key}. Aborting build.")
                 return False


            # Assume rule config includes input/output layer directory keys and file extensions
            source_layer_dir_key = rule_config.get('input_layer_dir_key')
            target_layer_dir_key = rule_config.get('output_layer_dir_key')
            source_ext = rule_config.get('input_extension')
            target_ext = rule_config.get('output_extension')
            source_parser_key = rule_config.get('source_parser')
            target_parser_key = rule_config.get('target_parser') # Target parser might be optional or not used for validation

            if not all([source_layer_dir_key, target_layer_dir_key, source_ext, target_ext, source_parser_key]):
                 self.log_error(f"BuildOrchestrator: Incomplete rule configuration for {rule_key}. Missing directory keys, extensions, or source parser. Aborting build.")
                 return False


            # Get all source files for the current layer
            # Note: "requirements" is likely a single file, not a directory. Handle this edge case.
            if current_layer_key == "requirements":
                 # Assuming requirements file name is fixed or in config
                 req_dir_key = self.config_manager.get_setting("layer_mapping.requirements_dir", ".") # e.g., "requirements" or "."
                 req_file_name = "requirements.md" # Standard name
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


            # Get the source parser instance
            source_parser_instance = self.parsers.get(source_parser_key)
            if source_parser_instance is None:
               self.log_error(f"BuildOrchestrator: Source parser '{source_parser_key}' not found in injected parsers for rule '{rule_key}'. Aborting build.")
               return False

            # Get the target parser instance (might be optional for some rules)
            target_parser_instance = self.parsers.get(target_parser_key) # Can be None if not required


            # Process each source file
            for source_file_path in source_files:
                self.log_info(f"BuildOrchestrator: Transforming file {source_file_path}...")

                # Derive the target file path
                # Note: For md->mcbc, the output file name might be derived differently,
                # e.g., from requirements.md to a single mcbc file like project_behaviors.mcbc
                # For mcbc->mcpc and mcpc->code, usually same base name different ext/dir.
                # The derive_target_file_name needs logic considering the rule/layer.
                # Simplified derivation for now: replace extension and change directory.
                source_base_name = os.path.splitext(os.path.basename(source_file_path))[0]
                # Specific handling for md->mcbc if needed, e.g., hardcode target name
                if rule_key == "md_to_mcbc":
                     project_name_slug = self.config_manager.get_setting('project_name', 'project').replace('-', '_').lower()
                     target_file_name = f"{project_name_slug}_behaviors{target_ext}"
                else:
                     target_file_name = f"{source_base_name}{target_ext}"


                target_file_path = self.file_manager.get_file_path(project_path, target_layer_dir_key, target_file_name)
                self.log_info(f"BuildOrchestrator: Target file path derived: {target_file_path}")


                # Create LayerTransformer instance and execute transformation
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
                    return False # If any file transformation fails, the entire build fails

            # Save symbols after all files in a layer transition are processed
            # This ensures that even if the build is interrupted, partial symbol updates are not lost
            self.symbol_manager.save_all_symbol_tables()
            self.log_info(f"BuildOrchestrator: Symbols saved after {current_layer_key} -> {next_layer_key} transition.")


        # All layer transitions completed successfully
        self.log_info("BuildOrchestrator: Forward build process completed.")
        # Final symbol save (redundant but safe)
        self.symbol_manager.save_all_symbol_tables()
        return True

    def run_reverse_build(self, project_path: str, start_layer: str, end_layer: str) -> bool:
        """
        Execute the reverse build process from a start layer to an end layer (TBD).
        This method is marked as frozen in the symbol table.

        Args:
            project_path: Project root directory.
            start_layer: Start layer ('code', 'mcpc', 'mcbc').
            end_layer: End layer ('mcpc', 'mcbc', 'md').

        Returns:
            bool: Whether the build process completed successfully.
        """
        # According to the symbol table definition, this is a TBD/frozen method
        self.log_warning("BuildOrchestrator: Reverse build is currently not fully implemented.")
        # Future implementation will mirror run_forward_build but use reverse rules and layer sequence.
        # It would involve parsing target code, extracting structure, comparing/updating symbols,
        # and generating higher-level representations (.mcpc, .mcbc, .md) via LLM calls with different prompts.

        # As a placeholder, always return False and indicate not implemented
        # self.symbol_manager.load_all_symbol_tables(project_path) # Need to load symbols for context
        # ... Placeholder logic ...
        return False # Indicate not implemented or failed for now

    def get_rule_key(self, source_layer_key: str, target_layer_key: str, direction: str) -> Optional[str]:
      """
      Find the matching build rule key based on source layer, target layer, and direction.

      Args:
          source_layer_key: Source layer key.
          target_layer_key: Target layer key.
          direction: Build direction ('forward' or 'reverse').

      Returns:
          str | None: The matching build rule key, or None if not found.
      """
      # Get the full config data
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

      # Create a reverse mapping from directory key to layer key for easier lookup
      dir_to_layer_key = {v: k for k, v in layer_mapping.items()}

      for rule_key, rule_config in rules_config.items():
          # Check if the rule's input/output layer directory keys match the requested transition's layer keys
          rule_input_dir_key = rule_config.get('input_layer_dir_key')
          rule_output_dir_key = rule_config.get('output_layer_dir_key')

          input_layer_from_rule = dir_to_layer_key.get(rule_input_dir_key)
          output_layer_from_rule = dir_to_layer_key.get(rule_output_dir_key)

          if input_layer_from_rule == source_layer_key and output_layer_from_rule == target_layer_key:
               return rule_key

      self.log_warning(f"BuildOrchestrator: Could not find rule key for {source_layer_key} -> {target_layer_key} ({direction}).")
      return None


class LayerTransformer:
    """
    Layer Transformer class, responsible for executing a single layer transformation
    (e.g., .mcbc -> .mcpc), involving calling the LLM.
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
        Initializes the Layer Transformer.

        Args:
            config_manager: Config Manager instance.
            file_manager: File Manager instance.
            symbol_manager: Symbol Table Manager instance.
            llm_client: LLM Client instance.
            source_parser: Specific parser instance for source file content.
            target_parser: Optional specific parser instance for target file content.
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
        Executes the transformation from the source file to the target file.
        Includes reading, parsing (conceptually), generating LLM prompt, calling LLM,
        processing response, updating symbols, and writing the target file.

        Args:
            source_file_path: Full path to the source file.
            target_file_path: Full path to the target file.
            build_rule_key: The build rule key from mccp_config.json (e.g., 'mcbc_to_mcpc').

        Returns:
            bool: True if transformation was successful, False otherwise.
        """
        self.log_info(f"LayerTransformer: Transforming {source_file_path} to {target_file_path} using rule '{build_rule_key}'")

        # Read source file content
        source_content = self.file_manager.read_file(source_file_path)
        if source_content is None:
            self.log_error(f"LayerTransformer: Failed to read source file: {source_file_path}")
            return False

        # Get the build rule configuration
        rule_config = self.config_manager.get_build_rule(build_rule_key)
        if rule_config is None:
           self.log_error(f"LayerTransformer: Build rule configuration not found for key: {build_rule_key}")
           return False

        # Get all symbol table data for LLM context
        all_symbols_data = self.symbol_manager.get_all_symbols()

        # Get the full project configuration for LLM context
        full_config = self.config_manager.get_config_data()

        # Generate the LLM prompt
        # PromptGenerator needs ConfigManager to get prompt templates
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

        # Call the LLM
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

        # Process LLM response
        # Assume LLM directly outputted the target file content
        generated_content = llm_response_text

        # --- Symbol update logic (complex, needs refinement) ---
        # The LLM might introduce new symbols or modify existing ones.
        # This part requires parsing the generated_content or a specific part of the LLM response
        # designed for symbol updates.
        # Then call self.symbol_manager.update_symbol(symbol_update)
        # ensuring the 'is_frozen' property is respected.
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


        # If target parser exists, optionally validate or process the generated content
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


        # Write generated content to target file
        success = self.file_manager.write_file(target_file_path, generated_content)
        if not success:
            self.log_error(f"LayerTransformer: Failed to write target file: {target_file_path}")
            return False

        self.log_info(f"LayerTransformer: Successfully transformed {source_file_path} to {target_file_path}.")
        return True

    # Placeholder for complex symbol extraction logic
    def _extract_symbol_updates_from_content(self, content: str, file_path: str, rule_key: str) -> List[Dict]:
        """
        Placeholder: Extracts suggested symbol updates from the generated content.
        This is a complex process depending on the generated content format and build rule.
        e.g., parse generated .mcpc or .py, identify new/modified function signatures, class attributes etc.
        """
        self.log_warning(f"LayerTransformer: Placeholder method _extract_symbol_updates_from_content called for {file_path}, rule {rule_key}.")
        # Implement parsing logic specific to the target format generated by the LLM for this rule
        # Example: If target is .mcpc, use McpcParser to get structure, compare with existing symbols,
        # and propose updates for non-frozen symbols.
        # If target is .py, use AST parser to get code structure and propose updates.
        return [] # Return empty list for now

```

文件: `/mccp_toolchain/core/llm.py`
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
from langchain_openai import ChatOpenAI # Example LLM implementation - Requires openai package installed

# Import MCCP Toolchain Modules
# Use relative imports within the package
from ..mccp.config import ConfigManager
from ..mccp.parsers import JsonParser # Assuming JsonParser is in mccp.parsers


class LLMClient:
    """
    LLM Client class, encapsulates Langchain calls.
    Responsible for connecting to and calling the configured Large Language Model.
    """

    def __init__(self, config_manager: ConfigManager):
        """
        Initializes the LLM Client, reads configuration, and sets up the Langchain model.

        Args:
            config_manager: Config Manager instance.
        """
        self.config_manager: ConfigManager = config_manager
        self.langchain_model: Any = None # Placeholder for Langchain model instance

        self.log_info = print
        self.log_warning = print
        self.log_error = print

        # Get LLM settings
        model_name = self.config_manager.get_setting("llm_settings.model")
        api_url = self.config_manager.get_setting("llm_settings.api_url")
        api_key = self.config_manager.get_setting("llm_settings.api_key")
        # Add other potential settings like temperature, max_tokens etc.

        # Initialize Langchain model
        # This part depends on the specific LLM configured.
        # Using ChatOpenAI as an example. More complex logic might be needed
        # to handle different model types based on config.
        if model_name and api_key: # Basic check if settings are available
             try:
                 # Configure environment variable for API key, or pass key directly
                 # os.environ["OPENAI_API_KEY"] = api_key # Example for OpenAI

                 # Check if api_url suggests a specific endpoint (e.g., for local models)
                 # Note: ChatOpenAI might not support arbitrary API URLs directly in constructor
                 # For custom endpoints or other models, a different Langchain class would be needed.
                 # If base_url parameter is supported, use it.
                 base_url = api_url if api_url and api_url.lower() != "default" else None

                 self.log_info(f"LLMClient: Initializing Langchain model: {model_name}")

                 # Using ChatOpenAI as a concrete example
                 self.langchain_model = ChatOpenAI(
                     model=model_name,
                     api_key=api_key, # Pass key directly
                     base_url=base_url # Pass base_url if not default
                 )
                 self.log_info(f"LLMClient: Model {model_name} initialized successfully.")

             except Exception as e:
                 self.log_error(f"LLMClient: Failed to initialize Langchain model {model_name}: {e}")
                 self.langchain_model = None # Ensure model is None if initialization fails
        else:
            self.log_warning("LLMClient: LLM model name or API key not configured. LLM calls will not function.")
            self.langchain_model = None # Ensure model is None if no config


    def generate_content(self, prompt: str, context: Dict) -> str:
        """
        Calls the LLM to generate content based on the prompt and context.

        Args:
            prompt: The prompt string to send to the LLM.
            context: A dictionary containing supplementary context data (e.g., source_file, target_file, rule, config, symbols).

        Returns:
            str: The raw text response received from the LLM. Returns an empty string if the model is not initialized or the call fails.
        """
        if self.langchain_model is None:
            self.log_error("LLMClient: LLM model is not initialized. Cannot generate content.")
            return ""

        self.log_info("LLMClient: Sending prompt to LLM...")
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
        Parses the raw text output from the LLM to validate its format or extract structured data.

        Args:
            response_text: The raw text response from the LLM.
            target_format: Identifier for the expected target format (e.g., 'mcbc', 'mcpc', 'python_code', 'json').

        Returns:
            object: Structured data (like a dict) or the raw text, depending on the format and parsing capability.
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
        elif target_format in ["mcbc", "mcpc", "python_code", "md"]: # Added md as target format
             # For structured text formats like MCBC, MCPC, code, or markdown,
             # the LayerTransformer might expect the raw text directly,
             # and use dedicated parsers (like McbcParser, McpcParser, TargetCodeParser, RequirementsParser)
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
    Prompt Generator class, responsible for assembling the complete, detailed prompt string
    that will be sent to the LLM, incorporating all necessary information for the transformation task.
    """

    def __init__(self, config_manager: ConfigManager):
        """
        Initializes the Prompt Generator.

        Args:
            config_manager: Config Manager instance.
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
        Creates a comprehensive prompt by combining a base instruction template (from config)
        with specific context data relevant to the current transformation step.

        Args:
            build_rule_key: Build rule key (e.g., 'mcbc_to_mcpc').
            source_content: String content of the source file.
            symbols: Dictionary containing relevant distributed symbol table content.
            config: Dictionary of the mccp_config.json configuration.

        Returns:
            str: The complete, formatted prompt string. Returns empty string if template is not found.
        """
        self.log_info(f"PromptGenerator: Generating prompt for rule '{build_rule_key}'")

        # Get the base prompt template from the configuration
        rule_config = self.config_manager.get_build_rule(build_rule_key)
        if rule_config is None:
             self.log_error(f"PromptGenerator: Rule config not found for key: {build_rule_key}")
             return ""

        base_template = rule_config.get('llm_prompt')

        if not base_template:
            self.log_error(f"PromptGenerator: Prompt template not found in config for rule: {build_rule_key}")
            return ""

        # Format the template, injecting context information
        # The prompt template is expected to use placeholders, e.g., {source_content}, {symbols}, {config}
        # Need to convert symbols and config dictionaries into JSON strings to include structured data in the text prompt
        try:
            symbols_json_str = json.dumps(symbols, indent=2, ensure_ascii=False)
            config_json_str = json.dumps(config, indent=2, ensure_ascii=False)

            # Use Langchain's PromptTemplate or Python f-string for formatting
            # Using Langchain PromptTemplate.from_template(base_template).format(...) is preferred
            # as it's designed for this purpose and handles placeholders robustly.
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

文件: `/mccp_toolchain/mccp/__init__.py`
```python
# This file makes the 'mccp' directory a Python package.
```

文件: `/mccp_toolchain/mccp/config.py`
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

# Import MCCP Toolchain Modules (using relative imports)
# The type hint for FileManager needs the class definition, but avoids import cycle at runtime
# by using a string literal for type hinting initially if needed, or relying on Python 3.7+ postponed evaluation.
# Current structure uses simple imports as defined by the generated code.
from .file_manager import FileManager # Import the real one after placeholder
from .parsers import JsonParser # Assuming JsonParser is here


class ConfigManager:
    """
    Config Manager class, loads and provides configuration data from mccp_config.json.
    Responsible for loading, parsing, and providing project configuration.
    """

    def __init__(self, file_manager: Optional[FileManager]):
        """
        Initializes the Config Manager.

        Args:
            file_manager: File Manager instance. (Can be None initially due to circular dependency)
        """
        # Store file_manager. Due to circular dependency,
        # main.py might instantiate with None initially and set it later.
        self.file_manager: Optional[FileManager] = file_manager
        self.json_parser: JsonParser = JsonParser() # Assuming JsonParser can be instantiated directly
        # Internal state to hold loaded config and project root
        self._config_data: Dict[str, Any] = {}
        self._project_root: Optional[str] = None

        self.log_info = print
        self.log_warning = print
        self.log_error = print

    def load_config(self, project_path: str) -> bool:
        """
        Loads and parses the mccp_config.json file from the project directory.

        Args:
            project_path: Project root directory.

        Returns:
            bool: True if configuration was loaded successfully, False otherwise.
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
        Retrieves a configuration value based on a key path. Supports nested path access.
        E.g., "llm_settings.model"

        Args:
            key: The key path for the configuration item (dot-separated).
            default: The default value to return if the key does not exist.

        Returns:
            any: The configuration value, or the default value.
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
        Retrieves the directory name corresponding to a specific MCCP layer key.

        Args:
            layer_key: Layer key (e.g., 'behavior_code_dir', 'symbol_table_root').

        Returns:
            str | None: The directory name associated with the layer (relative to project root), or None if not found.
        """
        # Get from 'layer_mapping' section using get_setting
        return self.get_setting(f"layer_mapping.{layer_key}", None)

    def get_build_rule(self, rule_key: str) -> Optional[Dict]:
        """
        Retrieves the detailed configuration for a specific build or reverse build rule.
        Checks both 'build_rules' and 'reverse_build_rules' sections.

        Args:
            rule_key: Build rule key (e.g., 'mcbc_to_mcpc', 'py_to_mcpc').

        Returns:
            dict | None: Dictionary containing the configuration for the rule, or None if not found.
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
       Retrieves the complete configuration data dictionary.

       Returns:
           dict: The currently loaded configuration data dictionary.
       """
       # Return a copy of the internal config data to prevent external modification
       return self._config_data.copy()

    def get_project_root(self) -> Optional[str]:
        """
        Retrieves the currently loaded project root directory path.

        Returns:
            str | None: Project root path, or None if no project is loaded.
        """
        return self._project_root

    def get_default_config_json(self) -> Dict[str, Any]:
         """
         Provides a default configuration dictionary structure, used for the initial mccp_config.json file
         when creating a new project. This is necessary to solve the circular dependency issue
         where FileManager needs default config to create the file, but ConfigManager needs FileManager
         to load the file. Defining defaults locally avoids this dependency.

         Returns:
              Dict[str, Any]: Default configuration dictionary.
         """
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

文件: `/mccp_toolchain/mccp/file_manager.py`
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

# Import MCCP Toolchain Modules (using relative imports)
# The type hint for ConfigManager needs the class definition, but avoids import cycle at runtime
# by using a string literal for type hinting initially if needed, or relying on Python 3.7+ postponed evaluation.
# Current structure uses simple imports as defined by the generated code.
from .config import ConfigManager # Import the real one after placeholder
from .parsers import JsonParser # Assuming JsonParser is here


class FileManager:
    """
    File Manager class, provides encapsulation for file and directory operations.
    Responsible for handling project directory structure, file reading/writing, etc.
    """

    def __init__(self, config_manager: Optional[ConfigManager]):
        """
        Initializes the File Manager.

        Args:
            config_manager: Config Manager instance. (Can be None initially due to circular dependency)
        """
        # Store config_manager. Due to circular dependency,
        # main.py might instantiate with None initially and set it later.
        self.config_manager: Optional[ConfigManager] = config_manager

        # References to standard libraries
        self.os_module = os
        self.pathlib_module = pathlib

        self.log_info = print
        self.log_warning = print
        self.log_error = print


    def create_project_structure(self, project_path: str) -> bool:
        """
        Creates the standard project directory structure and initial files (like mccp_config.json)
        according to MCCP specifications and configuration.

        Args:
            project_path: The root directory path for the new project.

        Returns:
            bool: True if structure creation was successful, False otherwise.
        """
        self.log_info(f"FileManager: Creating project structure at {project_path}")

        # Ensure config_manager is set (handle circular dependency resolution)
        # Although ConfigManager *can* be None initially, it must be set before this method is called.
        if self.config_manager is None:
             self.log_error("FileManager: ConfigManager not set. Cannot create project structure.")
             return False

        # Define standard directories (or get from config - but config needs to be created first)
        # Using hardcoded defaults and assuming config will load them later.
        # The default config data structure from ConfigManager is used to get these names.
        default_config_data = self.config_manager.get_default_config_json() # Use real ConfigManager method
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
        # Add temp directory
        directory_names.append("temp")


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
            # Use the default config data from the ConfigManager
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
            # Ensure get_file_path works even before config is loaded by File Manager,
            # potentially by temporarily using the default layer_mapping or having get_file_path
            # robust enough to handle this initial call.
            # Let's rely on get_file_path to work by reading the *newly created* config file.
            # Or, temporarily derive path based on default mapping. Let's use default mapping explicitly here for safety.
            default_req_dir = default_config_data.get("layer_mapping", {}).get("requirements_dir", ".")
            req_file_path = self.os_module.path.join(project_path, default_req_dir, req_file_name)
            self.os_module.makedirs(self.os_module.path.dirname(req_file_path), exist_ok=True) # Ensure req dir exists


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
            default_symbol_dir = default_config_data.get("layer_mapping", {}).get("symbol_table_root", "mccp_symbols")
            initial_symbol_file_name = "mccp_symbols_initial.json"
            initial_symbol_file_path = self.os_module.path.join(project_path, default_symbol_dir, initial_symbol_file_name)
            self.os_module.makedirs(self.os_module.path.dirname(initial_symbol_file_path), exist_ok=True) # Ensure symbol dir exists

            default_symbol_content_json = json_parser.generate({
                "module_name": "initial_symbols",
                "description": "Initial project symbols",
                "symbols": [
                    # Example symbol if needed
                    # {"name": "ExampleClass", "type": "class", "module_name": "initial_symbols", "is_frozen": False}
                ]
            })
            if not self.write_file(initial_symbol_file_path, default_symbol_content_json):
                 self.log_error(f"FileManager: Failed to write initial symbol file: {initial_symbol_file_path}")
                 success = False


        except Exception as e:
            self.log_error(f"FileManager: Error creating project structure: {e}")
            success = False

        return success

    def read_file(self, file_path: str) -> Optional[str]:
        """
        Reads file content and returns it as a string. Returns None if the file does not exist or reading fails.

        Args:
            file_path: The path to the file to read.

        Returns:
            str | None: File content, or None if reading failed.
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
        Writes content to a file. Creates parent directories if they don't exist. Returns True on success, False on failure.

        Args:
            file_path: The path where the file should be written.
            content: The string content to write.

        Returns:
            bool: True if writing was successful, False otherwise.
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
        Constructs the full file system path for a file within a specific MCCP project layer,
        based on configured layer mapping and the file name.

        Args:
            project_path: Project root directory.
            layer_key: Layer key (e.g., 'behavior_code_dir', 'symbol_table_root').
            file_name: File name (without path).

        Returns:
            str: The complete file path.
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
        Lists all file paths with a specific extension within a designated layer directory of the project.

        Args:
            project_path: Project root directory.
            layer_key: Layer key (e.g., 'behavior_code_dir').
            extension: File extension (e.g., '.mcbc', '.py').

        Returns:
            list[str]: List of complete paths to matching files.
        """
        self.log_info(f"FileManager: Listing files in layer '{layer_key}' with extension '{extension}' for project {project_path}")

        # Get the full path to the layer directory
        # Use get_file_path with empty file_name to get the directory path
        # Note: this relies on get_file_path handling the trailing slash or pathlib joining correctly.
        # get_file_path(project_path, layer_key, "") should give the directory path.
        # Let's explicitly join project_path and the layer_dir_name from config for clarity.
        layer_dir_name = self.config_manager.get_layer_dir(layer_key)
        if layer_dir_name is None:
             self.log_error(f"FileManager: Could not determine directory path for layer key: {layer_key} (config missing mapping).")
             return []

        # Handle layer_dir_name being '.' for project root
        if layer_dir_name == ".":
            layer_dir_path = project_path
        else:
            layer_dir_path = self.os_module.path.join(project_path, layer_dir_name)


        # Check if the directory exists
        if not self.os_module.path.isdir(layer_dir_path):
             self.log_warning(f"FileManager: Layer directory not found: {layer_dir_path}. Returning empty list.")
             return []

        # Use pathlib to list files with the specified extension
        path_object = self.pathlib_module.Path(layer_dir_path)
        file_paths: List[str] = []
        try:
            # Using glob() for pattern matching. Use *{extension} for non-recursive scan in the specific layer directory.
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
    Given a path believed to be somewhere within an MCCP project, attempt to locate
    the project's root directory by searching upwards for mccp_config.json.
    This is a standalone function, not a method of FileManager.

    Args:
        any_path_within_project: Any path string potentially inside an MCCP project.

    Returns:
        str | None: The path string of the project root directory if found, otherwise None.
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
        # Check for drive letter roots on Windows (e.g., C:\ == C:\)
        if parent_path == current_path and os.path.exists(current_path): # Check exists to handle non-existent initial path
             print(f"FileManager: Reached filesystem root without finding mccp_config.json.")
             break # Reached the filesystem root or an invalid path


        current_path = parent_path
        # Also check if parent_path becomes empty string or just '/' after os.path.dirname
        if not current_path or current_path == '/':
             print(f"FileManager: Reached filesystem root without finding mccp_config.json.")
             break # Reached the filesystem root

    # Config file not found in any parent directory
    print("FileManager: Could not find project root.")
    return None

```

文件: `/mccp_toolchain/mccp/parsers.py`
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
    Parser class for requirements.md files.
    Parses Markdown formatted requirements text into structured data.
    """
    def parse(self, content: str) -> Dict[str, Any]:
        """
        Parses Markdown formatted requirements text into structured data.

        Args:
            content: Text content of the requirements.md file.

        Returns:
            dict: Structured representation of the requirements data.
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
                       last_sub_section_key = list(data[current_section].keys())[-1] if data[current_section] else None
                       if last_sub_section_key:
                            data[current_section][last_sub_section_key] += line + "\n"


        # This is a very basic placeholder parse. A real implementation would need
        # a proper Markdown parser library and more sophisticated logic.
        print("RequirementsParser: Returning placeholder data.")
        return data

    def generate(self, data: Dict[str, Any]) -> str:
        """
        Generates Markdown text from structured requirements data.

        Args:
            data: Structured requirements data.

        Returns:
            str: Markdown formatted text string.
        """
        print("RequirementsParser: Placeholder generate method called.")
        # Logic to format structured data back into Markdown.
        # This is simplified and doesn't reverse the parsing complexity.
        lines: List[str] = []
        lines.append("# Project Requirements\n\n") # Assuming a standard title

        for section, content in data.items():
            lines.append(f"## {section}\n")
            if isinstance(content, str):
                lines.append(content.strip() + "\n")
            elif isinstance(content, dict):
                for sub_section, sub_content in content.items():
                    lines.append(f"### {sub_section}\n")
                    lines.append(sub_content.strip() + "\n")
            lines.append("") # Add blank line after section

        markdown_text = "\n".join(lines)
        print("RequirementsParser: Returning placeholder Markdown text.")
        return markdown_text


class McbcParser:
    """
    Parser class for .mcbc (Behavior Code) files.
    Parses .mcbc text into structured behavior description objects and can generate .mcbc format from structured data.
    """
    def parse(self, content: str) -> Dict[str, Any]:
        """
        Parses .mcbc text into structured behavior description objects.

        Args:
            content: Text content of the .mcbc file.

        Returns:
            dict: Structured behavior description data.
        """
        print("McbcParser: Placeholder parse method called.")
        # Logic to parse MCBC markdown format:
        # Identify "# Module:", "### Overview", "#### Class:", "### Components", etc.
        # Structure into dictionary: { "module_name": ..., "overview": {...}, "components": [{ "type": "class", "name": ..., "behaviors": [...] }] }
        # Requires sophisticated text processing, likely line-by-line with state tracking.
        # Example structure based on headings and key-value lines:
        data: Dict[str, Any] = {"module_name": None, "overview": {}, "components": [], "constants": []} # Added constants
        current_component: Optional[Dict] = None
        current_behavior: Optional[Dict] = None
        current_constant: Optional[Dict] = None # Added constant tracking
        current_section_type: Optional[str] = None # e.g., "overview", "component", "behavior", "constant"

        lines = content.splitlines()
        for line in lines:
             stripped_line = line.strip()

             if stripped_line.startswith("# Module: "):
                  data["module_name"] = stripped_line[len("# Module: "):].strip()
                  current_section_type = None # Reset section state
             elif stripped_line.startswith("### Overview"):
                  data["overview"] = {}
                  current_section_type = "overview"
                  current_component = None # Reset component state
                  current_behavior = None # Reset behavior state
                  current_constant = None # Reset constant state
             elif stripped_line.startswith("### Components"):
                  data["components"] = []
                  current_section_type = "components_list" # State indicating we are in components section, before a component
                  current_component = None # Reset component state
                  current_behavior = None # Reset behavior state
                  current_constant = None # Reset constant state
             elif stripped_line.startswith("### Constants"): # Added parsing for constants section
                  data["constants"] = []
                  current_section_type = "constants_list" # State indicating we are in constants section, before a constant
                  current_component = None
                  current_behavior = None
                  current_constant = None
             elif stripped_line.startswith("#### Class: "):
                  component_name = stripped_line[len("#### Class: "):].strip()
                  current_component = {"type": "class", "name": component_name, "description": "", "behaviors": []}
                  data["components"].append(current_component)
                  current_section_type = "component" # Inside a component
                  current_behavior = None # Reset behavior state
                  current_constant = None # Reset constant state
             elif stripped_line.startswith("#### Constant: "): # Added parsing for individual constants
                  constant_name = stripped_line[len("#### Constant: "):].strip()
                  current_constant = {"type": "constant", "name": constant_name, "description": "", "value_description": ""}
                  data["constants"].append(current_constant)
                  current_section_type = "constant" # Inside a constant
                  current_component = None
                  current_behavior = None

             # Handle items within sections based on current_section_type
             elif stripped_line.startswith("- Description:") and (current_component or current_constant) and current_section_type in ["component", "constant"]:
                  if current_component:
                      current_component["description"] = stripped_line[len("- Description:"):].strip()
                  elif current_constant:
                       current_constant["description"] = stripped_line[len("- Description:"):].strip()

             elif stripped_line.startswith("- Behaviors:") and current_component and current_section_type == "component":
                 # Prepare for behavior list
                 current_section_type = "behaviors_list" # State indicating we are in behaviors section, before a behavior
                 current_behavior = None # Reset behavior state

             elif stripped_line.startswith("- Value Description:") and current_constant and current_section_type == "constant": # Added parsing for constant value desc
                  current_constant["value_description"] = stripped_line[len("- Value Description:"):].strip()

             elif stripped_line.startswith("- ") and current_section_type == "behaviors_list":
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
                     current_section_type = "behavior" # Inside a behavior
                 # Add other list items here if needed for component details outside behaviors?
             elif stripped_line.startswith("- Purpose:") and current_behavior and current_section_type == "behavior":
                 current_behavior["purpose"] = stripped_line[len("- Purpose:"):].strip()
             elif stripped_line.startswith("- Process:") and current_behavior and current_section_type == "behavior":
                 current_behavior["process"] = stripped_line[len("- Process:"):].strip()
             elif stripped_line.startswith("- Input:") and current_behavior and current_section_type == "behavior":
                 current_behavior["input"] = stripped_line[len("- Input:"):].strip()
             elif stripped_line.startswith("- Output:") and current_behavior and current_section_type == "behavior":
                 current_behavior["output"] = stripped_line[len("- Output:"):].strip()
             elif stripped_line.startswith("- Dependencies:") and current_behavior and current_section_type == "behavior":
                 current_behavior["dependencies"] = stripped_line[len("- Dependencies:"):].strip()
             elif stripped_line.startswith("- Interactions:") and current_behavior and current_section_type == "behavior":
                 current_behavior["interactions"] = stripped_line[len("- Interactions:"):].strip()

             # Handle multiline descriptions or other fields - needs indentation check
             # This is complex without strict indentation rules. Simplistic approach: if a line is indented
             # relative to the start of the current field line, append it.
             # Need to store the indentation level of the start of the field.
             # Skipping this complex logic in the placeholder.

             elif stripped_line and current_section_type == "overview":
                 # Append lines to overview, sophisticated parsing needed for key-value pairs
                 # For now, just append (basic)
                 for key_prefix in ["- Purpose:", "- Responsibilities:", "- Interactions:"]:
                      if stripped_line.startswith(key_prefix):
                           key = key_prefix[2:].strip(":")
                           # Handle potential duplicates or appending to existing value
                           existing_value = data["overview"].get(key, "")
                           if existing_value: existing_value += " " # Add space if appending
                           data["overview"][key] = existing_value + stripped_line[len(key_prefix):].strip()
                           break
                 else:
                      # If it didn't match a known key prefix, maybe append to a generic overview text or ignore
                      pass # Ignoring unformatted lines in overview for this simple parser


        # This placeholder parser is very simplistic. A real one would handle
        # indentation for multiline values, different list types, comments, etc.
        print("McbcParser: Returning placeholder data.")
        return data

    def generate(self, data: Dict[str, Any]) -> str:
        """
        Generates .mcbc formatted text from structured data.

        Args:
            data: Structured behavior description data.

        Returns:
            str: .mcbc formatted text string.
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
            for key in ["Purpose", "Responsibilities", "Interactions"]: # Maintain order
                 value = overview.get(key)
                 if value: # Only include if value is not empty
                    # Handle multiline values by indenting subsequent lines
                    indented_value = "\n  ".join(str(value).splitlines())
                    lines.append(f"- {key}: {indented_value}")
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
                    indented_desc = "\n  ".join(str(comp_description).splitlines())
                    lines.append(f"- Description: {indented_desc}")

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

        constants = data.get("constants", []) # Added constant generation
        if constants:
            lines.append("### Constants")
            for constant in constants:
                 const_name = constant.get("name", "unknown_constant").upper() # Constants often uppercase
                 const_desc = constant.get("description")
                 const_value_desc = constant.get("value_description")
                 lines.append(f"#### Constant: {const_name}")
                 if const_desc:
                      indented_desc = "\n  ".join(str(const_desc).splitlines())
                      lines.append(f"- Description: {indented_desc}")
                 if const_value_desc:
                      indented_value_desc = "\n  ".join(str(const_value_desc).splitlines())
                      lines.append(f"- Value Description: {indented_value_desc}")
                 lines.append("") # Blank line after constant


        # Remove trailing blank lines
        while lines and not lines[-1].strip():
             lines.pop()

        mcbc_text = "\n".join(lines)
        print("McbcParser: Returning placeholder MCBC text.")
        return mcbc_text


class McpcParser:
    """
    Parser class for .mcpc (Pseudo Code) files.
    Parses .mcpc text into structured symbol-pseudo code objects and can generate .mcpc format from structured data.
    """
    def parse(self, content: str) -> Dict[str, Any]:
        """
        Parses .mcpc text into structured symbol-pseudo code objects.

        Args:
            content: Text content of the .mcpc file.

        Returns:
            dict: Structured symbol-pseudo code data.
        """
        print("McpcParser: Placeholder parse method called.")
        # Logic to parse MCPC pseudo-code structure:
        # Identify "MODULE", "CLASS", "METHOD", "FUNCTION", "CONSTANT", "DESCRIPTION", "INHERITS", "ATTRIBUTE", "PARAMETERS", "RETURNS", keywords like "SET", "CALL", "IF", "ELSE", "LOOP", "RETURN", "CREATE".
        # Represent the parsed structure (modules, classes, methods, functions, constants, their parameters, return types, and the pseudo-code body) in a dictionary.
        # RETURN { "module_name": ..., "classes": [{ "name": ..., "methods": [...] }], "functions": [...], "constants": [...] }
        data: Dict[str, Any] = {"module_name": None, "classes": [], "functions": [], "constants": []}
        current_class: Optional[Dict] = None
        current_method_or_function: Optional[Dict] = None
        current_constant: Optional[Dict] = None
        current_section_type: Optional[str] = None # "module", "class", "method", "function", "constant"

        lines = content.splitlines()
        # Need to handle indentation for blocks (DESCRIPTION, pseudo-code)
        current_block_indent = -1
        current_block_lines: List[str] = []

        def add_current_block_to(target_dict: Dict, key: str):
            """Helper to add accumulated lines to a dictionary key."""
            nonlocal current_block_lines, current_block_indent
            if current_block_lines:
                # Join lines, stripping only leading/trailing whitespace from the whole block
                # But preserve internal line breaks and indentation relative to the block start
                target_dict[key] = "\n".join(current_block_lines) # Or strip initial indent? Complex.
            current_block_lines = [] # Reset
            current_block_indent = -1 # Reset


        for i, line in enumerate(lines):
             stripped_line = line.strip()
             current_indent = len(line) - len(line.lstrip())

             # Check for block start/end based on keywords and indentation
             # A new keyword at the same or lower indentation level ends the previous block
             if stripped_line.startswith(("MODULE", "CLASS", "METHOD", "FUNCTION", "CONSTANT", "DESCRIPTION", "INHERITS", "ATTRIBUTE")):
                 # Process any pending block lines before starting new element/block
                 if current_method_or_function: add_current_block_to(current_method_or_function, "pseudo_code")
                 if current_constant and current_section_type == "constant_value_block": add_current_block_to(current_constant, "value_pseudo_code")
                 # Add other block types here if needed (e.g., multi-line DESCRIPTION)

                 if stripped_line.startswith("MODULE "):
                       module_name = stripped_line[len("MODULE "):].split(" ", 1)[0].strip()
                       data["module_name"] = module_name
                       current_section_type = "module"
                       current_class = None
                       current_method_or_function = None
                       current_constant = None
                       # Indent for module is 0, but subsequent blocks might be indented (e.g. DESCRIPTION)
                       # Let's track indent based on the first line of a potential block
                       current_block_indent = -1

                 elif stripped_line.startswith("CLASS "):
                       class_name = stripped_line[len("CLASS "):].split(" ", 1)[0].strip()
                       current_class = {"name": class_name, "description": "", "inherits": None, "attributes": [], "methods": []}
                       data["classes"].append(current_class)
                       current_section_type = "class"
                       current_method_or_function = None
                       current_constant = None
                       current_block_indent = -1

                 elif stripped_line.startswith("METHOD ") and current_class:
                       # Extract name, parameters, returns
                       method_signature = stripped_line[len("METHOD "):].strip()
                       name_match = re.match(r"(\w+)\s*\(", method_signature)
                       method_name = name_match.group(1) if name_match else method_signature.split()[0]

                       params_match = re.search(r"\(PARAMETERS (.*?)\)", method_signature)
                       parameters_str = params_match.group(1).strip() if params_match else ""

                       returns_match = re.search(r"RETURNS (.*)$", method_signature)
                       returns_str = returns_match.group(1).strip() if returns_match else None

                       current_method_or_function = {"name": method_name, "description": "", "parameters": parameters_str, "return_type": returns_str, "pseudo_code": ""}
                       current_class["methods"].append(current_method_or_function)
                       current_section_type = "method"
                       current_constant = None
                       # Pseudo-code block starts after the method/function signature line
                       # The first indented line after this will set current_block_indent
                       current_block_indent = -1 # Wait for first body line indent

                 elif stripped_line.startswith("FUNCTION "):
                       # Extract name, parameters, returns - similar to method
                       function_signature = stripped_line[len("FUNCTION "):].strip()
                       name_match = re.match(r"(\w+)\s*\(", function_signature)
                       function_name = name_match.group(1) if name_match else function_signature.split()[0]

                       params_match = re.search(r"\(PARAMETERS (.*?)\)", function_signature)
                       parameters_str = params_match.group(1).strip() if params_match else ""

                       returns_match = re.search(r"RETURNS (.*)$", function_signature)
                       returns_str = returns_match.group(1).strip() if returns_match else None


                       current_method_or_function = {"name": function_name, "description": "", "parameters": parameters_str, "return_type": returns_str, "pseudo_code": ""}
                       data["functions"].append(current_method_or_function)
                       current_section_type = "function"
                       current_class = None # Functions are top-level
                       current_constant = None
                       current_block_indent = -1 # Wait for first body line indent

                 elif stripped_line.startswith("CONSTANT "):
                       constant_name = stripped_line[len("CONSTANT "):].split(" ", 1)[0].strip()
                       current_constant = {"name": constant_name, "description": "", "value_pseudo_code": ""} # Use value_pseudo_code for multi-line values
                       data["constants"].append(current_constant)
                       current_section_type = "constant"
                       current_class = None
                       current_method_or_function = None
                       current_block_indent = -1 # Wait for first body line indent

                 elif stripped_line.startswith("DESCRIPTION "):
                     # This DESCRIPTION is likely for the current element (MODULE, CLASS, METHOD, FUNCTION, CONSTANT)
                     desc = stripped_line[len("DESCRIPTION "):].strip('"').strip("'") # Simple quote removal
                     if current_section_type == "module" and data["module_name"]: data["description"] = desc
                     elif current_class and current_section_type == "class": current_class["description"] = desc
                     elif current_method_or_function and current_section_type in ["method", "function"]: current_method_or_function["description"] = desc
                     elif current_constant and current_section_type == "constant": current_constant["description"] = desc
                     # If DESCRIPTION is multi-line, the next line might be indented and not a keyword
                     # This needs logic to detect continuation lines - skipping in placeholder.


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
                      # This indicates the start of the value definition block
                      # The rest of this line and subsequent indented lines are the value definition
                      value_str_on_line = stripped_line[len("VALUE "):].strip()
                      current_constant["value_pseudo_code"] += value_str_on_line + "\n"
                      current_section_type = "constant_value_block" # Transition state
                      current_block_indent = current_indent # Block starts at this indent


             elif stripped_line: # Any other non-empty, non-comment line
                  # Check if this line is part of the current block (pseudo-code or value)
                  if current_section_type in ["method", "function"] and current_method_or_function:
                       # This line is part of the method/function body
                       if current_block_indent == -1: # First line of the block
                           current_block_indent = current_indent
                       # Add line, removing the base indent
                       if current_indent >= current_block_indent:
                            pseudo_code_lines.append(line[current_block_indent:])
                       else:
                            # Indentation decreased, block likely ended implicitly (or syntax error)
                            add_current_block_to(current_method_or_function, "pseudo_code")
                            # This line is not part of the block, re-process it? Or assume structure is clean?
                            # For placeholder, assume structure is clean, this shouldn't happen if block parsing was right.
                            print(f"McpcParser Warning: Unexpected indentation at line {i+1}: {line}")

                  elif current_section_type == "constant_value_block" and current_constant:
                       # This line is part of the constant value definition
                       if current_indent > current_block_indent: # Must be further indented than VALUE line
                            current_block_lines.append(line[current_block_indent:]) # Add line removing block indent
                       else:
                            # Indentation not sufficient or decreased, block ended
                            add_current_block_to(current_constant, "value_pseudo_code")
                            # Re-process this line? Skipping for placeholder.
                            print(f"McpcParser Warning: Unexpected indentation for constant value at line {i+1}: {line}")

                  # Add logic for multi-line DESCRIPTION if implemented...


        # Add any remaining block lines at the end of the file
        if current_method_or_function: add_current_block_to(current_method_or_function, "pseudo_code")
        if current_constant and current_section_type == "constant_value_block": add_current_block_to(current_constant, "value_pseudo_code")


        # This placeholder parser is very simplistic. A real implementation would need
        # robust state tracking based on keywords and indentation, handling multiline
        # descriptions, parameters, and complex pseudo-code structures accurately.
        print("McpcParser: Returning placeholder data.")
        return data


    def generate(self, data: Dict[str, Any]) -> str:
        """
        Generates .mcpc formatted text from structured data.

        Args:
            data: Structured symbol-pseudo code data.

        Returns:
            str: .mcpc formatted text string.
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
             const_value_pseudo_code = const.get("value_pseudo_code", "") # Use value_pseudo_code

             lines.append(f"CONSTANT {const_name}")
             if const_desc:
                 lines.append(f"  DESCRIPTION \"{const_desc}\"")
             if const_value_pseudo_code:
                  lines.append(f"  VALUE") # Indicate start of value block
                  # Add pseudo-code lines, indented consistently relative to VALUE keyword
                  body_lines = const_value_pseudo_code.splitlines()
                  for body_line in body_lines:
                       lines.append(f"    {body_line}") # Indent 4 spaces

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
                # Assuming method["parameters"] is a string from the parse method, use it directly.
                # If it were structured data like [{"name": "p1", "type": "T1"}], format it.
                parameters_str = method.get("parameters", "")
                params_declaration = f"(PARAMETERS {parameters_str})" if parameters_str else "()"

                return_type = method.get("return_type")
                return_str = f" RETURNS {return_type}" if return_type else ""

                lines.append(f"  METHOD {method_name}{params_declaration}{return_str}")
                if method_desc:
                     lines.append(f"    DESCRIPTION \"{method_desc}\"") # Indent 4 spaces

                pseudo_code_body = method.get("pseudo_code", "")
                if pseudo_code_body:
                     # Add pseudo-code lines, indented consistently
                     body_lines = pseudo_code_body.splitlines()
                     for body_line in body_lines:
                          # Simple indentation - does not preserve original pseudo-code indentation
                          lines.append(f"    {body_line}") # Indent 4 spaces

            lines.append("") # Blank line after methods in a class

        functions = data.get("functions", [])
        for func in functions:
             func_name = func.get("name", "unknown_function")
             func_desc = func.get("description")
             # Parameter/Return handling similar to methods
             parameters_str = func.get("parameters", "")
             params_declaration = f"(PARAMETERS {parameters_str})" if parameters_str else "()"

             return_type = func.get("return_type")
             return_str = f" RETURNS {return_type}" if return_type else ""

             lines.append(f"FUNCTION {func_name}{params_declaration}{return_str}")
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
    Parser class for target language source code (e.g., Python .py files).
    Parses source code into structured data and can generate source code from structured data.
    Primarily used for the reverse build process.
    """
    def parse(self, content: str, language: str) -> Dict[str, Any]:
        """
        Parses source code into structured data (classes, functions, variables, etc.) for reverse build.

        Args:
            content: Text content of the source code file.
            language: Target language (e.g., 'python').

        Returns:
            dict: Structured representation of the code data.
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
                            "bases": [ast.unparse(b).strip() for b in node.bases],
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
                                    "return_type": ast.unparse(item.returns).strip() if item.returns else None,
                                    "docstring": ast.get_docstring(item),
                                    "pseudo_code_summary": "..." # Placeholder summary
                                }
                                # Parse function/method arguments
                                for arg in item.args.args:
                                     param_info = {"name": arg.arg, "type": ast.unparse(arg.annotation).strip() if arg.annotation else None}
                                     # Add default value if present
                                     if arg in item.args.defaults:
                                         # Find the index of the arg in args.args and use the corresponding default
                                         arg_index = item.args.args.index(arg)
                                         default_index_in_defaults = arg_index - (len(item.args.args) - len(item.args.defaults))
                                         if default_index_in_defaults >= 0:
                                              param_info["default"] = ast.unparse(item.args.defaults[default_index_in_defaults]).strip()

                                     method_info["parameters"].append(param_info)

                                # Handle *args and kwargs
                                if item.args.vararg:
                                    method_info["parameters"].append({"name": item.args.vararg.arg, "type": "tuple", "is_vararg": True})
                                if item.args.kwarg:
                                     method_info["parameters"].append({"name": item.args.kwarg.arg, "type": "dict", "is_kwarg": True})


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
                            "return_type": ast.unparse(node.returns).strip() if node.returns else None,
                            "docstring": ast.get_docstring(node),
                            "pseudo_code_summary": "..." # Placeholder summary
                        }
                        for arg in node.args.args:
                             param_info = {"name": arg.arg, "type": ast.unparse(arg.annotation).strip() if arg.annotation else None}
                             if arg in item.args.defaults: # Check for default value
                                arg_index = item.args.args.index(arg)
                                default_index_in_defaults = arg_index - (len(item.args.args) - len(item.args.defaults))
                                if default_index_in_defaults >= 0:
                                     param_info["default"] = ast.unparse(item.args.defaults[default_index_in_defaults]).strip()
                             function_info["parameters"].append(param_info)
                        if item.args.vararg: function_info["parameters"].append({"name": item.args.vararg.arg, "type": "tuple", "is_vararg": True})
                        if item.args.kwarg: function_info["parameters"].append({"name": item.args.kwarg.arg, "type": "dict", "is_kwarg": True})

                        data["functions"].append(function_info)

                    elif isinstance(node, ast.Assign):
                        # Simple variable assignments (may need to filter top-level vs class/function level)
                        # This is a basic attempt, need to check context
                        # Check if it's a top-level assignment and target is a simple Name
                        if node.lineno > 0 and not isinstance(node.targets[0], ast.Attribute) and isinstance(node.targets[0], ast.Name):
                             # Crude check if it's at module level (not inside class/function node)
                             # This requires traversing up the AST, which is complex.
                             # Simple heuristic: if parent node is module, it's top-level.
                             # Need to track parent nodes during traversal. Skipping complex scope detection.
                             # For now, just collect top-level assignments assuming simple structure.
                             # A robust parser would need ast.NodeVisitor with stack.

                             # Placeholder: Check if assignee name is all caps as heuristic for constant
                             assigned_name = node.targets[0].id
                             if assigned_name.isupper() and assigned_name.replace('_', '').isalnum():
                                  try:
                                      value_preview = ast.unparse(node.value).strip()
                                  except:
                                      value_preview = "...unparseable value..."

                                  const_info = {
                                      "name": assigned_name,
                                      "type": "constant",
                                      "lineno": node.lineno,
                                      "value_preview": value_preview
                                      # Description would come from nearby comments, which AST doesn't link easily
                                  }
                                  data["constants"].append(const_info)


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
        Generates source code formatted text from structured data, following code standards.

        Args:
            data: Structured code data.
            language: Target language (e.g., 'python').

        Returns:
            str: Generated source code text.
        """
        print(f"TargetCodeParser: Placeholder generate method called for language: {language}.")
        # Logic to generate source code from structured data based on language.
        # For Python, generate code strings from the dictionary representation, adhering to PEP8.
        # Add docstrings, comments, follow naming conventions.
        generated_code = ""

        if language.lower() == "python":
             lines: List[str] = []

             # Add module docstring (if available in data, or from config?)
             module_docstring = data.get("module_docstring", "Generated Python code.")
             if module_docstring:
                 lines.append(f'"""{module_docstring}\n"""')
                 lines.append("")

             # Imports (need to determine based on dependencies in symbol table or inferred?)
             # This is a complex part - dependencies should drive imports.
             # Placeholder: Add necessary imports found in the original generated Python code
             placeholder_imports = [
                 "import os",
                 "import sys",
                 "import json",
                 "from typing import Dict, Any, Optional, List",
                 "from PyQt5.QtWidgets import (QMainWindow, QTreeView, QPushButton, QStatusBar, QComboBox, QVBoxLayout, QHBoxLayout, QWidget, QApplication, QFileSystemModel, QFileDialog, QMessageBox, QLabel, QMenu, QAction, QSizePolicy)",
                 "from PyQt5.QtGui import QIcon",
                 "from PyQt5.QtCore import Qt, QModelIndex, QDir",
                 "from langchain_core.prompts import ChatPromptTemplate, PromptTemplate",
                 "from langchain_core.output_parsers import StrOutputParser",
                 "from langchain_openai import ChatOpenAI",
                 "import pathlib",
                 "import re",
                 "import ast",
                 "# Imports from mccp_toolchain package will be added automatically by split structure",
             ]
             for imp_line in placeholder_imports:
                 if "mccp_toolchain" not in imp_line: # Avoid duplicating relative imports
                     lines.append(imp_line)
             lines.append("")


             # Constants
             constants = data.get("constants", [])
             for const in constants:
                  const_name = const.get("name", "UNKNOWN_CONSTANT")
                  # Use value_preview or a more robust representation
                  const_value_repr = const.get("value_preview", "None")
                  const_desc = const.get("description") # Assuming description is in data (less likely for constants from AST)

                  lines.append(f"{const_name} = {const_value_repr}")
                  if const_desc:
                       lines.append(f'# {const_desc}') # Simple comment
                  lines.append("")


             # Functions
             functions = data.get("functions", [])
             for func in functions:
                  func_name = func.get("name", "unknown_function")
                  func_docstring = func.get("docstring") # Assuming docstring is in data
                  # Reconstruct parameters string from structured parameter data
                  parameters: List[Dict] = func.get("parameters", []) # Assuming list of {"name": "p", "type": "T", "default": "D"}
                  param_strings = []
                  for p in parameters:
                      param_str = p.get("name", "arg")
                      param_type = p.get("type")
                      param_default = p.get("default")
                      is_vararg = p.get("is_vararg", False)
                      is_kwarg = p.get("is_kwarg", False)

                      if is_vararg:
                           param_str = f"*{param_str}"
                      elif is_kwarg:
                           param_str = f"{param_str}"

                      if param_type:
                          param_str += f": {param_type}"
                      if param_default is not None:
                           param_str += f" = {param_default}"

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
                  # This would ideally come from parsing MCPC and translating pseudo_code
                  pseudo_code_summary = func.get("pseudo_code_summary", "# TODO: Implement logic based on pseudo-code")
                  lines.append(f"    {pseudo_code_summary}")
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
                       parameters: List[Dict] = method.get("parameters", []) # Assuming list of {"name": "p", "type": "T", "default": "D", "is_vararg": bool, "is_kwarg": bool}

                       param_strings = []
                       for p in parameters:
                            param_str = p.get("name", "arg")
                            param_type = p.get("type")
                            param_default = p.get("default")
                            is_vararg = p.get("is_vararg", False)
                            is_kwarg = p.get("is_kwarg", False)

                            if is_vararg:
                                 param_str = f"*{param_str}"
                            elif is_kwarg:
                                 param_str = f"{param_str}"

                            if param_type:
                                 param_str += f": {param_type}"
                            if param_default is not None:
                                 param_str += f" = {param_default}"

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
                       # This would ideally come from parsing MCPC and translating pseudo_code
                       pseudo_code_summary = method.get("pseudo_code_summary", "# TODO: Implement logic based on pseudo-code")
                       lines.append(f"        {pseudo_code_summary}")
                       lines.append("        pass # Placeholder")
                       lines.append("") # Blank line after method


                  # If the class is empty or only has methods, add 'pass' or docstring at class level
                  # Check if body is empty after adding docstring/methods
                  # Crude check: len(methods) == 0 and len(attributes) == 0
                  # A real AST parse would give the body nodes
                  # If there are no methods AND no attributes, add pass (assuming __init__ is not generated automatically here)
                  # if not methods and not attributes: # Crude check
                  #      lines.append("    pass") # Or include class docstring if only that exists
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
    General purpose parser class for JSON configuration files.
    """
    def parse(self, content: str) -> Dict[str, Any]:
        """
        Parses JSON text into a Python dictionary.

        Args:
            content: Text content of the JSON file.

        Returns:
            dict: Parsed Python dictionary.

        Raises:
            json.JSONDecodeError: If the content is not valid JSON.
        """
        # Use built-in JSON library.
        print("JsonParser: Parsing JSON content.")
        return json.loads(content)

    def generate(self, data: Dict[str, Any]) -> str:
        """
        Generates formatted JSON text from a Python dictionary.

        Args:
            data: Python dictionary to serialize.

        Returns:
            str: Formatted JSON string.
        """
        # Use built-in JSON library with indentation for readability.
        print("JsonParser: Generating JSON content.")
        return json.dumps(data, indent=2, ensure_ascii=False)
```

文件: `/mccp_toolchain/mccp/symbols.py`
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

# Import MCCP Toolchain Modules (using relative imports)
from .file_manager import FileManager
from .config import ConfigManager
from .parsers import JsonParser # For JsonParser
from ..utils.utils import find_in_list_by_key, FIND_INDEX_OF_DICT_IN_LIST # Assuming utils provides these helpers


class SymbolTableManager:
    """
    Symbol Table Manager class, manages all distributed symbol table files in the project.
    Responsible for loading, saving, finding, and updating symbol definitions.
    """

    def __init__(self, file_manager: FileManager, config_manager: ConfigManager):
        """
        Initializes the Symbol Table Manager, stores dependencies. Symbol loading requires calling load_all_symbol_tables.

        Args:
            file_manager: File Manager instance.
            config_manager: Config Manager instance.
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
        Loads all symbols.json files from the mccp_symbols directory into memory.

        Args:
            project_path: Project root directory.
        """
        self.log_info(f"SymbolTableManager: Loading all symbol tables for project: {project_path}")
        self._symbol_data_map = {} # Clear existing loaded data

        # Get the directory key for symbol tables from config
        # Use get_setting with a default if config hasn't been loaded yet (shouldn't happen if called after load_config)
        symbol_dir_key = self.config_manager.get_setting("symbol_table_root", "mccp_symbols") # Default to 'mccp_symbols'
        symbol_file_extension = ".json" # Standard extension for symbols

        # List all symbol files in the designated directory
        # Assuming symbol files have a naming convention like mccp_symbols_<module_name>.json
        # Let's list all .json files and filter later, or rely on a specific pattern if needed.
        # For now, list all .json files in the directory.
        symbol_file_paths = self.file_manager.list_files_in_layer(project_path, symbol_dir_key, symbol_file_extension)

        if not symbol_file_paths:
             self.log_warning(f"SymbolTableManager: No symbol files found in the '{symbol_dir_key}' directory with extension '{symbol_file_extension}'.")

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
        Saves the current in-memory state of all symbol tables back to their respective JSON files.
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
             # Use file manager's get_file_path which handles joining project_root, dir_key, file_name
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
        Finds a specific symbol across all loaded symbol tables.

        Args:
            symbol_name: The name of the symbol to find.
            module_name: Optional: Restrict the search to a specific module name.

        Returns:
            dict | None: The found symbol data dictionary, or None if not found.
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
        Updates or adds a symbol to the corresponding module symbol table.
        If the symbol already exists and is_frozen is true, the update is rejected.

        Args:
            symbol_data: Dictionary containing the symbol data to update or add (must include 'name' and 'module_name' keys).

        Returns:
            bool: True if the update was successful (including adding a new symbol), False if the update was rejected by the frozen flag.
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
             # Update the existing symbol dictionary with new data, potentially overriding existing values
             module_symbols_list[existing_symbol_index].update(symbol_data)
             # Ensure the final 'is_frozen' status is correctly set (either from new data or preserved existing)
             module_symbols_list[existing_symbol_index]['is_frozen'] = symbol_data.get('is_frozen', is_frozen_status)

             self.log_info(f"SymbolTableManager: Updated symbol: '{symbol_name}' in module '{module_name}'.")

        else:
            # Symbol does not exist, add it
            # Ensure basic structure and default 'is_frozen' if not provided
            # Ensure module_name is correctly set in the symbol data being added
            new_symbol_data = symbol_data.copy() # Avoid modifying the input dict
            new_symbol_data['module_name'] = module_name
            if 'is_frozen' not in new_symbol_data:
                 new_symbol_data['is_frozen'] = False # Default to not frozen
            module_symbols_list.append(new_symbol_data)
            self.log_info(f"SymbolTableManager: Added new symbol: '{symbol_name}' to module '{module_name}'.")

        # The list 'module_symbols_list' is a reference to the list inside _symbol_data_map,
        # so changes are reflected directly. No need to re-assign.

        return True # Update/add successful


    def get_module_symbols(self, module_name: str) -> Dict[str, Any]:
        """
        Retrieves the symbol table data for a specified module.

        Args:
            module_name: Module name.

        Returns:
            dict: Dictionary containing the symbol table data for the specified module. Returns an empty structure if the module is not found.
        """
        # Return the data for the specified module, or an empty structure if not found
        # Ensure the returned structure includes the 'symbols' list key for consistency
        return self._symbol_data_map.get(module_name, {"module_name": module_name, "description": f"Symbols for {module_name} (not loaded/found).", "symbols": []})

    def get_all_symbols(self) -> Dict[str, Dict]:
        """
        Retrieves symbol table data for all loaded modules.

        Returns:
            dict: Dictionary containing symbol table data for all modules.
        """
        # Return a copy of the internal map to prevent external modification
        return self._symbol_data_map.copy()


    def derive_symbol_file_name(self, module_name: str) -> str:
       """
       Generates the corresponding symbols.json file name based on the module name.
       Format: mccp_symbols_<module_name_snake_case>.json

       Args:
           module_name: Module name (e.g., 'mccp_toolchain.ui').

       Returns:
           str: The generated symbols.json file name (e.g., 'mccp_symbols_mccp_toolchain_ui.json').
       """
       # Replace dots with underscores, prepend "mccp_symbols_", append ".json"
       # Use snake_case conversion if module_name might not be in perfect snake_case?
       # Assuming module_name from the symbol table is the canonical name.
       # Let's just replace dots with underscores.
       filename_base = module_name.replace(".", "_")
       return f"mccp_symbols_{filename_base}.json"

```

文件: `/mccp_toolchain/ui/__init__.py`
```python
# This file makes the 'ui' directory a Python package.
```

文件: `/mccp_toolchain/ui/main_window.py`
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

# Import MCCP Toolchain Modules (using relative imports)
from ..mccp.config import ConfigManager
from ..mccp.file_manager import FileManager, get_project_root_from_path # get_project_root_from_path is a standalone function
from ..core.build import BuildOrchestrator, BUILD_LAYERS # Import constants and orchestrator
from ..mccp.symbols import SymbolTableManager


class MainWindow(QMainWindow):
    """
    Main window class, inherits from PyQt's QMainWindow, contains file tree view, buttons, status bar, etc.
    """

    def __init__(
        self,
        config_manager: ConfigManager,
        file_manager: FileManager,
        build_orchestrator: BuildOrchestrator,
        symbol_manager: SymbolTableManager
    ):
        """
        Initializes the main window, sets up layout and connects signals/slots.

        Args:
            config_manager: Config Manager instance.
            file_manager: File Manager instance.
            build_orchestrator: Build Orchestrator instance.
            symbol_manager: Symbol Table Manager instance.
        """
        super().__init__()

        # Store injected dependency services
        self.config_manager: ConfigManager = config_manager
        self.file_manager: FileManager = file_manager
        self.build_orchestrator: BuildOrchestrator = build_orchestrator
        self.symbol_manager: SymbolTableManager = symbol_manager

        # Store current project root directory
        self._current_project_root: Optional[str] = None

        # Set window properties
        self.setWindowTitle("MCCP Toolchain")
        self.setGeometry(100, 100, 800, 600)

        # Build UI elements and layout
        self.setup_ui()

        # Connect signals to slots
        self.connect_signals()

        # Set initial status bar message
        self.log_message("MCCP Toolchain ready.")

    def setup_ui(self) -> None:
        """
        Builds the user interface elements such as the file tree view, menu bar, toolbars, and status bar.
        """
        # Create central widget and main layout
        central_widget = QWidget()
        main_layout = QVBoxLayout(central_widget)
        self.setCentralWidget(central_widget)

        # Create file tree view
        self.file_tree_view = QTreeView()
        self.file_tree_view.setHeaderHidden(True) # Hide headers like Name, Size, Type, Date Modified
        self.file_tree_view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        main_layout.addWidget(self.file_tree_view)

        # Create button layout
        button_layout = QHBoxLayout()
        self.new_project_button = QPushButton("新建项目")
        self.open_project_button = QPushButton("打开项目")
        self.run_build_button = QPushButton("运行构建 (正向)")
        self.run_reverse_build_button = QPushButton("运行构建 (反向)") # Added reverse build button
        self.build_target_selector = QComboBox() # For selecting target layer
        # Populate build target layer options (get from BUILD_LAYERS constant)
        # Assume starting from behavior_code, so possible targets are mcpc, target_code
        # BUILD_LAYERS = ["requirements", "behavior_code", "pseudo_code", "target_code"]
        try:
            mcbc_index = BUILD_LAYERS.index("behavior_code")
            build_targets = BUILD_LAYERS[mcbc_index + 1:] # Start from the layer after mcbc
            self.build_target_selector.addItems(build_targets)
        except ValueError:
            self.log_warning("Build layers constant missing 'behavior_code'. Build target selector will be empty.")


        button_layout.addWidget(self.new_project_button)
        button_layout.addWidget(self.open_project_button)
        button_layout.addStretch(1) # Add stretchable space
        button_layout.addWidget(QLabel("目标层级:"))
        button_layout.addWidget(self.build_target_selector)
        button_layout.addWidget(self.run_build_button)
        button_layout.addWidget(self.run_reverse_build_button)

        main_layout.addLayout(button_layout)

        # Create status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

    def connect_signals(self) -> None:
        """
        Connects signals from UI elements (e.g., buttons, menu items) to slot methods.
        """
        # Connect button click signals to handlers
        self.new_project_button.clicked.connect(self.handle_new_project)
        self.open_project_button.clicked.connect(self.handle_open_project)
        # Pass the selected target layer when the build button is clicked
        self.run_build_button.clicked.connect(
            lambda: self.handle_run_build(self.build_target_selector.currentText())
        )
        # Reverse build handler (currently frozen)
        self.run_reverse_build_button.clicked.connect(self.handle_run_reverse_build_placeholder)

        # Connect file tree view signals (e.g., file selection event)
        # self.file_tree_view.clicked.connect(self.handle_file_selected) # Example: single click
        # self.file_tree_view.doubleClicked.connect(self.handle_file_double_clicked) # Example: double click to open file

        # Connect build target selector signal (optional, if UI or status needs to refresh based on selection)
        # self.build_target_selector.currentTextChanged.connect(self.handle_build_target_changed) # Example

    def handle_run_reverse_build_placeholder(self) -> None:
        """Placeholder handler for the reverse build button."""
        QMessageBox.information(self, "功能待实现", "反向构建功能目前尚未完全实现。")
        self.log_message("Reverse build function is not yet fully implemented.")


    def update_file_tree(self, project_root: str) -> None:
        """
        Refreshes the file structure tree view to display project files and directories.

        Args:
            project_root: Project root directory path.
        """
        # Use QFileSystemModel to represent the file system
        model = QFileSystemModel()
        # Set filters to show relevant MCCP files and directories, or show all initially
        # model.setFilter(QDir.NoDotAndDotDot | QDir.AllDirs | QDir.Files)
        # model.setNameFilters(["*.md", "*.mcbc", "*.mcpc", "*.py", "*.json"]) # Example filter
        # model.setNameFilterDisables(False)

        model.setRootPath(project_root)
        self.file_tree_view.setModel(model)
        # Set the root index of the tree view to the project root directory
        self.file_tree_view.setRootIndex(model.index(project_root))
        # Auto-expand some important directories, e.g., src_mcbc, src_mcpc, mccp_symbols, config, requirements
        self._expand_important_dirs(model, project_root)

    def _expand_important_dirs(self, model: QFileSystemModel, root_path: str) -> None:
        """Helper to expand key MCCP directories."""
        # Get directory names from config if config is loaded, otherwise use standard defaults
        important_dir_keys = ["requirements_dir", "behavior_code_dir", "pseudo_code_dir", "symbol_table_root", "config_dir", "target_code_dir"]
        important_dirs = []
        if self.config_manager and self.config_manager.get_config_data():
             for key in important_dir_keys:
                  dir_name = self.config_manager.get_layer_dir(key)
                  if dir_name and dir_name != ".": # Don't try to expand '.'
                       important_dirs.append(dir_name)
        else:
             # Fallback to standard default names if config isn't loaded
             important_dirs = ["requirements", "src_mcbc", "src_mcpc", "mccp_symbols", "config", "src_target"]


        for dir_name in important_dirs:
            dir_path = os.path.join(root_path, dir_name)
            if os.path.isdir(dir_path):
                index = model.index(dir_path)
                if index.isValid():
                    self.file_tree_view.expand(index)

    def log_message(self, message: str) -> None:
        """
        Displays information in the status bar.

        Args:
            message: The message string to display.
        """
        print(f"LOG: {message}") # Also print to console for debugging
        self.status_bar.showMessage(message)

    def handle_new_project(self) -> None:
        """
        Handles the user operation to create a new project.
        Prompts for project path, calls FileManager to create structure.
        """
        # Prompt user to select project directory
        project_path = QFileDialog.getExistingDirectory(
            self, "选择新项目目录", os.path.expanduser("~")
        )

        if project_path:
            self.log_message(f"尝试在 {project_path} 创建新项目...")
            # The actual creation logic should be in FileManager, call it here
            # Assume create_project_structure includes creating config file and requirements.md
            # and if successful, the project can be considered existing and opened.
            try:
                success = self.file_manager.create_project_structure(project_path)
                if success:
                    self.log_message(f"项目在 {project_path} 创建成功。")
                    # Upon successful creation, automatically open this new project
                    self.open_project(project_path)
                else:
                    self.log_message(f"在 {project_path} 创建项目失败。")
                    QMessageBox.warning(self, "创建失败", f"无法在 {project_path} 创建项目结构。")
            except Exception as e:
                 self.log_message(f"创建项目过程中发生错误: {e}")
                 QMessageBox.critical(self, "创建错误", f"创建项目过程中发生错误: {e}")


    def handle_open_project(self) -> None:
        """
        Handles the user operation to open an existing project.
        Presents a file dialog to select the project directory, then calls open_project to load and update the file tree.
        """
        # Prompt user to select project directory (MCCP project root directory)
        selected_path = QFileDialog.getExistingDirectory(
            self, "选择 MCCP 项目根目录或子目录", os.path.expanduser("~")
        )

        if selected_path:
            # Attempt to load and open the project
            self.open_project(selected_path)

    def open_project(self, path: str) -> None:
        """
        Loads and displays an existing project (config, symbol tables) and updates the UI.

        Args:
            path: The path selected by the user, which might be the project root or a subdirectory within it.
        """
        # Try to find the project root directory (by searching for mccp_config.json)
        project_root = get_project_root_from_path(path) # Use the standalone function

        if project_root:
            self.log_message(f"正在打开项目: {project_root}...")
            try:
                # Load configuration first, as it's needed by other managers
                if not self.config_manager.load_config(project_root):
                    # load_config already logs error, just raise exception to stop
                    raise Exception("配置加载失败。")

                # Load symbol tables using the configured symbol directory
                self.symbol_manager.load_all_symbol_tables(project_root)
                self._current_project_root = project_root # Store the current project root

                # Update the file tree
                self.update_file_tree(project_root)

                self.log_message(f"项目 {project_root} 加载成功。")

            except Exception as e:
                self.log_message(f"加载项目时发生错误: {e}")
                QMessageBox.critical(self, "加载项目失败", f"无法加载项目 {project_root}: {e}\n请确保这是一个有效的MCCP项目目录，且包含 mccp_config.json 文件。")
                self._current_project_root = None # Reset project root on failure
                self.update_file_tree("") # Clear file tree on failure

        else:
            self.log_message(f"在 {path} 或其父目录中未找到 MCCP 项目配置文件 (mccp_config.json)。")
            QMessageBox.warning(self, "不是 MCCP 项目", f"在 {path} 或其父目录中未找到有效的 MCCP 项目配置文件 (mccp_config.json)。")
            self._current_project_root = None # Reset project root
            self.update_file_tree("") # Clear file tree


    def handle_run_build(self, target_layer: str) -> None:
        """
        Handles the user operation to trigger the forward build process, calls BuildOrchestrator.

        Args:
            target_layer: The key of the target layer for the build (e.g., 'mcpc', 'target_code').
        """
        project_root = self._current_project_root # Get the currently loaded project root

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
            # Call the build orchestrator
            success = self.build_orchestrator.run_forward_build(
                project_root, start_layer, target_layer
            )

            if success:
                self.log_message("正向构建流程完成成功。")
                # Refresh file tree, as new files might have been generated
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
    #     """Handles event when a file is selected in the file tree."""
    #     model = self.file_tree_view.model() # type: QFileSystemModel
    #     file_path = model.filePath(index)
    #     if os.path.isfile(file_path):
    #         self.log_message(f"Selected file: {file_path}")
    #         # Optionally, open the file in an external editor or integrated view
    #         # self.open_file_in_editor(file_path) # Needs implementation

    # Example handler for file tree item double click (optional)
    # def handle_file_double_clicked(self, index: QModelIndex) -> None:
    #      """Handles event when a file is double-clicked in the file tree."""
    #      model = self.file_tree_view.model() # type: QFileSystemModel
    #      file_path = model.filePath(index)
    #      if os.path.isfile(file_path):
    #           print(f"Double-clicked file: {file_path}")
    #           # Implement logic to open the file, e.g., in a text editor window
    #           pass # Placeholder

```

文件: `/mccp_toolchain/utils/__init__.py`
```python
# This file makes the 'utils' directory a Python package.
```

文件: `/mccp_toolchain/utils/utils.py`
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

# No external MCCP dependencies needed within these functions


def normalize_path(path: str) -> str:
    """
    Normalizes a file path, handling slashes, relative paths, etc.

    Args:
        path: The path string to normalize.

    Returns:
        str: The normalized file path string.
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
    Validates if a file name string conforms to a naming convention (snake_case).

    Args:
        file_name: The file name string to validate.

    Returns:
        bool: True if the file name conforms to the convention, False otherwise.
    """
    # Use regular expression to check for snake_case pattern
    # Pattern explanation:
    # ^           - Start of string
    # [a-z0-9_]+  - One or more lowercase letters, numbers, or underscores (for the base name)
    # \.          - A literal dot (for the extension separator)
    # [a-z]+      - One or more lowercase letters (for the extension)
    # $           - End of string
    # This is a strict snake_case for the base name, followed by a dot and lowercase extension.
    # Note: This validates the file *name*, not the path.
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
    Converts a snake_case string to PascalCase.

    Args:
        text: The snake_case string.

    Returns:
        str: The PascalCase string.
    """
    # Split the text by underscore, capitalize the first letter of each part, and join.
    parts = text.split("_")
    pascal_parts = [part.capitalize() for part in parts if part] # Ensure part is not empty
    return "".join(pascal_parts)

def pascal_to_snake_case(text: str) -> str:
    """
    Converts a PascalCase string to snake_case.

    Args:
        text: The PascalCase string.

    Returns:
        str: The snake_case string.
    """
    # Use regex to insert underscore before uppercase letters (except the first) and convert to lowercase.
    # s1: Find sequence of a non-uppercase char followed by an uppercase char (or an uppercase followed by lowercase) and insert underscore.
    # s2: Convert the result to lowercase.
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', text)
    s2 = re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()
    return s2

def find_in_list_by_key(list_data: List[Dict], key_name: str, key_value: Any) -> Optional[Dict]:
   """
   Finds the first dictionary in a list of dictionaries where a specific key matches a value.

   Args:
       list_data: The list of dictionaries to search.
       key_name: The key name to match.
       key_value: The value to match against the key.

   Returns:
       dict | None: The first matching dictionary found, or None if not found.
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
   Finds the index of the first dictionary in a list of dictionaries where a specific key matches a value.

   Args:
       list_data: The list of dictionaries to search.
       key_name: The key name to match.
       key_value: The value to match against the key.

   Returns:
       int | None: The index of the first matching dictionary found, or None if not found.
   """
   if not isinstance(list_data, list):
        # print(f"Utils: FIND_INDEX_OF_DICT_IN_LIST requires a list, got {type(list_data)}") # Verbose
        return None

   for index, item in enumerate(list_data):
      if isinstance(item, dict) and item.get(key_name) == key_value:
         return index
   return None
```

文件: `/requirements/requirements.md`
```markdown
# Software Requirements Document - `mccp-toolchain`

1. 项目愿景

`mccp-toolchain` 项目的核心目标是构建一个实用的、开源的工具集，将 MCCP（Model Context Code Protocol）理论转化为赋能开发者的高效工作流。该工具旨在成为连接人类需求、大语言模型（LLM）与传统编程代码的“超级中间件”，核心价值在于实现基于 LLM 的可控化、精确化、可信化软件开发过程。通过提供结构化的层级转换能力和符号管理, `mccp-toolchain` 将降低 LLM 在代码生成中的不确定性，提高开发效率，并促进标准化、模块化的工程实践。

2. 核心功能需求

该工具链需要支持 MCCP 协议定义的核心开发流程和文件管理。

2.1. 正向构建流程

实现从高层级抽象向低层级具象的代码生成工作流。

*   SR.Func.Build.Forward.1: 支持解析项目中的 `requirements.md` 文件，提取自然语言需求。
*   SR.Func.Build.Forward.2: 支持基于 `requirements.md` 内容，通过 LLM 引导，生成或更新对应的行为描述文件 (`src_mcbc/*.mcbc`)。生成过程中需参考 `mccp_config.json` 中的文件系统映射规则。
*   SR.Func.Build.Forward.3: 支持解析行为描述文件 (`.mcbc`)，提取结构化的行为定义（函数、输入、输出、行为描述）。
*   SR.Func.Build.Forward.4: 支持基于 `.mcbc` 内容和分布式符号表 (`mccp_symbols_*.json`)，通过 LLM 引导，生成或更新对应的符号-伪代码文件 (`src_mcpc/*.mcpc`)。生成过程中需参考 `mccp_config.json` 中的文件系统映射和命名规则，并同步更新相关的符号表文件。
*   SR.Func.Build.Forward.5: 支持解析符号-伪代码文件 (`.mcpc`)，提取接近代码结构的伪代码定义。
*   SR.Func.Build.Forward.6: 支持基于 `.mcpc` 内容和分布式符号表，通过 LLM 引导，生成或更新对应目标语言（由 `mccp_config.json` 指定，如 Python）的源代码文件 (`src_target/*`)。生成过程中需严格遵循目标语言的代码规范（参见非功能性需求 SR.NonFunc.CodeStd.1）和 `mccp_config.json` 中的配置（如文件映射、是否添加额外后缀 `is_extra_suffix`）。
*   SR.Func.Build.Forward.7: 在每个层级转换步骤中，能够将当前层级内容、目标层级结构要求、相关的分布式符号表信息以及 `mccp_config.json` 配置，作为上下文提供给 LLM 进行处理。

2.2. 反向构建流程

实现从现有代码向更高层级抽象的逆向工程能力。这是一个高优先级待实现功能（参考文档描述）。

*   SR.Func.Build.Reverse.1: 支持解析目标语言源代码文件 (`src_target/*`)，提取代码结构（函数、类、变量等）。
*   SR.Func.Build.Reverse.2: 支持基于源代码结构，通过 LLM 引导，生成或更新对应的符号-伪代码文件 (`src_mcpc/*.mcpc`)，并同步更新相关的分布式符号表。
*   SR.Func.Build.Reverse.3: 支持基于符号-伪代码文件 (`.mcpc`)，通过 LLM 引导，生成或更新对应的行为描述文件 (`src_mcbc/*.mcbc`)。
*   SR.Func.Build.Reverse.4: 支持将反向构建过程中提取的关键信息（如函数功能、模块职责）提炼并用于更新 `requirements.md` 或生成摘要。

2.3. LLM 集成

与大语言模型进行交互，驱动层级转换。

*   SR.Func.LLM.1: 使用 Langchain 框架作为与 LLM 交互的主要工具层。
*   SR.Func.LLM.2: 设计并实现一套层次化的、结构清晰的提示词体系，用于精确指导 LLM 完成各层级文件（`.md`, `.mcbc`, `.mcpc`, 目标代码）之间的内容生成、转换和同步。提示词应包含足够的上下文信息，包括但不限于：
    *   源文件内容。
    *   目标层级的文件结构和语法要求。
    *   相关的 `mccp_config.json` 配置。
    *   相关的分布式符号表 (`mccp_symbols_*.json`) 内容，特别是符号定义、依赖关系和 `is_frozen` 标记。
    *   期望的输出格式和结构。
*   SR.Func.LLM.3: 支持配置不同的 LLM 模型（通过 `mccp_config.json` 中的 `llmModel`）。
*   SR.Func.LLM.4: 支持配置 LLM 访问参数，如 API 地址 (`api-url`) 和 API 密钥 (`api-key`)。
*   SR.Func.LLM.5: 能够处理 LLM 的响应，解析生成的文本，并将其格式化为对应的 MCCP 文件或目标代码文件。

2.4. 文件管理

管理 MCCP 项目中的各类文件。

*   SR.Func.File.1: 能够创建一个符合 MCCP 规范的新项目结构，包括创建标准目录 (`config`, `src_mcbc`, `src_mcpc`, `src_target`, `temp`) 和初始化核心配置文件 (`mccp_config.json`, `mccp_compatibility.json`)。
*   SR.Func.File.2: 能够读取和解析 MCCP 项目中的关键文件：`mccp_config.json`, `mccp_compatibility.json`, `mccp_symbols_*.json`, `requirements.md`, `.mcbc` 文件, `.mcpc` 文件, 目标语言源代码文件。
*   SR.Func.File.3: 能够根据 LLM 输出或其他工具链操作，更新和写入上述各类文件，同时遵循 `mccp_config.json` 中定义的文件系统映射和命名规则。
*   SR.Func.File.4: 能够管理分布式符号表文件 (`mccp_symbols_*.json`) 的创建、更新、合并和查找，确保符号的一致性和依赖关系的正确记录。在生成或修改代码时，严格依据符号表中的 `is_frozen` 标记决定是否修改特定符号或文件。

3. 用户界面 (UI) 需求

提供一个直观易用的图形用户界面。

*   SR.UI.1: 使用 PyQt 框架开发 GUI。
*   SR.UI.2: UI 主界面应包含一个文件结构树视图，清晰展示当前打开的 MCCP 项目的文件和目录结构，特别是 `config`, `src_mcbc`, `src_mcpc`, `src_target` 目录及其内容。
*   SR.UI.3: 提供明确的按钮或菜单项来触发核心功能：
    *   创建新项目。
    *   打开现有项目。
    *   触发正向构建流程（可选择构建到特定层级，例如 `.md` -> `.mcbc`，或 `.mcbc` -> `.mcpc`，或 `.mcpc` -> 目标代码，或完整流程）。
    *   触发反向构建流程（待实现）。
    *   刷新文件结构树。
    *   打开项目配置文件 (`mccp_config.json`) 进行编辑。
*   SR.UI.4: 提供一个状态栏或文本区域，用于实时反馈当前任务的执行进度、日志信息、LLM 调用状态以及任何错误或警告信息。

4. 非功能性需求

保障工具链本身的质量和可维护性。

*   SR.NonFunc.Modularity.1: `mccp-toolchain` 项目的代码结构应高度模块化。核心逻辑组件，例如：
    *   MCCP 文件解析器（`.md`, `.mcbc`, `.mcpc`, `.json`）
    *   符号表管理器
    *   LLM 交互模块（Langchain 封装）
    *   提示词生成器
    *   目标代码生成器（例如，针对 Python 的生成逻辑）
    *   文件系统操作模块
    都应设计为相对独立的单元。
*   SR.NonFunc.Modularity.2: 每个核心逻辑模块应具备可独立运行和测试的能力（单元测试），以减少模块间的耦合，提高代码质量和可维护性。
*   SR.NonFunc.CodeStd.1: `mccp-toolchain` 通过 LLM 生成的目标语言代码（例如 Python 代码）必须严格遵循该语言的官方或普遍接受的代码规范（例如 Python 的 PEP8），代码应简洁、逻辑清晰，并包含准确的 Docstring 和必要的行内注释。
*   SR.NonFunc.MCCPComp.1: `mccp-toolchain` 项目本身应作为一个 MCCP 协议的最佳实践范例。其自身的项目结构和开发过程应尽量符合 MCCP 协议规范进行组织和管理。
```

文件: `/requirements.txt`
```
PyQt5
langchain
langchain-openai
```

文件: `/src_mcbc/config.mcbc`
```markdown
# MCCP Behavior Code

## Module: mccp_toolchain.mccp.config

### Overview
- Purpose: Manage the project's configuration data loaded from `mccp_config.json`, providing centralized access to settings that control the toolchain's behavior.
- Responsibilities:
    - Load the configuration file from the project directory.
    - Parse the JSON content into a usable data structure.
    - Provide methods to retrieve specific configuration settings based on keys.
    - Offer helper methods to access frequently used configuration parts, such as layer directories or build rules.
- Interactions: Interacts with `mccp.file_manager` to read the configuration file and `mccp.parsers.JsonParser` to process its content. Used by virtually all other modules that need to access project-specific or toolchain-wide settings.

### Components

#### Class: ConfigManager
- Description: A service class responsible for loading, holding, and providing access to the project's configuration data defined in `mccp_config.json`.
- Behaviors:
    - Initialization (`__init__`):
        - Purpose: Prepare the config manager by providing it with the necessary file handling service.
        - Process: Accepts an instance of the file manager, which will be used internally to read the configuration file. Initializes an internal structure to hold the loaded configuration data (initially empty).
        - Dependencies: Requires an instance of `mccp_toolchain.mccp.file_manager.FileManager`.
    - Load Config (`load_config`):
        - Purpose: Read the `mccp_config.json` file from the specified project directory and parse its content.
        - Process: Constructs the full path to `mccp_config.json` within the `project_path`. Uses the file manager to read the file content. Uses a JSON parser to convert the file content string into a Python dictionary or equivalent structure. Stores this structure internally for subsequent access. Handles errors if the file is not found or is invalid JSON.
        - Input: The root path of the project (`project_path`).
        - Output: A boolean indicating whether the configuration was loaded successfully.
        - Dependencies: Uses `mccp_toolchain.mccp.file_manager.FileManager` to read the file and `mccp_toolchain.mccp.parsers.JsonParser` to parse the JSON.
    - Get Setting (`get_setting`):
        - Purpose: Retrieve a specific configuration value from the loaded configuration data structure using a dot-separated key path.
        - Process: Takes a `key` string (e.g., 'llm_settings.model'). Navigates through the internal configuration data structure using the parts of the key path to find the requested value. Handles cases where the key or intermediate paths do not exist.
        - Input: The dot-separated string path to the desired setting (`key`).
        - Output: The value associated with the key, or potentially `None` or a default if not found (behavior TBD). The return type is flexible (`any`) as configuration values can be strings, numbers, booleans, lists, or dictionaries.
    - Get Layer Dir (`get_layer_dir`):
        - Purpose: Retrieve the directory name corresponding to a specific MCCP layer type as defined in the configuration.
        - Process: Looks up the provided `layer_key` (e.g., 'behavior_code_dir') within the 'layer_mapping' section of the loaded configuration data.
        - Input: The key identifying the layer mapping (`layer_key`).
        - Output: The string name of the directory associated with that layer.
    - Get Build Rule (`get_build_rule`):
        - Purpose: Retrieve the complete configuration dictionary for a specific build or reverse build rule.
        - Process: Looks up the provided `rule_key` (e.g., 'mcbc_to_mcpc') within the 'build_rules' or 'reverse_build_rules' sections of the loaded configuration data.
        - Input: The key identifying the desired build rule (`rule_key`).
        - Output: A dictionary containing the detailed configuration for that rule (e.g., input/output extensions, LLM prompt template).
    - Get Config Data (`get_config_data`):
       - Purpose: Retrieve the complete loaded configuration data dictionary.
       - Process: Returns a copy of the internal configuration dictionary.
       - Output: A dictionary representing the entire configuration.
    - Get Project Root (`get_project_root`):
        - Purpose: Retrieve the path of the currently loaded project's root directory.
        - Process: Returns the stored project root path.
        - Output: The project root path string, or None if no project is loaded.
    - Get Default Config Json (`get_default_config_json`):
       - Purpose: Provide a default configuration dictionary for new project creation.
       - Process: Returns a predefined dictionary structure representing the default `mccp_config.json`.
       - Output: A default configuration dictionary.

```

文件: `/src_mcbc/build.mcbc`
```markdown
# MCCP Behavior Code

## Module: mccp_toolchain.core.build

### Overview
- Purpose: Manage and orchestrate the core transformation processes within the MCCP toolchain, facilitating the flow of information and code generation between different architectural layers.
- Responsibilities:
    - Define and manage the steps involved in the forward build process (requirements -> behavior -> pseudo -> target code).
    - Define and manage the steps involved in the reverse build process (target code -> pseudo -> behavior -> requirements).
    - Coordinate the use of various services (file manager, symbol manager, configuration manager, LLM client, parsers) for each transformation step.
    - Execute layer-specific transformations.
- Interactions: Heavily interacts with `mccp.config` for build rules and layer mappings, `mccp.file_manager` for file access, `mccp.symbols` for symbol management, `core.llm` for AI-driven transformations, and `mccp.parsers` for content parsing and generation.

### Components

#### Class: BuildOrchestrator
- Description: Acts as the central controller for build operations. It defines the sequence of transformations required to move from one layer to another and ensures that each step is executed correctly, coordinating the activities of other modules.
- Behaviors:
    - Initialization (`__init__`):
        - Purpose: Configure the orchestrator with access to all necessary services required to perform build steps.
        - Process: Accepts instances of core managers and clients (config, file, symbol, LLM) and a collection of parser instances. Stores these references for later use in coordinating build tasks.
        - Dependencies: Requires instances of `mccp_toolchain.mccp.config.ConfigManager`, `mccp_toolchain.mccp.file_manager.FileManager`, `mccp_toolchain.mccp.symbols.SymbolTableManager`, `mccp_toolchain.core.llm.LLMClient`, and a collection of `mccp_toolchain.mccp.parsers` instances.
    - Run Forward Build (`run_forward_build`):
        - Purpose: Execute the structured sequence of transformations from a higher-level layer to a lower-level layer, typically starting from requirements or behavior code and moving towards target code.
        - Process: Determines the necessary intermediate steps based on the specified start and end layers and the configured build rules. For each step (e.g., `.mcbc` to `.mcpc`), it identifies the relevant input files, output files, build rule, and necessary services (parsers, LLM). It then delegates the actual transformation for each file to a `LayerTransformer` instance. Manages the overall flow, including loading/saving symbols and configuration as needed between steps. Reports success or failure of the overall process.
        - Input: Project root path (`project_path`), the starting layer identifier (`start_layer_key`), and the ending layer identifier (`end_layer_key`).
        - Output: A boolean indicating whether the build process completed successfully.
        - Interactions: Coordinates multiple calls to `mccp_toolchain.core.build.LayerTransformer` and potentially file/symbol management operations.
    - Run Reverse Build (`run_reverse_build`):
        - Purpose: Execute the sequence of transformations from a lower-level layer to a higher-level layer, typically starting from target code and moving towards behavior code or requirements. (Note: Marked as frozen/pending implementation in symbols).
        - Process: (Planned) Similar to forward build, but follows the reverse sequence of layers. Identifies necessary steps (e.g., target code to `.mcpc`, `.mcpc` to `.mcbc`). Delegates transformations to `LayerTransformer` instances. Coordinates file and symbol management updates based on reverse engineering insights. Reports success or failure.
        - Input: Project root path (`project_path`), the starting layer identifier (`start_layer`), and the ending layer identifier (`end_layer`).
        - Output: A boolean indicating whether the reverse build process completed successfully (when implemented).
        - Interactions: (Planned) Coordinates calls to `mccp_toolchain.core.build.LayerTransformer` and file/symbol management operations, focusing on extracting structure and meaning.
    - Get Rule Key (`get_rule_key`):
       - Purpose: Find the matching build rule key based on source layer, target layer, and direction.
       - Process: Looks up rules in config based on input/output layer mapping keys. Handles forward and reverse rules.
       - Input: Source layer key (`source_layer_key`), target layer key (`target_layer_key`), direction (`direction`).
       - Output: Matching rule key string, or None if not found.
       - Dependencies: Relies on `mccp_toolchain.mccp.config.ConfigManager`.
    - Derive Target File Name (`derive_target_file_name`):
       - Purpose: Generate the target file name based on the source file name and target extension, often preserving the base name.
       - Process: Takes the source file path, removes its extension, and adds the target extension. May have special handling for initial steps (e.g., requirements.md to a specific mcbc file).
       - Input: Source file path (`source_file_path`), source extension (`source_ext`), target extension (`target_ext`).
       - Output: Target file name string.

#### Class: LayerTransformer
- Description: Performs the concrete task of transforming content from a single source file in one layer to a target file in another layer, typically involving an LLM call.
- Behaviors:
    - Initialization (`__init__`):
        - Purpose: Set up the transformer with the specific services and parsers needed for a particular layer-to-layer conversion.
        - Process: Accepts instances of the config, file, symbol, and LLM clients, along with specific parsers for the source and target file formats. Stores these references.
        - Dependencies: Requires instances of `mccp_toolchain.mccp.config.ConfigManager`, `mccp_toolchain.mccp.file_manager.FileManager`, `mccp_toolchain.mccp.symbols.SymbolTableManager`, `mccp_toolchain.core.llm.LLMClient`, and appropriate parser instances (from `mccp_toolchain.mccp.parsers`).
    - Transform (`transform`):
        - Purpose: Execute the complete process of reading a source file, preparing context, invoking the LLM for transformation, processing the LLM's response, potentially updating symbols, and writing the result to a target file.
        - Process: Reads the `source_file_path` using the file manager. Uses the configured build rule key to get LLM prompt instructions, input/output formats, etc. from the config manager. Retrieves relevant symbol data from the symbol manager. Constructs a detailed prompt including source content, symbols, config, and formatting requirements. Calls the LLM client's `generate_content` method with the prompt and context. Receives and potentially parses the LLM response. Updates the symbol table manager based on changes requested by the LLM or inferred from the generated content (respecting `is_frozen`). Writes the generated content to the `target_file_path` using the file manager. Reports success or failure of the transformation.
        - Input: Paths for the source file (`source_file_path`) and target file (`target_file_path`), and a key identifying the specific build rule from the configuration (`build_rule_key`).
        - Output: A boolean indicating whether the transformation was successful.
        - Interactions: Orchestrates calls to `file_manager` (read/write), `config_manager` (get rules), `symbol_manager` (get/update symbols), `llm_client` (generate/parse), and potentially `parsers` (for source/target content processing).

### Constants

#### Constant: BUILD_LAYERS
- Description: Defines the sequence and mapping of the distinct architectural layers recognized by the build system (e.g., requirements, behavior code, pseudo code, target code).
- Usage: Used by the `BuildOrchestrator` to understand the flow and identify intermediate steps during forward and reverse builds.
- Relation: Directly corresponds to the `layer_mapping` section in `mccp_config.json`.

#### Constant: BUILD_RULES
- Description: Defines the keys used to identify specific transformation rules within the configuration (e.g., `md_to_mcbc`, `mcbc_to_mcpc`, `mcpc_to_py`).
- Usage: Used by the `BuildOrchestrator` and `LayerTransformer` to look up the correct prompts, input/output extensions, and other settings for a given transformation step from the `mccp_config.json`.
- Relation: Directly corresponds to the keys within the `build_rules` and `reverse_build_rules` sections in `mccp_config.json`.
```

文件: `/src_mcbc/file_manager.mcbc`
```markdown
# MCCP Behavior Code

## Module: mccp_toolchain.mccp.file_manager

### Overview
- Purpose: Abstract and manage all file system interactions within the MCCP toolchain, ensuring consistent and reliable access to project files and directories according to MCCP structure and configuration.
- Responsibilities:
    - Create the standard MCCP project directory structure.
    - Read content from specific files.
    - Write content to specific files, creating parent directories if necessary.
    - Determine file paths based on project root, layer mapping, and file names.
    - List files within specific project layers.
    - Identify the project root directory from any path within the project.
- Interactions: Heavily relies on `mccp.config` to understand project structure and layer mappings. Used by almost all other modules that need to access or manage files, particularly `core.build`, `mccp.symbols`, and `mccp.config`. Utilizes standard operating system libraries for file operations.

### Components

#### Class: FileManager
- Description: A service class providing high-level functions for managing project files and directories, based on the configured MCCP project structure.
- Behaviors:
    - Initialization (`__init__`):
        - Purpose: Prepare the file manager by giving it access to the project's configuration.
        - Process: Stores a reference to the configuration manager, which contains essential information about directory names for different layers. Initializes underlying file system interaction libraries if needed.
        - Dependencies: Requires an instance of `mccp_toolchain.mccp.config.ConfigManager` and utilizes standard OS libraries (`os`, `pathlib`).
    - Create Project Structure (`create_project_structure`):
        - Purpose: Generate the initial set of directories and placeholder files required for a new MCCP project.
        - Process: Reads the standard directory structure definition (potentially from configuration or a template). Creates the necessary directories (e.g., `config`, `src_mcbc`, `src_mcpc`, `mccp_symbols`). Initializes key files like `mccp_config.json` with default content. Ensures required permissions are set.
        - Input: The desired path for the new project's root directory (`project_path`).
        - Output: A boolean indicating success or failure of the structure creation.
        - Dependencies: Uses the `ConfigManager` to get directory names and potentially default file content. May use a `JsonParser` to write initial JSON files.
    - Read File (`read_file`):
        - Purpose: Retrieve the content of a specified file.
        - Process: Opens the file located at `file_path` in read mode. Reads the entire content as a string. Handles potential errors such as the file not existing or permission issues.
        - Input: The path to the file (`file_path`).
        - Output: The content of the file as a string, or `None` if the file could not be read (e.g