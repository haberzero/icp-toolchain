import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from utils.ibc_analyzer.ibc_lexer import Lexer
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
    
    lexer = Lexer(code)
    tokens = lexer.tokenize()
    
    if not tokens:
        print("❌ 词法分析失败")
        return False
        
    parser = IbcParser(tokens)
    try:
        ast = parser.parse()
        # 应该有3个节点: module, func, behavior_step
        if len(ast) >= 3:
            print(f"✓ 基本解析测试通过，生成 {len(ast)} 个节点")
            return True
        else:
            print(f"❌ 基本解析测试失败，节点数不足: {len(ast)}")
            return False
    except Exception as e:
        print(f"❌ 基本解析测试失败: {e}")
        return False


def test_class_parsing():
    """测试类解析功能"""
    code = """\
class TestClass:
    var test_var: 测试变量
    
    func __init__():
        初始化步骤
"""
    
    lexer = Lexer(code)
    tokens = lexer.tokenize()
    
    if not tokens:
        print("❌ 词法分析失败")
        return False
        
    parser = IbcParser(tokens)
    try:
        ast = parser.parse()
        # 应该有4个节点: class, var, func, behavior_step
        if len(ast) >= 4:
            print(f"✓ 类解析测试通过，生成 {len(ast)} 个节点")
            return True
        else:
            print(f"❌ 类解析测试失败，节点数不足: {len(ast)}")
            return False
    except Exception as e:
        print(f"❌ 类解析测试失败: {e}")
        return False


def test_intent_comments():
    """测试意图注释处理"""
    code = """\
@ 这是一个意图注释
func test_function():
    @ 另一个意图注释
    行为步骤
"""
    
    lexer = Lexer(code)
    tokens = lexer.tokenize()
    
    if not tokens:
        print("❌ 词法分析失败")
        return False
        
    parser = IbcParser(tokens)
    try:
        ast = parser.parse()
        # 应该有2个节点: func, behavior_step (intent comments不生成节点)
        if len(ast) >= 2:
            print(f"✓ 意图注释测试通过，生成 {len(ast)} 个节点")
            return True
        else:
            print(f"❌ 意图注释测试失败，节点数不足: {len(ast)}")
            return False
    except Exception as e:
        print(f"❌ 意图注释测试失败: {e}")
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
    
    lexer = Lexer(code)
    tokens = lexer.tokenize()
    
    if not tokens:
        print("❌ 词法分析失败")
        return False
        
    parser = IbcParser(tokens)
    try:
        ast = parser.parse()
        # 应该有5个节点: module, OuterClass, InnerClass, inner_func, behavior_step
        if len(ast) >= 5:
            print(f"✓ 嵌套结构测试通过，生成 {len(ast)} 个节点")
            return True
        else:
            print(f"❌ 嵌套结构测试失败，节点数不足: {len(ast)}")
            return False
    except Exception as e:
        print(f"❌ 嵌套结构测试失败: {e}")
        return False


def test_behavior_with_refs():
    """测试包含符号引用的行为步骤"""
    code = """\
func test_func():
    调用 $SomeClass$ 的方法
"""
    
    lexer = Lexer(code)
    tokens = lexer.tokenize()
    
    if not tokens:
        print("❌ 词法分析失败")
        return False
        
    parser = IbcParser(tokens)
    try:
        ast = parser.parse()
        # 应该有2个节点: func, behavior_step
        if len(ast) >= 2:
            # 检查behavior_step节点是否正确处理了符号引用
            behavior_node = None
            for node in ast.values():
                if node.node_type == AstNodeType.BEHAVIOR_STEP:
                    behavior_node = node
                    break
            
            if behavior_node and len(behavior_node.symbol_refs) > 0:
                print(f"✓ 符号引用测试通过，生成 {len(ast)} 个节点，包含符号引用")
                return True
            else:
                print(f"❌ 符号引用测试失败，未正确处理符号引用")
                return False
        else:
            print(f"❌ 符号引用测试失败，节点数不足: {len(ast)}")
            return False
    except Exception as e:
        print(f"❌ 符号引用测试失败: {e}")
        return False


def test_parse_errors():
    """测试解析错误处理"""
    # 测试无效的缩进
    code = """func test_func():
        无效缩进
"""
    
    lexer = Lexer(code)
    tokens = lexer.tokenize()
    
    if not tokens:
        print("❌ 词法分析失败")
        return False
        
    parser = IbcParser(tokens)
    try:
        ast = parser.parse()
        # 如果没有抛出异常，说明错误处理可能有问题
        print(f"❌ 错误处理测试失败，应该抛出解析异常")
        return False
    except Exception as e:
        # 任何异常都可以接受，因为我们故意制造了一个错误的缩进
        print(f"✓ 错误处理测试通过，正确捕获异常: {type(e).__name__}")
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
    
    print(f"\n测试结果: {passed}/{total} 通过")
    
    if passed == total:
        print("✓ 所有测试通过!")
        return True
    else:
        print("❌ 部分测试失败!")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)