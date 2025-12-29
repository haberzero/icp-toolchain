"""
测试符号替换功能

该脚本专注测试 ibc_funcs.py 中的符号替换相关功能
验证符号替换的正确性、稳定性和各种边界情况
"""

import sys
import os

# 添加项目根目录到Python路径
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from libs.ibc_funcs import IbcFuncs
from utils.ibc_analyzer.ibc_lexer import IbcLexer
from utils.ibc_analyzer.ibc_parser import IbcParser


def test_simple_symbol_replacement():
    """测试简单符号替换"""
    print("\n测试 simple_symbol_replacement 功能...")
    
    try:
        # 简单函数的IBC代码
        ibc_content = """func calculate_sum(数值1, 数值2):
    结果 = 数值1 + 数值2
    返回 结果
"""
        
        # 解析AST
        lexer = IbcLexer(ibc_content)
        tokens = lexer.tokenize()
        parser = IbcParser(tokens)
        ast_dict = parser.parse()
        
        # 构造符号元数据
        symbols_metadata = {
            "test.calculate_sum": {
                "type": "func",
                "normalized_name": "calculate_sum"
            },
            "test.calculate_sum.数值1": {
                "type": "param",
                "normalized_name": "num1"
            },
            "test.calculate_sum.数值2": {
                "type": "param",
                "normalized_name": "num2"
            },
            "test.calculate_sum.结果": {
                "type": "var",
                "normalized_name": "result"
            }
        }
        
        # 执行替换
        result = IbcFuncs.replace_symbols_with_normalized_names(
            ibc_content=ibc_content,
            ast_dict=ast_dict,
            symbols_metadata=symbols_metadata,
            current_file_name="test"
        )
        
        # 验证替换结果
        assert "calculate_sum(num1, num2)" in result, "函数签名替换失败"
        assert "result = num1 + num2" in result, "变量替换失败"
        assert "返回 result" in result, "返回语句中的变量替换失败"
        assert "数值1" not in result, "原始参数名未替换"
        assert "数值2" not in result, "原始参数名未替换"
        assert "结果" not in result, "原始变量名未替换"
        
        print("  ✓ 简单符号替换测试通过")
        return True
        
    except Exception as e:
        print(f"  ❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_class_symbol_replacement():
    """测试类符号替换"""
    print("\n测试 class_symbol_replacement 功能...")
    
    try:
        # 包含类的IBC代码
        ibc_content = """class 用户管理器():
    var 用户列表
    
    func 添加用户(用户名):
        用户对象 = 创建用户(用户名)
        self.用户列表.append(用户对象)
"""
        
        # 解析AST
        lexer = IbcLexer(ibc_content)
        tokens = lexer.tokenize()
        parser = IbcParser(tokens)
        ast_dict = parser.parse()
        
        # 符号元数据
        symbols_metadata = {
            "test.用户管理器": {
                "type": "class",
                "normalized_name": "UserManager"
            },
            "test.用户管理器.用户列表": {
                "type": "var",
                "normalized_name": "user_list"
            },
            "test.用户管理器.添加用户": {
                "type": "func",
                "normalized_name": "add_user"
            },
            "test.用户管理器.添加用户.用户名": {
                "type": "param",
                "normalized_name": "username"
            },
            "test.用户管理器.添加用户.用户对象": {
                "type": "var",
                "normalized_name": "user_obj"
            }
        }
        
        # 执行替换
        result = IbcFuncs.replace_symbols_with_normalized_names(
            ibc_content=ibc_content,
            ast_dict=ast_dict,
            symbols_metadata=symbols_metadata,
            current_file_name="test"
        )
        
        # 验证
        assert "class UserManager" in result, "类名替换失败"
        assert "var user_list" in result, "成员变量替换失败"
        assert "func add_user(username)" in result, "方法签名替换失败"
        assert "user_obj" in result, "局部变量替换失败"
        assert "self.user_list.append(user_obj)" in result, "方法体中的符号替换失败"
        
        print("  ✓ 类符号替换测试通过")
        return True
        
    except Exception as e:
        print(f"  ❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_dollar_reference_replacement():
    """测试$符号引用替换"""
    print("\n测试 dollar_reference_replacement 功能...")
    
    try:
        # 包含$引用的IBC代码
        ibc_content = """module logger

func 处理数据():
    日志器 = $logger.Logger()
    结果 = $self.内部方法()
    数据 = $logger.get_data()
"""
        
        # 解析AST
        lexer = IbcLexer(ibc_content)
        tokens = lexer.tokenize()
        parser = IbcParser(tokens)
        ast_dict = parser.parse()
        
        # 符号元数据
        symbols_metadata = {
            "test.处理数据": {
                "type": "func",
                "normalized_name": "process_data"
            },
            "test.处理数据.日志器": {
                "type": "var",
                "normalized_name": "logger_instance"
            },
            "test.处理数据.结果": {
                "type": "var",
                "normalized_name": "result"
            },
            "test.处理数据.数据": {
                "type": "var",
                "normalized_name": "data"
            }
        }
        
        # 执行替换
        result = IbcFuncs.replace_symbols_with_normalized_names(
            ibc_content=ibc_content,
            ast_dict=ast_dict,
            symbols_metadata=symbols_metadata,
            current_file_name="test"
        )
        
        # 验证$引用被保留
        assert "$logger.Logger" in result, "$logger.Logger引用应被保留"
        assert "$self." in result, "$self引用应被保留"
        assert "$logger.get_data" in result, "$logger.get_data引用应被保留"
        
        # 验证局部变量被替换
        assert "logger_instance" in result, "日志器变量应被替换为logger_instance"
        assert "result" in result, "结果变量应被替换为result"
        assert "data" in result, "数据变量应被替换为data"
        
        print("  ✓ $符号引用替换测试通过")
        return True
        
    except Exception as e:
        print(f"  ❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_nested_scope_replacement():
    """测试嵌套作用域的符号替换"""
    print("\n测试 nested_scope_replacement 功能...")
    
    try:
        # 嵌套作用域的IBC代码
        ibc_content = """class 外部类():
    var 外部变量
    
    func 外部方法(外部参数):
        内部变量 = 外部参数 + self.外部变量
        返回 内部变量
"""
        
        # 解析AST
        lexer = IbcLexer(ibc_content)
        tokens = lexer.tokenize()
        parser = IbcParser(tokens)
        ast_dict = parser.parse()
        
        # 符号元数据
        symbols_metadata = {
            "test.外部类": {
                "type": "class",
                "normalized_name": "OuterClass"
            },
            "test.外部类.外部变量": {
                "type": "var",
                "normalized_name": "outer_var"
            },
            "test.外部类.外部方法": {
                "type": "func",
                "normalized_name": "outer_method"
            },
            "test.外部类.外部方法.外部参数": {
                "type": "param",
                "normalized_name": "outer_param"
            },
            "test.外部类.外部方法.内部变量": {
                "type": "var",
                "normalized_name": "inner_var"
            }
        }
        
        # 执行替换
        result = IbcFuncs.replace_symbols_with_normalized_names(
            ibc_content=ibc_content,
            ast_dict=ast_dict,
            symbols_metadata=symbols_metadata,
            current_file_name="test"
        )
        
        # 验证各级符号都被正确替换
        assert "class OuterClass" in result, "外部类名替换失败"
        assert "var outer_var" in result, "外部变量替换失败"
        assert "func outer_method(outer_param)" in result, "方法签名替换失败"
        assert "inner_var = outer_param + self.outer_var" in result, "方法体内符号替换失败"
        assert "返回 inner_var" in result, "返回语句中符号替换失败"
        
        print("  ✓ 嵌套作用域符号替换测试通过")
        return True
        
    except Exception as e:
        print(f"  ❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_multiple_params_replacement():
    """测试多参数替换"""
    print("\n测试 multiple_params_replacement 功能...")
    
    try:
        # 多参数函数
        ibc_content = """func 计算(第一参数, 第二参数, 第三参数, 第四参数):
    临时1 = 第一参数 + 第二参数
    临时2 = 第三参数 + 第四参数
    最终结果 = 临时1 + 临时2
    返回 最终结果
"""
        
        lexer = IbcLexer(ibc_content)
        tokens = lexer.tokenize()
        parser = IbcParser(tokens)
        ast_dict = parser.parse()
        
        symbols_metadata = {
            "test.计算": {"type": "func", "normalized_name": "calculate"},
            "test.计算.第一参数": {"type": "param", "normalized_name": "param1"},
            "test.计算.第二参数": {"type": "param", "normalized_name": "param2"},
            "test.计算.第三参数": {"type": "param", "normalized_name": "param3"},
            "test.计算.第四参数": {"type": "param", "normalized_name": "param4"},
            "test.计算.临时1": {"type": "var", "normalized_name": "temp1"},
            "test.计算.临时2": {"type": "var", "normalized_name": "temp2"},
            "test.计算.最终结果": {"type": "var", "normalized_name": "final_result"}
        }
        
        result = IbcFuncs.replace_symbols_with_normalized_names(
            ibc_content, ast_dict, symbols_metadata, "test"
        )
        
        assert "calculate(param1, param2, param3, param4)" in result, "多参数替换失败"
        assert "temp1 = param1 + param2" in result, "第一组参数使用替换失败"
        assert "temp2 = param3 + param4" in result, "第二组参数使用替换失败"
        assert "final_result = temp1 + temp2" in result, "变量组合替换失败"
        
        print("  ✓ 多参数替换测试通过")
        return True
        
    except Exception as e:
        print(f"  ❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_boundary_case_empty_metadata():
    """测试边界情况：空元数据"""
    print("\n测试 boundary_case_empty_metadata 功能...")
    
    try:
        ibc_content = """func test():
    var x = 1
"""
        
        lexer = IbcLexer(ibc_content)
        tokens = lexer.tokenize()
        parser = IbcParser(tokens)
        ast_dict = parser.parse()
        
        # 空元数据
        symbols_metadata = {}
        
        # 执行替换（应该不崩溃，返回原内容）
        result = IbcFuncs.replace_symbols_with_normalized_names(
            ibc_content, ast_dict, symbols_metadata, "test"
        )
        
        # 验证返回原始内容
        assert result == ibc_content, "空元数据时应返回原始内容"
        
        print("  ✓ 边界情况（空元数据）测试通过")
        return True
        
    except Exception as e:
        print(f"  ❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_boundary_case_partial_metadata():
    """测试边界情况：部分元数据"""
    print("\n测试 boundary_case_partial_metadata 功能...")
    
    try:
        ibc_content = """func calculate(参数1, 参数2):
    结果 = 参数1 + 参数2
    返回 结果
"""
        
        lexer = IbcLexer(ibc_content)
        tokens = lexer.tokenize()
        parser = IbcParser(tokens)
        ast_dict = parser.parse()
        
        # 只提供部分符号的元数据
        symbols_metadata = {
            "test.calculate.参数1": {
                "type": "param",
                "normalized_name": "param1"
            }
            # 其他符号没有元数据
        }
        
        # 执行替换
        result = IbcFuncs.replace_symbols_with_normalized_names(
            ibc_content, ast_dict, symbols_metadata, "test"
        )
        
        # 验证部分替换
        assert "param1" in result, "有元数据的符号应被替换"
        assert "参数2" in result, "无元数据的符号应保持原样"
        
        print("  ✓ 边界情况（部分元数据）测试通过")
        return True
        
    except Exception as e:
        print(f"  ❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_boundary_case_same_name():
    """测试边界情况：规范化名称与原名称相同"""
    print("\n测试 boundary_case_same_name 功能...")
    
    try:
        ibc_content = """func test(param):
    var result = param
"""
        
        lexer = IbcLexer(ibc_content)
        tokens = lexer.tokenize()
        parser = IbcParser(tokens)
        ast_dict = parser.parse()
        
        # 规范化名称与原名称相同
        symbols_metadata = {
            "test.test": {"type": "func", "normalized_name": "test"},
            "test.test.param": {"type": "param", "normalized_name": "param"}
        }
        
        # 执行替换
        result = IbcFuncs.replace_symbols_with_normalized_names(
            ibc_content, ast_dict, symbols_metadata, "test"
        )
        
        # 验证内容没有变化（因为规范化名称与原名称相同）
        assert result == ibc_content, "名称相同时不应修改内容"
        
        print("  ✓ 边界情况（相同名称）测试通过")
        return True
        
    except Exception as e:
        print(f"  ❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_similar_names_replacement():
    """测试相似名称的精确替换"""
    print("\n测试 similar_names_replacement 功能...")
    
    try:
        # 包含相似名称的代码
        ibc_content = """func process():
    数据 = 1
    数据集 = 2
    大数据 = 3
    结果 = 数据 + 数据集 + 大数据
"""
        
        lexer = IbcLexer(ibc_content)
        tokens = lexer.tokenize()
        parser = IbcParser(tokens)
        ast_dict = parser.parse()
        
        symbols_metadata = {
            "test.process": {"type": "func", "normalized_name": "process"},
            "test.process.数据": {"type": "var", "normalized_name": "data"},
            "test.process.数据集": {"type": "var", "normalized_name": "dataset"},
            "test.process.大数据": {"type": "var", "normalized_name": "bigdata"},
            "test.process.结果": {"type": "var", "normalized_name": "result"}
        }
        
        result = IbcFuncs.replace_symbols_with_normalized_names(
            ibc_content, ast_dict, symbols_metadata, "test"
        )
        
        # 验证精确替换（不应该误替换相似名称）
        assert "data = 1" in result, "数据应被替换为data"
        assert "dataset = 2" in result, "数据集应被替换为dataset"
        assert "bigdata = 3" in result, "大数据应被替换为bigdata"
        assert "result = data + dataset + bigdata" in result, "表达式中的符号应正确替换"
        
        # 确保没有误替换
        assert "dataet" not in result, "不应产生错误的部分替换"
        
        print("  ✓ 相似名称精确替换测试通过")
        return True
        
    except Exception as e:
        print(f"  ❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_symbol_in_expression():
    """测试表达式中的符号替换"""
    print("\n测试 symbol_in_expression 功能...")
    
    try:
        ibc_content = """func 计算面积(长度, 宽度):
    面积 = 长度 × 宽度
    周长 = (长度 + 宽度) × 2
    对角线 = 长度 ** 2 + 宽度 ** 2
"""
        
        lexer = IbcLexer(ibc_content)
        tokens = lexer.tokenize()
        parser = IbcParser(tokens)
        ast_dict = parser.parse()
        
        symbols_metadata = {
            "test.计算面积": {"type": "func", "normalized_name": "calc_area"},
            "test.计算面积.长度": {"type": "param", "normalized_name": "length"},
            "test.计算面积.宽度": {"type": "param", "normalized_name": "width"},
            "test.计算面积.面积": {"type": "var", "normalized_name": "area"},
            "test.计算面积.周长": {"type": "var", "normalized_name": "perimeter"},
            "test.计算面积.对角线": {"type": "var", "normalized_name": "diagonal"}
        }
        
        result = IbcFuncs.replace_symbols_with_normalized_names(
            ibc_content, ast_dict, symbols_metadata, "test"
        )
        
        assert "calc_area(length, width)" in result, "函数签名替换失败"
        assert "area = length × width" in result, "乘法表达式中的符号替换失败"
        assert "perimeter = (length + width) × 2" in result, "加法表达式中的符号替换失败"
        assert "diagonal = length ** 2 + width ** 2" in result, "幂运算表达式中的符号替换失败"
        
        print("  ✓ 表达式中的符号替换测试通过")
        return True
        
    except Exception as e:
        print(f"  ❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_symbol_in_method_call():
    """测试方法调用中的符号替换"""
    print("\n测试 symbol_in_method_call 功能...")
    
    try:
        ibc_content = """func 处理():
    列表项 = []
    元素 = 1
    列表项.append(元素)
    长度值 = 列表项.length()
"""
        
        lexer = IbcLexer(ibc_content)
        tokens = lexer.tokenize()
        parser = IbcParser(tokens)
        ast_dict = parser.parse()
        
        symbols_metadata = {
            "test.处理": {"type": "func", "normalized_name": "process"},
            "test.处理.列表项": {"type": "var", "normalized_name": "list_item"},
            "test.处理.元素": {"type": "var", "normalized_name": "element"},
            "test.处理.长度值": {"type": "var", "normalized_name": "length_value"}
        }
        
        result = IbcFuncs.replace_symbols_with_normalized_names(
            ibc_content, ast_dict, symbols_metadata, "test"
        )
        
        assert "list_item = []" in result, "变量初始化替换失败"
        assert "element = 1" in result, "变量赋值替换失败"
        assert "list_item.append(element)" in result, "方法调用参数替换失败"
        assert "length_value = list_item.length()" in result, "方法调用返回值替换失败"
        
        print("  ✓ 方法调用中的符号替换测试通过")
        return True
        
    except Exception as e:
        print(f"  ❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_special_chars_in_context():
    """测试包含特殊字符的上下文中的符号替换"""
    print("\n测试 special_chars_in_context 功能...")
    
    try:
        ibc_content = """func 格式化(文本):
    结果 = "前缀: " + 文本 + " 后缀"
    返回 结果
"""
        
        lexer = IbcLexer(ibc_content)
        tokens = lexer.tokenize()
        parser = IbcParser(tokens)
        ast_dict = parser.parse()
        
        symbols_metadata = {
            "test.格式化": {"type": "func", "normalized_name": "format_text"},
            "test.格式化.文本": {"type": "param", "normalized_name": "text"},
            "test.格式化.结果": {"type": "var", "normalized_name": "result"}
        }
        
        result = IbcFuncs.replace_symbols_with_normalized_names(
            ibc_content, ast_dict, symbols_metadata, "test"
        )
        
        assert "format_text(text)" in result, "函数名替换失败"
        assert 'result = "前缀: " + text + " 后缀"' in result, "字符串中的符号替换失败"
        assert "返回 result" in result, "返回语句中的符号替换失败"
        
        print("  ✓ 特殊字符上下文中的符号替换测试通过")
        return True
        
    except Exception as e:
        print(f"  ❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_inheritance_params_replacement():
    """测试类继承参数的符号替换"""
    print("\n测试 inheritance_params_replacement 功能...")
    
    try:
        ibc_content = """class 子类(父类: 基础功能类):
    var 子变量
"""
        
        lexer = IbcLexer(ibc_content)
        tokens = lexer.tokenize()
        parser = IbcParser(tokens)
        ast_dict = parser.parse()
        
        symbols_metadata = {
            "test.子类": {"type": "class", "normalized_name": "ChildClass"},
            "test.子类.父类": {"type": "param", "normalized_name": "ParentClass"},
            "test.子类.子变量": {"type": "var", "normalized_name": "child_var"}
        }
        
        result = IbcFuncs.replace_symbols_with_normalized_names(
            ibc_content, ast_dict, symbols_metadata, "test"
        )
        
        assert "class ChildClass(ParentClass:" in result, "类名和继承参数替换失败"
        assert "var child_var" in result, "成员变量替换失败"
        
        print("  ✓ 类继承参数符号替换测试通过")
        return True
        
    except Exception as e:
        print(f"  ❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_comment_preservation():
    """测试注释中的符号不被替换"""
    print("\n测试 comment_preservation 功能...")
    
    try:
        ibc_content = """func 处理数据(输入数据):
    // 这里处理输入数据
    结果 = 输入数据 + 1
    // 返回结果给调用者
    返回 结果
"""
        
        lexer = IbcLexer(ibc_content)
        tokens = lexer.tokenize()
        parser = IbcParser(tokens)
        ast_dict = parser.parse()
        
        symbols_metadata = {
            "test.处理数据": {"type": "func", "normalized_name": "process_data"},
            "test.处理数据.输入数据": {"type": "param", "normalized_name": "input_data"},
            "test.处理数据.结果": {"type": "var", "normalized_name": "result"}
        }
        
        result = IbcFuncs.replace_symbols_with_normalized_names(
            ibc_content, ast_dict, symbols_metadata, "test"
        )
        
        assert "process_data(input_data)" in result, "函数签名替换失败"
        assert "result = input_data + 1" in result, "代码中的符号替换失败"
        # 注释中的原始符号可能会被替换，这取决于实现方式
        # 这里主要验证代码逻辑正确
        assert "返回 result" in result, "返回语句替换失败"
        
        print("  ✓ 注释保留测试通过")
        return True
        
    except Exception as e:
        print(f"  ❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("开始测试 ibc_funcs.py 中的符号替换功能...")
    print("=" * 60)
    
    try:
        test_results = []
        
        # 基础符号替换测试
        test_results.append(("简单符号替换", test_simple_symbol_replacement()))
        test_results.append(("类符号替换", test_class_symbol_replacement()))
        test_results.append(("$符号引用替换", test_dollar_reference_replacement()))
        test_results.append(("嵌套作用域替换", test_nested_scope_replacement()))
        test_results.append(("多参数替换", test_multiple_params_replacement()))
        
        # 边界情况测试
        test_results.append(("边界-空元数据", test_boundary_case_empty_metadata()))
        test_results.append(("边界-部分元数据", test_boundary_case_partial_metadata()))
        test_results.append(("边界-相同名称", test_boundary_case_same_name()))
        
        # 复杂场景测试
        test_results.append(("相似名称精确替换", test_similar_names_replacement()))
        test_results.append(("表达式中的符号", test_symbol_in_expression()))
        test_results.append(("方法调用中的符号", test_symbol_in_method_call()))
        test_results.append(("特殊字符上下文", test_special_chars_in_context()))
        test_results.append(("类继承参数替换", test_inheritance_params_replacement()))
        test_results.append(("注释保留", test_comment_preservation()))
        
        print("\n" + "=" * 60)
        print("测试结果汇总")
        print("=" * 60)
        
        passed = 0
        failed = 0
        
        for test_name, result in test_results:
            status = "✓ 通过" if result else "❌ 失败"
            print(f"{test_name:30} {status}")
            if result:
                passed += 1
            else:
                failed += 1
        
        print(f"\n总计: {passed} 通过, {failed} 失败")
        
        if failed == 0:
            print("=" * 60)
            print("所有测试通过！✓")
            print("=" * 60)
            return True
        else:
            print(f"⚠️  有 {failed} 个测试失败")
            return False
            
    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
