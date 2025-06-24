import sys
from lines_loader import LinesLoader
from ast_builder import AstBuilder
from lines_parser import LinesParser

from typing import List, Dict, Any, Optional

class McbcAnalyzer:
    def __init__(self, file_path: str):
        self.current_file_path: str = file_path
        self.file_content: List[str] = []
        self.structured_lines: List[Dict[str, Any]] = []
        self.ast: Dict[str, Any] = {}
        # self.symbol_table: Dict[str, Any] = {}  这一行存疑，大概率应该放进ast_builder
        self.lines_parser = LinesParser()
    
    def start_analysis(self) -> bool:
        print(f"Starting Analyzing file: '{self.current_file_path}'")
        if not self._read_file():
            print(f"Error: Could not read source file: '{self.current_file_path}'", file=sys.stderr)
            return False
        
        print(f"File read successfully: ")
        
        if not self._generate_structured_lines():
            print(f"Error: Failed to generate structured lines: '{self.current_file_path}'", file=sys.stderr)
            return False
        
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
    
    def _generate_structured_lines(self) -> bool:
        generator = LinesLoader(self.file_content)
        result = generator.generate()
        if len(result) == 0:
            return False
        else:
            self.structured_lines = result
            return True
    
    def _build_ast(self) -> bool:
        builder = AstBuilder(self.structured_lines)
        ast = builder.build()
        if not ast:
            return False
        else:
            self.ast = ast
            return True

if __name__ == "__main__":
    analyzer = McbcAnalyzer("example.mcbc")
    if analyzer.start_analysis():
        print("Analysis completed successfully.")
    else:
        print("Analysis failed.")
