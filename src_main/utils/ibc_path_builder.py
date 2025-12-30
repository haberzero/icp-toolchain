"""IBC路径构建器

统一管理IBC相关文件的路径构建逻辑。

设计说明：
- 从 IbcDataStore 中提取路径构建方法
- 统一路径构建规则，便于维护
- 处理Windows和Linux路径分隔符差异
"""
import os
from typing import Optional


class IbcPathBuilder:
    """IBC路径构建器
    
    提供IBC相关文件路径的统一构建方法。
    """
    
    @staticmethod
    def build_ibc_path(ibc_root: str, file_path: str) -> str:
        """构建IBC文件路径
        
        格式：ibc_root/file_path.ibc
        
        Args:
            ibc_root: IBC根目录路径
            file_path: 文件相对路径（如 "src/ball/ball_entity"）
            
        Returns:
            str: IBC文件的完整路径
            
        Example:
            >>> path = IbcPathBuilder.build_ibc_path("/project/src_ibc", "src/ball/ball_entity")
            >>> # Windows: "\\project\\src_ibc\\src\\ball\\ball_entity.ibc"
            >>> # Linux: "/project/src_ibc/src/ball/ball_entity.ibc"
        """
        # 解决Windows和Linux路径分隔符问题
        normalized_file_path = file_path.replace('/', os.sep)
        return os.path.join(ibc_root, f"{normalized_file_path}.ibc")
    
    @staticmethod
    def build_ast_path(ibc_root: str, file_path: str) -> str:
        """构建AST文件路径
        
        格式：ibc_root/file_path_ibc_ast.json
        
        Args:
            ibc_root: IBC根目录路径
            file_path: 文件相对路径（如 "src/ball/ball_entity"）
            
        Returns:
            str: AST文件的完整路径
            
        Example:
            >>> path = IbcPathBuilder.build_ast_path("/project/src_ibc", "src/ball/ball_entity")
            >>> # Windows: "\\project\\src_ibc\\src\\ball\\ball_entity_ibc_ast.json"
            >>> # Linux: "/project/src_ibc/src/ball/ball_entity_ibc_ast.json"
        """
        # 解决Windows和Linux路径分隔符问题
        normalized_file_path = file_path.replace('/', os.sep)
        return os.path.join(ibc_root, f"{normalized_file_path}_ibc_ast.json")
    
    @staticmethod
    def build_symbols_path(ibc_root: str, file_path: str) -> str:
        """构建符号表路径（目录级）
        
        格式：ibc_root/dir/symbols.json
        
        注意：符号表采用目录级存储，一个symbols.json包含该目录下所有文件的符号。
        
        Args:
            ibc_root: IBC根目录路径
            file_path: 文件相对路径（如 "src/ball/ball_entity"）
            
        Returns:
            str: 符号表文件的完整路径
            
        Example:
            >>> path = IbcPathBuilder.build_symbols_path("/project/src_ibc", "src/ball/ball_entity")
            >>> # Windows: "\\project\\src_ibc\\src\\ball\\symbols.json"
            >>> # Linux: "/project/src_ibc/src/ball/symbols.json"
        """
        file_dir = os.path.dirname(file_path)
        if file_dir:
            symbols_dir = os.path.join(ibc_root, file_dir)
        else:
            symbols_dir = ibc_root
        return os.path.join(symbols_dir, 'symbols.json')
    
    @staticmethod
    def build_target_code_path(
        target_root: str,
        file_path: str,
        file_extension: str = '.py'
    ) -> str:
        """构建目标代码文件路径
        
        Args:
            target_root: 目标代码根目录路径
            file_path: 文件相对路径（如 "src/ball/ball_entity"）
            file_extension: 目标文件扩展名，默认.py
            
        Returns:
            str: 目标代码文件的完整路径
            
        Example:
            >>> path = IbcPathBuilder.build_target_code_path(
            ...     "/project/src_target",
            ...     "src/ball/ball_entity",
            ...     ".py"
            ... )
            >>> # Windows: "\\project\\src_target\\src\\ball\\ball_entity.py"
            >>> # Linux: "/project/src_target/src/ball/ball_entity.py"
        """
        # 将路径分隔符统一为系统分隔符
        normalized_path = file_path.replace('/', os.sep)
        
        # 添加目标文件扩展名
        target_file_name = normalized_path + file_extension
        
        # 拼接完整路径
        return os.path.join(target_root, target_file_name)
    
    @staticmethod
    def build_one_file_req_path(staging_root: str, file_path: str) -> str:
        """构建单文件需求描述路径
        
        格式：staging_root/file_path_one_file_req.txt
        
        Args:
            staging_root: staging根目录路径（通常为src_staging）
            file_path: 文件相对路径（如 "src/ball/ball_entity"）
            
        Returns:
            str: 单文件需求描述文件的完整路径
            
        Example:
            >>> path = IbcPathBuilder.build_one_file_req_path(
            ...     "/project/src_staging",
            ...     "src/ball/ball_entity"
            ... )
            >>> # "/project/src_staging/src/ball/ball_entity_one_file_req.txt"
        """
        normalized_file_path = file_path.replace('/', os.sep)
        return os.path.join(staging_root, f"{normalized_file_path}_one_file_req.txt")
    
    @staticmethod
    def extract_file_name(file_path: str) -> str:
        """从文件路径中提取文件名（不含路径和扩展名）
        
        Args:
            file_path: 文件路径（如 "src/ball/ball_entity" 或 "src/ball/ball_entity.ibc"）
            
        Returns:
            str: 文件名（如 "ball_entity"）
            
        Example:
            >>> name = IbcPathBuilder.extract_file_name("src/ball/ball_entity")
            >>> print(name)
            'ball_entity'
            >>> name = IbcPathBuilder.extract_file_name("src/ball/ball_entity.ibc")
            >>> print(name)
            'ball_entity'
        """
        # 先获取基础文件名
        base_name = os.path.basename(file_path)
        # 移除扩展名
        name_without_ext = os.path.splitext(base_name)[0]
        return name_without_ext
    
    @staticmethod
    def extract_dir_path(file_path: str) -> str:
        """从文件路径中提取目录路径
        
        Args:
            file_path: 文件路径（如 "src/ball/ball_entity"）
            
        Returns:
            str: 目录路径（如 "src/ball"），如果没有目录则返回空字符串
            
        Example:
            >>> dir_path = IbcPathBuilder.extract_dir_path("src/ball/ball_entity")
            >>> print(dir_path)
            'src/ball'
            >>> dir_path = IbcPathBuilder.extract_dir_path("ball_entity")
            >>> print(dir_path)
            ''
        """
        dir_path = os.path.dirname(file_path)
        return dir_path if dir_path else ""
    
    @staticmethod
    def normalize_file_path(file_path: str, separator: str = '/') -> str:
        """规范化文件路径
        
        将路径统一为使用指定分隔符的格式。
        
        Args:
            file_path: 要规范化的文件路径
            separator: 路径分隔符，默认为'/'
            
        Returns:
            str: 规范化后的文件路径
            
        Example:
            >>> path = IbcPathBuilder.normalize_file_path("src\\ball\\ball_entity")
            >>> print(path)
            'src/ball/ball_entity'
        """
        # 替换所有路径分隔符为指定分隔符
        normalized = file_path.replace('\\', separator).replace('/', separator)
        
        # 移除多余的分隔符
        while separator + separator in normalized:
            normalized = normalized.replace(separator + separator, separator)
        
        return normalized
    
    @staticmethod
    def join_file_paths(*parts: str) -> str:
        """连接文件路径部分
        
        自动过滤空字符串，使用操作系统的路径分隔符。
        
        Args:
            *parts: 路径部分
            
        Returns:
            str: 连接后的完整路径
            
        Example:
            >>> path = IbcPathBuilder.join_file_paths("src", "ball", "ball_entity")
            >>> # Windows: "src\\ball\\ball_entity"
            >>> # Linux: "src/ball/ball_entity"
        """
        # 过滤空字符串
        non_empty_parts = [p for p in parts if p]
        return os.path.join(*non_empty_parts) if non_empty_parts else ""
