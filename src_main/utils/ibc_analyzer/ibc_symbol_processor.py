"""
IBC符号提取模块

负责从AST中提取符号信息
"""
from typing import Dict, Optional
from typedef.ibc_data_types import (
    IbcBaseAstNode, ClassNode, FunctionNode, VariableNode, ModuleNode, BehaviorStepNode,
    VisibilityTypes, SymbolNode, SymbolType, FileSymbolTable, SymbolRefInfo, ReferenceType
)


class IbcSymbolProcessor:
    """
    IBC符号处理器，用于提取符号/对符号信息进行更新
    """
    
    def __init__(self, ast_dict: Dict[int, IbcBaseAstNode]):
        """初始化符号生成器"""
        self.ast_dict = ast_dict
    
    def process_symbols(self) -> FileSymbolTable:
        """
        从AST中提取符号信息，包括符号声明和符号使用
        
        Returns:
            FileSymbolTable: 文件符号表对象，包含所有提取的符号声明和符号使用

        注意：
        - normalized_name (规范化名称)和visibility (可见性)在符号提取时不填充,
        - 留空字符串, 后续由cmd_handler调用ai_interface推断后填充
        """
        symbol_table = FileSymbolTable()
        
        # 提取符号声明
        for uid, node in self.ast_dict.items():
            symbol = self._create_symbol_from_node(uid, node)
            if symbol:
                symbol_table.add_symbol(symbol)

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
        symbol_table: FileSymbolTable, 
        symbol_uid: int, 
        normalized_name: str
    ) -> bool:
        """
        更新符号的规范化名称
        
        Args:
            symbol_table: 符号表
            symbol_uid: 符号UID
            normalized_name: 规范化名称
            
        Returns:
            bool: 更新是否成功
        """
        symbol = symbol_table.get_symbol_by_uid(symbol_uid)
        if symbol is None:
            return False
        
        symbol.normalized_name = normalized_name
        return True
    
    def update_symbol_visibility(
        self, 
        symbol_table: FileSymbolTable, 
        symbol_uid: int, 
        visibility: VisibilityTypes
    ) -> bool:
        """
        更新符号的可见性
        
        Args:
            symbol_table: 符号表
            symbol_uid: 符号UID
            visibility: 可见性
            
        Returns:
            bool: 更新是否成功
        """
        symbol = symbol_table.get_symbol_by_uid(symbol_uid)
        if symbol is None:
            return False
        
        symbol.visibility = visibility
        return True
    
    def update_symbol_normalized_info(
        self,
        symbol_table: FileSymbolTable,
        symbol_uid: int,
        normalized_name: str,
        visibility: VisibilityTypes
    ) -> bool:
        """
        同时更新符号的规范化名称和可见性
        
        Args:
            symbol_table: 符号表
            symbol_uid: 符号UID
            normalized_name: 规范化名称
            visibility: 可见性
            
        Returns:
            bool: 更新是否成功
        """
        symbol = symbol_table.get_symbol_by_uid(symbol_uid)
        if symbol is None:
            return False
        
        symbol.normalized_name = normalized_name
        symbol.visibility = visibility
        return True
    
    def add_symbol_ref_node_to_behavior(
        self,
        symbol_table: FileSymbolTable,
        behavior_uid: int,
        ref_symbol_name: str,
        line_number: int = 0,
        context: str = ""
    ) -> bool:
        """
        向BehaviorStepNode添加新的符号引用
        这个方法用于添加隐式符号引用，即通过AI智能解析后添加的引用
        
        Args:
            symbol_table: 符号表
            behavior_uid: BehaviorStepNode的UID
            ref_symbol_name: 引用的符号名称
            line_number: 行号（可选）
            context: 上下文信息（可选）
            
        Returns:
            bool: 添加是否成功
        """
        # 验证behavior节点存在
        if behavior_uid not in self.ast_dict:
            return False
        
        node = self.ast_dict[behavior_uid]
        if not isinstance(node, BehaviorStepNode):
            return False
        
        # 向AST节点添加符号引用
        if ref_symbol_name not in node.symbol_refs:
            node.symbol_refs.append(ref_symbol_name)
        
        # 向符号表添加符号引用记录
        ref = SymbolRefInfo(
            ref_symbol_name=ref_symbol_name,
            ref_type=ReferenceType.BEHAVIOR_REF,
            source_uid=behavior_uid,
            line_number=line_number if line_number > 0 else node.line_number,
            context=context if context else node.content
        )
        symbol_table.add_reference(ref)
        
        return True

