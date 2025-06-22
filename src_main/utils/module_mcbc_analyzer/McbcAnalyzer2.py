# =================================================================
# File:    McbcAnalyzer.py
# Author:  零哈伯
# Date:    6/22/2025
# Version: test
# Desc:    新生成的测试版本，大概率会把之前那个版本取代掉。这里面class的设计我不太满意，等待进一步优化
# =================================================================

import re
from collections import namedtuple

# -----------------------------------------------------------------
# Helper Classes & Data Structures
# -----------------------------------------------------------------

# Represents a line of source code after initial processing.
ProcessedLine = namedtuple('ProcessedLine', ['type', 'indent', 'content', 'lineNumber'])

class LineProcessor:
    """
    Responsible for converting raw text lines into structured ProcessedLine objects,
    identifying type, indentation, and content.
    """
    def process(self, line_text: str, line_number: int) -> ProcessedLine:
        """Processes a single line of text."""
        stripped_line = line_text.lstrip()
        indentation = len(line_text) - len(stripped_line)

        if not stripped_line:
            return ProcessedLine("empty", indentation, "", line_number)

        if stripped_line.startswith('//'):
            return ProcessedLine("comment", indentation, stripped_line, line_number)
        
        if stripped_line.startswith('@'):
            return ProcessedLine("annotation", indentation, stripped_line[1:].strip(), line_number)

        # Default to a statement type, which the AstNodeFactory will further classify.
        return ProcessedLine("statement", indentation, stripped_line.rstrip(), line_number)

class SymbolTable:
    """
    Manages scopes and symbol definitions to prevent naming conflicts.
    A stack of dictionaries represents the scopes, where each dictionary
    maps a symbol name to the AST node that defined it.
    """
    def __init__(self):
        self._scope_stack = []

    def push_scope(self, scope_name: str):
        """Pushes a new scope (e.g., for a class or function) onto the stack."""
        self._scope_stack.append({})

    def pop_scope(self):
        """Pops the current scope from the stack when exiting it."""
        if self._scope_stack:
            self._scope_stack.pop()

    def try_register_symbol(self, node) -> bool:
        """
        Tries to register a new symbol in the current scope.
        Returns False if the symbol is already defined, True otherwise.
        """
        if not self._scope_stack:
            return False # Should not happen in a valid flow
        
        current_scope = self._scope_stack[-1]
        symbol_name = getattr(node, 'name', None)

        if symbol_name in current_scope:
            return False # Symbol redefinition

        current_scope[symbol_name] = node
        return True

# -----------------------------------------------------------------
# AST Node Definitions
# -----------------------------------------------------------------

class AstNode:
    """Base class for all AST nodes, defining common properties and interfaces."""
    def __init__(self, processed_line: ProcessedLine, annotation: str = None):
        self.node_type = "base"
        self.content = processed_line.content
        self.parent = None
        self.children = []
        self.metadata = {'annotation': annotation}
        self.indent = processed_line.indent
        self.line_number = processed_line.lineNumber
        # Symbol name, extracted by subclasses
        self.name = ""
        # By default, nodes can have children. This is overridden by terminal nodes.
        self.accepts_children = True

    def add_child(self, child_node):
        """Adds a child node to this node's children list and sets its parent."""
        self.children.append(child_node)
        child_node.parent = self

    def can_add_child(self, child_node, last_child) -> bool:
        """
        Validates if a child node can be added. This is the core of syntax rule enforcement.
        Base implementation denies all children. Subclasses must override this.
        """
        return False

    def __repr__(self):
        return f"<{self.__class__.__name__} L{self.line_number} '{self.content}'>"

class RootNode(AstNode):
    """The root of the AST, representing the entire file."""
    def __init__(self):
        # The root node isn't from a specific line, so we create a dummy ProcessedLine.
        super().__init__(ProcessedLine("root", -1, "ROOT", 0))
        self.node_type = "root"

    def can_add_child(self, child_node, last_child) -> bool:
        return child_node.node_type in ["module", "class"]

class ClassNode(AstNode):
    """Represents a 'class' declaration."""
    def __init__(self, processed_line, annotation):
        super().__init__(processed_line, annotation)
        self.node_type = "class"
        match = re.match(r"class\s*:\s*(\w+)", self.content)
        if match:
            self.name = match.group(1)

    def can_add_child(self, child_node, last_child) -> bool:
        """
        Enforces the structure within a class block.
        - 'description' can follow 'class', 'var', or 'func'.
        - 'inh' must be the first declaration (after an optional description).
        - 'var' and 'func' are general members.
        """
        if child_node.node_type == "description":
            # The last added node (`last_child`) is what the description must follow.
            # If this is the first child, `last_child` will be the parent ClassNode itself.
            return last_child.node_type in ["class", "var", "func"]

        if child_node.node_type == "inh":
            # 'inh' is only valid if no non-description nodes precede it.
            for c in self.children:
                if c.node_type != "description":
                    return False
            return True
        
        return child_node.node_type in ["var", "func"]

class FuncNode(AstNode):
    """Represents a 'func' declaration."""
    def __init__(self, processed_line, annotation):
        super().__init__(processed_line, annotation)
        self.node_type = "func"
        match = re.match(r"func\s*:\s*(\w+)", self.content)
        if match:
            self.name = match.group(1)

    def can_add_child(self, child_node, last_child) -> bool:
        """Ensures correct ordering of 'description', 'input', 'output', 'behavior'."""
        seen = {c.node_type for c in self.children}
        
        if child_node.node_type == "description":
            return not self.children # Must be the very first child
        if child_node.node_type == "input":
            return "output" not in seen and "behavior" not in seen
        if child_node.node_type == "output":
            return "behavior" not in seen
        if child_node.node_type == "behavior":
            return "behavior" not in seen
        return False

class VarNode(AstNode):
    """Represents a 'var' declaration. It cannot have children."""
    def __init__(self, processed_line, annotation):
        super().__init__(processed_line, annotation)
        self.node_type = "var"
        self.accepts_children = False
        match = re.match(r"var\s*:\s*(\w+)", self.content)
        if match:
            self.name = match.group(1)

class DescriptionNode(AstNode):
    """Represents a 'description:' line."""
    def __init__(self, processed_line, annotation):
        super().__init__(processed_line, annotation)
        self.node_type = "description"
        self.accepts_children = False
        self.metadata['description_text'] = self.content.replace("description:", "").strip()

class BehaviorNode(AstNode):
    """Represents a 'behavior' block."""
    def __init__(self, processed_line, annotation):
        super().__init__(processed_line, annotation)
        self.node_type = "behavior"

    def can_add_child(self, child_node, last_child) -> bool:
        allowed_types = ["statement", "if", "else"]
        if child_node.node_type in allowed_types:
            if child_node.node_type == "else":
                # 'else' must immediately follow an 'if'.
                return last_child and last_child.node_type == "if"
            return True
        return False

# Define other node types for completeness
class SimpleKeywordNode(AstNode):
    """A generic node for simple keywords that don't need special logic."""
    def __init__(self, processed_line, annotation):
        super().__init__(processed_line, annotation)
        self.node_type = self.content.split(':')[0].strip()
        self.accepts_children = False # Most are terminal, like 'module', 'input', etc.

class IfNode(AstNode):
    def __init__(self, processed_line, annotation):
        super().__init__(processed_line, annotation)
        self.node_type = "if"
    def can_add_child(self, child_node, last_child) -> bool:
        # 'if' blocks can contain statements
        return child_node.node_type == "statement"

class ElseNode(AstNode):
    def __init__(self, processed_line, annotation):
        super().__init__(processed_line, annotation)
        self.node_type = "else"
    def can_add_child(self, child_node, last_child) -> bool:
        # 'else' blocks can contain statements
        return child_node.node_type == "statement"

class StatementNode(AstNode):
    def __init__(self, processed_line, annotation):
        super().__init__(processed_line, annotation)
        self.node_type = "statement"
        self.accepts_children = False # Simple statements are terminal

class AstNodeFactory:
    """Creates AstNode instances based on the content of a ProcessedLine."""
    NODE_MAP = {
        "class": ClassNode,
        "func": FuncNode,
        "var": VarNode,
        "description": DescriptionNode,
        "behavior": BehaviorNode,
        "if": IfNode,
        "else": ElseNode,
        # Keywords that are simple terminal nodes
        "module": SimpleKeywordNode,
        "inh": SimpleKeywordNode,
        "input": SimpleKeywordNode,
        "output": SimpleKeywordNode,
    }

    @staticmethod
    def create_node(processed_line: ProcessedLine, annotation: str = None) -> AstNode:
        """Factory method to create and return the correct AST node."""
        # Extract the keyword (the part before ':')
        keyword_match = re.match(r"^\s*([\w\s]+?)\s*:", processed_line.content)
        keyword = None
        if keyword_match:
            keyword = keyword_match.group(1).strip()
        
        # Handle special cases or default behavior
        if keyword and keyword in AstNodeFactory.NODE_MAP:
            return AstNodeFactory.NODE_MAP[keyword](processed_line, annotation)
        elif processed_line.type == 'statement':
            # Check for simple keywords that don't have a colon
            if processed_line.content.strip() in ['continue', 'break']:
                return StatementNode(processed_line, annotation)
            # Check for multi-word keywords
            if keyword and keyword in ['define macro', 'return']:
                return StatementNode(processed_line, annotation)
            # Default to a generic statement if no keyword is matched
            if keyword is None:
                return StatementNode(processed_line, annotation)
                
        return None # Unrecognized line format

# -----------------------------------------------------------------
# Core Parser
# -----------------------------------------------------------------
class McbcAnalyzer:
    """
    Core parser that orchestrates the analysis process. It implements a single-pass,
    validating parse with error recovery.
    """
    def __init__(self):
        """Initializes the analyzer state for a new parsing session."""
        self.line_processor = LineProcessor()
        self.symbol_table = SymbolTable()
        self.error_list = []
        self.ast_root = RootNode()
        # Push the global scope
        self.symbol_table.push_scope("global")

    def _reset_state(self):
        """Resets the state for a new file parse."""
        self.__init__()

    def parse_file(self, file_path: str) -> bool:
        """
        Main entry point for the parser. Implements error recovery to report
        multiple errors in a single pass. Returns True if parsing is successful
        (error_list is empty), False otherwise.
        """
        self._reset_state()
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                source_lines = f.readlines()
        except IOError as e:
            self.error_list.append(f"File read error: {e}")
            return False

        current_node = self.ast_root
        last_added_node = self.ast_root
        pending_annotation = None
        
        line_index = 0
        while line_index < len(source_lines):
            line = source_lines[line_index]
            line_number = line_index + 1
            processed_line = self.line_processor.process(line, line_number)

            if processed_line.type in ["empty", "comment"]:
                line_index += 1
                continue

            if processed_line.type == "annotation":
                if pending_annotation is not None:
                    self.error_list.append(f"Error (Line {line_number}): Consecutive '@' annotations are not allowed. Previous one ignored.")
                pending_annotation = processed_line.content
                line_index += 1
                continue
            
            # --- Error Recovery Macro Implementation ---
            def handle_structural_error(error_message):
                nonlocal line_index
                self.error_list.append(error_message)

                # Core Recovery Logic: Find a safe synchronization point.
                # A sync point is a line with indentation <= the current parent's indent,
                # indicating an exit from the problematic code block.
                sync_index = -1
                recovery_scan_index = line_index + 1
                while recovery_scan_index < len(source_lines):
                    preview_line_text = source_lines[recovery_scan_index]
                    preview_line = self.line_processor.process(preview_line_text, recovery_scan_index + 1)
                    if preview_line.type not in ["empty", "comment"]:
                        if preview_line.indent <= current_node.indent:
                            sync_index = recovery_scan_index
                            break
                    recovery_scan_index += 1
                
                if sync_index != -1:
                    line_index = sync_index # Resume parsing from the safe point
                else:
                    line_index = len(source_lines) # No safe point found, end parsing
                return True # Indicates an error was handled

            # Step 1: Find the correct parent node based on indentation (handling dedents)
            while processed_line.indent < current_node.indent:
                if current_node.node_type in ["class", "func"]:
                    self.symbol_table.pop_scope()
                current_node = current_node.parent

            # Step 2: Validate indentation
            if processed_line.indent > current_node.indent:
                if not last_added_node.accepts_children:
                    if handle_structural_error(f"Error (Line {line_number}): Node of type '{last_added_node.node_type}' cannot have child nodes."):
                        continue # Skip to next iteration from new line_index

                expected_indent = last_added_node.indent + 4 if last_added_node.node_type != "root" else 0
                if processed_line.indent != expected_indent:
                    if handle_structural_error(f"Indentation Error (Line {line_number}): Expected indent of {expected_indent}, but got {processed_line.indent}."):
                        continue
                
                current_node = last_added_node
            
            elif processed_line.indent != current_node.indent:
                if handle_structural_error(f"Indentation Error (Line {line_number}): Invalid indentation level."):
                    continue

            # Step 3: Create a new AST node
            new_node = AstNodeFactory.create_node(processed_line, pending_annotation)
            if new_node is None:
                if handle_structural_error(f"Syntax Error (Line {line_number}): Unrecognized keyword or line format: '{processed_line.content}'."):
                    continue

            # Step 4: Perform immediate syntax validation
            if not current_node.can_add_child(new_node, last_added_node):
                if handle_structural_error(f"Structural Error (Line {line_number}): Node of type '{new_node.node_type}' cannot be placed here inside a '{current_node.node_type}' node."):
                    continue

            # Step 5: Add the node and update state
            current_node.add_child(new_node)
            last_added_node = new_node
            pending_annotation = None

            # Step 6: Update symbol table and scope
            if new_node.node_type in ["class", "func"]:
                self.symbol_table.push_scope(new_node.name)
            
            if hasattr(new_node, 'name') and new_node.name:
                if not self.symbol_table.try_register_symbol(new_node):
                    # Note: Symbol redefinition is a semantic error, not a structural one.
                    # We record it but continue parsing the structure.
                    self.error_list.append(f"Semantic Error (Line {line_number}): Symbol '{new_node.name}' is already defined in the current scope.")

            line_index += 1
            # The label 'end_of_loop' from the blueprint is implicitly here.
            
        return not self.error_list

    def get_ast(self) -> RootNode:
        """Returns the generated Abstract Syntax Tree."""
        return self.ast_root

    def get_errors(self) -> list:
        """Returns the list of all errors collected during parsing."""
        return self.error_list
