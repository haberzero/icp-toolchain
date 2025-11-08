import json
import os
from typing import Dict, Any
from typedef.ibc_data_types import (
    AstNode, AstNodeType, ModuleNode, ClassNode, 
    FunctionNode, VariableNode, BehaviorStepNode
)


class AstDataManager:
    """AST数据管理器，负责AST的持久化存储和加载"""
    
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(AstDataManager, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, '_initialized'):
            self._initialized = True
            self.ast_dict: Dict[int, AstNode] = {}
    
    def save_ast_to_file(self, ast_dict: Dict[int, AstNode], file_path: str) -> bool:
        """
        将AST字典保存到JSON文件
        
        Args:
            ast_dict: AST节点字典，key为uid，value为AstNode对象
            file_path: 保存的文件路径
            
        Returns:
            bool: 保存是否成功
        """
        try:
            # 确保目录存在
            directory = os.path.dirname(file_path)
            if directory and not os.path.exists(directory):
                os.makedirs(directory)
            
            # 将AST字典转换为可序列化的字典
            serializable_dict = {}
            for uid, node in ast_dict.items():
                node_dict = node.to_dict()
                # 添加类型标识，用于反序列化时确定具体类型
                node_dict["_class_type"] = type(node).__name__
                serializable_dict[str(uid)] = node_dict
            
            # 写入JSON文件
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(serializable_dict, f, ensure_ascii=False, indent=2)
            
            return True
        except (IOError, OSError, ValueError) as e:
            print(f"保存AST到文件失败: {e}")
            return False
    
    def load_ast_from_file(self, file_path: str) -> Dict[int, AstNode]:
        """
        从JSON文件加载AST字典
        
        Args:
            file_path: 文件路径
            
        Returns:
            Dict[int, AstNode]: AST节点字典，key为uid，value为AstNode对象
        """
        try:
            if not os.path.exists(file_path):
                print(f"AST文件不存在: {file_path}")
                return {}
            
            # 读取JSON文件
            with open(file_path, 'r', encoding='utf-8') as f:
                serializable_dict = json.load(f)
            
            # 将字典反序列化为AST节点对象
            ast_dict: Dict[int, AstNode] = {}
            for uid_str, node_dict in serializable_dict.items():
                uid = int(uid_str)
                node = self._create_node_from_dict(node_dict)
                ast_dict[uid] = node
            
            self.ast_dict = ast_dict
            return ast_dict
            
        except (IOError, OSError, ValueError) as e:
            print(f"从文件加载AST失败: {e}")
            return {}
    
    def _create_node_from_dict(self, node_dict: Dict[str, Any]) -> AstNode:
        """
        根据字典创建对应类型的AST节点
        
        Args:
            node_dict: 节点字典数据
            
        Returns:
            AstNode: 创建的节点对象
        """
        class_type = node_dict.get("_class_type", "AstNode")
        
        # 根据类型创建相应的节点对象
        if class_type == "ModuleNode":
            return ModuleNode.from_dict(node_dict)
        elif class_type == "ClassNode":
            return ClassNode.from_dict(node_dict)
        elif class_type == "FunctionNode":
            return FunctionNode.from_dict(node_dict)
        elif class_type == "VariableNode":
            return VariableNode.from_dict(node_dict)
        elif class_type == "BehaviorStepNode":
            return BehaviorStepNode.from_dict(node_dict)
        else:
            return AstNode.from_dict(node_dict)
    
    def get_current_ast(self) -> Dict[int, AstNode]:
        """获取当前的AST字典"""
        return self.ast_dict
    
    def set_current_ast(self, ast_dict: Dict[int, AstNode]) -> None:
        """设置当前的AST字典"""
        self.ast_dict = ast_dict


# 单例实例
_instance = AstDataManager()


def get_instance() -> AstDataManager:
    """获取AstDataManager单例实例"""
    return _instance
