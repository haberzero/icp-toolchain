import os
import json
import re
import hashlib
from typing import List, Dict, Optional, Union, Set, Any, Tuple

from typedef.exception_types import SymbolNotFoundError
from typedef.ibc_data_types import (
    IbcBaseAstNode, AstNodeType, ClassNode, FunctionNode, VariableNode, BehaviorStepNode
)

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
    
    @staticmethod
    def calculate_symbols_metadata_md5(symbols_metadata: Dict[str, Dict[str, Any]]) -> str:
        """计算符号元数据的MD5校验值
        
        Args:
            symbols_metadata: 符号元数据字典
            
        Returns:
            str: MD5校验值
        """
        try:
            # 将字典转换为JSON字符串(排序键以确保一致性)
            metadata_json = json.dumps(symbols_metadata, sort_keys=True, ensure_ascii=False)
            return IbcFuncs.calculate_text_md5(metadata_json)
        except Exception as e:
            raise RuntimeError(f"计算符号元数据MD5时发生错误: {e}") from e
    
    @staticmethod
    def count_symbols_in_metadata(symbols_metadata: Dict[str, Dict[str, Any]]) -> int:
        """统计符号元数据中的符号数量(排除文件夹和文件节点)
        
        Args:
            symbols_metadata: 符号元数据字典
            
        Returns:
            int: 符号数量
        """
        count = 0
        for meta in symbols_metadata.values():
            meta_type = meta.get("type", "")
            # 只统计实际符号(class, func, var),不统计folder和file
            if meta_type in ("class", "func", "var"):
                count += 1
        return count
    
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
    
    # ==================== 符号替换 ====================
    
    @staticmethod
    def replace_symbols_with_normalized_names(
        ibc_content: str,
        ast_dict: Dict[int, IbcBaseAstNode],
        symbols_metadata: Dict[str, Dict[str, Any]],
        current_file_name: str
    ) -> str:
        """将IBC代码内容中的所有符号替换为规范化后的名称
        
        该方法遍历AST，找到所有定义的符号（类名、函数名、变量名、参数名）和
        所有符号引用（$引用），然后用规范化后的名称替换原始文本中的相应位置。
        
        Args:
            ibc_content: IBC代码原始内容
            ast_dict: AST字典
            symbols_metadata: 符号元数据（包含normalized_name）
            current_file_name: 当前文件名（不含路径和扩展名）
            
        Returns:
            str: 替换后的IBC代码内容
        """
        # 收集所有需要替换的符号映射
        # 格式: {原始名称: (规范化名称, 符号类型, 优先级)}
        replacements = {}
        
        # 遍历AST收集符号
        for uid, node in ast_dict.items():
            if uid == 0:  # 跳过根节点
                continue
                
            # 处理类节点
            if isinstance(node, ClassNode) and node.identifier:
                symbol_path = f"{current_file_name}.{node.identifier}"
                normalized = IbcFuncs._get_normalized_name(symbol_path, symbols_metadata)
                if normalized and normalized != node.identifier:
                    # 类名的优先级最高（3），因为可能包含在其他标识符中
                    replacements[node.identifier] = (normalized, 'class', 3)
                
                # 处理类的继承参数
                for param_name in node.inh_params.keys():
                    param_path = f"{current_file_name}.{node.identifier}.{param_name}"
                    param_normalized = IbcFuncs._get_normalized_name(param_path, symbols_metadata)
                    if param_normalized and param_normalized != param_name:
                        replacements[param_name] = (param_normalized, 'param', 1)
            
            # 处理函数节点
            elif isinstance(node, FunctionNode) and node.identifier:
                # 获取父节点路径
                parent_path = IbcFuncs._get_parent_symbol_path(node, ast_dict, current_file_name)
                symbol_path = f"{parent_path}.{node.identifier}" if parent_path else f"{current_file_name}.{node.identifier}"
                normalized = IbcFuncs._get_normalized_name(symbol_path, symbols_metadata)
                if normalized and normalized != node.identifier:
                    replacements[node.identifier] = (normalized, 'func', 2)
                
                # 处理函数参数
                for param_name in node.params.keys():
                    param_symbol_path = f"{symbol_path}.{param_name}"
                    param_normalized = IbcFuncs._get_normalized_name(param_symbol_path, symbols_metadata)
                    if param_normalized and param_normalized != param_name:
                        replacements[param_name] = (param_normalized, 'param', 1)
            
            # 处理变量节点
            elif isinstance(node, VariableNode) and node.identifier:
                # 获取父节点路径
                parent_path = IbcFuncs._get_parent_symbol_path(node, ast_dict, current_file_name)
                symbol_path = f"{parent_path}.{node.identifier}" if parent_path else f"{current_file_name}.{node.identifier}"
                normalized = IbcFuncs._get_normalized_name(symbol_path, symbols_metadata)
                if normalized and normalized != node.identifier:
                    replacements[node.identifier] = (normalized, 'var', 2)
            
            # 处理行为步骤中的符号引用
            elif isinstance(node, BehaviorStepNode):
                # symbol_refs中包含$引用，这些已经被解析并验证过
                # 我们需要在文本中找到这些引用并替换为规范化名称
                pass  # 符号引用的处理在后面统一进行
        
        # 从 symbols_metadata 中收集所有其他符号（特别是 behavior 中的局部变量）
        for symbol_path, meta in symbols_metadata.items():
            # 跳过文件夹和文件节点
            if meta.get('type') in ('folder', 'file'):
                continue
            
            normalized_name = meta.get('normalized_name')
            if not normalized_name:
                continue
            
            # 提取原始名称（symbol_path 的最后一部分）
            original_name = symbol_path.split('.')[-1]
            
            # 如果还没有被添加，就加入
            if original_name not in replacements and normalized_name != original_name:
                # 优先级设为1，在普通符号之后替换
                replacements[original_name] = (normalized_name, meta.get('type', 'unknown'), 1)
        
        # 执行替换
        result = IbcFuncs._apply_symbol_replacements(ibc_content, replacements, symbols_metadata)
        
        return result
    
    @staticmethod
    def _get_normalized_name(symbol_path: str, symbols_metadata: Dict[str, Dict[str, Any]]) -> Optional[str]:
        """从symbols_metadata中获取规范化名称
        
        Args:
            symbol_path: 符号完整路径
            symbols_metadata: 符号元数据
            
        Returns:
            Optional[str]: 规范化名称，如果不存在则返回None
        """
        if symbol_path in symbols_metadata:
            meta = symbols_metadata[symbol_path]
            return meta.get('normalized_name')
        return None
    
    @staticmethod
    def _get_parent_symbol_path(node: IbcBaseAstNode, ast_dict: Dict[int, IbcBaseAstNode], file_name: str) -> str:
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
    def _apply_symbol_replacements(
        content: str,
        replacements: Dict[str, Tuple[str, str, int]],
        symbols_metadata: Dict[str, Dict[str, Any]]
    ) -> str:
        """应用符号替换到IBC内容
        
        策略：
        1. 按照优先级和长度排序（先长后短，避免部分匹配）
        2. 使用正则表达式进行精确的标识符边界匹配
        3. 处理$符号引用
        
        Args:
            content: 原始内容
            replacements: 替换映射 {原始名称: (规范化名称, 类型, 优先级)}
            symbols_metadata: 符号元数据（用于处理$引用）
            
        Returns:
            str: 替换后的内容
        """
        result = content
        
        # 按优先级和长度排序（优先级高的先处理，同优先级的长的先处理）
        sorted_replacements = sorted(
            replacements.items(),
            key=lambda x: (-x[1][2], -len(x[0]))  # 优先级降序，长度降序
        )
        
        # 执行普通标识符替换
        for original, (normalized, sym_type, _) in sorted_replacements:
            # 使用正则表达式匹配完整的标识符（避免部分匹配）
            # 标识符前后必须是非标识符字符
            pattern = r'(?<![\w_])' + re.escape(original) + r'(?![\w_])'
            result = re.sub(pattern, normalized, result)
        
        # 处理$符号引用
        # $引用的格式: $module.symbol 或 $symbol
        # 需要找到所有$引用，并替换其中的符号名称
        result = IbcFuncs._replace_dollar_references(result, symbols_metadata, replacements)
        
        return result
    
    @staticmethod
    def _replace_dollar_references(
        content: str,
        symbols_metadata: Dict[str, Dict[str, Any]],
        replacements: Dict[str, Tuple[str, str, int]]
    ) -> str:
        """替换$符号引用中的符号名称
        
        Args:
            content: 内容
            symbols_metadata: 符号元数据
            replacements: 已有的替换映射
            
        Returns:
            str: 替换后的内容
        """
        # 匹配$引用：$后跟标识符和点分隔的路径
        # 例如: $gravity.apply_gravity, $self.position, $friction.FrictionManager
        pattern = r'\$([\w_]+(?:\.[\w_]+)*)'
        
        def replace_ref(match):
            ref = match.group(1)  # 不含$的引用路径
            parts = ref.split('.')
            
            # 替换路径中的每个部分
            new_parts = []
            for part in parts:
                if part in replacements:
                    new_parts.append(replacements[part][0])  # 使用规范化名称
                else:
                    new_parts.append(part)
            
            return '$' + '.'.join(new_parts)
        
        return re.sub(pattern, replace_ref, content)
    

    