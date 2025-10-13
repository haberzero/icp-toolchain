from typing import Dict, List, Optional, Any
from typedef.ibc_data_types import IbcKeywords, IbcTokenType, Token

from utils.ibc_analyzer.ibc_lexer import Lexer
from utils.ibc_analyzer.ibc_parser import parse_ibc_tokens


def analyze_ibc_code(text: str) -> Dict[str, Dict[str, Any]]:
    """分析IBC代码，返回AST字典"""
    # 词法分析
    lexer = Lexer(text)
    tokens = lexer.tokenize()
    
    # 语法分析
    ast_dict = parse_ibc_tokens(tokens)
    
    return ast_dict