"""
反斜杠延续行的额外测试用例
测试各种边界情况和组合场景
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from utils.ibc_analyzer.ibc_lexer import IbcLexer
from utils.ibc_analyzer.ibc_parser import IbcParser
from typedef.ibc_data_types import BehaviorStepNode


def print_ast_tree(ast_nodes, uid=0, indent=0):
    """打印AST树结构"""
    node = ast_nodes[uid]
    prefix = "  " * indent
    
    if hasattr(node, 'identifier'):
        node_type = node.node_type.value
        print(f"{prefix}{node_type}: {node.identifier} (uid={node.uid})")
        if hasattr(node, 'content') and node.content:
            print(f"{prefix}  - 描述: {node.content}")
    elif hasattr(node, 'content'):
        content_preview = node.content[:50] + "..." if len(node.content) > 50 else node.content
        print(f"{prefix}Behavior: {content_preview} (uid={node.uid})")
        if hasattr(node, 'symbol_refs') and node.symbol_refs:
            print(f"{prefix}  - 符号引用: {', '.join(node.symbol_refs)}")
    else:
        print(f"{prefix}Node (uid={node.uid}, type={node.node_type})")
    
    for child_uid in node.children_uids:
        print_ast_tree(ast_nodes, child_uid, indent + 1)


def test_backslash_with_symbol_refs():
    """测试反斜杠延续行中包含符号引用"""
    print("\n测试反斜杠延续行中包含符号引用...")
    
    code = """\
func 处理用户数据():
    结果 = 调用 $userService.getUserInfo 传递参数 \\
    用户ID, 详细信息标志, 权限级别
    
    返回 结果"""
    
    try:
        lexer = IbcLexer(code)
        tokens = lexer.tokenize()
        parser = IbcParser(tokens)
        ast_nodes = parser.parse()
        
        root_node = ast_nodes[0]
        func_node = ast_nodes[root_node.children_uids[0]]
        
        # 验证第一个行为步骤
        behavior1 = ast_nodes[func_node.children_uids[0]]
        assert isinstance(behavior1, BehaviorStepNode), "预期为BehaviorStepNode"
        
        # 验证内容合并正确
        assert "getUserInfo" in behavior1.content
        assert "用户ID" in behavior1.content
        assert "详细信息标志" in behavior1.content
        assert "权限级别" in behavior1.content
        
        # 验证符号引用
        assert "userService.getUserInfo" in behavior1.symbol_refs
        
        print("  ✓ 成功解析反斜杠延续行中的符号引用")
        print("\nAST树结构:")
        print_ast_tree(ast_nodes)
        return True
    except Exception as e:
        print(f"  ❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_backslash_multiple_lines():
    """测试多行反斜杠延续"""
    print("\n测试多行反斜杠延续...")
    
    code = """\
func 构建长字符串():
    消息 = 这是第一部分内容 \\
    这是第二部分内容 \\
    这是第三部分内容 \\
    这是第四部分内容
    
    输出 消息"""
    
    try:
        lexer = IbcLexer(code)
        tokens = lexer.tokenize()
        parser = IbcParser(tokens)
        ast_nodes = parser.parse()
        
        root_node = ast_nodes[0]
        func_node = ast_nodes[root_node.children_uids[0]]
        
        behavior1 = ast_nodes[func_node.children_uids[0]]
        
        # 验证所有部分都被合并
        assert "第一部分" in behavior1.content
        assert "第二部分" in behavior1.content
        assert "第三部分" in behavior1.content
        assert "第四部分" in behavior1.content
        
        print("  ✓ 成功解析多行反斜杠延续")
        print("\nAST树结构:")
        print_ast_tree(ast_nodes)
        return True
    except Exception as e:
        print(f"  ❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_backslash_in_nested_block():
    """测试嵌套代码块中的反斜杠延续行"""
    print("\n测试嵌套代码块中的反斜杠延续行...")
    
    code = """\
func 处理条件():
    如果 条件A 且 条件B:
        执行 操作1 使用参数 \\
        参数1, 参数2, 参数3
        
        执行 操作2"""
    
    try:
        lexer = IbcLexer(code)
        tokens = lexer.tokenize()
        parser = IbcParser(tokens)
        ast_nodes = parser.parse()
        
        root_node = ast_nodes[0]
        func_node = ast_nodes[root_node.children_uids[0]]
        
        # 第一个行为是if语句
        if_behavior = ast_nodes[func_node.children_uids[0]]
        assert if_behavior.new_block_flag, "预期if语句有新代码块标志"
        
        # if代码块内的第一个行为应该包含合并的内容
        nested_behavior1 = ast_nodes[if_behavior.children_uids[0]]
        assert "操作1" in nested_behavior1.content
        assert "参数1" in nested_behavior1.content
        assert "参数2" in nested_behavior1.content
        assert "参数3" in nested_behavior1.content
        
        print("  ✓ 成功解析嵌套代码块中的反斜杠延续行")
        print("\nAST树结构:")
        print_ast_tree(ast_nodes)
        return True
    except Exception as e:
        print(f"  ❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_backslash_with_special_chars():
    """测试反斜杠延续行中包含特殊字符"""
    print("\n测试反斜杠延续行中包含特殊字符...")
    
    code = """\
func 构建表达式():
    表达式 = (变量A + 变量B) × \\
    (变量C - 变量D)
    
    返回 表达式"""
    
    try:
        lexer = IbcLexer(code)
        tokens = lexer.tokenize()
        parser = IbcParser(tokens)
        ast_nodes = parser.parse()
        
        root_node = ast_nodes[0]
        func_node = ast_nodes[root_node.children_uids[0]]
        
        behavior1 = ast_nodes[func_node.children_uids[0]]
        
        # 验证括号和运算符都被保留
        assert "(" in behavior1.content
        assert ")" in behavior1.content
        assert "×" in behavior1.content or "x" in behavior1.content
        assert "变量A" in behavior1.content
        assert "变量D" in behavior1.content
        
        print("  ✓ 成功解析包含特殊字符的反斜杠延续行")
        print("\nAST树结构:")
        print_ast_tree(ast_nodes)
        return True
    except Exception as e:
        print(f"  ❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_backslash_error_with_colon():
    """测试反斜杠延续行行末包含冒号的错误情况"""
    print("\n测试反斜杠延续行行末包含冒号的错误情况...")
    
    code = """\
func 错误示例():
    这是一个错误的延续行 \\
    因为下一行以冒号结束:"""
    
    try:
        lexer = IbcLexer(code)
        tokens = lexer.tokenize()
        parser = IbcParser(tokens)
        ast_nodes = parser.parse()
        
        print("  ❌ 应该抛出错误但没有")
        return False
    except Exception as e:
        error_msg = str(e)
        if "Backslash continuation line cannot end with colon" in error_msg:
            print(f"  ✓ 成功检测到反斜杠延续行行末冒号错误: {error_msg}")
            return True
        else:
            print(f"  ❌ 错误类型不匹配: {error_msg}")
            return False


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("反斜杠延续行额外测试")
    print("=" * 60)
    
    test_results = []
    
    test_results.append(("反斜杠+符号引用", test_backslash_with_symbol_refs()))
    test_results.append(("多行反斜杠延续", test_backslash_multiple_lines()))
    test_results.append(("嵌套块中反斜杠", test_backslash_in_nested_block()))
    test_results.append(("反斜杠+特殊字符", test_backslash_with_special_chars()))
    test_results.append(("反斜杠错误-冒号", test_backslash_error_with_colon()))
    
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    
    passed = 0
    failed = 0
    
    for test_name, result in test_results:
        status = "✓ 通过" if result else "❌ 失败"
        print(f"{test_name:20} {status}")
        if result:
            passed += 1
        else:
            failed += 1
    
    print("=" * 60)
    print(f"总计: {passed} 通过, {failed} 失败")
    
    if failed == 0:
        print("所有测试通过！✓")
    else:
        print(f"⚠️  有 {failed} 个测试失败")
    print("=" * 60)
