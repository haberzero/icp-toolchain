import json
import os
import re
from typing import Any, Dict, List, Optional, Tuple

# A type alias for a structured representation of a parsed line.
# (line_number, indent_level, line_content)
ParsedLine = Tuple[int, int, str]

# A type alias for the Abstract Syntax Tree (AST) node structure.
AstNode = Dict[str, Any]


class MCBCAnalyzer:
    """
    Analyzes `.mcbc` files for syntax, extracts symbols, and updates a JSON symbol table.

    This class serves as the main engine for processing MCBC files. It maintains the
    state of the current working directory and active file, providing a set of public
    methods to control the analysis and symbol management process.

    Attributes:
        working_directory (Optional[str]): The absolute path to the folder being analyzed.
        active_file (Optional[str]): The name of the `.mcbc` file currently being processed.
        symbols_json_path (Optional[str]): The full path to the `mccp_symbols_single.json` file.
        symbols_data (Dict[str, Any]): The in-memory representation of the symbols JSON data.
        parsed_ast (Optional[AstNode]): The structured representation (AST) of the active file.
    """

    def __init__(self) -> None:
        """
        Initializes the MCBCAnalyzer with a clean state.
        """
        self.active_directory: Optional[str] = None
        self.active_file: Optional[str] = None
        self.active_file_path:  Optional[str] = None
        self.symbols_json_path: Optional[str] = None
        self.symbols_data: Dict[str, Any] = {}
        self.parsed_ast: Optional[AstNode] = None

    # --------------------------------------------------------------------------
    # Public API - Main Control Interface
    # --------------------------------------------------------------------------

    def set_active_directory(self, path: str) -> None:
        abs_path = os.path.abspath(path)
        if os.path.isfile(abs_path):
            self.active_directory = os.path.dirname(abs_path)
        elif os.path.isdir(abs_path):
            self.active_directory = abs_path
        else:
            raise FileNotFoundError(f"The specified path does not exist: {path}")

        self.symbols_json_path = self._get_symbols_json_path()
        self._ensure_symbols_json_exists()
        self._load_symbols_json()
        print(f"Working directory set to: {self.active_directory}")

    def set_active_file(self, filename: str) -> bool:
        if not self.active_directory:
            print("Error: Working directory is not set. Call set_working_directory() first.")
            return False

        file_path = os.path.join(self.active_directory, filename)
        if not os.path.exists(file_path):
            print(f"Error: File '{filename}' not found in '{self.active_directory}'.")
            return False
        
        self.active_file = filename
        self.active_file_path = file_path

        print(f"Active file set to: {self.active_file}")
        
    def start_file_analysis(self):
        # Automatically parse and validate the file when it's set.
        try:
            self._run_file_analysis()
            return self.parsed_ast is not None
        except ValueError as e:
            print(f"Error during analysis of '{self.active_file}': {e}")
            self.parsed_ast = None
            return False

    def update_all_func(self) -> None:
        self._update_symbols_by_type('func', is_top_level=True)

    def update_all_var(self) -> None:
        self._update_symbols_by_type('var', is_top_level=True)

    def update_all_class(self) -> None:
        self._update_symbols_by_type('class', is_top_level=True)

    def update_all_class_func(self) -> None:
        self._update_symbols_by_type('func', is_top_level=False)

    def update_all_class_var(self) -> None:
        self._update_symbols_by_type('var', is_top_level=False)

    def all_symbols_update(self) -> None:
        """
        Runs all `update_*` methods to perform a comprehensive symbol update for the active file.
        """
        if not self._is_ready_for_update():
            return
        print(f"\n--- Starting full symbol update for '{self.active_file}' ---")
        self.update_all_func()
        self.update_all_var()
        self.update_all_class()
        self.update_all_class_func()
        self.update_all_class_var()
        self._save_symbols_json()
        print(f"--- Full symbol update for '{self.active_file}' completed ---\n")

    def sync_specific_symbols(self) -> None:
        """
        Synchronizes descriptions for existing symbols in the JSON from the .mcbc file.
        """
        if not self._is_ready_for_update():
            return

        print(f"Syncing descriptions for symbols in '{self.active_file}'...")
        self._load_symbols_json() # Load the latest version
        file_base_name = os.path.splitext(self.active_file)[0]
        symbols_to_sync = {
            k: v for k, v in self.symbols_data.get("symbols_param", {}).items()
            if k.startswith(f"{file_base_name}.")
        }

        updated_count = 0
        for symbol_path, symbol_info in symbols_to_sync.items():
            path_parts = symbol_path.split('.')[1:] # Skip filename
            node = self._find_node_by_path(path_parts)

            if node and node.get('description'):
                # Note: The JSON spec was updated. We now only sync the `description` field.
                if self.symbols_data["symbols_param"][symbol_path].get('description') != node['description']:
                    self.symbols_data["symbols_param"][symbol_path]['description'] = node['description']
                    print(f"  - Synced description for '{symbol_path}'")
                    updated_count += 1
            elif node:
                 print(f"  - Warning: Symbol '{symbol_path}' exists in code but has no 'description' tag. Cannot sync.")
            else:
                 print(f"  - Warning: Symbol '{symbol_path}' not found in '{self.active_file}'. It may have been renamed or removed.")

        if updated_count > 0:
            self._save_symbols_json()
        else:
            print("No descriptions needed an update.")

    # --------------------------------------------------------------------------
    # Private Helper Methods - Analysis, Parsing, and Validation
    # --------------------------------------------------------------------------

    def _run_file_analysis(self) -> None:
        """Orchestrates the parsing and validation of the active file."""
        self.parsed_ast = {}

        print(f"Analyzing '{self.active_file}'...")
        parsed_lines = self._parse_mcbc_to_lines()
        if not parsed_lines:
            print("Analysis warning: File is empty or contains no valid content.")
            return

        self.parsed_ast = self._build_ast_from_lines(parsed_lines)
        self._perform_syntax_checks(self.parsed_ast)
        print("Analysis complete.")

    # Reads the active .mcbc file and converts it into a list of structured lines.
    def _parse_mcbc_to_lines(self) -> List[ParsedLine]:
        print("  - Step 1: Parsing file to lines...")
        if not self.active_directory or not self.active_file:
            return []
        file_path = self.active_file_path
        parsed_lines: List[ParsedLine] = []
        with open(file_path, 'r', encoding='utf-8') as f:
            for i, line_content in enumerate(f):
                line_num = i + 1

                # Strip comments
                comment_pos = line_content.find('//')
                if comment_pos != -1:
                    line_content = line_content[:comment_pos]

                stripped_content = line_content.strip()
                if not stripped_content:
                    continue  # Ignore empty lines

                # Calculate indentation
                indent_spaces = len(line_content) - len(line_content.lstrip(' '))
                if indent_spaces % 4 != 0:
                    raise ValueError(f"Line {line_num}: Indentation error. Indentation must be a multiple of 4 spaces.")
                indent_level = indent_spaces // 4

                parsed_lines.append((line_num, indent_level, stripped_content))
        return parsed_lines

    def _build_ast_from_lines(self, lines: List[ParsedLine]) -> AstNode:
        """Constructs an Abstract Syntax Tree (AST) from a list of parsed lines."""
        print("  - Step 2: Building Abstract Syntax Tree (AST)...")
        root: AstNode = {'type': 'root', 'children': [], 'indent': -1}
        stack: List[AstNode] = [root]

        # FIX: Changed `last_annotations` to store indent level for alignment checks.
        last_annotations: List[Tuple[str, int]] = []
        last_description: Optional[str] = None

        for line_num, indent, content in lines:
            while indent <= stack[-1]['indent']:
                stack.pop()
            parent_node = stack[-1]
            
            # This will raise ValueError for malformed keywords.
            node_type, name = self._classify_line(content, line_num)

            # FIX (L-2): Check for dangling annotations before processing a new line if indentation decreases.
            if indent <= parent_node['indent'] and (last_annotations or last_description):
                raise ValueError(f"Line {line_num}: Dangling 'description' or '@' annotation found. It must be followed by a valid code block (func, class, var).")

            # FIX (2.3.6): Disallow statements at the root level.
            if parent_node['type'] == 'root' and node_type == 'statement':
                raise ValueError(f"Line {line_num}: Illegal statement '{content}' found at the root level of the file. Only 'func', 'class', or 'var' are allowed here.")

            # Handle annotations and descriptions, which are metadata for the *next* node.
            if node_type == 'annotation':
                last_annotations.append((name, indent))
                continue
            if node_type == 'description':
                if last_description is not None:
                    raise ValueError(f"Line {line_num}: Found a 'description' tag while another was already pending. Only one description per symbol is allowed.")
                last_description = name
                continue
            
            # FIX (2.3.7): Check annotation alignment when a new node is created.
            attached_annotations = []
            for ann_name, ann_indent in last_annotations:
                if ann_indent != indent:
                    raise ValueError(f"Line {line_num}: Misaligned annotation '@{ann_name}'. Annotations must have the same indentation as the block they apply to ('{content}').")
                attached_annotations.append(ann_name)
            
            node: AstNode = {
                'type': node_type,
                'name': name,
                'content': content,
                'line': line_num,
                'indent': indent,
                'description': last_description,
                'annotations': attached_annotations, # Attach validated annotations
                'children': [],
                'parent_type': parent_node.get('type')
            }

            parent_node['children'].append(node)

            # Reset metadata holders after they've been attached to the node.
            last_annotations = []
            last_description = None

            # If the node is a block-starter, push it onto the stack to become the new parent.
            if content.endswith(':'):
                stack.append(node)

        # FIX (L-2): Check for any annotations left at the end of the file.
        if last_annotations or last_description:
            raise ValueError("Syntax error: File ends with a dangling '@' annotation or 'description' tag.")

        return root

    def _classify_line(self, content: str, line_num: int) -> Tuple[str, Optional[str]]:
        """
        Determines the type and name of a line, with strict validation.
        FIX (L-1): This method now raises ValueError for malformed keywords.
        """
        content = content.strip()
        parts = content.split()
        keyword = parts[0] if parts else ""

        # Stricter checks for keywords requiring a name.
        if keyword in ["class", "func", "var"]:
            # Check for missing name or colon in 'var'
            if len(parts) < 2 or (keyword == 'var' and ':' not in parts[1]):
                raise ValueError(f"Line {line_num}: Malformed declaration. '{keyword}' must be followed by a name (e.g., '{keyword} MyName:').")
            name = parts[1].strip(':')
            return keyword, name

        if content.startswith("description:"):
            return "description", content.replace("description:", "").strip()
        if content.startswith("@"):
            return "annotation", content[1:].strip()
        if content.startswith("input:"):
            return "input", content.replace("input:", "").strip()
        if content.startswith("output:"):
            return "output", content.replace("output:", "").strip()
        if content.startswith("behavior:"):
            return "behavior", None
        if content.startswith("if "):
            return "if", content
        if content.startswith("else:"):
            return "else", None

        return "statement", content

    def _perform_syntax_checks(self, ast: AstNode) -> None:
        """Performs a suite of syntax checks based on the generated AST."""
        print("  - Step 3: Performing syntax validation...")
        self._check_indentation_rules(ast)
        self._check_block_structure_rules(ast)
        self._check_keyword_and_token_rules(ast)
        self._check_annotation_rules(ast)
        print("  - Validation finished.")

    def _check_indentation_rules(self, node: AstNode) -> None:
        """Recursively checks if all block content is correctly indented."""
        for child in node.get('children', []):
            # 计算期望缩进 = 父节点缩进 + 1
            expected_indent = node['indent'] + 1
            
            # 特殊处理根节点的直接子节点
            if node['type'] == 'root':
                # 文件顶层声明必须是 0 缩进
                if child['indent'] != 0:
                    raise ValueError(
                        f"Line {child['line']}: Indentation error. "
                        f"'{child['content']}' is incorrectly indented. "
                        f"Expected 0 spaces, found {child['indent']*4}."
                    )
                # 但不要修改期望缩进值，保持递归逻辑
            else:
                # 常规嵌套结构检查
                if child['indent'] != expected_indent:
                    raise ValueError(
                        f"Line {child['line']}: Indentation error. "
                        f"'{child['content']}' is incorrectly indented. "
                        f"Expected {expected_indent*4} spaces, found {child['indent']*4}."
                    )
            
            # 递归检查子节点
            self._check_indentation_rules(child)

    def _check_block_structure_rules(self, ast: AstNode) -> None:
        """
        Validates the structure of `func` blocks.
        FIX (2.3.1): Now checks for presence of `behavior`, `input`, and `output`.
        """
        func_nodes = self._find_nodes_by_type(ast, 'func')
        for func_node in func_nodes:
            child_types = {child['type'] for child in func_node.get('children', [])}
            required_children = {'behavior', 'input', 'output'}
            missing = required_children - child_types
            if missing:
                raise ValueError(f"Line {func_node['line']}: `func {func_node['name']}` is missing required block(s): {', '.join(missing)}.")

    def _check_keyword_and_token_rules(self, ast: AstNode) -> None:
        """Validates keyword usage, like colons at the end of block declarations."""
        nodes_to_check = self._find_nodes_by_type(ast, 'any')
        
        for node in nodes_to_check:
            # Check for required colons on block-defining keywords.
            if node['type'] in ['func', 'class', 'if', 'else', 'behavior'] and not node['content'].endswith(':'):
                raise ValueError(f"Line {node['line']}: Statement '{node['content']}' must end with a colon ':'.")

    def _check_annotation_rules(self, ast: AstNode) -> None:
        """Validates the placement of `@` and `description` annotations."""
        all_nodes = self._find_nodes_by_type(ast, 'any')
        for node in all_nodes:
            if node['annotations'] and node['type'] not in ['func', 'class']:
                raise ValueError(f"Line {node['line']}: Annotations '@' are only allowed before 'func' or 'class' blocks.")
            if node['description'] and node['type'] not in ['func', 'class', 'var']:
                raise ValueError(f"Line {node['line']}: 'description' is only allowed for 'func', 'class', or 'var' declarations.")

    # --------------------------------------------------------------------------
    # Private Helper Methods - Symbol Management & JSON I/O
    # --------------------------------------------------------------------------

    def _get_symbols_json_path(self) -> str:
        """Constructs the full path to the `mccp_symbols_single.json` file."""
        if not self.active_directory:
            raise ValueError("Working directory is not set.")
        return os.path.join(self.active_directory, "mccp_symbols_single.json")

    def _ensure_symbols_json_exists(self) -> None:
        """Creates a default `mccp_symbols_single.json` if it does not exist."""
        if self.symbols_json_path and not os.path.exists(self.symbols_json_path):
            print(f"'{os.path.basename(self.symbols_json_path)}' not found. Creating a new one.")
            default_structure = {
                "depend_content": {}, "dir_content": {}, "symbols_param": {},
                "ignore_list": [], "frozen_list": []
            }
            with open(self.symbols_json_path, 'w', encoding='utf-8') as f:
                json.dump(default_structure, f, indent=4)

    def _load_symbols_json(self) -> None:
        """Loads the content of the symbols JSON file into memory."""
        if self.symbols_json_path and os.path.exists(self.symbols_json_path):
            try:
                with open(self.symbols_json_path, 'r', encoding='utf-8') as f:
                    self.symbols_data = json.load(f)
            except json.JSONDecodeError:
                print(f"Warning: Could not parse '{self.symbols_json_path}'. Starting with an empty symbol table.")
                self.symbols_data = {}
        else:
            self.symbols_data = {}

    def _save_symbols_json(self) -> None:
        """Saves the in-memory symbol data back to the JSON file."""
        if self.symbols_json_path:
            with open(self.symbols_json_path, 'w', encoding='utf-8') as f:
                json.dump(self.symbols_data, f, indent=4, sort_keys=True)
            print(f"Symbol table '{os.path.basename(self.symbols_json_path)}' has been updated.")
            
    def _is_ready_for_update(self) -> bool:
        """Checks if the analyzer is in a valid state to perform an update."""
        if not self.active_directory or not self.active_file:
            print("Error: Working directory and active file must be set before updating.")
            return False
        if not self.parsed_ast:
            print(f"Error: File '{self.active_file}' has not been parsed or failed parsing. Cannot update symbols.")
            return False
        return True

    def _update_symbols_by_type(self, symbol_type: str, is_top_level: bool):
        """
        REFACTORED: Generic helper to update symbols, reducing code duplication.
        Finds symbols of a given type and updates the symbol table.
        """
        if not self._is_ready_for_update():
            return

        file_base_name = os.path.splitext(self.active_file)[0]

        if is_top_level:
            print(f"Updating all top-level {symbol_type}s from '{self.active_file}'...")
            nodes_to_process = [
                node for node in self.parsed_ast.get('children', [])
                if node.get('type') == symbol_type
            ]
            for node in nodes_to_process:
                symbol_path = f"{file_base_name}.{node['name']}"
                symbol_data = self._create_symbol_data_from_node(node)
                self._update_symbol_in_json(symbol_path, symbol_data)
        else: # Update class members
            print(f"Updating all class {symbol_type}s from '{self.active_file}'...")
            class_nodes = self._find_nodes_by_type(self.parsed_ast, 'class')
            for class_node in class_nodes:
                class_path = f"{file_base_name}.{class_node['name']}"
                member_nodes = [
                    child for child in class_node.get('children', [])
                    if child.get('type') == symbol_type
                ]
                for member_node in member_nodes:
                    symbol_path = f"{class_path}.{member_node['name']}"
                    symbol_data = self._create_symbol_data_from_node(member_node)
                    self._update_symbol_in_json(symbol_path, symbol_data)
                    
    def _update_symbol_in_json(self, symbol_path: str, symbol_data: Dict[str, Any]) -> None:
        """A helper to add or update a single symbol in the `symbols_param` dictionary."""
        if "symbols_param" not in self.symbols_data:
            self.symbols_data["symbols_param"] = {}
        # Preserve existing `is_frozen` state if symbol already exists.
        if symbol_path in self.symbols_data["symbols_param"]:
            symbol_data['is_frozen'] = self.symbols_data["symbols_param"][symbol_path].get('is_frozen', False)
        
        self.symbols_data["symbols_param"][symbol_path] = symbol_data

    def _find_nodes_by_type(self, start_node: AstNode, node_type: str) -> List[AstNode]:
        """Recursively finds all nodes of a specific type in the AST."""
        found_nodes = []
        if start_node is None:
            return []
        
        # 'any' is a special type to match all nodes during traversal
        if node_type == 'any' or start_node.get('type') == node_type:
            found_nodes.append(start_node)
            
        for child in start_node.get('children', []):
            found_nodes.extend(self._find_nodes_by_type(child, node_type))
        return found_nodes

    def _find_node_by_path(self, path_parts: List[str], start_node: Optional[AstNode] = None) -> Optional[AstNode]:
        """Finds a specific node in the AST by its name path."""
        if start_node is None:
            start_node = self.parsed_ast

        if not path_parts:
            return start_node

        if not start_node:
            return None

        current_name = path_parts[0]
        remaining_path = path_parts[1:]

        for child in start_node.get('children', []):
            if child.get('name') == current_name:
                return self._find_node_by_path(remaining_path, child)

        return None

    def _create_symbol_data_from_node(self, node: AstNode) -> Dict[str, Any]:
        """
        Creates a standardized dictionary for a symbol from its AST node.
        FIX (JSON Output): This method is completely rewritten to adhere strictly
        to the `symbols_param` specification. It now includes `scope`, correct `type`
        for methods, and `is_frozen`, while removing non-spec fields.
        """
        parent_type = node.get('parent_type')

        # Determine scope based on the parent node in the AST.
        if parent_type == 'root':
            scope = 'file'
        elif parent_type == 'class':
            scope = 'class'
        else:
            scope = parent_type  # Fallback scope

        # Determine the symbol's type, correcting 'func' to 'method' inside classes.
        node_type = node.get('type')
        if node_type == 'func' and parent_type == 'class':
            symbol_type = 'method'
        else:
            symbol_type = node_type

        # Construct the final symbol data object according to the spec.
        symbol_data = {
            "type": symbol_type,
            "scope": scope,
            "description": node.get('description', ""),
            "is_frozen": False  # Default to false as per spec.
        }
        return symbol_data