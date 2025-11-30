"""
IBC符号提取模块

负责从AST中提取符号信息
"""
from typing import Dict, Optional
from typedef.ibc_data_types import (
    IbcBaseAstNode, ClassNode, FunctionNode, VariableNode, ModuleNode, BehaviorStepNode,
    VisibilityTypes, SymbolNode, SymbolType, FileSymbolTable, SymbolReference, ReferenceType
)


class IbcSymbolProcessor:
    """
    IBC符号生成器，负责从AST提取符号信息
    
    注意：
    - normalized_name（规范化名称）和visibility（可见性）由符号提取时不填充，
    - 留空字符串，后续由cmd_handler调用ai_interface推断后填充
    
    功能：
    1. 提取符号声明（类、函数、变量）
    2. 提取符号使用（行为描述中的引用、模块调用、类继承）
    3. 为函数符号添加参数信息
    """
    
    def __init__(self, ast_dict: Dict[int, IbcBaseAstNode]):
        """初始化符号生成器"""
        self.ast_dict = ast_dict
    
    def process_symbols(self) -> FileSymbolTable:
        """
        从AST中提取符号信息，包括符号声明和符号使用
        
        Returns:
            FileSymbolTable: 文件符号表对象，包含所有提取的符号声明和符号使用
        """
        symbol_table = FileSymbolTable()
        
        # 提取符号声明
        for uid, node in self.ast_dict.items():
            symbol = self._create_symbol_from_node(uid, node)
            if symbol:
                symbol_table.add_symbol(symbol)
        
        # 提取符号使用
        for uid, node in self.ast_dict.items():
            references = self._extract_references_from_node(uid, node)
            for ref in references:
                symbol_table.add_reference(ref)
        
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
    
    def _extract_references_from_node(self, uid: int, node: IbcBaseAstNode) -> list[SymbolReference]:
        """
        从AST节点提取符号引用
        
        Args:
            uid: 节点UID
            node: AST节点
            
        Returns:
            list[SymbolReference]: 符号引用列表
        """
        references = []
        
        # 1. 从BehaviorStepNode提取行为描述中的符号引用
        if isinstance(node, BehaviorStepNode):
            for ref_name in node.symbol_refs:
                references.append(SymbolReference(
                    ref_symbol_name=ref_name,
                    ref_type=ReferenceType.BEHAVIOR_REF,
                    source_uid=uid,
                    line_number=node.line_number,
                    context=node.content
                ))
        
        # 2. 从ModuleNode提取模块调用
        elif isinstance(node, ModuleNode):
            if node.identifier:  # 模块名称本身就是一个引用
                references.append(SymbolReference(
                    ref_symbol_name=node.identifier,
                    ref_type=ReferenceType.MODULE_CALL,
                    source_uid=uid,
                    line_number=node.line_number,
                    context=node.content
                ))
        
        # 3. 从ClassNode提取类继承引用
        elif isinstance(node, ClassNode):
            for parent_class, inherit_desc in node.inh_params.items():
                if parent_class:  # 确保父类名不为空
                    references.append(SymbolReference(
                        ref_symbol_name=parent_class,
                        ref_type=ReferenceType.CLASS_INHERIT,
                        source_uid=uid,
                        line_number=node.line_number,
                        context=inherit_desc
                    ))
        
        return references
    
    # ==================== 符号表修改方法 ====================
    
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
    
    def add_symbol_reference_to_behavior(
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
        ref = SymbolReference(
            ref_symbol_name=ref_symbol_name,
            ref_type=ReferenceType.BEHAVIOR_REF,
            source_uid=behavior_uid,
            line_number=line_number if line_number > 0 else node.line_number,
            context=context if context else node.content
        )
        symbol_table.add_reference(ref)
        
        return True

