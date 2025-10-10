from typing import Dict, List, Optional, Any
from lexer import Lexer, IbcTokenType, IbcKeywords, Token
from enum import Enum


class NodeType(Enum):
    """AST节点类型枚举"""
    DEFAULT = "DEFAULT"
    MODULE = "MODULE"
    CLASS = "CLASS"
    FUNCTION = "FUNCTION"
    VARIABLE = "VARIABLE"
    DESCRIPTION = "DESCRIPTION"
    BEHAVIOR_STEP = "BEHAVIOR_STEP"
    ERROR = "ERROR"


class ASTNode:
    """AST节点类"""
    def __init__(self, uid: str = "", parent_uid: str = "", children_uids: List[str] = [], 
                 node_type: NodeType = NodeType.DEFAULT, line_number: int = 0, identifier: str = "",
                 content: str = "", external_desc: str = "", intent_comment: str = "",
                 params: Dict[str, str] = {}, symbol_refs: Dict[str, str] = {}):
        self.uid = uid
        self.parent_uid = parent_uid
        self.children_uids = children_uids if children_uids is not None else []
        self.node_type = node_type
        self.line_number = line_number
        self.identifier = identifier
        self.content = content
        self.external_desc = external_desc
        self.intent_comment = intent_comment
        self.params = params if params is not None else {}
        self.symbol_refs = symbol_refs if symbol_refs is not None else {}

    def to_dict(self) -> Dict[str, Any]:
        """将节点转换为字典表示"""
        return {
            "uid": self.uid,
            "parent_uid": self.parent_uid,
            "children_uids": self.children_uids,
            "node_type": self.node_type.value if self.node_type else None,
            "line_number": self.line_number,
            "identifier": self.identifier,
            "content": self.content,
            "external_desc": self.external_desc,
            "intent_comment": self.intent_comment,
            "params": self.params,
            "symbol_refs": self.symbol_refs
        }

    def __repr__(self):
        return f"ASTNode(uid={self.uid}, type={self.node_type}, identifier={self.identifier})"


class ParseError(Exception):
    """解析器异常"""
    def __init__(self, message: str, line_number: int = 0):
        self.message = message
        self.line_number = line_number
        super().__init__(self.message)
    
    def __str__(self):
        if self.line_number:
            return f"ParseError at line {self.line_number}: {self.message}"
        return f"ParseError: {self.message}"


class Parser:
    """IBC语法解析器"""
    
    def __init__(self, text: str):
        self.text = text
        self.lexer = Lexer(text)
        self.tokens: List[Token] = []
        self.current_token_index = 0
        self.ast_nodes: Dict[str, ASTNode] = {}
        self.node_counter = 0
        
    def _generate_node_uid(self) -> str:
        """生成唯一的节点ID"""
        self.node_counter += 1
        return f"node_{self.node_counter}"
    
    def _peek_token(self, offset: int = 0) -> Token:
        """查看下一个token但不移动指针"""
        index = self.current_token_index + offset
        if index < len(self.tokens):
            return self.tokens[index]
        return Token(IbcTokenType.EOF, "EOF", 0)
    
    def _consume_token(self) -> Token:
        """消费当前token并移动到下一个"""
        if self.current_token_index < len(self.tokens):
            token = self.tokens[self.current_token_index]
            self.current_token_index += 1
            return token
        return Token(IbcTokenType.EOF, "EOF", 0)
    
    def _match_token(self, expected_type: IbcTokenType) -> Token:
        """匹配期望类型的token"""
        token = self._peek_token()
        if token.type == expected_type:
            return self._consume_token()
        raise ParseError(f"Expected {expected_type} but got {token.type}", token.line_num)
    
    def _match_optional_token(self, expected_type: IbcTokenType) -> Optional[Token]:
        """可选地匹配token"""
        token = self._peek_token()
        if token.type == expected_type:
            return self._consume_token()
        return None
    
    def _collect_until_newline(self) -> str:
        """收集直到换行符的所有内容"""
        content_parts = []
        while self._peek_token().type not in [IbcTokenType.NEWLINE, IbcTokenType.EOF]:
            token = self._consume_token()
            content_parts.append(token.value)
        return "".join(content_parts)
    
    def _parse_module_decl(self, line_num: int) -> ASTNode:
        """解析模块声明"""
        # module关键字已经被消费
        module_token = self._match_token(IbcTokenType.IDENTIFIER)
        
        # 检查是否有冒号和描述
        description = ""
        if self._match_optional_token(IbcTokenType.COLON):
            description = self._collect_until_newline()
        else:
            # 确保行结束
            self._match_optional_token(IbcTokenType.NEWLINE)
        
        node = ASTNode(
            uid=self._generate_node_uid(),
            node_type=NodeType.MODULE,
            line_number=line_num,
            identifier=module_token.value,
            content=description.strip()
        )
        
        self.ast_nodes[node.uid] = node
        return node
    
    def _parse_var_decl(self, line_num: int) -> ASTNode:
        """解析变量声明"""
        # var关键字已经被消费
        vars_content = self._collect_until_newline()
        
        # 简单解析变量声明 (实际应用中可能需要更复杂的解析)
        node = ASTNode(
            uid=self._generate_node_uid(),
            node_type=NodeType.VARIABLE,
            line_number=line_num,
            content=vars_content.strip()
        )
        
        self.ast_nodes[node.uid] = node
        return node
    
    def _parse_description(self, line_num: int) -> ASTNode:
        """解析描述声明"""
        # description关键字已经被消费
        self._match_token(IbcTokenType.COLON)
        description_content = self._collect_until_newline()
        
        node = ASTNode(
            uid=self._generate_node_uid(),
            node_type=NodeType.DESCRIPTION,
            line_number=line_num,
            content=description_content.strip()
        )
        
        self.ast_nodes[node.uid] = node
        return node
    
    def _parse_intent_comment(self, line_num: int) -> ASTNode:
        """解析意图注释"""
        # @符号已经被消费
        comment_content = self._collect_until_newline()
        
        node = ASTNode(
            uid=self._generate_node_uid(),
            node_type=NodeType.BEHAVIOR_STEP,  # 意图注释暂时作为行为步骤处理
            line_number=line_num,
            intent_comment=comment_content.strip()
        )
        
        self.ast_nodes[node.uid] = node
        return node
    
    def _parse_func_decl(self, line_num: int) -> ASTNode:
        """解析函数声明"""
        # func关键字已经被消费
        func_name_token = self._match_token(IbcTokenType.IDENTIFIER)
        
        # 解析参数列表
        self._match_token(IbcTokenType.LPAREN)
        
        params = {}
        # 解析参数直到右括号
        while self._peek_token().type != IbcTokenType.RPAREN:
            param_token = self._consume_token()
            if param_token.type == IbcTokenType.IDENTIFIER:
                param_name = param_token.value
                # 检查是否有参数描述
                if self._match_optional_token(IbcTokenType.COLON):
                    # 收集参数描述直到逗号或右括号
                    desc_parts = []
                    while self._peek_token().type not in [IbcTokenType.COMMA, IbcTokenType.RPAREN, IbcTokenType.EOF]:
                        desc_token = self._consume_token()
                        desc_parts.append(desc_token.value)
                    param_desc = "".join(desc_parts).strip()
                    params[param_name] = param_desc
                else:
                    params[param_name] = ""
                    
                # 如果是逗号，继续下一个参数
                if self._peek_token().type == IbcTokenType.COMMA:
                    self._consume_token()  # 消费逗号
                    
        self._match_token(IbcTokenType.RPAREN)
        self._match_token(IbcTokenType.COLON)
        self._match_token(IbcTokenType.NEWLINE)
        
        node = ASTNode(
            uid=self._generate_node_uid(),
            node_type=NodeType.FUNCTION,
            line_number=line_num,
            identifier=func_name_token.value,
            params=params
        )
        
        self.ast_nodes[node.uid] = node
        return node
    
    def _parse_class_decl(self, line_num: int) -> ASTNode:
        """解析类声明"""
        # class关键字已经被消费
        class_name_token = self._match_token(IbcTokenType.IDENTIFIER)
        
        # 解析继承关系
        self._match_token(IbcTokenType.LPAREN)
        
        inherit_info = ""
        # 收集继承信息直到右括号
        while self._peek_token().type != IbcTokenType.RPAREN:
            inherit_token = self._consume_token()
            inherit_info += inherit_token.value
            
        self._match_token(IbcTokenType.RPAREN)
        self._match_token(IbcTokenType.COLON)
        self._match_token(IbcTokenType.NEWLINE)
        
        node = ASTNode(
            uid=self._generate_node_uid(),
            node_type=NodeType.CLASS,
            line_number=line_num,
            identifier=class_name_token.value,
            content=inherit_info.strip()
        )
        
        self.ast_nodes[node.uid] = node
        return node
    
    def _parse_behavior_steps(self, parent_uid: str, indent_level: int) -> List[str]:
        """解析行为步骤"""
        child_uids = []
        
        while True:
            # 查看下一行的缩进级别
            next_indent_token = self._peek_token()
            if next_indent_token.type == IbcTokenType.INDENT_LEVEL:
                current_indent = int(next_indent_token.value)
                if current_indent < indent_level:
                    # 缩进减少，退出当前层级
                    break
                elif current_indent > indent_level:
                    # 更深的缩进，递归解析子节点
                    # 这里简化处理，实际应该递归调用相应的解析函数
                    pass
            elif next_indent_token.type in [IbcTokenType.EOF, IbcTokenType.KEYWORDS]:
                break
                
            # 解析当前行
            if next_indent_token.type == IbcTokenType.INDENT_LEVEL:
                self._consume_token()  # 消费缩进
                
            # 检查行首关键字
            first_token = self._peek_token()
            if first_token.type == IbcTokenType.KEYWORDS:
                # 新的声明，不是行为步骤
                break
            elif first_token.type == IbcTokenType.INTENT_COMMENT:
                self._consume_token()  # 消费@符号
                node = self._parse_intent_comment(first_token.line_num)
                node.parent_uid = parent_uid
                child_uids.append(node.uid)
            else:
                # 普通行为步骤
                content = self._collect_until_newline()
                if content.strip():  # 忽略空行
                    node = ASTNode(
                        uid=self._generate_node_uid(),
                        parent_uid=parent_uid,
                        node_type=NodeType.BEHAVIOR_STEP,
                        line_number=first_token.line_num,
                        content=content.strip()
                    )
                    self.ast_nodes[node.uid] = node
                    child_uids.append(node.uid)
            
            # 确保行结束
            self._match_optional_token(IbcTokenType.NEWLINE)
            
            # 检查是否还有更多行
            if self._peek_token().type == IbcTokenType.EOF:
                break
                
        return child_uids
    
    def parse(self) -> Dict[str, ASTNode]:
        """执行语法解析，返回AST节点字典"""
        # 首先进行词法分析
        self.tokens = self.lexer.tokenize()
        
        # 如果词法分析失败，返回空AST
        if not self.tokens:
            return {}
        
        # 解析顶层声明
        try:
            while self.current_token_index < len(self.tokens):
                token = self._peek_token()
                
                if token.type == IbcTokenType.EOF:
                    break
                    
                if token.type == IbcTokenType.KEYWORDS:
                    self._consume_token()  # 消费关键字
                    
                    if token.value == IbcKeywords.MODULE.value:
                        node = self._parse_module_decl(token.line_num)
                        
                    elif token.value == IbcKeywords.FUNC.value:
                        node = self._parse_func_decl(token.line_num)
                        # 解析函数体
                        func_indent_token = self._peek_token()
                        if func_indent_token.type == IbcTokenType.INDENT_LEVEL:
                            func_indent_level = int(func_indent_token.value)
                            child_uids = self._parse_behavior_steps(node.uid, func_indent_level)
                            node.children_uids.extend(child_uids)
                            
                    elif token.value == IbcKeywords.CLASS.value:
                        node = self._parse_class_decl(token.line_num)
                        # 解析类体
                        class_indent_token = self._peek_token()
                        if class_indent_token.type == IbcTokenType.INDENT_LEVEL:
                            class_indent_level = int(class_indent_token.value)
                            child_uids = self._parse_behavior_steps(node.uid, class_indent_level)
                            node.children_uids.extend(child_uids)
                            
                    elif token.value == IbcKeywords.VAR.value:
                        node = self._parse_var_decl(token.line_num)
                        
                    elif token.value == IbcKeywords.DESCRIPTION.value:
                        node = self._parse_description(token.line_num)
                        
                    else:
                        # 未知关键字，当作普通内容处理
                        self._collect_until_newline()
                        continue
                        
                elif token.type == IbcTokenType.INTENT_COMMENT:
                    self._consume_token()  # 消费@符号
                    node = self._parse_intent_comment(token.line_num)
                    
                elif token.type == IbcTokenType.INDENT_LEVEL:
                    # 缩进行，可能是函数或类体的内容
                    self._consume_token()
                    indent_level = int(token.value)
                    # 解析行为步骤
                    self._parse_behavior_steps("", indent_level)
                    
                elif token.type == IbcTokenType.NEWLINE:
                    self._consume_token()  # 消费换行
                    
                else:
                    # 其他内容，当作行为步骤处理
                    self._collect_until_newline()
                    
            return self.ast_nodes
            
        except ParseError as e:
            print(e)
            return {}
        except Exception as e:
            print(f"!!! Unexpected parsing error: {e}")
            return {}


def parse_ibc_code(text: str) -> Dict[str, Dict[str, Any]]:
    """解析IBC代码并返回AST字典"""
    parser = Parser(text)
    nodes = parser.parse()
    
    # 转换为字典格式
    result = {}
    for uid, node in nodes.items():
        result[uid] = node.to_dict()
    
    return result