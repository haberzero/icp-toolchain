import os
import json


# 单例，请勿进行额外创建，只允许外部import文件末尾的唯一实例
class MccpDirContentManager:
    def __init__(self, project_path):
        """初始化目录内容管理器
        :param project_path: 项目根路径
        """
        self.project_path = project_path
        # 构建mccp_dir_content.json文件路径，统一使用正斜杠
        self.json_path = os.path.normpath(f"{project_path}/.mccp_config/mccp_dir_content.json").replace("\\", "/")
        self.dir_content = self._load_dir_content()
        # 确保顶层src对象存在
        if "src" not in self.dir_content:
            self.dir_content["src"] = {}
            self._save_dir_content()

    def _load_dir_content(self):
        """加载目录内容JSON文件，如果文件不存在则直接返回一个空{}"""
        if os.path.exists(self.json_path):
            try:
                with open(self.json_path, 'r', encoding='utf-8') as f:
                    content = json.load(f)
                    # 确保顶层结构正确
                    if isinstance(content, dict):
                        return content
                    print("警告: 目录内容文件结构不正确，将使用默认结构")
            except Exception as e:
                print(f"警告: 加载目录内容文件失败 - {str(e)}")
        return {}

    def _save_dir_content(self):
        """保存目录内容到JSON文件"""
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(self.json_path), exist_ok=True)
            with open(self.json_path, 'w', encoding='utf-8') as f:
                json.dump(self.dir_content, f, indent=4, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"保存目录内容文件失败 - {str(e)}")
            return False

    def _normalize_path(self, path):
        if not path:
            return []
        normalized = path.replace('.', '/').replace('\\', '/').strip('/')
        components = [c for c in normalized.split('/') if c]  # 过滤掉空字符串
        return components

    def _get_node(self, path_components):
        """根据路径组件获取对应的节点及父节点
        :param path_components: 标准化后的路径组件列表
        :return: (parent_node, target_node, target_name) 或 (None, None, None) if not found
        """
        current_node = self.dir_content["src"]
        parent_node = None
        target_name = None

        for i, component in enumerate(path_components):
            if component not in current_node:
                return (None, None, None)

            if i == len(path_components) - 1:
                target_name = component
                parent_node = current_node
                current_node = current_node[component]
                break

            next_node = current_node[component]
            if not isinstance(next_node, dict):
                return (None, None, None)
            current_node = next_node

        return (parent_node, current_node, target_name)

    def read_all_dir(self):
        """读取全目录，返回src对应的对象"""
        return self.dir_content["src"].copy()

    def read_directory(self, path):
        """读取某个目录
        :param path: 目录路径，如"ui.main_window"或"ui/main_window"
        :return: 目录对象或None
        """
        path_components = self._normalize_path(path)
        if not path_components:
            print("警告: 目录路径不能为空")
            return None

        parent_node, target_node, target_name = self._get_node(path_components)

        if not target_node:
            print(f"警告: 目录 '{path}' 不存在")
            return None

        if not isinstance(target_node, dict):
            print(f"警告: '{path}' 是文件，不是目录")
            return None

        return target_node.copy()

    def file_exists(self, path):
        """确定某文件是否存在
        :param path: 文件路径，如"ui.main_window.main_entry"或"ui/main_window/main_entry"
        :return: True if exists and is file, None otherwise
        """
        path_components = self._normalize_path(path)
        if not path_components:
            print("警告: 文件路径不能为空")
            return None

        parent_node, target_node, target_name = self._get_node(path_components)

        if not target_node:
            print(f"警告: 文件 '{path}' 不存在")
            return None

        if isinstance(target_node, dict):
            print(f"警告: '{path}' 是目录，不是文件")
            return None

        return True

    def create_directory(self, path):
        """新建一个目录
        :param path: 目录路径，如"ui.main_window"或"ui/main_window"
        :return: True if created successfully, False otherwise
        """
        path_components = self._normalize_path(path)
        if not path_components:
            print("警告: 目录路径不能为空")
            return False

        current_node = self.dir_content["src"]

        for i, component in enumerate(path_components):
            # 检查当前组件是否存在
            if component in current_node:
                child_node = current_node[component]
                # 如果是最后一个组件且已存在
                if i == len(path_components) - 1:
                    if isinstance(child_node, dict):
                        print(f"警告: 目录 '{path}' 已存在")
                        return False
                    else:
                        print(f"警告: 与文件 '{path}' 同名，无法创建目录")
                        return False
                # 如果不是最后一个组件但存在且不是目录
                elif not isinstance(child_node, dict):
                    print(f"警告: 路径 '{'/'.join(path_components[:i+1])}' 是文件，无法创建子目录")
                    return False
                # 继续遍历下一级目录
                current_node = child_node
            else:
                # 如果是最后一个组件，创建目录
                if i == len(path_components) - 1:
                    current_node[component] = {}
                    return self._save_dir_content()
                # 创建中间目录
                current_node[component] = {}
                current_node = current_node[component]

        return False

    def create_file(self, path):
        """新建一个文件
        :param path: 文件路径，如"ui.main_window.main_entry"或"ui/main_window/main_entry"
        :return: True if created successfully, False otherwise
        """
        path_components = self._normalize_path(path)
        if not path_components or len(path_components) < 1:
            print("警告: 文件路径不能为空")
            return False

        # 分离目录部分和文件名
        dir_components = path_components[:-1]
        file_name = path_components[-1]

        # 获取父目录节点
        if dir_components:
            parent_node, _, _ = self._get_node(dir_components)
            if not parent_node or not isinstance(parent_node, dict):
                print(f"警告: 文件父目录不存在或不是目录")
                return False
        else:
            parent_node = self.dir_content["src"]

        # 检查是否已存在同名条目
        if file_name in parent_node:
            existing_node = parent_node[file_name]
            if isinstance(existing_node, dict):
                print(f"警告: 与目录 '{path}' 同名，无法创建文件")
            else:
                print(f"警告: 文件 '{path}' 已存在")
            return False

        # 创建文件节点（值为null表示文件）
        parent_node[file_name] = None
        return self._save_dir_content()

    def delete_directory(self, path):
        """删除目录及其内容
        :param path: 目录路径
        :return: True if deleted successfully, False otherwise
        """
        path_components = self._normalize_path(path)
        if not path_components:
            print("警告: 目录路径不能为空")
            return False

        parent_node, target_node, target_name = self._get_node(path_components)

        if not target_node:
            print(f"警告: 目录 '{path}' 不存在")
            return False

        if not isinstance(target_node, dict):
            print(f"警告: '{path}' 是文件，不是目录")
            return False

        del parent_node[target_name]
        return self._save_dir_content()

    def delete_file(self, path):
        """删除文件
        :param path: 文件路径
        :return: True if deleted successfully, False otherwise
        """
        path_components = self._normalize_path(path)
        if not path_components:
            print("警告: 文件路径不能为空")
            return False

        parent_node, target_node, target_name = self._get_node(path_components)

        if not target_node:
            print(f"警告: 文件 '{path}' 不存在")
            return False

        if isinstance(target_node, dict):
            print(f"警告: '{path}' 是目录，不是文件")
            return False

        del parent_node[target_name]
        return self._save_dir_content()


# 自测代码
if __name__ == "__main__":
    import tempfile
    import shutil

    # 创建临时目录
    temp_dir = tempfile.mkdtemp()
    try:
        # 初始化管理器
        manager = MccpDirContentManager(temp_dir)
        print("初始化测试: ", "通过" if manager.read_all_dir() == {} else "失败")

        # 测试创建目录
        dir_result = manager.create_directory("ui/main_window")
        print("创建目录测试: ", "通过" if dir_result else "失败")

        # 测试创建文件
        file_result = manager.create_file("ui/main_window/main_entry")
        print("创建文件测试: ", "通过" if file_result else "失败")

        # 测试读取目录
        dir_content = manager.read_directory("ui/main_window")
        expected_content = {"main_entry": None}
        print("读取目录测试: ", "通过" if dir_content == expected_content else "失败")

        # 测试文件存在性
        exists_result = manager.file_exists("ui/main_window/main_entry")
        print("文件存在测试: ", "通过" if exists_result else "失败")

        # 测试删除文件
        delete_file_result = manager.delete_file("ui/main_window/main_entry")
        print("删除文件测试: ", "通过" if delete_file_result else "失败")

        # 测试删除目录
        delete_dir_result = manager.delete_directory("ui/main_window")
        print("删除目录测试: ", "通过" if delete_dir_result else "失败")

    finally:
        # 清理临时目录
        shutil.rmtree(temp_dir)


g_mccp_dir_content_manager = MccpDirContentManager()