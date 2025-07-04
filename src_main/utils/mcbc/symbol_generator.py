import sys
from typing import List, Dict, Any, Optional
from lines_parser import LinesParser

class symbolGenerator:
    def __init__(self, parsed_node: Dict[str, Any]):
        self.parsed_node = parsed_node
        self.symbol_table: Dict[str, Any] = {}
    
    def _update_symbol_table(self):
        parsed_node = self.parsed_node
        
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
