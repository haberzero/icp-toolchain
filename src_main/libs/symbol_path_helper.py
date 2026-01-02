from typing import Any, Dict, List


class SymbolPathHelper:
    """符号路径处理辅助类
    
    提供符号路径的简化、构建和转换功能
    """
    
    @staticmethod
    def simplify_symbol_path(full_symbol_path: str, proj_root_dict: Dict[str, Any]) -> str:
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
    
    @staticmethod
    def get_parent_symbol_path(
        node,  # IbcBaseAstNode类型，但为避免循环导入不做类型标注
        ast_dict: Dict[int, Any],
        file_name: str
    ) -> str:
        """获取节点的父符号路径
        
        Args:
            node: 当前节点
            ast_dict: AST字典
            file_name: 文件名
            
        Returns:
            str: 父符号路径
        """
        path_parts = [file_name]
        current_uid = node.parent_uid
        
        while current_uid != 0:
            if current_uid not in ast_dict:
                break
            parent = ast_dict[current_uid]
            
            # 只添加有identifier的节点
            if hasattr(parent, 'identifier') and parent.identifier:
                path_parts.insert(1, parent.identifier)
            
            current_uid = parent.parent_uid
        
        return '.'.join(path_parts)
    
    @staticmethod
    def build_full_symbol_path(
        symbol_name: str,
        parent_path: str = "",
        file_name: str = ""
    ) -> str:
        """构建完整的符号路径
        
        Args:
            symbol_name: 符号名称
            parent_path: 父路径（可选）
            file_name: 文件名（可选）
            
        Returns:
            str: 完整的符号路径
        """
        if parent_path:
            return f"{parent_path}.{symbol_name}"
        elif file_name:
            return f"{file_name}.{symbol_name}"
        else:
            return symbol_name
    
    @staticmethod
    def extract_symbol_name(symbol_path: str) -> str:
        """从符号路径中提取符号名称（最后一部分）
        
        Args:
            symbol_path: 符号路径（如 file.ClassName.method）
            
        Returns:
            str: 符号名称（如 method）
        """
        parts = symbol_path.split('.')
        return parts[-1] if parts else symbol_path
    
    @staticmethod
    def split_symbol_path(symbol_path: str) -> List[str]:
        """将符号路径分割为各个部分
        
        Args:
            symbol_path: 符号路径（如 file.ClassName.method）
            
        Returns:
            List[str]: 路径部分列表（如 ['file', 'ClassName', 'method']）
        """
        return symbol_path.split('.')
