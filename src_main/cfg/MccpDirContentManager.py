import os
import json

class MccpDirContentManager:
    def __init__(self, project_path):
        """初始化目录内容管理器
        :param project_path: 项目根路径
        """
        self.project_path = project_path
        # 构建mccp_dir_content.json文件路径，统一使用正斜杠
        self.json_path = os.path.normpath(f"{project_path}/.mccp_config/mccp_dir_content.json").replace("\\", "/")
        self.dir_content = self._load_dir_content()

    def _load_dir_content(self):
        """加载目录内容JSON文件，如果文件不存在则返回空字典"""
        if os.path.exists(self.json_path):
            try:
                with open(self.json_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"警告: 加载目录内容文件失败 - {str(e)}")
        return {}

    def read_dir_content(self, path=None):
        """读取目录内容
        :param path: 可选参数，指定要读取的路径，如"src_main/ui"，不指定则返回全部内容
        :return: 目录内容字典或None
        """
        if not path:
            return self.dir_content.copy()

        # 将路径转换为统一格式（正斜杠分隔）
        normalized_path = path.replace("\\", "/")
        if normalized_path in self.dir_content:
            return self.dir_content[normalized_path].copy()
        else:
            print(f"警告: 路径 '{normalized_path}' 不存在于目录内容文件中")
            return None

    def write_dir_content(self, path, content):
        """写入目录内容
        :param path: 要写入的路径，如"src_main/ui"
        :param content: 要写入的内容字典
        :return: 是否写入成功
        """
        if not isinstance(content, dict):
            print("错误: 目录内容必须是字典类型")
            return False

        # 将路径转换为统一格式（正斜杠分隔）
        normalized_path = path.replace("\\", "/")
        self.dir_content[normalized_path] = content

        return self._save_dir_content()

    def delete_dir_content(self, path):
        """删除指定路径的目录内容
        :param path: 要删除的路径
        :return: 是否删除成功
        """
        normalized_path = path.replace("\\", "/")
        if normalized_path in self.dir_content:
            del self.dir_content[normalized_path]
            return self._save_dir_content()
        else:
            print(f"警告: 路径 '{normalized_path}' 不存在于目录内容文件中")
            return False

    def _save_dir_content(self):
        """保存目录内容到JSON文件"""
        try:
            # 创建目录（如果不存在）
            os.makedirs(os.path.dirname(self.json_path), exist_ok=True)
            with open(self.json_path, 'w', encoding='utf-8') as f:
                json.dump(self.dir_content, f, ensure_ascii=False, indent=4)
            return True
        except Exception as e:
            print(f"错误: 写入目录内容文件失败 - {str(e)}")
            return False

    def get_all_paths(self):
        """获取所有已记录的路径列表"""
        return list(self.dir_content.keys())

if __name__ == "__main__":
    # 自测试代码
    import tempfile
    import shutil

    # 创建临时目录
    temp_dir = tempfile.mkdtemp()
    try:
        print(f"测试目录内容管理器，使用临时目录: {temp_dir}")
        dir_manager = MccpDirContentManager(temp_dir)

        # 测试写入目录内容
        print("测试写入目录内容...")
        dir_manager.write_dir_content("src_main/ui", {
            "type": "directory",
            "files": ["MainWindow.py", "LeftSideBrowser.py"],
            "subdirectories": []
        })

        dir_manager.write_dir_content("src_main/utils", {
            "type": "directory",
            "files": [],
            "subdirectories": ["module_dir_generator", "module_symbols_reader"]
        })

        # 测试读取特定路径内容
        print("测试读取特定路径内容...")
        ui_content = dir_manager.read_dir_content("src_main/ui")
        print(f"src_main/ui 内容: {ui_content}")

        # 测试读取所有内容
        print("测试读取所有内容...")
        all_content = dir_manager.read_dir_content()
        print(f"所有目录内容: {json.dumps(all_content, ensure_ascii=False, indent=2)}")

        # 测试获取所有路径
        print("测试获取所有路径...")
        all_paths = dir_manager.get_all_paths()
        print(f"所有路径: {all_paths}")

        # 测试删除路径
        print("测试删除路径...")
        dir_manager.delete_dir_content("src_main/utils")
        print(f"删除后所有路径: {dir_manager.get_all_paths()}")

        print("所有测试完成成功")
    except Exception as e:
        print(f"测试过程中发生错误: {str(e)}")
    finally:
        # 清理临时目录
        shutil.rmtree(temp_dir)