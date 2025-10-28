import sys
import os

# 正确添加src_main目录到sys.path，以便能够导入libs中的模块
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from utils.ibc_analyzer.ibc_analyzer import analyze_ibc_code, IbcAnalyzerError
from typedef.ibc_data_types import AstNodeType, ModuleNode, ClassNode, FunctionNode, VariableNode, BehaviorStepNode

def test_simple_module():
    """测试简单模块声明"""
    print("测试 simple_module 函数...")
    
    code = """module test_module: 测试模块"""
    
    try:
        ast_dict = analyze_ibc_code(code)
        
        # 检查根节点和模块节点
        root_node = ast_dict[0]
        assert len(root_node.children_uids) == 1, f"预期1个子节点，实际{len(root_node.children_uids)}个"
        
        module_uid = root_node.children_uids[0]
        module_node = ast_dict[module_uid]
        assert isinstance(module_node, ModuleNode), "节点类型应为ModuleNode"
        assert module_node.identifier == "test_module", f"模块名应为test_module，实际为{module_node.identifier}"
        assert module_node.content == " 测试模块", f"模块内容应为' 测试模块'，实际为'{module_node.content}'"
        
        print("  ✓ 成功处理简单模块声明")
        return True
    except Exception as e:
        print(f"  ❌ 测试失败: {e}")
        return False

def test_function_with_params():
    """测试带参数的函数"""
    print("测试 function_with_params 函数...")
    
    code = """func 计算总价(商品列表: 商品对象数组, 折扣率: 小数):
    初始化总价为0
    遍历商品列表
    返回总价"""
    
    try:
        ast_dict = analyze_ibc_code(code)
        
        # 检查根节点和函数节点
        root_node = ast_dict[0]
        assert len(root_node.children_uids) == 1, f"预期1个子节点，实际{len(root_node.children_uids)}个"
        
        func_uid = root_node.children_uids[0]
        func_node = ast_dict[func_uid]
        assert isinstance(func_node, FunctionNode), "节点类型应为FunctionNode"
        assert func_node.identifier == "计算总价", f"函数名应为'计算总价'，实际为'{func_node.identifier}'"
        assert len(func_node.params) == 2, f"应有2个参数，实际有{len(func_node.params)}个"
        assert "商品列表" in func_node.params, "应包含'商品列表'参数"
        assert "折扣率" in func_node.params, "应包含'折扣率'参数"
        assert func_node.params["商品列表"] == " 商品对象数组", f"商品列表参数描述错误"
        assert func_node.params["折扣率"] == " 小数", f"折扣率参数描述错误"
        
        # 检查行为步骤节点
        assert len(func_node.children_uids) == 3, f"应有3个行为步骤，实际有{len(func_node.children_uids)}个"
        
        step1_node = ast_dict[func_node.children_uids[0]]
        assert isinstance(step1_node, BehaviorStepNode), "应为BehaviorStepNode类型"
        assert step1_node.content == "初始化总价为0", f"步骤内容错误"
        
        print("  ✓ 成功处理带参数的函数")
        return True
    except Exception as e:
        print(f"  ❌ 测试失败: {e}")
        return False

def test_class_with_var():
    """测试包含变量的类"""
    print("测试 class_with_var 函数...")
    
    code = """class 用户管理:
    var 用户数量: 当前在线用户数
    var 用户列表"""
    
    try:
        ast_dict = analyze_ibc_code(code)
        
        # 检查根节点和类节点
        root_node = ast_dict[0]
        assert len(root_node.children_uids) == 1, f"预期1个子节点，实际{len(root_node.children_uids)}个"
        
        class_uid = root_node.children_uids[0]
        class_node = ast_dict[class_uid]
        assert isinstance(class_node, ClassNode), "节点类型应为ClassNode"
        assert class_node.identifier == "用户管理", f"类名应为'用户管理'，实际为'{class_node.identifier}'"
        
        # 检查变量节点
        assert len(class_node.children_uids) == 2, f"应有2个变量，实际有{len(class_node.children_uids)}个"
        
        var1_node = ast_dict[class_node.children_uids[0]]
        assert isinstance(var1_node, VariableNode), "应为VariableNode类型"
        assert var1_node.identifier == "用户数量", f"变量名错误"
        assert var1_node.content == " 当前在线用户数", f"变量内容错误"
        
        var2_node = ast_dict[class_node.children_uids[1]]
        assert isinstance(var2_node, VariableNode), "应为VariableNode类型"
        assert var2_node.identifier == "用户列表", f"变量名错误"
        assert var2_node.content == "", f"变量内容应为空，实际为'{var2_node.content}'"
        
        print("  ✓ 成功处理包含变量的类")
        return True
    except Exception as e:
        print(f"  ❌ 测试失败: {e}")
        return False

def test_complex_structure():
    """测试复杂结构"""
    print("测试 complex_structure 函数...")
    
    code = """module user_system: 用户管理系统

description: 用户认证和管理系统
@ 线程安全设计
class 用户管理器:
    var 用户数据: 存储用户信息
    var 锁对象: 用于线程同步
    
    description: 添加新用户
    func 添加用户(用户名, 密码: 加密后的密码字符串):
        验证输入参数
        创建用户对象
        保存到数据库
        返回结果"""
    
    try:
        ast_dict = analyze_ibc_code(code)
        
        # 检查根节点
        root_node = ast_dict[0]
        assert len(root_node.children_uids) == 2, f"预期2个子节点，实际{len(root_node.children_uids)}个"
        
        # 检查模块节点
        module_uid = root_node.children_uids[0]
        module_node = ast_dict[module_uid]
        assert isinstance(module_node, ModuleNode), "第一个节点应为ModuleNode"
        assert module_node.identifier == "user_system", f"模块名错误"
        
        # 检查类节点
        class_uid = root_node.children_uids[1]
        class_node = ast_dict[class_uid]
        assert isinstance(class_node, ClassNode), "第二个节点应为ClassNode"
        assert class_node.identifier == "用户管理器", f"类名错误"
        assert class_node.external_desc == " 用户认证和管理系统", f"外部描述错误"
        assert class_node.intent_comment == " 线程安全设计", f"意图注释错误"
        
        # 检查类中的变量
        assert len(class_node.children_uids) == 2, f"类应有2个变量，实际有{len(class_node.children_uids)}个"
        
        # 检查类中的函数
        func_uid = class_node.children_uids[0]  # 第一个子节点是变量，但我们需要查找函数节点
        # 在AST中查找函数节点
        func_node = None
        for child_uid in class_node.children_uids:
            if isinstance(ast_dict[child_uid], FunctionNode):
                func_node = ast_dict[child_uid]
                break
        
        assert func_node is not None, "应找到函数节点"
        assert func_node.identifier == "添加用户", f"函数名错误"
        assert func_node.external_desc == " 添加新用户", f"函数外部描述错误"
        assert len(func_node.params) == 2, f"应有2个参数，实际有{len(func_node.params)}个"
        
        print("  ✓ 成功处理复杂结构")
        return True
    except Exception as e:
        print(f"  ❌ 测试失败: {e}")
        return False

def test_error_handling():
    """测试错误处理"""
    print("测试 error_handling 函数...")
    
    # 测试不完整的代码
    code = """func 不完整的函数:"""
    
    try:
        ast_dict = analyze_ibc_code(code)
        # 如果能成功解析，检查结果
        root_node = ast_dict[0]
        # 这里我们接受任何结果，只要不抛出未处理的异常即可
        print("  ✓ 成功处理错误情况（不完整代码）")
        return True
    except IbcAnalyzerError:
        # 这是预期的错误类型
        print("  ✓ 成功处理错误情况（抛出预期异常）")
        return True
    except Exception as e:
        print(f"  ❌ 测试失败: {e}")
        return False

def main():
    """主测试函数"""
    print("开始测试 Intent Behavior Code 解析器...\\n")
    
    try:
        test_results = []
        
        test_results.append(("简单模块声明", test_simple_module()))
        print()
        
        test_results.append(("带参数的函数", test_function_with_params()))
        print()
        
        test_results.append(("包含变量的类", test_class_with_var()))
        print()
        
        test_results.append(("复杂结构", test_complex_structure()))
        print()
        
        test_results.append(("错误处理", test_error_handling()))
        print()
        
        print("测试结果汇总")
        print("=" * 40)
        
        passed = 0
        failed = 0
        
        for test_name, result in test_results:
            status = "✓ 通过" if result else "❌ 失败"
            print(f"{test_name:20} {status}")
            if result:
                passed += 1
            else:
                failed += 1
        
        print(f"\\n总计: {passed} 通过, {failed} 失败")
        
        if failed == 0:
            print("🎉 所有测试通过！")
        else:
            print(f"⚠️  有 {failed} 个测试失败")
        
        return failed == 0
        
    except Exception as e:
        print(f"测试过程中发生异常: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)