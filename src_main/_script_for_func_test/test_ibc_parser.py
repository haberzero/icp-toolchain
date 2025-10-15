import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from utils.ibc_analyzer.ibc_lexer import Lexer
from utils.ibc_analyzer.ibc_parser import IbcParser


def test_basic_parsing():
    """测试基本解析功能"""
    code = """module test_module : 测试模块
func test_function:
description: 测试函数
input: param1, param2
output: result
begin:
    步骤1
    步骤2:
        子步骤1
        子步骤2
    步骤3
"""
    
    lexer = Lexer(code)
    tokens = lexer.tokenize()
    
    if not tokens:
        print("❌ 词法分析失败")
        return False
        
    parser = IbcParser(tokens)
    try:
        ast = parser.parse()
        print(f"✓ 基本解析测试通过，生成 {len(ast)} 个节点")
        return True
    except Exception as e:
        print(f"❌ 基本解析测试失败: {e}")
        return False


def test_class_parsing():
    """测试类解析功能"""
    code = """class TestClass:
description: 测试类
begin:
    var test_var: 测试变量
    
    func __init__:
    begin:
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
        print(f"✓ 类解析测试通过，生成 {len(ast)} 个节点")
        return True
    except Exception as e:
        print(f"❌ 类解析测试失败: {e}")
        return False


def test_intent_comments():
    """测试意图注释处理"""
    code = """@ 这是一个意图注释
func test_function:
begin:
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
        print(f"✓ 意图注释测试通过，生成 {len(ast)} 个节点")
        return True
    except Exception as e:
        print(f"❌ 意图注释测试失败: {e}")
        return False


def main():
    """主测试函数"""
    print("开始测试IBC解析器...")
    
    tests = [
        test_basic_parsing,
        test_class_parsing,
        test_intent_comments
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