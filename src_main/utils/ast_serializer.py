"""AST序列化管理器

统一管理AST节点的序列化和反序列化操作。

设计说明：
- 从各AST节点类的to_dict/from_dict方法中提取序列化逻辑
- 提供统一的序列化接口
- 简化IbcDataStore中的AST处理代码
"""
from typing import Dict, Any
from typedef.ibc_data_types import (
    IbcBaseAstNode, ModuleNode, ClassNode, FunctionNode,
    VariableNode, BehaviorStepNode, AstNodeType
)


class AstSerializer:
    """AST序列化管理器
    
    提供AST节点的序列化和反序列化功能。
    """
    
    # 节点类型映射表
    _NODE_TYPE_MAP = {
        "IbcBaseAstNode": IbcBaseAstNode,
        "ModuleNode": ModuleNode,
        "ClassNode": ClassNode,
        "FunctionNode": FunctionNode,
        "VariableNode": VariableNode,
        "BehaviorStepNode": BehaviorStepNode
    }
    
    @staticmethod
    def serialize_node(node: IbcBaseAstNode) -> Dict[str, Any]:
        """序列化单个AST节点
        
        Args:
            node: AST节点对象
            
        Returns:
            Dict[str, Any]: 序列化后的字典，包含_class_type字段标识节点类型
            
        Example:
            >>> node = ClassNode(uid=1, identifier="MyClass")
            >>> node_dict = AstSerializer.serialize_node(node)
            >>> print(node_dict["_class_type"])
            'ClassNode'
        """
        node_dict = node.to_dict()
        node_dict["_class_type"] = type(node).__name__
        return node_dict
    
    @staticmethod
    def deserialize_node(node_dict: Dict[str, Any]) -> IbcBaseAstNode:
        """反序列化单个AST节点
        
        Args:
            node_dict: 序列化的节点字典
            
        Returns:
            IbcBaseAstNode: 反序列化后的AST节点对象
            
        Raises:
            ValueError: 未知的节点类型
            
        Example:
            >>> node_dict = {"_class_type": "ClassNode", "uid": 1, "identifier": "MyClass"}
            >>> node = AstSerializer.deserialize_node(node_dict)
            >>> print(type(node).__name__)
            'ClassNode'
        """
        class_type = node_dict.get("_class_type", "IbcBaseAstNode")
        
        if class_type not in AstSerializer._NODE_TYPE_MAP:
            raise ValueError(f"未知的AST节点类型: {class_type}")
        
        node_class = AstSerializer._NODE_TYPE_MAP[class_type]
        return node_class.from_dict(node_dict)
    
    @staticmethod
    def serialize_ast_dict(ast_dict: Dict[int, IbcBaseAstNode]) -> Dict[str, Dict[str, Any]]:
        """序列化整个AST字典
        
        Args:
            ast_dict: AST节点字典 {uid: node}
            
        Returns:
            Dict[str, Dict[str, Any]]: 可序列化的字典 {uid_str: node_dict}
            
        Example:
            >>> ast_dict = {0: IbcBaseAstNode(uid=0), 1: ClassNode(uid=1)}
            >>> serializable = AstSerializer.serialize_ast_dict(ast_dict)
            >>> print(type(serializable))
            <class 'dict'>
        """
        serializable_dict = {}
        for uid, node in ast_dict.items():
            node_dict = AstSerializer.serialize_node(node)
            serializable_dict[str(uid)] = node_dict
        return serializable_dict
    
    @staticmethod
    def deserialize_ast_dict(serializable_dict: Dict[str, Dict[str, Any]]) -> Dict[int, IbcBaseAstNode]:
        """反序列化整个AST字典
        
        Args:
            serializable_dict: 序列化的AST字典 {uid_str: node_dict}
            
        Returns:
            Dict[int, IbcBaseAstNode]: AST节点字典 {uid: node}
            
        Example:
            >>> serializable = {"0": {"_class_type": "IbcBaseAstNode", "uid": 0}}
            >>> ast_dict = AstSerializer.deserialize_ast_dict(serializable)
            >>> print(type(ast_dict[0]))
            <class 'typedef.ibc_data_types.IbcBaseAstNode'>
        """
        ast_dict: Dict[int, IbcBaseAstNode] = {}
        for uid_str, node_dict in serializable_dict.items():
            uid = int(uid_str)
            node = AstSerializer.deserialize_node(node_dict)
            ast_dict[uid] = node
        return ast_dict
    
    @staticmethod
    def validate_ast_dict(ast_dict: Dict[int, IbcBaseAstNode]) -> bool:
        """验证AST字典的完整性
        
        检查AST字典中的父子关系是否一致。
        
        Args:
            ast_dict: AST节点字典
            
        Returns:
            bool: 是否有效
            
        Example:
            >>> ast_dict = {0: IbcBaseAstNode(uid=0)}
            >>> is_valid = AstSerializer.validate_ast_dict(ast_dict)
            >>> print(is_valid)
            True
        """
        if not ast_dict:
            return True
        
        # 检查根节点存在
        if 0 not in ast_dict:
            return False
        
        # 检查所有节点的父子关系
        for uid, node in ast_dict.items():
            # 检查父节点引用
            if node.parent_uid != 0:
                if node.parent_uid not in ast_dict:
                    return False
                parent = ast_dict[node.parent_uid]
                # 检查父节点是否包含当前节点
                if uid not in parent.children_uids:
                    return False
            
            # 检查子节点引用
            for child_uid in node.children_uids:
                if child_uid not in ast_dict:
                    return False
                child = ast_dict[child_uid]
                # 检查子节点的父节点是否指向当前节点
                if child.parent_uid != uid:
                    return False
        
        return True
    
    @staticmethod
    def get_node_count_by_type(ast_dict: Dict[int, IbcBaseAstNode]) -> Dict[str, int]:
        """统计AST中各类型节点的数量
        
        Args:
            ast_dict: AST节点字典
            
        Returns:
            Dict[str, int]: 各类型节点数量 {节点类型: 数量}
            
        Example:
            >>> ast_dict = {
            ...     0: IbcBaseAstNode(uid=0),
            ...     1: ClassNode(uid=1),
            ...     2: FunctionNode(uid=2)
            ... }
            >>> counts = AstSerializer.get_node_count_by_type(ast_dict)
            >>> print(counts)
            {'IbcBaseAstNode': 1, 'ClassNode': 1, 'FunctionNode': 1}
        """
        counts = {}
        for node in ast_dict.values():
            node_type = type(node).__name__
            counts[node_type] = counts.get(node_type, 0) + 1
        return counts
    
    @staticmethod
    def find_nodes_by_type(
        ast_dict: Dict[int, IbcBaseAstNode],
        node_type: type
    ) -> Dict[int, IbcBaseAstNode]:
        """查找指定类型的所有节点
        
        Args:
            ast_dict: AST节点字典
            node_type: 要查找的节点类型
            
        Returns:
            Dict[int, IbcBaseAstNode]: 匹配的节点字典 {uid: node}
            
        Example:
            >>> ast_dict = {0: IbcBaseAstNode(), 1: ClassNode(), 2: ClassNode()}
            >>> class_nodes = AstSerializer.find_nodes_by_type(ast_dict, ClassNode)
            >>> print(len(class_nodes))
            2
        """
        result = {}
        for uid, node in ast_dict.items():
            if isinstance(node, node_type):
                result[uid] = node
        return result
    
    @staticmethod
    def get_node_depth(ast_dict: Dict[int, IbcBaseAstNode], uid: int) -> int:
        """获取节点在AST中的深度
        
        根节点深度为0，其子节点深度为1，以此类推。
        
        Args:
            ast_dict: AST节点字典
            uid: 节点UID
            
        Returns:
            int: 节点深度，节点不存在时返回-1
            
        Example:
            >>> ast_dict = {0: IbcBaseAstNode(uid=0), 1: ClassNode(uid=1, parent_uid=0)}
            >>> depth = AstSerializer.get_node_depth(ast_dict, 1)
            >>> print(depth)
            1
        """
        if uid not in ast_dict:
            return -1
        
        depth = 0
        current_uid = uid
        visited = set()
        
        while current_uid != 0:
            if current_uid in visited:
                # 检测到循环引用
                return -1
            visited.add(current_uid)
            
            if current_uid not in ast_dict:
                return -1
            
            node = ast_dict[current_uid]
            current_uid = node.parent_uid
            depth += 1
        
        return depth
    
    @staticmethod
    def clone_ast_dict(ast_dict: Dict[int, IbcBaseAstNode]) -> Dict[int, IbcBaseAstNode]:
        """克隆整个AST字典
        
        创建AST字典的深度拷贝。
        
        Args:
            ast_dict: 要克隆的AST字典
            
        Returns:
            Dict[int, IbcBaseAstNode]: 克隆后的AST字典
            
        Example:
            >>> original = {0: IbcBaseAstNode(uid=0)}
            >>> cloned = AstSerializer.clone_ast_dict(original)
            >>> print(cloned[0].uid)
            0
        """
        # 先序列化再反序列化实现深度拷贝
        serializable = AstSerializer.serialize_ast_dict(ast_dict)
        return AstSerializer.deserialize_ast_dict(serializable)
