"""IBC数据管理器 - 统一管理IBC相关数据的持久化存储"""
import json
import os
from typing import Dict, Any, List
from typedef.ibc_data_types import (
    IbcBaseAstNode, AstNodeType, ModuleNode, ClassNode, 
    FunctionNode, VariableNode, BehaviorStepNode,
    SymbolNode, VisibilityTypes
)
from typedef.cmd_data_types import Colors


class IbcDataStore:
    """IBC数据管理器 - 单例模式"""
    
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(IbcDataStore, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, '_initialized'):
            self._initialized = True
    
    # ==================== IBC代码文件管理 ====================
    
    def build_ibc_path(self, ibc_root: str, file_path: str) -> str:
        """构建IBC文件路径: ibc_root/file_path.ibc"""
        # 解决Windows和Linux路径分隔符问题
        normalized_file_path = file_path.replace('/', os.sep)
        return os.path.join(ibc_root, f"{normalized_file_path}.ibc")
    
    def save_ibc_code(self, ibc_path: str, ibc_code: str) -> None:
        """保存IBC代码到文件"""
        try:
            directory = os.path.dirname(ibc_path)
            if directory and not os.path.exists(directory):
                os.makedirs(directory)
            
            with open(ibc_path, 'w', encoding='utf-8') as f:
                f.write(ibc_code)
        except Exception as e:
            raise IOError(f"保存IBC代码失败 [{ibc_path}]: {e}") from e
    
    def load_ibc_code(self, ibc_path: str) -> str:
        """加载IBC代码，文件不存在时返回空字符串"""
        if not os.path.exists(ibc_path):
            return ""
        
        try:
            with open(ibc_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            raise IOError(f"读取IBC代码失败 [{ibc_path}]: {e}") from e
    
    # ==================== AST数据管理 ====================
    
    def build_ast_path(self, ibc_root: str, file_path: str) -> str:
        """构建AST文件路径: ibc_root/file_path_ibc_ast.json"""
        # 解决Windows和Linux路径分隔符问题
        normalized_file_path = file_path.replace('/', os.sep)
        return os.path.join(ibc_root, f"{normalized_file_path}_ibc_ast.json")
    
    def save_ast(self, ast_path: str, ast_dict: Dict[int, IbcBaseAstNode]) -> None:
        """保存AST到JSON文件"""
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
    
    def load_ast(self, ast_path: str) -> Dict[int, IbcBaseAstNode]:
        """加载AST字典，文件不存在时返回空字典"""
        if not os.path.exists(ast_path):
            return {}
        
        try:
            with open(ast_path, 'r', encoding='utf-8') as f:
                serializable_dict = json.load(f)
            
            # 反序列化AST节点
            ast_dict: Dict[int, IbcBaseAstNode] = {}
            for uid_str, node_dict in serializable_dict.items():
                uid = int(uid_str)
                node = self._create_node_from_dict(node_dict)
                ast_dict[uid] = node
            
            return ast_dict
        except (IOError, OSError, ValueError) as e:
            raise IOError(f"加载AST失败 [{ast_path}]: {e}") from e
    
    def _create_node_from_dict(self, node_dict: Dict[str, Any]) -> IbcBaseAstNode:
        """根据字典创建对应类型的AST节点"""
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
    
    # ==================== 校验数据管理 ====================
    
    def build_verify_path(self, ibc_root: str, file_path: str) -> str:
        """构建校验文件路径: ibc_root/file_path_verify.json"""
        # 解决Windows和Linux路径分隔符问题
        normalized_file_path = file_path.replace('/', os.sep)
        return os.path.join(ibc_root, f"{normalized_file_path}_verify.json")
    
    def save_verify_data(self, verify_path: str, verify_data: Dict[str, str]) -> None:
        """保存校验数据到文件"""
        try:
            directory = os.path.dirname(verify_path)
            if directory and not os.path.exists(directory):
                os.makedirs(directory)
            
            with open(verify_path, 'w', encoding='utf-8') as f:
                json.dump(verify_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            raise IOError(f"保存校验数据失败 [{verify_path}]: {e}") from e
    
    def load_verify_data(self, verify_path: str) -> Dict[str, str]:
        """加载校验数据，文件不存在时返回空字典"""
        if not os.path.exists(verify_path):
            return {}
        
        try:
            with open(verify_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            raise IOError(f"读取校验数据失败 [{verify_path}]: {e}") from e
    
    def update_verify_code(self, ibc_root: str, file_path: str, code_type: str = 'ibc') -> None:
        """更新单个文件的校验码"""
        from libs.ibc_funcs import IbcFuncs
        
        ibc_path = self.build_ibc_path(ibc_root, file_path)
        verify_path = self.build_verify_path(ibc_root, file_path)
        
        if not os.path.exists(ibc_path):
            raise FileNotFoundError(f"IBC文件不存在: {ibc_path}")
        
        ibc_content = self.load_ibc_code(ibc_path)
        if not ibc_content:
            raise ValueError(f"IBC文件内容为空: {ibc_path}")
        
        # 计算MD5
        current_md5 = IbcFuncs.calculate_text_md5(ibc_content)
        
        # 加载并更新校验数据
        verify_data = self.load_verify_data(verify_path)
        verify_data[f'{code_type}_verify_code'] = current_md5
        
        self.save_verify_data(verify_path, verify_data)
    
    def batch_update_verify_codes(self, ibc_root: str, file_paths: List[str]) -> None:
        """批量更新校验码"""
        for file_path in file_paths:
            self.update_verify_code(ibc_root, file_path)
    
    # ==================== 符号表数据管理 ====================
    # 注意：符号表采用目录级存储，一个symbols.json包含该目录下所有文件的符号
    
    def build_symbols_path(self, ibc_root: str, file_path: str) -> str:
        """构建符号表路径（目录级）: ibc_root/dir/symbols.json"""
        file_dir = os.path.dirname(file_path)
        if file_dir:
            symbols_dir = os.path.join(ibc_root, file_dir)
        else:
            symbols_dir = ibc_root
        return os.path.join(symbols_dir, 'symbols.json')
    
    def save_symbols(
        self,
        symbols_path: str,
        file_name: str,
        symbol_table: Dict[str, SymbolNode]
    ) -> None:
        """保存符号表（目录级存储，自动合并）"""
        # 加载目录级符号表
        dir_symbols = self._load_dir_symbols(symbols_path)
        
        # 更新当前文件的符号
        symbols_dict = {}
        for symbol_name, symbol in symbol_table.items():
            symbols_dict[symbol_name] = symbol.to_dict()
        dir_symbols[file_name] = symbols_dict
        
        # 保存回文件
        try:
            os.makedirs(os.path.dirname(symbols_path), exist_ok=True)
            with open(symbols_path, 'w', encoding='utf-8') as f:
                json.dump(dir_symbols, f, ensure_ascii=False, indent=2)
        except Exception as e:
            raise IOError(f"保存符号表失败 [{symbols_path}]: {e}") from e
    
    def load_symbols(self, symbols_path: str, file_name: str) -> Dict[str, SymbolNode]:
        """加载符号表，文件不存在或无数据时返回空字典"""
        dir_symbols = self._load_dir_symbols(symbols_path)
        
        file_symbol_data = dir_symbols.get(file_name, {})
        
        if not file_symbol_data:
            return {}
        
        # 反序列化符号表
        symbol_table: Dict[str, SymbolNode] = {}
        for symbol_name, symbol_dict in file_symbol_data.items():
            symbol_node = SymbolNode.from_dict(symbol_dict)
            symbol_table[symbol_name] = symbol_node
        return symbol_table
    
    def update_symbol_info(
        self,
        symbols_path: str,
        file_name: str,
        symbol_name: str,
        normalized_name: str,
        visibility: VisibilityTypes
    ) -> None:
        """更新符号的规范化信息"""
        # 加载符号表
        symbol_table = self.load_symbols(symbols_path, file_name)
        
        # 查找并更新符号
        symbol = symbol_table.get(symbol_name)
        if not symbol:
            raise ValueError(f"符号不存在: {symbol_name}，文件: {file_name}")
        
        symbol.update_normalized_info(normalized_name, visibility)
        
        # 保存更新后的符号表
        self.save_symbols(symbols_path, file_name, symbol_table)
    
    def _load_dir_symbols(self, symbols_path: str) -> Dict[str, Any]:
        """内部方法：加载目录级符号表，文件不存在时返回空字典"""
        if not os.path.exists(symbols_path):
            return {}
        
        try:
            with open(symbols_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            raise IOError(f"读取符号表失败 [{symbols_path}]: {e}") from e


# 单例实例
_instance = IbcDataStore()


def get_instance() -> IbcDataStore:
    """获取IbcDataManager单例实例"""
    return _instance
