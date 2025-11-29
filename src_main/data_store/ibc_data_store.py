"""
IBC数据管理器

负责IBC分析相关的所有持久化数据的存取操作：
1. AST数据的存储和加载
2. 符号表数据的存储和加载
"""
import json
import os
from typing import Dict, Any
from typedef.ibc_data_types import (
    IbcBaseAstNode, AstNodeType, ModuleNode, ClassNode, 
    FunctionNode, VariableNode, BehaviorStepNode,
    SymbolNode, FileSymbolTable
)
from typedef.cmd_data_types import Colors


class IbcDataStore:
    """IBC数据管理器，负责AST和符号表的持久化存储和加载"""
    
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(IbcDataStore, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, '_initialized'):
            self._initialized = True
            self.ast_dict: Dict[int, IbcBaseAstNode] = {}
    
    # ==================== AST数据管理 ====================
    
    def save_ast_to_file(self, ast_dict: Dict[int, IbcBaseAstNode], file_path: str) -> bool:
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
    
    def load_ast_from_file(self, file_path: str) -> Dict[int, IbcBaseAstNode]:
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
            ast_dict: Dict[int, IbcBaseAstNode] = {}
            for uid_str, node_dict in serializable_dict.items():
                uid = int(uid_str)
                node = self._create_node_from_dict(node_dict)
                ast_dict[uid] = node
            
            self.ast_dict = ast_dict
            return ast_dict
            
        except (IOError, OSError, ValueError) as e:
            print(f"从文件加载AST失败: {e}")
            return {}
    
    def _create_node_from_dict(self, node_dict: Dict[str, Any]) -> IbcBaseAstNode:
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
            return IbcBaseAstNode.from_dict(node_dict)
    
    def get_current_ast(self) -> Dict[int, IbcBaseAstNode]:
        """获取当前的AST字典"""
        return self.ast_dict
    
    def set_current_ast(self, ast_dict: Dict[int, IbcBaseAstNode]) -> None:
        """设置当前的AST字典"""
        self.ast_dict = ast_dict
    
    # ==================== 符号表数据管理 ====================
    
    def get_symbols_file_path(self, ibc_root_path: str, file_path: str) -> str:
        """
        获取文件对应的symbols.json路径
        
        Args:
            ibc_root_path: IBC根目录路径
            file_path: 文件相对路径
            
        Returns:
            str: symbols.json的完整路径
        """
        # 获取文件所在目录
        file_dir = os.path.dirname(file_path)
        if file_dir:
            symbols_dir = os.path.join(ibc_root_path, file_dir)
        else:
            symbols_dir = ibc_root_path
        
        return os.path.join(symbols_dir, 'symbols.json')
    
    def load_dir_symbols_table(self, symbols_file: str) -> Dict[str, Any]:
        """
        加载目录级别的符号表
        
        Args:
            symbols_file: symbols.json文件路径
            
        Returns:
            Dict[str, Any]: 目录符号表字典
        """
        if not os.path.exists(symbols_file):
            return {}
        
        try:
            with open(symbols_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"  {Colors.WARNING}警告: 读取符号表失败 {symbols_file}: {e}{Colors.ENDC}")
            return {}
    
    def load_file_symbols(self, ibc_root_path: str, file_path: str) -> FileSymbolTable:
        """
        加载指定文件的符号数据
        
        Args:
            ibc_root_path: IBC根目录路径
            file_path: 文件相对路径
            
        Returns:
            FileSymbolTable: 文件符号表对象
        """
        symbols_file = self.get_symbols_file_path(ibc_root_path, file_path)
        dir_symbols_table = self.load_dir_symbols_table(symbols_file)
        
        # 从目录符号表中获取当前文件的数据
        file_name = os.path.basename(file_path)
        file_symbol_data = dir_symbols_table.get(file_name, {})
        
        if not file_symbol_data:
            return FileSymbolTable()
        
        return FileSymbolTable.from_dict(file_symbol_data)
    
    def save_file_symbols(
        self, 
        ibc_root_path: str, 
        file_path: str, 
        file_symbol_table: FileSymbolTable
    ) -> bool:
        """
        保存文件的符号数据到对应目录的symbols.json
        
        Args:
            ibc_root_path: IBC根目录路径
            file_path: 文件相对路径
            file_symbol_table: 文件符号表对象
            
        Returns:
            bool: 保存是否成功
        """
        symbols_file = self.get_symbols_file_path(ibc_root_path, file_path)
        
        # 加载目录级别的符号表
        dir_symbols_table = self.load_dir_symbols_table(symbols_file)
        
        # 更新当前文件的数据
        file_name = os.path.basename(file_path)
        dir_symbols_table[file_name] = file_symbol_table.to_dict()
        
        # 保存更新后的符号表
        try:
            os.makedirs(os.path.dirname(symbols_file), exist_ok=True)
            with open(symbols_file, 'w', encoding='utf-8') as f:
                json.dump(dir_symbols_table, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"  {Colors.FAIL}错误: 保存符号表失败: {e}{Colors.ENDC}")
            return False
    
    def update_symbol_normalized_info(
        self,
        ibc_root_path: str,
        file_path: str,
        symbol_name: str,
        normalized_name: str,
        visibility: str
    ) -> bool:
        """
        更新符号的规范化信息
        
        Args:
            ibc_root_path: IBC根目录路径
            file_path: 文件相对路径
            symbol_name: 符号名称
            normalized_name: 规范化名称
            visibility: 可见性
            
        Returns:
            bool: 更新是否成功
        """
        # 加载文件符号表
        file_symbol_table = self.load_file_symbols(ibc_root_path, file_path)
        
        # 更新符号信息
        symbol = file_symbol_table.get_symbol(symbol_name)
        if not symbol:
            print(f"  {Colors.WARNING}警告: 找不到符号 {symbol_name}{Colors.ENDC}")
            return False
        
        symbol.update_normalized_info(normalized_name, visibility)
        
        # 保存更新后的符号表
        return self.save_file_symbols(ibc_root_path, file_path, file_symbol_table)


# 单例实例
_instance = IbcDataStore()


def get_instance() -> IbcDataStore:
    """获取IbcDataManager单例实例"""
    return _instance
