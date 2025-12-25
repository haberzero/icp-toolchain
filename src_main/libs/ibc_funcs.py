import os
import json
import re
import hashlib
from typing import List, Dict, Optional, Union, Set, Any

from typedef.ibc_data_types import (
    IbcBaseAstNode, ClassNode, FunctionNode, VariableNode, 
    BehaviorStepNode, SymbolType, VisibilityTypes, SymbolNode
)
from typedef.exception_types import SymbolNotFoundError

class IbcFuncs:
    """IBC代码处理相关的静态工具函数集合"""
    
    # ==================== MD5计算 ====================
    
    @staticmethod
    def calculate_text_md5(text: str) -> str:
        """计算文本字符串的MD5校验值"""
        try:
            text_hash = hashlib.md5()
            text_hash.update(text.encode('utf-8'))
            return text_hash.hexdigest()
        except UnicodeEncodeError as e:
            raise ValueError(f"文本编码错误,无法转换为UTF-8") from e
        except Exception as e:
            raise RuntimeError(f"计算文本MD5时发生未知错误") from e
    
    # ==================== 符号验证 ====================
    
    @staticmethod
    def validate_identifier(identifier: str) -> bool:
        """验证标识符是否符合编程规范
        
        标识符必须以字母或下划线开头,仅包含字母、数字、下划线
        """
        if not identifier:
            return False
        pattern = r'^[a-zA-Z_][a-zA-Z0-9_]*$'
        return re.match(pattern, identifier) is not None
    
    # ==================== 符号路径处理 ====================
    
    @staticmethod
    def build_available_symbol_list(
        symbols_metadata: Dict[str, Dict[str, Any]],
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
        available_symbol_lines = []
        
        for symbol_path, meta in symbols_metadata.items():
            meta_type = meta.get("type")
            # 跳过文件夹和文件节点，只处理具体符号
            if meta_type in ("folder", "file"):
                continue
            
            desc = meta.get("description")
            if not desc:
                desc = "没有对外功能描述"
            
            # 简化符号路径
            simplified_path = IbcFuncs._simplify_symbol_path(symbol_path, proj_root_dict)
            available_symbol_lines.append(f"${simplified_path} ：{desc}")
        
        return available_symbol_lines
    
    @staticmethod
    def _simplify_symbol_path(full_symbol_path: str, proj_root_dict: Dict[str, Any]) -> str:
        """简化符号路径，移除路径前缀，只保留从文件名开始的部分
        
        例如：
        - 输入：src.ball.ball_entity.BallEntity.get_position
        - 输出：ball_entity.BallEntity.get_position
        
        处理逻辑：
        1. 分割路径为各个部分
        2. 找到文件名部分（在 proj_root_dict 中是叶子节点）
        3. 返回从文件名开始到结尾的路径
        
        Args:
            full_symbol_path: 完整的符号路径（点分隔）
            proj_root_dict: 项目根目录字典
            
        Returns:
            str: 简化后的符号路径
        """
        parts = full_symbol_path.split('.')
        
        # 遍历proj_root_dict，找到文件名位置
        # 例如：src.ball.ball_entity -> ball_entity 是文件名
        current_dict = proj_root_dict
        file_name_index = -1
        
        for i, part in enumerate(parts):
            if isinstance(current_dict, dict) and part in current_dict:
                next_value = current_dict[part]
                # 如果下一个值是字符串，说明当前part是文件名
                if isinstance(next_value, str):
                    file_name_index = i
                    break
                # 否则继续向下查找
                current_dict = next_value
            else:
                # 无法继续匹配，说明已经到了符号部分
                break
        
        # 如果找到了文件名，从文件名开始返回路径
        if file_name_index >= 0:
            return '.'.join(parts[file_name_index:])
        
        # 如果没找到文件名（不应该发生），返回原路径
        return full_symbol_path
    