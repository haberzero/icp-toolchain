import sys
import os

# 添加src_main到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typedef.ibc_data_types import (
    AstNode, AstNodeType, ModuleNode, ClassNode, 
    FunctionNode, VariableNode, BehaviorStepNode
)
from data_exchange.ast_data_manager import get_instance as get_ast_data_manager


def test_ast_persistence():
    """测试AST的持久化存储和加载"""
    
    print("=" * 60)
    print("测试 AST 持久化存储和加载")
    print("=" * 60)
    
    # 创建测试AST
    print("\n1. 创建测试AST...")
    ast_dict = {}
    
    # 根节点
    ast_dict[0] = AstNode(uid=0, node_type=AstNodeType.DEFAULT)
    
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
        inh_params={"param1": "value1", "param2": "value2"},
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
        params={"x": "int", "y": "str"},
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
        symbol_refs=["@test_var", "@another_symbol"],
        new_block_flag=True,
        line_number=9
    )
    ast_dict[5] = behavior_node
    ast_dict[3].add_child(5)
    
    print(f"   创建了 {len(ast_dict)} 个节点")
    print(f"   - 根节点: uid=0")
    print(f"   - Module节点: uid=1, identifier={module_node.identifier}")
    print(f"   - Class节点: uid=2, identifier={class_node.identifier}")
    print(f"   - Function节点: uid=3, identifier={func_node.identifier}")
    print(f"   - Variable节点: uid=4, identifier={var_node.identifier}")
    print(f"   - BehaviorStep节点: uid=5")
    
    # 保存AST到文件
    print("\n2. 保存AST到文件...")
    ast_manager = get_ast_data_manager()
    test_file_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), 
        "test_ast_output.json"
    )
    
    success = ast_manager.save_ast_to_file(ast_dict, test_file_path)
    if success:
        print(f"   ✓ 保存成功: {test_file_path}")
    else:
        print(f"   ✗ 保存失败")
        return
    
    # 从文件加载AST
    print("\n3. 从文件加载AST...")
    loaded_ast_dict = ast_manager.load_ast_from_file(test_file_path)
    print(f"   加载了 {len(loaded_ast_dict)} 个节点")
    
    # 验证加载的AST
    print("\n4. 验证加载的AST数据...")
    all_correct = True
    
    # 验证节点数量
    if len(loaded_ast_dict) != len(ast_dict):
        print(f"   ✗ 节点数量不匹配: 期望{len(ast_dict)}, 实际{len(loaded_ast_dict)}")
        all_correct = False
    else:
        print(f"   ✓ 节点数量匹配: {len(loaded_ast_dict)}")
    
    # 验证Module节点
    if 1 in loaded_ast_dict:
        loaded_module = loaded_ast_dict[1]
        if isinstance(loaded_module, ModuleNode):
            if (loaded_module.identifier == module_node.identifier and
                loaded_module.content == module_node.content and
                loaded_module.uid == module_node.uid):
                print(f"   ✓ Module节点数据正确")
            else:
                print(f"   ✗ Module节点数据不匹配")
                all_correct = False
        else:
            print(f"   ✗ Module节点类型错误: {type(loaded_module)}")
            all_correct = False
    
    # 验证Class节点
    if 2 in loaded_ast_dict:
        loaded_class = loaded_ast_dict[2]
        if isinstance(loaded_class, ClassNode):
            if (loaded_class.identifier == class_node.identifier and
                loaded_class.external_desc == class_node.external_desc and
                loaded_class.intent_comment == class_node.intent_comment and
                loaded_class.inh_params == class_node.inh_params):
                print(f"   ✓ Class节点数据正确")
            else:
                print(f"   ✗ Class节点数据不匹配")
                all_correct = False
        else:
            print(f"   ✗ Class节点类型错误: {type(loaded_class)}")
            all_correct = False
    
    # 验证Function节点
    if 3 in loaded_ast_dict:
        loaded_func = loaded_ast_dict[3]
        if isinstance(loaded_func, FunctionNode):
            if (loaded_func.identifier == func_node.identifier and
                loaded_func.params == func_node.params and
                loaded_func.children_uids == func_node.children_uids):
                print(f"   ✓ Function节点数据正确")
            else:
                print(f"   ✗ Function节点数据不匹配")
                print(f"      期望children: {func_node.children_uids}")
                print(f"      实际children: {loaded_func.children_uids}")
                all_correct = False
        else:
            print(f"   ✗ Function节点类型错误: {type(loaded_func)}")
            all_correct = False
    
    # 验证Variable节点
    if 4 in loaded_ast_dict:
        loaded_var = loaded_ast_dict[4]
        if isinstance(loaded_var, VariableNode):
            if (loaded_var.identifier == var_node.identifier and
                loaded_var.content == var_node.content):
                print(f"   ✓ Variable节点数据正确")
            else:
                print(f"   ✗ Variable节点数据不匹配")
                all_correct = False
        else:
            print(f"   ✗ Variable节点类型错误: {type(loaded_var)}")
            all_correct = False
    
    # 验证BehaviorStep节点
    if 5 in loaded_ast_dict:
        loaded_behavior = loaded_ast_dict[5]
        if isinstance(loaded_behavior, BehaviorStepNode):
            if (loaded_behavior.content == behavior_node.content and
                loaded_behavior.symbol_refs == behavior_node.symbol_refs and
                loaded_behavior.new_block_flag == behavior_node.new_block_flag):
                print(f"   ✓ BehaviorStep节点数据正确")
            else:
                print(f"   ✗ BehaviorStep节点数据不匹配")
                all_correct = False
        else:
            print(f"   ✗ BehaviorStep节点类型错误: {type(loaded_behavior)}")
            all_correct = False
    
    # 验证树结构
    print("\n5. 验证AST树结构...")
    if loaded_ast_dict[0].children_uids == ast_dict[0].children_uids:
        print(f"   ✓ 根节点children正确: {loaded_ast_dict[0].children_uids}")
    else:
        print(f"   ✗ 根节点children不匹配")
        all_correct = False
    
    if loaded_ast_dict[1].children_uids == ast_dict[1].children_uids:
        print(f"   ✓ Module节点children正确: {loaded_ast_dict[1].children_uids}")
    else:
        print(f"   ✗ Module节点children不匹配")
        all_correct = False
    
    if loaded_ast_dict[2].children_uids == ast_dict[2].children_uids:
        print(f"   ✓ Class节点children正确: {loaded_ast_dict[2].children_uids}")
    else:
        print(f"   ✗ Class节点children不匹配")
        all_correct = False
    
    # 最终结果
    print("\n" + "=" * 60)
    if all_correct:
        print("✓ 所有测试通过！AST持久化功能正常工作")
    else:
        print("✗ 部分测试失败，请检查输出")
    print("=" * 60)
    
    return all_correct


if __name__ == "__main__":
    test_ast_persistence()
