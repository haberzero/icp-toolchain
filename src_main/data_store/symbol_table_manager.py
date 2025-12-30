"""符号表管理器 - 专门处理符号树和符号元数据的存储与加载"""
import json
import os
from typing import Dict, Any, List, Tuple
from typedef.ibc_data_types import SymbolMetadata, create_symbol_metadata


class SymbolTableManager:
    """符号表管理器
    
    职责：
    - 符号树和符号元数据的保存与加载
    - 目录级符号表的统一管理
    - 依赖符号表的批量加载
    - 符号规范化信息的更新
    
    所有方法均为静态方法，可独立使用。
    
    说明：
    符号表采用目录级存储，一个symbols.json包含该目录下所有文件的符号信息。
    存储结构示例：
    {
        "ball_entity": {
            "symbols_tree": {...},
            "symbols_metadata": {...}
        },
        "heptagon_shape": {
            "symbols_tree": {...},
            "symbols_metadata": {...}
        }
    }
    """
    
    @staticmethod
    def build_symbols_path(ibc_root: str, file_path: str) -> str:
        """构建符号表路径（目录级）: ibc_root/dir/symbols.json
        
        Args:
            ibc_root: IBC文件根目录
            file_path: 文件相对路径
            
        Returns:
            str: 目录级符号表文件路径
        """
        file_dir = os.path.dirname(file_path)
        if file_dir:
            symbols_dir = os.path.join(ibc_root, file_dir)
        else:
            symbols_dir = ibc_root
        return os.path.join(symbols_dir, 'symbols.json')
    
    @staticmethod
    def save_symbols(
        symbols_path: str,
        file_name: str,
        symbols_tree: Dict[str, Any],
        symbols_metadata: Dict[str, SymbolMetadata],
    ) -> None:
        """保存符号信息（目录级存储，自动合并）
        
        Args:
            symbols_path: 目录级符号表文件路径
            file_name: 文件名（不含扩展名）
            symbols_tree: 符号树
            symbols_metadata: 符号元数据字典
            
        Raises:
            IOError: 保存失败时抛出
        """
        # 加载目录级符号数据
        dir_symbols = SymbolTableManager._load_dir_symbols(symbols_path)
        
        # 将SymbolMetadata对象转换为字典以便JSON序列化
        symbols_metadata_dict = {path: meta.to_dict() for path, meta in symbols_metadata.items()}
            
        dir_symbols[file_name] = {
            "symbols_tree": symbols_tree,
            "symbols_metadata": symbols_metadata_dict,
        }
            
        # 保存回文件
        try:
            os.makedirs(os.path.dirname(symbols_path), exist_ok=True)
            with open(symbols_path, 'w', encoding='utf-8') as f:
                json.dump(dir_symbols, f, ensure_ascii=False, indent=2)
        except Exception as e:
            raise IOError(f"保存符号表失败 [{symbols_path}]: {e}") from e
    
    @staticmethod
    def load_symbols(symbols_path: str, file_name: str) -> Tuple[Dict[str, Any], Dict[str, SymbolMetadata]]:
        """加载单个文件的符号树和元数据，文件不存在或无数据时返回空结构
        
        Args:
            symbols_path: 目录级符号表文件路径
            file_name: 文件名（不含扩展名）
            
        Returns:
            Tuple[Dict, Dict]: (符号树, 符号元数据字典)，不存在时返回({}, {})
        """
        dir_symbols = SymbolTableManager._load_dir_symbols(symbols_path)
        file_symbol_data = dir_symbols.get(file_name, {})
            
        if not file_symbol_data:
            return {}, {}
            
        symbols_tree = file_symbol_data.get("symbols_tree", {})
        symbols_metadata_dict = file_symbol_data.get("symbols_metadata", {})
        
        # 将字典转换为SymbolMetadata对象
        symbols_metadata: Dict[str, SymbolMetadata] = {}
        for path, meta_dict in symbols_metadata_dict.items():
            try:
                symbols_metadata[path] = create_symbol_metadata(meta_dict)
            except ValueError as e:
                # 如果无法识别符号类型，跳过该符号
                print(f"警告: 无法加载符号 {path}: {e}")
                continue

        return symbols_tree, symbols_metadata
    
    @staticmethod
    def load_dependency_symbol_tables(
        ibc_root: str,
        dependent_relation: Dict[str, List[str]],
        current_file_path: str
    ) -> Dict[str, Tuple[Dict[str, Any], Dict[str, SymbolMetadata]]]:
        """根据依赖关系为单个文件批量加载依赖符号数据
        
        Args:
            ibc_root: IBC文件根目录
            dependent_relation: 依赖关系字典 {文件路径: [依赖文件路径列表]}
            current_file_path: 当前文件路径
            
        Returns:
            Dict[str, Tuple]: {依赖文件路径: (符号树, 符号元数据)} 的映射
        """
        dependencies = dependent_relation.get(current_file_path, [])
        if not dependencies:
            return {}
    
        result: Dict[str, Tuple[Dict[str, Any], Dict[str, SymbolMetadata]]] = {}
    
        for dep_file_path in dependencies:
            symbols_path = SymbolTableManager.build_symbols_path(ibc_root, dep_file_path)
            if not os.path.exists(symbols_path):
                continue
    
            file_name = os.path.basename(dep_file_path)
            symbols_tree, symbols_metadata = SymbolTableManager.load_symbols(symbols_path, file_name)
    
            if not symbols_tree and not symbols_metadata:
                continue
    
            result[dep_file_path] = (symbols_tree, symbols_metadata)
    
        return result
    
    @staticmethod
    def is_dependency_symbol_tables_valid(
        ibc_root: str,
        dependent_relation: Dict[str, List[str]],
        current_file_path: str
    ) -> bool:
        """检查当前文件的依赖符号数据是否都存在且有内容
        
        Args:
            ibc_root: IBC文件根目录
            dependent_relation: 依赖关系字典
            current_file_path: 当前文件路径
            
        Returns:
            bool: 所有依赖的符号表都存在且有内容返回True，否则返回False
            
        说明：
            - 不进行任何print，仅通过返回值告知调用方是否可以继续后续动作
            - 检查规则：
              * 如果不存在依赖，则认为无需依赖其它文件的符号，返回 True
              * 如果任一依赖文件的符号表文件不存在或无内容，则返回 False
              * 仅当所有依赖的符号表文件都存在且有内容时返回 True
        """
        dependencies = dependent_relation.get(current_file_path, [])
        if not dependencies:
            return True
    
        for dep_file_path in dependencies:
            symbols_path = SymbolTableManager.build_symbols_path(ibc_root, dep_file_path)
            if not os.path.exists(symbols_path):
                return False
    
            file_name = os.path.basename(dep_file_path)
            dir_symbols = SymbolTableManager._load_dir_symbols(symbols_path)
            file_symbol_data = dir_symbols.get(file_name, {})
            if not file_symbol_data:
                return False
    
        return True
    
    @staticmethod
    def update_symbol_info(
        symbols_path: str,
        file_name: str,
        symbol_path: str,
        normalized_name: str
    ) -> None:
        """更新单个符号的规范化信息
        
        该方法封装了加载→更新→保存的完整流程，适用于单个符号的更新场景。
        对于批量更新，建议使用 update_symbols_batch 方法。
            
        Args:
            symbols_path: 目录级符号文件路径
            file_name: 文件名（不含扩展名）
            symbol_path: 符号在文件内部的点分隔路径（例如 "ClassName.methodName"）
            normalized_name: 规范化后的名称
            
        Raises:
            ValueError: 符号数据不存在或符号路径无效
        """
        from libs.ibc_funcs import IbcFuncs
        
        # 加载符号数据
        symbols_tree, symbols_metadata = SymbolTableManager.load_symbols(symbols_path, file_name)
        if not symbols_metadata:
            raise ValueError(f"符号数据不存在，文件: {file_name}")
            
        if symbol_path not in symbols_metadata:
            raise ValueError(f"符号不存在: {symbol_path}，文件: {file_name}")
        
        # 使用 IbcFuncs 统一的更新方法
        normalized_mapping = {symbol_path: normalized_name}
        updated_count = IbcFuncs.update_symbols_normalized_names(symbols_metadata, normalized_mapping)
        
        if updated_count == 0:
            raise ValueError(f"符号更新失败: {symbol_path}，可能不是有效的符号类型")
            
        # 保存更新后的符号数据
        SymbolTableManager.save_symbols(symbols_path, file_name, symbols_tree, symbols_metadata)
    
    @staticmethod
    def update_symbols_batch(
        symbols_path: str,
        file_name: str,
        normalized_mapping: Dict[str, str]
    ) -> int:
        """批量更新符号的规范化信息
        
        该方法封装了加载→批量更新→保存的完整流程，适用于批量更新场景。
        相比直接调用 IbcFuncs.update_symbols_normalized_names + save_symbols，
        该方法更简洁，适合不需要自己管理符号树的场景。
        
        Args:
            symbols_path: 目录级符号文件路径
            file_name: 文件名（不含扩展名）
            normalized_mapping: 规范化映射 {符号路径: 规范化名称}
            
        Returns:
            int: 成功更新的符号数量
            
        Example:
            >>> normalized_mapping = {
            ...     "file.MyClass": "NormalizedClass",
            ...     "file.my_func": "normalized_func"
            ... }
            >>> count = SymbolTableManager.update_symbols_batch(
            ...     symbols_path="path/to/symbols.json",
            ...     file_name="file",
            ...     normalized_mapping=normalized_mapping
            ... )
            >>> print(f"更新了 {count} 个符号")
        """
        from libs.ibc_funcs import IbcFuncs
        
        # 加载符号数据
        symbols_tree, symbols_metadata = SymbolTableManager.load_symbols(symbols_path, file_name)
        if not symbols_metadata:
            return 0
        
        # 使用 IbcFuncs 工具方法批量更新
        updated_count = IbcFuncs.update_symbols_normalized_names(symbols_metadata, normalized_mapping)
        
        if updated_count > 0:
            # 保存更新后的符号数据
            SymbolTableManager.save_symbols(symbols_path, file_name, symbols_tree, symbols_metadata)
        
        return updated_count
    
    @staticmethod
    def _load_dir_symbols(symbols_path: str) -> Dict[str, Any]:
        """内部方法：加载目录级符号表，文件不存在时返回空字典
        
        Args:
            symbols_path: 目录级符号表文件路径
            
        Returns:
            Dict[str, Any]: 目录级符号表数据，文件不存在时返回空字典
            
        Raises:
            IOError: 读取失败时抛出
        """
        if not os.path.exists(symbols_path):
            return {}
        
        try:
            with open(symbols_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            raise IOError(f"读取符号表失败 [{symbols_path}]: {e}") from e
