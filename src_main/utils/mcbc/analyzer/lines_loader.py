import json
from typing import List, Dict, Any, Optional

from src_main.cfg.mccp_config_manager import g_mccp_config_manager
from src_main.lib.diag_handler import DiagHandler, EType, WType


class LinesLoader:
    def __init__(self, current_dir_path: str, file_content: List[str], diag_handler: DiagHandler):
        self.file_content = file_content
        self.current_dir_path = current_dir_path
        self.indent_space_num_config = 4  # Default value
        self.diag_handler = diag_handler
    
    def load_indent_config(self):
        pass
        # 暂时跳过,后面用manager读缩进数量的配置
        # config_manager = g_mccp_config_manager
    
    def generate(self):
        structured_lines = []
        
        for line_num, line in enumerate(self.file_content, 1):
            rstripped_line = line.rstrip(' ')
            fully_stripped_line = rstripped_line.lstrip(' ')

            if fully_stripped_line == '' or fully_stripped_line.startswith('//'):
                continue

            # 禁止使用tab字符
            if '\t' in line:
                self.diag_handler.set_line_error(line_num, EType.TAB_DETECTED)
                continue

            # 计算缩进空格数
            indent_space_num = len(rstripped_line) - len(fully_stripped_line)

            # 检查缩进是否为配置的整数倍
            if indent_space_num % self.indent_space_num_config != 0:
                self.diag_handler.set_line_error(line_num, EType.INDENT_MISALIGNMENT)
                continue

            current_indent_level = indent_space_num // self.indent_space_num_config
            
            # 禁止缩进向上跳变，向上跳变会导致后续行缩进读取出错
            if current_indent_level > previous_indent_level + 1:
                self.diag_handler.set_line_error(line_num, EType.INDENT_JUMP)
                continue

            # 如果一切正常，则添加到结构化行中
            structured_lines.append({
                'line_num': line_num,
                'indent_level': current_indent_level,
                'content': fully_stripped_line
            })

            previous_indent_level = current_indent_level

        # 返回 结构化行列表 和 错误表管理器
        return structured_lines, self.diag_handler
