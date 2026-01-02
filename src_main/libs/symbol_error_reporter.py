import difflib
from typing import Any, Dict, List, Set

from typedef.ibc_data_types import (ClassMetadata, FunctionMetadata,
                                    SymbolMetadata, VariableMetadata)
from utils.issue_recorder import IbcIssueRecorder


class SymbolErrorReporter:
    """符号错误报告器，提供统一的错误报告接口"""
    
    def __init__(
        self,
        ibc_issue_recorder: IbcIssueRecorder,
        local_symbols: Dict[str, SymbolMetadata]
    ):
        """初始化符号错误报告器
        
        Args:
            ibc_issue_recorder: 问题记录器
            local_symbols: 本地符号表
        """
        self.ibc_issue_recorder = ibc_issue_recorder
        self.local_symbols = local_symbols
    
    def collect_candidates(
        self,
        local_symbols_dict: Dict[str, SymbolMetadata],
        import_aliases: List[str]
    ) -> List[str]:
        """收集候选符号名称
        
        Args:
            local_symbols_dict: 局部作用域符号字典
            import_aliases: 导入的模块别名列表
            
        Returns:
            List[str]: 候选符号名称列表
        """
        candidates = []
        
        # 从局部符号收集
        candidates.extend(local_symbols_dict.keys())
        
        # 从本地符号收集
        for path in self.local_symbols:
            name = path.split('.')[-1]
            if name not in candidates:
                candidates.append(name)
        
        # 从导入的模块收集
        for alias in import_aliases:
            if alias not in candidates:
                candidates.append(alias)
        
        return candidates
    
    def find_similar_symbols(
        self,
        symbol_name: str,
        candidates: List[str],
        max_suggestions: int = 3,
        cutoff: float = 0.3
    ) -> List[str]:
        """查找相似的符号
        
        Args:
            symbol_name: 要查找的符号名
            candidates: 候选符号列表
            max_suggestions: 最大建议数量
            cutoff: 相似度阈值
            
        Returns:
            List[str]: 相似符号列表
        """
        return difflib.get_close_matches(symbol_name, candidates, n=max_suggestions, cutoff=cutoff)
    
    def generate_suggestion(self, similar_symbols: List[str]) -> str:
        """生成建议信息
        
        Args:
            similar_symbols: 相似符号列表
            
        Returns:
            str: 建议信息
        """
        if similar_symbols:
            return f"你是否想引用: {', '.join(similar_symbols)}？"
        else:
            return "未找到相似的符号"
    
    def record_not_found_error(
        self,
        ref: str,
        context_local_symbols: Dict[str, SymbolMetadata],
        import_aliases: List[str],
        line_num: int
    ) -> None:
        """记录符号未找到的错误，并提供建议
        
        Args:
            ref: 符号引用字符串
            context_local_symbols: 上下文局部符号
            import_aliases: 导入的模块别名列表
            line_num: 行号
        """
        parts = ref.split('.')
        first_part = parts[0]
        
        # 收集候选符号
        candidates = self.collect_candidates(context_local_symbols, import_aliases)
        
        # 模糊匹配
        matches = self.find_similar_symbols(first_part, candidates)
        suggestion = self.generate_suggestion(matches)
        
        # 确定错误类型
        if len(parts) == 1:
            message = f"符号引用错误：符号'{ref}'未找到。{suggestion}"
        else:
            # 检查第一部分是否是有效的模块别名
            is_module = first_part in import_aliases
            if is_module:
                message = f"符号引用错误：在模块'{first_part}'中未找到符号'{'.'.join(parts[1:])}'。{suggestion}"
            else:
                message = f"符号引用错误：'{first_part}'不是有效的模块或本地符号。{suggestion}"
        
        self.ibc_issue_recorder.record_issue(
            message=message,
            line_num=line_num,
            line_content=""
        )
    
    def record_visibility_error(
        self,
        symbol_name: str,
        visibility: str,
        line_num: int
    ) -> None:
        """记录可见性错误
        
        Args:
            symbol_name: 符号名称
            visibility: 可见性级别
            line_num: 行号
        """
        self.ibc_issue_recorder.record_issue(
            message=f"可见性错误：符号'{symbol_name}'在当前作用域中不可访问（{visibility}）",
            line_num=line_num,
            line_content=""
        )
    
    def record_self_reference_error(
        self,
        class_name: str,
        member_name: str,
        similar_members: List[str],
        line_num: int
    ) -> None:
        """记录self引用错误
        
        Args:
            class_name: 类名
            member_name: 成员名称
            similar_members: 相似成员列表
            line_num: 行号
        """
        suggestion = self.generate_suggestion(similar_members)
        if not similar_members:
            suggestion = "在当前类中未找到相似的成员"
        
        self.ibc_issue_recorder.record_issue(
            message=f"self引用错误：类'{class_name}'中不存在成员'{member_name}'。{suggestion}",
            line_num=line_num,
            line_content=""
        )
    
    def record_self_context_error(self, line_num: int) -> None:
        """记录self上下文错误
        
        Args:
            line_num: 行号
        """
        self.ibc_issue_recorder.record_issue(
            message=f"self引用错误：self只能在类的方法内使用",
            line_num=line_num,
            line_content=""
        )
