import os
import json
import hashlib
from typing import List, Dict, Optional, Union, Set, Any

from .icp_colors import Colors


class IcpTextFuncs:

    @staticmethod
    def calculate_text_md5(text: str) -> str:
        """
        计算文本字符串的MD5校验值
        
        Args:
            text: 要计算MD5的文本字符串
            
        Returns:
            str: MD5哈希值的十六进制字符串
        """
        try:
            text_hash = hashlib.md5()
            text_hash.update(text.encode('utf-8'))
            return text_hash.hexdigest()
        except UnicodeEncodeError as e:
            raise ValueError(f"文本编码错误，无法转换为UTF-8") from e
        except Exception as e:
            raise RuntimeError(f"计算文本MD5时发生未知错误") from e



    def _initialize_update_status(
        self,
        file_creation_order_list: List[str],
        staging_dir_path: str,
        ibc_root_path: str,
    ) -> Dict[str, bool]:
        """
        初始化更新状态字典
        
        遍历所有文件，检查以下条件判断是否需要重新生成：
        1. 需求文件的MD5是否与已保存的符号表中的MD5匹配
        2. 目标IBC文件是否存在
        3. 符号表文件是否存在
        
        满足以下任一条件则需要更新：
        - 需求文件的MD5发生变化
        - 需求文件不存在
        - IBC文件不存在
        - 符号表文件不存在
        
        Args:
            file_creation_order_list: 文件创建顺序列表
            staging_dir_path: staging目录路径
            ibc_root_path: IBC根目录路径
            
        Returns:
            Dict[str, bool]: 更新状态字典，key为文件路径，value为是否需要更新
        """

    def _check_dependency_updated(
        self,
        dependencies: List[str],
        update_status: Dict[str, bool]
    ) -> bool:
        """
        检查当前文件的依赖文件是否有更新
        
        Args:
            dependencies: 依赖文件列表
            update_status: 更新状态字典
            
        Returns:
            bool: 如果任一依赖文件需要更新，返回True
        """
