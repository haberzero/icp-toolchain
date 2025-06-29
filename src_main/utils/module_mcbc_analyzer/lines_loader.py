import json
from textwrap import indent
from typing import List, Dict, Any, Optional
from src_main.cfg.mccp_config_manager import MccpConfigManager
# 这里暂时不会用上，只有在真正开始实际构建项目目录的时候，具备项目根路径以及相应路径下的mccp_config.json文件后才会使用

class LinesLoader:
    def __init__(self, file_content: List[str]):
        self.file_content = file_content
        self.indent_space_num_config = 4  # Default value
        self.load_indent_config()
    
    def load_indent_config(self):
        pass
        # 对于测试代码，此处暂时无用，直接使用默认4空格缩进
        # try:
        #     with open('mccp_config.json', 'r', encoding='utf-8') as config_file:
        #         config = json.load(config_file)
        #         self.indent_space_num = config.get('indentSpaceNum', 4)
        # except FileNotFoundError:
        #     print("Warning: mccp_config.json not found. Using default indent space num of 4.")
        # except json.JSONDecodeError:
        #     print("Warning: Invalid JSON format in mccp_config.json. Using default indent space num of 4.")
    
    def generate(self) -> List[Dict[str, Any]]:
        structured_lines = []
        previous_indent_level = 0
        
        for line_num, line in enumerate(self.file_content, 1):
            rstripped_line = line.rstrip(' ')
            fully_stripped_line = rstripped_line.lstrip(' ')

            if fully_stripped_line == '' or fully_stripped_line.startswith('//'):
                continue
            
            if fully_stripped_line.startswith('\t'):
                print(f"Tab character found on line {line_num}")
                return []

            indent_space_num = len(rstripped_line) - len(fully_stripped_line)

            if indent_space_num % self.indent_space_num_config != 0:
                print(f"Indent space num on line {line_num} is not a multiple of indent_space_num_config: {self.indent_space_num_config}")
                return []

            current_indent_level = indent_space_num // self.indent_space_num_config
            
            # 缩进等级在代码块结束时会出现向下跳变，但是始终不允许向上跳变
            if current_indent_level > previous_indent_level + 1:
                print(f"Unexpected indentation increase on line {line_num}")
                return []

            structured_lines.append(
                {
                    'line_num': line_num,
                    'indent_level': current_indent_level,
                    'content': fully_stripped_line
                }
            )
            
            previous_indent_level = current_indent_level
        
        return structured_lines
