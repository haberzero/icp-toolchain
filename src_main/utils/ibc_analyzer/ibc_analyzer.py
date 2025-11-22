from typing import Dict, List, Optional, Any
from typedef.ibc_data_types import IbcKeywords, IbcTokenType, Token, IbcBaseAstNode, AstNodeType

from utils.ibc_analyzer.ibc_lexer import IbcLexer
from utils.ibc_analyzer.ibc_parser import IbcParser
from utils.ibc_analyzer.ibc_symbol_gen import IbcSymbolGenerator

from typedef.ibc_data_types import IbcBaseAstNode


class IbcAnalyzerError(Exception):
    """词法分析器异常"""
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)
    
    def __str__(self):
        return f"ParserError: {self.message}"


def analyze_ibc_code(text: str):
    """分析IBC代码，返回AST字典以及原始符号表"""
    try:
        # 预处理中文特殊标点符号
        text = preprocess_cn_text(text)

        # 词法分析
        lexer = IbcLexer(text)
        tokens = lexer.tokenize()
        
        # 语法分析
        parser = IbcParser(tokens)
        ast_dict = parser.parse()

        # 符号提取
        symbol_gen = IbcSymbolGenerator(ast_dict)
        symbol_table = symbol_gen.extract_symbols()
        
        return ast_dict, symbol_table
    except IbcAnalyzerError:
        raise IbcAnalyzerError("IBC代码分析失败")
    
def preprocess_cn_text(text: str) -> str:
    """将中文文本中的关键标点符号替换为英文形式"""
    text = text.replace("，", ", ")
    text = text.replace("：", ": ")
    text = text.replace("；", "; ")
    text = text.replace("（", "(")
    text = text.replace("）", ")")
    text = text.replace("【", "[")
    text = text.replace("】", "]")
    return text
