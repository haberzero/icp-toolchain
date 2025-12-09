"""
IBC符号提取模块

负责从AST中提取符号信息
"""
from typing import Dict, Optional
from typedef.ibc_data_types import (
    IbcBaseAstNode, ClassNode, FunctionNode, VariableNode, ModuleNode, BehaviorStepNode,
    VisibilityTypes, SymbolNode, SymbolType
)


class IbcSymbolProcessor:
    """
    IBC符号处理器，用于提取符号/对符号信息进行更新
    """
    
    def __init__(self, ast_dict: Dict[int, IbcBaseAstNode]):
        """初始化符号生成器"""
        self.ast_dict = ast_dict
    
    def process_symbols(self) -> Dict[str, SymbolNode]:
        """
        从AST中提取符号信息
        
        Returns:
            Dict[str, SymbolNode]: 文件符号表字典，以符号名为key，SymbolNode为value

        注意：
        - normalized_name (规范化名称)和visibility (可见性)在符号提取时不填充,
        - 留空字符串, 后续由cmd_handler调用ai_interface推断后填充
        """
        symbol_table: Dict[str, SymbolNode] = {}
        
        # 提取符号声明
        for uid, node in self.ast_dict.items():
            symbol = self._create_symbol_from_node(uid, node)
            if symbol:
                if symbol.symbol_name in symbol_table:
                    print(f"警告: 符号名 {symbol.symbol_name} 已存在，将被覆盖")
                symbol_table[symbol.symbol_name] = symbol

        return symbol_table
    
    def _create_symbol_from_node(self, uid: int, node: IbcBaseAstNode) -> Optional[SymbolNode]:
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
                visibility=VisibilityTypes.DEFAULT,  # Default，后续由AI推断填充
                description=node.external_desc,
                symbol_type=SymbolType.CLASS
            )
        elif isinstance(node, FunctionNode):
            return SymbolNode(
                uid=uid,
                symbol_name=node.identifier,
                normalized_name="",  # 留空，后续由AI推断填充
                visibility=VisibilityTypes.DEFAULT,  # Default，后续由AI推断填充
                description=node.external_desc,
                symbol_type=SymbolType.FUNCTION,
                parameters=node.params  # 添加函数参数信息
            )
        elif isinstance(node, VariableNode):
            return SymbolNode(
                uid=uid,
                symbol_name=node.identifier,
                normalized_name="",  # 留空，后续由AI推断填充
                visibility=VisibilityTypes.DEFAULT,  # Default，后续由AI推断填充
                description=node.external_desc,
                symbol_type=SymbolType.VARIABLE
            )
        
        return None
    
    def update_symbol_normalized_name(
        self, 
        symbol_table: Dict[str, SymbolNode], 
        symbol_name: str, 
        normalized_name: str
    ) -> bool:
        """
        更新符号的规范化名称
        
        Args:
            symbol_table: 符号表字典
            symbol_name: 符号名称
            normalized_name: 规范化名称
            
        Returns:
            bool: 更新是否成功
        """
        symbol = symbol_table.get(symbol_name)
        if symbol is None:
            return False
        
        symbol.normalized_name = normalized_name
        return True
    
    def update_symbol_visibility(
        self, 
        symbol_table: Dict[str, SymbolNode], 
        symbol_name: str, 
        visibility: VisibilityTypes
    ) -> bool:
        """
        更新符号的可见性
        
        Args:
            symbol_table: 符号表字典
            symbol_name: 符号名称
            visibility: 可见性
            
        Returns:
            bool: 更新是否成功
        """
        symbol = symbol_table.get(symbol_name)
        if symbol is None:
            return False
        
        symbol.visibility = visibility
        return True
    
    def update_symbol_normalized_info(
        self,
        symbol_table: Dict[str, SymbolNode],
        symbol_name: str,
        normalized_name: str,
        visibility: VisibilityTypes
    ) -> bool:
        """
        同时更新符号的规范化名称和可见性
        
        Args:
            symbol_table: 符号表字典
            symbol_name: 符号名称
            normalized_name: 规范化名称
            visibility: 可见性
            
        Returns:
            bool: 更新是否成功
        """
        symbol = symbol_table.get(symbol_name)
        if symbol is None:
            return False
        
        symbol.normalized_name = normalized_name
        symbol.visibility = visibility
        return True

