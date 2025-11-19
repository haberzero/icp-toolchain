from typing import List

from typedef.ibc_data_types import IbcKeywords, IbcTokenType, Token


class LexerError(Exception):
    """词法分析器异常"""
    def __init__(self, message: str) -> None:
        self.message:str = message
        super().__init__(self.message)
    
    def __str__(self) -> str:
        return f"LexerError: {self.message}"


class IbcLexer:
    """Intent Behavior Code 词法分析器"""
    def __init__(self, text: str) -> None:
        self.text: str = text
        # 修复：正确处理空字符串的情况
        self.lines: list[str] = text.split(sep='\n') if text else []
        self.line_num = 0
        self.current_line = ""
        self.tokens: List[Token] = []
        self.indent_stack: List[int] = [0]  # 用于跟踪缩进级别的栈，初始为0
        self.is_keyword_line = False
        
        # 如果文件为空，添加一个空行以确保后续处理逻辑正常工作
        if not self.lines or (len(self.lines) == 1 and self.lines[0] == ""):
            self.lines = [""]
    
    def _get_next_line(self) -> bool:
        """获取下一行，如果已经到文件末尾则返回False"""
        if self.line_num >= len(self.lines):
            return False
        
        self.current_line: str = self.lines[self.line_num].rstrip()
        self.line_num += 1
        return True
    
    def _calc_indent_level(self, current_line: str) -> int:
        """计算缩进等级"""
        lstriped_line: str = current_line.lstrip(' ')
        if lstriped_line.startswith('\t'):
            raise LexerError(message=f"Line {self.line_num}: Tab indentation is not allowed")

        left_spaces_num: int = len(current_line) - len(lstriped_line)
        if left_spaces_num % 4 != 0:
            # 打印警告并截断到最近的4倍数
            truncated_spaces = (left_spaces_num // 4) * 4
            print(f"Warning: Line {self.line_num}: Indentation is {left_spaces_num} spaces (not a multiple of 4), "
                  f"truncating to {truncated_spaces} spaces")
            left_spaces_num = truncated_spaces
            
        return left_spaces_num // 4
    
    def _process_keyword(self, striped_line: str) -> str:
        """处理关键字，仅在每一行起始且被空格或:分隔开的关键字被认为是关键字，其余时候识别为普通 IDENTIFIER"""
        
        parts: list[str] = [""]

        if striped_line.startswith('@'):
            # 意图注释开头的@被视为一个特殊关键字，考虑到不同人的书写习惯，暂时不强制要求空格分割
            # 如果未来认为逻辑结构的统一性更重要，则可能在后续版本中规定@符号后必须有空格
            parts[0] = '@'
        else:
            # 使用空格和冒号作为分隔符分割字符串。整个Lexer仅在识别关键字时会出现空格 split
            parts = striped_line.replace(':', ' ', 1).split()

        first_part: str = parts[0]
        if first_part not in [kw.value for kw in IbcKeywords]:
            self.is_keyword_line = False
            return striped_line
        
        self.is_keyword_line = True
        self.tokens.append(Token(type=IbcTokenType.KEYWORDS, value=first_part, line_num=self.line_num))

        # 移除关键字部分并返回剩余内容
        keyword_len: int = len(first_part)
        content_line: str = striped_line[keyword_len:].lstrip()
        return content_line
    
    def _tokenize_line(self, content_line: str) -> None:
        """对当前行进行词法分析"""
        # 检查是否包含符号引用
        ref_parts: list[str] = content_line.split(sep='$')
        if len(ref_parts) > 1:  # 包含$符号
            # 处理包含符号引用的行
            self._tokenize_line_with_refs(content_line)
            return 
        
        # 普通行处理
        self._tokenize_text_part(content_line)
        return
    
    def _tokenize_line_with_refs(self, content_line: str) -> None:
        """处理包含符号引用的行"""
        parts: list[str] = content_line.split(sep='$')
        
        # 检查$符号数量是否为偶数
        if len(parts) % 2 == 0:
            raise LexerError(f"Line {self.line_num}: Unexpected $ symbol usage, $ symbols must appear in pairs")
        
        # 处理过滤后的部分
        for i, part in enumerate(parts):
            if i % 2 == 1:
                # 奇数索引是引用标识符，对纯空白内容弹出警告并跳过
                if not parts[i].strip():
                    print(f"Warning: Line {self.line_num}: Empty reference identifier between $$, will be removed")
                    continue
                else:
                    self.tokens.append(Token(IbcTokenType.REF_IDENTIFIER, part, self.line_num))
            else:
                # 偶数索引是普通文本
                if part.strip():
                    self._tokenize_text_part(part)
    
    def _tokenize_text_part(self, text: str):
        r"""对文本部分进行分词：识别 ( ) { } [ ] , : \ 等特殊符号
        其余所有连续非特殊字符（包括数字、字母、符号、空格等）视为 IDENTIFIER 即普通文本
        """
        i = 0
        n = len(text)
        special_chars = '(){}[],:\\' # 特殊字符集合
        
        while i < n:
            char = text[i]
            if char == '(':
                self.tokens.append(Token(IbcTokenType.LPAREN, '(', self.line_num))
                i += 1
            elif char == ')':
                self.tokens.append(Token(IbcTokenType.RPAREN, ')', self.line_num))
                i += 1
            elif char == '{':
                self.tokens.append(Token(IbcTokenType.LBRACE, '{', self.line_num))
                i += 1
            elif char == '}':
                self.tokens.append(Token(IbcTokenType.RBRACE, '}', self.line_num))
                i += 1
            elif char == '[':
                self.tokens.append(Token(IbcTokenType.LBRACKET, '[', self.line_num))
                i += 1
            elif char == ']':
                self.tokens.append(Token(IbcTokenType.RBRACKET, ']', self.line_num))
                i += 1
            elif char == ',':
                self.tokens.append(Token(IbcTokenType.COMMA, ',', self.line_num))
                i += 1
            elif char == ':':
                self.tokens.append(Token(IbcTokenType.COLON, ':', self.line_num))
                i += 1
            elif char == '\\':
                self.tokens.append(Token(IbcTokenType.BACKSLASH, '\\', self.line_num))
                i += 1
            else:
                # 收集非保留符号的常规字符，包括空格也被直接作为常规字符收集
                start = i
                while i < n and text[i] not in special_chars:
                    i += 1
                identifier = text[start:i]
                self.tokens.append(Token(IbcTokenType.IDENTIFIER, identifier, self.line_num))

    def tokenize(self) -> List[Token]:
        """执行词法分析"""
        try:
            # 空文件也应该添加NEWLINE和EOF
            if not self.lines:
                self.tokens.append(Token(IbcTokenType.NEWLINE, '', 1))
                self.tokens.append(Token(IbcTokenType.EOF, '', 1))
                return self.tokens
            
            # 处理每一行
            while self._get_next_line():
                # 跳过空行和注释行
                striped_line = self.current_line.strip()
                if not striped_line or striped_line.startswith('//'):
                    continue

                # 处理缩进
                indent_level = self._calc_indent_level(self.current_line)
                current_indent = self.indent_stack[-1]
                if indent_level > current_indent:
                    # 根据缩进差值添加相应数量的 INDENT token
                    indent_diff = indent_level - current_indent
                    for _ in range(indent_diff):
                        self.tokens.append(Token(IbcTokenType.INDENT, "", self.line_num))
                        current_indent += 1
                        self.indent_stack.append(current_indent)
                elif indent_level < current_indent:
                    # 减少缩进
                    while self.indent_stack and self.indent_stack[-1] > indent_level:
                        self.tokens.append(Token(IbcTokenType.DEDENT, "", self.line_num))
                        self.indent_stack.pop()
                    
                    # 检查缩进是否对齐
                    if not self.indent_stack or self.indent_stack[-1] != indent_level:
                        raise LexerError(f"Line {self.line_num}: Inconsistent indentation")
                
                # 识别并处理行开头可能存在的关键字
                content_line: str = self._process_keyword(striped_line)

                # 处理行
                self._tokenize_line(content_line)
                
                # 每行结束后添加换行符
                self.tokens.append(Token(IbcTokenType.NEWLINE, '', self.line_num))
            
            # 文件结束前处理剩余的DEDENT
            while len(self.indent_stack) > 1:
                self.tokens.append(Token(IbcTokenType.DEDENT, "", self.line_num))
                self.indent_stack.pop()
            
            # 添加最终的换行符和EOF
            self.tokens.append(Token(IbcTokenType.NEWLINE, '', self.line_num))
            self.tokens.append(Token(IbcTokenType.EOF, '', self.line_num))
            
            return self.tokens
        
        except LexerError:
            raise LexerError(f"Line {self.line_num}: Lexer error")
        
        except Exception as e:
            print(f"!!! Unexpected Error: {e}")
            raise LexerError(f"Line {self.line_num}: Lexer error")
        
