import sys
from lines_loader import LinesLoader
from ast_builder import AstBuilder

from typing import List, Dict, Any, Optional

from src_main.lib.diag_handler import DiagHandler


# 关于运行过程中所涉及到的特殊变量: ast_node, parsed_lines, structured_lines等，请到mcbc_helper.py去查看其结构内容
# 考虑在这个模块里进行报错信息汇总处理。目前的大概思路是：lines-loader ast-builder两个如果出现任何报错flag，就直接调用suggester尝试处理
# 如果首次处理尝试后再次调用对应builder仍然存在报错，则直接把对应行丢弃，进行后续步骤，避免直接被卡死

# 对于单个文件的分析流程目前完全是固定的，一次McbcAnalyzer调用对应一个文件的分析过程

class McbcAnalyzer:
    def __init__(self, file_path, project_root):
        self.current_file_path: str = ""
        self.file_content: List[str] = []
        self.structured_lines: List[Dict[str, Any]] = []
        self.ast: Dict[str, Any] = {}

        self.diag_handler: DiagHandler
        self.advisor_flag: bool = False

    def start_analysis(self, file_path: str) -> bool:
        # 被外部调用，如果出现报错则外部直接跳过此文件
        self.current_file_path = file_path
        print(f"Starting Analyzing file: '{self.current_file_path}'")
        if not self._read_file():
            print(f"Error: Could not read source file: '{self.current_file_path}'", file=sys.stderr)
            return False
        
        print(f"File read successfully: ")
        
        lines_len = self._generate_structured_lines()
        if lines_len == 0:
            print(f"No analyzable content found in file: '{self.current_file_path}'", file=sys.stderr)
            return False

        if self.advisor_flag == True:
            print(f"File '{self.current_file_path}' contains advisor warnings.")
            pass
            # 此处后续用于调用advisor的逻辑，然后还需要一个advisor计数器的东西，多次建议后分析失败则返回false
        
        print("Structured lines generated successfully.")
        
        if not self._build_ast():
            print(f"Error: Failed to build AST: '{self.current_file_path}'", file=sys.stderr)
            return False
        
        print("AST built successfully.")
        
        return True
    
    def _read_file(self):
        try:
            with open(self.current_file_path, 'r', encoding='utf-8') as f:
                self.file_content = f.readlines()
            return True
        except IOError as e:
            return False
    
    def _generate_structured_lines(self):
        lines_loader = LinesLoader()
        result, diag_handler = lines_loader.generate()
        if diag_handler.is_diag_table_valid():
            self.advisor_flag = True
            self.diag_handler = diag_handler

        self.structured_lines = result
        return len(result)
    
    def _build_ast(self):
        ast_builder = AstBuilder(self.structured_lines)
        ast, diag_handler = ast_builder.build()

        if diag_handler.is_diag_table_valid():
            self.advisor_flag = True
            self.diag_handler = diag_handler

        return len(ast)

if __name__ == "__main__":
    analyzer = McbcAnalyzer("example.mcbc")
    if analyzer.start_analysis():
        print("Analysis completed successfully.")
    else:
        print("Analysis failed.")
