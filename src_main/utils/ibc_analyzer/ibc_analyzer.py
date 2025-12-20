from typing import Dict, List, Optional, Any, Tuple
from typedef.ibc_data_types import IbcKeywords, IbcTokenType, Token, IbcBaseAstNode, AstNodeType

from utils.ibc_analyzer.ibc_lexer import IbcLexer
from utils.ibc_analyzer.ibc_parser import IbcParser
from utils.ibc_analyzer.ibc_symbol_processor import IbcSymbolProcessor
from utils.issue_recorder import IbcIssueRecorder

from typedef.ibc_data_types import IbcBaseAstNode
from typedef.exception_types import IbcAnalyzerError


def analyze_ibc_code(
    text: str, 
    ibc_issue_recorder: Optional[IbcIssueRecorder] = None
) -> Tuple[Dict, Dict]:
    """分析IBC代码，返回AST字典以及原始符号表
    
    Args:
        text: 待分析的IBC代码文本
        ibc_issue_recorder: 可选的问题记录器，用于记录分析过程中的错误信息
        
    Returns:
        Tuple[Dict, Dict]: 
            - Dict: AST字典
            - Dict: 符号表
            
    Raises:
        IbcAnalyzerError: 当IBC代码存在语法错误时，会记录到issue_recorder并不再抛出
        其他异常: 非预期IBC错误将直接向上层抛出
    """
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
        
        return ast_dict, symbol_table

    except IbcAnalyzerError as e:
        # 根据行号，从text原始文本中提取行内容
        line_content = e.line_content
        if not line_content and e.line_num > 0:
            lines = text.split('\n')
            if 0 < e.line_num <= len(lines):
                line_content = lines[e.line_num - 1].rstrip()
        
        # 记录错误信息到issue recorder
        if ibc_issue_recorder is not None:
            ibc_issue_recorder.record_issue(
                message=e.message,
                line_num=e.line_num,
                line_content=line_content if line_content else ""
            )
        
        # 打印错误信息
        if line_content:
            print(f"IBC分析错误: {e.message}")
            print(f"  行号: {e.line_num}")
            print(f"  内容: {line_content}")
        else:
            print(f"IBC分析错误: {e.message}")
            if e.line_num > 0:
                print(f"  行号: {e.line_num}")
        
        # IbcAnalyzerError不再向上抛出，返回空字典
        return {}, {}
    
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
