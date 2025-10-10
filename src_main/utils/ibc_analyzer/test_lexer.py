import sys
import os

# 添加当前目录到路径，确保可以导入 lexer
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from lexer import Lexer, IbcTokenType, IbcKeywords, LexerError


def run_test(test_name, code, expected_tokens=None, should_fail=False, expect_empty=False):
    """运行单个测试用例"""
    print(f"\n{'='*60}")
    print(f"测试: {test_name}")
    print(f"{'='*60}")
    print("输入代码:")
    print(code)
    print("\n词法分析结果:")
    
    try:
        lexer = Lexer(code)
        tokens = lexer.tokenize()
        
        if expect_empty:
            if len(tokens) == 0:
                print("✅ 测试通过: 按预期返回空列表")
                return True
            else:
                print(f"❌ 测试失败: 预期返回空列表但实际返回了 {len(tokens)} 个token")
                return False
        
        if should_fail:
            print("❌ 测试失败: 预期会抛出异常但实际没有")
            return False
        
        # 打印所有token
        for i, token in enumerate(tokens):
            print(f"  {i:2d}: {token}")
        
        # 验证token序列（如果提供了预期值）
        if expected_tokens is not None:
            if len(tokens) != len(expected_tokens):
                print(f"❌ Token数量不匹配: 预期 {len(expected_tokens)}, 实际 {len(tokens)}")
                return False
            
            for i, (actual_token, expected_token) in enumerate(zip(tokens, expected_tokens)):
                expected_type, expected_value = expected_token
                if actual_token.type != expected_type or actual_token.value != expected_value:
                    print(f"❌ Token {i} 不匹配:")
                    print(f"   预期: Token({expected_type}, '{expected_value}', _)")
                    print(f"   实际: {actual_token}")
                    return False
        
        print("✅ 测试通过")
        return True
        
    except LexerError as e:
        if should_fail:
            print(f"✅ 测试通过: 按预期抛出异常 - {e}")
            return True
        else:
            print(f"❌ 测试失败: 意外异常 - {e}")
            return False
    except Exception as e:
        print(f"❌ 测试失败: 未知异常 - {e}")
        return False


def test_empty_file():
    """测试空文件"""
    expected = [
        (IbcTokenType.NEWLINE, 'NEWLINE'),
        (IbcTokenType.EOF, 'EOF')
    ]
    return run_test("空文件", "", expected_tokens=expected)


def test_comments_only():
    """测试只有注释的文件"""
    code = """// 这是一个注释
// 这是另一个注释
"""
    expected = [
        (IbcTokenType.NEWLINE, 'NEWLINE'),
        (IbcTokenType.EOF, 'EOF')
    ]
    return run_test("只有注释的文件", code, expected_tokens=expected)


def test_module_declaration():
    """测试模块声明"""
    code = """module requests: Python第三方HTTP请求库
module threading: 系统线程库
module utils"""
    expected = [
        (IbcTokenType.KEYWORDS, IbcKeywords.MODULE.value),
        (IbcTokenType.IDENTIFIER, 'requests'),
        (IbcTokenType.COLON, ':'),
        (IbcTokenType.IDENTIFIER, ' Python第三方HTTP请求库'),
        (IbcTokenType.NEWLINE, 'NEWLINE'),
        (IbcTokenType.KEYWORDS, IbcKeywords.MODULE.value),
        (IbcTokenType.IDENTIFIER, 'threading'),
        (IbcTokenType.COLON, ':'),
        (IbcTokenType.IDENTIFIER, ' 系统线程库'),
        (IbcTokenType.NEWLINE, 'NEWLINE'),
        (IbcTokenType.KEYWORDS, IbcKeywords.MODULE.value),
        (IbcTokenType.IDENTIFIER, 'utils'),
        (IbcTokenType.NEWLINE, 'NEWLINE'),
        (IbcTokenType.NEWLINE, 'NEWLINE'),
        (IbcTokenType.EOF, 'EOF')
    ]
    return run_test("模块声明", code, expected_tokens=expected)


def test_function_declaration():
    """测试函数声明"""
    code = """func 计算订单总价(商品列表: 包含价格信息的商品对象数组, 折扣率: 0到1之间的小数):
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
        (IbcTokenType.NEWLINE, 'NEWLINE'),
        (IbcTokenType.INDENT_LEVEL, '1'),
        (IbcTokenType.IDENTIFIER, '初始化 总价 = 0'),
        (IbcTokenType.NEWLINE, 'NEWLINE'),
        (IbcTokenType.NEWLINE, 'NEWLINE'),
        (IbcTokenType.EOF, 'EOF')
    ]
    return run_test("函数声明", code, expected_tokens=expected)


def test_class_declaration():
    """测试类声明"""
    code = """class UserManager(BaseManager: 使用公共基类管理生命周期):
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
        (IbcTokenType.NEWLINE, 'NEWLINE'),
        (IbcTokenType.INDENT_LEVEL, '1'),
        (IbcTokenType.KEYWORDS, IbcKeywords.VAR.value),
        (IbcTokenType.IDENTIFIER, 'users'),
        (IbcTokenType.COLON, ':'),
        (IbcTokenType.IDENTIFIER, ' 用户数据字典'),
        (IbcTokenType.NEWLINE, 'NEWLINE'),
        (IbcTokenType.NEWLINE, 'NEWLINE'),
        (IbcTokenType.EOF, 'EOF')
    ]
    return run_test("类声明", code, expected_tokens=expected)


def test_description_and_intent_comment():
    """测试描述和意图注释"""
    code = """description: 处理用户登录请求，验证凭据并返回认证结果
@ 线程安全设计，所有公共方法都内置锁机制
class AuthService():"""
    expected = [
        (IbcTokenType.KEYWORDS, IbcKeywords.DESCRIPTION.value),
        (IbcTokenType.COLON, ':'),
        (IbcTokenType.IDENTIFIER, ' 处理用户登录请求，验证凭据并返回认证结果'),
        (IbcTokenType.NEWLINE, 'NEWLINE'),
        (IbcTokenType.INTENT_COMMENT, '线程安全设计，所有公共方法都内置锁机制'),
        (IbcTokenType.NEWLINE, 'NEWLINE'),
        (IbcTokenType.KEYWORDS, IbcKeywords.CLASS.value),
        (IbcTokenType.IDENTIFIER, 'AuthService'),
        (IbcTokenType.LPAREN, '('),
        (IbcTokenType.RPAREN, ')'),
        (IbcTokenType.COLON, ':'),
        (IbcTokenType.NEWLINE, 'NEWLINE'),
        (IbcTokenType.NEWLINE, 'NEWLINE'),
        (IbcTokenType.EOF, 'EOF')
    ]
    return run_test("描述和意图注释", code, expected_tokens=expected)


def test_variable_declaration():
    """测试变量声明"""
    code = """var userCount: 当前在线用户数量
func test():
    var localVar: 局部变量"""
    expected = [
        (IbcTokenType.KEYWORDS, IbcKeywords.VAR.value),
        (IbcTokenType.IDENTIFIER, 'userCount'),
        (IbcTokenType.COLON, ':'),
        (IbcTokenType.IDENTIFIER, ' 当前在线用户数量'),
        (IbcTokenType.NEWLINE, 'NEWLINE'),
        (IbcTokenType.KEYWORDS, IbcKeywords.FUNC.value),
        (IbcTokenType.IDENTIFIER, 'test'),
        (IbcTokenType.LPAREN, '('),
        (IbcTokenType.RPAREN, ')'),
        (IbcTokenType.COLON, ':'),
        (IbcTokenType.NEWLINE, 'NEWLINE'),
        (IbcTokenType.INDENT_LEVEL, '1'),
        (IbcTokenType.KEYWORDS, IbcKeywords.VAR.value),
        (IbcTokenType.IDENTIFIER, 'localVar'),
        (IbcTokenType.COLON, ':'),
        (IbcTokenType.IDENTIFIER, ' 局部变量'),
        (IbcTokenType.NEWLINE, 'NEWLINE'),
        (IbcTokenType.NEWLINE, 'NEWLINE'),
        (IbcTokenType.EOF, 'EOF')
    ]
    return run_test("变量声明", code, expected_tokens=expected)


def test_symbol_reference():
    """测试符号引用"""
    code = """func 发送请求(请求数据):
    当 重试计数 < $maxRetries$:"""
    expected = [
        (IbcTokenType.KEYWORDS, IbcKeywords.FUNC.value),
        (IbcTokenType.IDENTIFIER, '发送请求'),
        (IbcTokenType.LPAREN, '('),
        (IbcTokenType.IDENTIFIER, '请求数据'),
        (IbcTokenType.RPAREN, ')'),
        (IbcTokenType.COLON, ':'),
        (IbcTokenType.NEWLINE, 'NEWLINE'),
        (IbcTokenType.INDENT_LEVEL, '1'),
        (IbcTokenType.IDENTIFIER, '当 重试计数 < '),
        (IbcTokenType.REF_IDENTIFIER, 'maxRetries'),
        (IbcTokenType.COLON, ':'),
        (IbcTokenType.NEWLINE, 'NEWLINE'),
        (IbcTokenType.NEWLINE, 'NEWLINE'),
        (IbcTokenType.EOF, 'EOF')
    ]
    return run_test("符号引用", code, expected_tokens=expected)


def test_multiple_symbol_references():
    """测试多个符号引用"""
    code = """func test():
    $httpClient.post$(请求数据)
    $记录错误$("配置加载失败: " + 异常信息)"""
    expected = [
        (IbcTokenType.KEYWORDS, IbcKeywords.FUNC.value),
        (IbcTokenType.IDENTIFIER, 'test'),
        (IbcTokenType.LPAREN, '('),
        (IbcTokenType.RPAREN, ')'),
        (IbcTokenType.COLON, ':'),
        (IbcTokenType.NEWLINE, 'NEWLINE'),
        (IbcTokenType.INDENT_LEVEL, '1'),
        (IbcTokenType.REF_IDENTIFIER, 'httpClient.post'),
        (IbcTokenType.LPAREN, '('),
        (IbcTokenType.IDENTIFIER, '请求数据'),
        (IbcTokenType.RPAREN, ')'),
        (IbcTokenType.NEWLINE, 'NEWLINE'),
        (IbcTokenType.INDENT_LEVEL, '1'),
        (IbcTokenType.REF_IDENTIFIER, '记录错误'),
        (IbcTokenType.LPAREN, '('),
        (IbcTokenType.IDENTIFIER, '"配置加载失败'),
        (IbcTokenType.COLON, ':'),
        (IbcTokenType.IDENTIFIER, ' " + 异常信息'),
        (IbcTokenType.RPAREN, ')'),
        (IbcTokenType.NEWLINE, 'NEWLINE'),
        (IbcTokenType.NEWLINE, 'NEWLINE'),
        (IbcTokenType.EOF, 'EOF')
    ]
    return run_test("多个符号引用", code, expected_tokens=expected)


def test_error_cases():
    """测试错误情况"""
    
    print(f"\n{'='*60}")
    print("测试错误情况")
    print(f"{'='*60}")
    
    # 测试1: 不成对的$符号
    code1 = """func test():
    var ref = $unclosed_ref"""
    print("\n1. 测试不成对的$符号:")
    result1 = run_test("不成对的$符号", code1, expect_empty=True)
    
    # 测试2: Tab缩进
    code2 = """func test():
\tvar tab_indented"""
    print("\n2. 测试Tab缩进:")
    result2 = run_test("Tab缩进", code2, expect_empty=True)
    
    # 测试3: 缩进不是4的倍数
    code3 = """func test():
 var invalid_indent"""
    print("\n3. 测试缩进不是4的倍数:")
    result3 = run_test("缩进不是4的倍数", code3, expect_empty=True)
    
    # 测试4: 空的符号引用
    code4 = """func test():
    var ref = $$"""
    print("\n4. 测试空的符号引用:")
    result4 = run_test("空的符号引用", code4, expect_empty=False)  # 这种情况只是警告，不会返回空列表
    
    return result1 and result2 and result3 and result4


def main():
    """运行所有测试"""
    print("开始测试 Intent Behavior Code 词法分析器")
    print("=" * 60)
    
    test_results = []
    
    # 运行所有测试用例
    test_results.append(("空文件", test_empty_file()))
    test_results.append(("只有注释", test_comments_only()))
    test_results.append(("模块声明", test_module_declaration()))
    test_results.append(("函数声明", test_function_declaration()))
    test_results.append(("类声明", test_class_declaration()))
    test_results.append(("描述和意图注释", test_description_and_intent_comment()))
    test_results.append(("变量声明", test_variable_declaration()))
    test_results.append(("符号引用", test_symbol_reference()))
    test_results.append(("多个符号引用", test_multiple_symbol_references()))
    
    # 错误情况测试
    error_result = test_error_cases()
    test_results.append(("错误情况", error_result))
    
    # 统计结果
    print(f"\n{'='*60}")
    print("测试结果汇总")
    print(f"{'='*60}")
    
    passed = 0
    failed = 0
    
    for test_name, result in test_results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{test_name:20} {status}")
        if result:
            passed += 1
        else:
            failed += 1
    
    print(f"\n总计: {passed} 通过, {failed} 失败")
    
    if failed == 0:
        print("🎉 所有测试通过！")
    else:
        print(f"⚠️  有 {failed} 个测试失败")
    
    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)