"""IBC数据管理器 - 统一管理IBC相关数据的持久化存储

本类作为facade模式，为保持向后兼容，委托给专门的管理器类：
- IbcFileManager: 处理IBC文件和AST文件的读写操作
- SymbolTableManager: 处理符号表的存储与加载
- VerifyDataManager: 处理校验数据的管理
"""
from typing import Dict, Any, List, Tuple
from typedef.ibc_data_types import (
    IbcBaseAstNode, SymbolMetadata
)

# 导入专门的管理器类
from data_store.ibc_file_manager import IbcFileManager
from data_store.symbol_table_manager import SymbolTableManager
from data_store.verify_data_manager import VerifyDataManager


class IbcDataStore:
    """IBC数据管理器 - 单例模式
    
    作为facade模式的统一入口，所有方法都委托给专门的管理器类。
    这样既保持了向后兼容性，又实现了职责分离。
    """
    
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(IbcDataStore, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, '_initialized'):
            self._initialized = True
    
    # ==================== IBC代码文件管理 ====================
    # 委托给 IbcFileManager
    
    def build_ibc_path(self, ibc_root: str, file_path: str) -> str:
        """构建IBC文件路径: ibc_root/file_path.ibc
        
        委托给 IbcFileManager.build_ibc_path
        """
        return IbcFileManager.build_ibc_path(ibc_root, file_path)
    
    def save_ibc_content(self, ibc_path: str, ibc_content: str) -> None:
        """保存IBC代码到文件
        
        委托给 IbcFileManager.save_ibc_content
        """
        return IbcFileManager.save_ibc_content(ibc_path, ibc_content)
    
    def load_ibc_content(self, ibc_path: str) -> str:
        """加载IBC代码，文件不存在时返回空字符串
        
        委托给 IbcFileManager.load_ibc_content
        """
        return IbcFileManager.load_ibc_content(ibc_path)
    
    # ==================== AST数据管理 ====================
    # 委托给 IbcFileManager
    
    def build_ast_path(self, ibc_root: str, file_path: str) -> str:
        """构建AST文件路径: ibc_root/file_path_ibc_ast.json
        
        委托给 IbcFileManager.build_ast_path
        """
        return IbcFileManager.build_ast_path(ibc_root, file_path)
    
    def save_ast(self, ast_path: str, ast_dict: Dict[int, IbcBaseAstNode]) -> None:
        """保存AST到JSON文件
        
        委托给 IbcFileManager.save_ast
        """
        return IbcFileManager.save_ast(ast_path, ast_dict)
    
    def load_ast(self, ast_path: str) -> Dict[int, IbcBaseAstNode]:
        """加载AST字典，文件不存在时返回空字典
        
        委托给 IbcFileManager.load_ast
        """
        return IbcFileManager.load_ast(ast_path)
    
    # ==================== 校验数据管理 ====================
    # 委托给 VerifyDataManager
    # 新版：统一verify文件管理（保存在 icp_proj_data/icp_verify_data.json）
    
    def load_file_verify_data(self, data_dir_path: str, file_path: str) -> Dict[str, str]:
        """从统一的verify文件中加载指定文件的校验数据
        
        委托给 VerifyDataManager.load_file_verify_data
        """
        return VerifyDataManager.load_file_verify_data(data_dir_path, file_path)
    
    def save_file_verify_data(self, data_dir_path: str, file_path: str, verify_data: Dict[str, str]) -> None:
        """将指定文件的校验数据保存到统一的verify文件中
        
        委托给 VerifyDataManager.save_file_verify_data
        """
        return VerifyDataManager.save_file_verify_data(data_dir_path, file_path, verify_data)
    
    def update_file_verify_data(self, data_dir_path: str, file_path: str, updates: Dict[str, str]) -> None:
        """更新指定文件的校验数据中的特定字段（增量更新）
        
        委托给 VerifyDataManager.update_file_verify_data
        """
        return VerifyDataManager.update_file_verify_data(data_dir_path, file_path, updates)
    
    def batch_update_ibc_verify_codes(
        self,
        data_dir_path: str,
        ibc_root: str,
        file_paths: List[str]
    ) -> None:
        """批量更新所有ibc文件的MD5校验码到统一的verify文件
        
        委托给 VerifyDataManager.batch_update_ibc_verify_codes
        """
        return VerifyDataManager.batch_update_ibc_verify_codes(data_dir_path, ibc_root, file_paths)
    
    # ==================== 旧版校验数据管理（等待废弃，保留以保持向后兼容） ====================
    # 委托给 VerifyDataManager
    
    def build_verify_path(self, ibc_root: str, file_path: str) -> str:
        """构建verify文件路径: ibc_root/file_path_verify.json
        
        @deprecated: 请使用 load_file_verify_data 和 save_file_verify_data
        委托给 VerifyDataManager.build_verify_path
        """
        return VerifyDataManager.build_verify_path(ibc_root, file_path)
    
    def save_verify_data(self, verify_path: str, verify_data: Dict[str, str]) -> None:
        """保存校验数据到文件
        
        @deprecated: 请使用 save_file_verify_data
        委托给 VerifyDataManager.save_verify_data
        """
        return VerifyDataManager.save_verify_data(verify_path, verify_data)
    
    def load_verify_data(self, verify_path: str) -> Dict[str, str]:
        """加载校验数据，文件不存在时返回空字典
        
        @deprecated: 请使用 load_file_verify_data
        委托给 VerifyDataManager.load_verify_data
        """
        return VerifyDataManager.load_verify_data(verify_path)
    
    def update_verify_code(self, ibc_root: str, file_path: str, code_type: str = 'ibc') -> None:
        """更新单个文件的校验码
        
        @deprecated: 请使用 batch_update_ibc_verify_codes
        委托给 VerifyDataManager.update_verify_code
        """
        return VerifyDataManager.update_verify_code(ibc_root, file_path, code_type)
    
    def batch_update_verify_codes(self, ibc_root: str, file_paths: List[str]) -> None:
        """批量更新校验码
        
        @deprecated: 请使用 batch_update_ibc_verify_codes
        委托给 VerifyDataManager.batch_update_verify_codes
        """
        return VerifyDataManager.batch_update_verify_codes(ibc_root, file_paths)
    
    # ==================== 符号表数据管理 ====================
    # 委托给 SymbolTableManager
    # 注意：符号表采用目录级存储，一个symbols.json包含该目录下所有文件的符号
        
    def build_symbols_path(self, ibc_root: str, file_path: str) -> str:
        """构建符号表路径（目录级）: ibc_root/dir/symbols.json
        
        委托给 SymbolTableManager.build_symbols_path
        """
        return SymbolTableManager.build_symbols_path(ibc_root, file_path)
        
    def save_symbols(
        self,
        symbols_path: str,
        file_name: str,
        symbols_tree: Dict[str, Any],
        symbols_metadata: Dict[str, SymbolMetadata],
    ) -> None:
        """保存符号信息（目录级存储，自动合并）
        
        委托给 SymbolTableManager.save_symbols
        """
        return SymbolTableManager.save_symbols(symbols_path, file_name, symbols_tree, symbols_metadata)
        
    def load_symbols(self, symbols_path: str, file_name: str) -> Tuple[Dict[str, Any], Dict[str, SymbolMetadata]]:
        """加载单个文件的符号树和元数据，文件不存在或无数据时返回空结构
        
        委托给 SymbolTableManager.load_symbols
        """
        return SymbolTableManager.load_symbols(symbols_path, file_name)
        
    def load_dependency_symbol_tables(
        self,
        ibc_root: str,
        dependent_relation: Dict[str, List[str]],
        current_file_path: str
    ) -> Dict[str, Tuple[Dict[str, Any], Dict[str, SymbolMetadata]]]:
        """根据依赖关系为单个文件批量加载依赖符号数据
        
        委托给 SymbolTableManager.load_dependency_symbol_tables
        """
        return SymbolTableManager.load_dependency_symbol_tables(ibc_root, dependent_relation, current_file_path)
        
    def is_dependency_symbol_tables_valid(
        self,
        ibc_root: str,
        dependent_relation: Dict[str, List[str]],
        current_file_path: str
    ) -> bool:
        """检查当前文件的依赖符号数据是否都存在且有内容
        
        委托给 SymbolTableManager.is_dependency_symbol_tables_valid
        """
        return SymbolTableManager.is_dependency_symbol_tables_valid(ibc_root, dependent_relation, current_file_path)
        
    def update_symbol_info(
        self,
        symbols_path: str,
        file_name: str,
        symbol_path: str,
        normalized_name: str
    ) -> None:
        """更新单个符号的规范化信息
        
        委托给 SymbolTableManager.update_symbol_info
        """
        return SymbolTableManager.update_symbol_info(symbols_path, file_name, symbol_path, normalized_name)
    
    def update_symbols_batch(
        self,
        symbols_path: str,
        file_name: str,
        normalized_mapping: Dict[str, str]
    ) -> int:
        """批量更新符号的规范化信息
        
        委托给 SymbolTableManager.update_symbols_batch
        """
        return SymbolTableManager.update_symbols_batch(symbols_path, file_name, normalized_mapping)


# 单例实例
_instance = IbcDataStore()


def get_instance() -> IbcDataStore:
    """获取IbcDataManager单例实例"""
    return _instance
