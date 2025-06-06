# 符号-伪代码层内容 (MCPC)

File: src_mcpc/ui.mcpc

```markdown
# MCCP Symbol-Pseudo Code

MODULE mccp_toolchain.ui
  DESCRIPTION "用户界面模块，基于 PyQt 框架，提供与用户交互的图形界面。"

  CLASS MainWindow
    DESCRIPTION "主窗口类，继承自 PyQt 的 QMainWindow，包含文件树视图、按钮、状态栏等。"
    INHERITS QMainWindow

    # Attributes (Placeholder for UI elements)
    ATTRIBUTE file_tree_view: QTreeView
    ATTRIBUTE new_project_button: QPushButton
    ATTRIBUTE open_project_button: QPushButton
    ATTRIBUTE run_build_button: QPushButton
    ATTRIBUTE status_bar: QStatusBar
    ATTRIBUTE build_target_selector: QComboBox # Or similar for target_layer selection

    # Dependencies (Injected Services)
    ATTRIBUTE config_manager: ConfigManager
    ATTRIBUTE file_manager: FileManager
    ATTRIBUTE build_orchestrator: BuildOrchestrator
    ATTRIBUTE symbol_manager: SymbolTableManager # Added dependency for loading symbols

    METHOD __init__(PARAMETERS config_manager: ConfigManager, file_manager: FileManager, build_orchestrator: BuildOrchestrator, symbol_manager: SymbolTableManager)
      DESCRIPTION "初始化主窗口，设置布局和连接信号槽。"
      # Store injected dependencies
      SET self.config_manager = config_manager
      SET self.file_manager = file_manager
      SET self.build_orchestrator = build_orchestrator
      SET self.symbol_manager = symbol_manager

      # Set up window properties
      # CALL super().__init__()

      # Build UI elements and layout
      CALL self.setup_ui()

      # Connect signals to slots
      CALL self.connect_signals()

      # Set initial status bar message
      CALL self.log_message("MCCP Toolchain ready.")

    METHOD setup_ui()
      DESCRIPTION "构建用户界面元素，如文件树视图、菜单、工具栏和状态栏。"
      # Create main layout
      # layout = CREATE QVBoxLayout()

      # Create File Tree View
      # self.file_tree_view = CREATE QTreeView()
      # layout.addWidget(self.file_tree_view)

      # Create buttons/actions (example)
      # button_layout = CREATE QHBoxLayout()
      # self.new_project_button = CREATE QPushButton("New Project")
      # self.open_project_button = CREATE QPushButton("Open Project")
      # self.run_build_button = CREATE QPushButton("Run Build")
      # self.build_target_selector = CREATE QComboBox() # Populate with layer options
      # button_layout.addWidget(self.new_project_button)
      # button_layout.addWidget(self.open_project_button)
      # button_layout.addWidget(self.run_build_button)
      # button_layout.addWidget(self.build_target_selector)
      # layout.addLayout(button_layout)

      # Create Status Bar
      # self.status_bar = CREATE QStatusBar()
      # self.setStatusBar(self.status_bar)

      # Set the main layout for the window
      # widget = CREATE QWidget()
      # widget.setLayout(layout)
      # self.setCentralWidget(widget)

    METHOD connect_signals()
      DESCRIPTION "连接UI元素（如按钮、菜单项）的信号到槽函数。"
      # Connect button clicks to handler methods
      # CALL self.new_project_button.clicked.connect(self.handle_new_project)
      # CALL self.open_project_button.clicked.connect(self.handle_open_project)
      # CALL self.run_build_button.clicked.connect(self.handle_run_build)

      # Connect file tree view signals (e.g., item selection)
      # CALL self.file_tree_view.clicked.connect(self.handle_file_selected) # Example

      # Connect build target selector signal
      # CALL self.build_target_selector.currentTextChanged.connect(self.handle_build_target_changed) # Example

    METHOD update_file_tree(PARAMETERS project_root: str)
      DESCRIPTION "刷新文件结构树视图，显示项目文件和目录。"
      # Use QFileSystemModel to represent the file system
      # model = CREATE QFileSystemModel()
      # model.setRootPath(project_root)
      # CALL self.file_tree_view.setModel(model)
      # CALL self.file_tree_view.setRootIndex(model.index(project_root))

    METHOD log_message(PARAMETERS message: str)
      DESCRIPTION "在状态栏或日志区域显示信息。"
      # Display message in the status bar
      # CALL self.status_bar.showMessage(message)

    METHOD handle_new_project()
      DESCRIPTION "处理创建新项目的用户操作，可能弹出对话框获取项目信息，调用 FileManager 创建结构。"
      # Prompt user for project path and name using a dialog
      # project_path = CALL show_new_project_dialog() # Returns selected path or None

      # IF project_path IS NOT None THEN
        # CALL self.log_message("Creating new project...")
        # success = CALL self.file_manager.create_project_structure(project_path)
        # IF success THEN
          # CALL self.log_message(f"Project created at {project_path}.")
          # CALL self.open_project(project_path) # Re-use open logic to load/display
        # ELSE
          # CALL self.log_message(f"Failed to create project at {project_path}.")
        # END IF
      # END IF

    METHOD handle_open_project()
      DESCRIPTION "处理打开现有项目的用户操作，弹出文件对话框选择项目目录，然后更新文件树。"
      # Prompt user to select a directory using a file dialog
      # selected_path = CALL show_open_directory_dialog() # Returns selected path or None

      # IF selected_path IS NOT None THEN
        # CALL self.open_project(selected_path)
      # END IF

    # Helper method to centralize project opening logic
    METHOD open_project(PARAMETERS path: str)
      DESCRIPTION "加载并显示一个已存在的项目。"
      # Try to find the project root (in case user selected a sub-directory)
      # project_root = CALL self.file_manager.get_project_root_from_path(path)

      # IF project_root IS NOT None THEN
        # CALL self.log_message(f"Opening project at {project_root}...")
        # CALL self.config_manager.load_config(project_root)
        # CALL self.symbol_manager.load_all_symbol_tables(project_root) # Load symbols when project opens
        # CALL self.update_file_tree(project_root)
        # CALL self.log_message(f"Project at {project_root} loaded.")
      # ELSE
        # CALL self.log_message(f"Could not find MCCP project config in {path} or parent directories.")
      # END IF

    METHOD handle_run_build()
      DESCRIPTION "处理触发构建流程的用户操作，调用 BuildOrchestrator。"
      # Get the currently selected build target layer from the UI selector
      # target_layer = CALL self.build_target_selector.currentText() # e.g., "mcpc", "code"
      # Get the current project root (assuming it's stored after opening)
      # project_root = CALL self.config_manager.get_project_root() # Assuming ConfigManager stores this

      # IF project_root IS NOT None AND target_layer IS NOT Empty THEN
        # Determine start layer (e.g., based on which file/layer is currently viewed/selected, or always start from md/mcbc?)
        # Let's assume for now we always run from mcbc to target_layer when triggered from UI build button.
        # start_layer = "behavior_code" # Needs refinement based on UI context

        # CALL self.log_message(f"Starting build from {start_layer} to {target_layer}...")
        # success = CALL self.build_orchestrator.run_forward_build(project_root, start_layer, target_layer)

        # IF success THEN
          # CALL self.log_message("Build process completed successfully.")
          # CALL self.update_file_tree(project_root) # Refresh file tree as new files might be generated
        # ELSE
          # CALL self.log_message("Build process failed.")
        # END IF
      # ELSE
        # CALL self.log_message("Cannot run build: No project loaded or target not selected.")
      # END IF

    # METHOD handle_file_selected(PARAMETERS index: QModelIndex) # Example handler
      # DESCRIPTION "处理文件树中文件被选中的事件。"
      # Get the file path from the selected index
      # file_path = CALL model.filePath(index)
      # IF file_path IS a file THEN
        # CALL open_file_in_editor(file_path) # Assuming integration with an editor
      # END IF

END CLASS
```

File: src_mcpc/core/build.mcpc

```
# MCCP Symbol-Pseudo Code

MODULE mccp_toolchain.core.build
  DESCRIPTION "核心构建模块，负责协调正向和反向构建流程，驱动层级转换。"

  CLASS BuildOrchestrator
    DESCRIPTION "构建流程协调器类，管理整个构建流程的步骤和依赖。"

    # Dependencies
    ATTRIBUTE config_manager: ConfigManager
    ATTRIBUTE file_manager: FileManager
    ATTRIBUTE symbol_manager: SymbolTableManager
    ATTRIBUTE llm_client: LLMClient
    ATTRIBUTE parsers: dict # Dictionary mapping parser keys to instances

    METHOD __init__(PARAMETERS config_manager: ConfigManager, file_manager: FileManager, symbol_manager: SymbolTableManager, llm_client: LLMClient, parsers: dict)
      DESCRIPTION "初始化构建协调器，注入所需的依赖服务。"
      SET self.config_manager = config_manager
      SET self.file_manager = file_manager
      SET self.symbol_manager = symbol_manager
      SET self.llm_client = llm_client
      SET self.parsers = parsers

    METHOD run_forward_build(PARAMETERS project_path: str, start_layer_key: str, end_layer_key: str) RETURNS bool
      DESCRIPTION "执行从起始层级到结束层级的正向构建流程，协调各步骤。"
      # Ensure symbols are loaded for context
      CALL self.symbol_manager.load_all_symbol_tables(project_path)

      # Get the defined build layer sequence from config
      # layer_sequence = CALL self.config_manager.get_setting("layer_mapping_sequence") # Assuming config has a sequence defined or derive from BUILD_LAYERS constant
      # Example derivation:
      # CONSTANT BUILD_LAYERS_SEQUENCE = [
      #    "requirements", "behavior_code", "pseudo_code", "target_code"
      # ]
      # start_index = FIND_INDEX_OF(start_layer_key, BUILD_LAYERS_SEQUENCE)
      # end_index = FIND_INDEX_OF(end_layer_key, BUILD_LAYERS_SEQUENCE)

      # IF start_index IS None OR end_index IS None OR start_index >= end_index THEN
        # LOG ERROR "Invalid start or end layer."
        # RETURN False
      # END IF

      # FOR each step in the layer sequence from start_index to end_index - 1 DO
        # current_layer_key = BUILD_LAYERS_SEQUENCE[step_index]
        # next_layer_key = BUILD_LAYERS_SEQUENCE[step_index + 1]
        # rule_key = CALL self.get_rule_key(current_layer_key, next_layer_key, "forward") # Helper to map layers to rule key (e.g., "mcbc_to_mcpc")

        # IF rule_key IS None THEN
          # LOG ERROR f"No forward build rule found for {current_layer_key} to {next_layer_key}."
          # RETURN False
        # END IF

        # rule_config = CALL self.config_manager.get_build_rule(rule_key)
        # source_layer_dir_key = rule_config['input_layer_dir_key'] # Assuming rule config links to layer mapping keys
        # target_layer_dir_key = rule_config['output_layer_dir_key'] # Assuming rule config links to layer mapping keys
        # source_ext = rule_config['input_extension']
        # target_ext = rule_config['output_extension']

        # Get list of source files for this layer transition
        # source_files = CALL self.file_manager.list_files_in_layer(project_path, source_layer_dir_key, source_ext)

        # IF source_files IS Empty AND current_layer_key IS NOT "requirements" THEN # requirements might be a single file
           # LOG WARNING f"No source files found in {source_layer_dir_key} with extension {source_ext} for rule {rule_key}. Skipping."
           # CONTINUE # Move to next layer transition
        # END IF

        # source_parser_key = rule_config['source_parser'] # Assuming rule config specifies parser keys
        # target_parser_key = rule_config['target_parser'] # Assuming rule config specifies parser keys

        # source_parser_instance = self.parsers.get(source_parser_key)
        # target_parser_instance = self.parsers.get(target_parser_key) # Target parser might be optional

        # IF source_parser_instance IS None THEN
           # LOG ERROR f"Parser {source_parser_key} not found for rule {rule_key}."
           # RETURN False
        # END IF

        # FOR each source_file_path in source_files DO
          # Derive target_file_name (e.g., same base name, different extension/dir)
          # target_file_name = CALL self.derive_target_file_name(source_file_path, source_ext, target_ext) # Helper method
          # target_file_path = CALL self.file_manager.get_file_path(project_path, target_layer_dir_key, target_file_name)

          # LOG INFO f"Transforming {source_file_path} to {target_file_path} using rule {rule_key}..."

          # Create LayerTransformer instance for this specific file transformation
          # transformer = CREATE LayerTransformer(
          #   self.config_manager,
          #   self.file_manager,
          #   self.symbol_manager,
          #   self.llm_client,
          #   source_parser_instance,
          #   target_parser_instance # Pass target parser instance
          # )

          # file_transform_success = CALL transformer.transform(source_file_path, target_file_path, rule_key)

          # IF NOT file_transform_success THEN
            # LOG ERROR f"Transformation failed for file {source_file_path}."
            # RETURN False # Fail the entire build
          # END IF
        # END FOR

        # Save symbols after each layer transformation completes successfully for all files in that layer
        CALL self.symbol_manager.save_all_symbol_tables()

      # END FOR

      # CALL self.symbol_manager.save_all_symbol_tables() # Ensure final state is saved
      RETURN True

    METHOD run_reverse_build(PARAMETERS project_path: str, start_layer: str, end_layer: str) RETURNS bool
      DESCRIPTION "执行从起始层级到结束层级的反向构建流程（待实现）。"
      # This method is currently frozen/placeholder as per symbol table.
      # Future implementation will mirror run_forward_build but use reverse rules and layer sequence.
      # CALL self.symbol_manager.load_all_symbol_tables(project_path)
      # ... reverse logic ...
      LOG WARNING "Reverse build is not yet fully implemented."
      RETURN False # Indicate not implemented or failed for now

    # Helper method to map source/target layers to a build rule key
    METHOD get_rule_key(PARAMETERS source_layer_key: str, target_layer_key: str, direction: str) RETURNS str | None
      DESCRIPTION "根据源层、目标层和方向查找匹配的构建规则键。"
      # Logic to derive "md_to_mcbc" from source="requirements", target="behavior_code", direction="forward"
      # Needs access to config build_rules/reverse_build_rules structure
      # Example:
      # IF direction == "forward" THEN
        # FOR each rule_key, rule_config in self.config_manager.get_build_rules():
          # IF rule_config.get('input_layer_dir_key') == source_layer_key AND rule_config.get('output_layer_dir_key') == target_layer_key THEN
             # RETURN rule_key
          # END IF
      # ELSE IF direction == "reverse" THEN
        # FOR each rule_key, rule_config in self.config_manager.get_reverse_build_rules():
          # IF rule_config.get('input_layer_dir_key') == source_layer_key AND rule_config.get('output_layer_dir_key') == target_layer_key THEN
             # RETURN rule_key
          # END IF
      # END IF
      RETURN None

    # Helper method to derive target file name from source file name
    METHOD derive_target_file_name(PARAMETERS source_file_path: str, source_ext: str, target_ext: str) RETURNS str
      DESCRIPTION "根据源文件路径和扩展名，生成目标文件的文件名（替换扩展名）。"
      # Example: source_file_path = "path/to/file.mcbc", source_ext = ".mcbc", target_ext = ".mcpc" -> "file.mcpc"
      # Remove source_ext, add target_ext
      # base_name = CALL path_without_extension(source_file_path, source_ext) # Assumes a path utility
      # target_name = base_name + target_ext
      # RETURN target_name
      RETURN "" # Placeholder

  CLASS LayerTransformer
    DESCRIPTION "层级转换器类，负责执行具体的层级转换（如 .mcbc -> .mcpc），调用 LLM。"

    # Dependencies
    ATTRIBUTE config_manager: ConfigManager
    ATTRIBUTE file_manager: FileManager
    ATTRIBUTE symbol_manager: SymbolTableManager
    ATTRIBUTE llm_client: LLMClient
    ATTRIBUTE source_parser: object # Specific parser instance for source format
    ATTRIBUTE target_parser: object # Specific parser instance for target format (Optional, can be None)

    METHOD __init__(PARAMETERS config_manager: ConfigManager, file_manager: FileManager, symbol_manager: SymbolTableManager, llm_client: LLMClient, source_parser: object, target_parser: object | None)
      DESCRIPTION "初始化层级转换器。"
      SET self.config_manager = config_manager
      SET self.file_manager = file_manager
      SET self.symbol_manager = symbol_manager
      SET self.llm_client = llm_client
      SET self.source_parser = source_parser
      SET self.target_parser = target_parser # Can be None

    METHOD transform(PARAMETERS source_file_path: str, target_file_path: str, build_rule_key: str) RETURNS bool
      DESCRIPTION "执行从源文件到目标文件的转换，包括读取、解析、生成LLM提示词、调用LLM、处理响应、更新符号表和写入文件。"
      # Read source file content
      source_content = CALL self.file_manager.read_file(source_file_path)
      IF source_content IS None THEN
        LOG ERROR f"Failed to read source file: {source_file_path}"
        RETURN False
      END IF

      # Get the build rule configuration
      rule_config = CALL self.config_manager.get_build_rule(build_rule_key)
      IF rule_config IS None THEN
         LOG ERROR f"Build rule not found for key: {build_rule_key}"
         RETURN False
      END IF

      # Determine relevant symbols for the prompt (e.g., symbols from modules involved in this transformation)
      # This logic needs refinement - how to know which symbols are relevant?
      # Maybe pass ALL symbols? Or symbols from source/target modules?
      # For mcbc->mcpc, relevant symbols are probably ALL defined symbols to ensure consistency.
      all_symbols_data = CALL self.symbol_manager.get_all_symbols() # Assuming SymbolManager has this helper

      # Get full project configuration for context
      full_config = CALL self.config_manager.get_config_data()

      # Generate the LLM prompt
      prompt_generator = CREATE PromptGenerator(self.config_manager) # PromptGenerator needs ConfigManager
      llm_prompt = CALL prompt_generator.generate_prompt(build_rule_key, source_content, all_symbols_data, full_config)
      IF llm_prompt IS Empty THEN
         LOG ERROR "Failed to generate LLM prompt."
         RETURN False
      END IF

      # Call the LLM
      LOG INFO f"Calling LLM for transformation rule '{build_rule_key}'..."
      llm_response_text = CALL self.llm_client.generate_content(llm_prompt, { "source_file": source_file_path, "target_file": target_file_path, "rule": build_rule_key }) # Pass context

      IF llm_response_text IS Empty THEN
        LOG ERROR "LLM returned empty response."
        RETURN False
      END IF

      # Parse or process LLM response
      # The LLM response for mcbc->mcpc should be the content of the target .mcpc file.
      # The LLM is also expected to suggest symbol updates implicitly or explicitly.
      # Processing the response and updating symbols might be interleaved or happen after parsing.

      # Option 1: LLM response is just the target file content. Symbol update happens based on parsing *this* content.
      generated_content = llm_response_text # Assuming the LLM directly outputs the desired file content

      # Option 2: LLM response includes both target content and symbol updates (e.g., structured JSON)
      # In this case, need to parse the LLM response carefully. Let's assume Option 1 for simplicity at MCPC level.
      # Future refinement: LLMClient.parse_response could handle a structured LLM output that includes both content and symbol delta.
      # For now, assume LLM outputs raw target content.

      # If target parser exists, potentially validate or process the generated content
      # IF self.target_parser IS NOT None THEN
         # Validate generated_content using self.target_parser.parse() or similar validation logic?
         # Or perhaps self.llm_client.parse_response handles the initial structure extraction?
         # Let's assume for now the LLM response IS the target content text.
      # END IF

      # Process potential symbol updates suggested or implied by the generated content
      # This is a critical step that needs careful design.
      # Example: If LLM outputs a function signature different from the symbol table,
      # the toolchain needs to decide whether to update the symbol (if not frozen)
      # or flag a discrepancy. For mcbc->mcpc, LLM might add parameter names/types
      # that weren't in the initial symbol definition.
      # SYMBOL_UPDATES_FROM_LLM_RESPONSE = CALL self.extract_symbol_updates(llm_response_text, build_rule_key) # Helper function or logic
      # FOR each symbol_update in SYMBOL_UPDATES_FROM_LLM_RESPONSE DO
         # success = CALL self.symbol_manager.update_symbol(symbol_update)
         # IF NOT success THEN
            # LOG WARNING f"Failed to update symbol {symbol_update.get('name')} (maybe frozen?)."
         # END IF
      # END FOR
      # Note: Actual symbol update logic needs to parse the *generated content* or a specific part of the LLM output
      # designed for symbol updates. This is complex and depends on the LLM interaction protocol.
      # At MCPC level, we acknowledge the *need* for this step.

      # Write generated content to target file
      success = CALL self.file_manager.write_file(target_file_path, generated_content)
      IF NOT success THEN
        LOG ERROR f"Failed to write target file: {target_file_path}"
        RETURN False
      END IF

      LOG INFO f"Successfully transformed {source_file_path} to {target_file_path}."
      RETURN True

  # CONSTANT definitions as per Symbol Table
  CONSTANT BUILD_LAYERS
    DESCRIPTION "定义构建流程的层级顺序和映射关系，与 mccp_config.json 中的 layer_mapping 相关。"
    VALUE ["requirements", "behavior_code", "pseudo_code", "target_code"]

  CONSTANT BUILD_RULES
    DESCRIPTION "定义构建规则，如 md_to_mcbc, mcbc_to_mcpc, mcpc_to_py，与 mccp_config.json 中的 build_rules 相关。"
    VALUE ["md_to_mcbc", "mcbc_to_mcpc", "mcpc_to_py"]

END CLASS
```

File: src_mcpc/core/llm.mcpc

```
# MCCP Symbol-Pseudo Code

MODULE mccp_toolchain.core.llm
  DESCRIPTION "大语言模型集成模块，使用 Langchain 与 LLM 交互，生成和处理文本。"

  CLASS LLMClient
    DESCRIPTION "LLM 客户端类，封装 Langchain 调用。"

    # Dependencies
    ATTRIBUTE config_manager: ConfigManager
    ATTRIBUTE langchain_model: object # Placeholder for Langchain model instance

    METHOD __init__(PARAMETERS config_manager: ConfigManager)
      DESCRIPTION "初始化 LLM 客户端，读取配置并设置 Langchain 模型。"
      SET self.config_manager = config_manager
      # Get LLM settings from config
      # model_name = CALL self.config_manager.get_setting("llm_settings.model")
      # api_url = CALL self.config_manager.get_setting("llm_settings.api_url")
      # api_key = CALL self.config_manager.get_setting("llm_settings.api_key")

      # Initialize the Langchain model
      # self.langchain_model = CALL langchain.llms.YourLLMModel(model_name, api_url, api_key, ...) # Use actual Langchain class

    METHOD generate_content(PARAMETERS prompt: str, context: dict) RETURNS str
      DESCRIPTION "根据提示词和上下文调用 LLM 生成内容。"
      # Prepare input for Langchain
      # formatted_prompt = CALL langchain.prompts.PromptTemplate(template=prompt, ...).format(...) # If using template objects
      # Use a Langchain chain or directly call the model
      # response = CALL self.langchain_model.invoke(formatted_prompt) # Or run, predict, etc.

      # Extract the generated text
      # generated_text = response.text # Example

      # RETURN generated_text
      RETURN "Generated content based on prompt and context." # Placeholder response

    METHOD parse_response(PARAMETERS response_text: str, target_format: str) RETURNS object
      DESCRIPTION "解析 LLM 返回的文本，将其结构化或验证格式。"
      # Note: The specific parsing logic depends on the target format and expected LLM output structure.
      # This method might delegate to specific parsers or contain basic validation.
      # For mcbc and mcpc, the format is structured text (like Markdown/Pseudo-code).
      # For Python code, it's code text.

      # IF target_format == ".mcbc" THEN
        # Assuming McbcParser is available and has a parse_text method
        # parsed_data = CALL McbcParser.parse_text(response_text) # Needs access to parser logic/instances?
        # RETURN parsed_data
      # ELSE IF target_format == ".mcpc" THEN
        # Assuming McpcParser is available
        # parsed_data = CALL McpcParser.parse_text(response_text) # Needs access to parser logic/instances?
        # RETURN parsed_data
      # ELSE IF target_format == ".py" THEN
        # Assuming TargetCodeParser is available
        # parsed_data = CALL TargetCodeParser.parse_text(response_text, "python") # Needs access to parser logic/instances?
        # RETURN parsed_data
      # ELSE IF target_format == "json" THEN
        # Assuming JsonParser is available
        # parsed_data = CALL JsonParser.parse(response_text) # Needs access to parser logic/instances?
        # RETURN parsed_data
      # ELSE
        # LOG WARNING f"Unknown target format for parsing: {target_format}. Returning raw text."
        # RETURN response_text
      # END IF
       RETURN response_text # Placeholder

  CLASS PromptGenerator
    DESCRIPTION "提示词生成器类，根据源内容、目标格式、符号表和配置生成结构化的 LLM 提示词。"

    # Dependencies
    ATTRIBUTE config_manager: ConfigManager

    METHOD __init__(PARAMETERS config_manager: ConfigManager)
      DESCRIPTION "初始化提示词生成器。"
      SET self.config_manager = config_manager

    METHOD generate_prompt(PARAMETERS build_rule_key: str, source_content: str, symbols: dict, config: dict) RETURNS str
      DESCRIPTION "结合基础提示词模板、源内容、符号表和配置生成完整的提示词。"
      # Retrieve the base prompt template for the given rule key
      # rule_config = CALL self.config_manager.get_build_rule(build_rule_key)
      # base_template = rule_config.get('llm_prompt')

      # IF base_template IS Empty THEN
        # LOG ERROR f"Prompt template not found for rule: {build_rule_key}"
        # RETURN ""
      # END IF

      # Format the template with provided context
      # The template is expected to use placeholders like {source_content}, {symbols}, {config}.
      # formatted_prompt = FORMAT_STRING(base_template, {
      #   "source_content": source_content,
      #   "symbols": JSON_STRINGIFY(symbols), # Represent symbols as JSON string
      #   "config": JSON_STRINGIFY(config) # Represent config as JSON string
      # })

      # RETURN formatted_prompt
      RETURN f"Generated prompt for {build_rule_key} with source content, symbols, and config." # Placeholder
```

File: src_mcpc/mccp/parsers.mcpc

```
# MCCP Symbol-Pseudo Code

MODULE mccp_toolchain.mccp.parsers
  DESCRIPTION "MCCP 文件解析器模块，负责读取、解析和验证不同格式的 MCCP 相关文件。"

  CLASS RequirementsParser
    DESCRIPTION "解析 requirements.md 文件的类。"
    METHOD parse(PARAMETERS content: str) RETURNS dict
      DESCRIPTION "将 Markdown 格式的需求文本解析为结构化数据。"
      # Logic to parse markdown headings, lists, and text into a structured dictionary.
      # Identify sections like "1. Project Vision", "2. Core Function Requirements", "3. UI Requirements", "4. Non-Functional Requirements".
      # Extract requirement IDs (e.g., SR.Func.Build.Forward.1), descriptions, and hierarchical structure.
      # RETURN { "project_vision": "...", "functional_requirements": [...], ... }
      RETURN {} # Placeholder

  CLASS McbcParser
    DESCRIPTION "解析 .mcbc (Behavior Code) 文件的类。"
    METHOD parse(PARAMETERS content: str) RETURNS dict
      DESCRIPTION "将 .mcbc 文本解析为结构化的行为描述对象。"
      # Logic to parse MCBC markdown format:
      # Identify "# Module: ...", "### Overview", "- Purpose:", "- Responsibilities:", "- Interactions:", "### Components", "#### Class: ...", "- Description:", "- Behaviors:", "- Behavior Name (`method_name`):", "- Purpose:", "- Process:", "- Input:", "- Output:", "- Dependencies:", "- Interactions:".
      # Structure this into a dictionary representing the module, classes, and behaviors.
      # RETURN { "module_name": ..., "overview": {...}, "components": [{ "type": "class", "name": ..., "behaviors": [...] }] }
      RETURN {} # Placeholder

    METHOD generate(PARAMETERS data: dict) RETURNS str
      DESCRIPTION "将结构化数据生成为 .mcbc 格式的文本。"
      # Logic to format a dictionary of behavior code data into the MCBC markdown structure.
      # Iterate through modules, classes, and behaviors, formatting each section with appropriate markdown syntax.
      # RETURN markdown_string
      RETURN "" # Placeholder

  CLASS McpcParser
    DESCRIPTION "解析 .mcpc (Pseudo Code) 文件的类。"
    METHOD parse(PARAMETERS content: str) RETURNS dict
      DESCRIPTION "将 .mcpc 文本解析为结构化的符号-伪代码对象。"
      # Logic to parse MCPC pseudo-code structure:
      # Identify "MODULE", "CLASS", "METHOD", "FUNCTION", "CONSTANT", "DESCRIPTION", "INHERITS", "ATTRIBUTE", "PARAMETERS", "RETURNS", keywords like "SET", "CALL", "IF", "ELSE", "LOOP", "RETURN", "CREATE".
      # Represent the parsed structure (modules, classes, methods, functions, constants, their parameters, return types, and the pseudo-code body) in a dictionary.
      # RETURN { "module_name": ..., "classes": [{ "name": ..., "methods": [...] }], "functions": [...], "constants": [...] }
      RETURN {} # Placeholder

    METHOD generate(PARAMETERS data: dict) RETURNS str
      DESCRIPTION "将结构化数据生成为 .mcpc 格式的文本。"
      # Logic to format a dictionary of symbol-pseudo code data into the MCPC text format.
      # Iterate through modules, classes, methods, functions, constants, formatting each with MCPC keywords and indentation.
      # RETURN mcpc_string
      RETURN "" # Placeholder

  CLASS TargetCodeParser
    DESCRIPTION "解析目标语言源代码（如 Python .py 文件）的类。"
    METHOD parse(PARAMETERS content: str, language: str) RETURNS dict
      DESCRIPTION "将源代码解析为结构化数据（类、函数、变量等），用于反向构建。"
      # Logic to parse source code based on language.
      # For Python, use AST (Abstract Syntax Tree) module or similar library.
      # Extract class definitions, method/function definitions (names, parameters, return hints), variable assignments, etc.
      # Structure this into a dictionary suitable for reverse transformation.
      # RETURN { "language": language, "classes": [...], "functions": [...], ... }
      RETURN {} # Placeholder

    METHOD generate(PARAMETERS data: dict, language: str) RETURNS str
      DESCRIPTION "将结构化数据生成为源代码格式的文本，遵循代码规范。"
      # Logic to generate source code from structured data based on language.
      # For Python, generate code strings from the dictionary representation, adhering to PEP8.
      # Add docstrings, comments, follow naming conventions.
      # RETURN source_code_string
      RETURN "" # Placeholder

  CLASS JsonParser
    DESCRIPTION "解析 JSON 配置文件的通用类。"
    METHOD parse(PARAMETERS content: str) RETURNS dict
      DESCRIPTION "解析 JSON 文本为 Python 字典。"
      # Use built-in JSON library.
      # RETURN CALL json.loads(content)
      RETURN {} # Placeholder

    METHOD generate(PARAMETERS data: dict) RETURNS str
      DESCRIPTION "将 Python 字典生成为格式化的 JSON 文本。"
      # Use built-in JSON library.
      # RETURN CALL json.dumps(data, indent=2) # Use indentation for readability
      RETURN "" # Placeholder
```

File: src_mcpc/mccp/file_manager.mcpc

```
# MCCP Symbol-Pseudo Code

MODULE mccp_toolchain.mccp.file_manager
  DESCRIPTION "文件管理模块，负责处理项目目录结构、文件读写等文件系统操作。"

  CLASS FileManager
    DESCRIPTION "文件管理器类，提供文件和目录操作的封装。"

    # Dependencies
    ATTRIBUTE config_manager: ConfigManager
    # Internal libraries
    ATTRIBUTE os_module: object # Reference to the 'os' module
    ATTRIBUTE pathlib_module: object # Reference to the 'pathlib' module

    METHOD __init__(PARAMETERS config_manager: ConfigManager)
      DESCRIPTION "初始化文件管理器。"
      SET self.config_manager = config_manager
      SET self.os_module = IMPORT "os"
      SET self.pathlib_module = IMPORT "pathlib"

    METHOD create_project_structure(PARAMETERS project_path: str) RETURNS bool
      DESCRIPTION "根据 MCCP 规范和配置，创建标准的项目目录结构和初始文件（如 mccp_config.json）。"
      # Define standard directories (or get from config if possible, but initial config needs to exist first)
      # Standard directories: config, src_mcbc, src_mcpc, mccp_symbols, src_target, temp
      # directory_names = ["config", "src_mcbc", "src_mcpc", "mccp_symbols", "src_target", "temp"]

      # Create root project directory
      # CALL self.os_module.makedirs(project_path, exist_ok=True)

      # FOR each dir_name in directory_names DO
        # dir_path = JOIN_PATHS(project_path, dir_name)
        # CALL self.os_module.makedirs(dir_path, exist_ok=True)
      # END FOR

      # Create initial mccp_config.json (requires default content)
      # default_config_content = CALL self.config_manager.get_default_config_json() # Assuming ConfigManager can provide defaults
      # config_file_path = JOIN_PATHS(project_path, "mccp_config.json")
      # success = CALL self.write_file(config_file_path, default_config_content)

      # Create initial requirements.md
      # default_requirements_content = "# Project Requirements\n\n..." # Define default
      # requirements_file_path = CALL self.get_file_path(project_path, "requirements_dir", "requirements.md") # Needs requirements_dir mapping
      # success = success AND CALL self.write_file(requirements_file_path, default_requirements_content)

      # RETURN success # True if all steps succeeded
      RETURN True # Placeholder

    METHOD read_file(PARAMETERS file_path: str) RETURNS str | None
      DESCRIPTION "读取文件内容，返回字符串。文件不存在或读取失败返回 None。"
      # USE TRY-EXCEPT BLOCK
      # TRY:
        # OPEN file_path in read mode ('r') with UTF-8 encoding
        # content = READ ALL content from file
        # CLOSE file
        # RETURN content
      # EXCEPT FileNotFoundError:
        # LOG WARNING f"File not found: {file_path}"
        # RETURN None
      # EXCEPT Exception as e: # Catch other potential errors (permissions, etc.)
        # LOG ERROR f"Failed to read file {file_path}: {e}"
        # RETURN None
      # END TRY-EXCEPT
       RETURN "File content placeholder." # Placeholder

    METHOD write_file(PARAMETERS file_path: str, content: str) RETURNS bool
      DESCRIPTION "将内容写入文件。如果父目录不存在则创建。写入成功返回 True，失败返回 False。"
      # USE TRY-EXCEPT BLOCK
      # TRY:
        # parent_dir = GET PARENT DIRECTORY of file_path
        # CALL self.os_module.makedirs(parent_dir, exist_ok=True) # Create parent directories if they don't exist
        # OPEN file_path in write mode ('w') with UTF-8 encoding
        # WRITE content to file
        # CLOSE file
        # RETURN True
      # EXCEPT Exception as e:
        # LOG ERROR f"Failed to write file {file_path}: {e}"
        # RETURN False
      # END TRY-EXCEPT
       RETURN True # Placeholder

    METHOD get_file_path(PARAMETERS project_path: str, layer_key: str, file_name: str) RETURNS str
      DESCRIPTION "根据配置的层级映射和文件名生成文件的完整路径。"
      # Get the directory name for the layer from config
      # layer_dir_name = CALL self.config_manager.get_layer_dir(layer_key)
      # IF layer_dir_name IS None THEN
        # LOG ERROR f"Layer directory not found in config for key: {layer_key}"
        # RETURN "" # Or raise exception
      # END IF
      # Construct the full path
      # full_path = JOIN_PATHS(project_path, layer_dir_name, file_name)
      # RETURN full_path
      RETURN f"{project_path}/{layer_key}/{file_name}" # Placeholder

    METHOD list_files_in_layer(PARAMETERS project_path: str, layer_key: str, extension: str) RETURNS list[str]
      DESCRIPTION "列出指定层级目录下匹配扩展名的所有文件路径。"
      # Get the full path to the layer directory
      # layer_dir_path = CALL self.get_file_path(project_path, layer_key, "") # Pass empty file_name to get directory path

      # Check if the directory exists
      # IF NOT CALL self.os_module.path.isdir(layer_dir_path) THEN
         # LOG WARNING f"Layer directory not found: {layer_dir_path}. Returning empty list."
         # RETURN []
      # END IF

      # Use pathlib to list files with the specified extension
      # path_object = self.pathlib_module.Path(layer_dir_path)
      # file_paths = []
      # FOR each file_path_obj in CALL path_object.glob(f'*.{extension}') DO
         # IF file_path_obj IS a file THEN
            # ADD STRING(file_path_obj) to file_paths list
         # END IF
      # END FOR

      # RETURN file_paths
       RETURN [f"{project_path}/{layer_key}/example1{extension}", f"{project_path}/{layer_key}/example2{extension}"] # Placeholder

  FUNCTION get_project_root_from_path(PARAMETERS any_path_within_project: str) RETURNS str | None
    DESCRIPTION "给定项目内的任意路径，向上查找 mccp_config.json 所在的目录作为项目根目录。"
    # Start with the given path
    # current_path = CALL self.os_module.path.abspath(any_path_within_project)

    # LOOP indefinitly (or until root is reached)
    # WHILE TRUE DO
      # config_file = JOIN_PATHS(current_path, "mccp_config.json")
      # IF CALL self.os_module.path.exists(config_file) THEN
        # RETURN current_path # Found the root
      # END IF
      # Move up one directory
      # parent_path = CALL self.os_module.path.dirname(current_path)
      # IF parent_path == current_path THEN # Reached the filesystem root
        # BREAK
      # END IF
      # SET current_path = parent_path
    # END WHILE

    # RETURN None # Config file not found in any parent directory
    RETURN "/path/to/project/root" # Placeholder
```

File: src_mcpc/mccp/symbols.mcpc

```
# MCCP Symbol-Pseudo Code

MODULE mccp_toolchain.mccp.symbols
  DESCRIPTION "分布式符号表管理模块，负责加载、保存、查找和更新符号定义。"

  CLASS SymbolTableManager
    DESCRIPTION "符号表管理器类，管理项目中的所有分布式符号表文件。"

    # Dependencies
    ATTRIBUTE file_manager: FileManager
    ATTRIBUTE config_manager: ConfigManager
    ATTRIBUTE json_parser: JsonParser # Dependency added for parsing/generating JSON

    # Internal state
    ATTRIBUTE _symbol_data_map: dict # Dictionary mapping module_name to its symbol data (dict)

    METHOD __init__(PARAMETERS file_manager: FileManager, config_manager: ConfigManager)
      DESCRIPTION "初始化符号表管理器，存储依赖。符号加载需调用 load_all_symbol_tables。"
      SET self.file_manager = file_manager
      SET self.config_manager = config_manager
      # Assume JsonParser can be instantiated directly or is provided? Let's assume instantiation for MCPC simplicity.
      SET self.json_parser = CREATE JsonParser()
      SET self._symbol_data_map = {} # Initialize empty map

    METHOD load_all_symbol_tables(PARAMETERS project_path: str) RETURNS None
      DESCRIPTION "加载 mccp_symbols 目录下的所有 symbols.json 文件到内存。"
      # Get the directory key for symbol tables from config
      # symbol_dir_key = "symbol_table_root" # From mccp_config.json layer_mapping
      # symbol_file_extension = "json"

      # List all symbol files in the designated directory
      # symbol_file_paths = CALL self.file_manager.list_files_in_layer(project_path, symbol_dir_key, symbol_file_extension)

      # FOR each symbol_file_path in symbol_file_paths DO
        # content = CALL self.file_manager.read_file(symbol_file_path)
        # IF content IS NOT None THEN
          # parsed_data = CALL self.json_parser.parse(content)
          # IF parsed_data IS NOT None AND parsed_data has "module_name" key THEN
            # module_name = parsed_data["module_name"]
            # SET self._symbol_data_map[module_name] = parsed_data
            # LOG INFO f"Loaded symbols for module: {module_name}"
          # ELSE
            # LOG WARNING f"Failed to parse or found invalid format in symbol file: {symbol_file_path}"
          # END IF
        # ELSE
          # LOG WARNING f"Could not read symbol file: {symbol_file_path}"
        # END IF
      # END FOR

    METHOD save_all_symbol_tables() RETURNS None
      DESCRIPTION "将内存中的符号表数据保存回对应的 symbols.json 文件。"
      # Get the directory key for symbol tables from config
      # symbol_dir_key = "symbol_table_root" # From mccp_config.json layer_mapping
      # project_path = CALL self.config_manager.get_project_root() # Need access to project root - assuming config_manager stores it

      # IF project_path IS None THEN
         # LOG ERROR "Cannot save symbols: Project root not set."
         # RETURN
      # END IF

      # FOR each module_name, symbols_data in self._symbol_data_map DO
         # Determine the expected file name for this module (e.g., mccp_symbols_<module_name_snake_case>.json)
         # file_name = CALL self.derive_symbol_file_name(module_name) # Helper method, e.g., mccp_symbols/mccp_toolchain_ui.json
         # file_path = CALL self.file_manager.get_file_path(project_path, symbol_dir_key, file_name)

         # json_content = CALL self.json_parser.generate(symbols_data)
         # success = CALL self.file_manager.write_file(file_path, json_content)
         # IF NOT success THEN
            # LOG ERROR f"Failed to save symbols for module {module_name} to {file_path}"
         # END IF
      # END FOR

    METHOD find_symbol(PARAMETERS symbol_name: str, module_name: str | None) RETURNS dict | None
      DESCRIPTION "在所有加载的符号表中查找指定符号。"
      # IF module_name IS NOT None THEN
        # Check only the specified module's symbols
        # module_symbols_data = self._symbol_data_map.get(module_name)
        # IF module_symbols_data IS NOT None AND module_symbols_data has "symbols" key THEN
           # RETURN CALL mccp_toolchain.utils.find_in_list_by_key(module_symbols_data["symbols"], "name", symbol_name) # Use utils helper
        # ELSE
           # RETURN None # Module not found or has no symbols list
        # END IF
      # ELSE # Search across all modules
        # FOR each mod_name, mod_symbols_data in self._symbol_data_map DO
           # IF mod_symbols_data has "symbols" key THEN
              # symbol = CALL mccp_toolchain.utils.find_in_list_by_key(mod_symbols_data["symbols"], "name", symbol_name) # Use utils helper
              # IF symbol IS NOT None THEN
                 # RETURN symbol
              # END IF
           # END IF
        # END FOR
        # RETURN None # Symbol not found in any module
      # END IF
       RETURN {"name": symbol_name, "type": "placeholder", "module_name": module_name} # Placeholder

    METHOD update_symbol(PARAMETERS symbol_data: dict) RETURNS bool
      DESCRIPTION "更新或添加一个符号到对应的模块符号表。如果符号已存在且 is_frozen 为 true，则拒绝更新。"
      # REQUIRES symbol_data to have "name" and "module_name"
      # module_name = symbol_data.get("module_name")
      # symbol_name = symbol_data.get("name")

      # IF module_name IS None OR symbol_name IS None THEN
         # LOG ERROR "Invalid symbol data for update: Missing name or module_name."
         # RETURN False
      # END IF

      # IF self._symbol_data_map does NOT have module_name THEN
         # Create a new entry for the module
         # SET self._symbol_data_map[module_name] = { "module_name": module_name, "description": "Auto-generated module symbols.", "symbols": [] }
      # END IF

      # module_symbols_list = self._symbol_data_map[module_name].get("symbols", [])
      # existing_symbol_index = FIND_INDEX_OF_DICT_IN_LIST(module_symbols_list, "name", symbol_name) # Helper

      # IF existing_symbol_index IS NOT None THEN
        # existing_symbol = module_symbols_list[existing_symbol_index]
        # IF existing_symbol.get("is_frozen", False) THEN
          # LOG WARNING f"Attempted to update frozen symbol: {symbol_name} in module {module_name}. Update rejected."
          # RETURN False # Refuse update if frozen
        # ELSE
          # Update the existing symbol entry (e.g., merge data, prioritize new data)
          # MERGE symbol_data into existing_symbol_list[existing_symbol_index]
          # Ensure 'is_frozen' from existing symbol is kept if present
          # existing_symbol_list[existing_symbol_index]['description'] = symbol_data.get('description', existing_symbol.get('description', ''))
          # existing_symbol_list[existing_symbol_index]['type'] = symbol_data.get('type', existing_symbol.get('type', ''))
          # # ... update other fields like parameters, return_type, attributes, dependencies ...
          # LOG INFO f"Updated symbol: {symbol_name} in module {module_name}."
        # END IF
      # ELSE
        # Add the new symbol
        # ADD symbol_data to module_symbols_list
        # LOG INFO f"Added new symbol: {symbol_name} to module {module_name}."
      # END IF
      # Ensure the symbols list in the map is updated if it was a new list
      # self._symbol_data_map[module_name]["symbols"] = module_symbols_list

      # RETURN True # Update successful
      RETURN True # Placeholder

    METHOD get_module_symbols(PARAMETERS module_name: str) RETURNS dict
      DESCRIPTION "获取指定模块的符号表数据。"
      # RETURN self._symbol_data_map.get(module_name, {})
      RETURN {} # Placeholder

    # Helper method to derive the symbol file name for a module
    METHOD derive_symbol_file_name(PARAMETERS module_name: str) RETURNS str
       DESCRIPTION "根据模块名生成对应的 symbols.json 文件名。"
       # Example: module_name = "mccp_toolchain.ui" -> "mccp_symbols_mccp_toolchain_ui.json"
       # Replace dots with underscores, prepend "mccp_symbols_", append ".json"
       # RETURN "mccp_symbols_" + module_name.replace(".", "_") + ".json"
       RETURN f"mccp_symbols_{module_name.replace('.', '_')}.json" # Placeholder


  # Symbol data structure description - not active pseudocode
  # CLASS Symbol ... (attributes defined in initial symbols.json)
END CLASS

# Helper function needed for list search
FUNCTION FIND_INDEX_OF_DICT_IN_LIST(PARAMETERS list_data: list[dict], key_name: str, key_value: any) RETURNS int | None
   DESCRIPTION "在字典列表中按键值查找字典的索引。"
   # FOR index, item in ENUMERATE list_data DO
      # IF item.get(key_name) == key_value THEN
         # RETURN index
      # END IF
   # END FOR
   # RETURN None
   RETURN None # Placeholder
```

File: src_mcpc/mccp/config.mcpc

```
# MCCP Symbol-Pseudo Code

MODULE mccp_toolchain.mccp.config
  DESCRIPTION "MCCP 配置管理模块，负责加载、解析和提供项目配置。"

  CLASS ConfigManager
    DESCRIPTION "配置管理器类，加载并提供 mccp_config.json 的配置数据。"

    # Dependencies
    ATTRIBUTE file_manager: FileManager
    ATTRIBUTE json_parser: JsonParser # Dependency added for parsing JSON

    # Internal state
    ATTRIBUTE _config_data: dict # Dictionary to hold loaded config
    ATTRIBUTE _project_root: str | None # Store the project root once loaded

    METHOD __init__(PARAMETERS file_manager: FileManager)
      DESCRIPTION "初始化配置管理器。"
      SET self.file_manager = file_manager
      # Assume JsonParser can be instantiated directly or is provided? Let's assume instantiation.
      SET self.json_parser = CREATE JsonParser()
      SET self._config_data = {}
      SET self._project_root = None

    METHOD load_config(PARAMETERS project_path: str) RETURNS bool
      DESCRIPTION "从项目目录加载 mccp_config.json 文件并解析。"
      SET self._project_root = project_path # Store the project root

      # Construct the full path to the config file
      # config_file_name = "mccp_config.json"
      # config_file_path = JOIN_PATHS(project_path, config_file_name) # mccp_config.json is at project root

      # Read file content
      # content = CALL self.file_manager.read_file(config_file_path)
      # IF content IS None THEN
        # LOG ERROR f"Failed to read config file: {config_file_path}"
        # SET self._config_data = {} # Reset config
        # RETURN False
      # END IF

      # Parse JSON content
      # parsed_data = CALL self.json_parser.parse(content)
      # IF parsed_data IS NOT None THEN
        # SET self._config_data = parsed_data
        # LOG INFO f"Config loaded successfully from {config_file_path}."
        # RETURN True
      # ELSE
        # LOG ERROR f"Failed to parse JSON config file: {config_file_path}"
        # SET self._config_data = {} # Reset config
        # RETURN False
      # END IF
       SET self._config_data = { # Placeholder config data
           "project_name": "mccp-toolchain",
           "layer_mapping": {
             "requirements_dir": "requirements",
             "behavior_code_dir": "src_mcbc",
             "pseudo_code_dir": "src_mcpc",
             "target_code_dir": "mccp_toolchain",
             "symbol_table_root": "mccp_symbols",
             "config_dir": "config" # Added config dir mapping for consistency
           },
           "build_rules": {
              "mcbc_to_mcpc": {
                 "input_layer_dir_key": "behavior_code_dir", # Added keys linking rules to layer mapping
                 "output_layer_dir_key": "pseudo_code_dir",
                 "input_extension": ".mcbc",
                 "output_extension": ".mcpc",
                 "source_parser": "McbcParser", # Added parser keys
                 "target_parser": "McpcParser",
                 "llm_prompt": "..."
              }
              # ... other rules
           },
           "llm_settings": { "model": "..." }
         }
       SET self._project_root = project_path # Store the root path
       RETURN True # Placeholder

    METHOD get_setting(PARAMETERS key: str) RETURNS any
      DESCRIPTION "根据键路径获取配置值。支持嵌套路径访问。"
      # Walk through the dictionary using dot-separated key parts.
      # parts = SPLIT key BY "."
      # current_value = self._config_data
      # FOR each part in parts DO
        # IF current_value IS a DICTIONARY AND current_value has key part THEN
          # SET current_value = current_value[part]
        # ELSE
          # LOG WARNING f"Config setting not found for key path: {key}"
          # RETURN None # Or raise error, or return default
        # END IF
      # END FOR
      # RETURN current_value
       RETURN "Placeholder setting value" # Placeholder

    METHOD get_layer_dir(PARAMETERS layer_key: str) RETURNS str | None
      DESCRIPTION "获取指定层级对应的目录名。"
      # RETURN CALL self.get_setting(f"layer_mapping.{layer_key}")
       # Use placeholder config for demonstration
       layer_mapping = self._config_data.get("layer_mapping", {})
       RETURN layer_mapping.get(layer_key) # Placeholder using internal placeholder config

    METHOD get_build_rule(PARAMETERS rule_key: str) RETURNS dict | None
      DESCRIPTION "获取指定构建规则的详细配置 (input_extension, output_extension, llm_prompt等)。"
      # Check in 'build_rules' and 'reverse_build_rules'
      # build_rules = self._config_data.get("build_rules", {})
      # IF build_rules has key rule_key THEN RETURN build_rules[rule_key]
      # reverse_rules = self._config_data.get("reverse_build_rules", {})
      # IF reverse_rules has key rule_key THEN RETURN reverse_rules[rule_key]
      # LOG WARNING f"Build rule not found for key: {rule_key}"
      # RETURN None

      # Use placeholder config for demonstration
      build_rules = self._config_data.get("build_rules", {})
      IF build_rules has key rule_key THEN RETURN build_rules[rule_key]
      # Add check for reverse rules if placeholder config included them
      RETURN None # Placeholder using internal placeholder config

    METHOD get_config_data() RETURNS dict
       DESCRIPTION "获取完整的配置数据字典。"
       RETURN self._config_data

    METHOD get_project_root() RETURNS str | None
        DESCRIPTION "获取当前加载的项目根目录路径。"
        RETURN self._project_root

END CLASS
```

File: src_mcpc/mccp/utils.mcpc

```
# MCCP Symbol-Pseudo Code

MODULE mccp_toolchain.utils
  DESCRIPTION "通用工具模块，提供各种辅助函数。"

  FUNCTION normalize_path(PARAMETERS path: str) RETURNS str
    DESCRIPTION "规范化文件路径，处理斜杠、相对路径等。"
    # USE pathlib for robust path handling
    # path_obj = CALL pathlib.Path(path)
    # normalized_path_obj = CALL path_obj.resolve() # Resolves symlinks, .. components
    # RETURN STRING(normalized_path_obj)
    RETURN path # Placeholder

  FUNCTION validate_file_name(PARAMETERS file_name: str) RETURNS bool
    DESCRIPTION "验证文件名是否符合命名规范 (snake_case)。"
    # Use regular expression to check for snake_case pattern
    # pattern = r"^[a-z0-9_]+\.[a-z]+$" # Allows lowercase, numbers, underscores, one dot for extension
    # IF CALL re.fullmatch(pattern, file_name) THEN
      # RETURN True
    # ELSE
      # RETURN False
    # END IF
     # Basic check:
     # IF file_name CONTAINS " " OR file_name CONTAINS "-" THEN RETURN False
     # IF file_name CONTAINS UPPECASE_LETTERS THEN RETURN False
     # RETURN True # Simplified placeholder logic
     RETURN True # Placeholder

  FUNCTION snake_to_pascal_case(PARAMETERS text: str) RETURNS str
    DESCRIPTION "将 snake_case 字符串转换为 PascalCase。"
    # parts = SPLIT text BY "_"
    # pascal_parts = []
    # FOR each part in parts DO
      # ADD CAPITALIZE(part) to pascal_parts
    # END FOR
    # RETURN JOIN pascal_parts
    RETURN text # Placeholder

  FUNCTION pascal_to_snake_case(PARAMETERS text: str) RETURNS str
    DESCRIPTION "将 PascalCase 字符串转换为 snake_case。"
    # Use regex to insert underscore before uppercase letters (except the first) and convert to lowercase.
    # s1 = CALL re.sub('(.)([A-Z][a-z]+)', r'\1_\2', text)
    # s2 = CALL re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()
    # RETURN s2
    RETURN text # Placeholder

  FUNCTION find_in_list_by_key(PARAMETERS list_data: list[dict], key_name: str, key_value: any) RETURNS dict | None
   DESCRIPTION "在字典列表中按键值查找字典。"
   # FOR each item in list_data DO
      # IF item IS a DICTIONARY AND item.get(key_name) == key_value THEN
         # RETURN item
      # END IF
   # END FOR
   # RETURN None
   RETURN None # Placeholder
```

更新后的分布式符号表

*Note: The symbol tables below reflect the initial state from the reference *plus* refinements and additions identified during the MCPC pseudocode generation. This includes clarifying dependencies, potentially adding parameters/return types if more specific than the initial "object" or "any", and adding symbols for concepts that became clearer (like helper methods or internal data structures if deemed significant).*

Updated Symbol Table: src/mccp/symbols.json

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
          "dependencies": ["PyQt5.QtWidgets.QFileSystemModel"]
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
          "dependencies": ["mccp_toolchain.mccp.file_manager.FileManager.create_project_structure", "mccp_toolchain.ui.MainWindow.open_project"]
        },
        {
          "name": "handle_open_project",
          "parameters": [],
          "return_type": "None",
          "description": "处理打开现有项目的用户操作，弹出文件对话框选择项目目录，然后调用 open_project 加载并更新文件树。",
          "dependencies": ["mccp_toolchain.mccp.file_manager.FileManager.get_project_root_from_path", "mccp_toolchain.ui.MainWindow.open_project"]
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
             "mccp_toolchain.mccp.file_manager.FileManager.get_project_root_from_path",
             "mccp_toolchain.mccp.config.ConfigManager.load_config",
             "mccp_toolchain.mccp.symbols.SymbolTableManager.load_all_symbol_tables",
             "mccp_toolchain.ui.MainWindow.update_file_tree",
             "mccp_toolchain.ui.MainWindow.log_message"
          ]
        },
        {
          "name": "handle_run_build",
          "parameters": [
            {"name": "target_layer", "type": "str", "description": "构建目标层级 ('mcbc', 'mcpc', 'code')"}
          ],
          "return_type": "None",
          "description": "处理触发构建流程的用户操作，调用 BuildOrchestrator。",
          "dependencies": ["mccp_toolchain.core.build.BuildOrchestrator.run_forward_build", "mccp_toolchain.ui.MainWindow.log_message", "mccp_toolchain.ui.MainWindow.update_file_tree"]
        }
      ]
    }
  ]
}
```

Updated Symbol Table: src/mccp/core/build/symbols.json

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
            {"name": "end_layer_key", "type": "str", "description": "结束层级键 ('mcpc', 'code')"}
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
           "dependencies": ["mccp_toolchain.mccp.config.ConfigManager.get_build_rule"] # Or get_build_rules/get_reverse_build_rules if added
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
           "dependencies": [] # Likely uses os.path or pathlib internally, not other MCCP symbols
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
            "mccp_toolchain.mccp.parsers" # General dependency on parsers module
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
             "mccp_toolchain.mccp.symbols.SymbolTableManager.get_all_symbols", # Assuming this helper exists
             "mccp_toolchain.mccp.symbols.SymbolTableManager.update_symbol",
             "mccp_toolchain.core.llm.PromptGenerator", # Need to instantiate it? Or inject? Symbol table says Class, so instantiate.
             "mccp_toolchain.core.llm.LLMClient.generate_content",
             "mccp_toolchain.core.llm.LLMClient.parse_response" # If used for initial response structuring
             # Also depends on the specific source/target parsers passed in __init__
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

Updated Symbol Table: src/mccp/core/llm/symbols.json

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
          "dependencies": ["langchain.llms", "mccp_toolchain.mccp.config.ConfigManager.get_setting"]
        },
        {
          "name": "generate_content",
          "parameters": [
            {"name": "prompt", "type": "str", "description": "发送给 LLM 的提示词"},
            {"name": "context", "type": "dict", "description": "包含上下文信息的字典 (e.g., source_content, config, symbols, file_paths)"}
          ],
          "return_type": "str",
          "description": "根据提示词和上下文调用 LLM 生成内容，返回原始文本响应。",
          "dependencies": ["langchain.prompts", "langchain.chains"] # Or specific Langchain model invoke/predict
        },
         {
          "name": "parse_response",
          "parameters": [
            {"name": "response_text", "type": "str", "description": "LLM 返回的原始文本"},
            {"name": "target_format", "type": "str", "description": "期望的目标格式标识符 (e.g., 'mcbc', 'mcpc', 'python_code', 'json')"}
          ],
          "return_type": "object",
          "description": "解析 LLM 返回的文本，将其结构化或验证格式。可能委托给特定的解析器。",
          "dependencies": ["mccp_toolchain.mccp.parsers"] # Depends on the module providing parsers
          # Specific dependencies on parser classes like McbcParser, McpcParser, TargetCodeParser, JsonParser implied by description/pseudocode
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
           "dependencies": ["mccp_toolchain.mccp.config.ConfigManager.get_build_rule"]
        }
      ]
    }
  ]
}
```

Updated Symbol Table: src/mccp/parsers/symbols.json

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

Updated Symbol Table: src/mccp/symbols/symbols.json

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
          "dependencies": ["mccp_toolchain.utils.find_in_list_by_key"] # Or a similar helper to find index
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
           "dependencies": [] # String manipulation
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

Updated Symbol Table: src/mccp/file_manager/symbols.json

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
          "dependencies": ["mccp_toolchain.mccp.config.ConfigManager", "mccp_toolchain.mccp.parsers.JsonParser", "os"]
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
          "dependencies": ["mccp_toolchain.mccp.config.ConfigManager.get_layer_dir", "pathlib"]
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
  ]
}
```

Updated Symbol Table: src/mccp/config/symbols.json

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
            {"name": "key", "type": "str", "description": "配置项的键路径 (e.g., 'llm_settings.model')"}
          ],
          "return_type": "any",
          "description": "根据键路径获取配置值。支持嵌套路径访问。",
          "dependencies": [] # String/dict manipulation
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

Updated Symbol Table: src/mccp/utils/symbols.json

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
     }
  ]
}
```
