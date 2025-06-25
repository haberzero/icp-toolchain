import sys
from typing import List, Dict, Any, Optional
from lines_parser import LinesParser

class AstBuilder:
    def __init__(self, structured_lines: List[Dict[str, Any]]):
        self.structured_lines = structured_lines
        self.lines_parser = LinesParser()
        self.ast: Dict[str, Any] = self.lines_parser.gen_root_ast_node()
        self.symbol_table: Dict[str, Any] = {}
        self.last_intent_comment: str = ""
        self.previous_node: Optional[Dict[str, Any]] = None
    
    def build(self) -> Dict[str, Any]:
        ast_stack: List[Dict[str, Any]] = [self.ast]
        
        for line_info in self.structured_lines:
            line_num = line_info['line_num']
            content = line_info['content']
            
            parsed_node = self.lines_parser.parse_line(content, line_num)
            
            if parsed_node is None:
                continue
            
            if parsed_node['type'] == 'intent_comment':
                self.last_intent_comment = parsed_node['value']
                continue
            
            current_context_node = ast_stack[-1]
            
            if parsed_node['type'] not in current_context_node['expected_next_types']:
                err_str = (
                    f"Syntax Error on line {line_num}: Unexpected node type '{parsed_node['type']}' "
                    f"after '{current_context_node['type']}'. Expected one of: {current_context_node['expected_next_types']}. "
                    f"Line content: '{content}'"
                )
                print(err_str, file=sys.stderr)
                return {}
            
            if parsed_node['type'] in ['input', 'output', 'description', 'inh']:
                if self.previous_node:
                    if 'attributes' not in self.previous_node:
                        self.previous_node['attributes'] = {}
                    self.previous_node['attributes'][parsed_node['type']] = parsed_node['value']
                continue
            
            if parsed_node.get('is_block_start', False):
                ast_stack.append(parsed_node)
            
            parsed_node['parent'] = current_context_node
            self._append_node_to_parent(current_context_node, parsed_node)
            self._update_symbol_table(parsed_node)
            self.previous_node = parsed_node
        
        return self.ast
    
    def _append_node_to_parent(self, parent_node: Dict[str, Any], child_node: Dict[str, Any]):
        if 'children' not in parent_node:
            parent_node['children'] = []
        parent_node['children'].append(child_node)
    
    # 此函数后续分离至symbol_generator.py，不要混杂在ast_builder中处理
    def _update_symbol_table(self, parsed_node: Dict[str, Any]):
        node_type = parsed_node.get('type')
        if node_type in ["class", "func", "var"]:
            symbol_name = parsed_node.get('name')
            if symbol_name:
                symbol_info = {
                    'type': node_type,
                    'description': parsed_node.get('description', parsed_node.get('intent', '')),
                    'line_num': parsed_node.get('line_num')
                }
                self.symbol_table[symbol_name] = symbol_info
