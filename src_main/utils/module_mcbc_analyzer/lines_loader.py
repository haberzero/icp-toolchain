import json
from typing import List, Dict, Any, Optional

class LinesLoader:
    def __init__(self, file_content: List[str]):
        self.file_content = file_content
        self.indent_space_num = 4  # Default value
        self.load_indent_config()
    
    def load_indent_config(self):
        try:
            with open('mccp_config.json', 'r', encoding='utf-8') as config_file:
                config = json.load(config_file)
                self.indent_space_num = config.get('indent_space_num', 4)
        except FileNotFoundError:
            print("Warning: mccp_config.json not found. Using default indent space num of 4.")
        except json.JSONDecodeError:
            print("Warning: Invalid JSON format in mccp_config.json. Using default indent space num of 4.")
    
    def generate(self) -> List[Dict[str, Any]]:
        structured_lines = []
        previous_indent_level = 0
        
        for line_num, line in enumerate(self.file_content, 1):
            stripped_line = line.rstrip()
            fully_stripped_line = stripped_line.lstrip()
            
            if fully_stripped_line.startswith('\t'):
                return f"Tab character found on line {line_num}"
            
            indent_level = len(stripped_line) - len(fully_stripped_line)
            
            if indent_level % self.indent_space_num != 0:
                return f"Indentation level on line {line_num} is not a multiple of {self.indent_space_num}"
            
            current_indent_level = indent_level // self.indent_space_num
            
            if current_indent_level > previous_indent_level + 1:
                return f"Unexpected indentation increase on line {line_num}"
            
            if fully_stripped_line:
                structured_lines.append({
                    'line_num': line_num,
                    'indent_level': current_indent_level,
                    'content': fully_stripped_line
                })
            
            previous_indent_level = current_indent_level
        
        return structured_lines
