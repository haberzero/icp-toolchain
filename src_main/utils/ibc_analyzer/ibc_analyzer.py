from typing import Dict, List, Optional, Any, Tuple
from typedef.ibc_data_types import IbcKeywords, IbcTokenType, Token, IbcBaseAstNode, AstNodeType

from utils.ibc_analyzer.ibc_lexer import IbcLexer
from utils.ibc_analyzer.ibc_parser import IbcParser
from utils.ibc_analyzer.ibc_symbol_processor import IbcSymbolProcessor

from typedef.ibc_data_types import IbcBaseAstNode
from typedef.exception_types import IbcAnalyzerError, LexerError, IbcParserError



def analyze_ibc_code(text: str) -> Tuple[bool, Optional[Dict], Optional[Dict]]:
    """分析IBC代码，返回解析状态、AST字典以及原始符号表
    
    Args:
        text: 待分析的IBC代码文本
        
    Returns:
        Tuple[bool, Optional[Dict], Optional[Dict]]: 
            - bool: 解析是否成功（空文件也视为成功）
            - Optional[Dict]: AST字典（解析失败时为None）
            - Optional[Dict]: 符号表（解析失败时为None）
    """
    # 空文件视为解析成功
    if not text or not text.strip():
        return True, None, None
    
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
        symbol_gen = IbcSymbolProcessor(ast_dict)
        symbol_table = symbol_gen.process_symbols()
        
        return True, ast_dict, symbol_table

    except IbcAnalyzerError as e:
        # 根据行号，从text原始文本中提取行内容
        if not e.line_content and e.line_num > 0:
            lines = text.split('\n')
            if 0 < e.line_num <= len(lines):
                line_content = lines[e.line_num - 1].rstrip()
                print(f"IBC分析错误: {e.message}")
                print(f"  行号: {e.line_num}")
                print(f"  内容: {line_content}")
        else:
            print(f"IBC分析错误: {e.message}")
            if e.line_num > 0:
                print(f"  行号: {e.line_num}")
            if e.line_content:
                print(f"  内容: {e.line_content}")
        return False, None, None
    
    except Exception as e:
        # 捕获其他异常
        print(f"IBC分析时发生未预期的错误: {str(e)}")
        return False, None, None
    
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
