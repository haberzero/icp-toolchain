import os

class IgnoreManager:
    def __init__(self, file_ops):
        self.file_ops = file_ops

    def add_to_ignore(self, path):
        ignore_list = self.file_ops.read_ignore_list()
        current_workspace = self.file_ops.root_path  # 当前工作区绝对路径
        abs_path = os.path.abspath(path)  # 确保忽略路径为绝对路径

        # 查找当前工作区是否已存在记录
        existing_entry = next((item for item in ignore_list if item["workspace_path"] == current_workspace), None)
        if existing_entry:
            if abs_path not in existing_entry["ignore_info"]:
                existing_entry["ignore_info"].append(abs_path)
        else:
            ignore_list.append({
                "workspace_path": current_workspace,  # 工作区绝对路径
                "ignore_info": [abs_path]  # 忽略路径绝对路径列表
            })
        self.file_ops.write_ignore_list(ignore_list)  # 写入 json 文件

    def remove_from_ignore(self, path):
        ignore_list = self.file_ops.read_ignore_list()
        current_workspace = self.file_ops.root_path
        abs_path = os.path.abspath(path)

        existing_entry = next((item for item in ignore_list if item["workspace_path"] == current_workspace), None)
        if existing_entry and abs_path in existing_entry["ignore_info"]:
            existing_entry["ignore_info"].remove(abs_path)
            # 可选：若忽略列表为空则删除该工作区记录
            if not existing_entry["ignore_info"]:
                ignore_list.remove(existing_entry)
            self.file_ops.write_ignore_list(ignore_list)

