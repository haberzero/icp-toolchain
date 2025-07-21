import os
import json
from typing import List, Dict, Optional, Union


class MccpDirContentManager:
    _instance = None  # 类变量用于保存单例实例

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(MccpDirContentManager, cls).__new__(cls)
            cls._instance.init_project_path(*args, **kwargs)
        return cls._instance

    class ContentNode:
        # 内部节点信息结构体
        def __init__(self, node_type: str, name: str, path: str):
            self.node_type = node_type      # 节点类型, "file" 或 "directory"
            self.name = name                # 节点名称
            self.path = path                # 当前节点完整路径
            self.child_list = []            # 子节点列表，内容为节点名称列表
            self.parent = ''                # 父节点完整路径+父节点名称

    # 初始化目录内容管理器，dir_content.json不存在时会自动创建
    def init_project_path(self, project_path: str = ""):
        if project_path:
            self.project_path = project_path
            self.json_path = os.path.abspath(self.json_path)
            self.json_path = os.path.normpath(f"{project_path}/.mccp_config/mccp_dir_content.json")
            self.json_path = self.json_path.replace("\\", "/")  # 确保路径使用正斜杠
            
            if not os.path.exists(self.json_path):
                with open(self.json_path, 'w', encoding='utf-8') as f:
                    json.dump({}, f, indent=4, ensure_ascii=False)
            self.dir_content = self._load_content()
        else:
            self.project_path = ""
            self.json_path = ""
            self.dir_content = {}

    # 检查实例是否正确初始化，以及project_path是否正确设置
    def is_initialized(self) -> bool:
        if not self.project_path:
            print("警告: 未设置项目路径，目录内容管理器将无法正常工作")
        return bool(self.project_path and self.json_path and self.dir_content)

    # 加载JSON内容
    def _load_content(self) -> dict:
        if not self.json_path:
            print("警告: JSON路径未设置，无法加载内容")
            return {}
        try:
            with open(self.json_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {}

    # 保存JSON内容
    def _save_content(self) -> bool:
        if not self.json_path:
            print("警告: JSON路径未设置，无法保存内容")
            return False
        try:
            os.makedirs(os.path.dirname(self.json_path), exist_ok=True)
            with open(self.json_path, 'w', encoding='utf-8') as f:
                json.dump(self.dir_content, f, indent=4, ensure_ascii=False)
            return True
        except Exception:
            return False

    # 传入路径的结构处理，返回路径片段列表，便于针对JSON结构进行操作
    def _path_to_parts_list(self, path: str) -> List[str]:
        if not path:
            raise ValueError("Path cannot be empty.")

        # 检查是否包含 '..'（禁止向上级目录访问）
        if ".." in path:
            raise ValueError("Path contains '..' which is not allowed.")

        # 检查是否包含连续斜杠（// 或 \\）
        if "//" in path or "\\\\" in path:
            raise ValueError("Path contains consecutive slashes which are not allowed.")
        
        # 检查是否以proj_root开头
        if not path.startswith("proj_root/"):
            raise ValueError("Path must start with 'proj_root/'.")

        # 替换反斜杠为正斜杠，移除开头的斜杠，移除多余空格
        path = path.replace("\\", "/").lstrip("/").strip()

        # 分割路径并做简单过滤
        parts = [p for p in path.split("/") if p]

        # 检查每个路径片段是否合法（如不含控制字符等）
        for part in parts:
            if not part:  # 空路径片段
                raise ValueError("Empty path component detected.")
            if any(c in part for c in r'<>:"|?*'):  # 简单检查是否包含非法字符（Windows限制的）
                raise ValueError(f"Path component '{part}' contains invalid characters.")

        return parts
    from typing import List

    # 检查传入的路径状态
    def check_path_status(self, path_parts: List[str]) -> str:
        if not path_parts:
            raise ValueError("Path cannot be empty.")
        if path_parts[0] != "proj_root":
            raise ValueError("Path must start with 'proj_root/'.")
        
        current_content = self.dir_content
        
        # 遍历除最后一个节点外的所有路径
        for part in path_parts[:-1]:
            if part not in current_content:
                return "dir_invalid"
            
            parent_node = current_content[part]
            if parent_node is None:
                # 父目录路径中出现了一个文件节点，这是不允许的
                print(f"错误: 父目录 '{'/'.join(path_parts[:-1])}' 中包含文件节点 '{part}'")
                return "unexpected_node_type"
            elif not isinstance(parent_node, dict):
                # 如果不是 dict 类型，也不是 None（理论上不会出现），也视为错误
                print(f"错误: 父目录 '{'/'.join(path_parts[:-1])}' 中的节点 '{part}' 不是目录")
                return "unexpected_node_type"
            
            current_content = parent_node  # 继续深入

        # 检查最后一个节点是否存在
        last_part = path_parts[-1]
        if last_part in current_content:
            node = current_content[last_part]
            if isinstance(node, dict):
                return "dir_existed"
            elif node is None:
                return "file_existed"
            else:
                # 不应出现的类型
                print(f"错误: 未知状态，请检查相关代码")
                return "unexpected_node_type"
        else:
            return "dir_valid"

    def create_dir(self, path: str) -> bool:
        path_parts = self._path_to_parts_list(path)

        if not path_parts:
            return False
        
        # 检查传入路径的状态
        status = self.check_path_status(path_parts)
        if status != "dir_valid":
            print(f"无法创建目录 '{path}': {status}")
            return False
        
        if status == "dir_existed":
            print(f"目录 '{path}' 已存在")
            return False

        if status == "file_existed":
            print(f"无法在 '{'/'.join(path_parts[:-1])}' 中创建目录，因为存在同名文件 '{path_parts[-1]}'")
            return False
        
        if status == "dir_valid":
            current_content = self.dir_content
            for part in path_parts:
                if part not in current_content:
                    current_content[part] = {}
                current_content = current_content[part]

        return self._save_content()

    def create_file(self, path: str) -> bool:
        path_parts = self._path_to_parts_list(path)

        if not path_parts:
            return False

        # 检查路径状态
        status = self.check_path_status(path_parts)
        if status == "file_existed":
            print(f"文件 '{path}' 已存在")
            return False
        elif status == "dir_existed":
            print(f"存在同名目录 '{path}'，无法创建文件")
            return False
        elif status == "unexpected_node_type":
            print(f"路径 '{path}' 中存在非法节点类型")
            return False

        # 路径有效，可以创建文件
        current_content = self.dir_content
        for part in path_parts[:-1]:
            current_content = current_content[part]

        last_part = path_parts[-1]
        current_content[last_part] = None  # 文件用 None 表示

        return self._save_content()

    def delete_dir(self, path: str) -> bool:
        path_parts = self._path_to_parts_list(path)

        if not path_parts:
            return False

        status = self.check_path_status(path_parts)
        if status != "dir_existed":
            print(f"目录 '{path}' 不存在或不是目录")
            return False

        # 删除目录
        current_content = self.dir_content
        for part in path_parts[:-1]:
            current_content = current_content[part]

        del current_content[path_parts[-1]]
        return self._save_content()
    
    def delete_file(self, path: str) -> bool:
        path_parts = self._path_to_parts_list(path)

        if not path_parts:
            return False

        status = self.check_path_status(path_parts)
        if status != "file_existed":
            print(f"文件 '{path}' 不存在或不是文件")
            return False

        # 删除文件
        current_content = self.dir_content
        for part in path_parts[:-1]:
            current_content = current_content[part]

        del current_content[path_parts[-1]]
        return self._save_content()
    
    # 以字典形式返回特定路径下的，展平的完整目录结构，并且指明每个节点的类型（文件或目录）
    def get_flat_path_dict(self, path: str) -> dict:

        # 递归解析 JSON 对象，将键路径以 "dir1/dir2/key" 形式存入 content_dict。
        def _recursive_parser(init_path_str, content_dict, stack, json_obj):
            # 临时列表用于保存当前层级的所有 key
            temp_list = []

            # 遍历当前 JSON 对象的键
            for key in json_obj:
                # 构造当前路径字符串
                current_path = init_path_str + "/".join(stack + [key])
                value = json_obj[key]

                if type(value) is dict:
                    # 如果值是字典且不为空，则视为目录
                    content_dict[current_path] = "dir"
                    temp_list.append((key, value))
                elif value is None or not isinstance(value, dict):
                    # 如果值为 null 或非字典类型，则视为文件
                    content_dict[current_path] = "file"
                else:
                    # Something wrong, should not happen
                    print(f"错误: 不被期望的节点内容 '{current_path}'")

            # 逆序遍历 temp_list，模拟栈操作
            for key, value in reversed(temp_list):
                if type(value) is dict:
                    stack.append(key)
                    _recursive_parser(init_path_str, content_dict, stack, value)
                    stack.pop()

        path_parts = self._path_to_parts_list(path)

        if not path_parts:
            return {}

        current_content = self.dir_content
        for part in path_parts:
            if part not in current_content:
                print(f"路径 '{path}' 不存在")
                return {}
            current_content = current_content[part]

        init_path_str = "/".join(path_parts) + "/" if path_parts else ""

        # 生成节点列表
        temp_stack = []
        content_dict = {}
        _recursive_parser(init_path_str, content_dict, temp_stack, current_content)
        
        return content_dict


# 创建一个单例实例，供模块导入时使用
_instance = MccpDirContentManager()

# 提供一个全局访问方法
def get_instance():
    return _instance
