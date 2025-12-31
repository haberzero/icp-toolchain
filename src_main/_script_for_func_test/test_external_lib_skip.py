"""测试第三方库符号引用跳过机制

本测试脚本专门用于测试ref resolver对第三方库符号的跳过机制，
确保无论何种形式的第三方库引用都不会导致解析错误。

测试场景：
1. module tkinter + $tkinter.Canvas - 基本外部库引用
2. module tkinter.Canvas - 外部库子模块引用  
3. module tkinter + $tkinter.ttk.Button - 多层外部库引用
4. module numpy.random + $random.randint - 外部库子模块别名引用
5. 混合场景：内部模块 + 多个外部库
6. 边界情况：外部库符号作为类型标注
7. 边界情况：外部库符号在行为描述中使用
"""

import sys
import os

# 添加项目根目录到系统路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from utils.ibc_analyzer.ibc_analyzer import analyze_ibc_content
from utils.ibc_analyzer.ibc_symbol_ref_resolver import SymbolRefResolver
from utils.ibc_analyzer.ibc_visible_symbol_builder import VisibleSymbolBuilder
from utils.issue_recorder import IbcIssueRecorder
from typedef.cmd_data_types import Colors


def run_test(test_name: str, ibc_content: str, proj_root_dict: dict, expected_issues: int = 0) -> bool:
    """运行单个测试用例
    
    Args:
        test_name: 测试名称
        ibc_content: IBC代码内容
        proj_root_dict: 项目根目录字典（包含ExternalLibraryDependencies）
        expected_issues: 预期的问题数量
    
    Returns:
        bool: 测试是否通过
    """
    print(f"\n{Colors.OKBLUE}{'='*80}{Colors.ENDC}")
    print(f"{Colors.OKBLUE}测试: {test_name}{Colors.ENDC}")
    print(f"{Colors.OKBLUE}{'='*80}{Colors.ENDC}\n")
    
    # 打印IBC内容（用于调试）
    print("IBC代码内容:")
    print("-" * 80)
    print(ibc_content)
    print("-" * 80)
    print()
    
    # 解析IBC代码
    issue_recorder = IbcIssueRecorder()
    ast_dict, symbols_tree, symbols_metadata = analyze_ibc_content(ibc_content, issue_recorder)
    
    if not ast_dict:
        print(f"{Colors.FAIL}✗ IBC代码解析失败{Colors.ENDC}")
        if issue_recorder.has_issues():
            print("解析错误:")
            issue_recorder.print_issues()
        return False
    
    print(f"{Colors.OKGREEN}✓ IBC代码解析成功{Colors.ENDC}\n")
    
    # 构建可见符号树
    builder = VisibleSymbolBuilder(proj_root_dict)
    visible_symbols_tree, visible_symbols_metadata = builder.build_visible_symbol_tree(
        current_file_path="src/test",
        dependency_symbol_tables={},
        include_local_symbols=True,
        local_symbols_tree=symbols_tree,
        local_symbols_metadata=symbols_metadata
    )
    
    # 创建符号引用解析器
    issue_recorder.clear()
    resolver = SymbolRefResolver(
        ast_dict=ast_dict,
        symbols_tree=visible_symbols_tree,
        symbols_metadata=visible_symbols_metadata,
        ibc_issue_recorder=issue_recorder,
        proj_root_dict=proj_root_dict,
        dependent_relation={"src/test": []},
        current_file_path="src/test"
    )
    
    # 解析所有引用
    resolver.resolve_all_references()
    
    # 检查结果
    issues = issue_recorder.get_issues()
    actual_issues = len(issues)
    
    print(f"预期问题数: {expected_issues}")
    print(f"实际问题数: {actual_issues}")
    
    if issues:
        print(f"\n{Colors.WARNING}问题列表:{Colors.ENDC}")
        for i, issue in enumerate(issues, 1):
            print(f"  {i}. 第{issue.line_num}行: {issue.message}")
            if issue.line_content:
                print(f"     代码: {issue.line_content}")
    
    # 验证问题数量
    if actual_issues != expected_issues:
        print(f"\n{Colors.FAIL}✗ 测试失败: 问题数量不匹配{Colors.ENDC}")
        return False
    
    print(f"\n{Colors.OKGREEN}✓ 测试通过{Colors.ENDC}")
    return True


def test_1_basic_external_library():
    """测试1: module tkinter + $tkinter.Canvas - 基本外部库引用"""
    ibc_content = """module tkinter: GUI库

description: 测试基本外部库引用
class TestWindow():
    var canvas: 画布对象，类型为 $tkinter.Canvas
    var button: 按钮对象，类型为 $tkinter.Button
    
    func create_widgets():
        self.canvas = $tkinter.Canvas()
        self.button = $tkinter.Button()
"""
    
    proj_root_dict = {
        "ExternalLibraryDependencies": {
            "tkinter": "Python标准GUI库"
        }
    }
    
    return run_test(
        test_name="1. 基本外部库引用 (module tkinter + $tkinter.Canvas)",
        ibc_content=ibc_content,
        proj_root_dict=proj_root_dict,
        expected_issues=0
    )


def test_2_external_submodule_import():
    """测试2: module tkinter.Canvas - 外部库子模块引用"""
    ibc_content = """module tkinter.Canvas: GUI画布类

description: 测试外部库子模块引用
class TestWindow():
    var canvas: 画布对象，类型为 $Canvas
    
    func create_canvas():
        self.canvas = $Canvas()
        调用 $Canvas.create_line(0, 0, 100, 100)
"""
    
    proj_root_dict = {
        "ExternalLibraryDependencies": {
            "tkinter": "Python标准GUI库"
        }
    }
    
    return run_test(
        test_name="2. 外部库子模块引用 (module tkinter.Canvas)",
        ibc_content=ibc_content,
        proj_root_dict=proj_root_dict,
        expected_issues=0
    )


def test_3_multi_level_external_reference():
    """测试3: module tkinter + $tkinter.ttk.Button - 多层外部库引用"""
    ibc_content = """module tkinter: GUI库

description: 测试多层外部库引用
class TestWindow():
    var button: TTK按钮，类型为 $tkinter.ttk.Button
    var combobox: TTK组合框，类型为 $tkinter.ttk.Combobox
    
    func create_widgets():
        self.button = $tkinter.ttk.Button()
        self.combobox = $tkinter.ttk.Combobox()
        调用 $tkinter.messagebox.showinfo("标题", "内容")
"""
    
    proj_root_dict = {
        "ExternalLibraryDependencies": {
            "tkinter": "Python标准GUI库"
        }
    }
    
    return run_test(
        test_name="3. 多层外部库引用 (module tkinter + $tkinter.ttk.Button)",
        ibc_content=ibc_content,
        proj_root_dict=proj_root_dict,
        expected_issues=0
    )


def test_4_external_submodule_alias():
    """测试4: module numpy.random + $random.randint - 外部库子模块别名引用"""
    ibc_content = """module numpy.random: 随机数生成模块

description: 测试外部库子模块别名引用
class RandomGenerator():
    func generate_numbers():
        数字1 = $random.randint(0, 100)
        数字2 = $random.uniform(0.0, 1.0)
        数组 = $random.choice([1, 2, 3, 4, 5])
        返回 数字1, 数字2, 数组
"""
    
    proj_root_dict = {
        "ExternalLibraryDependencies": {
            "numpy": "数值计算库"
        }
    }
    
    return run_test(
        test_name="4. 外部库子模块别名引用 (module numpy.random + $random.randint)",
        ibc_content=ibc_content,
        proj_root_dict=proj_root_dict,
        expected_issues=0
    )


def test_5_mixed_internal_and_external():
    """测试5: 混合场景 - 内部模块 + 多个外部库"""
    ibc_content = """module tkinter: GUI库
module numpy: 数值计算库
module pandas: 数据分析库

description: 测试混合内部和外部引用
class DataVisualizer():
    var window: 窗口对象，类型为 $tkinter.Tk
    
    func visualize_data(data: 数据):
        数组 = $numpy.array(data)
        数据框 = $pandas.DataFrame(数组)
        
        self.window = $tkinter.Tk()
        画布 = $tkinter.Canvas(self.window)
        
        绘制 数据框 到 画布 上
"""
    
    proj_root_dict = {
        "ExternalLibraryDependencies": {
            "tkinter": "Python标准GUI库",
            "numpy": "数值计算库",
            "pandas": "数据分析库"
        }
    }
    
    return run_test(
        test_name="5. 混合内部和外部引用",
        ibc_content=ibc_content,
        proj_root_dict=proj_root_dict,
        expected_issues=0  # 只测试外部库，不涉及内部模块
    )


def test_6_external_in_type_annotation():
    """测试6: 外部库符号作为类型标注"""
    ibc_content = """module tkinter: GUI库
module typing: 类型标注库

description: 测试外部库符号作为类型标注
class TestClass():
    var widgets: 组件列表，类型为 $typing.List[$tkinter.Widget]
    var callback: 回调函数，类型为 $typing.Callable[[int], str]
    
    func process_widget(
        widget: 组件对象，类型为 $tkinter.Widget,
        handler: 处理函数，类型为 $typing.Callable
    ):
        执行处理逻辑
"""
    
    proj_root_dict = {
        "ExternalLibraryDependencies": {
            "tkinter": "Python标准GUI库",
            "typing": "类型标注模块"
        }
    }
    
    return run_test(
        test_name="6. 外部库符号作为类型标注",
        ibc_content=ibc_content,
        proj_root_dict=proj_root_dict,
        expected_issues=0
    )


def test_7_external_in_behavior():
    """测试7: 外部库符号在行为描述中使用"""
    ibc_content = """module requests: HTTP请求库
module json: JSON处理库

description: 测试外部库符号在行为描述中使用
class ApiClient():
    func fetch_data(url: 请求URL):
        响应 = $requests.get(url)
        
        如果 响应.status_code == 200:
            数据 = $json.loads(响应.text)
            返回 数据
        否则:
            抛出 $requests.HTTPError("请求失败")
    
    func post_data(url: 请求URL, data: 数据字典):
        json字符串 = $json.dumps(data)
        响应 = $requests.post(url, json字符串)
        返回 响应
"""
    
    proj_root_dict = {
        "ExternalLibraryDependencies": {
            "requests": "HTTP请求库",
            "json": "JSON处理标准库"
        }
    }
    
    return run_test(
        test_name="7. 外部库符号在行为描述中使用",
        ibc_content=ibc_content,
        proj_root_dict=proj_root_dict,
        expected_issues=0
    )


def test_8_external_library_edge_cases():
    """测试8: 边界情况综合测试"""
    ibc_content = """module os.path: 路径处理模块
module tkinter.filedialog: 文件对话框
module PIL.Image: 图像处理

description: 综合边界情况测试
class FileManager():
    func open_file():
        文件路径 = $filedialog.askopenfilename()
        
        如果 $path.exists(文件路径):
            目录名 = $path.dirname(文件路径)
            文件名 = $path.basename(文件路径)
            
            图像 = $Image.open(文件路径)
            宽度, 高度 = 图像.size
            
            返回 图像
        否则:
            返回 None
"""
    
    proj_root_dict = {
        "ExternalLibraryDependencies": {
            "os": "操作系统接口",
            "tkinter": "Python标准GUI库",
            "PIL": "Python图像库"
        }
    }
    
    return run_test(
        test_name="8. 综合边界情况测试",
        ibc_content=ibc_content,
        proj_root_dict=proj_root_dict,
        expected_issues=0
    )


def test_9_no_external_lib_should_error():
    """测试9: 没有声明外部库时应该报错"""
    ibc_content = """description: 测试未声明外部库时的错误检测
class TestClass():
    var data: 数据，类型为 $numpy.ndarray
    
    func process():
        结果 = $numpy.array([1, 2, 3])
"""
    
    proj_root_dict = {
        "ExternalLibraryDependencies": {}
    }
    
    return run_test(
        test_name="9. 未声明外部库时应该报错",
        ibc_content=ibc_content,
        proj_root_dict=proj_root_dict,
        expected_issues=2  # 期望有2个错误：$numpy.ndarray 和 $numpy.array
    )


def test_10_pytorch_complex_case():
    """测试10: PyTorch复杂场景（实际使用案例）"""
    ibc_content = """module torch: PyTorch深度学习框架
module torch.nn: 神经网络模块
module torch.optim: 优化器模块

description: PyTorch神经网络训练器
class NeuralNetworkTrainer():
    var model: 模型对象，类型为 $nn.Module
    var optimizer: 优化器，类型为 $optim.Adam
    var loss_function: 损失函数，类型为 $nn.CrossEntropyLoss
    
    func __init__(
        模型: 神经网络模型,
        学习率: float
    ):
        self.model = 模型
        self.optimizer = $optim.Adam(self.model.parameters(), 学习率)
        self.loss_function = $nn.CrossEntropyLoss()
    
    func train_step(inputs: 输入张量, targets: 目标标签):
        self.optimizer.zero_grad()
        
        输出 = self.model(inputs)
        损失 = self.loss_function(输出, targets)
        
        损失.backward()
        self.optimizer.step()
        
        返回 损失.item()
    
    func save_model(路径: str):
        $torch.save(self.model.state_dict(), 路径)
"""
    
    proj_root_dict = {
        "ExternalLibraryDependencies": {
            "torch": "PyTorch深度学习框架"
        }
    }
    
    return run_test(
        test_name="10. PyTorch复杂场景",
        ibc_content=ibc_content,
        proj_root_dict=proj_root_dict,
        expected_issues=0
    )


def run_all_tests():
    """运行所有测试"""
    print(f"\n{Colors.HEADER}{'='*80}{Colors.ENDC}")
    print(f"{Colors.HEADER}开始执行第三方库符号引用跳过机制测试套件{Colors.ENDC}")
    print(f"{Colors.HEADER}{'='*80}{Colors.ENDC}\n")
    
    tests = [
        test_1_basic_external_library,
        test_2_external_submodule_import,
        test_3_multi_level_external_reference,
        test_4_external_submodule_alias,
        test_5_mixed_internal_and_external,
        test_6_external_in_type_annotation,
        test_7_external_in_behavior,
        test_8_external_library_edge_cases,
        test_9_no_external_lib_should_error,
        test_10_pytorch_complex_case
    ]
    
    results = []
    for test_func in tests:
        try:
            result = test_func()
            results.append((test_func.__doc__.split('\n')[0], result))
        except Exception as e:
            print(f"\n{Colors.FAIL}✗ 测试执行异常: {test_func.__name__}{Colors.ENDC}")
            print(f"异常信息: {e}")
            import traceback
            traceback.print_exc()
            results.append((test_func.__doc__.split('\n')[0], False))
    
    # 打印测试摘要
    print(f"\n{Colors.HEADER}{'='*80}{Colors.ENDC}")
    print(f"{Colors.HEADER}测试摘要{Colors.ENDC}")
    print(f"{Colors.HEADER}{'='*80}{Colors.ENDC}\n")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = f"{Colors.OKGREEN}✓ 通过{Colors.ENDC}" if result else f"{Colors.FAIL}✗ 失败{Colors.ENDC}"
        print(f"{status} - {test_name}")
    
    print(f"\n{Colors.HEADER}总计: {passed}/{total} 个测试通过{Colors.ENDC}")
    
    if passed == total:
        print(f"{Colors.OKGREEN}{'='*80}{Colors.ENDC}")
        print(f"{Colors.OKGREEN}所有测试通过！第三方库符号跳过机制工作正常。{Colors.ENDC}")
        print(f"{Colors.OKGREEN}{'='*80}{Colors.ENDC}\n")
        return True
    else:
        print(f"{Colors.FAIL}{'='*80}{Colors.ENDC}")
        print(f"{Colors.FAIL}部分测试失败，请检查日志。{Colors.ENDC}")
        print(f"{Colors.FAIL}{'='*80}{Colors.ENDC}\n")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
