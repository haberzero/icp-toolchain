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
    SymbolNode, VisibilityTypes
)
from typedef.cmd_data_types import Colors


class IbcDataStore:
    """IBC数据管理器，负责AST、符号表和校验数据的持久化存储和加载"""
    
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(IbcDataStore, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, '_initialized'):
            self._initialized = True
    
    # ==================== IBC代码管理 ====================
    
    def get_ibc_file_path(self, ibc_root_path: str, file_path: str) -> str:
        """获取文件对应的.ibc文件路径"""
        return os.path.join(ibc_root_path, f"{file_path}.ibc")
    
    def save_ibc_code(self, ibc_file_path: str, ibc_code: str) -> bool:
        """保存IBC代码到文件"""
        try:
            directory = os.path.dirname(ibc_file_path)
            if directory and not os.path.exists(directory):
                os.makedirs(directory)
            
            with open(ibc_file_path, 'w', encoding='utf-8') as f:
                f.write(ibc_code)
            return True
        except Exception as e:
            print(f"保存IBC代码失败: {e}")
            return False
    
    def load_ibc_code(self, ibc_file_path: str) -> str:
        """加载IBC代码，文件不存在则返回空字符串"""
        if not os.path.exists(ibc_file_path):
            return ""
        
        try:
            with open(ibc_file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            print(f"读取IBC代码失败: {e}")
            return ""
    
    # ==================== AST数据管理 ====================
    
    def save_ast_to_file(self, ast_dict: Dict[int, IbcBaseAstNode], file_path: str) -> bool:
        """将AST字典保存到JSON文件"""
        try:
            directory = os.path.dirname(file_path)
            if directory and not os.path.exists(directory):
                os.makedirs(directory)
            
            serializable_dict = {}
            for uid, node in ast_dict.items():
                node_dict = node.to_dict()
                node_dict["_class_type"] = type(node).__name__
                serializable_dict[str(uid)] = node_dict
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(serializable_dict, f, ensure_ascii=False, indent=2)
            return True
        except (IOError, OSError, ValueError) as e:
            print(f"保存AST到文件失败: {e}")
            return False
    
    def load_ast_from_file(self, file_path: str) -> Dict[int, IbcBaseAstNode]:
        """从JSON文件加载AST字典"""
        try:
            if not os.path.exists(file_path):
                print(f"AST文件不存在: {file_path}")
                return {}
            
            with open(file_path, 'r', encoding='utf-8') as f:
                serializable_dict = json.load(f)
            
            ast_dict: Dict[int, IbcBaseAstNode] = {}
            for uid_str, node_dict in serializable_dict.items():
                uid = int(uid_str)
                node = self._create_node_from_dict(node_dict)
                ast_dict[uid] = node
            
            return ast_dict
        except (IOError, OSError, ValueError) as e:
            print(f"从文件加载AST失败: {e}")
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
    
    def get_verify_file_path(self, ibc_root_path: str, file_path: str) -> str:
        """获取文件对应的_verify.json路径"""
        return os.path.join(ibc_root_path, f"{file_path}_verify.json")
    
    def load_verify_data(self, verify_file_path: str) -> Dict[str, str]:
        """加载verify.json文件，不存在则返回空字典"""
        if os.path.exists(verify_file_path):
            try:
                with open(verify_file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"    {Colors.WARNING}警告: 读取verify文件失败，将创建新文件: {e}{Colors.ENDC}")
                return {}
        else:
            return {}
    
    def save_verify_data(self, verify_file_path: str, verify_data: Dict[str, str]) -> bool:
        """保存verify.json文件"""
        try:
            directory = os.path.dirname(verify_file_path)
            if directory and not os.path.exists(directory):
                os.makedirs(directory)
            
            with open(verify_file_path, 'w', encoding='utf-8') as f:
                json.dump(verify_data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"    {Colors.WARNING}警告: 保存verify文件失败: {e}{Colors.ENDC}")
            return False
    
    def update_ibc_verify_code(self, ibc_root_path: str, file_path: str) -> bool:
        """更新单个文件的IBC校验码
        
        Args:
            ibc_root_path: IBC根目录路径
            file_path: 文件路径
            
        Returns:
            bool: 更新是否成功
        """
        from libs.ibc_funcs import IbcFuncs
        
        ibc_file = self.get_ibc_file_path(ibc_root_path, file_path)
        verify_file = self.get_verify_file_path(ibc_root_path, file_path)
        
        if not os.path.exists(ibc_file):
            return False
        
        try:
            ibc_content = self.load_ibc_code(ibc_file)
            if not ibc_content:
                return False
            
            current_ibc_md5 = IbcFuncs.calculate_text_md5(ibc_content)
            
            verify_data = self.load_verify_data(verify_file)
            verify_data['ibc_verify_code'] = current_ibc_md5
            
            return self.save_verify_data(verify_file, verify_data)
        except Exception as e:
            print(f"    {Colors.WARNING}警告: 更新ibc文件MD5失败: {file_path}, {e}{Colors.ENDC}")
            return False
    
    def update_all_ibc_verify_codes(self, ibc_root_path: str, file_paths: List[str]) -> None:
        """批量更新所有IBC文件的校验码
        
        Args:
            ibc_root_path: IBC根目录路径
            file_paths: 文件路径列表
        """
        success_count = 0
        fail_count = 0
        
        for file_path in file_paths:
            if self.update_ibc_verify_code(ibc_root_path, file_path):
                success_count += 1
            else:
                fail_count += 1
        
        if fail_count > 0:
            print(f"    {Colors.WARNING}警告: {fail_count} 个文件更新失败{Colors.ENDC}")
    
    # ==================== 符号表数据管理 ====================
    def get_symbols_file_path(self, ibc_root_path: str, file_path: str) -> str:
        """获取文件对应的symbols.json路径"""
        file_dir = os.path.dirname(file_path)
        if file_dir:
            symbols_dir = os.path.join(ibc_root_path, file_dir)
        else:
            symbols_dir = ibc_root_path
        return os.path.join(symbols_dir, 'symbols.json')
    
    def load_dir_symbols_table(self, symbols_file: str) -> Dict[str, Any]:
        """加载目录级别的符号表"""
        if not os.path.exists(symbols_file):
            return {}
        
        try:
            with open(symbols_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"  {Colors.WARNING}警告: 读取符号表失败 {symbols_file}: {e}{Colors.ENDC}")
            return {}
    
    def load_file_symbols(self, ibc_root_path: str, file_path: str) -> Dict[str, SymbolNode]:
        """加载指定文件的符号数据"""
        symbols_file = self.get_symbols_file_path(ibc_root_path, file_path)
        dir_symbols_table = self.load_dir_symbols_table(symbols_file)
        
        file_name = os.path.basename(file_path)
        file_symbol_data = dir_symbols_table.get(file_name, {})
        
        if not file_symbol_data:
            return {}
        
        # 从字典数据重建符号表
        symbol_table: Dict[str, SymbolNode] = {}
        for symbol_name, symbol_dict in file_symbol_data.items():
            symbol_node = SymbolNode.from_dict(symbol_dict)
            symbol_table[symbol_name] = symbol_node
        return symbol_table
    
    def save_file_symbols(
        self, 
        ibc_root_path: str, 
        file_path: str, 
        file_symbol_table: Dict[str, SymbolNode]
    ) -> bool:
        """保存文件的符号数据到对应目录的symbols.json"""
        symbols_file = self.get_symbols_file_path(ibc_root_path, file_path)
        dir_symbols_table = self.load_dir_symbols_table(symbols_file)
        
        file_name = os.path.basename(file_path)
        # 将符号表转换为字典格式
        symbols_dict = {}
        for symbol_name, symbol in file_symbol_table.items():
            symbols_dict[symbol_name] = symbol.to_dict()
        dir_symbols_table[file_name] = symbols_dict
        
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
        visibility: VisibilityTypes
    ) -> bool:
        """更新符号的规范化信息"""
        file_symbol_table = self.load_file_symbols(ibc_root_path, file_path)
        
        symbol = file_symbol_table.get(symbol_name)
        if not symbol:
            print(f"  {Colors.WARNING}警告: 找不到符号 {symbol_name}{Colors.ENDC}")
            return False
        
        symbol.update_normalized_info(normalized_name, visibility)
        return self.save_file_symbols(ibc_root_path, file_path, file_symbol_table)


# 单例实例
_instance = IbcDataStore()


def get_instance() -> IbcDataStore:
    """获取IbcDataManager单例实例"""
    return _instance
