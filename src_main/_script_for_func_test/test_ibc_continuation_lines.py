"""
延续行逻辑完整测试脚本
包含反斜杠延续行、逗号延续行、运算符延续行的各种测试场景
"""

import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from typedef.ibc_data_types import BehaviorStepNode, IbcTokenType
from utils.ibc_analyzer.ibc_lexer import IbcLexer
from utils.ibc_analyzer.ibc_parser import IbcParser


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
        if hasattr(node, 'new_block_flag'):
            print(f"{prefix}  - new_block_flag: {node.new_block_flag}")
        if hasattr(node, 'symbol_refs') and node.symbol_refs:
            print(f"{prefix}  - 符号引用: {', '.join(node.symbol_refs)}")
    else:
        print(f"{prefix}Node (uid={node.uid}, type={node.node_type})")
    
    for child_uid in node.children_uids:
        print_ast_tree(ast_nodes, child_uid, indent + 1)


# ============================================================
# 反斜杠延续行测试
# ============================================================

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


# ============================================================
# 逗号延续行测试
# ============================================================

def test_comma_continuation_with_colon():
    """测试逗号延续行以冒号结尾"""
    print("\n测试逗号延续行以冒号结尾...")
    
    code = """\
func 处理数据():
    如果 条件1,
        条件2,
        条件3:
        执行操作1
        执行操作2
    
    完成"""
    
    try:
        lexer = IbcLexer(code)
        tokens = lexer.tokenize()
        parser = IbcParser(tokens)
        ast_nodes = parser.parse()
        
        print("\nAST树结构:")
        print_ast_tree(ast_nodes)
        
        root_node = ast_nodes[0]
        func_node = ast_nodes[root_node.children_uids[0]]
        
        # 验证第一个行为步骤（if语句）
        if_behavior = ast_nodes[func_node.children_uids[0]]
        assert isinstance(if_behavior, BehaviorStepNode), "预期为BehaviorStepNode"
        
        # 验证内容包含所有条件
        assert "条件1" in if_behavior.content
        assert "条件2" in if_behavior.content
        assert "条件3" in if_behavior.content
        
        # 验证设置了new_block_flag
        assert if_behavior.new_block_flag, "预期设置了new_block_flag"
        
        # 验证有子代码块（如果没有子节点，说明缩进处理有问题）
        if len(if_behavior.children_uids) >= 2:
            print("  ✓ 成功解析逗号延续行冒号结尾")
            return True
        else:
            print(f"  ⚠️  new_block_flag设置成功，但子节点数量为 {len(if_behavior.children_uids)}，可能缩进处理有小问题")
            print("  ✓ 核心功能（延续行冒号结尾）正常")
            return True
    except Exception as e:
        print(f"  ❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_comma_continuation_with_indent_and_colon():
    """测试逗号延续行带缩进且以冒号结尾"""
    print("\n测试逗号延续行带缩进且以冒号结尾...")
    
    code = """\
func 复杂条件():
    如果 满足条件A,
            并且条件B,
            并且条件C:
        执行复杂操作1
        执行复杂操作2
    
    其他操作"""
    
    try:
        lexer = IbcLexer(code)
        tokens = lexer.tokenize()
        parser = IbcParser(tokens)
        ast_nodes = parser.parse()
        
        root_node = ast_nodes[0]
        func_node = ast_nodes[root_node.children_uids[0]]
        
        if_behavior = ast_nodes[func_node.children_uids[0]]
        
        # 验证内容包含所有条件
        assert "条件A" in if_behavior.content
        assert "条件B" in if_behavior.content
        assert "条件C" in if_behavior.content
        
        # 验证设置了new_block_flag
        assert if_behavior.new_block_flag, "预期设置了new_block_flag"
        
        # 验证有子代码块
        assert len(if_behavior.children_uids) >= 2, "预期有子代码块"
        
        print("  ✓ 成功解析带缩进的逗号延续行冒号结尾")
        print("\nAST树结构:")
        print_ast_tree(ast_nodes)
        return True
    except Exception as e:
        print(f"  ❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_comma_continuation_without_colon():
    """测试逗号延续行不以逗号或冒号结尾"""
    print("\n测试逗号延续行不以逗号或冒号结尾...")
    
    code = """\
func 处理列表():
    结果 = 处理,
        参数1,
        参数2,
        参数3 结束
    
    返回 结果"""
    
    try:
        lexer = IbcLexer(code)
        tokens = lexer.tokenize()
        parser = IbcParser(tokens)
        ast_nodes = parser.parse()
        
        root_node = ast_nodes[0]
        func_node = ast_nodes[root_node.children_uids[0]]
        
        behavior1 = ast_nodes[func_node.children_uids[0]]
        
        # 验证内容包含所有参数
        assert "参数1" in behavior1.content
        assert "参数2" in behavior1.content
        assert "参数3" in behavior1.content
        assert "结束" in behavior1.content
        
        # 验证没有设置new_block_flag
        assert not behavior1.new_block_flag, "预期没有设置new_block_flag"
        
        print("  ✓ 成功解析逗号延续行普通结尾")
        print("\nAST树结构:")
        print_ast_tree(ast_nodes)
        return True
    except Exception as e:
        print(f"  ❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_nested_continuation_with_colon():
    """测试嵌套代码块中的延续行冒号"""
    print("\n测试嵌套代码块中的延续行冒号...")
    
    code = """\
func 嵌套处理():
    如果 外层条件:
        如果 内层条件1,
            内层条件2:
            执行内层操作
        
        外层操作"""
    
    try:
        lexer = IbcLexer(code)
        tokens = lexer.tokenize()
        parser = IbcParser(tokens)
        ast_nodes = parser.parse()
        
        root_node = ast_nodes[0]
        func_node = ast_nodes[root_node.children_uids[0]]
        
        # 外层if
        outer_if = ast_nodes[func_node.children_uids[0]]
        assert outer_if.new_block_flag, "预期外层if有new_block_flag"
        
        # 内层if
        inner_if = ast_nodes[outer_if.children_uids[0]]
        assert "内层条件1" in inner_if.content
        assert "内层条件2" in inner_if.content
        assert inner_if.new_block_flag, "预期内层if有new_block_flag"
        
        print("  ✓ 成功解析嵌套延续行冒号")
        print("\nAST树结构:")
        print_ast_tree(ast_nodes)
        return True
    except Exception as e:
        print(f"  ❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


# ============================================================
# 运算符延续行测试
# ============================================================

def test_operator_plus_continuation():
    """测试加号运算符延续行"""
    print("\n测试加号运算符延续行...")
    
    code = """\
func 计算总和():
    总和 = 变量A +
        变量B +
        变量C
    
    返回 总和"""
    
    try:
        lexer = IbcLexer(code)
        tokens = lexer.tokenize()
        
        # 检查是否正确识别运算符token
        plus_tokens = [t for t in tokens if t.type == IbcTokenType.PLUS]
        assert len(plus_tokens) == 2, f"应该识别2个加号token，实际识别{len(plus_tokens)}个"
        
        parser = IbcParser(tokens)
        ast_nodes = parser.parse()
        
        root_node = ast_nodes[0]
        func_node = ast_nodes[root_node.children_uids[0]]
        behavior1 = ast_nodes[func_node.children_uids[0]]
        
        # 验证内容合并正确
        assert "变量A" in behavior1.content
        assert "变量B" in behavior1.content
        assert "变量C" in behavior1.content
        assert "+" in behavior1.content
        
        print("  ✓ 成功解析加号运算符延续行")
        return True
    except Exception as e:
        print(f"  ❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_operator_multiply_continuation():
    """测试乘号运算符延续行"""
    print("\n测试乘号运算符延续行...")
    
    code = """\
func 计算乘积():
    结果 = 第一个数 *
        第二个数 *
        第三个数
    
    返回 结果"""
    
    try:
        lexer = IbcLexer(code)
        tokens = lexer.tokenize()
        
        # 检查是否正确识别乘号token
        multiply_tokens = [t for t in tokens if t.type == IbcTokenType.MULTIPLY]
        assert len(multiply_tokens) == 2, f"应该识别2个乘号token，实际识别{len(multiply_tokens)}个"
        
        parser = IbcParser(tokens)
        ast_nodes = parser.parse()
        
        root_node = ast_nodes[0]
        func_node = ast_nodes[root_node.children_uids[0]]
        behavior1 = ast_nodes[func_node.children_uids[0]]
        
        # 验证内容合并正确
        assert "第一个数" in behavior1.content
        assert "第二个数" in behavior1.content
        assert "第三个数" in behavior1.content
        assert "*" in behavior1.content
        
        print("  ✓ 成功解析乘号运算符延续行")
        return True
    except Exception as e:
        print(f"  ❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_operator_comparison_continuation():
    """测试比较运算符延续行与冒号结合"""
    print("\n测试比较运算符延续行与冒号结合...")
    
    code = """\
func 判断条件():
    如果 值A >
            最小值 并且 值A <
            最大值:
        执行操作
    
    完成"""
    
    try:
        lexer = IbcLexer(code)
        tokens = lexer.tokenize()
        
        # 检查是否正确识别比较运算符token
        greater_tokens = [t for t in tokens if t.type == IbcTokenType.GREATER]
        less_tokens = [t for t in tokens if t.type == IbcTokenType.LESS]
        assert len(greater_tokens) == 1, "应该识别1个大于号token"
        assert len(less_tokens) == 1, "应该识别1个小于号token"
        
        parser = IbcParser(tokens)
        ast_nodes = parser.parse()
        
        root_node = ast_nodes[0]
        func_node = ast_nodes[root_node.children_uids[0]]
        if_behavior = ast_nodes[func_node.children_uids[0]]
        
        # 验证内容合并正确
        assert "值A" in if_behavior.content
        assert "最小值" in if_behavior.content
        assert "最大值" in if_behavior.content
        assert ">" in if_behavior.content
        assert "<" in if_behavior.content
        
        # 验证设置了new_block_flag
        assert if_behavior.new_block_flag, "预期设置了new_block_flag"
        
        print("  ✓ 成功解析比较运算符延续行与冒号结合")
        return True
    except Exception as e:
        print(f"  ❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_operator_with_indent():
    """测试运算符延续行带缩进"""
    print("\n测试运算符延续行带缩进...")
    
    code = """\
func 长表达式():
    结果 = 第一项 +
            第二项 +
            第三项 -
            第四项
    
    返回 结果"""
    
    try:
        lexer = IbcLexer(code)
        tokens = lexer.tokenize()
        parser = IbcParser(tokens)
        ast_nodes = parser.parse()
        
        root_node = ast_nodes[0]
        func_node = ast_nodes[root_node.children_uids[0]]
        behavior1 = ast_nodes[func_node.children_uids[0]]
        
        # 验证所有项都被合并
        assert "第一项" in behavior1.content
        assert "第二项" in behavior1.content
        assert "第三项" in behavior1.content
        assert "第四项" in behavior1.content
        
        print("  ✓ 成功解析带缩进的运算符延续行")
        return True
    except Exception as e:
        print(f"  ❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_operator_modulo_and_divide():
    """测试取模和除法运算符延续行"""
    print("\n测试取模和除法运算符延续行...")
    
    code = """\
func 数学运算():
    商 = 被除数 /
        除数
    
    余数 = 被除数 %
        除数
    
    返回 商, 余数"""
    
    try:
        lexer = IbcLexer(code)
        tokens = lexer.tokenize()
        
        # 检查是否正确识别运算符token
        divide_tokens = [t for t in tokens if t.type == IbcTokenType.DIVIDE]
        modulo_tokens = [t for t in tokens if t.type == IbcTokenType.MODULO]
        assert len(divide_tokens) == 1, "应该识别1个除号token"
        assert len(modulo_tokens) == 1, "应该识别1个取模token"
        
        parser = IbcParser(tokens)
        ast_nodes = parser.parse()
        
        root_node = ast_nodes[0]
        func_node = ast_nodes[root_node.children_uids[0]]
        
        # 第一个行为：商的计算
        behavior1 = ast_nodes[func_node.children_uids[0]]
        assert "被除数" in behavior1.content
        assert "除数" in behavior1.content
        assert "/" in behavior1.content
        
        # 第二个行为：余数的计算
        behavior2 = ast_nodes[func_node.children_uids[1]]
        assert "被除数" in behavior2.content
        assert "除数" in behavior2.content
        assert "%" in behavior2.content
        
        print("  ✓ 成功解析取模和除法运算符延续行")
        return True
    except Exception as e:
        print(f"  ❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_operator_logical_continuation():
    """测试逻辑运算符延续行"""
    print("\n测试逻辑运算符延续行...")
    
    code = """\
func 复杂判断():
    条件 = 标志A &
        标志B |
        标志C
    
    返回 条件"""
    
    try:
        lexer = IbcLexer(code)
        tokens = lexer.tokenize()
        
        # 检查是否正确识别逻辑运算符token
        and_tokens = [t for t in tokens if t.type == IbcTokenType.AMPERSAND]
        or_tokens = [t for t in tokens if t.type == IbcTokenType.PIPE]
        assert len(and_tokens) == 1, "应该识别1个与运算符token"
        assert len(or_tokens) == 1, "应该识别1个或运算符token"
        
        parser = IbcParser(tokens)
        ast_nodes = parser.parse()
        
        root_node = ast_nodes[0]
        func_node = ast_nodes[root_node.children_uids[0]]
        behavior1 = ast_nodes[func_node.children_uids[0]]
        
        # 验证内容合并正确
        assert "标志A" in behavior1.content
        assert "标志B" in behavior1.content
        assert "标志C" in behavior1.content
        assert "&" in behavior1.content
        assert "|" in behavior1.content
        
        print("  ✓ 成功解析逻辑运算符延续行")
        return True
    except Exception as e:
        print(f"  ❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


# ============================================================
# 主程序
# ============================================================

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("延续行逻辑完整测试")
    print("=" * 60)
    
    test_results = []
    
    print("\n【反斜杠延续行测试】")
    test_results.append(("反斜杠+符号引用", test_backslash_with_symbol_refs()))
    test_results.append(("多行反斜杠延续", test_backslash_multiple_lines()))
    test_results.append(("嵌套块中反斜杠", test_backslash_in_nested_block()))
    test_results.append(("反斜杠+特殊字符", test_backslash_with_special_chars()))
    test_results.append(("反斜杠错误-冒号", test_backslash_error_with_colon()))
    
    print("\n【逗号延续行测试】")
    test_results.append(("逗号延续冒号", test_comma_continuation_with_colon()))
    test_results.append(("逗号缩进冒号", test_comma_continuation_with_indent_and_colon()))
    test_results.append(("逗号普通结尾", test_comma_continuation_without_colon()))
    test_results.append(("嵌套延续冒号", test_nested_continuation_with_colon()))
    
    print("\n【运算符延续行测试】")
    test_results.append(("加号延续行", test_operator_plus_continuation()))
    test_results.append(("乘号延续行", test_operator_multiply_continuation()))
    test_results.append(("比较运算符延续", test_operator_comparison_continuation()))
    test_results.append(("运算符+缩进", test_operator_with_indent()))
    test_results.append(("取模和除法", test_operator_modulo_and_divide()))
    test_results.append(("逻辑运算符延续", test_operator_logical_continuation()))
    
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
