from typing import Dict, List, Optional, Tuple
from typedef.ibc_data_types import IbcKeywords, IbcTokenType, Token, AstNode, AstNodeType

from utils.ibc_analyzer.ibc_lexer import IbcLexer
from utils.ibc_analyzer.ibc_parser import IbcParser
from utils.ibc_analyzer.ibc_symbol_gen import IbcSymbolGenerator


class IbcAnalyzerError(Exception):
    """词法分析器异常"""
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)
    
    def __str__(self):
        return f"ParserError: {self.message}"


def analyze_ibc_code(
    text: str, 
) -> Tuple[Dict[int, AstNode], Dict[str, Dict[str, str]]]:
    """
    分析IBC代码，返回AST字典和可选的原始符号表
    
    Args:
        text: IBC代码文本
        extract_symbols: 是否提取符号表（默认False）
        
    Returns:
        如果extract_symbols=False：返回AST字典
        如果extract_symbols=True：返回(AST字典, 原始符号表)
        
    Raises:
        IbcAnalyzerError: 分析失败
    """
    try:
        # 词法分析
        lexer = IbcLexer(text)
        tokens = lexer.tokenize()
        
        # 语法分析
        parser = IbcParser(tokens)
        ast_dict = parser.parse()
        
        # 符号提取
        symbol_generator = IbcSymbolGenerator(ast_dict)
        symbols_table = symbol_generator.extract_symbols()
        return ast_dict, symbols_table

    except Exception:
        raise IbcAnalyzerError("IBC代码分析失败")
    