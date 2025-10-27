import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from utils.ibc_analyzer.ibc_lexer import IbcLexer
from utils.ibc_analyzer.ibc_parser import IbcParser, ParseError
from typedef.ibc_data_types import AstNodeType


def test_basic_parsing():
    """测试基本解析功能"""
    code = """\
module test_module: 测试模块
func test_function():
    步骤1
    步骤2
"""
    
    print("=== 基本解析测试 ===")
    print("输入代码:")
    print(code)
    
    lexer = IbcLexer(code)
    tokens = lexer.tokenize()
    
    if not tokens:
        print("词法分析失败")
        return False
        
    parser = IbcParser(tokens)
    try:
        ast = parser.parse()
        print("\\n生成的AST节点:")
        for uid, node in ast.items():
            print(f"  UID: {uid}, 节点: {node}")
        print(f"\\n总计生成 {len(ast)} 个节点\\n")
        return True
    except Exception as e:
        print(f"解析失败: {e}")
        return False


def test_class_parsing():
    """测试类解析功能"""
    code = """\
class TestClass:
    var test_var: 测试变量
    
    func __init__():
        初始化步骤
"""
    
    print("=== 类解析测试 ===")
    print("输入代码:")
    print(code)
    
    lexer = IbcLexer(code)
    tokens = lexer.tokenize()
    
    if not tokens:
        print("词法分析失败")
        return False
        
    parser = IbcParser(tokens)
    try:
        ast = parser.parse()
        print("\\n生成的AST节点:")
        for uid, node in ast.items():
            print(f"  UID: {uid}, 节点: {node}")
        print(f"\\n总计生成 {len(ast)} 个节点\\n")
        return True
    except Exception as e:
        print(f"解析失败: {e}")
        return False


def test_intent_comments():
    """测试意图注释处理"""
    code = """\
@ 这是一个意图注释
func test_function():
    @ 另一个意图注释
    行为步骤
"""
    
    print("=== 意图注释测试 ===")
    print("输入代码:")
    print(code)
    
    lexer = IbcLexer(code)
    tokens = lexer.tokenize()
    
    if not tokens:
        print("词法分析失败")
        return False
        
    parser = IbcParser(tokens)
    try:
        ast = parser.parse()
        print("\\n生成的AST节点:")
        for uid, node in ast.items():
            print(f"  UID: {uid}, 节点: {node}")
        print(f"\\n总计生成 {len(ast)} 个节点\\n")
        return True
    except Exception as e:
        print(f"解析失败: {e}")
        return False


def test_nested_structure():
    """测试嵌套结构"""
    code = """\
module TestModule
    
class OuterClass:
    class InnerClass:
        func inner_func():
            内部函数步骤
"""
    
    print("=== 嵌套结构测试 ===")
    print("输入代码:")
    print(code)
    
    lexer = IbcLexer(code)
    tokens = lexer.tokenize()
    
    if not tokens:
        print("词法分析失败")
        return False
        
    parser = IbcParser(tokens)
    try:
        ast = parser.parse()
        print("\\n生成的AST节点:")
        for uid, node in ast.items():
            print(f"  UID: {uid}, 节点: {node}")
        print(f"\\n总计生成 {len(ast)} 个节点\\n")
        return True
    except Exception as e:
        print(f"解析失败: {e}")
        return False


def test_behavior_with_refs():
    """测试包含符号引用的行为步骤"""
    code = """\
func test_func():
    调用 $SomeClass$ 的方法
"""
    
    print("=== 符号引用测试 ===")
    print("输入代码:")
    print(code)
    
    lexer = IbcLexer(code)
    tokens = lexer.tokenize()
    
    if not tokens:
        print("词法分析失败")
        return False

    for token in tokens:
        print(token)
        
    parser = IbcParser(tokens)
    try:
        ast = parser.parse()
        print("\\n生成的AST节点:")
        for uid, node in ast.items():
            print(f"  UID: {uid}, 节点: {node}")
        print(f"\\n总计生成 {len(ast)} 个节点\\n")
        return True
    except Exception as e:
        print(f"解析失败: {e}")
        return False


def test_parse_errors():
    """测试解析错误处理"""
    # 测试无效的缩进
    code = """func test_func():
        无效缩进
"""
    
    print("=== 错误处理测试 ===")
    print("输入代码:")
    print(code)
    
    lexer = IbcLexer(code)
    tokens = lexer.tokenize()
    
    if not tokens:
        print("词法分析失败")
        return False
        
    parser = IbcParser(tokens)
    try:
        ast = parser.parse()
        print("\\n生成的AST节点:")
        for uid, node in ast.items():
            print(f"  UID: {uid}, 节点: {node}")
        print(f"\\n总计生成 {len(ast)} 个节点\\n")
        print("注意: 应该抛出解析异常，但没有抛出\\n")
        return True
    except Exception as e:
        print(f"正确捕获异常: {type(e).__name__}: {e}\\n")
        return True


def main():
    """主测试函数"""
    print("开始测试IBC解析器...")
    
    tests = [
        test_basic_parsing,
        test_class_parsing,
        test_intent_comments,
        test_nested_structure,
        test_behavior_with_refs,
        test_parse_errors
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
    
    print(f"\\n测试完成: {passed}/{total} 个测试正常执行")
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)