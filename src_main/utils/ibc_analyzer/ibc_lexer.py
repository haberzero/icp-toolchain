from typing import List

from typedef.ibc_data_types import IbcKeywords, IbcTokenType, Token


class LexerError(Exception):
    """词法分析器异常"""
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)
    
    def __str__(self):
        return f"LexerError: {self.message}"


class Lexer:
    """Intent Behavior Code 词法分析器"""
    def __init__(self, text: str):
        self.text = text
        # 修复：正确处理空字符串的情况
        self.lines = text.split('\n') if text else []
        self.line_num = 0
        self.current_line = ""
        self.tokens: List[Token] = []
        self.indent_stack: List[int] = [0]  # 用于跟踪缩进级别的栈，初始为0
        
        # 如果文件为空，添加一个空行以确保后续处理逻辑正常工作
        if not self.lines or (len(self.lines) == 1 and self.lines[0] == ""):
            self.lines = [""]
    
    def _get_next_line(self) -> bool:
        """获取下一行，如果已经到文件末尾则返回False"""
        if self.line_num >= len(self.lines):
            return False
        
        self.current_line = self.lines[self.line_num].rstrip()
        self.line_num += 1
        return True
    
    def _calc_indent_level(self, current_line: str) -> int:
        """计算缩进等级"""
        lstriped_line = current_line.lstrip(' ')
        if lstriped_line.startswith('\t'):
            print(f"Line {self.line_num}: Tab indentation is not allowed")
            return -1

        left_spaces_num = len(current_line) - len(lstriped_line)
        if left_spaces_num % 4 != 0:
            print(f"Line {self.line_num}: Invalid indentation level")
            return -1
            
        return left_spaces_num // 4
    
    def _process_keyword(self, striped_line: str):
        """处理关键字，仅在每一行起始且被空格或:分隔开的关键字被认为是关键字，其余时候识别为普通 IDENTIFIER"""
        # 使用空格和冒号作为分隔符分割字符串，仅在识别关键字时会出现空格识别
        parts = striped_line.replace(':', ' ', 1).split()
        
        # 如果没有分割出任何部分，或者输入为空，则直接返回原字符串
        if not parts:
            return striped_line
            
        # 获取第一个分割出的部分，检查它是否是关键字
        first_part = parts[0]
        for keyword in IbcKeywords:
            if keyword.value == first_part:
                # 找到关键字，添加到tokens列表中
                self.tokens.append(Token(IbcTokenType.KEYWORDS, first_part, self.line_num))
                # 移除关键字部分并返回剩余内容
                keyword_len = len(first_part)
                content_line = striped_line[keyword_len:].lstrip()
                return content_line
        
        # 没有找到关键字，返回原始字符串
        return striped_line
    
    def _tokenize_line(self, content_line: str):
        """对当前行进行词法分析"""
        # 检查是否是意图注释行
        if content_line.startswith('@'):
            content = content_line[1:].strip()
            self.tokens.append(Token(IbcTokenType.INTENT_COMMENT, content, self.line_num))
            return
        
        # 检查是否包含符号引用
        ref_parts = content_line.split('$')
        if len(ref_parts) > 1:  # 包含$符号
            # 处理包含符号引用的行
            self._tokenize_line_with_refs(content_line)
            return 
        
        # 普通行处理
        self._tokenize_text_part(content_line)
        return
    
    def _tokenize_line_with_refs(self, content_line: str):
        """处理包含符号引用的行"""
        parts = content_line.split('$')
        
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
        """对文本部分进行分词：仅识别 ( ) , : 四个特殊符号
        其余所有连续非特殊字符（包括数字、字母、符号、空格等）视为 IDENTIFIER 即普通文本
        """
        i = 0
        n = len(text)
        while i < n:
            char = text[i]
            if char == '(':
                self.tokens.append(Token(IbcTokenType.LPAREN, '(', self.line_num))
                i += 1
            elif char == ')':
                self.tokens.append(Token(IbcTokenType.RPAREN, ')', self.line_num))
                i += 1
            elif char == ',':
                self.tokens.append(Token(IbcTokenType.COMMA, ',', self.line_num))
                i += 1
            elif char == ':':
                self.tokens.append(Token(IbcTokenType.COLON, ':', self.line_num))
                i += 1
            else:
                # 收集非保留符号的常规字符，包括空格也被直接作为常规字符收集
                start = i
                while i < n and text[i] not in '(),:':
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
                if indent_level == -1:
                    raise LexerError(f"Line {self.line_num}: Invalid indentation")
                else:
                    # 处理缩进变化
                    current_indent = self.indent_stack[-1]
                    if indent_level > current_indent:
                        # 检查缩进是否跳变（一次增加超过1级）
                        if indent_level - current_indent > 1:
                            raise LexerError(
                                f"Line {self.line_num}: Indentation jump is not allowed, "
                                f"expected {current_indent + 1}, but got {indent_level}")
                        
                        # 增加缩进
                        self.tokens.append(Token(IbcTokenType.INDENT, "", self.line_num))
                        self.indent_stack.append(indent_level)
                    elif indent_level < current_indent:
                        # 减少缩进
                        while self.indent_stack and self.indent_stack[-1] > indent_level:
                            self.tokens.append(Token(IbcTokenType.DEDENT, "", self.line_num))
                            self.indent_stack.pop()
                        
                        # 检查缩进是否对齐
                        if not self.indent_stack or self.indent_stack[-1] != indent_level:
                            raise LexerError(f"Line {self.line_num}: Inconsistent indentation")
                    
                # 识别并处理行开头可能存在的关键字
                content_line = self._process_keyword(striped_line)

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
        
        except LexerError as e:
            # 出现错误时打印错误信息并返回空列表
            print(e)
            return []
        
        except Exception as e:
            # 其他异常时打印错误信息并返回空列表
            print(f"!!! Unexpected Error: {e}")
            return []