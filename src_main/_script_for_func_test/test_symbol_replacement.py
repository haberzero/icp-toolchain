"""
测试符号替换功能

该脚本测试 IbcFuncs.replace_symbols_with_normalized_names 方法
验证IBC代码中的符号能否正确替换为规范化名称
"""

import sys
import os

# 添加项目根目录到Python路径
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from libs.ibc_funcs import IbcFuncs
from utils.ibc_analyzer.ibc_analyzer import analyze_ibc_code
from typedef.cmd_data_types import Colors


def test_simple_function_replacement():
    """测试简单函数符号替换"""
    print(f"\n{Colors.OKBLUE}测试1: 简单函数符号替换{Colors.ENDC}")
    
    # 原始IBC代码
    ibc_content = """description: 实现重力对球体运动状态的影响逻辑
@ 独立处理Y轴方向速度变化，与边界碰撞和摩擦模块协同工作
func apply_gravity(球实例, 时间步长):
    var 重力常数 = 9.81
    
    // 根据重力加速度更新球的垂直速度
    更新后的垂直速度 = 球实例.速度.y + 重力常数 × 时间步长
    
    // 应用新的垂直速度到球的位置上
    新位置.y = 球实例.位置.y + 更新后的垂直速度 × 时间步长
    
    // 将更新后的位置和速度写回球对象
    球实例.速度.y = 更新后的垂直速度
    球实例.位置.y = 新位置.y
"""
    
    # 解析生成AST
    ast_dict, _, _ = analyze_ibc_code(ibc_content)
    if not ast_dict:
        print(f"  {Colors.FAIL}❌ AST生成失败{Colors.ENDC}")
        return False
    
    # 构造模拟的符号元数据
    symbols_metadata = {
        "gravity.apply_gravity": {
            "type": "func",
            "normalized_name": "apply_gravity",
            "parameters": {
                "球实例": "",
                "时间步长": ""
            }
        },
        "gravity.apply_gravity.球实例": {
            "type": "param",
            "normalized_name": "ball_instance"
        },
        "gravity.apply_gravity.时间步长": {
            "type": "param",
            "normalized_name": "time_step"
        },
        "gravity.apply_gravity.重力常数": {
            "type": "var",
            "normalized_name": "gravity_constant"
        },
        "gravity.apply_gravity.更新后的垂直速度": {
            "type": "var",
            "normalized_name": "updated_vertical_velocity"
        },
        "gravity.apply_gravity.新位置": {
            "type": "var",
            "normalized_name": "new_position"
        }
    }
    
    # 执行替换
    result = IbcFuncs.replace_symbols_with_normalized_names(
        ibc_content=ibc_content,
        ast_dict=ast_dict,
        symbols_metadata=symbols_metadata,
        current_file_name="gravity"
    )
    
    # 验证结果
    print(f"\n{Colors.OKBLUE}替换后的代码:{Colors.ENDC}")
    print(result)
    
    # 检查关键替换
    checks = [
        ("apply_gravity" in result and "apply_gravity(ball_instance, time_step)" in result, "函数名和参数名"),
        ("gravity_constant" in result, "局部变量 gravity_constant"),
        ("updated_vertical_velocity" in result, "局部变量 updated_vertical_velocity"),
        ("new_position" in result, "局部变量 new_position"),
        ("球实例" not in result.split("//")[0], "原始参数名已替换"),  # 排除注释
    ]
    
    all_passed = True
    for check, desc in checks:
        if check:
            print(f"  {Colors.OKGREEN}✓ {desc} 替换正确{Colors.ENDC}")
        else:
            print(f"  {Colors.FAIL}✗ {desc} 替换失败{Colors.ENDC}")
            all_passed = False
    
    return all_passed


def test_class_with_methods():
    """测试类和方法符号替换"""
    print(f"\n{Colors.OKBLUE}测试2: 类和方法符号替换{Colors.ENDC}")
    
    ibc_content = """class FrictionManager():
    private
    var friction_coefficient: 摩擦系数常量
    
    public
    func __init__(摩擦系数):
        self.friction_coefficient = 摩擦系数
    
    func apply_friction(球对象, 时间间隔):
        计算后速度 = self.calculate_energy_loss(球对象.velocity, 时间间隔)
        球对象.velocity = 计算后速度
"""
    
    # 解析AST
    ast_dict, _, _ = analyze_ibc_code(ibc_content)
    if not ast_dict:
        print(f"  {Colors.FAIL}❌ AST生成失败{Colors.ENDC}")
        return False
    
    # 符号元数据
    symbols_metadata = {
        "friction.FrictionManager": {
            "type": "class",
            "normalized_name": "FrictionManager"
        },
        "friction.FrictionManager.friction_coefficient": {
            "type": "var",
            "normalized_name": "friction_coefficient"
        },
        "friction.FrictionManager.__init__": {
            "type": "func",
            "normalized_name": "__init__"
        },
        "friction.FrictionManager.__init__.摩擦系数": {
            "type": "param",
            "normalized_name": "friction_coef"
        },
        "friction.FrictionManager.apply_friction": {
            "type": "func",
            "normalized_name": "apply_friction"
        },
        "friction.FrictionManager.apply_friction.球对象": {
            "type": "param",
            "normalized_name": "ball_obj"
        },
        "friction.FrictionManager.apply_friction.时间间隔": {
            "type": "param",
            "normalized_name": "time_interval"
        },
        "friction.FrictionManager.apply_friction.计算后速度": {
            "type": "var",
            "normalized_name": "calculated_velocity"
        }
    }
    
    # 执行替换
    result = IbcFuncs.replace_symbols_with_normalized_names(
        ibc_content=ibc_content,
        ast_dict=ast_dict,
        symbols_metadata=symbols_metadata,
        current_file_name="friction"
    )
    
    print(f"\n{Colors.OKBLUE}替换后的代码:{Colors.ENDC}")
    print(result)
    
    # 验证
    checks = [
        ("FrictionManager" in result, "类名"),
        ("friction_coefficient" in result, "成员变量"),
        ("__init__(friction_coef)" in result, "构造函数参数"),
        ("apply_friction(ball_obj, time_interval)" in result, "方法参数"),
        ("calculated_velocity" in result, "局部变量"),
    ]
    
    all_passed = True
    for check, desc in checks:
        if check:
            print(f"  {Colors.OKGREEN}✓ {desc} 替换正确{Colors.ENDC}")
        else:
            print(f"  {Colors.FAIL}✗ {desc} 替换失败{Colors.ENDC}")
            all_passed = False
    
    return all_passed


def test_dollar_reference_replacement():
    """测试$符号引用替换"""
    print(f"\n{Colors.OKBLUE}测试3: $符号引用替换{Colors.ENDC}")
    
    ibc_content = """module src.physics.gravity
module src.physics.friction

func update_ball():
    应用重力 = $gravity.apply_gravity(self, 时间步长)
    摩擦管理器 = $friction.FrictionManager(0.5)
    新速度 = 摩擦管理器.apply_friction(self.velocity)
"""
    
    # 解析AST
    ast_dict, _, _ = analyze_ibc_code(ibc_content)
    if not ast_dict:
        print(f"  {Colors.FAIL}❌ AST生成失败{Colors.ENDC}")
        return False
    
    # 符号元数据（模拟规范化后的外部符号）
    symbols_metadata = {
        "ball.update_ball": {
            "type": "func",
            "normalized_name": "update_ball"
        },
        "ball.update_ball.时间步长": {
            "type": "var",
            "normalized_name": "time_step"
        },
        "ball.update_ball.应用重力": {
            "type": "var",
            "normalized_name": "apply_gravity_result"
        },
        "ball.update_ball.摩擦管理器": {
            "type": "var",
            "normalized_name": "friction_manager"
        },
        "ball.update_ball.新速度": {
            "type": "var",
            "normalized_name": "new_velocity"
        },
        # 注意：$引用中的符号在metadata中不需要前缀
        "gravity.apply_gravity": {
            "type": "func",
            "normalized_name": "apply_gravity"
        },
        "friction.FrictionManager": {
            "type": "class",
            "normalized_name": "FrictionManager"
        }
    }
    
    # 执行替换
    result = IbcFuncs.replace_symbols_with_normalized_names(
        ibc_content=ibc_content,
        ast_dict=ast_dict,
        symbols_metadata=symbols_metadata,
        current_file_name="ball"
    )
    
    print(f"\n{Colors.OKBLUE}替换后的代码:{Colors.ENDC}")
    print(result)
    
    # 验证
    checks = [
        ("update_ball" in result, "函数名"),
        ("time_step" in result, "参数名"),
        ("apply_gravity_result" in result, "局部变量1"),
        ("friction_manager" in result, "局部变量2"),
        ("new_velocity" in result, "局部变量3"),
        ("$gravity.apply_gravity" in result, "$引用保留"),
        ("$friction.FrictionManager" in result, "$引用保留"),
    ]
    
    all_passed = True
    for check, desc in checks:
        if check:
            print(f"  {Colors.OKGREEN}✓ {desc} 替换正确{Colors.ENDC}")
        else:
            print(f"  {Colors.FAIL}✗ {desc} 替换失败{Colors.ENDC}")
            all_passed = False
    
    return all_passed


def main():
    """运行所有测试"""
    print(f"{Colors.OKBLUE}{'='*60}{Colors.ENDC}")
    print(f"{Colors.OKBLUE}开始测试符号替换功能{Colors.ENDC}")
    print(f"{Colors.OKBLUE}{'='*60}{Colors.ENDC}")
    
    tests = [
        test_simple_function_replacement,
        test_class_with_methods,
        test_dollar_reference_replacement,
    ]
    
    results = []
    for test_func in tests:
        try:
            result = test_func()
            results.append(result)
        except Exception as e:
            print(f"\n{Colors.FAIL}测试异常: {e}{Colors.ENDC}")
            import traceback
            traceback.print_exc()
            results.append(False)
    
    # 汇总结果
    print(f"\n{Colors.OKBLUE}{'='*60}{Colors.ENDC}")
    print(f"{Colors.OKBLUE}测试汇总{Colors.ENDC}")
    print(f"{Colors.OKBLUE}{'='*60}{Colors.ENDC}")
    
    passed = sum(results)
    total = len(results)
    
    if passed == total:
        print(f"{Colors.OKGREEN}所有测试通过! ({passed}/{total}){Colors.ENDC}")
        return True
    else:
        print(f"{Colors.FAIL}部分测试失败: {passed}/{total} 通过{Colors.ENDC}")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
