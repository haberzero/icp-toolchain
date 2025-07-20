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

    class NodeInfo:
        # 内部节点信息结构体
        def __init__(self, name: str, is_directory: bool, path: str):
            self.name = name                # 节点名称
            self.is_directory = is_directory # 是否为目录
            self.path = path                # 完整路径
            self.child_list = []            # 子节点列表，内容为节点名称列表
            self.parent = ''              # 父节点完整路径+父节点名称

    # 初始化目录内容管理器
    def init_project_path(self, project_path: str = ""):
        if project_path:
            self.project_path = project_path
            self.json_path = os.path.normpath(f"{project_path}/.mccp_config/mccp_dir_content.json")
            self.json_path = self.json_path.replace("\\", "/")
            if not os.path.exists(self.json_path):
                with open(self.json_path, 'w', encoding='utf-8') as f:
                    json.dump({}, f, indent=4, ensure_ascii=False)
            self.dir_content = self._load_content()
        else:
            self.project_path = ""
            self.json_path = ""
            self.dir_content = {}
            print("警告: 未设置项目路径，目录内容管理器将无法正常工作")

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

    # 获取节点引用
    def _get_node_ref(self, path_parts: List[str]) -> Optional[dict]:
        current = self.dir_content
        for part in path_parts:
            if not isinstance(current, dict) or part not in current:
                return None
            current = current[part]
        return current if isinstance(current, dict) else None

    # 获取父节点和目标名称
    def _get_parent_and_name(self, path_parts: List[str]) -> tuple:
        if not path_parts:
            return self.dir_content, ""
        
        parent_parts = path_parts[:-1]
        target_name = path_parts[-1]
        parent_node = self._get_node_ref(parent_parts) if parent_parts else self.dir_content
        
        return parent_node, target_name

    def _normalize_path(self, path: str) -> List[str]:
        if not path:
            raise ValueError("Path cannot be empty.")

        # 检查是否包含 '..'（禁止向上级目录访问）
        if ".." in path:
            raise ValueError("Path contains '..' which is not allowed.")

        # 检查是否包含连续斜杠（// 或 \\）
        if "//" in path or "\\\\" in path:
            raise ValueError("Path contains consecutive slashes which are not allowed.")
        
        # 根目录直接返回
        if path == "/":
            return []

        # 移除开头的斜杠，并替换反斜杠为正斜杠
        path = path.strip()
        clean_path = path.lstrip("/").replace("\\", "/")

        # 分割路径并做简单过滤
        parts = [p for p in clean_path.split("/") if p]

        # 检查每个路径片段是否合法（如不含控制字符等）
        for part in parts:
            if not part:  # 空路径片段
                raise ValueError("Empty path component detected.")
            if any(c in part for c in r'<>:"|?*'):  # 简单检查是否包含非法字符（Windows限制的）
                raise ValueError(f"Path component '{part}' contains invalid characters.")

        return parts

    # 检查路径是否存在
    def exists(self, path: str) -> bool:
        path_parts = self._normalize_path(path)
        if not path_parts:
            return True  # 根目录总是存在
        
        parent_node, target_name = self._get_parent_and_name(path_parts)
        return parent_node is not None and target_name in parent_node

    # 检查是否为目录
    def is_directory(self, path: str) -> bool:
        path_parts = self._normalize_path(path)
        if not path_parts:
            return True  # 根目录是目录
        
        parent_node, target_name = self._get_parent_and_name(path_parts)
        if parent_node is None or target_name not in parent_node:
            return False
        
        return isinstance(parent_node[target_name], dict)

    # 检查是否为文件
    def is_file(self, path: str) -> bool:
        return self.exists(path) and not self.is_directory(path)

    # 列出目录内容
    def list_directory(self, path: str = "") -> List[NodeInfo]:
        path_parts = self._normalize_path(path)
        node = self._get_node_ref(path_parts) if path_parts else self.dir_content
        
        if node is None:
            return []
        
        result = []
        base_path = "/" + "/".join(path_parts) if path_parts else ""
        parent_path = path if path else "/"
        
        for name, value in node.items():
            is_dir = isinstance(value, dict)
            item_path = f"{base_path}/{name}".strip("/")
            
            # 创建NodeInfo实例
            node_info = self.NodeInfo(name, is_dir, item_path)
            
            # 设置父节点路径
            node_info.parent = parent_path
            
            # 如果是目录，填充子节点列表
            if is_dir and isinstance(value, dict):
                node_info.child_list = list(value.keys())
            
            result.append(node_info)
        
        return result

    # 创建目录
    def create_directory(self, path: str) -> bool:
        if not path.strip():
            return False
        
        path_parts = self._normalize_path(path)
        if not path_parts:
            return False
        
        # 检查是否已存在
        if self.exists(path):
            return False
        
        # 逐级创建目录
        current = self.dir_content
        for part in path_parts:
            if part not in current:
                current[part] = {}
            elif not isinstance(current[part], dict):
                return False  # 路径冲突：存在同名文件
            current = current[part]
        
        return self._save_content()

    # 创建文件
    def create_file(self, path: str) -> bool:
        if not path.strip():
            return False
        
        path_parts = self._normalize_path(path)
        if not path_parts:
            return False
        
        # 检查是否已存在
        if self.exists(path):
            return False
        
        # 确保父目录存在
        if len(path_parts) > 1:
            parent_path = "/".join(path_parts[:-1])
            if not self.exists(parent_path):
                if not self.create_directory(parent_path):
                    return False
            elif not self.is_directory(parent_path):
                return False  # 父路径是文件，无法创建
        
        # 创建文件
        parent_node, file_name = self._get_parent_and_name(path_parts)
        if parent_node is not None:
            parent_node[file_name] = None
            return self._save_content()
        
        return False

    # 删除路径（文件或目录）
    def delete(self, path: str) -> bool:
        if not path.strip():
            return False
        
        path_parts = self._normalize_path(path)
        if not path_parts:
            return False  # 不能删除根目录
        
        parent_node, target_name = self._get_parent_and_name(path_parts)
        if parent_node is None or target_name not in parent_node:
            return False
        
        del parent_node[target_name]
        return self._save_content()

    # 移动/重命名
    def move(self, old_path: str, new_path: str) -> bool:
        if not self.exists(old_path) or self.exists(new_path):
            return False
        
        old_parts = self._normalize_path(old_path)
        new_parts = self._normalize_path(new_path)
        
        if not old_parts or not new_parts:
            return False
        
        # 获取源数据
        old_parent, old_name = self._get_parent_and_name(old_parts)
        if old_parent is None or old_name not in old_parent:
            return False
        
        source_data = old_parent[old_name]
        
        # 确保目标父目录存在
        if len(new_parts) > 1:
            new_parent_path = "/".join(new_parts[:-1])
            if not self.exists(new_parent_path):
                if not self.create_directory(new_parent_path):
                    return False
        
        # 移动数据
        new_parent, new_name = self._get_parent_and_name(new_parts)
        if new_parent is not None:
            new_parent[new_name] = source_data
            del old_parent[old_name]
            return self._save_content()
        
        return False

    # 获取完整的目录树（扁平化列表）
    def get_all_paths(self) -> List[NodeInfo]:
        result = []
        
        def _traverse(node: dict, current_path: str = "", parent_path: Optional[str] = None):
            for name, value in node.items():
                is_dir = isinstance(value, dict)
                item_path = f"{current_path}/{name}".strip("/")
                
                # 创建NodeInfo实例
                node_info = self.NodeInfo(name, is_dir, item_path)
                
                # 设置父节点路径
                node_info.parent = parent_path if parent_path else ("/" if current_path else '')
                
                # 如果是目录，填充子节点列表
                if is_dir and isinstance(value, dict):
                    node_info.child_list = list(value.keys())
                
                result.append(node_info)
                
                if is_dir:
                    _traverse(value, item_path, item_path)
        
        _traverse(self.dir_content)
        return result

    # 获取指定路径的NodeInfo对象
    def get_node_info(self, path: str) -> Optional[NodeInfo]:
        """获取指定路径的NodeInfo对象，包含完整的父子关系信息"""
        if not self.exists(path):
            return None
        
        path_parts = self._normalize_path(path)
        if not path_parts:
            # 根目录
            node_info = self.NodeInfo("/", True, "/")
            node_info.parent = ''
            node_info.child_list = list(self.dir_content.keys())
            return node_info
        
        # 获取父路径
        parent_path = "/" + "/".join(path_parts[:-1]) if len(path_parts) > 1 else "/"
        parent_path = parent_path.strip("/") if parent_path != "/" else "/"
        
        name = path_parts[-1]
        is_dir = self.is_directory(path)
        
        # 创建NodeInfo实例
        node_info = self.NodeInfo(name, is_dir, path)
        node_info.parent = parent_path if parent_path != "/" else ''
        
        # 如果是目录，获取子节点列表
        if is_dir:
            children = self.list_directory(path)
            node_info.child_list = [child.name for child in children]
        
        return node_info

    # 获取节点的所有子孙节点
    def get_descendants(self, path: str) -> List[NodeInfo]:
        """获取指定路径下的所有子孙节点"""
        if not self.is_directory(path):
            return []
        
        result = []
        
        def _collect_descendants(current_path: str):
            children = self.list_directory(current_path)
            for child in children:
                result.append(child)
                if child.is_directory:
                    _collect_descendants(child.path)
        
        _collect_descendants(path)
        return result

    # 获取节点的所有祖先节点路径
    def get_ancestors(self, path: str) -> List[str]:
        """获取指定路径的所有祖先节点路径"""
        path_parts = self._normalize_path(path)
        ancestors = []
        
        for i in range(len(path_parts)):
            ancestor_path = "/" + "/".join(path_parts[:i+1])
            ancestor_path = ancestor_path.strip("/")
            if ancestor_path:
                ancestors.append(ancestor_path)
        
        return ancestors

    # 获取节点的直接父节点信息
    def get_parent_info(self, path: str) -> Optional[NodeInfo]:
        """获取指定路径的直接父节点信息"""
        path_parts = self._normalize_path(path)
        if not path_parts:
            return None  # 根目录没有父节点
        
        if len(path_parts) == 1:
            # 父节点是根目录
            return self.get_node_info("/")
        
        parent_path = "/" + "/".join(path_parts[:-1])
        parent_path = parent_path.strip("/")
        return self.get_node_info(parent_path)

    # 获取节点的直接子节点信息
    def get_children_info(self, path: str) -> List[NodeInfo]:
        """获取指定路径的直接子节点信息"""
        return self.list_directory(path)


# 创建一个单例实例，供模块导入时使用
_instance = MccpDirContentManager()

# 提供一个全局访问方法
def get_instance():
    return _instance
