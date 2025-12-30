"""符号元数据处理辅助类

负责处理符号元数据的更新、验证、统计等操作
从ibc_funcs.py中提取的符号元数据相关功能
"""
import json
import hashlib
from typing import Dict, List, Any, Optional
from typedef.ibc_data_types import (
    SymbolMetadata, ClassMetadata, FunctionMetadata, VariableMetadata,
    FolderMetadata, FileMetadata
)


class SymbolMetadataHelper:
    """符号元数据处理辅助类
    
    提供符号元数据的更新、查询、统计和校验功能
    """
    
    @staticmethod
    def calculate_metadata_md5(symbols_metadata: Dict[str, SymbolMetadata]) -> str:
        """计算符号元数据的MD5校验值
        
        Args:
            symbols_metadata: 符号元数据字典
            
        Returns:
            str: MD5校验值
        """
        try:
            # 将SymbolMetadata对象转换为字典，然后转换为JSON字符串(排序键以确保一致性)
            metadata_dict = {path: meta.to_dict() for path, meta in symbols_metadata.items()}
            metadata_json = json.dumps(metadata_dict, sort_keys=True, ensure_ascii=False)
            
            text_hash = hashlib.md5()
            text_hash.update(metadata_json.encode('utf-8'))
            return text_hash.hexdigest()
        except Exception as e:
            raise RuntimeError(f"计算符号元数据MD5时发生错误: {e}") from e
    
    @staticmethod
    def count_symbols(symbols_metadata: Dict[str, SymbolMetadata]) -> int:
        """统计符号元数据中的符号数量(排除文件夹和文件节点)
        
        Args:
            symbols_metadata: 符号元数据字典
            
        Returns:
            int: 符号数量
        """
        count = 0
        for meta in symbols_metadata.values():
            # 只统计实际符号(class, func, var),不统计folder和file
            if isinstance(meta, (ClassMetadata, FunctionMetadata, VariableMetadata)):
                count += 1
        return count
    
    @staticmethod
    def get_normalized_name(
        symbol_path: str,
        symbols_metadata: Dict[str, SymbolMetadata]
    ) -> Optional[str]:
        """从symbols_metadata中获取规范化名称
        
        Args:
            symbol_path: 符号完整路径
            symbols_metadata: 符号元数据
            
        Returns:
            Optional[str]: 规范化名称，如果不存在则返回None
        """
        if symbol_path in symbols_metadata:
            meta = symbols_metadata[symbol_path]
            if isinstance(meta, (ClassMetadata, FunctionMetadata, VariableMetadata)):
                return meta.normalized_name if meta.normalized_name else None
        return None
    
    @staticmethod
    def update_normalized_names(
        symbols_metadata: Dict[str, SymbolMetadata],
        normalized_mapping: Dict[str, str]
    ) -> int:
        """批量更新符号元数据中的 normalized_name
        
        这是一个通用的批量更新工具方法，用于更新符号的规范化名称。
        由于 dataclass 是不可变的，需要创建新实例来更新字段。
        
        Args:
            symbols_metadata: 符号元数据字典（会被原地修改）
            normalized_mapping: 规范化映射 {符号路径: 规范化名称}
            
        Returns:
            int: 成功更新的符号数量
            
        Example:
            >>> symbols_metadata = {"file.MyClass": ClassMetadata(...)}
            >>> normalized_mapping = {"file.MyClass": "MyNormalizedClass"}
            >>> count = SymbolMetadataHelper.update_normalized_names(symbols_metadata, normalized_mapping)
            >>> print(count)  # 1
        """
        updated_count = 0
        
        for symbol_key, normalized_name in normalized_mapping.items():
            # 按照完整路径精确匹配
            if symbol_key not in symbols_metadata:
                continue
                
            meta = symbols_metadata[symbol_key]
            
            # 只更新实际符号（ClassMetadata, FunctionMetadata, VariableMetadata）
            # 跳过 FolderMetadata 和 FileMetadata
            if isinstance(meta, ClassMetadata):
                symbols_metadata[symbol_key] = ClassMetadata(
                    type=meta.type,
                    description=meta.description,
                    visibility=meta.visibility,
                    normalized_name=normalized_name,
                    __is_local__=meta.__is_local__,
                    __local_file__=meta.__local_file__
                )
                updated_count += 1
            elif isinstance(meta, FunctionMetadata):
                symbols_metadata[symbol_key] = FunctionMetadata(
                    type=meta.type,
                    description=meta.description,
                    visibility=meta.visibility,
                    parameters=meta.parameters,
                    normalized_name=normalized_name,
                    __is_local__=meta.__is_local__,
                    __local_file__=meta.__local_file__
                )
                updated_count += 1
            elif isinstance(meta, VariableMetadata):
                symbols_metadata[symbol_key] = VariableMetadata(
                    type=meta.type,
                    description=meta.description,
                    visibility=meta.visibility,
                    scope=meta.scope,
                    normalized_name=normalized_name,
                    __is_local__=meta.__is_local__,
                    __local_file__=meta.__local_file__
                )
                updated_count += 1
        
        return updated_count
    
    @staticmethod
    def build_available_symbol_list(
        symbols_metadata: Dict[str, SymbolMetadata],
        proj_root_dict: Dict[str, Any]
    ) -> List[str]:
        """构建可用依赖符号列表
        
        从 symbols_metadata 中提取符号信息，并将完整路径简化为相对路径。
        
        Args:
            symbols_metadata: 符号元数据字典，键为完整的点分隔路径（如 src.ball.ball_entity.BallEntity）
            proj_root_dict: 项目根目录字典，用于确定文件名位置
            
        Returns:
            List[str]: 符号列表，每个元素格式为 "$filename.symbol ：功能描述"
            
        示例：
            输入: {"src.ball.ball_entity.BallEntity": {"type": "class", "description": "球体实体类"}}
            输出: ["$ball_entity.BallEntity ：球体实体类"]
        """
        from libs.symbol_path_helper import SymbolPathHelper
        
        available_symbol_lines = []
        
        for symbol_path, meta in symbols_metadata.items():
            # 跳过文件夹和文件节点，只处理具体符号
            if not isinstance(meta, (ClassMetadata, FunctionMetadata, VariableMetadata)):
                continue
            
            desc = meta.description
            if not desc:
                desc = "没有对外功能描述"
            
            # 简化符号路径
            simplified_path = SymbolPathHelper.simplify_symbol_path(symbol_path, proj_root_dict)
            available_symbol_lines.append(f"${simplified_path} ：{desc}")
        
        return available_symbol_lines
    
    @staticmethod
    def filter_symbols_by_type(
        symbols_metadata: Dict[str, SymbolMetadata],
        symbol_type: str
    ) -> Dict[str, SymbolMetadata]:
        """根据类型过滤符号
        
        Args:
            symbols_metadata: 符号元数据字典
            symbol_type: 符号类型 (class/func/var/folder/file)
            
        Returns:
            Dict[str, SymbolMetadata]: 过滤后的符号字典
        """
        filtered = {}
        for path, meta in symbols_metadata.items():
            if meta.type == symbol_type:
                filtered[path] = meta
        return filtered
    
    @staticmethod
    def filter_symbols_by_visibility(
        symbols_metadata: Dict[str, SymbolMetadata],
        visibility: str
    ) -> Dict[str, SymbolMetadata]:
        """根据可见性过滤符号
        
        Args:
            symbols_metadata: 符号元数据字典
            visibility: 可见性 (public/protected/private)
            
        Returns:
            Dict[str, SymbolMetadata]: 过滤后的符号字典
        """
        filtered = {}
        for path, meta in symbols_metadata.items():
            if isinstance(meta, (ClassMetadata, FunctionMetadata, VariableMetadata)):
                if meta.visibility == visibility:
                    filtered[path] = meta
        return filtered
