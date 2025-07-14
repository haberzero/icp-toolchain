import os
import json
import time

class FileOperator:
    def __init__(self, root_path):
        self.root_path = root_path  # 用户指定的工作区路径
        # 获取 main.py 所在目录（假设 file_operations.py 在 app 目录下）
        main_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # 上级目录即 main.py 所在路径
        self.hidden_folder = os.path.join(main_dir, '.fileScope')  # 固定在 main.py 目录下
        self.ignore_file = os.path.join(self.hidden_folder, 'fileScope_ignore.json')  # 改为 json 格式
        self.recent_paths_file = os.path.join(self.hidden_folder, 'recent_paths.json')  # 新增：最近路径存储文件
        self.ensure_hidden_folder_exists()
        # 新增：初始化忽略列表
        self.ignore_list = self.read_ignore_list()  # 读取并保存忽略列表
        self.recent_paths = self.read_recent_paths()  # 新增：读取最近路径

    def ensure_hidden_folder_exists(self):
        # 改为使用 main.py 目录下的隐藏文件夹
        if not os.path.exists(self.hidden_folder):
            os.makedirs(self.hidden_folder)

    def read_ignore_list(self):
        # 读取 json 格式的忽略列表（返回 [{"workspace_path": "...", "ignore_info": [...]}]）
        if not os.path.exists(self.ignore_file):
            return []
        with open(self.ignore_file, 'r', encoding='utf-8') as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return []

    def write_ignore_list(self, ignore_list):
        # 写入 json 格式的忽略列表
        with open(self.ignore_file, 'w', encoding='utf-8') as f:
            json.dump(ignore_list, f, indent=2, ensure_ascii=False)

    def read_recent_paths(self):
        """读取最近5个路径（最多保留5条）"""
        if not os.path.exists(self.recent_paths_file):
            return []
        with open(self.recent_paths_file, 'r', encoding='utf-8') as f:
            try:
                paths = json.load(f)
                return paths[:5]  # 确保最多5条
            except json.JSONDecodeError:
                return []

    def write_recent_paths(self, new_path):
        """添加新路径到最近列表（去重并保持最多5条）"""
        current_paths = self.read_recent_paths()
        # 去重并将新路径移到最前面
        updated_paths = [new_path] + [p for p in current_paths if p != new_path]
        self.recent_paths = updated_paths[:5]  # 截断到5条
        with open(self.recent_paths_file, 'w', encoding='utf-8') as f:
            json.dump(self.recent_paths, f, indent=2, ensure_ascii=False)

    def clear_ignore_list(self):
        """清空忽略列表（需求4）"""
        self.write_ignore_list([])

    def save_tree_to_markdown(self, md_content):
        # 直接接收已生成的带标题的md_content并保存到.hidden_folder（即main.py目录下的.fileScope）
        target_path = os.path.join(self.hidden_folder, "dir_tree_struct.md")  # 新增路径拼接
        with open(target_path, "w", encoding="utf-8") as f:  # 修改文件路径
            f.write(md_content)

    def _write_node(self, node, file, prefix):
        file.write(prefix + '- ' + node['name'] + '\n')
        for child in node.get('children', []):
            self._write_node(child, file, prefix + '  ')

    def _get_current_ignore_list(self, folder_path):
        """获取当前文件夹下的忽略路径"""
        return [
            path for entry in self.ignore_list  # 遍历每个工作区的忽略配置
            for path in entry.get("ignore_info", [])  # 从每个配置中获取具体忽略路径
            if os.path.dirname(path) == folder_path  # 检查路径的父目录是否匹配当前文件夹
        ]

