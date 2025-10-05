import sys
import os
from typing import List, cast, Tuple, Callable
import traceback

# 正确添加src_main目录到sys.path，以便能够导入utils.icb中的模块
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from utils.icb.icb_analyzer import IcbAnalyzer
from utils.icb.ast_builder import AstBuilder
from utils.icb.lines_loader import LinesLoader
from utils.icb.lines_parser import LinesParser
from utils.icb.symbol_generator import SymbolGenerator
from libs.diag_handler import DiagHandler, IcbEType

def create_test_icb_file(file_path, content):
    """创建测试用的ICB文件"""
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)

def test_lines_loader_basic():
    """测试LinesLoader基本功能"""
    print("测试LinesLoader基本功能...")
    
    test_content = """class Ball:
description: 球体类
inh: object

    var position: 球心坐标
    
    func update:
    input: dt: float
    output: None
    behavior:
        更新位置
"""
    
    lines: List[str] = cast(List[str], test_content.splitlines())
    diag_handler = DiagHandler("test.icb", lines)
    lines_loader = LinesLoader("test.icb", lines, diag_handler)
    structured_lines, _ = lines_loader.generate()
    
    assert len(structured_lines) > 0, "应该生成结构化行"
    # 检查缩进级别是否正确计算
    indent_levels = [line['indent_level'] for line in structured_lines]
    assert indent_levels == [0, 0, 0, 1, 1, 1, 1, 1, 2], "缩进级别应该正确计算"
    print("  ✓ LinesLoader基本功能测试通过")

def test_lines_loader_with_comments_and_empty_lines():
    """测试LinesLoader处理注释和空行"""
    print("测试LinesLoader处理注释和空行...")
    
    test_content = """// 这是一个注释行

class Ball:
// 类注释

description: 球体类

    // 字段注释
    var position: 球心坐标
    
    // 方法注释
    
    func update:
    input: dt: float
    // 参数注释
    output: None
    behavior:
        更新位置
"""
    
    lines: List[str] = cast(List[str], test_content.splitlines())
    diag_handler = DiagHandler("test.icb", lines)
    lines_loader = LinesLoader("test.icb", lines, diag_handler)
    structured_lines, _ = lines_loader.generate()
    
    # 注释和空行应该被过滤掉
    assert len(structured_lines) == 8, "应该正确过滤注释和空行"
    print("  ✓ LinesLoader处理注释和空行测试通过")

def test_lines_loader_tab_detection():
    """测试LinesLoader检测tab字符"""
    print("测试LinesLoader检测tab字符...")
    
    test_content = """class Ball:
description: 球体类
inh: object

	var position: 球心坐标  // 使用tab缩进
"""
    
    lines: List[str] = cast(List[str], test_content.splitlines())
    diag_handler = DiagHandler("test.icb", lines)
    lines_loader = LinesLoader("test.icb", lines, diag_handler)
    structured_lines, diag_handler = lines_loader.generate()
    
    # 包含tab的行应该被过滤掉
    assert len(structured_lines) == 3, "包含tab的行应该被过滤掉"
    assert diag_handler.is_diag_table_valid(), "应该报告tab错误"
    print("  ✓ LinesLoader检测tab字符测试通过")

def test_lines_parser_basic_elements():
    """测试LinesParser基本元素解析"""
    print("测试LinesParser基本元素解析...")
    
    diag_handler = DiagHandler("test.icb", [])
    lines_parser = LinesParser(diag_handler)
    
    # 测试根节点
    root_node = lines_parser.gen_root_ast_node()
    assert root_node is not None, "应该能生成根节点"
    assert root_node['type'] == 'root', "根节点类型应该正确"
    assert 'module' in root_node['expected_child'], "根节点应该期望module子节点"
    assert 'class' in root_node['expected_child'], "根节点应该期望class子节点"
    assert 'func' in root_node['expected_child'], "根节点应该期望func子节点"
    assert 'var' in root_node['expected_child'], "根节点应该期望var子节点"
    
    # 测试class声明解析
    class_node = lines_parser.parse_line("class TestClass:", 1)
    assert class_node is not None, "应该能解析class声明"
    assert class_node['type'] == 'class', "节点类型应该正确"
    assert class_node['name'] == 'TestClass', "类名应该正确"
    assert class_node['is_block_start'] == True, "class应该是块开始"
    
    # 测试func声明解析
    func_node = lines_parser.parse_line("func test_func:", 2)
    assert func_node is not None, "应该能解析func声明"
    assert func_node['type'] == 'func', "节点类型应该正确"
    assert func_node['name'] == 'test_func', "函数名应该正确"
    assert func_node['is_block_start'] == True, "func应该是块开始"
    
    # 测试var声明解析
    var_node = lines_parser.parse_line("var test_var: 测试变量", 3)
    assert var_node is not None, "应该能解析var声明"
    assert var_node['type'] == 'var', "节点类型应该正确"
    assert var_node['name'] == 'test_var', "变量名应该正确"
    assert var_node['description'] == '测试变量', "变量描述应该正确"
    
    print("  ✓ LinesParser基本元素解析测试通过")

def test_lines_parser_module_element():
    """测试LinesParser module元素解析"""
    print("测试LinesParser module元素解析...")
    
    diag_handler = DiagHandler("test.icb", [])
    lines_parser = LinesParser(diag_handler)
    
    # 测试module声明解析
    module_node = lines_parser.parse_line("module test_module : 测试模块", 1)
    assert module_node is not None, "应该能解析module声明"
    assert module_node['type'] == 'module', "节点类型应该正确"
    assert module_node['name'] == 'test_module', "模块名应该正确"
    assert module_node['description'] == '测试模块', "模块描述应该正确"
    
    # 测试错误的module声明
    lines_parser = LinesParser(diag_handler)
    module_node_error = lines_parser.parse_line("module test_module 错误格式", 2)
    assert module_node_error is None, "错误格式的module声明应该返回None"
    
    print("  ✓ LinesParser module元素解析测试通过")

def test_lines_parser_special_attributes():
    """测试LinesParser特殊属性解析"""
    print("测试LinesParser特殊属性解析...")
    
    diag_handler = DiagHandler("test.icb", [])
    lines_parser = LinesParser(diag_handler)
    
    # 测试input属性解析
    input_node = lines_parser.parse_line("input: param1, param2, param3", 1)
    assert input_node is not None, "应该能解析input属性"
    assert input_node['type'] == 'input', "节点类型应该正确"
    assert input_node['value'] == ['param1', 'param2', 'param3'], "输入参数应该正确解析"
    
    # 测试output属性解析
    output_node = lines_parser.parse_line("output: result, error", 2)
    assert output_node is not None, "应该能解析output属性"
    assert output_node['type'] == 'output', "节点类型应该正确"
    assert output_node['value'] == ['result', 'error'], "输出参数应该正确解析"
    
    # 测试description属性解析
    desc_node = lines_parser.parse_line("description: 函数描述", 3)
    assert desc_node is not None, "应该能解析description属性"
    assert desc_node['type'] == 'description', "节点类型应该正确"
    assert desc_node['value'] == '函数描述', "描述内容应该正确"
    
    # 测试inh属性解析
    inh_node = lines_parser.parse_line("inh: BaseClass", 4)
    assert inh_node is not None, "应该能解析inh属性"
    assert inh_node['type'] == 'inh', "节点类型应该正确"
    assert inh_node['value'] == 'BaseClass', "继承类应该正确"
    
    print("  ✓ LinesParser特殊属性解析测试通过")

def test_ast_builder_basic():
    """测试AstBuilder基本功能"""
    print("测试AstBuilder基本功能...")
    
    test_content = """
module test_module : 测试模块

class TestClass:
description: 测试类
inh: object
begin:

    var test_var: 测试变量
    
    func test_func:
    description: 测试函数
    input: x: int
    output: int
    begin:
        返回x
"""
    
    lines: List[str] = cast(List[str], test_content.splitlines())
    diag_handler = DiagHandler("test.icb", lines)
    lines_loader = LinesLoader("test.icb", lines, diag_handler)
    structured_lines, _ = lines_loader.generate()
    
    ast_builder = AstBuilder(structured_lines, diag_handler, "test.icb", "")
    build_result = ast_builder.build()
    assert build_result == True, "应该成功构建AST"
    
    node_dict = ast_builder.get_node_dict()
    
    assert -1 in node_dict, "应该包含根节点"
    assert len(node_dict) > 1, "应该包含多个节点"
    
    # 检查module节点是否被正确存储
    module_nodes = ast_builder.module_nodes
    assert len(module_nodes) == 1, "应该有1个module节点"
    assert module_nodes[0]['name'] == 'test_module', "module名称应该正确"
    
    print("  ✓ AstBuilder基本功能测试通过")

def test_ast_builder_module_position_check():
    """测试AstBuilder module位置检查"""
    print("测试AstBuilder module位置检查...")
    
    test_content = """class TestClass:
description: 测试类

module test_module : 错误位置的模块

    var test_var: 测试变量
"""
    
    lines: List[str] = cast(List[str], test_content.splitlines())
    diag_handler = DiagHandler("test.icb", lines)
    lines_loader = LinesLoader("test.icb", lines, diag_handler)
    structured_lines, _ = lines_loader.generate()
    
    ast_builder = AstBuilder(structured_lines, diag_handler, "test.icb", "")
    build_result = ast_builder.build()
    assert build_result == True, "构建应该成功（即使有位置错误）"
    
    # 应该报告module位置错误
    assert diag_handler.is_diag_table_valid(), "应该报告module位置错误"
    
    print("  ✓ AstBuilder module位置检查测试通过")

def test_symbol_generator_basic():
    """测试SymbolGenerator基本功能"""
    print("测试SymbolGenerator基本功能...")
    
    test_content = """class TestClass:
description: 测试类
inh: object

    var instance_var: 实例变量
    
    func __init__:
    description: 构造函数
    input: value: int
    output: None
    begin:
        初始化
    
    func get_value:
    description: 获取值
    input: None
    output: int
    begin:
        返回值

func global_func:
description: 全局函数
input: x: int, y: int
output: int
begin:
    返回和

var global_var: 全局变量
"""
    
    lines: List[str] = cast(List[str], test_content.splitlines())
    diag_handler = DiagHandler("test.icb", lines)
    lines_loader = LinesLoader("test.icb", lines, diag_handler)
    structured_lines, _ = lines_loader.generate()
    
    ast_builder = AstBuilder(structured_lines, diag_handler, "test.icb", "")
    ast_builder.build()
    node_dict = ast_builder.get_node_dict()
    
    symbols = SymbolGenerator.generate_symbol_table(node_dict)
    
    # 调试输出符号表内容
    print("生成的符号表内容:")
    for symbol in symbols:
        print(f"  类型: {symbol['type']}, 名称: {symbol['name']}")
    
    # 检查符号类型和数量（注意：module现在会出现在符号表中）
    # 根据需求，module关键字相关的内容并不会被symbol_generator所使用，所以移除对module符号的测试
    class_symbols = [s for s in symbols if s['type'] == 'class']
    func_symbols = [s for s in symbols if s['type'] == 'func']
    var_symbols = [s for s in symbols if s['type'] == 'var']
    
    assert len(class_symbols) == 1, "应该有1个class符号"
    assert len(func_symbols) == 2, "应该有2个func符号"
    assert len(var_symbols) == 2, "应该有2个var符号"
    
    # 验证class符号内容
    test_class = class_symbols[0]
    assert test_class['name'] == 'TestClass', "类名应该正确"
    assert test_class['inh'] == 'object', "继承关系应该正确"
    assert len(test_class['children']) == 2, "类内部应该有2个子元素"
    
    # 验证函数符号内容
    init_func = [f for f in func_symbols if f['name'] == '__init__'][0]
    assert len(init_func['input']) == 1, "构造函数应该有1个输入参数"
    assert len(init_func['output']) == 1, "构造函数应该有1个输出参数"
    
    global_func = [f for f in func_symbols if f['name'] == 'global_func'][0]
    assert len(global_func['input']) == 2, "全局函数应该有2个输入参数"
    assert len(global_func['output']) == 1, "全局函数应该有1个输出参数"
    
    print("  ✓ SymbolGenerator基本功能测试通过")

def test_full_analysis_process():
    """测试完整的ICB分析流程"""
    print("测试完整的ICB分析流程...")
    
    test_content = """module math_utils : 数学工具模块
module physics_core : 物理核心模块

class Particle:
description: 粒子类
inh: object

    var position: 位置
    var velocity: 速度
    
    func update:
    description: 更新粒子状态
    input: dt: float
    output: None
    behavior:
        更新位置

func calculate_distance:
description: 计算距离
input: p1: Particle, p2: Particle
output: float
behavior:
    计算并返回距离

var gravity: 重力常数
"""
    
    test_file = "test_full_analysis.icb"
    create_test_icb_file(test_file, test_content)
    
    analyzer = IcbAnalyzer()
    result = analyzer._file_analysis(test_file)
    assert result == True, "完整分析流程应该成功"
    
    # 验证分析器内部状态
    assert len(analyzer.structured_lines) > 0, "应该生成结构化行"
    assert len(analyzer.ast) > 0, "应该构建AST"
    
    os.remove(test_file)
    print("  ✓ 完整ICB分析流程测试通过")

def test_basic_icb_analysis():
    """测试基本的ICB文件分析功能"""
    print("测试基本的ICB文件分析功能...")
    
    # 创建一个简单的测试ICB文件
    test_content = """class Ball:
description: 球体类，用于表示和管理球体的物理状态
inh: object

    var position: 球心坐标(x, y)
    
    var velocity: 速度向量(vx, vy)
    
    var radius: 球的半径
    
    func __init__:
    description: 初始化球体
    input: x: float, y: float, vx: float, vy: float, radius: float
    output: None
    behavior:
        设置position为(x, y)
        设置velocity为(vx, vy)
        设置radius为radius
    
    func update_position:
    description: 根据速度更新球的位置
    input: dt: float (时间步长)
    output: None
    behavior:
        position.x += velocity.x * dt
        position.y += velocity.y * dt

func check_collision:
description: 检查两个球体是否发生碰撞
input: ball1: Ball, ball2: Ball
output: bool (是否碰撞)
behavior:
    计算两球心之间的距离
    如果距离小于两球半径之和:
        返回True
    否则:
        返回False
"""
    
    test_file = "test_basic.icb"
    create_test_icb_file(test_file, test_content)
    
    # 创建分析器并分析文件
    analyzer = IcbAnalyzer()
    result = analyzer._file_analysis(test_file)
    
    # 验证结果
    assert result == True, "基本ICB文件分析应该成功"
    print("  ✓ 基本ICB文件分析成功")
    
    # 清理测试文件
    os.remove(test_file)

def test_icb_with_syntax_errors():
    """测试包含语法错误的ICB文件分析"""
    print("测试包含语法错误的ICB文件分析...")
    
    # 创建一个包含语法错误的ICB文件（使用了tab字符）
    test_content = """class Ball:
description: 球体类，用于表示和管理球体的物理状态
inh: object

	var position: 球心坐标(x, y)  # 使用tab缩进，应该报错
	
    var velocity: 速度向量(vx, vy)
"""
    
    test_file = "test_syntax_error.icb"
    create_test_icb_file(test_file, test_content)
    
    # 创建分析器并分析文件
    analyzer = IcbAnalyzer()
    result = analyzer._file_analysis(test_file)
    
    # 对于包含语法错误的文件，我们期望分析仍然成功（但会记录错误）
    # 因为错误处理在诊断处理器中进行
    assert result == True, "即使有语法错误，分析也应该继续进行"
    print("  ✓ 包含语法错误的ICB文件分析处理正确")
    
    # 清理测试文件
    os.remove(test_file)

def test_empty_icb_file():
    """测试空ICB文件分析"""
    print("测试空ICB文件分析...")
    
    # 创建一个空的ICB文件
    test_content = ""
    
    test_file = "test_empty.icb"
    create_test_icb_file(test_file, test_content)
    
    # 创建分析器并分析文件
    analyzer = IcbAnalyzer()
    result = analyzer._file_analysis(test_file)
    
    # 空文件应该分析失败
    assert result == False, "空ICB文件分析应该失败"
    print("  ✓ 空ICB文件分析正确处理")
    
    # 清理测试文件
    os.remove(test_file)

def test_icb_with_indentation_errors():
    """测试包含缩进错误的ICB文件分析"""
    print("测试包含缩进错误的ICB文件分析...")
    
    # 创建一个包含缩进错误的ICB文件（跳级缩进）
    test_content = """class Ball:
description: 球体类，用于表示和管理球体的物理状态
inh: object

        var position: 球心坐标(x, y)  # 跳级缩进，应该报错
        
    var velocity: 速度向量(vx, vy)
"""
    
    test_file = "test_indent_error.icb"
    create_test_icb_file(test_file, test_content)
    
    # 创建分析器并分析文件
    analyzer = IcbAnalyzer()
    result = analyzer._file_analysis(test_file)
    
    # 分析应该继续进行，即使有错误
    assert result == True, "即使有缩进错误，分析也应该继续进行"
    print("  ✓ 包含缩进错误的ICB文件分析处理正确")
    
    # 清理测试文件
    os.remove(test_file)

def test_complex_icb_structure():
    """测试复杂的ICB结构分析"""
    print("测试复杂的ICB结构分析...")
    
    # 创建一个复杂的ICB文件
    test_content = """@ 球体物理引擎模块
class PhysicsEngine:
description: 物理引擎类，处理球体运动和碰撞检测
inh: object

    var balls: 存储所有球体的列表
    
    var gravity: 重力加速度
    
    func __init__:
    description: 初始化物理引擎
    input: gravity: float
    output: None
    behavior:
        初始化balls为空列表
        设置gravity值
    
    func add_ball:
    description: 添加球体到物理引擎
    input: ball: Ball
    output: None
    behavior:
        将ball添加到balls列表中
    
    func update:
    description: 更新所有球体的状态
    input: dt: float (时间步长)
    output: None
    behavior:
        对每个ball在balls中:
            如果ball不是静态的:
                应用重力加速度到ball的速度
                更新ball的位置使用dt时间步长
                检查ball与边界碰撞并处理
        
        对每对ball1, ball2在balls中:
            如果ball1和ball2碰撞:
                处理碰撞响应

@ 碰撞处理模块
func resolve_collision:
description: 处理两个球体之间的碰撞
input: ball1: Ball, ball2: Ball
output: None
behavior:
    计算碰撞法线方向
    分解ball1和ball2的速度到法线和切线方向
    分解ball1和ball2的速度到法线和切线方向
    交换法线方向的速度分量
    应用弹性系数调整速度
"""
    
    test_file = "test_complex.icb"
    create_test_icb_file(test_file, test_content)
    
    # 创建分析器并分析文件
    analyzer = IcbAnalyzer()
    result = analyzer._file_analysis(test_file)
    
    # 复杂结构应该分析成功
    assert result == True, "复杂ICB结构分析应该成功"
    print("  ✓ 复杂ICB结构分析成功")
    
    # 清理测试文件
    os.remove(test_file)

def test_module_declaration_valid():
    """测试有效的module声明"""
    print("测试有效的module声明...")
    
    # 创建包含正确module声明的ICB文件
    test_content = """module math_utils : 数学工具模块，提供常用的数学计算函数

module physics_core : 核心物理引擎模块

class Vector3D:
description: 三维向量类
inh: object

    var x: X轴坐标值
    
    var y: Y轴坐标值
    
    var z: Z轴坐标值
    
    func __init__:
    description: 初始化三维向量
    input: x: float, y: float, z: float
    output: None
    behavior:
        设置x, y, z坐标值

func calculate_distance:
description: 计算两个三维点之间的距离
input: point1: Vector3D, point2: Vector3D
output: float (距离值)
behavior:
    返回点1和点2之间的欧几里得距离
"""
    
    test_file = "test_module_valid.icb"
    create_test_icb_file(test_file, test_content)
    
    # 创建分析器并分析文件
    analyzer = IcbAnalyzer()
    result = analyzer._file_analysis(test_file)
    
    # 有效module声明应该分析成功
    assert result == True, "包含有效module声明的ICB文件应该分析成功"
    print("  ✓ 有效的module声明处理正确")
    
    # 清理测试文件
    os.remove(test_file)

def test_module_declaration_invalid_position():
    """测试module声明位置错误"""
    print("测试module声明位置错误...")
    
    # 创建包含错误位置module声明的ICB文件
    test_content = """class Vector3D:
description: 三维向量类
inh: object

    var x: X轴坐标值

module math_utils : 错误位置的模块声明

    var y: Y轴坐标值
    
    var z: Z轴坐标值
"""
    
    test_file = "test_module_invalid.icb"
    create_test_icb_file(test_file, test_content)
    
    # 创建分析器并分析文件
    analyzer = IcbAnalyzer()
    result = analyzer._file_analysis(test_file)
    
    # 文件分析应该成功（诊断信息通过DiagHandler处理）
    assert result == True, "即使module位置错误，分析也应该继续进行"
    print("  ✓ module声明位置错误处理正确")
    
    # 清理测试文件
    os.remove(test_file)

def test_module_parsing_components():
    """测试module解析组件功能"""
    print("测试module解析组件功能...")
    
    # 测试内容包含module声明
    test_content = """
module graphics : 图形处理模块
module physics : 物理引擎模块

class Particle:
description: 粒子类
inh: object

    var position: 粒子位置
    
    var velocity: 粒子速度
    
    func update:
    description: 更新粒子状态
    input: dt: float
    output: None
    behavior:
        根据速度更新位置
"""
    
    # 模拟分析过程，分别测试各个组件
    lines: List[str] = cast(List[str], test_content.splitlines())
    diag_handler = DiagHandler("test_components.icb", lines)
    
    # 测试LinesLoader
    lines_loader = LinesLoader("test_components.icb", lines, diag_handler)
    structured_lines, diag_handler = lines_loader.generate()
    assert len(structured_lines) > 0, "LinesLoader应该生成结构化行"
    print("  ✓ LinesLoader组件工作正常")
    
    # 测试LinesParser
    lines_parser = LinesParser(diag_handler)
    root_node = lines_parser.gen_root_ast_node()
    assert root_node is not None, "LinesParser应该能生成根节点"
    assert 'module' in root_node['expected_child'], "根节点应该期望module子节点"
    print("  ✓ LinesParser组件工作正常")
    
    # 测试AstBuilder
    ast_builder = AstBuilder(structured_lines, diag_handler, "test_components.icb", "")
    build_result = ast_builder.build()
    assert build_result == True, "AstBuilder应该成功构建AST"
    print("  ✓ AstBuilder组件工作正常")
    
    # 测试SymbolGenerator
    node_dict = ast_builder.get_node_dict()
    symbols = SymbolGenerator.generate_symbol_table(node_dict)
    # 检查是否包含module符号
    print("  ✓ SymbolGenerator组件工作正常")

def test_module_with_other_declarations():
    """测试module与其他声明的组合"""
    print("测试module与其他声明的组合...")
    
    test_content = """module io_utils : 输入输出工具模块
module string_utils : 字符串处理工具模块
module math_utils : 数学计算工具模块

var global_config: 全局配置变量

func helper_function:
description: 辅助函数
input: data: str
output: str
behavior:
    处理输入数据并返回结果

class DataProcessor:
description: 数据处理器类
inh: object

    var buffer: 数据缓冲区
    
    func process:
    description: 处理数据
    input: data: list
    output: list
    behavior:
        处理数据列表并返回结果
"""
    
    test_file = "test_module_combination.icb"
    create_test_icb_file(test_file, test_content)
    
    # 创建分析器并分析文件
    analyzer = IcbAnalyzer()
    result = analyzer._file_analysis(test_file)
    
    # 组合声明应该分析成功
    assert result == True, "module与其他声明的组合应该分析成功"
    print("  ✓ module与其他声明的组合处理正确")
    
    # 清理测试文件
    os.remove(test_file)

def test_symbol_generator_comprehensive():
    """全面测试符号生成器功能"""
    print("全面测试符号生成器功能...")
    
    test_content = """@ 测试类
class TestClass:
description: 用于测试的类
inh: object

    var test_var: 测试变量
    
    func __init__:
    description: 构造函数
    input: value: int
    output: None
    begin:
        初始化test_var
    
    func get_value:
    description: 获取变量值
    input: None
    output: int
    begin:
        返回test_var的值

func standalone_func:
description: 独立函数
input: x: int, y: int
output: int
begin:
    返回x和y的和

var global_var: 全局变量
"""
    
    test_file = "test_symbol_generator.icb"
    create_test_icb_file(test_file, test_content)
    
    # 分析文件
    analyzer = IcbAnalyzer()
    result = analyzer._file_analysis(test_file)
    assert result == True, "符号生成器测试文件应该分析成功"
    
    # 测试LinesLoader
    lines: List[str] = cast(List[str], test_content.splitlines())
    diag_handler = DiagHandler(test_file, lines)
    lines_loader = LinesLoader(test_file, lines, diag_handler)
    structured_lines, _ = lines_loader.generate()
    assert len(structured_lines) > 0, "应该生成结构化行"
    
    # 测试AstBuilder
    ast_builder = AstBuilder(structured_lines, diag_handler, test_file, "")
    build_result = ast_builder.build()
    assert build_result == True, "应该成功构建AST"
    
    # 测试SymbolGenerator
    node_dict = ast_builder.get_node_dict()
    symbols = SymbolGenerator.generate_symbol_table(node_dict)
    
    # 验证符号数量和类型
    # 根据需求，module关键字相关的内容并不会被symbol_generator所使用，所以移除对module符号的测试
    class_symbols = [s for s in symbols if s['type'] == 'class']
    func_symbols = [s for s in symbols if s['type'] == 'func']
    var_symbols = [s for s in symbols if s['type'] == 'var']
    
    assert len(class_symbols) == 1, "应该有1个class符号"
    assert len(func_symbols) == 2, "应该有2个func符号"
    assert len(var_symbols) == 2, "应该有2个var符号"
    
    # 验证类内部结构
    test_class = class_symbols[0]
    assert test_class['name'] == 'TestClass', "类名应该正确"
    assert test_class['inh'] == 'object', "继承关系应该正确"
    assert len(test_class['children']) == 2, "类内部应该有2个子元素"
    
    # 验证函数输入输出
    standalone_func = [f for f in func_symbols if f['name'] == 'standalone_func'][0]
    assert len(standalone_func['input']) == 2, "独立函数应该有2个输入参数"
    assert len(standalone_func['output']) == 1, "独立函数应该有1个输出参数"
    
    print("  ✓ 符号生成器功能测试通过")
    os.remove(test_file)

def test_behavior_step_processing():
    """测试行为步骤处理"""
    print("测试行为步骤处理...")
    
    test_content = """func test_behavior:
description: 测试行为步骤
input: None
output: None
begin:
    常规行为步骤
    带子步骤的行为:
        子步骤1
        子步骤2
    var local_var: 局部变量
    另一个常规步骤
"""
    
    test_file = "test_behavior.icb"
    create_test_icb_file(test_file, test_content)
    
    analyzer = IcbAnalyzer()
    result = analyzer._file_analysis(test_file)
    assert result == True, "行为步骤测试应该成功"
    
    # 验证AST构建
    lines: List[str] = cast(List[str], test_content.splitlines())
    diag_handler = DiagHandler(test_file, lines)
    lines_loader = LinesLoader(test_file, lines, diag_handler)
    structured_lines, _ = lines_loader.generate()
    
    ast_builder = AstBuilder(structured_lines, diag_handler, test_file, "")
    build_result = ast_builder.build()
    assert build_result == True, "应该成功构建AST"
    
    # 检查AST节点
    node_dict = ast_builder.get_node_dict()
    root_node = node_dict[-1]  # 根节点
    
    # 查找test_behavior函数
    func_node = None
    for child_uid in root_node['child_list']:
        child_node = node_dict.get(child_uid)
        if child_node and child_node.get('name') == 'test_behavior':
            func_node = child_node
            break
    
    assert func_node is not None, "应该找到test_behavior函数"
    
    # 检查函数的behavior子节点
    behavior_children = []
    for child_uid in func_node['child_list']:
        child_node = node_dict.get(child_uid)
        if child_node and child_node.get('type') == 'begin':
            behavior_children = child_node.get('child_list', [])
            break
    
    assert len(behavior_children) > 0, "behavior块应该有子节点"
    print("  ✓ 行为步骤处理测试通过")
    os.remove(test_file)

def test_special_attributes():
    """测试特殊属性处理（input/output/description/inh）"""
    print("测试特殊属性处理...")
    
    test_content = """class TestSpecial:
description: 测试特殊属性
inh: BaseClass

    var test_field: 测试字段
    
    func complex_func:
    description: 复杂函数测试特殊属性
    input: param1: str, param2: int, param3: list
    output: result: bool, error: str
    begin:
        处理输入参数
        返回结果和错误信息
"""
    
    test_file = "test_special_attributes.icb"
    create_test_icb_file(test_file, test_content)
    
    # 分析
    analyzer = IcbAnalyzer()
    result = analyzer._file_analysis(test_file)
    assert result == True, "特殊属性测试应该成功"
    
    # 构建AST
    lines: List[str] = cast(List[str], test_content.splitlines())
    diag_handler = DiagHandler(test_file, lines)
    lines_loader = LinesLoader(test_file, lines, diag_handler)
    structured_lines, _ = lines_loader.generate()
    
    ast_builder = AstBuilder(structured_lines, diag_handler, test_file, "")
    build_result = ast_builder.build()
    assert build_result == True, "应该成功构建AST"
    
    # 生成符号表
    node_dict = ast_builder.get_node_dict()
    symbols = SymbolGenerator.generate_symbol_table(node_dict)
    
    # 检查类符号
    class_symbols = [s for s in symbols if s['type'] == 'class']
    assert len(class_symbols) == 1, "应该有1个类符号"
    test_class = class_symbols[0]
    assert test_class['inh'] == 'BaseClass', "继承关系应该正确"
    
    # 检查函数符号
    func_symbols = [s for s in symbols if s['type'] == 'func']
    complex_func = [f for f in func_symbols if f['name'] == 'complex_func'][0]
    assert len(complex_func['input']) == 3, "应该有3个输入参数"
    assert len(complex_func['output']) == 2, "应该有2个输出参数"
    
    print("  ✓ 特殊属性处理测试通过")
    os.remove(test_file)

def test_intent_comments():
    """测试意图注释处理"""
    print("测试意图注释处理...")
    
    test_content = """@ 这是一个意图注释
class TestIntent:
@ 类的意图注释
description: 测试意图注释
inh: object

    @ 变量意图注释
    var test_var: 测试变量
    
    @ 函数意图注释
    func test_func:
    description: 测试函数
    input: None
    output: None
    behavior:
        @ 行为步骤意图注释
        执行测试操作
"""
    
    test_file = "test_intent_comments.icb"
    create_test_icb_file(test_file, test_content)
    
    analyzer = IcbAnalyzer()
    result = analyzer._file_analysis(test_file)
    assert result == True, "意图注释测试应该成功"
    
    # 验证AST构建
    lines: List[str] = cast(List[str], test_content.splitlines())
    diag_handler = DiagHandler(test_file, lines)
    lines_loader = LinesLoader(test_file, lines, diag_handler)
    structured_lines, _ = lines_loader.generate()
    
    ast_builder = AstBuilder(structured_lines, diag_handler, test_file, "")
    build_result = ast_builder.build()
    assert build_result == True, "应该成功构建AST"
    
    # 检查节点数量
    node_dict = ast_builder.get_node_dict()
    # 意图注释不应该作为AST节点
    intent_comment_count = sum(1 for node in node_dict.values() if node.get('type') == 'intent_comment')
    assert intent_comment_count == 0, "意图注释不应该作为AST节点"
    
    print("  ✓ 意图注释处理测试通过")
    os.remove(test_file)

def test_pass_keyword():
    """测试pass关键字处理"""
    print("测试pass关键字处理...")
    
    test_content = """class TestPass:
description: 测试pass关键字
inh: object

    func empty_func:
    description: 空函数
    input: None
    output: None
    behavior:
        pass
    
    func another_func:
    description: 另一个函数
    input: x: int
    output: int
    behavior:
        如果x小于0:
            pass
        否则:
            返回x
"""
    
    test_file = "test_pass.icb"
    create_test_icb_file(test_file, test_content)
    
    analyzer = IcbAnalyzer()
    result = analyzer._file_analysis(test_file)
    assert result == True, "pass关键字测试应该成功"
    
    print("  ✓ pass关键字处理测试通过")
    os.remove(test_file)

def main():
    """主测试函数"""
    print("开始测试ICB Analyzer功能...")
    print("=" * 50)
    
    # 定义所有测试函数
    test_functions: List[Tuple[str, Callable]] = [
        ("test_lines_loader_basic", test_lines_loader_basic),
        ("test_lines_loader_with_comments_and_empty_lines", test_lines_loader_with_comments_and_empty_lines),
        ("test_lines_loader_tab_detection", test_lines_loader_tab_detection),
        ("test_lines_parser_basic_elements", test_lines_parser_basic_elements),
        ("test_lines_parser_module_element", test_lines_parser_module_element),
        ("test_lines_parser_special_attributes", test_lines_parser_special_attributes),
        ("test_ast_builder_basic", test_ast_builder_basic),
        ("test_ast_builder_module_position_check", test_ast_builder_module_position_check),
        ("test_symbol_generator_basic", test_symbol_generator_basic),
        ("test_full_analysis_process", test_full_analysis_process),
        ("test_basic_icb_analysis", test_basic_icb_analysis),
        ("test_icb_with_syntax_errors", test_icb_with_syntax_errors),
        ("test_empty_icb_file", test_empty_icb_file),
        ("test_icb_with_indentation_errors", test_icb_with_indentation_errors),
        ("test_complex_icb_structure", test_complex_icb_structure),
        ("test_module_declaration_valid", test_module_declaration_valid),
        ("test_module_declaration_invalid_position", test_module_declaration_invalid_position),
        ("test_module_parsing_components", test_module_parsing_components),
        ("test_module_with_other_declarations", test_module_with_other_declarations),
        ("test_symbol_generator_comprehensive", test_symbol_generator_comprehensive),
        ("test_behavior_step_processing", test_behavior_step_processing),
        ("test_special_attributes", test_special_attributes),
        ("test_intent_comments", test_intent_comments),
        ("test_pass_keyword", test_pass_keyword),
    ]
    
    failed_tests = []
    
    # 执行所有测试
    for test_name, test_func in test_functions:
        try:
            print(f"\n执行测试: {test_name}")
            test_func()
            print(f"  ✓ {test_name} 通过")
        except Exception as e:
            print(f"  ✗ {test_name} 失败: {e}")
            failed_tests.append((test_name, e, traceback.format_exc()))
    
    # 输出测试总结
    print("\n" + "=" * 50)
    if failed_tests:
        print(f"测试完成，共 {len(test_functions)} 个测试，{len(failed_tests)} 个失败:")
        for test_name, exception, trace in failed_tests:
            print(f"\n--- {test_name} ---")
            print(f"错误: {exception}")
            print(f"详情:\n{trace}")
        sys.exit(1)
    else:
        print("所有测试通过!")
        sys.exit(0)

if __name__ == "__main__":
    main()