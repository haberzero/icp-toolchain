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
        - visibility (可见性)直接从AST节点读取，由Parser在解析阶段通过可见性声明关键字确定
        - normalized_name (规范化名称)在符号提取时不填充，留空字符串，后续由cmd_handler调用ai_interface推断后填充
        """
        symbol_table: Dict[str, SymbolNode] = {}
        
        # 提取符号声明
        for uid, node in self.ast_dict.items():
            symbol = self._create_symbol_from_node(uid, node)
            if symbol:
                if symbol.symbol_name in symbol_table:
                    print(f"警告: 符号名 {symbol.symbol_name} 已存在，将被覆盖")
                symbol_table[symbol.symbol_name] = symbol
        
        # 填充parent_symbol_name和children_symbol_names关系
        self._build_symbol_hierarchy(symbol_table)

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
                parent_symbol_name="",  # 初始为空，由_build_symbol_hierarchy填充
                symbol_name=node.identifier,
                normalized_name="",  # 留空，后续由AI推断填充
                visibility=node.visibility,
                description=node.external_desc,
                symbol_type=SymbolType.CLASS
            )
        elif isinstance(node, FunctionNode):
            return SymbolNode(
                uid=uid,
                parent_symbol_name="",  # 初始为空，由_build_symbol_hierarchy填充
                symbol_name=node.identifier,
                normalized_name="",  # 留空，后续由AI推断填充
                visibility=node.visibility,
                description=node.external_desc,
                symbol_type=SymbolType.FUNCTION,
                parameters=node.params  # 添加函数参数信息
            )
        elif isinstance(node, VariableNode):
            return SymbolNode(
                uid=uid,
                parent_symbol_name="",  # 初始为空，由_build_symbol_hierarchy填充
                symbol_name=node.identifier,
                normalized_name="",  # 留空，后续由AI推断填充
                visibility=node.visibility,
                description=node.external_desc,
                symbol_type=SymbolType.VARIABLE
            )
        
        return None
    
    def _build_symbol_hierarchy(self, symbol_table: Dict[str, SymbolNode]) -> None:
        """
        构建符号层次关系，填充parent_symbol_name和children_symbol_names
        
        Args:
            symbol_table: 符号表字典
            
        说明：
            通过遍历AST中的parent-child关系，构建符号之间的层级结构。
            每个符号会记录其父符号名称，父符号也会在子符号列表中添加该符号。
        """
        # 首先构建 uid -> symbol_name 的映射
        uid_to_symbol_name: Dict[int, str] = {}
        for symbol_name, symbol in symbol_table.items():
            uid_to_symbol_name[symbol.uid] = symbol_name
        
        # 然后遍历AST，查找符号节点的父子关系
        for uid, ast_node in self.ast_dict.items():
            # 如果这个节点是符号节点（Class/Function/Variable）
            if uid in uid_to_symbol_name:
                current_symbol_name = uid_to_symbol_name[uid]
                current_symbol = symbol_table[current_symbol_name]
                
                # 查找父符号
                parent_uid = ast_node.parent_uid
                if parent_uid in uid_to_symbol_name:
                    parent_symbol_name = uid_to_symbol_name[parent_uid]
                    current_symbol.parent_symbol_name = parent_symbol_name
                    # 在父符号中添加当前符号为子符号
                    parent_symbol = symbol_table[parent_symbol_name]
                    parent_symbol.add_child(current_symbol_name)

