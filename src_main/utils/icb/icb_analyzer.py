import sys
from lines_loader import LinesLoader
from ast_builder import AstBuilder
from symbol_generator import SymbolGenerator

from typing import List, Dict, Any, Optional, Tuple

from libs.diag_handler import DiagHandler

# 关于运行过程中所涉及到的特殊变量: ast_node, parsed_lines, structured_lines等，请到icb_helper.py去查看其结构内容
# 考虑在这个模块里进行报错信息汇总处理。
# 目前的大概思路是：lines-loader ast-builder两个如果出现任何报错flag，就直接调用suggester尝试处理
# 如果首次处理尝试后再次调用对应builder仍然存在报错，则直接把对应行丢弃，进行后续步骤，避免直接被卡死

# 上面提到的操作逻辑应该在cmd_handler里进行。
# IcbAnalyzer应该是一个纯粹底层的模块，应该只负责文件分析，不包含任何逻辑处理

# 对于单个文件的分析流程目前完全是固定的，一次IcbAnalyzer调用对应一个文件的分析过程

class IcbAnalyzer:
    def __init__(self, file_path: str = ""):
        self.current_file_path: str = file_path
        self.file_content: List[str] = []
        self.structured_lines: List[Dict[str, Any]] = []
        self.ast: Dict[str, Any] = {}

        self.diag_handler: Optional[DiagHandler] = None
        self.advisor_flag: bool = False

    def _file_analysis(self, file_path: str) -> bool:
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

        if self.advisor_flag:
            print(f"File '{self.current_file_path}' contains advisor warnings.")
            pass
            # 此处后续用于调用advisor的逻辑，然后还需要一个advisor计数器的东西，多次建议后分析失败则返回false
        
        print("Structured lines generated successfully.")
        
        if not self._build_ast():
            print(f"Error: Failed to build AST: '{self.current_file_path}'", file=sys.stderr)
            return False
        
        print("AST built successfully.")
        
        return True
    
    def _read_file(self) -> bool:
        try:
            with open(self.current_file_path, 'r', encoding='utf-8') as f:
                self.file_content = f.readlines()
            return True
        except IOError as e:
            return False
    
    def _generate_structured_lines(self) -> int:
        # 创建诊断处理器
        self.diag_handler = DiagHandler(self.current_file_path, self.file_content)
        
        # 创建LinesLoader实例
        lines_loader = LinesLoader(self.current_file_path, self.file_content, self.diag_handler)
        result, diag_handler = lines_loader.generate()
        
        if diag_handler.is_diag_table_valid():
            self.advisor_flag = True
            self.diag_handler = diag_handler

        self.structured_lines = result
        return len(result)
    
    def _build_ast(self) -> bool:
        # 确保diag_handler已经创建
        if self.diag_handler is None:
            self.diag_handler = DiagHandler(self.current_file_path, self.file_content)
        
        # 创建AstBuilder实例
        ast_builder = AstBuilder(
            structured_lines=self.structured_lines,
            diag_handler=self.diag_handler,
            active_file=self.current_file_path,
            project_root=""  # 根据需要设置项目根目录
        )
        
        result = ast_builder.build()

        if self.diag_handler.is_diag_table_valid():
            self.advisor_flag = True

        return result

if __name__ == "__main__":
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
    else:
        file_path = "example.icb"
        
    analyzer = IcbAnalyzer(file_path)
    if analyzer._file_analysis(file_path):
        print("Analysis completed successfully.")
    else:
        print("Analysis failed.")