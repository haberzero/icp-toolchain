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
        self.symbol_table: Dict[str, Any] = {}
        self.last_intent_comment: str = ""
        self.previous_node: Optional[Dict[str, Any]] = None
        self.lines_parser = LinesParser()
    
    def start_analyzer(self) -> bool:
        print("Starting Analyzer...")
        if not self._read_file():
            print(f"Error: Could not read source file at '{self.current_file_path}'", file=sys.stderr)
            return False
        
        print("File read successfully.")
        
        if not self._generate_structured_lines():
            print("Error: Failed to generate structured lines.", file=sys.stderr)
            return False
        
        print("Structured lines generated successfully.")
        
        if not self._build_ast():
            print("Error: Failed to build AST.", file=sys.stderr)
            return False
        
        print("AST built successfully.")
        
        return True
    
    def _read_file(self) -> bool:
        try:
            with open(self.current_file_path, 'r', encoding='utf-8') as f:
                self.file_content = f.readlines()
            return True
        except IOError as e:
            print(f"Error opening or reading file: {e}", file=sys.stderr)
            return False
    
    def _generate_structured_lines(self) -> bool:
        generator = LinesLoader(self.file_content)
        result = generator.generate()
        if isinstance(result, list):
            self.structured_lines = result
            return True
        else:
            print(f"Indentation Error: {result}")
            return False
    
    def _build_ast(self) -> bool:
        builder = AstBuilder(self.structured_lines, self.lines_parser)
        self.ast = builder.build()
        if not self.ast:
            return False
        return True

if __name__ == "__main__":
    analyzer = McbcAnalyzer("example.mcbc")
    if analyzer.start_analyzer():
        print("Analysis completed successfully.")
    else:
        print("Analysis failed.")
