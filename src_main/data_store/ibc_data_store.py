"""
IBC数据管理器

负责IBC分析相关的所有持久化数据的存取操作：
1. IBC代码文件 (.ibc) 的存储和加载
2. AST数据 (*_ibc_ast.json) 的存储和加载
3. 符号表数据 (symbols.json) 的存储和加载
4. 校验数据 (*_verify.json) 的存储和加载

使用指南：
- 路径构建方法：build_*_path(ibc_root, file_path) -> str
- 数据保存方法：save_*(path, data) -> bool
- 数据加载方法：load_*(path) -> data (失败返回空对象)
- 数据更新方法：update_*(ibc_root, file_path, ...) -> bool
"""
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
    """
    IBC数据管理器 - 统一管理所有IBC相关数据的持久化
    
    功能概览：
    1. IBC代码管理 - .ibc文件的读写
    2. AST管理 - 抽象语法树的序列化和反序列化
    3. 符号表管理 - 符号数据的存储和检索
    4. 校验数据管理 - MD5校验码的维护
    
    设计原则：
    - 所有路径构建方法统一使用 build_*_path 前缀
    - 所有保存方法返回 bool 表示成功/失败
    - 所有加载方法失败时返回空对象（空字符串、空字典等）
    - 参数顺序统一：先 ibc_root，后 file_path
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
    # 方法说明：
    # - build_ibc_path: 构建.ibc文件的完整路径
    # - save_ibc_code: 保存IBC代码到.ibc文件
    # - load_ibc_code: 从.ibc文件加载代码
    
    def build_ibc_path(self, ibc_root: str, file_path: str) -> str:
        """
        构建IBC代码文件的完整路径
        
        Args:
            ibc_root: IBC根目录路径
            file_path: 相对文件路径（不含.ibc后缀）
            
        Returns:
            str: 完整的.ibc文件路径
            
        Example:
            >>> store.build_ibc_path("/root/ibc", "user/manager")
            "/root/ibc/user/manager.ibc"
        """
        # 解决Windows和Linux路径分隔符问题
        normalized_file_path = file_path.replace('/', os.sep)
        return os.path.join(ibc_root, f"{normalized_file_path}.ibc")
    
    def save_ibc_code(self, ibc_path: str, ibc_code: str) -> bool:
        """
        保存IBC代码到文件
        
        Args:
            ibc_path: IBC文件的完整路径
            ibc_code: 要保存的IBC代码内容
            
        Returns:
            bool: 保存成功返回True，失败返回False
        """
        try:
            directory = os.path.dirname(ibc_path)
            if directory and not os.path.exists(directory):
                os.makedirs(directory)
            
            with open(ibc_path, 'w', encoding='utf-8') as f:
                f.write(ibc_code)
            return True
        except Exception as e:
            print(f"{Colors.FAIL}保存IBC代码失败: {e}{Colors.ENDC}")
            return False
    
    def load_ibc_code(self, ibc_path: str) -> str:
        """
        从文件加载IBC代码
        
        Args:
            ibc_path: IBC文件的完整路径
            
        Returns:
            str: IBC代码内容，文件不存在或读取失败返回空字符串
        """
        if not os.path.exists(ibc_path):
            return ""
        
        try:
            with open(ibc_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            print(f"{Colors.WARNING}读取IBC代码失败: {e}{Colors.ENDC}")
            return ""
    
    # ==================== AST数据管理 ====================
    # 方法说明：
    # - build_ast_path: 构建AST文件的完整路径
    # - save_ast: 将AST字典保存到JSON文件
    # - load_ast: 从JSON文件加载AST字典
    
    def build_ast_path(self, ibc_root: str, file_path: str) -> str:
        """
        构建AST文件的完整路径
        
        Args:
            ibc_root: IBC根目录路径
            file_path: 相对文件路径
            
        Returns:
            str: 完整的AST文件路径
            
        Example:
            >>> store.build_ast_path("/root/ibc", "user/manager")
            "/root/ibc/user/manager_ibc_ast.json"
        """
        # 解决Windows和Linux路径分隔符问题
        normalized_file_path = file_path.replace('/', os.sep)
        return os.path.join(ibc_root, f"{normalized_file_path}_ibc_ast.json")
    
    def save_ast(self, ast_path: str, ast_dict: Dict[int, IbcBaseAstNode]) -> bool:
        """
        将AST字典保存到JSON文件
        
        Args:
            ast_path: AST文件的完整路径
            ast_dict: AST节点字典，key为节点UID，value为节点对象
            
        Returns:
            bool: 保存成功返回True，失败返回False
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
            return True
        except (IOError, OSError, ValueError) as e:
            print(f"{Colors.FAIL}保存AST失败: {e}{Colors.ENDC}")
            return False
    
    def load_ast(self, ast_path: str) -> Dict[int, IbcBaseAstNode]:
        """
        从JSON文件加载AST字典
        
        Args:
            ast_path: AST文件的完整路径
            
        Returns:
            Dict[int, IbcBaseAstNode]: AST节点字典，文件不存在或加载失败返回空字典
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
                node = self._create_node_from_dict(node_dict)
                ast_dict[uid] = node
            
            return ast_dict
        except (IOError, OSError, ValueError) as e:
            print(f"{Colors.WARNING}加载AST失败: {e}{Colors.ENDC}")
            return {}
    
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
    # 方法说明：
    # - build_verify_path: 构建校验数据文件的完整路径
    # - save_verify_data: 保存校验数据到文件
    # - load_verify_data: 从文件加载校验数据
    # - update_verify_code: 更新单个文件的校验码
    # - batch_update_verify_codes: 批量更新多个文件的校验码
    
    def build_verify_path(self, ibc_root: str, file_path: str) -> str:
        """
        构建校验数据文件的完整路径
        
        Args:
            ibc_root: IBC根目录路径
            file_path: 相对文件路径
            
        Returns:
            str: 完整的校验数据文件路径
            
        Example:
            >>> store.build_verify_path("/root/ibc", "user/manager")
            "/root/ibc/user/manager_verify.json"
        """
        # 解决Windows和Linux路径分隔符问题
        normalized_file_path = file_path.replace('/', os.sep)
        return os.path.join(ibc_root, f"{normalized_file_path}_verify.json")
    
    def save_verify_data(self, verify_path: str, verify_data: Dict[str, str]) -> bool:
        """
        保存校验数据到文件
        
        Args:
            verify_path: 校验数据文件的完整路径
            verify_data: 校验数据字典（通常包含MD5值）
            
        Returns:
            bool: 保存成功返回True，失败返回False
        """
        try:
            directory = os.path.dirname(verify_path)
            if directory and not os.path.exists(directory):
                os.makedirs(directory)
            
            with open(verify_path, 'w', encoding='utf-8') as f:
                json.dump(verify_data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"{Colors.WARNING}保存校验数据失败: {e}{Colors.ENDC}")
            return False
    
    def load_verify_data(self, verify_path: str) -> Dict[str, str]:
        """
        从文件加载校验数据
        
        Args:
            verify_path: 校验数据文件的完整路径
            
        Returns:
            Dict[str, str]: 校验数据字典，文件不存在或读取失败返回空字典
        """
        if not os.path.exists(verify_path):
            return {}
        
        try:
            with open(verify_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"{Colors.WARNING}读取校验数据失败: {e}{Colors.ENDC}")
            return {}
    
    def update_verify_code(self, ibc_root: str, file_path: str, code_type: str = 'ibc') -> bool:
        """
        更新单个文件的校验码
        
        Args:
            ibc_root: IBC根目录路径
            file_path: 相对文件路径
            code_type: 校验码类型，'ibc' 表示IBC代码校验码
            
        Returns:
            bool: 更新成功返回True，失败返回False
        """
        from libs.ibc_funcs import IbcFuncs
        
        ibc_path = self.build_ibc_path(ibc_root, file_path)
        verify_path = self.build_verify_path(ibc_root, file_path)
        
        if not os.path.exists(ibc_path):
            return False
        
        try:
            ibc_content = self.load_ibc_code(ibc_path)
            if not ibc_content:
                return False
            
            # 计算MD5
            current_md5 = IbcFuncs.calculate_text_md5(ibc_content)
            
            # 加载并更新校验数据
            verify_data = self.load_verify_data(verify_path)
            verify_data[f'{code_type}_verify_code'] = current_md5
            
            return self.save_verify_data(verify_path, verify_data)
        except Exception as e:
            print(f"{Colors.WARNING}更新校验码失败 [{file_path}]: {e}{Colors.ENDC}")
            return False
    
    def batch_update_verify_codes(self, ibc_root: str, file_paths: List[str]) -> Dict[str, int]:
        """
        批量更新多个文件的校验码
        
        Args:
            ibc_root: IBC根目录路径
            file_paths: 相对文件路径列表
            
        Returns:
            Dict[str, int]: 包含 'success' 和 'failed' 计数的字典
        """
        result = {'success': 0, 'failed': 0}
        
        for file_path in file_paths:
            if self.update_verify_code(ibc_root, file_path):
                result['success'] += 1
            else:
                result['failed'] += 1
        
        if result['failed'] > 0:
            print(f"{Colors.WARNING}批量更新完成: {result['success']} 成功, {result['failed']} 失败{Colors.ENDC}")
        
        return result
    
    # ==================== 符号表数据管理 ====================
    # 方法说明：
    # - build_symbols_path: 构建符号表文件的完整路径（目录级别的symbols.json）
    # - save_symbols: 保存文件的符号表数据
    # - load_symbols: 加载文件的符号表数据
    # - update_symbol_info: 更新单个符号的规范化信息
    # 注意：符号表采用目录级存储，一个symbols.json包含该目录下所有文件的符号
    
    def build_symbols_path(self, ibc_root: str, file_path: str) -> str:
        """
        构建符号表文件的完整路径
        
        Args:
            ibc_root: IBC根目录路径
            file_path: 相对文件路径
            
        Returns:
            str: 符号表文件路径（目录级别的symbols.json）
            
        Example:
            >>> store.build_symbols_path("/root/ibc", "user/manager")
            "/root/ibc/user/symbols.json"
        """
        file_dir = os.path.dirname(file_path)
        if file_dir:
            symbols_dir = os.path.join(ibc_root, file_dir)
        else:
            symbols_dir = ibc_root
        return os.path.join(symbols_dir, 'symbols.json')
    
    def save_symbols(
        self, 
        ibc_root: str, 
        file_path: str, 
        symbol_table: Dict[str, SymbolNode]
    ) -> bool:
        """
        保存文件的符号表数据
        
        Args:
            ibc_root: IBC根目录路径
            file_path: 相对文件路径
            symbol_table: 符号表字典，key为符号名，value为符号节点
            
        Returns:
            bool: 保存成功返回True，失败返回False
            
        Note:
            符号表采用目录级存储，会加载现有symbols.json，更新该文件的符号后保存
        """
        symbols_path = self.build_symbols_path(ibc_root, file_path)
        
        # 加载目录级符号表
        dir_symbols = self._load_dir_symbols(symbols_path)
        
        # 更新当前文件的符号
        file_name = os.path.basename(file_path)
        symbols_dict = {}
        for symbol_name, symbol in symbol_table.items():
            symbols_dict[symbol_name] = symbol.to_dict()
        dir_symbols[file_name] = symbols_dict
        
        # 保存回文件
        try:
            os.makedirs(os.path.dirname(symbols_path), exist_ok=True)
            with open(symbols_path, 'w', encoding='utf-8') as f:
                json.dump(dir_symbols, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"{Colors.FAIL}保存符号表失败: {e}{Colors.ENDC}")
            return False
    
    def load_symbols(self, ibc_root: str, file_path: str) -> Dict[str, SymbolNode]:
        """
        加载文件的符号表数据
        
        Args:
            ibc_root: IBC根目录路径
            file_path: 相对文件路径
            
        Returns:
            Dict[str, SymbolNode]: 符号表字典，文件不存在或加载失败返回空字典
        """
        symbols_path = self.build_symbols_path(ibc_root, file_path)
        dir_symbols = self._load_dir_symbols(symbols_path)
        
        file_name = os.path.basename(file_path)
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
        ibc_root: str,
        file_path: str,
        symbol_name: str,
        normalized_name: str,
        visibility: VisibilityTypes
    ) -> bool:
        """
        更新符号的规范化信息
        
        Args:
            ibc_root: IBC根目录路径
            file_path: 相对文件路径
            symbol_name: 符号名称
            normalized_name: 规范化后的名称
            visibility: 可见性类型
            
        Returns:
            bool: 更新成功返回True，失败返回False
        """
        # 加载符号表
        symbol_table = self.load_symbols(ibc_root, file_path)
        
        # 查找并更新符号
        symbol = symbol_table.get(symbol_name)
        if not symbol:
            print(f"{Colors.WARNING}符号不存在: {symbol_name}{Colors.ENDC}")
            return False
        
        symbol.update_normalized_info(normalized_name, visibility)
        
        # 保存更新后的符号表
        return self.save_symbols(ibc_root, file_path, symbol_table)
    
    def _load_dir_symbols(self, symbols_path: str) -> Dict[str, Any]:
        """
        内部方法：加载目录级别的符号表
        
        Args:
            symbols_path: 符号表文件的完整路径
            
        Returns:
            Dict[str, Any]: 目录级符号表字典
        """
        if not os.path.exists(symbols_path):
            return {}
        
        try:
            with open(symbols_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"{Colors.WARNING}读取符号表失败: {e}{Colors.ENDC}")
            return {}


# 单例实例
_instance = IbcDataStore()


def get_instance() -> IbcDataStore:
    """获取IbcDataManager单例实例"""
    return _instance
