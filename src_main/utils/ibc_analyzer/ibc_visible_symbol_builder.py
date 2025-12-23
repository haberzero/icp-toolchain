"""
IBC可见符号表构建器

负责构建当前文件的可见符号表。
基于dependent_relation中定义的依赖关系，从依赖文件中提取public符号，
结合proj_root_dict构建成树状结构。
"""
import os
import json
from typing import Dict, List, Any, Optional, Set, Tuple
from libs.dir_json_funcs import DirJsonFuncs
from typedef.ibc_data_types import SymbolNode, VisibilityTypes


class VisibleSymbolBuilder:
    """
    可见符号表构建器
    
    职责：
    1. 根据dependent_relation确定当前文件可见的依赖文件列表
    2. 从这些依赖文件中加载符号表
    3. 过滤掉private符号，只保留对外可见的符号
    4. 结合proj_root_dict的结构，构建树状的可见符号表
    """
    
    def __init__(self, proj_root_dict: Dict, dependent_relation: Dict[str, List[str]]):
        """
        初始化可见符号表构建器
        
        Args:
            proj_root_dict: 项目根目录字典，描述文件/文件夹结构
            dependent_relation: 依赖关系字典，格式为 {文件路径: [依赖文件列表]}
        """
        self.proj_root_dict = proj_root_dict
        self.dependent_relation = dependent_relation
        
        print(f"初始化可见符号表构建器")
        print(f"  项目文件总数: {len(DirJsonFuncs.get_all_file_paths(proj_root_dict))}")
        print(f"  依赖关系条目: {len(dependent_relation)}")
    
    def build_visible_symbol_tree(
        self, 
        current_file_path: str, 
        work_ibc_dir_path: str
    ) -> Tuple[Dict[str, Any], Dict[str, Dict[str, Any]]]:
        """
        构建当前文件的可见符号树
        
        处理流程：
        1. 从dependent_relation获取当前文件的依赖列表
        2. 对每个依赖文件，加载其符号表
        3. 过滤private符号
        4. 将符号组织成树状结构，元数据单独存储
        
        Args:
            current_file_path: 当前正在处理的文件路径（relative path）
            work_ibc_dir_path: IBC文件根目录的绝对路径
            
        Returns:
            Tuple[Dict[str, Any], Dict[str, Dict[str, Any]]]:
                - symbols_tree: 纯树状结构，所有节点都是{}
                - symbols_metadata: 符号元数据字典，使用点分隔的路径作为键
        
        注：详细的数据结构示例请参考测试脚本 test_symbol_builder_workflow.py
        """
        print(f"开始构建可见符号树: {current_file_path}")
        
        # 获取当前文件的依赖列表
        dependencies = self.dependent_relation.get(current_file_path, [])
        if not dependencies:
            print(f"  当前文件无依赖，返回空符号树")
            return {}, {}
        
        print(f"  依赖文件数: {len(dependencies)}")
        
        # 构建可见符号树和元数据
        symbols_tree = {}
        symbols_metadata = {}
        
        for dep_file_path in dependencies:
            print(f"  处理依赖: {dep_file_path}")
            
            # 加载依赖文件的符号表
            dep_symbols = self._load_dependency_symbols(dep_file_path, work_ibc_dir_path)
            if not dep_symbols:
                print(f"    警告: 无法加载符号表或符号表为空")
                continue
            
            # 过滤private符号
            public_symbols = self._filter_public_symbols(dep_symbols)
            print(f"    可见符号数: {len(public_symbols)} / {len(dep_symbols)}")
            
            if not public_symbols:
                continue
            
            # 将符号插入到树中
            self._insert_symbols_into_tree(symbols_tree, symbols_metadata, dep_file_path, public_symbols)
        
        print(f"  可见符号树构建完成")
        return symbols_tree, symbols_metadata
    
    def _load_dependency_symbols(
        self, 
        file_path: str, 
        work_ibc_dir_path: str
    ) -> Dict[str, SymbolNode]:
        """
        加载依赖文件的符号表
        
        Args:
            file_path: 依赖文件路径（相对路径）
            work_ibc_dir_path: IBC文件根目录的绝对路径
            
        Returns:
            Dict[str, SymbolNode]: 符号表字典
        """
        try:
            from data_store.ibc_data_store import get_instance as get_ibc_data_store
            
            ibc_data_store = get_ibc_data_store()
            symbols_path = ibc_data_store.build_symbols_path(work_ibc_dir_path, file_path)
            
            # 检查文件是否存在
            if not os.path.exists(symbols_path):
                print(f"    符号表文件不存在: {symbols_path}")
                return {}
            
            file_name = os.path.basename(file_path)
            symbol_table = ibc_data_store.load_symbols(symbols_path, file_name)
            
            return symbol_table
            
        except Exception as e:
            print(f"    加载符号表失败: {e}")
            return {}
    
    def _filter_public_symbols(
        self, 
        symbol_table: Dict[str, SymbolNode]
    ) -> Dict[str, SymbolNode]:
        """
        过滤出对外可见的符号（排除private）
        
        Args:
            symbol_table: 完整符号表
            
        Returns:
            Dict[str, SymbolNode]: 只包含public/protected符号的字典
        """
        public_symbols = {}
        
        for symbol_name, symbol in symbol_table.items():
            # 只保留非private的符号
            if symbol.visibility != VisibilityTypes.PRIVATE:
                public_symbols[symbol_name] = symbol
        
        return public_symbols
    
    def _insert_symbols_into_tree(
        self, 
        tree: Dict[str, Any],
        metadata: Dict[str, Dict[str, Any]],
        file_path: str, 
        symbols: Dict[str, SymbolNode]
    ) -> None:
        """
        将符号插入到树状结构中，元数据单独存储
        
        文件路径会被解析为目录层级，符号会挂载到文件节点下。
        
        Args:
            tree: 要插入的树（会被修改）
            metadata: 元数据字典（会被修改）
            file_path: 文件路径，如 "src/ball/ball_entity"
            symbols: 该文件的符号字典
        """
        # 解析文件路径
        path_parts = file_path.split('/')
        
        # 构建路径并记录元数据
        current_node = tree
        current_path_parts = []
        
        # 处理目录部分
        for part in path_parts[:-1]:
            current_path_parts.append(part)
            path_key = '.'.join(current_path_parts)
            
            if part not in current_node:
                current_node[part] = {}
                # 添加文件夹元数据
                metadata[path_key] = {"type": "folder"}
            
            current_node = current_node[part]
        
        # 处理文件节点
        file_name = path_parts[-1]
        current_path_parts.append(file_name)
        file_path_key = '.'.join(current_path_parts)
        
        if file_name not in current_node:
            current_node[file_name] = {}
        
        file_node = current_node[file_name]
        
        # 添加文件元数据
        file_desc = self._get_file_description(file_path)
        file_metadata = {"type": "file"}
        if file_desc:
            file_metadata["description"] = file_desc
        metadata[file_path_key] = file_metadata
        
        # 构建符号的层次结构
        # 先找出所有顶层符号（没有父符号的）
        top_level_symbols = [
            (name, symbol) for name, symbol in symbols.items()
            if not symbol.parent_symbol_name
        ]
        
        # 递归插入符号
        for symbol_name, symbol in top_level_symbols:
            self._insert_symbol_recursive(file_node, metadata, file_path_key, symbol_name, symbol, symbols)
    
    def _insert_symbol_recursive(
        self, 
        parent_node: Dict[str, Any],
        metadata: Dict[str, Dict[str, Any]],
        parent_path: str,
        symbol_name: str, 
        symbol: SymbolNode,
        all_symbols: Dict[str, SymbolNode]
    ) -> None:
        """
        递归插入符号及其子符号
        
        Args:
            parent_node: 父节点（字典）
            metadata: 元数据字典
            parent_path: 父节点路径
            symbol_name: 当前符号名
            symbol: 当前符号对象
            all_symbols: 完整符号表（用于查找子符号）
        """
        # 创建符号节点（空字典）
        symbol_node = {}
        
        # 构建符号路径
        symbol_path = f"{parent_path}.{symbol_name}"
        
        # 添加符号元数据
        symbol_metadata = {
            "type": symbol.symbol_type.value,
            "visibility": symbol.visibility.value
        }
        
        if symbol.description:
            symbol_metadata["description"] = symbol.description
        
        if symbol.normalized_name:
            symbol_metadata["normalized_name"] = symbol.normalized_name
        
        # 如果是函数，添加参数信息
        if symbol.parameters:
            symbol_metadata["parameters"] = symbol.parameters
        
        metadata[symbol_path] = symbol_metadata
        
        # 递归处理子符号
        for child_name in symbol.children_symbol_names:
            if child_name in all_symbols:
                child_symbol = all_symbols[child_name]
                self._insert_symbol_recursive(symbol_node, metadata, symbol_path, child_name, child_symbol, all_symbols)
        
        # 将符号节点插入父节点
        parent_node[symbol_name] = symbol_node
    
    def _get_file_description(self, file_path: str) -> str:
        """
        从proj_root_dict获取文件描述
        
        Args:
            file_path: 文件路径，如 "src/ball/ball_entity"
            
        Returns:
            str: 文件描述，如果找不到返回空字符串
        """
        path_parts = file_path.split('/')
        
        current_node = self.proj_root_dict
        for part in path_parts:
            if isinstance(current_node, dict) and part in current_node:
                current_node = current_node[part]
            else:
                return ""
        
        # 如果最终节点是字符串，那就是描述
        if isinstance(current_node, str):
            return current_node
        
        return ""
    

