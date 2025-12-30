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
from typedef.ibc_data_types import (
    SymbolMetadata, FolderMetadata, FileMetadata, ClassMetadata, 
    FunctionMetadata, VariableMetadata
)


class VisibleSymbolBuilder:
    """可见符号表构建器（基于符号树+元数据）"""
    
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
        dependency_symbol_tables: Dict[str, Tuple[Dict[str, Any], Dict[str, SymbolMetadata]]],
        include_local_symbols: bool = False,
        local_symbols_tree: Optional[Dict[str, Any]] = None,
        local_symbols_metadata: Optional[Dict[str, SymbolMetadata]] = None
    ) -> Tuple[Dict[str, Any], Dict[str, SymbolMetadata]]:
        """构建当前文件的可见符号树
        
        Args:
            current_file_path: 当前正在处理的文件路径（relative path，仅用于日志输出）
            dependency_symbol_tables: 依赖文件路径到 (symbols_tree, symbols_metadata) 的映射
                - symbols_tree: 单文件内部的符号树
                - symbols_metadata: 单文件内部的符号元数据
            include_local_symbols: 是否包含当前文件自己的符号（用于符号引用验证）
            local_symbols_tree: 当前文件自己的符号树
            local_symbols_metadata: 当前文件自己的符号元数据
        """
        print(f"开始构建可见符号树: {current_file_path}")
        
        # 合并后的可见符号树和元数据
        symbols_tree: Dict[str, Any] = {}
        symbols_metadata: Dict[str, SymbolMetadata] = {}
        
        if not dependency_symbol_tables:
            print(f"  当前文件无可用依赖符号")
        else:
            print(f"  依赖文件数: {len(dependency_symbol_tables)}")
        
        if dependency_symbol_tables:
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
        
        # 如果需要包含本地符号，则将本地符号合并到可见符号树中
        if include_local_symbols and local_symbols_tree and local_symbols_metadata:
            print(f"  正在合并本地符号到可见符号树...")
            self._merge_local_symbols(
                symbols_tree=symbols_tree,
                symbols_metadata=symbols_metadata,
                local_symbols_tree=local_symbols_tree,
                local_symbols_metadata=local_symbols_metadata,
                current_file_path=current_file_path
            )
        
        print(f"  可见符号树构建完成")
        return symbols_tree, symbols_metadata
    
    
    def _insert_file_symbols_into_tree(
        self,
        tree: Dict[str, Any],
        metadata: Dict[str, SymbolMetadata],
        file_path: str,
        file_symbols_tree: Dict[str, Any],
        file_symbols_metadata: Dict[str, SymbolMetadata],
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
                metadata[path_key] = FolderMetadata(type="folder")
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
        file_metadata = FileMetadata(type="file", description=file_desc)
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
            if isinstance(meta, (ClassMetadata, FunctionMetadata, VariableMetadata)):
                if meta.visibility == "private" or (isinstance(meta, VariableMetadata) and meta.scope == "local"):
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
    
    def _merge_local_symbols(
        self,
        symbols_tree: Dict[str, Any],
        symbols_metadata: Dict[str, SymbolMetadata],
        local_symbols_tree: Dict[str, Any],
        local_symbols_metadata: Dict[str, SymbolMetadata],
        current_file_path: str
    ) -> None:
        """将当前文件的本地符号合并到可见符号树中
        
        Args:
            symbols_tree: 总符号树（会被原地修改）
            symbols_metadata: 总符号元数据（会被原地修改）
            local_symbols_tree: 当前文件的符号树
            local_symbols_metadata: 当前文件的符号元数据
            current_file_path: 当前文件路径
        
        注意：
            - 本地符号直接挂载到根节点，不需要文件路径前缀
            - 本地符号包含所有可见性（private/local也包含）
            - 元数据中会添加特殊标记 '__is_local__': True，用于优先级判断
        """
        print(f"    开始合并本地符号...")
        
        # 统计本地符号数量
        local_symbol_count = 0
        
        # 直接将本地符号树合并到根节点
        for symbol_name, symbol_subtree in local_symbols_tree.items():
            if symbol_name in symbols_tree:
                print(f"      警告: 本地符号 '{symbol_name}' 与依赖符号重名，本地符号优先")
            symbols_tree[symbol_name] = self._deep_copy_tree(symbol_subtree)
            local_symbol_count += 1
        
        # 合并本地符号元数据
        # 本地符号的元数据key不带文件路径前缀，直接使用相对路径
        for relative_path, meta in local_symbols_metadata.items():
            # 添加特殊标记表示这是本地符号
            if isinstance(meta, (ClassMetadata, FunctionMetadata, VariableMetadata)):
                # 修改本地符号的标记
                if isinstance(meta, ClassMetadata):
                    meta = ClassMetadata(
                        type=meta.type,
                        description=meta.description,
                        visibility=meta.visibility,
                        normalized_name=meta.normalized_name,
                        __is_local__=True,
                        __local_file__=current_file_path
                    )
                elif isinstance(meta, FunctionMetadata):
                    meta = FunctionMetadata(
                        type=meta.type,
                        description=meta.description,
                        visibility=meta.visibility,
                        parameters=meta.parameters,
                        normalized_name=meta.normalized_name,
                        __is_local__=True,
                        __local_file__=current_file_path
                    )
                elif isinstance(meta, VariableMetadata):
                    meta = VariableMetadata(
                        type=meta.type,
                        description=meta.description,
                        visibility=meta.visibility,
                        scope=meta.scope,
                        normalized_name=meta.normalized_name,
                        __is_local__=True,
                        __local_file__=current_file_path
                    )
            
            # 检查是否与依赖符号重名
            if relative_path in symbols_metadata:
                print(f"      警告: 本地符号元数据 '{relative_path}' 与依赖符号重名，本地符号优先")
            
            symbols_metadata[relative_path] = meta
            local_symbol_count += 1
        
        print(f"    本地符号合并完成，共合并 {local_symbol_count} 个符号")
    
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
    

