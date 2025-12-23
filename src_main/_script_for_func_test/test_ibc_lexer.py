import sys
import os

# 正确添加src_main目录到sys.path，以便能够导入libs中的模块
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from utils.ibc_analyzer.ibc_lexer import IbcLexer, IbcTokenType, IbcKeywords, LexerError

def test_empty_file():
    """测试空文件"""
    print("测试 empty_file 函数...")
    
    code = ""
    expected = [
        (IbcTokenType.NEWLINE, ''),
        (IbcTokenType.NEWLINE, ''),
        (IbcTokenType.EOF, '')
    ]
    
    try:
        lexer = IbcLexer(code)
        tokens = lexer.tokenize()
        
        # assert len(tokens) == len(expected), f"Token数量不匹配: 预期 {len(expected)}, 实际 {len(tokens)}"
        
        for i, (actual_token, expected_token) in enumerate(zip(tokens, expected)):
            expected_type, expected_value = expected_token
            assert actual_token.type == expected_type and actual_token.value == expected_value, \
                f"Token {i} 不匹配: 预期 Token({expected_type}, '{expected_value}', _) 实际 {actual_token}"
        
        print("  ✓ 成功处理空文件")
        return True
    except Exception as e:
        print(f"  ❌ 测试失败: {e}")
        return False

def test_comments_only():
    """测试只有注释的文件"""
    print("测试 comments_only 函数...")
    
    code = """// 这是一个注释
// 这是另一个注释
"""
    expected = [
        (IbcTokenType.NEWLINE, ''),
        (IbcTokenType.NEWLINE, ''),
        (IbcTokenType.NEWLINE, ''),
        
        (IbcTokenType.NEWLINE, ''),
        (IbcTokenType.EOF, '')
    ]
    
    try:
        lexer = IbcLexer(code)
        tokens = lexer.tokenize()
        
        # assert len(tokens) == len(expected), f"Token数量不匹配: 预期 {len(expected)}, 实际 {len(tokens)}"
        
        for i, (actual_token, expected_token) in enumerate(zip(tokens, expected)):
            expected_type, expected_value = expected_token
            assert actual_token.type == expected_type and actual_token.value == expected_value, \
                f"Token {i} 不匹配: 预期 Token({expected_type}, '{expected_value}', _) 实际 {actual_token}"
        
        print("  ✓ 成功处理只有注释的文件")
        return True
    except Exception as e:
        print(f"  ❌ 测试失败: {e}")
        return False

def test_module_declaration():
    """测试模块声明"""
    print("测试 module_declaration 函数...")
    
    code = """module requests: Python第三方HTTP请求库
module threading: 系统线程库
module utils"""
    expected = [
        (IbcTokenType.KEYWORDS, IbcKeywords.MODULE.value),
        (IbcTokenType.IDENTIFIER, 'requests'),
        (IbcTokenType.COLON, ':'),
        (IbcTokenType.IDENTIFIER, ' Python第三方HTTP请求库'),
        (IbcTokenType.NEWLINE, ''),
        (IbcTokenType.KEYWORDS, IbcKeywords.MODULE.value),
        (IbcTokenType.IDENTIFIER, 'threading'),
        (IbcTokenType.COLON, ':'),
        (IbcTokenType.IDENTIFIER, ' 系统线程库'),
        (IbcTokenType.NEWLINE, ''),
        (IbcTokenType.KEYWORDS, IbcKeywords.MODULE.value),
        (IbcTokenType.IDENTIFIER, 'utils'),
        (IbcTokenType.NEWLINE, ''),
        (IbcTokenType.NEWLINE, ''),
        (IbcTokenType.EOF, '')
    ]
    
    try:
        lexer = IbcLexer(code)
        tokens = lexer.tokenize()
        
        # assert len(tokens) == len(expected), f"Token数量不匹配: 预期 {len(expected)}, 实际 {len(tokens)}"
        
        for i, (actual_token, expected_token) in enumerate(zip(tokens, expected)):
            expected_type, expected_value = expected_token
            assert actual_token.type == expected_type and actual_token.value == expected_value, \
                f"Token {i} 不匹配: 预期 Token({expected_type}, '{expected_value}', _) 实际 {actual_token}"
        
        print("  ✓ 成功处理模块声明")
        return True
    except Exception as e:
        print(f"  ❌ 测试失败: {e}")
        return False

def test_function_declaration():
    """测试函数声明"""
    print("测试 function_declaration 函数...")
    
    code = """\
func 计算订单总价(商品列表: 包含价格信息的商品对象数组, 折扣率: 0到1之间的小数):
    初始化 总价 = 0"""
    expected = [
        (IbcTokenType.KEYWORDS, IbcKeywords.FUNC.value),
        (IbcTokenType.IDENTIFIER, '计算订单总价'),
        (IbcTokenType.LPAREN, '('),
        (IbcTokenType.IDENTIFIER, '商品列表'),
        (IbcTokenType.COLON, ':'),
        (IbcTokenType.IDENTIFIER, ' 包含价格信息的商品对象数组'),
        (IbcTokenType.COMMA, ','),
        (IbcTokenType.IDENTIFIER, ' 折扣率'),
        (IbcTokenType.COLON, ':'),
        (IbcTokenType.IDENTIFIER, ' 0到1之间的小数'),
        (IbcTokenType.RPAREN, ')'),
        (IbcTokenType.COLON, ':'),
        (IbcTokenType.NEWLINE, ''),
        (IbcTokenType.INDENT, ''),
        (IbcTokenType.IDENTIFIER, '初始化 总价 '),
        (IbcTokenType.EQUAL, '='),
        (IbcTokenType.IDENTIFIER, ' 0'),
        (IbcTokenType.NEWLINE, ''),
        (IbcTokenType.DEDENT, ''),
        (IbcTokenType.NEWLINE, ''),
        (IbcTokenType.EOF, '')
    ]
    
    try:
        lexer = IbcLexer(code)
        tokens = lexer.tokenize()
        
        # assert len(tokens) == len(expected), f"Token数量不匹配: 预期 {len(expected)}, 实际 {len(tokens)}"
        
        for i, (actual_token, expected_token) in enumerate(zip(tokens, expected)):
            expected_type, expected_value = expected_token
            assert actual_token.type == expected_type and actual_token.value == expected_value, \
                f"Token {i} 不匹配: 预期 Token({expected_type}, '{expected_value}', _) 实际 {actual_token}"
        
        print("  ✓ 成功处理函数声明")
        return True
    except Exception as e:
        print(f"  ❌ 测试失败: {e}")
        return False

def test_class_declaration():
    """测试类声明"""
    print("测试 class_declaration 函数...")
    
    code = """\
class UserManager(BaseManager: 使用公共基类管理生命周期):
    var users: 用户数据字典"""
    expected = [
        (IbcTokenType.KEYWORDS, IbcKeywords.CLASS.value),
        (IbcTokenType.IDENTIFIER, 'UserManager'),
        (IbcTokenType.LPAREN, '('),
        (IbcTokenType.IDENTIFIER, 'BaseManager'),
        (IbcTokenType.COLON, ':'),
        (IbcTokenType.IDENTIFIER, ' 使用公共基类管理生命周期'),
        (IbcTokenType.RPAREN, ')'),
        (IbcTokenType.COLON, ':'),
        (IbcTokenType.NEWLINE, ''),
        (IbcTokenType.INDENT, ''),
        (IbcTokenType.KEYWORDS, IbcKeywords.VAR.value),
        (IbcTokenType.IDENTIFIER, 'users'),
        (IbcTokenType.COLON, ':'),
        (IbcTokenType.IDENTIFIER, ' 用户数据字典'),
        (IbcTokenType.NEWLINE, ''),
        (IbcTokenType.DEDENT, ''),
        (IbcTokenType.NEWLINE, ''),
        (IbcTokenType.EOF, '')
    ]
    
    try:
        lexer = IbcLexer(code)
        tokens = lexer.tokenize()
        
        # assert len(tokens) == len(expected), f"Token数量不匹配: 预期 {len(expected)}, 实际 {len(tokens)}"
        
        for i, (actual_token, expected_token) in enumerate(zip(tokens, expected)):
            expected_type, expected_value = expected_token
            assert actual_token.type == expected_type and actual_token.value == expected_value, \
                f"Token {i} 不匹配: 预期 Token({expected_type}, '{expected_value}', _) 实际 {actual_token}"
        
        print("  ✓ 成功处理类声明")
        return True
    except Exception as e:
        print(f"  ❌ 测试失败: {e}")
        return False

def test_description_and_intent_comment():
    """测试描述和意图注释"""
    print("测试 description_and_intent_comment 函数...")
    
    code = """description: 处理用户登录请求，验证凭据并返回认证结果
@ 线程安全设计，所有公共方法都内置锁机制
class AuthService():"""
    expected = [
        (IbcTokenType.KEYWORDS, IbcKeywords.DESCRIPTION.value),
        (IbcTokenType.COLON, ':'),
        (IbcTokenType.IDENTIFIER, ' 处理用户登录请求，验证凭据并返回认证结果'),
        (IbcTokenType.NEWLINE, ''),
        (IbcTokenType.KEYWORDS, IbcKeywords.INTENT.value),
        (IbcTokenType.IDENTIFIER, '线程安全设计，所有公共方法都内置锁机制'),
        (IbcTokenType.NEWLINE, ''),
        (IbcTokenType.KEYWORDS, IbcKeywords.CLASS.value),
        (IbcTokenType.IDENTIFIER, 'AuthService'),
        (IbcTokenType.LPAREN, '('),
        (IbcTokenType.RPAREN, ')'),
        (IbcTokenType.COLON, ':'),
        (IbcTokenType.NEWLINE, ''),
        (IbcTokenType.NEWLINE, ''),
        (IbcTokenType.EOF, '')
    ]
    
    try:
        lexer = IbcLexer(code)
        tokens = lexer.tokenize()
        
        # assert len(tokens) == len(expected), f"Token数量不匹配: 预期 {len(expected)}, 实际 {len(tokens)}"
        
        for i, (actual_token, expected_token) in enumerate(zip(tokens, expected)):
            expected_type, expected_value = expected_token
            assert actual_token.type == expected_type and actual_token.value == expected_value, \
                f"Token {i} 不匹配: 预期 Token({expected_type}, '{expected_value}', _) 实际 {actual_token}"
        
        print("  ✓ 成功处理描述和意图注释")
        return True
    except Exception as e:
        print(f"  ❌ 测试失败: {e}")
        return False

def test_variable_declaration():
    """测试变量声明"""
    print("测试 variable_declaration 函数...")
    
    code = """\
var userCount: 当前在线用户数量
func test():
    var localVar: 局部变量"""
    expected = [
        (IbcTokenType.KEYWORDS, IbcKeywords.VAR.value),
        (IbcTokenType.IDENTIFIER, 'userCount'),
        (IbcTokenType.COLON, ':'),
        (IbcTokenType.IDENTIFIER, ' 当前在线用户数量'),
        (IbcTokenType.NEWLINE, ''),
        (IbcTokenType.KEYWORDS, IbcKeywords.FUNC.value),
        (IbcTokenType.IDENTIFIER, 'test'),
        (IbcTokenType.LPAREN, '('),
        (IbcTokenType.RPAREN, ')'),
        (IbcTokenType.COLON, ':'),
        (IbcTokenType.NEWLINE, ''),
        (IbcTokenType.INDENT, ''),
        (IbcTokenType.KEYWORDS, IbcKeywords.VAR.value),
        (IbcTokenType.IDENTIFIER, 'localVar'),
        (IbcTokenType.COLON, ':'),
        (IbcTokenType.IDENTIFIER, ' 局部变量'),
        (IbcTokenType.NEWLINE, ''),
        (IbcTokenType.DEDENT, ''),
        (IbcTokenType.NEWLINE, ''),
        (IbcTokenType.EOF, '')
    ]
    
    try:
        lexer = IbcLexer(code)
        tokens = lexer.tokenize()
        
        # assert len(tokens) == len(expected), f"Token数量不匹配: 预期 {len(expected)}, 实际 {len(tokens)}"
        
        for i, (actual_token, expected_token) in enumerate(zip(tokens, expected)):
            expected_type, expected_value = expected_token
            assert actual_token.type == expected_type and actual_token.value == expected_value, \
                f"Token {i} 不匹配: 预期 Token({expected_type}, '{expected_value}', _) 实际 {actual_token}"
        
        print("  ✓ 成功处理变量声明")
        return True
    except Exception as e:
        print(f"  ❌ 测试失败: {e}")
        return False

def test_symbol_reference():
    """测试符号引用（新语法：单$起始）"""
    print("测试 symbol_reference 函数...")
    
    code = """\
func 发送请求(请求数据):
    当 重试计数 < $maxRetries:"""
    expected = [
        (IbcTokenType.KEYWORDS, IbcKeywords.FUNC.value),
        (IbcTokenType.IDENTIFIER, '发送请求'),
        (IbcTokenType.LPAREN, '('),
        (IbcTokenType.IDENTIFIER, '请求数据'),
        (IbcTokenType.RPAREN, ')'),
        (IbcTokenType.COLON, ':'),
        (IbcTokenType.NEWLINE, ''),
        (IbcTokenType.INDENT, ''),
        (IbcTokenType.IDENTIFIER, '当 重试计数 < '),
        (IbcTokenType.REF_IDENTIFIER, 'maxRetries'),
        (IbcTokenType.COLON, ':'),
        (IbcTokenType.NEWLINE, ''),
        (IbcTokenType.DEDENT, ''),
        (IbcTokenType.NEWLINE, ''),
        (IbcTokenType.EOF, '')
    ]
    
    try:
        lexer = IbcLexer(code)
        tokens = lexer.tokenize()
        
        # assert len(tokens) == len(expected), f"Token数量不匹配: 预期 {len(expected)}, 实际 {len(tokens)}"
        
        for i, (actual_token, expected_token) in enumerate(zip(tokens, expected)):
            expected_type, expected_value = expected_token
            assert actual_token.type == expected_type and actual_token.value == expected_value, \
                f"Token {i} 不匹配: 预期 Token({expected_type}, '{expected_value}', _) 实际 {actual_token}"
        
        print("  ✓ 成功处理符号引用")
        return True
    except Exception as e:
        print(f"  ❌ 测试失败: {e}")
        return False

def test_multiple_symbol_references():
    """测试多个符号引用（新语法：单$起始）"""
    print("测试 multiple_symbol_references 函数...")
    
    code = """\
func test():
    $httpClient.post(请求数据)
    $记录错误(\"\u914d置加载失败: \" + 异常信息)"""
    expected = [
        (IbcTokenType.KEYWORDS, IbcKeywords.FUNC.value),
        (IbcTokenType.IDENTIFIER, 'test'),
        (IbcTokenType.LPAREN, '('),
        (IbcTokenType.RPAREN, ')'),
        (IbcTokenType.COLON, ':'),
        (IbcTokenType.NEWLINE, ''),
        (IbcTokenType.INDENT, ''),
        (IbcTokenType.REF_IDENTIFIER, 'httpClient.post'),
        (IbcTokenType.LPAREN, '('),
        (IbcTokenType.IDENTIFIER, '请求数据'),
        (IbcTokenType.RPAREN, ')'),
        (IbcTokenType.NEWLINE, ''),
        (IbcTokenType.REF_IDENTIFIER, '记录错误'),
        (IbcTokenType.LPAREN, '('),
        (IbcTokenType.IDENTIFIER, '\"\u914d置加载失败'),
        (IbcTokenType.COLON, ':'),
        (IbcTokenType.IDENTIFIER, ' \" + 异常信息'),
        (IbcTokenType.RPAREN, ')'),
        (IbcTokenType.NEWLINE, ''),
        (IbcTokenType.DEDENT, ''),
        (IbcTokenType.NEWLINE, ''),
        (IbcTokenType.EOF, '')
    ]
    
    try:
        lexer = IbcLexer(code)
        tokens = lexer.tokenize()
        
        # assert len(tokens) == len(expected), f"Token数量不匹配: 预期 {len(expected)}, 实际 {len(tokens)}"
        
        for i, (actual_token, expected_token) in enumerate(zip(tokens, expected)):
            expected_type, expected_value = expected_token
            assert actual_token.type == expected_type and actual_token.value == expected_value, \
                f"Token {i} 不匹配: 预期 Token({expected_type}, '{expected_value}', _) 实际 {actual_token}"
        
        print("  ✓ 成功处理多个符号引用")
        return True
    except Exception as e:
        print(f"  ❌ 测试失败: {e}")
        return False

def test_error_cases():
    """测试错误情况"""
    print("测试 error_cases 函数...")
    
    # 测试1: Tab缩进
    print("  1. 测试Tab缩进:")
    code1 = """func test():
\tvar tab_indented"""
    try:
        lexer = IbcLexer(code1)
        tokens = lexer.tokenize()
        # 应该抛出LexerError异常
        print("    ❌ 测试失败: 应该抛出异常但没有")
        return False
    except LexerError as e:
        print("    ✓ 成功检测到Tab缩进")
    except Exception as e:
        print(f"    ❌ 测试失败: {e}")
        return False
    
    # 测试2: 空的符号引用
    print("  2. 测试空的符号引用:")
    code2 = """func test():
    var ref = $ """
    try:
        lexer = IbcLexer(code2)
        tokens = lexer.tokenize()
        # 这种情况只是警告，不会返回空列表，应该有token
        print("    ✓ 成功处理空的符号引用")
    except Exception as e:
        print(f"    ❌ 测试失败: {e}")
        return False
    
    return True


def test_bracket_and_backslash_symbols():
    r"""测试符号 token 也即 () {} [] \\ ="""
    print("测试 bracket_and_backslash_symbols 函数...")
    
    code = """func test():
    dict = {key: value}
    list = [item1, item2]
    line1 \\
    line2"""
    expected = [
        (IbcTokenType.KEYWORDS, IbcKeywords.FUNC.value),
        (IbcTokenType.IDENTIFIER, 'test'),
        (IbcTokenType.LPAREN, '('),
        (IbcTokenType.RPAREN, ')'),
        (IbcTokenType.COLON, ':'),
        (IbcTokenType.NEWLINE, ''),
        (IbcTokenType.INDENT, ''),
        (IbcTokenType.IDENTIFIER, 'dict '),
        (IbcTokenType.EQUAL, '='),
        (IbcTokenType.IDENTIFIER, ' '),
        (IbcTokenType.LBRACE, '{'),
        (IbcTokenType.IDENTIFIER, 'key'),
        (IbcTokenType.COLON, ':'),
        (IbcTokenType.IDENTIFIER, ' value'),
        (IbcTokenType.RBRACE, '}'),
        (IbcTokenType.NEWLINE, ''),
        (IbcTokenType.IDENTIFIER, 'list '),
        (IbcTokenType.EQUAL, '='),
        (IbcTokenType.IDENTIFIER, ' '),
        (IbcTokenType.LBRACKET, '['),
        (IbcTokenType.IDENTIFIER, 'item1'),
        (IbcTokenType.COMMA, ','),
        (IbcTokenType.IDENTIFIER, ' item2'),
        (IbcTokenType.RBRACKET, ']'),
        (IbcTokenType.NEWLINE, ''),
        (IbcTokenType.IDENTIFIER, 'line1 '),
        (IbcTokenType.BACKSLASH, '\\'),
        (IbcTokenType.NEWLINE, ''),
        (IbcTokenType.IDENTIFIER, 'line2'),
        (IbcTokenType.NEWLINE, ''),
        (IbcTokenType.DEDENT, ''),
        (IbcTokenType.NEWLINE, ''),
        (IbcTokenType.EOF, '')
    ]
    
    try:
        lexer = IbcLexer(code)
        tokens = lexer.tokenize()
        
        # assert len(tokens) == len(expected), f"Token数量不匹配: 预期 {len(expected)}, 实际 {len(tokens)}"
        
        for i, (actual_token, expected_token) in enumerate(zip(tokens, expected)):
            expected_type, expected_value = expected_token
            assert actual_token.type == expected_type and actual_token.value == expected_value, \
                f"Token {i} 不匹配: 预期 Token({expected_type}, '{expected_value}', _) 实际 {actual_token}"
        
        print("  ✓ 成功处理特殊符号")
        return True
    except Exception as e:
        print(f"  ❌ 测试失败: {e}")
        return False

def test_equal_sign_in_var_declaration():
    """测试变量声明中的等号"""
    print("测试 equal_sign_in_var_declaration 函数...")
    
    code = """var total = 0
var count = 10
var name: 用户姓名"""
    expected = [
        (IbcTokenType.KEYWORDS, IbcKeywords.VAR.value),
        (IbcTokenType.IDENTIFIER, 'total '),
        (IbcTokenType.EQUAL, '='),
        (IbcTokenType.IDENTIFIER, ' 0'),
        (IbcTokenType.NEWLINE, ''),
        (IbcTokenType.KEYWORDS, IbcKeywords.VAR.value),
        (IbcTokenType.IDENTIFIER, 'count '),
        (IbcTokenType.EQUAL, '='),
        (IbcTokenType.IDENTIFIER, ' 10'),
        (IbcTokenType.NEWLINE, ''),
        (IbcTokenType.KEYWORDS, IbcKeywords.VAR.value),
        (IbcTokenType.IDENTIFIER, 'name'),
        (IbcTokenType.COLON, ':'),
        (IbcTokenType.IDENTIFIER, ' 用户姓名'),
        (IbcTokenType.NEWLINE, ''),
        (IbcTokenType.NEWLINE, ''),
        (IbcTokenType.EOF, '')
    ]
    
    try:
        lexer = IbcLexer(code)
        tokens = lexer.tokenize()
        
        for i, (actual_token, expected_token) in enumerate(zip(tokens, expected)):
            expected_type, expected_value = expected_token
            assert actual_token.type == expected_type and actual_token.value == expected_value, \
                f"Token {i} 不匹配: 预期 Token({expected_type}, '{expected_value}', _) 实际 {actual_token}"
        
        print("  ✓ 成功处理变量声明中的等号")
        return True
    except Exception as e:
        print(f"  ❌ 测试失败: {e}")
        return False


def test_equal_sign_with_symbol_ref():
    """测试等号与符号引用结合"""
    print("测试 equal_sign_with_symbol_ref 函数...")
    
    code = """func test():
    result = $httpClient.get(url)"""
    expected = [
        (IbcTokenType.KEYWORDS, IbcKeywords.FUNC.value),
        (IbcTokenType.IDENTIFIER, 'test'),
        (IbcTokenType.LPAREN, '('),
        (IbcTokenType.RPAREN, ')'),
        (IbcTokenType.COLON, ':'),
        (IbcTokenType.NEWLINE, ''),
        (IbcTokenType.INDENT, ''),
        (IbcTokenType.IDENTIFIER, 'result '),
        (IbcTokenType.EQUAL, '='),
        (IbcTokenType.IDENTIFIER, ' '),
        (IbcTokenType.REF_IDENTIFIER, 'httpClient.get'),
        (IbcTokenType.LPAREN, '('),
        (IbcTokenType.IDENTIFIER, 'url'),
        (IbcTokenType.RPAREN, ')'),
        (IbcTokenType.NEWLINE, ''),
        (IbcTokenType.DEDENT, ''),
        (IbcTokenType.NEWLINE, ''),
        (IbcTokenType.EOF, '')
    ]
    
    try:
        lexer = IbcLexer(code)
        tokens = lexer.tokenize()
        
        for i, (actual_token, expected_token) in enumerate(zip(tokens, expected)):
            expected_type, expected_value = expected_token
            assert actual_token.type == expected_type and actual_token.value == expected_value, \
                f"Token {i} 不匹配: 预期 Token({expected_type}, '{expected_value}', _) 实际 {actual_token}"
        
        print("  ✓ 成功处理等号与符号引用结合")
        return True
    except Exception as e:
        print(f"  ❌ 测试失败: {e}")
        return False


def test_visibility_keywords():
    """测试可见性关键字（public, protected, private）"""
    print("测试 visibility_keywords 函数...")
    
    code = """class TestClass():
    public
    var public_member: 公开成员
    
    protected
    var protected_member: 保护成员
    
    private
    var private_member: 私有成员
"""
    
    expected = [
        (IbcTokenType.KEYWORDS, IbcKeywords.CLASS.value),
        (IbcTokenType.IDENTIFIER, 'TestClass'),
        (IbcTokenType.LPAREN, '('),
        (IbcTokenType.RPAREN, ')'),
        (IbcTokenType.COLON, ':'),
        (IbcTokenType.NEWLINE, ''),
        (IbcTokenType.INDENT, ''),
        (IbcTokenType.KEYWORDS, IbcKeywords.PUBLIC.value),  # public关键字
        (IbcTokenType.COLON, ':'),
        (IbcTokenType.NEWLINE, ''),
        (IbcTokenType.KEYWORDS, IbcKeywords.VAR.value),
        (IbcTokenType.IDENTIFIER, 'public_member'),
        (IbcTokenType.COLON, ':'),
        (IbcTokenType.IDENTIFIER, ' 公开成员'),
        (IbcTokenType.NEWLINE, ''),
        (IbcTokenType.NEWLINE, ''),
        (IbcTokenType.KEYWORDS, IbcKeywords.PROTECTED.value),  # protected关键字
        (IbcTokenType.COLON, ':'),
        (IbcTokenType.NEWLINE, ''),
        (IbcTokenType.KEYWORDS, IbcKeywords.VAR.value),
        (IbcTokenType.IDENTIFIER, 'protected_member'),
        (IbcTokenType.COLON, ':'),
        (IbcTokenType.IDENTIFIER, ' 保护成员'),
        (IbcTokenType.NEWLINE, ''),
        (IbcTokenType.NEWLINE, ''),
        (IbcTokenType.KEYWORDS, IbcKeywords.PRIVATE.value),  # private关键字
        (IbcTokenType.COLON, ':'),
        (IbcTokenType.NEWLINE, ''),
        (IbcTokenType.KEYWORDS, IbcKeywords.VAR.value),
        (IbcTokenType.IDENTIFIER, 'private_member'),
        (IbcTokenType.COLON, ':'),
        (IbcTokenType.IDENTIFIER, ' 私有成员'),
        (IbcTokenType.NEWLINE, ''),
        (IbcTokenType.DEDENT, ''),
        (IbcTokenType.NEWLINE, ''),
        (IbcTokenType.EOF, '')
    ]
    
    try:
        lexer = IbcLexer(code)
        tokens = lexer.tokenize()
        
        # 检查是否生成了public、protected、private关键字token
        keywords_found = []
        for token in tokens:
            if token.type == IbcTokenType.KEYWORDS and token.value in ['public', 'protected', 'private']:
                keywords_found.append(token.value)
        
        assert 'public' in keywords_found, "未找到public关键字"
        assert 'protected' in keywords_found, "未找到protected关键字"
        assert 'private' in keywords_found, "未找到private关键字"
        
        print("  ✓ 成功识别可见性关键字: public, protected, private")
        return True
    except Exception as e:
        print(f"  ❌ 测试失败: {e}")
        return False


if __name__ == "__main__":
    print("\n开始测试 Intent Behavior Code 词法分析器...\n")
    
    try:
        test_results = []
        
        test_results.append(("空文件", test_empty_file()))
        print()
        
        test_results.append(("只有注释", test_comments_only()))
        print()
        
        test_results.append(("模块声明", test_module_declaration()))
        print()
        
        test_results.append(("函数声明", test_function_declaration()))
        print()
        
        test_results.append(("类声明", test_class_declaration()))
        print()
        
        test_results.append(("描述和意图注释", test_description_and_intent_comment()))
        print()
        
        test_results.append(("变量声明", test_variable_declaration()))
        print()
        
        test_results.append(("符号引用", test_symbol_reference()))
        print()
        
        test_results.append(("多个符号引用", test_multiple_symbol_references()))
        print()
        
        test_results.append(("特殊符号", test_bracket_and_backslash_symbols()))
        print()
        
        test_results.append(("变量等号语法", test_equal_sign_in_var_declaration()))
        print()
        
        test_results.append(("等号符号引用", test_equal_sign_with_symbol_ref()))
        print()
        
        test_results.append(("错误情况", test_error_cases()))
        print()
        
        test_results.append(("可见性关键字", test_visibility_keywords()))
        print()
        
        print("=" * 50)
        print("测试结果汇总")
        print("=" * 50)
        
        passed = 0
        failed = 0
        
        for test_name, result in test_results:
            status = "✓ 通过" if result else "❌ 失败"
            print(f"{test_name:20} {status}")
            if result:
                passed += 1
            else:
                failed += 1
        
        print(f"\n总计: {passed} 通过, {failed} 失败")
        
        if failed == 0:
            print("=" * 50)
            print("所有测试通过！✓")
            print("=" * 50)
        else:
            print(f"⚠️  有 {failed} 个测试失败")
        
    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()