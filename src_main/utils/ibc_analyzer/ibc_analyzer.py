from typing import Dict, List, Optional, Any
from typedef.ibc_data_types import IbcKeywords, IbcTokenType, Token, AstNode, AstNodeType

from utils.ibc_analyzer.ibc_lexer import IbcLexer
from utils.ibc_analyzer.ibc_parser import IbcParser
from typedef.ibc_data_types import AstNode


class IbcAnalyzerError(Exception):
    """词法分析器异常"""
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)
    
    def __str__(self):
        return f"ParserError: {self.message}"


def analyze_ibc_code(text: str) -> Dict[int, AstNode]:
    """分析IBC代码，返回AST字典"""
    try:
        # 词法分析
        lexer = IbcLexer(text)
        tokens = lexer.tokenize()
        
        # 语法分析
        parser = IbcParser(tokens)
        ast_dict = parser.parse()
        
        return ast_dict
    except IbcAnalyzerError:
        raise IbcAnalyzerError("IBC代码分析失败")
    