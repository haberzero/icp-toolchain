from typing import Dict, List, Optional, Any
from typedef.ibc_data_types import IbcKeywords, IbcTokenType, Token, IbcBaseAstNode, AstNodeType

from utils.ibc_analyzer.ibc_lexer import IbcLexer
from utils.ibc_analyzer.ibc_parser import IbcParser
from utils.ibc_analyzer.ibc_symbol_gen import IbcSymbolGenerator

from typedef.ibc_data_types import IbcBaseAstNode
from typedef.exception_types import IbcAnalyzerError, LexerError, IbcParserError



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
    
    except (LexerError, IbcParserError) as e:
        # 如果异常还没有行内容信息，尝试从text中提取
        if not e.line_content and e.line_num > 0:
            lines = text.split('\n')
            if 0 < e.line_num <= len(lines):
                line_content = lines[e.line_num - 1].rstrip()
                # 重新抛出带有完整信息的异常
                if isinstance(e, LexerError):
                    raise LexerError(
                        message=e.message,
                        line_num=e.line_num,
                        line_content=line_content
                    ) from e
                else:
                    raise IbcParserError(
                        message=e.message,
                        line_num=e.line_num,
                        line_content=line_content
                    ) from e
        # 如果已经有行内容，直接重新抛出
        raise
    
    except IbcAnalyzerError as e:
        # 其他IbcAnalyzerError类型的异常，尝试补全行内容
        if not e.line_content and e.line_num > 0:
            lines = text.split('\n')
            if 0 < e.line_num <= len(lines):
                line_content = lines[e.line_num - 1].rstrip()
                raise IbcAnalyzerError(
                    message=e.message,
                    line_num=e.line_num,
                    line_content=line_content
                ) from e
        raise
    
    except Exception as e:
        # 捕获其他异常并包装为IbcAnalyzerError
        raise IbcAnalyzerError(
            message=f"Unexpected error during IBC analysis: {str(e)}"
        ) from e
    
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
