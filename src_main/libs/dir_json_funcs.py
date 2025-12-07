import os
import json
from typing import List, Dict, Optional, Union, Set, Any


class DirJsonFuncs:
    @staticmethod
    def detect_circular_dependencies(dependencies: Dict[str, List[str]]) -> List[str]:
        """
        检测是否存在循环依赖
        使用深度优先搜索算法检测有向图中的环
        返回循环依赖路径列表
        """
        # 构建图的邻接表表示
        graph = {key: set(value) for key, value in dependencies.items() if isinstance(value, list)}
        
        # 状态: 0-未访问, 1-正在访问(在当前DFS路径中), 2-已访问完成
        state = {node: 0 for node in graph.keys()}
        
        # 存储所有检测到的循环依赖路径
        circular_dependencies = []

        def dfs(node, visited_path):
            """深度优先搜索检测环"""
            # 如果节点正在访问中，说明存在环
            if state[node] == 1:
                # 检查环是否是自环或者真正的循环（node是否在当前访问路径中）
                if node in visited_path:
                    # 构建循环路径
                    # 找到node在路径中的位置
                    cycle_start_index = visited_path.index(node)
                    cycle_path = visited_path[cycle_start_index:] + [node]
                    cycle_str = " -> ".join(cycle_path)
                    circular_dependencies.append(cycle_str)
                return
            
            if state[node] == 2:  # 如果节点已访问完成，无需再次访问
                return
            
            # 标记为正在访问
            state[node] = 1
            visited_path.append(node)
            
            # 访问所有邻居节点
            for neighbor in graph.get(node, []):
                # 只检查在dependent_relation中的节点
                if neighbor in graph:
                    dfs(neighbor, visited_path)
            
            # 标记为访问完成
            state[node] = 2
            visited_path.pop()
        
        # 对每个节点进行DFS
        for node in graph.keys():
            if state[node] == 0:
                visited_path = []
                dfs(node, visited_path)
        
        return circular_dependencies if circular_dependencies else []
    
    @staticmethod
    def ensure_all_files_in_dependent_relation(json_content: Dict) -> bool:
        """
        确保proj_root_dict下的所有文件都在dependent_relation中有对应的条目
        如果没有，则添加一个空的依赖列表
        返回是否进行了修改
        """
        proj_root_dict = json_content.get("proj_root_dict", {})
        dependent_relation = json_content.get("dependent_relation", {})
        
        # 收集proj_root_dict下的所有文件路径
        proj_root_dict_paths = set()
        def _collect_paths(node, current_path=""):
            if isinstance(node, dict):
                for key, value in node.items():
                    new_path = f"{current_path}/{key}" if current_path else key
                    if isinstance(value, dict):
                        _collect_paths(value, new_path)
                    elif isinstance(value, str):
                        # 只有当值是字符串时，才认为key是文件路径
                        proj_root_dict_paths.add(new_path)
        
        _collect_paths(proj_root_dict)
        dependent_files = set(dependent_relation.keys())
        missing_files = proj_root_dict_paths - dependent_files
        
        # 为缺失的文件添加空的依赖列表
        modified = False
        for file_path in missing_files:
            dependent_relation[file_path] = []
            modified = True
        
        # 更新json_content中的dependent_relation
        json_content["dependent_relation"] = dependent_relation
        return modified

    @staticmethod
    def build_file_creation_order(dependencies: Dict[str, List[str]]) -> List[str]:
        """
        根据依赖关系构建文件创建顺序
        """
        # 计算入度和出度
        in_degree = {file: 0 for file in dependencies}
        out_degree = {file: len(deps) for file, deps in dependencies.items()}
        
        for file, deps in dependencies.items():
            for dep in deps:
                if dep in in_degree:
                    in_degree[dep] += 1
        
        # 分类文件
        no_in_no_out = []
        has_in_no_out = []
        no_in_has_out = []
        has_in_has_out = []
        
        for file in dependencies:
            if in_degree[file] == 0 and out_degree[file] == 0:
                no_in_no_out.append(file)
            elif in_degree[file] > 0 and out_degree[file] == 0:
                has_in_no_out.append(file)
            elif in_degree[file] == 0 and out_degree[file] > 0:
                no_in_has_out.append(file)
            else:
                has_in_has_out.append(file)
        
        # 拓扑排序 has_in_has_out
        ordered_has_in_has_out = DirJsonFuncs._topological_sort(dependencies, has_in_has_out) if has_in_has_out else []
        
        # no_in_has_out 按字母顺序排在最后
        no_in_has_out_ordered = sorted(no_in_has_out)
        
        # 合并结果
        return no_in_no_out + has_in_no_out + ordered_has_in_has_out + no_in_has_out_ordered

    @staticmethod
    def _topological_sort(dependencies: Dict[str, List[str]], files: List[str]) -> List[str]:
        """
        使用Kahn算法对有依赖关系的文件进行拓扑排序
        参数:
            dependencies: 文件依赖关系字典，键为文件名，值为该文件直接依赖的文件列表
            files: 需要排序的文件列表
        返回:
            拓扑排序后的文件列表
        """
        # 创建文件集合用于快速查找
        file_set = set(files)
        
        # 初始化入度字典，记录每个文件被依赖的次数
        in_degree = {file: 0 for file in files}
        
        # 构建图的邻接表表示并计算初始入度
        adjacency = {file: [] for file in files}
        
        # 填充邻接表并计算入度
        for file in files:
            if file in dependencies:
                for dep in dependencies[file]:
                    if dep in file_set:
                        # 修正依赖方向：dep → file
                        adjacency[dep].append(file)
                        in_degree[file] += 1
        
        # 寻找初始入度为0的节点
        queue = [file for file in files if in_degree[file] == 0]
        
        result = []
        
        # 进行拓扑排序
        while queue:
            current = queue.pop(0)
            result.append(current)
            
            # 处理当前节点的所有依赖
            for dependent in adjacency[current]:
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    queue.append(dependent)
        
        # 检查是否有循环依赖
        if len(result) != len(files):
            return []
        
        return result

    @staticmethod
    def compare_structure(old_node: Any, new_node: Any) -> bool:
        """
        递归比较结构
        检查新节点结构是否与旧节点结构一致
        主要提供给dir_file_fill命令使用
        """
        # 如果旧节点是字典
        if isinstance(old_node, dict):
            # 新节点也必须是字典
            if not isinstance(new_node, dict):
                return False
            
            # 检查旧节点的所有键是否都存在于新节点中
            old_keys = set(old_node.keys())
            new_keys = set(new_node.keys())
            
            # 旧键集合必须是新键集合的子集
            if not old_keys.issubset(new_keys):
                return False
            
            # 递归检查每个键的值
            for key, old_value in old_node.items():
                new_value = new_node[key]
                # 如果旧节点值是字典，递归比较
                if isinstance(old_value, dict):
                    if not DirJsonFuncs.compare_structure(old_value, new_value):
                        return False
                # 如果旧节点值不是字典（叶节点），新节点对应位置也必须不是字典
                elif isinstance(new_value, dict):
                    return False
                        
        return True
    
    @staticmethod
    def check_new_nodes_are_strings(node):
        """检查是否只添加了字符串类型的叶子节点"""
        if isinstance(node, dict):
            for key, value in node.items():
                # 如果值是字典，递归检查
                if isinstance(value, dict):
                    if not DirJsonFuncs.check_new_nodes_are_strings(value):
                        return False
                # 如果值不是字典，那它必须是字符串（文件描述）
                elif not isinstance(value, str):
                    return False
            return True
        return True

    @staticmethod
    def _collect_paths(node: Any, current_path: str = "", paths: Optional[Set[str]] = None) -> Set[str]:
        """
        收集proj_root_dict中的所有路径
        """
        if paths is None:
            paths = set()
            
        if isinstance(node, dict):
            for key, value in node.items():
                new_path = f"{current_path}/{key}" if current_path else key
                if isinstance(value, dict):
                    # 如果值是字典，递归收集子路径
                    DirJsonFuncs._collect_paths(value, new_path, paths)
                elif isinstance(value, str):
                    # 如果值是字符串，说明key是文件路径
                    paths.add(new_path)
        return paths

    @staticmethod
    def get_file_description(proj_root_dict_content: Dict, file_path: str) -> str:
        """
        获取文件描述
        从proj_root_dict_content结构中根据文件路径获取对应的文件描述
        """
        keys = file_path.split('/')
        current = proj_root_dict_content
        
        for key in keys[:-1]:  # 遍历目录部分
            if key in current and isinstance(current[key], dict):
                current = current[key]
            else:
                return ""
                
        # 获取文件描述
        file_name = keys[-1]
        if file_name in current and isinstance(current[file_name], str):
            return current[file_name]
        return ""

    @staticmethod
    def get_all_file_paths(proj_root_dict: Dict[str, Any]) -> List[str]:
        """
        获取proj_root_dict中的所有文件路径列表，按字母顺序排序
        返回: 文件路径列表
        """
        paths = DirJsonFuncs._collect_paths(proj_root_dict)
        return list(paths)

    @staticmethod
    def validate_dependent_paths(dependent_relation: Dict[str, Any], proj_root_dict: Dict[str, Any]) -> tuple[bool, List[str]]:
        """
        检查dependent_relation中的依赖路径是否都存在于proj_root_dict中
        返回: (是否有效, 错误信息列表)
        """
        errors = []
        
        if not isinstance(dependent_relation, dict):
            errors.append("dependent_relation 不是有效的字典类型")
            return False, errors
            
        # 收集proj_root_dict中的所有路径
        proj_root_dict_paths = DirJsonFuncs._collect_paths(proj_root_dict)
        
        # 检查dependent_relation中的依赖路径
        for dep_key, dep_value in dependent_relation.items():
            # 检查依赖项路径是否存在
            if dep_key not in proj_root_dict_paths:
                errors.append(f"dependent_relation 中的键 '{dep_key}' 在 proj_root_dict 中不存在")

            # 检查依赖项的值是否为列表
            if not isinstance(dep_value, list):
                errors.append(f"dependent_relation 中 '{dep_key}' 的值不是列表类型")
                continue

            # 检查依赖项中的被依赖路径是否存在
            for sub_dep_key in dep_value:
                if sub_dep_key not in proj_root_dict_paths:
                    errors.append(f"dependent_relation 中 '{dep_key}' 依赖的路径 '{sub_dep_key}' 在 proj_root_dict 中不存在")
        
        return len(errors) == 0, errors
