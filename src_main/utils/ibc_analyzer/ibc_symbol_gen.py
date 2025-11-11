"""
IBC符号提取模块

负责从AST中提取符号信息
"""
from typing import Dict
from typedef.ibc_data_types import (
    AstNode, ClassNode, FunctionNode, VariableNode
)


class IbcSymbolGenerator:
    """IBC符号生成器，负责从AST提取符号信息"""
    
    def __init__(self, ast_dict: Dict[int, AstNode]):
        """初始化符号生成器"""
        self.ast_dict = ast_dict
    
    def extract_symbols(self) -> Dict:
        """
        从AST中提取符号信息
        
        Args:
            ast_dict: AST节点字典
            
        Returns:
            Dict[str, Dict[str, str]]: 符号信息字典
                格式: {
                    "符号名称": {
                        "uid": "节点ID",
                        "symbol_type": "类型",
                        "description": "描述"
                    }
                }
        """
        symbols = {}
        ast_dict = self.ast_dict
        
        for uid, node in ast_dict.items():
            if isinstance(node, ClassNode):
                symbols[node.identifier] = {
                    'uid': uid,
                    'symbol_type': 'class',
                    'description': node.external_desc
                }
            elif isinstance(node, FunctionNode):
                symbols[node.identifier] = {
                    'uid': uid,
                    'symbol_type': 'func',
                    'description': node.external_desc
                }
            elif isinstance(node, VariableNode):
                symbols[node.identifier] = {
                    'uid': uid,
                    'symbol_type': 'var',
                    'description': node.external_desc
                }
        
        return symbols
