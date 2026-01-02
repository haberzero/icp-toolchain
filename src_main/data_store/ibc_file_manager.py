import json
import os
from typing import Any, Dict

from typedef.ibc_data_types import (BehaviorStepNode, ClassNode, FunctionNode,
                                    IbcBaseAstNode, ModuleNode, VariableNode)


class IbcFileManager:
    """IBC文件操作管理器
    
    职责：
    - IBC代码文件的读写操作
    - AST文件的序列化与反序列化
    - 文件路径构建
    
    所有方法均为静态方法，可独立使用。
    """
    
    # ==================== IBC代码文件管理 ====================
    
    @staticmethod
    def build_ibc_path(ibc_root: str, file_path: str) -> str:
        """构建IBC文件路径: ibc_root/file_path.ibc
        
        Args:
            ibc_root: IBC文件根目录
            file_path: 文件相对路径（不含.ibc扩展名）
            
        Returns:
            str: 完整的IBC文件路径
        """
        # 解决Windows和Linux路径分隔符问题
        normalized_file_path = file_path.replace('/', os.sep)
        return os.path.join(ibc_root, f"{normalized_file_path}.ibc")
    
    @staticmethod
    def save_ibc_content(ibc_path: str, ibc_content: str) -> None:
        """保存IBC代码到文件
        
        Args:
            ibc_path: IBC文件路径
            ibc_content: IBC代码内容
            
        Raises:
            IOError: 保存失败时抛出
        """
        try:
            directory = os.path.dirname(ibc_path)
            if directory and not os.path.exists(directory):
                os.makedirs(directory)
            
            with open(ibc_path, 'w', encoding='utf-8') as f:
                f.write(ibc_content)
        except Exception as e:
            raise IOError(f"保存IBC代码失败 [{ibc_path}]: {e}") from e
    
    @staticmethod
    def load_ibc_content(ibc_path: str) -> str:
        """加载IBC代码，文件不存在时返回空字符串
        
        Args:
            ibc_path: IBC文件路径
            
        Returns:
            str: IBC代码内容，文件不存在时返回空字符串
            
        Raises:
            IOError: 读取失败时抛出
        """
        if not os.path.exists(ibc_path):
            return ""
        
        try:
            with open(ibc_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            raise IOError(f"读取IBC代码失败 [{ibc_path}]: {e}") from e
    
    # ==================== AST数据管理 ====================
    
    @staticmethod
    def build_ast_path(ibc_root: str, file_path: str) -> str:
        """构建AST文件路径: ibc_root/file_path_ibc_ast.json
        
        Args:
            ibc_root: IBC文件根目录
            file_path: 文件相对路径
            
        Returns:
            str: 完整的AST文件路径
        """
        # 解决Windows和Linux路径分隔符问题
        normalized_file_path = file_path.replace('/', os.sep)
        return os.path.join(ibc_root, f"{normalized_file_path}_ibc_ast.json")
    
    @staticmethod
    def save_ast(ast_path: str, ast_dict: Dict[int, IbcBaseAstNode]) -> None:
        """保存AST到JSON文件
        
        Args:
            ast_path: AST文件路径
            ast_dict: AST节点字典 {节点uid: AST节点对象}
            
        Raises:
            IOError: 保存失败时抛出
        """
        try:
            directory = os.path.dirname(ast_path)
            if directory and not os.path.exists(directory):
                os.makedirs(directory)
            
            # 序列化AST节点
            serializable_dict = {}
            for uid, node in ast_dict.items():
                node_dict = node.to_dict()
                node_dict["_class_type"] = type(node).__name__
                serializable_dict[str(uid)] = node_dict
            
            with open(ast_path, 'w', encoding='utf-8') as f:
                json.dump(serializable_dict, f, ensure_ascii=False, indent=2)
        except (IOError, OSError, ValueError) as e:
            raise IOError(f"保存AST失败 [{ast_path}]: {e}") from e
    
    @staticmethod
    def load_ast(ast_path: str) -> Dict[int, IbcBaseAstNode]:
        """加载AST字典，文件不存在时返回空字典
        
        Args:
            ast_path: AST文件路径
            
        Returns:
            Dict[int, IbcBaseAstNode]: AST节点字典，文件不存在时返回空字典
            
        Raises:
            IOError: 加载失败时抛出
        """
        if not os.path.exists(ast_path):
            return {}
        
        try:
            with open(ast_path, 'r', encoding='utf-8') as f:
                serializable_dict = json.load(f)
            
            # 反序列化AST节点
            ast_dict: Dict[int, IbcBaseAstNode] = {}
            for uid_str, node_dict in serializable_dict.items():
                uid = int(uid_str)
                node = IbcFileManager._create_node_from_dict(node_dict)
                ast_dict[uid] = node
            
            return ast_dict
        except (IOError, OSError, ValueError) as e:
            raise IOError(f"加载AST失败 [{ast_path}]: {e}") from e
    
    @staticmethod
    def _create_node_from_dict(node_dict: Dict[str, Any]) -> IbcBaseAstNode:
        """根据字典创建对应类型的AST节点
        
        Args:
            node_dict: 节点字典，必须包含_class_type字段
            
        Returns:
            IbcBaseAstNode: 创建的AST节点对象
        """
        class_type = node_dict.get("_class_type", "IbcBaseAstNode")
        
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
            return IbcBaseAstNode.from_dict(node_dict)
