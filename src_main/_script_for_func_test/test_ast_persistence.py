import sys
import os

# 添加src_main到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typedef.ibc_data_types import (
    IbcBaseAstNode, AstNodeType, ModuleNode, ClassNode, 
    FunctionNode, VariableNode, BehaviorStepNode
)
from data_store.ibc_data_store import get_instance as get_ibc_data_store
from utils.ibc_analyzer.ibc_analyzer import analyze_ibc_code


def test_ast_basic_persistence():
    """测试AST的基本持久化存储和加载"""
    
    print("=" * 60)
    print("测试 1: AST 基本持久化功能")
    print("=" * 60)
    
    # 创建测试AST
    print("\n1. 创建测试AST...")
    ast_dict = {}
    
    # 根节点
    ast_dict[0] = IbcBaseAstNode(uid=0, node_type=AstNodeType.DEFAULT)
    
    # Module节点
    module_node = ModuleNode(
        uid=1,
        parent_uid=0,
        node_type=AstNodeType.MODULE,
        identifier="TestModule",
        content="这是一个测试模块",
        line_number=1
    )
    ast_dict[1] = module_node
    ast_dict[0].add_child(1)
    
    # Class节点
    class_node = ClassNode(
        uid=2,
        parent_uid=1,
        node_type=AstNodeType.CLASS,
        identifier="TestClass",
        external_desc="测试类描述",
        intent_comment="这是意图注释",
        inh_params={"BaseClass": "基础类"},
        line_number=3
    )
    ast_dict[2] = class_node
    ast_dict[1].add_child(2)
    
    # Function节点
    func_node = FunctionNode(
        uid=3,
        parent_uid=2,
        node_type=AstNodeType.FUNCTION,
        identifier="test_function",
        external_desc="测试函数描述",
        intent_comment="函数意图",
        params={"x": "int类型参数", "y": "str类型参数"},
        line_number=5
    )
    ast_dict[3] = func_node
    ast_dict[2].add_child(3)
    
    # Variable节点
    var_node = VariableNode(
        uid=4,
        parent_uid=3,
        node_type=AstNodeType.VARIABLE,
        identifier="test_var",
        content="测试变量内容",
        external_desc="变量描述",
        intent_comment="变量意图",
        line_number=7
    )
    ast_dict[4] = var_node
    ast_dict[3].add_child(4)
    
    # BehaviorStep节点
    behavior_node = BehaviorStepNode(
        uid=5,
        parent_uid=3,
        node_type=AstNodeType.BEHAVIOR_STEP,
        content="执行某个操作",
        symbol_refs=["test_var", "another_symbol"],
        new_block_flag=True,
        line_number=9
    )
    ast_dict[5] = behavior_node
    ast_dict[3].add_child(5)
    
    print(f"   创建了 {len(ast_dict)} 个节点")
    
    # 保存AST到文件
    print("\n2. 保存AST到文件...")
    ast_manager = get_ibc_data_store()
    
    # 使用_dev_temp目录
    dev_temp_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "_dev_temp"
    )
    os.makedirs(dev_temp_dir, exist_ok=True)
    
    test_file_path = os.path.join(dev_temp_dir, "test_ast_output.json")
    
    success = ast_manager.save_ast_to_file(ast_dict, test_file_path)
    if not success:
        print(f"   ✗ 保存失败")
        return False
    print(f"   ✓ 保存成功")
    
    # 从文件加载AST
    print("\n3. 从文件加载AST...")
    loaded_ast_dict = ast_manager.load_ast_from_file(test_file_path)
    print(f"   加载了 {len(loaded_ast_dict)} 个节点")
    
    # 验证加载的AST
    print("\n4. 验证加载的AST数据...")
    all_correct = True
    
    # 验证节点数量
    if len(loaded_ast_dict) != len(ast_dict):
        print(f"   ✗ 节点数量不匹配")
        all_correct = False
    else:
        print(f"   ✓ 节点数量匹配: {len(loaded_ast_dict)}")
    
    # 验证Module节点
    loaded_module = loaded_ast_dict.get(1)
    if not isinstance(loaded_module, ModuleNode) or \
       loaded_module.identifier != module_node.identifier:
        print(f"   ✗ Module节点验证失败")
        all_correct = False
    else:
        print(f"   ✓ Module节点数据正确")
    
    # 验证Class节点
    loaded_class = loaded_ast_dict.get(2)
    if not isinstance(loaded_class, ClassNode) or \
       loaded_class.identifier != class_node.identifier or \
       loaded_class.inh_params != class_node.inh_params:
        print(f"   ✗ Class节点验证失败")
        all_correct = False
    else:
        print(f"   ✓ Class节点数据正确")
    
    # 验证Function节点
    loaded_func = loaded_ast_dict.get(3)
    if not isinstance(loaded_func, FunctionNode) or \
       loaded_func.identifier != func_node.identifier or \
       loaded_func.params != func_node.params:
        print(f"   ✗ Function节点验证失败")
        all_correct = False
    else:
        print(f"   ✓ Function节点数据正确")
    
    # 验证Variable节点
    loaded_var = loaded_ast_dict.get(4)
    if not isinstance(loaded_var, VariableNode) or \
       loaded_var.identifier != var_node.identifier:
        print(f"   ✗ Variable节点验证失败")
        all_correct = False
    else:
        print(f"   ✓ Variable节点数据正确")
    
    # 验证BehaviorStep节点
    loaded_behavior = loaded_ast_dict.get(5)
    if not isinstance(loaded_behavior, BehaviorStepNode) or \
       loaded_behavior.content != behavior_node.content or \
       loaded_behavior.symbol_refs != behavior_node.symbol_refs:
        print(f"   ✗ BehaviorStep节点验证失败")
        all_correct = False
    else:
        print(f"   ✓ BehaviorStep节点数据正确")
    
    # 验证树结构
    print("\n5. 验证AST树结构...")
    if loaded_ast_dict[0].children_uids != ast_dict[0].children_uids or \
       loaded_ast_dict[1].children_uids != ast_dict[1].children_uids or \
       loaded_ast_dict[2].children_uids != ast_dict[2].children_uids:
        print(f"   ✗ 树结构验证失败")
        all_correct = False
    else:
        print(f"   ✓ 树结构正确")
    
    return all_correct


def test_ast_with_real_ibc_code():
    """测试使用真实IBC代码的AST持久化"""
    
    print("\n" + "=" * 60)
    print("测试 2: 真实 IBC 代码的 AST 持久化")
    print("=" * 60)
    
    # 示例IBC代码
    ibc_code = """
module UserManagement: 用户管理模块

class User():
    var username: 用户名
    var email: 电子邮件地址
    
    description: 用户登录功能
    @ 验证用户名和密码，返回登录结果
    func login(
        username: 用户名,
        password: 密码
    ):
        检查用户名是否存在 $username$
        验证密码是否正确 $password$
        如果验证成功:
            创建会话
            返回成功
        否则:
            返回失败
    """
    
    # 1. 解析IBC代码生成AST
    print("\n1. 解析IBC代码...")
    success, ast_dict, _ = analyze_ibc_code(ibc_code)
    if not success or not ast_dict:
        print(f"   ✗ 解析失败")
        return False
    print(f"   ✓ 解析成功，生成 {len(ast_dict)} 个节点")
    
    # 2. 保存AST到文件
    print("\n2. 保存AST到文件...")
    ast_manager = get_ibc_data_store()
    
    # 使用_dev_temp目录
    dev_temp_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "_dev_temp"
    )
    os.makedirs(dev_temp_dir, exist_ok=True)
    
    save_path = os.path.join(dev_temp_dir, "user_management_ast.json")
    
    success = ast_manager.save_ast_to_file(ast_dict, save_path)
    if not success:
        print(f"   ✗ 保存失败")
        return False
    print(f"   ✓ 保存成功")
    
    # 3. 从文件加载AST
    print("\n3. 从文件加载AST...")
    loaded_ast = ast_manager.load_ast_from_file(save_path)
    print(f"   ✓ 成功加载 {len(loaded_ast)} 个节点")
    
    # 4. 验证加载的AST
    print("\n4. 验证加载的AST内容...")
    all_correct = True
    
    # 验证节点数量
    if len(loaded_ast) != len(ast_dict):
        print(f"   ✗ 节点数量不匹配")
        all_correct = False
    else:
        print(f"   ✓ 节点数量匹配: {len(loaded_ast)}")
    
    # 验证关键节点类型
    module_count = sum(1 for node in loaded_ast.values() if isinstance(node, ModuleNode))
    class_count = sum(1 for node in loaded_ast.values() if isinstance(node, ClassNode))
    func_count = sum(1 for node in loaded_ast.values() if isinstance(node, FunctionNode))
    var_count = sum(1 for node in loaded_ast.values() if isinstance(node, VariableNode))
    
    print(f"   - Module节点: {module_count}")
    print(f"   - Class节点: {class_count}")
    print(f"   - Function节点: {func_count}")
    print(f"   - Variable节点: {var_count}")
    
    if module_count != 1 or class_count != 1 or func_count != 1 or var_count != 2:
        print(f"   ✗ 节点类型数量不正确")
        all_correct = False
    else:
        print(f"   ✓ 节点类型正确")
    
    # 验证关键节点数据
    for uid, node in loaded_ast.items():
        if isinstance(node, ModuleNode):
            if node.identifier != "UserManagement":
                print(f"   ✗ Module节点标识符错误: {node.identifier}")
                all_correct = False
        elif isinstance(node, ClassNode):
            if node.identifier != "User":
                print(f"   ✗ Class节点标识符错误: {node.identifier}")
                all_correct = False
        elif isinstance(node, FunctionNode):
            if node.identifier != "login":
                print(f"   ✗ Function节点标识符错误: {node.identifier}")
                all_correct = False
            elif len(node.params) != 2:
                print(f"   ✗ Function节点参数数量错误: 期望2个，实际{len(node.params)}个")
                print(f"      参数内容: {node.params}")
                all_correct = False
    
    if all_correct:
        print(f"   ✓ 关键节点数据正确")
    
    return all_correct


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("AST 数据管理器测试套件")
    print("=" * 60)
    
    try:
        # 运行测试1：基本持久化功能
        result1 = test_ast_basic_persistence()
        
        # 运行测试2：真实IBC代码
        result2 = test_ast_with_real_ibc_code()
        
        # 汇总结果
        print("\n" + "=" * 60)
        print("测试结果汇总")
        print("=" * 60)
        print(f"测试 1 - AST 基本持久化功能: {'\u2713 通过' if result1 else '\u2717 失败'}")
        print(f"测试 2 - 真实 IBC 代码的 AST 持久化: {'\u2713 通过' if result2 else '\u2717 失败'}")
        print("=" * 60)
        
        if result1 and result2:
            print("✓ 所有测试通过！")
        else:
            print("✗ 有测试失败，请检查输出")
        print("=" * 60 + "\n")
        
    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
