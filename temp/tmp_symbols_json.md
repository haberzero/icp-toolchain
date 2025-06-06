# mccp_toolchain.ui 模块

```markdown
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
                    "parameters": [],
                    "return_type": "None",
                    "description": "初始化主窗口，设置布局和连接信号槽。"
                },
                {
                    "name": "setup_ui",
                    "parameters": [],
                    "return_type": "None",
                    "description": "构建用户界面元素，如文件树视图、菜单、工具栏和状态栏。",
                    "dependencies": [
                        "PyQt5.QtWidgets",
                        "PyQt5.QtGui",
                        "PyQt5.QtCore"
                    ]
                },
                {
                    "name": "connect_signals",
                    "parameters": [],
                    "return_type": "None",
                    "description": "连接UI元素（如按钮、菜单项）的信号到槽函数。",
                    "dependencies": [
                        "mccp_toolchain.core.build.BuildOrchestrator",
                        "mccp_toolchain.mccp.file_manager.FileManager"
                    ]
                },
                {
                    "name": "update_file_tree",
                    "parameters": [
                        {
                            "name": "project_root",
                            "type": "str",
                            "description": "项目根目录路径"
                        }
                    ],
                    "return_type": "None",
                    "description": "刷新文件结构树视图，显示项目文件和目录。",
                    "dependencies": [
                        "PyQt5.QtWidgets.QFileSystemModel"
                    ]
                },
                {
                    "name": "log_message",
                    "parameters": [
                        {
                            "name": "message",
                            "type": "str",
                            "description": "要显示在状态栏或日志区域的消息"
                        }
                    ],
                    "return_type": "None",
                    "description": "在状态栏或日志区域显示信息。"
                },
                {
                    "name": "handle_new_project",
                    "parameters": [],
                    "return_type": "None",
                    "description": "处理创建新项目的用户操作，可能弹出对话框获取项目信息，调用 FileManager 创建结构。"
                },
                {
                    "name": "handle_open_project",
                    "parameters": [],
                    "return_type": "None",
                    "description": "处理打开现有项目的用户操作，弹出文件对话框选择项目目录，然后更新文件树。"
                },
                {
                    "name": "handle_run_build",
                    "parameters": [
                        {
                            "name": "target_layer",
                            "type": "str",
                            "description": "构建目标层级 ('mcbc', 'mcpc', 'code')"
                        }
                    ],
                    "return_type": "None",
                    "description": "处理触发构建流程的用户操作，调用 BuildOrchestrator。",
                    "dependencies": [
                        "mccp_toolchain.core.build.BuildOrchestrator"
                    ]
                }
            ]
        }
    ]
}
```

## File: mccp_toolchain/core/build/symbols.json

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
                        {
                            "name": "config_manager",
                            "type": "mccp_toolchain.mccp.config.ConfigManager",
                            "description": "配置管理器实例"
                        },
                        {
                            "name": "file_manager",
                            "type": "mccp_toolchain.mccp.file_manager.FileManager",
                            "description": "文件管理器实例"
                        },
                        {
                            "name": "symbol_manager",
                            "type": "mccp_toolchain.mccp.symbols.SymbolTableManager",
                            "description": "符号表管理器实例"
                        },
                        {
                            "name": "llm_client",
                            "type": "mccp_toolchain.core.llm.LLMClient",
                            "description": "LLM 客户端实例"
                        },
                        {
                            "name": "parsers",
                            "type": "dict",
                            "description": "包含各种解析器实例的字典"
                        }
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
                        {
                            "name": "project_path",
                            "type": "str",
                            "description": "项目根目录"
                        },
                        {
                            "name": "start_layer",
                            "type": "str",
                            "description": "起始层级 ('md', 'mcbc', 'mcpc')"
                        },
                        {
                            "name": "end_layer",
                            "type": "str",
                            "description": "结束层级 ('mcbc', 'mcpc', 'code')"
                        }
                    ],
                    "return_type": "bool",
                    "description": "执行从起始层级到结束层级的正向构建流程，协调各步骤。",
                    "dependencies": [
                        "mccp_toolchain.core.build.LayerTransformer"
                    ]
                },
                {
                    "name": "run_reverse_build",
                    "parameters": [
                        {
                            "name": "project_path",
                            "type": "str",
                            "description": "项目根目录"
                        },
                        {
                            "name": "start_layer",
                            "type": "str",
                            "description": "起始层级 ('code', 'mcpc', 'mcbc')"
                        },
                        {
                            "name": "end_layer",
                            "type": "str",
                            "description": "结束层级 ('mcpc', 'mcbc', 'md')"
                        }
                    ],
                    "return_type": "bool",
                    "description": "执行从起始层级到结束层级的反向构建流程（待实现）。",
                    "is_frozen": true
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
                        {
                            "name": "config_manager",
                            "type": "mccp_toolchain.mccp.config.ConfigManager"
                        },
                        {
                            "name": "file_manager",
                            "type": "mccp_toolchain.mccp.file_manager.FileManager"
                        },
                        {
                            "name": "symbol_manager",
                            "type": "mccp_toolchain.mccp.symbols.SymbolTableManager"
                        },
                        {
                            "name": "llm_client",
                            "type": "mccp_toolchain.core.llm.LLMClient"
                        },
                        {
                            "name": "source_parser",
                            "type": "object",
                            "description": "源文件解析器"
                        },
                        {
                            "name": "target_parser",
                            "type": "object",
                            "description": "目标文件解析器 (用于验证或结构化)"
                        }
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
                        {
                            "name": "source_file_path",
                            "type": "str"
                        },
                        {
                            "name": "target_file_path",
                            "type": "str"
                        },
                        {
                            "name": "build_rule_key",
                            "type": "str",
                            "description": "mccp_config.json 中的构建规则键 (e.g., 'mcbc_to_mcpc')"
                        }
                    ],
                    "return_type": "bool",
                    "description": "执行从源文件到目标文件的转换，包括读取、解析、生成LLM提示词、调用LLM、处理响应、更新符号表和写入文件。"
                }
            ]
        },
        {
            "name": "BUILD_LAYERS",
            "type": "constant",
            "description": "定义构建流程的层级顺序和映射关系，与 mccp_config.json 中的 layer_mapping 相关。",
            "value": [
                "requirements",
                "behavior_code",
                "pseudo_code",
                "target_code"
            ]
        },
        {
            "name": "BUILD_RULES",
            "type": "constant",
            "description": "定义构建规则，如 md_to_mcbc, mcbc_to_mcpc, mcpc_to_py，与 mccp_config.json 中的 build_rules 相关。",
            "value": [
                "md_to_mcbc",
                "mcbc_to_mcpc",
                "mcpc_to_py"
            ]
        }
    ]
}
```

## File: mccp_toolchain/core/llm/symbols.json

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
                        {
                            "name": "config_manager",
                            "type": "mccp_toolchain.mccp.config.ConfigManager",
                            "description": "配置管理器实例"
                        }
                    ],
                    "return_type": "None",
                    "description": "初始化 LLM 客户端，读取配置并设置 Langchain 模型。",
                    "dependencies": [
                        "langchain.llms",
                        "mccp_toolchain.mccp.config.ConfigManager"
                    ]
                },
                {
                    "name": "generate_content",
                    "parameters": [
                        {
                            "name": "prompt",
                            "type": "str",
                            "description": "发送给 LLM 的提示词"
                        },
                        {
                            "name": "context",
                            "type": "dict",
                            "description": "包含上下文信息的字典 (e.g., source_content, config, symbols)"
                        }
                    ],
                    "return_type": "str",
                    "description": "根据提示词和上下文调用 LLM 生成内容。",
                    "dependencies": [
                        "langchain.prompts",
                        "langchain.chains"
                    ]
                },
                {
                    "name": "parse_response",
                    "parameters": [
                        {
                            "name": "response_text",
                            "type": "str",
                            "description": "LLM 返回的原始文本"
                        },
                        {
                            "name": "target_format",
                            "type": "str",
                            "description": "期望的目标格式 (e.g., 'mcbc', 'mcpc', 'python_code')"
                        }
                    ],
                    "return_type": "object",
                    "description": "解析 LLM 返回的文本，将其结构化或验证格式。"
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
                        {
                            "name": "config_manager",
                            "type": "mccp_toolchain.mccp.config.ConfigManager",
                            "description": "配置管理器实例"
                        }
                    ],
                    "return_type": "None",
                    "description": "初始化提示词生成器。"
                },
                {
                    "name": "generate_prompt",
                    "parameters": [
                        {
                            "name": "build_rule_key",
                            "type": "str",
                            "description": "构建规则键 (e.g., 'mcbc_to_mcpc')"
                        },
                        {
                            "name": "source_content",
                            "type": "str",
                            "description": "源文件内容"
                        },
                        {
                            "name": "symbols",
                            "type": "dict",
                            "description": "相关的分布式符号表内容"
                        },
                        {
                            "name": "config",
                            "type": "dict",
                            "description": "mccp_config.json 配置"
                        }
                    ],
                    "return_type": "str",
                    "description": "结合基础提示词模板、源内容、符号表和配置生成完整的提示词。",
                    "dependencies": [
                        "mccp_toolchain.mccp.config.ConfigManager"
                    ]
                }
            ]
        }
    ]
}
```

## File: mccp_toolchain/mccp/parsers/symbols.json

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
                        {
                            "name": "content",
                            "type": "str",
                            "description": "requirements.md 文件的文本内容"
                        }
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
                        {
                            "name": "content",
                            "type": "str",
                            "description": ".mcbc 文件的文本内容"
                        }
                    ],
                    "return_type": "dict",
                    "description": "将 .mcbc 文本解析为结构化的行为描述对象。"
                },
                {
                    "name": "generate",
                    "parameters": [
                        {
                            "name": "data",
                            "type": "dict",
                            "description": "结构化的行为描述数据"
                        }
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
                        {
                            "name": "content",
                            "type": "str",
                            "description": ".mcpc 文件的文本内容"
                        }
                    ],
                    "return_type": "dict",
                    "description": "将 .mcpc 文本解析为结构化的符号-伪代码对象。"
                },
                {
                    "name": "generate",
                    "parameters": [
                        {
                            "name": "data",
                            "type": "dict",
                            "description": "结构化的符号-伪代码数据"
                        }
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
                        {
                            "name": "content",
                            "type": "str",
                            "description": "源代码文件的文本内容"
                        },
                        {
                            "name": "language",
                            "type": "str",
                            "description": "目标语言 (e.g., 'python')"
                        }
                    ],
                    "return_type": "dict",
                    "description": "将源代码解析为结构化数据（类、函数、变量等），用于反向构建。"
                },
                {
                    "name": "generate",
                    "parameters": [
                        {
                            "name": "data",
                            "type": "dict",
                            "description": "结构化的代码数据"
                        },
                        {
                            "name": "language",
                            "type": "str",
                            "description": "目标语言 (e.g., 'python')"
                        }
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
                        {
                            "name": "content",
                            "type": "str",
                            "description": "JSON 文件的文本内容"
                        }
                    ],
                    "return_type": "dict",
                    "description": "解析 JSON 文本为 Python 字典。",
                    "dependencies": [
                        "json"
                    ]
                },
                {
                    "name": "generate",
                    "parameters": [
                        {
                            "name": "data",
                            "type": "dict",
                            "description": "Python 字典数据"
                        }
                    ],
                    "return_type": "str",
                    "description": "将 Python 字典生成为格式化的 JSON 文本。",
                    "dependencies": [
                        "json"
                    ]
                }
            ]
        }
    ]
}
```

## File: mccp_toolchain/mccp/symbols/symbols.json

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
                        {
                            "name": "file_manager",
                            "type": "mccp_toolchain.mccp.file_manager.FileManager",
                            "description": "文件管理器实例"
                        },
                        {
                            "name": "config_manager",
                            "type": "mccp_toolchain.mccp.config.ConfigManager",
                            "description": "配置管理器实例"
                        }
                    ],
                    "return_type": "None",
                    "description": "初始化符号表管理器，加载所有符号表文件。",
                    "dependencies": [
                        "mccp_toolchain.mccp.file_manager.FileManager",
                        "mccp_toolchain.mccp.config.ConfigManager"
                    ]
                },
                {
                    "name": "load_all_symbol_tables",
                    "parameters": [
                        {
                            "name": "project_path",
                            "type": "str",
                            "description": "项目根目录"
                        }
                    ],
                    "return_type": "None",
                    "description": "加载 mccp_symbols 目录下的所有 symbols.json 文件到内存。"
                },
                {
                    "name": "save_all_symbol_tables",
                    "parameters": [],
                    "return_type": "None",
                    "description": "将内存中的符号表数据保存回对应的 symbols.json 文件。"
                },
                {
                    "name": "find_symbol",
                    "parameters": [
                        {
                            "name": "symbol_name",
                            "type": "str",
                            "description": "要查找的符号名"
                        },
                        {
                            "name": "module_name",
                            "type": "str",
                            "description": "可选：限定查找的模块名"
                        }
                    ],
                    "return_type": "dict | None",
                    "description": "在所有加载的符号表中查找指定符号。",
                    "dependencies": [
                        "mccp_toolchain.utils"
                    ]
                },
                {
                    "name": "update_symbol",
                    "parameters": [
                        {
                            "name": "symbol_data",
                            "type": "dict",
                            "description": "要更新或添加的符号数据 (包含 'name', 'module_name')"
                        }
                    ],
                    "return_type": "bool",
                    "description": "更新或添加一个符号到对应的模块符号表。如果符号已存在且 is_frozen 为 true，则拒绝更新。"
                },
                {
                    "name": "get_module_symbols",
                    "parameters": [
                        {
                            "name": "module_name",
                            "type": "str",
                            "description": "模块名"
                        }
                    ],
                    "return_type": "dict",
                    "description": "获取指定模块的符号表数据。"
                }
            ]
        },
        {
            "name": "Symbol",
            "type": "class",
            "description": "表示一个符号的简单数据结构。",
            "attributes": [
                {
                    "name": "name",
                    "type": "str",
                    "description": "符号名称"
                },
                {
                    "name": "type",
                    "type": "str",
                    "description": "符号类型 ('class', 'function', 'variable', 'constant')"
                },
                {
                    "name": "description",
                    "type": "str",
                    "description": "符号描述"
                },
                {
                    "name": "module_name",
                    "type": "str",
                    "description": "符号所属模块名"
                },
                {
                    "name": "dependencies",
                    "type": "list[str]",
                    "description": "依赖的其他符号名或模块名"
                },
                {
                    "name": "is_frozen",
                    "type": "bool",
                    "description": "标记该符号是否被冻结，不可由 LLM 修改。"
                }
            ]
        }
    ]
}
```

## File: mccp_toolchain/mccp/file_manager/symbols.json

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
                        {
                            "name": "config_manager",
                            "type": "mccp_toolchain.mccp.config.ConfigManager",
                            "description": "配置管理器实例"
                        }
                    ],
                    "return_type": "None",
                    "description": "初始化文件管理器。",
                    "dependencies": [
                        "mccp_toolchain.mccp.config.ConfigManager",
                        "os",
                        "pathlib"
                    ]
                },
                {
                    "name": "create_project_structure",
                    "parameters": [
                        {
                            "name": "project_path",
                            "type": "str",
                            "description": "新项目的根目录路径"
                        }
                    ],
                    "return_type": "bool",
                    "description": "根据 MCCP 规范和配置，创建标准的项目目录结构和初始文件（如 mccp_config.json）。",
                    "dependencies": [
                        "mccp_toolchain.mccp.config.ConfigManager",
                        "mccp_toolchain.mccp.parsers.JsonParser"
                    ]
                },
                {
                    "name": "read_file",
                    "parameters": [
                        {
                            "name": "file_path",
                            "type": "str",
                            "description": "要读取的文件路径"
                        }
                    ],
                    "return_type": "str | None",
                    "description": "读取文件内容，返回字符串。文件不存在或读取失败返回 None。"
                },
                {
                    "name": "write_file",
                    "parameters": [
                        {
                            "name": "file_path",
                            "type": "str",
                            "description": "要写入的文件路径"
                        },
                        {
                            "name": "content",
                            "type": "str",
                            "description": "要写入的文件内容"
                        }
                    ],
                    "return_type": "bool",
                    "description": "将内容写入文件。如果父目录不存在则创建。写入成功返回 True，失败返回 False。"
                },
                {
                    "name": "get_file_path",
                    "parameters": [
                        {
                            "name": "project_path",
                            "type": "str",
                            "description": "项目根目录"
                        },
                        {
                            "name": "layer_key",
                            "type": "str",
                            "description": "层级键 (e.g., 'behavior_code_dir')"
                        },
                        {
                            "name": "file_name",
                            "type": "str",
                            "description": "文件名 (不含路径)"
                        }
                    ],
                    "return_type": "str",
                    "description": "根据配置的层级映射和文件名生成文件的完整路径。"
                },
                {
                    "name": "list_files_in_layer",
                    "parameters": [
                        {
                            "name": "project_path",
                            "type": "str",
                            "description": "项目根目录"
                        },
                        {
                            "name": "layer_key",
                            "type": "str",
                            "description": "层级键 (e.g., 'behavior_code_dir')"
                        },
                        {
                            "name": "extension",
                            "type": "str",
                            "description": "文件扩展名"
                        }
                    ],
                    "return_type": "list[str]",
                    "description": "列出指定层级目录下匹配扩展名的所有文件路径。"
                },
                {
                    "name": "get_project_root_from_path",
                    "type": "function",
                    "parameters": [
                        {
                            "name": "any_path_within_project",
                            "type": "str"
                        }
                    ],
                    "return_type": "str | None",
                    "description": "给定项目内的任意路径，向上查找 mccp_config.json 所在的目录作为项目根目录。"
                }
            ]
        }
    ]
}
```

## File: mccp_toolchain/mccp/config/symbols.json

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
                        {
                            "name": "file_manager",
                            "type": "mccp_toolchain.mccp.file_manager.FileManager",
                            "description": "文件管理器实例"
                        }
                    ],
                    "return_type": "None",
                    "description": "初始化配置管理器。",
                    "dependencies": [
                        "mccp_toolchain.mccp.file_manager.FileManager",
                        "mccp_toolchain.mccp.parsers.JsonParser"
                    ]
                },
                {
                    "name": "load_config",
                    "parameters": [
                        {
                            "name": "project_path",
                            "type": "str",
                            "description": "项目根目录"
                        }
                    ],
                    "return_type": "bool",
                    "description": "从项目目录加载 mccp_config.json 文件并解析。"
                },
                {
                    "name": "get_setting",
                    "parameters": [
                        {
                            "name": "key",
                            "type": "str",
                            "description": "配置项的键路径 (e.g., 'llm_settings.model')"
                        }
                    ],
                    "return_type": "any",
                    "description": "根据键路径获取配置值。支持嵌套路径访问。"
                },
                {
                    "name": "get_layer_dir",
                    "parameters": [
                        {
                            "name": "layer_key",
                            "type": "str",
                            "description": "层级键 (e.g., 'behavior_code_dir')"
                        }
                    ],
                    "return_type": "str",
                    "description": "获取指定层级对应的目录名。"
                },
                {
                    "name": "get_build_rule",
                    "parameters": [
                        {
                            "name": "rule_key",
                            "type": "str",
                            "description": "构建规则键 (e.g., 'mcbc_to_mcpc')"
                        }
                    ],
                    "return_type": "dict",
                    "description": "获取指定构建规则的详细配置 (input_extension, output_extension, llm_prompt等)。"
                }
            ]
        }
    ]
}
```

## File: mccp_toolchain/utils/symbols.json

```json
{
    "module_name": "mccp_toolchain.utils",
    "description": "通用工具模块，提供各种辅助函数。",
    "symbols": [
        {
            "name": "normalize_path",
            "type": "function",
            "parameters": [
                {
                    "name": "path",
                    "type": "str",
                    "description": "待规范化的路径"
                }
            ],
            "return_type": "str",
            "description": "规范化文件路径，处理斜杠、相对路径等。"
        },
        {
            "name": "validate_file_name",
            "type": "function",
            "parameters": [
                {
                    "name": "file_name",
                    "type": "str",
                    "description": "待验证的文件名"
                }
            ],
            "return_type": "bool",
            "description": "验证文件名是否符合命名规范 (snake_case)。",
            "dependencies": [
                "re"
            ]
        },
        {
            "name": "snake_to_pascal_case",
            "type": "function",
            "parameters": [
                {
                    "name": "text",
                    "type": "str",
                    "description": "snake_case 字符串"
                }
            ],
            "return_type": "str",
            "description": "将 snake_case 字符串转换为 PascalCase。"
        },
        {
            "name": "pascal_to_snake_case",
            "type": "function",
            "parameters": [
                {
                    "name": "text",
                    "type": "str",
                    "description": "PascalCase 字符串"
                }
            ],
            "return_type": "str",
            "description": "将 PascalCase 字符串转换为 snake_case。"
        }
    ]
}
```
