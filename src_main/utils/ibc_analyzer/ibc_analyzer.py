from typing import Dict, List, Optional, Any, Tuple
from typedef.ibc_data_types import IbcKeywords, IbcTokenType, Token, AstNode, AstNodeType

from utils.ibc_analyzer.ibc_lexer import IbcLexer
from utils.ibc_analyzer.ibc_parser import IbcParser
from utils.ibc_analyzer.ibc_symbol_gen import IbcSymbolGenerator
from typedef.ibc_data_types import AstNode
from libs.ai_interface.chat_interface import ChatInterface


class IbcAnalyzerError(Exception):
    """词法分析器异常"""
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)
    
    def __str__(self):
        return f"ParserError: {self.message}"


def analyze_ibc_code(
    text: str, 
    extract_symbols: bool = False,
    ai_handler: Optional[ChatInterface] = None,
    file_path: str = ""
) -> Dict[int, AstNode] | Tuple[Dict[int, AstNode], Dict[str, Dict[str, Any]]]:
    """
    分析IBC代码，返回AST字典和可选的符号表
    
    Args:
        text: IBC代码文本
        extract_symbols: 是否提取符号表（默认False）
        ai_handler: 用于符号规范化的AI处理器（可选）
        file_path: 文件路径（用于符号提示）
        
    Returns:
        如果extract_symbols=False：返回AST字典
        如果extract_symbols=True：返回(AST字典, 符号表)
        
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
        
        # 如果需要提取符号表
        if extract_symbols:
            symbol_generator = IbcSymbolGenerator(ai_handler)
            symbols_table = symbol_generator.extract_and_normalize_symbols(ast_dict, file_path)
            return ast_dict, symbols_table
        
        return ast_dict
    except IbcAnalyzerError:
        raise IbcAnalyzerError("IBC代码分析失败")
    