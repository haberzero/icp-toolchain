# MCCP Behavior Code Document - mccp-toolchain

This document describes the intended behavior and responsibilities of the core modules within the `mccp-toolchain` project, based on the provided software requirements, symbol tables, and configuration context. Each section represents the content of a distinct Behavior Code (`.mcbc`) file.

## File: src_mcbc/ui.mcbc

```markdown
# MCCP Behavior Code

## Module: mccp_toolchain.ui

### Overview
- Purpose: Provide the graphical user interface for the mccp-toolchain, enabling user interaction and visualization of the project state.
- Responsibilities:
    - Display the project's file structure.
    - Capture user commands for project management (new, open) and build processes.
    - Present feedback, progress, errors, and warnings to the user.
    - Integrate with core backend services for action execution.
- Interactions: Primarily interacts with `core.build` to trigger transformations and with `mccp.file_manager` for project file system representation and management.

### Components

#### Class: MainWindow
- Description: The main application window component, serving as the central hub for the user interface and interaction points. Inherits from a standard window class (e.g., PyQt QMainWindow).
- Behaviors:
    - Initialization (`__init__`):
        - Purpose: Establish the foundational state of the main window and inject necessary dependencies from the core system.
        - Process: Sets up initial window properties. Accepts and stores instances of core orchestrator and file management services. Prepares the UI structure but does not necessarily populate it with data yet.
        - Dependencies: Relies on external instances of `mccp_toolchain.core.build.BuildOrchestrator` and `mccp_toolchain.mccp.file_manager.FileManager` being provided upon creation.
    - Setup UI (`setup_ui`):
        - Purpose: Construct and arrange all visual elements that make up the user interface within the main window.
        - Process: Creates UI controls such as the file tree view area, menu bar, toolbars, buttons for actions, and a status or log display area. Configures their layout and appearance using the UI framework (PyQt).
        - Output: A fully laid out, but not yet functional (signal-connected), user interface within the window.
        - Dependencies: Utilizes components from the PyQt5 framework (`PyQt5.QtWidgets`, `PyQt5.QtGui`, `PyQt5.QtCore`).
    - Connect Signals (`connect_signals`):
        - Purpose: Link user-generated events from UI controls (like button clicks or menu selections) to the corresponding internal methods that handle these actions.
        - Process: Establishes the connections required by the UI framework's signal/slot mechanism. Maps specific signals (e.g., button `clicked`) to designated handler methods within this class.
        - Interactions: This step enables the UI to trigger operations managed by other core modules, such as initiating builds or managing files.
    - Update File Tree (`update_file_tree`):
        - Purpose: Refresh and populate the file structure tree view with the current contents of the specified project directory.
        - Process: Configures a file system model to point to the project's root directory. Associates this model with the tree view widget to display the directory and file hierarchy dynamically.
        - Input: The absolute path to the root directory of the currently open project (`project_root`).
        - Output: A visual representation of the project's file system structure displayed in the UI.
        - Dependencies: Specifically uses `PyQt5.QtWidgets.QFileSystemModel` to interface with the file system.
    - Log Message (`log_message`):
        - Purpose: Provide textual feedback to the user regarding ongoing operations, status updates, or issues encountered by the toolchain.
        - Process: Accepts a message string and displays it in a designated area of the UI, such as the status bar at the bottom of the window or within a dedicated log panel.
        - Input: The message string to be displayed (`message`).
    - Handle New Project (`handle_new_project`):
        - Purpose: Respond to the user's intent to create a new MCCP project.
        - Process: Typically involves prompting the user via a dialog for details like the project name and location. Delegates the actual creation of the project's standard directory structure and initial configuration files to the file manager service. Updates the UI upon successful creation to display the new project.
        - Interactions: Initiates a `create_project_structure` operation on the injected `FileManager` instance.
    - Handle Open Project (`handle_open_project`):
        - Purpose: Respond to the user's intent to open an existing MCCP project.
        - Process: Presents a file selection dialog allowing the user to choose the project's root directory. Upon selection, it instructs the file manager to load project-specific data (like config and symbols) and updates the file tree view to display the opened project's structure.
        - Interactions: Interacts with the `FileManager` (e.g., `get_project_root_from_path`, potentially triggering config and symbol loading via managers), and uses file dialogs from the UI framework.
    - Handle Run Build (`handle_run_build`):
        - Purpose: Respond to the user's command to execute a build or transformation process between MCCP layers.
        - Process: Determines the desired transformation target layer (e.g., from requirements to behavior code, or pseudo-code to target code) based on the UI context or user selection. Delegates the complex orchestration of this process to the Build Orchestrator service. Provides user feedback during the build process via logging.
        - Input: An identifier specifying the target layer for the build process (`target_layer`).
        - Interactions: Calls the `run_forward_build` method on the injected `BuildOrchestrator` instance.
```

## File: src_mcbc/core/build.mcbc

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
        - Input: Project root path (`project_path`), the starting layer identifier (`start_layer`), and the ending layer identifier (`end_layer`).
        - Output: A boolean indicating whether the build process completed successfully.
        - Interactions: Coordinates multiple calls to `mccp_toolchain.core.build.LayerTransformer` and potentially file/symbol management operations.
    - Run Reverse Build (`run_reverse_build`):
        - Purpose: Execute the sequence of transformations from a lower-level layer to a higher-level layer, typically starting from target code and moving towards behavior code or requirements. (Note: Marked as frozen/pending implementation in symbols).
        - Process: (Planned) Similar to forward build, but follows the reverse sequence of layers. Identifies necessary steps (e.g., target code to `.mcpc`, `.mcpc` to `.mcbc`). Delegates transformations to `LayerTransformer` instances. Coordinates file and symbol management updates based on reverse engineering insights. Reports success or failure.
        - Input: Project root path (`project_path`), the starting layer identifier (`start_layer`), and the ending layer identifier (`end_layer`).
        - Output: A boolean indicating whether the reverse build process completed successfully (when implemented).
        - Interactions: (Planned) Coordinates calls to `mccp_toolchain.core.build.LayerTransformer` and file/symbol management operations, focusing on extracting structure and meaning.

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

## File: src_mcbc/core/llm.mcbc

```markdown
# MCCP Behavior Code

## Module: mccp_toolchain.core.llm

### Overview
- Purpose: Integrate the mccp-toolchain with large language models (LLMs) to facilitate the AI-driven transformation of content between architectural layers.
- Responsibilities:
    - Manage the connection and interaction with the configured LLM service.
    - Generate structured prompts containing all necessary context for the LLM.
    - Send prompts to the LLM and receive responses.
    - Parse or validate the format of the LLM's textual responses.
- Interactions: Primarily interacts with `mccp.config` to get LLM settings and `mccp.symbols` to include symbol information in prompts. Used by `core.build.LayerTransformer` to perform actual transformations. Relies on the Langchain library for underlying LLM communication.

### Components

#### Class: LLMClient
- Description: A service client that encapsulates the logic for communicating with a large language model, abstracting the details of the underlying LLM framework (Langchain).
- Behaviors:
    - Initialization (`__init__`):
        - Purpose: Configure the LLM client based on the project settings and prepare the connection to the specific LLM model.
        - Process: Reads LLM-specific configuration (like model name, API URL, API key) from the provided configuration manager. Sets up the underlying LLM interaction object using the specified framework (Langchain).
        - Dependencies: Requires an instance of `mccp_toolchain.mccp.config.ConfigManager` to fetch settings and uses libraries from the `langchain` framework.
    - Generate Content (`generate_content`):
        - Purpose: Send a structured prompt and additional context to the LLM and obtain a generated textual response.
        - Process: Takes the prepared prompt and context (which may include source content, configuration, symbols) and passes them to the configured LLM via the underlying framework (Langchain). Handles the communication protocol and waits for the LLM's output.
        - Input: The prompt string to send (`prompt`), and a dictionary containing supplementary context data (`context`).
        - Output: The raw textual response received from the LLM (`str`).
        - Dependencies: Uses prompt and chain objects from the `langchain` framework (`langchain.prompts`, `langchain.chains`).
    - Parse Response (`parse_response`):
        - Purpose: Process the raw text output from the LLM to validate its format or extract structured data based on the expected target format.
        - Process: Examines the `response_text` based on the specified `target_format` (e.g., 'mcbc', 'mcpc', 'python_code'). This might involve checking for specific Markdown structures, JSON format (for MCBC/MCPC), or parsing code syntax. It could also involve basic validation against expected structures.
        - Input: The raw text response from the LLM (`response_text`) and a string indicating the expected format (`target_format`).
        - Output: A structured representation of the parsed content (e.g., a dictionary or code AST) or the validated text itself. Returns an object, which might be a string, dict, or other structure depending on the format.

#### Class: PromptGenerator
- Description: Responsible for assembling the complete, detailed prompt string that will be sent to the LLM, incorporating all necessary information for the transformation task.
- Behaviors:
    - Initialization (`__init__`):
        - Purpose: Prepare the prompt generator by providing access to the configuration manager.
        - Process: Stores a reference to the configuration manager, which contains prompt templates and other settings required for prompt construction.
    - Generate Prompt (`generate_prompt`):
        - Purpose: Create a comprehensive prompt by combining a base instruction template (from config) with specific context data relevant to the current transformation step.
        - Process: Retrieves the base prompt template for the given `build_rule_key` from the configuration manager. Incorporates the `source_content`, relevant `symbols` data, and the overall `config` into the template. Formats these pieces together into a single, coherent prompt string designed to guide the LLM's generation towards the desired output format and content.
        - Input: A key identifying the build rule (`build_rule_key`), the content of the source file (`source_content`), relevant symbol data (`symbols`), and the full project configuration (`config`).
        - Output: The complete, formatted prompt string ready to be sent to the LLM (`str`).
        - Dependencies: Relies on the `mccp_toolchain.mccp.config.ConfigManager` to retrieve prompt templates and configuration details.
```

## File: src_mcbc/mccp/file_manager.mcbc

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
        - Output: The content of the file as a string, or `None` if the file could not be read (e.g., not found).
    - Write File (`write_file`):
        - Purpose: Write provided content to a specified file.
        - Process: Ensures the parent directories for the `file_path` exist, creating them if necessary. Opens the file in write mode (overwriting existing content). Writes the `content` string to the file. Handles potential errors during writing.
        - Input: The path where the file should be written (`file_path`) and the content string (`content`).
        - Output: A boolean indicating whether the write operation was successful.
    - Get File Path (`get_file_path`):
        - Purpose: Construct the full, absolute file system path for a file located within a specific MCCP project layer, given its simple name.
        - Process: Takes the project root path. Uses the `ConfigManager` to look up the directory name corresponding to the `layer_key` (e.g., 'behavior_code_dir' maps to 'src_mcbc'). Combines the project root, the layer directory name, and the `file_name` using appropriate path separators.
        - Input: Project root path (`project_path`), the key identifying the layer (`layer_key`), and the simple name of the file (`file_name`).
        - Output: The complete file path as a string.
    - List Files in Layer (`list_files_in_layer`):
        - Purpose: Find and list all files with a specific extension within a designated layer directory of the project.
        - Process: Determines the full path of the layer directory using `get_file_path` (without a file name). Scans this directory recursively or non-recursively (depending on requirement) for files. Filters the list to include only files matching the specified `extension`. Returns a list of paths.
        - Input: Project root path (`project_path`), the key identifying the layer (`layer_key`), and the desired file extension (`extension`).
        - Output: A list of strings, where each string is the path to a file matching the criteria.

#### Function: Get Project Root From Path (`get_project_root_from_path`)
- Description: Given a path that is believed to be somewhere within an MCCP project, attempt to locate the project's root directory.
- Behavior:
    - Purpose: Discover the project's base directory by searching upwards from a given path.
    - Process: Starts at the provided `any_path_within_project`. Checks if a known project indicator file (e.g., `mccp_config.json`) exists in the current directory. If found, that directory is the root. If not, moves up one directory level and repeats the check until the file is found or the file system root is reached.
    - Input: Any path string (`any_path_within_project`) potentially inside an MCCP project.
    - Output: The path string of the project root directory if found, otherwise `None`.
```

## File: src_mcbc/mccp/symbols.mcbc

```markdown
# MCCP Behavior Code

## Module: mccp_toolchain.mccp.symbols

### Overview
- Purpose: Manage the project's distributed symbol tables, which store structured definitions of code elements (classes, functions, variables, etc.) and their metadata.
- Responsibilities:
    - Load symbol definitions from multiple distributed symbol files (`mccp_symbols_*.json`) into memory.
    - Save in-memory symbol data back to the corresponding files.
    - Provide methods to search for specific symbols across all loaded tables.
    - Manage the creation, update, and merging of symbol definitions, respecting 'frozen' symbols.
    - Provide access to the symbols defined within a specific module.
- Interactions: Interacts with `mccp.file_manager` to read and write symbol files and with `mccp.config` to locate the symbols directory. Used by `core.build` and `core.llm` (via `PromptGenerator`) to access symbol information during transformations. Uses the `utils` module for search/data handling.

### Components

#### Class: SymbolTableManager
- Description: Manages the collection of distributed symbol tables for the entire project. Holds symbol data in memory and orchestrates persistence to the file system.
- Behaviors:
    - Initialization (`__init__`):
        - Purpose: Prepare the symbol manager by providing access to file and configuration services and loading existing symbol data.
        - Process: Accepts instances of the file manager and config manager. Upon initialization, it typically triggers the loading of all existing symbol table files from the project's symbol directory into an internal data structure.
        - Dependencies: Requires instances of `mccp_toolchain.mccp.file_manager.FileManager` and `mccp_toolchain.mccp.config.ConfigManager`.
    - Load All Symbol Tables (`load_all_symbol_tables`):
        - Purpose: Read all symbol definition files (`mccp_symbols_*.json`) from the project's designated symbol directory and store their content in memory.
        - Process: Uses the file manager to list all JSON files within the symbol table root directory (obtained from config). Reads each file's content using the file manager and parses the JSON data. Stores the parsed symbol data, organized by module or file name, in an internal dictionary or equivalent structure.
        - Input: Project root directory path (`project_path`).
    - Save All Symbol Tables (`save_all_symbol_tables`):
        - Purpose: Persist the current in-memory state of all symbol tables back to their respective JSON files on the file system.
        - Process: Iterates through the internal data structure holding the symbol data. For each set of symbols corresponding to a file, it generates the JSON string representation and uses the file manager to write the content back to the original file path.
    - Find Symbol (`find_symbol`):
        - Purpose: Search across all loaded symbol tables to locate a symbol definition by its name, optionally restricted to a specific module.
        - Process: Searches the internal symbol data structure. If `module_name` is provided, it searches only within that module's symbols. Otherwise, it searches across all modules. Returns the symbol data dictionary if found.
        - Input: The name of the symbol to find (`symbol_name`) and an optional module name to restrict the search (`module_name`).
        - Output: The dictionary containing the symbol's definition if found, otherwise `None`.
        - Dependencies: May use helper functions from the `mccp_toolchain.utils` module for search logic.
    - Update Symbol (`update_symbol`):
        - Purpose: Add a new symbol definition or modify an existing one within the appropriate module's symbol table.
        - Process: Takes a dictionary containing the symbol data, which must include `name` and `module_name`. Locates the symbol table for the specified module. If the symbol already exists and its `is_frozen` property is `true`, the update is rejected. Otherwise, the symbol definition is added or updated. The in-memory data is modified.
        - Input: A dictionary containing the symbol data to update or add (`symbol_data`).
        - Output: A boolean indicating whether the update was successful (i.e., not blocked by a frozen symbol).
    - Get Module Symbols (`get_module_symbols`):
        - Purpose: Retrieve all symbol definitions specifically belonging to a given module.
        - Process: Accesses the internal data structure and returns the subset of symbol data associated with the specified `module_name`.
        - Input: The name of the module (`module_name`).
        - Output: A dictionary or list containing all symbol definitions for that module.

#### Class: Symbol
- Description: Represents the structure and attributes of a single symbol definition as stored in the symbol tables. This is a data structure definition rather than an active component with behaviors.
- Attributes:
    - Name (`name`): The unique identifier for the symbol (e.g., class name, function name).
    - Type (`type`): Categorizes the symbol (e.g., 'class', 'function', 'variable', 'constant').
    - Description (`description`): A natural language explanation of the symbol's purpose or functionality.
    - Module Name (`module_name`): The dot-separated name of the module the symbol belongs to (e.g., 'mccp_toolchain.ui').
    - Dependencies (`dependencies`): A list of names of other symbols or modules that this symbol depends on.
    - Is Frozen (`is_frozen`): A boolean flag indicating whether the definition of this symbol (or the code generated from it) is protected from modification by automated tools like the LLM.
```

## File: src_mcbc/mccp/config.mcbc

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
```

## File: src_mcbc/utils.mcbc

```markdown
# MCCP Behavior Code

## Module: mccp_toolchain.utils

### Overview
- Purpose: Provide a collection of general-purpose utility functions that support various operations across different modules of the mccp-toolchain but do not belong to a specific core domain.
- Responsibilities:
    - Standardize file paths.
    - Validate string formats, particularly file names.
    - Convert between different naming conventions (snake_case, PascalCase).
- Interactions: Used by other modules as needed for common tasks like path manipulation or string formatting.

### Components

#### Function: Normalize Path (`normalize_path`)
- Description: Standardize the format of a given file path string.
- Behavior:
    - Purpose: Ensure paths are represented consistently, regardless of the original input format (e.g., handling different slash types, resolving relative paths, removing redundant components).
    - Process: Applies standard path normalization operations provided by the operating system or standard libraries.
    - Input: A file path string (`path`).
    - Output: The normalized file path string.

#### Function: Validate File Name (`validate_file_name`)
- Description: Check if a file name string conforms to a specified naming convention, such as snake_case.
- Behavior:
    - Purpose: Enforce naming standards for files generated or managed by the toolchain, ensuring consistency and compatibility with conventions defined in `mccp_config.json`.
    - Process: Uses regular expressions or string manipulation to verify that the `file_name` matches the expected pattern for the snake_case convention.
    - Input: The file name string to validate (`file_name`).
    - Output: A boolean value: `True` if the name is valid according to the convention, `False` otherwise.
    - Dependencies: Utilizes the standard `re` module for regular expression operations.

#### Function: Snake to Pascal Case (`snake_to_pascal_case`)
- Description: Convert a string from snake_case naming convention to PascalCase.
- Behavior:
    - Purpose: Support conversions between code elements (like function names in snake_case) and corresponding identifiers in other contexts (like class names or behavior descriptions often using PascalCase).
    - Process: Splits the input string by underscores (`_`). Capitalizes the first letter of each resulting segment. Joins the capitalized segments together without separators.
    - Input: A string formatted in snake_case (`text`).
    - Output: The converted string in PascalCase.

#### Function: Pascal to Snake Case (`pascal_to_snake_case`)
- Description: Convert a string from PascalCase naming convention to snake_case.
- Behavior:
    - Purpose: Support conversions from identifiers in PascalCase (like class names) to identifiers in snake_case (like variable names or internal function names), following common programming language conventions.
    - Process: Iterates through the input string, identifying uppercase letters that are not the first character. Inserts an underscore (`_`) before such uppercase letters. Converts the entire string to lowercase.
    - Input: A string formatted in PascalCase (`text`).
    - Output: The converted string in snake_case.
```
