class IbcAnalyzerError(Exception):
    """IBC分析器基础异常类"""
    def __init__(self, message: str, line_num: int = 0, line_content: str = ""):
        self.message = message
        self.line_num = line_num
        self.line_content = line_content
        super().__init__(self._format_message())
    
    def _format_message(self) -> str:
        """格式化错误信息"""
        if self.line_num > 0:
            if self.line_content:
                return (
                    f"IBC Analysis Error at Line {self.line_num}\n"
                    f"Line Content: {self.line_content}\n"
                    f"Error: {self.message}\n"
                )
            else:
                return f"Line {self.line_num}: {self.message}"
        return self.message


class LexerError(IbcAnalyzerError):
    """词法分析器异常"""
    def _format_message(self) -> str:
        """格式化词法错误信息"""
        if self.line_num > 0:
            if self.line_content:
                return (
                    f"Lexer Error at Line {self.line_num}\n"
                    f"Line Content: {self.line_content}\n"
                    f"Error: {self.message}\n"
                )
            else:
                return f"Lexer Error at Line {self.line_num}: {self.message}"
        return f"Lexer Error: {self.message}"


class IbcParserError(IbcAnalyzerError):
    """解析器状态机异常"""
    def _format_message(self) -> str:
        """格式化解析器错误信息"""
        if self.line_num > 0:
            if self.line_content:
                return (
                    f"Parser Error at Line {self.line_num}\n"
                    f"Line Content: {self.line_content}\n"
                    f"Error: {self.message}\n"
                )
            else:
                return f"Parser Error at Line {self.line_num}: {self.message}"
        return f"Parser Error: {self.message}"


class SymbolNotFoundError(Exception):
    """符号未找到异常"""
    def __init__(self, symbol_name: str, operation: str = ""):
        self.symbol_name = symbol_name
        self.operation = operation
        message = f"符号 '{symbol_name}' 在符号表中不存在"
        if operation:
            message += f"，无法执行操作: {operation}"
        super().__init__(message)
