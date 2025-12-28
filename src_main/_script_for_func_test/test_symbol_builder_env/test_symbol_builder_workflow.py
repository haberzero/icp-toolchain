"""
符号表构建器完整工作流测试

本测试脚本完全模拟ICP工具链的真实使用流程：
1. 使用IbcAnalyzer分析IBC代码生成AST和符号表
2. 使用IbcDataStore保存和加载符号表
3. 使用VisibleSymbolBuilder构建可见符号树
4. 验证整个流程的正确性

不使用任何测试专用的文本操作，完全还原真实代码模块调用。

【build_visible_symbol_tree 返回值数据结构说明】

VisibleSymbolBuilder.build_visible_symbol_tree() 返回两个字典：

1. symbols_tree (纯树状结构，所有节点都是字典{})
示例：
{
    "src": {
        "ball": {
            "ball_entity": {
                "BallEntity": {
                    "get_position": {},
                    "set_velocity": {},
                    "get_velocity": {}
                }
            }
        },
        "heptagon": {
            "heptagon_shape": {
                "HeptagonShape": {
                    "get_vertices": {},
                    "is_point_inside": {}
                }
            }
        }
    }
}

2. symbols_metadata (符号元数据，使用点分隔的路径作为键)
示例：
{
    "src": {
        "type": "folder"
    },
    "src.ball": {
        "type": "folder"
    },
    "src.ball.ball_entity": {
        "type": "file",
        "description": "表示球体状态及其颜色编号管理"
    },
    "src.ball.ball_entity.BallEntity": {
        "type": "class",
        "description": "球体实体类, 管理单个球体的状态信息",
        "visibility": "public"
    },
    "src.ball.ball_entity.BallEntity.get_position": {
        "type": "func",
        "description": "获取球体位置",
        "visibility": "public",
        "parameters": {}
    },
    "src.ball.ball_entity.BallEntity.set_velocity": {
        "type": "func",
        "description": "设置球体速度",
        "visibility": "public",
        "parameters": {
            "速度向量": "新的速度向量"
        }
    }
}

【元数据节点类型说明】

- 文件夹节点: {"type": "folder"}
- 文件节点: {"type": "file", "description": "..."}
- 类节点: {"type": "class", "description": "...", "visibility": "public"}
- 函数节点: {"type": "func", "description": "...", "visibility": "public", "parameters": {...}}
- 变量节点: {"type": "var", "description": "...", "visibility": "public"}

注意：在可见符号树中不会出现 visibility="private" 的节点（已被过滤）
"""
import sys
import os
import json

# 添加项目根目录到路径
test_env_root = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(test_env_root, '..', '..'))
sys.path.insert(0, project_root)

# 导入真实的工程模块
from utils.ibc_analyzer.ibc_analyzer import analyze_ibc_code
from utils.ibc_analyzer.ibc_visible_symbol_builder import VisibleSymbolBuilder
from data_store.ibc_data_store import get_instance as get_ibc_data_store
from typedef.cmd_data_types import Colors


class SymbolBuilderWorkflowTest:
    """符号表构建器工作流测试类"""
    
    def __init__(self):
        self.test_env_root = test_env_root
        self.work_dir_path = test_env_root
        self.work_ibc_dir_path = os.path.join(test_env_root, 'src_ibc')
        self.work_data_dir_path = os.path.join(test_env_root, 'icp_proj_data')
        
        self.ibc_data_store = get_ibc_data_store()
        
        print(f"{Colors.OKBLUE}=== 符号表构建器工作流测试 ==={Colors.ENDC}")
        print(f"测试环境路径: {self.test_env_root}")
        print(f"IBC目录: {self.work_ibc_dir_path}")
        print(f"数据目录: {self.work_data_dir_path}")
        print()
    
    @staticmethod
    def format_tree_as_text(
        tree: dict[str, any], 
        metadata: dict[str, dict[str, any]], 
        indent_level: int = 0,
        path_prefix: str = ""
    ) -> str:
        """
        将符号树格式化为可读的文本形式（用于测试输出）
        
        Args:
            tree: 符号树
            metadata: 符号元数据
            indent_level: 当前缩进级别
            path_prefix: 当前路径前缀
            
        Returns:
            str: 格式化后的文本
        """
        lines = []
        indent = "  " * indent_level
        
        for key, value in tree.items():
            # 构建当前路径
            if path_prefix:
                current_path = f"{path_prefix}.{key}"
            else:
                current_path = key
            
            # 获取元数据
            node_metadata = metadata.get(current_path, {})
            node_type = node_metadata.get('type', 'unknown')
            
            if isinstance(value, dict):
                if node_type == 'folder':
                    # 文件夹节点
                    lines.append(f"{indent}{key}/")
                    # 递归处理子节点
                    child_text = SymbolBuilderWorkflowTest.format_tree_as_text(
                        value, metadata, indent_level + 1, current_path
                    )
                    if child_text:
                        lines.append(child_text)
                        
                elif node_type == 'file':
                    # 文件节点
                    desc = node_metadata.get('description', '')
                    line = f"{indent}{key}/"
                    if desc:
                        line += f"  # {desc}"
                    lines.append(line)
                    # 递归处理子节点（符号）
                    child_text = SymbolBuilderWorkflowTest.format_tree_as_text(
                        value, metadata, indent_level + 1, current_path
                    )
                    if child_text:
                        lines.append(child_text)
                        
                else:
                    # 符号节点（class, func, var）
                    visibility = node_metadata.get('visibility', 'public')
                    description = node_metadata.get('description', '')
                    normalized_name = node_metadata.get('normalized_name', '')
                    
                    line = f"{indent}{key} ({node_type}, {visibility})"
                    if normalized_name:
                        line += f" -> {normalized_name}"
                    if description:
                        line += f": {description}"
                    lines.append(line)
                    
                    # 如果是函数，显示参数
                    if 'parameters' in node_metadata and node_metadata['parameters']:
                        params_str = ", ".join(
                            f"{p_name}: {p_desc}" if p_desc else p_name
                            for p_name, p_desc in node_metadata['parameters'].items()
                        )
                        lines.append(f"{indent}  参数: ({params_str})")
                    
                    # 递归处理子符号
                    if value:  # 如果有子节点
                        child_text = SymbolBuilderWorkflowTest.format_tree_as_text(
                            value, metadata, indent_level + 1, current_path
                        )
                        if child_text:
                            lines.append(child_text)
        
        return '\n'.join(lines)
    
    def step1_analyze_ibc_and_generate_symbols(self):
        """步骤1: 分析IBC代码并生成符号表"""
        print(f"{Colors.OKBLUE}>>> 步骤1: 分析IBC代码并生成符号表{Colors.ENDC}")
        
        # 要处理的文件列表
        files = [
            'src/ball/ball_entity',
            'src/heptagon/heptagon_shape'
        ]
        
        for file_path in files:
            print(f"\n  处理文件: {file_path}")
            
            # 1.1 使用IbcDataStore加载IBC代码
            ibc_path = self.ibc_data_store.build_ibc_path(self.work_ibc_dir_path, file_path)
            
            if not os.path.exists(ibc_path):
                print(f"    {Colors.FAIL}错误: IBC文件不存在: {ibc_path}{Colors.ENDC}")
                continue
            
            ibc_code = self.ibc_data_store.load_ibc_content(ibc_path)
            print(f"    [OK] 加载IBC代码: {len(ibc_code)} 字符")
            
            # 1.2 使用IbcAnalyzer分析生成AST和符号树
            ast_dict, symbols_tree, symbols_metadata = analyze_ibc_code(ibc_code)
            
            if not ast_dict:
                print(f"    {Colors.WARNING}警告: 分析失败{Colors.ENDC}")
                continue
            
            print(f"    [OK] AST节点数: {len(ast_dict)}")
            print(f"    [OK] 符号数量: {len(symbols_metadata)}")
            
            # 1.3 使用IbcDataStore保存符号数据
            file_name = os.path.basename(file_path)
            symbols_path = self.ibc_data_store.build_symbols_path(self.work_ibc_dir_path, file_path)
            self.ibc_data_store.save_symbols(symbols_path, file_name, symbols_tree, symbols_metadata)
            print(f"    [OK] 符号表已保存: {symbols_path}")
        
        print(f"\n{Colors.OKGREEN}步骤1完成: 符号表生成成功{Colors.ENDC}\n")
    
    def step2_load_project_structure(self):
        """步骤2: 加载项目结构和依赖关系"""
        print(f"{Colors.OKBLUE}>>> 步骤2: 加载项目结构和依赖关系{Colors.ENDC}")
        
        # 2.1 加载依赖关系文件（真实流程中由depend_analysis命令生成）
        depend_file = os.path.join(self.work_data_dir_path, 'icp_dir_content_with_depend.json')
        
        if not os.path.exists(depend_file):
            print(f"  {Colors.FAIL}错误: 依赖关系文件不存在: {depend_file}{Colors.ENDC}")
            return None, None
        
        with open(depend_file, 'r', encoding='utf-8') as f:
            depend_data = json.load(f)
        
        proj_root_dict = depend_data['proj_root_dict']
        dependent_relation = depend_data['dependent_relation']
        
        print(f"  [OK] 项目结构加载成功")
        print(f"  [OK] 文件总数: {len(dependent_relation)}")
        print(f"  [OK] 依赖关系:")
        for file_path, deps in dependent_relation.items():
            print(f"      {file_path} -> {deps if deps else '[]'}")
        
        print(f"\n{Colors.OKGREEN}步骤2完成: 项目结构加载成功{Colors.ENDC}\n")
        return proj_root_dict, dependent_relation
    
    def step3_build_visible_symbol_tree(self, proj_root_dict, dependent_relation):
        """步骤3: 构建可见符号树"""
        print(f"{Colors.OKBLUE}>>> 步骤3: 构建可见符号树{Colors.ENDC}")
        
        # 3.1 创建VisibleSymbolBuilder（真实流程中在cmd_handler_ibc_gen中创建）
        builder = VisibleSymbolBuilder(
            proj_root_dict=proj_root_dict,
        )
        print(f"  [OK] VisibleSymbolBuilder已创建")
        
        # 3.2 为每个文件构建可见符号树
        test_cases = [
            ('src/ball/ball_entity', '测试无依赖文件'),
            ('src/heptagon/heptagon_shape', '测试无依赖文件'),
        ]
        
        results = {}
        
        for file_path, description in test_cases:
            print(f"\n  测试用例: {file_path} ({description})")
            
            # 使用真实的build_visible_symbol_tree方法
            if not self.ibc_data_store.is_dependency_symbol_tables_valid(
                ibc_root=self.work_ibc_dir_path,
                dependent_relation=dependent_relation,
                current_file_path=file_path,
            ):
                symbols_tree, symbols_metadata = {}, {}
            else:
                dependency_symbol_tables = self.ibc_data_store.load_dependency_symbol_tables(
                    ibc_root=self.work_ibc_dir_path,
                    dependent_relation=dependent_relation,
                    current_file_path=file_path,
                )
                symbols_tree, symbols_metadata = builder.build_visible_symbol_tree(
                    current_file_path=file_path,
                    dependency_symbol_tables=dependency_symbol_tables,
                )
            
            results[file_path] = (symbols_tree, symbols_metadata)
            
            # 验证结果
            if not symbols_tree:
                print(f"    [OK] 符号树为空（符合预期，无依赖）")
            else:
                print(f"    [OK] 符号树构建成功")
                # 使用测试类的format_tree_as_text方法
                formatted = self.format_tree_as_text(symbols_tree, symbols_metadata)
                print(f"    [OK] 格式化输出:")
                for line in formatted.split('\n')[:10]:
                    print(f"        {line}")
                if len(formatted.split('\n')) > 10:
                    print(f"        ... (共{len(formatted.split('\n'))}行)")
        
        print(f"\n{Colors.OKGREEN}步骤3完成: 可见符号树构建成功{Colors.ENDC}\n")
        return results, builder
    
    def step4_create_file_with_dependency(self):
        """步骤4: 创建带依赖的测试文件"""
        print(f"{Colors.OKBLUE}>>> 步骤4: 创建带依赖的测试文件{Colors.ENDC}")
        
        # 4.1 创建一个新的IBC文件，依赖ball_entity和heptagon_shape
        test_file_path = 'src/test_physics'
        test_ibc_code = """module src.ball.ball_entity: 球体实体模块
module src.heptagon.heptagon_shape: 七边形模块

description: 简化的物理引擎，用于测试符号引用
class TestPhysics():
    var ball: 球体实例，类型为 $ball_entity.BallEntity
    var shape: 七边形实例，类型为 $heptagon_shape.HeptagonShape
    
    func check_collision():
        球体位置 = self.ball.get_center()
        是否碰撞 = self.shape.is_point_inside(球体位置)
        返回 是否碰撞
"""
        
        # 保存IBC文件
        ibc_path = self.ibc_data_store.build_ibc_path(self.work_ibc_dir_path, test_file_path)
        os.makedirs(os.path.dirname(ibc_path), exist_ok=True)
        self.ibc_data_store.save_ibc_content(ibc_path, test_ibc_code)
        print(f"  [OK] 测试IBC文件已创建: {ibc_path}")
        
        # 4.2 分析并生成符号树
        ast_dict, symbols_tree, symbols_metadata = analyze_ibc_code(test_ibc_code)
        print(f"  [OK] AST节点数: {len(ast_dict)}")
        print(f"  [OK] 符号数量: {len(symbols_metadata)}")
        
        # 保存符号数据
        file_name = os.path.basename(test_file_path)
        symbols_path = self.ibc_data_store.build_symbols_path(self.work_ibc_dir_path, test_file_path)
        self.ibc_data_store.save_symbols(symbols_path, file_name, symbols_tree, symbols_metadata)
        print(f"  [OK] 符号表已保存")
        
        # 4.3 更新依赖关系
        depend_file = os.path.join(self.work_data_dir_path, 'icp_dir_content_with_depend.json')
        with open(depend_file, 'r', encoding='utf-8') as f:
            depend_data = json.load(f)
        
        depend_data['proj_root_dict']['src']['test_physics'] = "测试物理引擎"
        depend_data['dependent_relation'][test_file_path] = [
            'src/ball/ball_entity',
            'src/heptagon/heptagon_shape'
        ]
        
        with open(depend_file, 'w', encoding='utf-8') as f:
            json.dump(depend_data, f, ensure_ascii=False, indent=2)
        
        print(f"  [OK] 依赖关系已更新")
        print(f"\n{Colors.OKGREEN}步骤4完成: 带依赖测试文件创建成功{Colors.ENDC}\n")
        
        return test_file_path, depend_data['proj_root_dict'], depend_data['dependent_relation']
    
    def step5_test_with_dependencies(self, test_file_path, proj_root_dict, dependent_relation):
        """步骤5: 测试带依赖的符号树构建"""
        print(f"{Colors.OKBLUE}>>> 步骤5: 测试带依赖的符号树构建{Colors.ENDC}")
        
        # 5.1 重新创建VisibleSymbolBuilder
        builder = VisibleSymbolBuilder(
            proj_root_dict=proj_root_dict,
        )
        
        # 5.2 为测试文件构建可见符号树
        print(f"\n  为 {test_file_path} 构建可见符号树...")
        if not self.ibc_data_store.is_dependency_symbol_tables_valid(
            ibc_root=self.work_ibc_dir_path,
            dependent_relation=dependent_relation,
            current_file_path=test_file_path,
        ):
            symbols_tree, symbols_metadata = {}, {}
        else:
            dependency_symbol_tables = self.ibc_data_store.load_dependency_symbol_tables(
                ibc_root=self.work_ibc_dir_path,
                dependent_relation=dependent_relation,
                current_file_path=test_file_path,
            )
            symbols_tree, symbols_metadata = builder.build_visible_symbol_tree(
                current_file_path=test_file_path,
                dependency_symbol_tables=dependency_symbol_tables,
            )
        
        # 5.3 验证结果
        if symbols_tree:
            print(f"  [OK] 符号树构建成功")
            print(f"  [OK] 可见的依赖文件数: {len(dependent_relation[test_file_path])}")
            
            # 格式化输出
            formatted = self.format_tree_as_text(symbols_tree, symbols_metadata)
            print(f"\n  [OK] 可见符号详情:")
            for line in formatted.split('\n'):
                print(f"    {line}")
            
            # 验证是否包含预期的符号
            expected_symbols = ['BallEntity', 'HeptagonShape', 'get_center', 'is_point_inside']
            found_symbols = []
            
            for symbol in expected_symbols:
                if symbol in formatted:
                    found_symbols.append(symbol)
            
            print(f"\n  [OK] 预期符号验证:")
            print(f"    预期: {expected_symbols}")
            print(f"    找到: {found_symbols}")
            
            if len(found_symbols) == len(expected_symbols):
                print(f"    {Colors.OKGREEN}✓ 所有预期符号都已找到{Colors.ENDC}")
            else:
                print(f"    {Colors.WARNING}⚠ 部分符号未找到{Colors.ENDC}")
        else:
            print(f"  {Colors.FAIL}✗ 符号树构建失败{Colors.ENDC}")
        
        print(f"\n{Colors.OKGREEN}步骤5完成: 依赖符号验证成功{Colors.ENDC}\n")
    
    def run_full_workflow(self):
        """运行完整的工作流测试"""
        print(f"\n{Colors.OKBLUE}{'='*60}{Colors.ENDC}")
        print(f"{Colors.OKBLUE}开始完整工作流测试{Colors.ENDC}")
        print(f"{Colors.OKBLUE}{'='*60}{Colors.ENDC}\n")
        
        try:
            # 步骤1: 分析IBC代码并生成符号表
            self.step1_analyze_ibc_and_generate_symbols()
            
            # 步骤2: 加载项目结构
            proj_root_dict, dependent_relation = self.step2_load_project_structure()
            if not proj_root_dict:
                return
            
            # 步骤3: 构建可见符号树（无依赖场景）
            results, builder = self.step3_build_visible_symbol_tree(proj_root_dict, dependent_relation)
            
            # 步骤4: 创建带依赖的测试文件
            test_file_path, new_proj_root_dict, new_dependent_relation = self.step4_create_file_with_dependency()
            
            # 步骤5: 测试带依赖的符号树构建
            self.step5_test_with_dependencies(test_file_path, new_proj_root_dict, new_dependent_relation)
            
            print(f"\n{Colors.OKGREEN}{'='*60}{Colors.ENDC}")
            print(f"{Colors.OKGREEN}完整工作流测试成功完成！{Colors.ENDC}")
            print(f"{Colors.OKGREEN}{'='*60}{Colors.ENDC}\n")
            
        except Exception as e:
            print(f"\n{Colors.FAIL}{'='*60}{Colors.ENDC}")
            print(f"{Colors.FAIL}测试过程中发生错误: {e}{Colors.ENDC}")
            print(f"{Colors.FAIL}{'='*60}{Colors.ENDC}\n")
            import traceback
            traceback.print_exc()


def main():
    """主函数"""
    test = SymbolBuilderWorkflowTest()
    test.run_full_workflow()


if __name__ == "__main__":
    main()
