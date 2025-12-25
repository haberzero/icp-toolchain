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


class VisibleSymbolBuilder:
    """可见符号表构建器（基于符号树+元数据）
    
    新设计说明：
    - 不再依赖 SymbolNode/平铺符号表
    - 输入为依赖文件级别的 (symbols_tree, symbols_metadata)
    - 输出保持不变：合并后的可见符号树 symbols_tree 和 symbols_metadata
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
        dependency_symbol_tables: Dict[str, Tuple[Dict[str, Any], Dict[str, Dict[str, Any]]]]
    ) -> Tuple[Dict[str, Any], Dict[str, Dict[str, Any]]]:
        """构建当前文件的可见符号树
        
        Args:
            current_file_path: 当前正在处理的文件路径（relative path，仅用于日志输出）
            dependency_symbol_tables: 依赖文件路径到 (symbols_tree, symbols_metadata) 的映射
                - symbols_tree: 单文件内部的符号树
                - symbols_metadata: 单文件内部的符号元数据
        """
        print(f"开始构建可见符号树: {current_file_path}")
        
        if not dependency_symbol_tables:
            print(f"  当前文件无可用依赖符号，返回空符号树")
            return {}, {}
        
        print(f"  依赖文件数: {len(dependency_symbol_tables)}")
        
        # 合并后的可见符号树和元数据
        symbols_tree: Dict[str, Any] = {}
        symbols_metadata: Dict[str, Dict[str, Any]] = {}
        
        for dep_file_path, (file_symbols_tree, file_symbols_metadata) in dependency_symbol_tables.items():
            print(f"  处理依赖: {dep_file_path}")
            
            if not file_symbols_tree and not file_symbols_metadata:
                print(f"    警告: 依赖符号数据为空")
                continue
            
            # 将单文件符号树插入到整体树中（保持与原有目录结构一致）
            self._insert_file_symbols_into_tree(
                tree=symbols_tree,
                metadata=symbols_metadata,
                file_path=dep_file_path,
                file_symbols_tree=file_symbols_tree,
                file_symbols_metadata=file_symbols_metadata,
            )
        
        print(f"  可见符号树构建完成")
        return symbols_tree, symbols_metadata
    
    
    def _insert_file_symbols_into_tree(
        self,
        tree: Dict[str, Any],
        metadata: Dict[str, Dict[str, Any]],
        file_path: str,
        file_symbols_tree: Dict[str, Any],
        file_symbols_metadata: Dict[str, Dict[str, Any]],
    ) -> None:
        """将单个文件的符号树和元数据插入到总符号树中
            
        - 目录结构仍然根据 file_path 来创建
        - 文件节点下挂载该文件的符号树
        - 元数据的 key 由 "dir.dir.file" + 文件内符号路径 拼接而成
        """
        # 解析文件路径
        path_parts = file_path.split('/')
            
        # 构建目录节点
        current_node = tree
        current_path_parts: List[str] = []
        for part in path_parts[:-1]:
            current_path_parts.append(part)
            path_key = '.'.join(current_path_parts)
            if part not in current_node:
                current_node[part] = {}
                metadata[path_key] = {"type": "folder"}
            current_node = current_node[part]
            
        # 文件节点
        file_name = path_parts[-1]
        current_path_parts.append(file_name)
        file_path_key = '.'.join(current_path_parts)
            
        if file_name not in current_node:
            current_node[file_name] = {}
        file_node = current_node[file_name]
            
        # 文件元数据
        file_desc = self._get_file_description(file_path)
        file_metadata = {"type": "file"}
        if file_desc:
            file_metadata["description"] = file_desc
        metadata[file_path_key] = file_metadata
            
        # 将文件内部的符号树挂载到 file_node 下
        # 这里直接拷贝结构，避免修改原始树
        for symbol_name, symbol_subtree in file_symbols_tree.items():
            file_node[symbol_name] = self._deep_copy_tree(symbol_subtree)
            
        # 整合文件内部的符号元数据到全局 metadata
        # 文件内部的 key 是相对路径，例如 "ClassName.method"
        for relative_path, meta in file_symbols_metadata.items():
            full_path = f"{file_path_key}.{relative_path}" if relative_path else file_path_key
            # 过滤掉 private 符号，仅保留非 private 的符号元数据
            visibility = meta.get("visibility", "public")
            scope = meta.get("scope", "")
            if visibility == "private" or scope == "local":
                continue
            metadata[full_path] = meta
        
    @staticmethod
    def _deep_copy_tree(tree: Dict[str, Any]) -> Dict[str, Any]:
        """对符号树进行浅层递归复制，避免修改源结构"""
        new_tree: Dict[str, Any] = {}
        for key, value in tree.items():
            if isinstance(value, dict):
                new_tree[key] = VisibleSymbolBuilder._deep_copy_tree(value)
            else:
                new_tree[key] = value
        return new_tree
    
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
    

