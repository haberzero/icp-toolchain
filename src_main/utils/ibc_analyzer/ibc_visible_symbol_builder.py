"""
IBC可见符号表构建器

负责构建当前文件的可见符号树。
调用方根据 dependent_relation 从依赖文件中加载符号表后传入本构建器，
本构建器负责按可见性过滤并结合proj_root_dict构建成树状结构。
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
    1. 基于调用方传入的依赖符号表，构建当前文件可见的符号树
    2. 过滤掉private符号，只保留对外可见的符号
    3. 结合proj_root_dict的结构，构建树状的可见符号表
    """
    
    def __init__(self, proj_root_dict: Dict):
        """初始化可见符号表构建器
        
        Args:
            proj_root_dict: 项目根目录字典，描述文件/文件夹结构
        """
        self.proj_root_dict = proj_root_dict
        
        print(f"初始化可见符号表构建器")
        print(f"  项目文件总数: {len(DirJsonFuncs.get_all_file_paths(proj_root_dict))}")
    
    def build_visible_symbol_tree(
        self, 
        current_file_path: str,
        dependency_symbol_tables: Dict[str, Dict[str, SymbolNode]]
    ) -> Tuple[Dict[str, Any], Dict[str, Dict[str, Any]]]:
        """构建当前文件的可见符号树
        
        处理流程：
        1. 调用方根据 dependent_relation 从 IBC 目录加载依赖符号表
        2. 本方法对符号表进行可见性过滤
        3. 将符号组织成树状结构，元数据单独存储
        
        Args:
            current_file_path: 当前正在处理的文件路径（relative path，仅用于日志输出）
            dependency_symbol_tables: 依赖文件路径到符号表的映射
            
        Returns:
            Tuple[Dict[str, Any], Dict[str, Dict[str, Any]]]:
                - symbols_tree: 纯树状结构，所有节点都是{}
                - symbols_metadata: 符号元数据字典，使用点分隔的路径作为键
        
        注：详细的数据结构示例请参考测试脚本 test_symbol_builder_workflow.py
        """
        print(f"开始构建可见符号树: {current_file_path}")
        
        if not dependency_symbol_tables:
            print(f"  当前文件无可用依赖符号，返回空符号树")
            return {}, {}
        
        print(f"  依赖文件数: {len(dependency_symbol_tables)}")
        
        # 构建可见符号树和元数据
        symbols_tree: Dict[str, Any] = {}
        symbols_metadata: Dict[str, Dict[str, Any]] = {}
        
        for dep_file_path, dep_symbols in dependency_symbol_tables.items():
            print(f"  处理依赖: {dep_file_path}")
            
            if not dep_symbols:
                print(f"    警告: 依赖符号表为空")
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
    
    
    def _filter_public_symbols(
        self, 
        symbol_table: Dict[str, SymbolNode]
    ) -> Dict[str, SymbolNode]:
        """过滤出对外可见的符号（排除private）
        
        Args:
            symbol_table: 完整符号表
            
        Returns:
            Dict[str, SymbolNode]: 只包含public/protected符号的字典
        """
        public_symbols: Dict[str, SymbolNode] = {}
        
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
        """将符号插入到树状结构中，元数据单独存储
        
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
        """从proj_root_dict获取文件描述
        
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
    

