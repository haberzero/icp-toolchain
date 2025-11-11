"""
IBC符号提取模块

负责从AST中提取符号信息
"""
from typing import Dict, Optional
from typedef.ibc_data_types import (
    AstNode, ClassNode, FunctionNode, VariableNode,
    SymbolNode, SymbolType, FileSymbolTable
)


class IbcSymbolGenerator:
    """
    IBC符号生成器，负责从AST提取符号信息
    
    注意：
    - normalized_name（规范化名称）和visibility（可见性）由符号提取时不填充，
    - 留空字符串，后续由cmd_handler调用ai_interface推断后填充
    """
    
    def __init__(self, ast_dict: Dict[int, AstNode]):
        """初始化符号生成器"""
        self.ast_dict = ast_dict
    
    def extract_symbols(self) -> FileSymbolTable:
        """
        从AST中提取符号信息
        
        Returns:
            FileSymbolTable: 文件符号表对象，包含所有提取的符号
        """
        symbol_table = FileSymbolTable()
        
        for uid, node in self.ast_dict.items():
            symbol = self._create_symbol_from_node(uid, node)
            if symbol:
                symbol_table.add_symbol(symbol)
        
        return symbol_table
    
    def _create_symbol_from_node(self, uid: int, node: AstNode) -> Optional[SymbolNode]:
        """
        从AST节点创建符号节点
        
        Args:
            uid: 节点UID
            node: AST节点
            
        Returns:
            SymbolNode: 符号节点对象，如果节点类型不需要创建符号则返回None
        """
        if isinstance(node, ClassNode):
            return SymbolNode(
                uid=uid,
                symbol_name=node.identifier,
                normalized_name="",  # 留空，后续由AI推断填充
                visibility="",  # 留空，后续由AI推断填充
                description=node.external_desc,
                symbol_type=SymbolType.CLASS
            )
        elif isinstance(node, FunctionNode):
            return SymbolNode(
                uid=uid,
                symbol_name=node.identifier,
                normalized_name="",  # 留空，后续由AI推断填充
                visibility="",  # 留空，后续由AI推断填充
                description=node.external_desc,
                symbol_type=SymbolType.FUNCTION
            )
        elif isinstance(node, VariableNode):
            return SymbolNode(
                uid=uid,
                symbol_name=node.identifier,
                normalized_name="",  # 留空，后续由AI推断填充
                visibility="",  # 留空，后续由AI推断填充
                description=node.external_desc,
                symbol_type=SymbolType.VARIABLE
            )
        
        return None
