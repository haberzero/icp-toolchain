from typing import Any, Dict, Optional, Tuple

from typedef.ibc_data_types import (BehaviorStepNode, ClassMetadata, ClassNode,
                                    FunctionMetadata, FunctionNode,
                                    IbcBaseAstNode, ModuleNode, SymbolMetadata,
                                    VariableMetadata, VariableNode,
                                    VisibilityTypes)


class IbcSymbolProcessor:
    """IBC符号处理器，用于基于AST构建符号树和符号元数据

    新设计：
    - 不再返回以符号名为 key 的平铺符号表
    - 直接从AST构建层次化的符号树(symbols_tree)和符号元数据(symbols_metadata)
    - 构造函数相关的参数提取和metadata更新交由SymbolRefResolver负责
    """
    
    def __init__(self, ast_dict: Dict[int, IbcBaseAstNode]):
        """初始化符号处理器
        
        Args:
            ast_dict: 单文件的 AST 节点字典
        """
        self.ast_dict = ast_dict
    
    def build_symbol_tree(self) -> Tuple[Dict[str, Any], Dict[str, SymbolMetadata]]:
        """从 AST 构建单文件符号树及其元数据
        
        返回值：
            Tuple[Dict, Dict]:
                - symbols_tree: 符号树，纯层次结构，所有节点都是 dict
                - symbols_metadata: 符号元数据，键为文件内的点分隔路径，值为SymbolMetadata对象
        """
        symbols_tree: Dict[str, Any] = {}
        symbols_metadata: Dict[str, SymbolMetadata] = {}
        
        # 从虚拟根节点(uid=0)开始遍历，如果不存在则直接返回空结构
        root_node = self.ast_dict.get(0)
        if not root_node:
            return symbols_tree, symbols_metadata
        
        for child_uid in root_node.children_uids:
            self._process_ast_symbol(child_uid, parent_node=symbols_tree, parent_path="", metadata=symbols_metadata)
        
        return symbols_tree, symbols_metadata
    
    def _process_ast_symbol(
        self,
        uid: int,
        parent_node: Dict[str, Any],
        parent_path: str,
        metadata: Dict[str, SymbolMetadata],
    ) -> None:
        """递归遍历 AST，构建符号树和元数据
        
        只对 ClassNode / FunctionNode / VariableNode 创建符号节点：
        - ClassNode: type="class"
        - FunctionNode: type="func"
        - VariableNode: type="var"，根据父节点推断 scope (global/field/local)
        其它节点（如 ModuleNode / BehaviorStepNode）仅用于继续向下遍历。
        """
        node = self.ast_dict.get(uid)
        if not node:
            return
        
        # Module 节点本身不作为符号节点，只透传到子节点
        if isinstance(node, ModuleNode):
            for child_uid in node.children_uids:
                self._process_ast_symbol(child_uid, parent_node, parent_path, metadata)
            return
        
        # Class / Function / Variable 作为符号节点
        if isinstance(node, (ClassNode, FunctionNode, VariableNode)):
            name = getattr(node, "identifier", "")
            if not name:
                return
            
            # 构建基础元数据对象
            current_path = name if not parent_path else f"{parent_path}.{name}"
            
            if isinstance(node, ClassNode):
                meta = ClassMetadata(
                    type="class",
                    visibility=getattr(node, "visibility", VisibilityTypes.PUBLIC).value,
                    description=getattr(node, "external_desc", "")
                )
            elif isinstance(node, FunctionNode):
                desc = getattr(node, "external_desc", "")
                params = getattr(node, "params", None) or {}
                meta = FunctionMetadata(
                    type="func",
                    visibility=getattr(node, "visibility", VisibilityTypes.PUBLIC).value,
                    description=desc,
                    parameters=params
                )
            else:  # VariableNode
                # 变量没有external_desc时，退而使用content作为描述
                desc = getattr(node, "external_desc", "")
                if not desc:
                    desc = getattr(node, "content", "")
                
                # 推断变量作用域
                scope = "unknown"
                parent_ast = self.ast_dict.get(node.parent_uid)
                if isinstance(parent_ast, FunctionNode):
                    scope = "local"
                elif isinstance(parent_ast, ClassNode):
                    scope = "field"
                elif isinstance(parent_ast, ModuleNode):
                    scope = "global"
                
                meta = VariableMetadata(
                    type="var",
                    visibility=getattr(node, "visibility", VisibilityTypes.PUBLIC).value,
                    description=desc,
                    scope=scope
                )
            
            metadata[current_path] = meta
            
            # 在符号树中创建/获取当前节点
            symbol_node = parent_node.setdefault(name, {})
            
            # 如果是类或函数，继续向下处理其子节点
            if isinstance(node, (ClassNode, FunctionNode)):
                for child_uid in node.children_uids:
                    self._process_ast_symbol(child_uid, parent_node=symbol_node, parent_path=current_path, metadata=metadata)
            
            return
        
        # 其它节点（例如 BehaviorStepNode）目前不参与符号树构建，直接忽略
        return

