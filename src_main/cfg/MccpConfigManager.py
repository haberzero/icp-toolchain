import os
import json

class MccpConfigManager:
    def __init__(self, project_path):
        """初始化配置管理器
        :param project_path: 项目根路径
        """
        self.project_path = project_path
        self.config_path = os.path.join(project_path, '.mccp_config', 'mccp_config.json')
        # 处理斜杠方向
        self.config_path = self.config_path.replace('\\', '/')
        self.config_data = self._load_config()

    def _load_config(self):
        """加载配置文件数据，如果文件不存在则返回空字典"""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"警告: 加载配置文件失败 - {str(e)}")
        return {}

    def read_param(self, param_path):
        """读取配置参数
        :param param_path: 参数路径，支持嵌套参数，如 'fileSystemMapping.targetLayerDir'
        :return: 参数值或None
        """
        keys = param_path.split('.')
        current_data = self.config_data

        for key in keys:
            if isinstance(current_data, dict) and key in current_data:
                current_data = current_data[key]
            else:
                print(f"警告: 参数 '{param_path}' 不存在于配置文件中")
                return None
        return current_data

    def write_param(self, param_path, value):
        """写入配置参数
        :param param_path: 参数路径，支持嵌套参数，如 'fileSystemMapping.targetLayerDir'
        :param value: 要写入的参数值
        :return: 是否写入成功
        """
        keys = param_path.split('.')
        current_data = self.config_data

        # 遍历除最后一个键之外的所有键，创建嵌套结构
        for key in keys[:-1]:
            if key not in current_data or not isinstance(current_data[key], dict):
                current_data[key] = {}
            current_data = current_data[key]

        # 设置最后一个键的值
        current_data[keys[-1]] = value

        # 保存配置文件
        try:
            # 创建目录（如果不存在）
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config_data, f, ensure_ascii=False, indent=4)
            return True
        except Exception as e:
            print(f"错误: 写入配置文件失败 - {str(e)}")
            return False

    def get_all_config(self):
        """获取所有配置数据"""
        return self.config_data

    def set_all_config(self, new_config):
        """设置所有配置数据
        :param new_config: 新的配置字典
        :return: 是否设置成功
        """
        if not isinstance(new_config, dict):
            print("错误: 配置数据必须是字典类型")
            return False

        self.config_data = new_config
        try:
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config_data, f, ensure_ascii=False, indent=4)
            return True
        except Exception as e:
            print(f"错误: 写入配置文件失败 - {str(e)}")
            return False

if __name__ == "__main__":
    # 自测试代码
    import tempfile
    import shutil

    # 创建临时目录
    temp_dir = tempfile.mkdtemp()
    try:
        print(f"测试配置管理器，使用临时目录: {temp_dir}")
        config_manager = MccpConfigManager(temp_dir)

        # 测试写入参数
        print("测试写入参数...")
        config_manager.write_param("projectName", "test_project")
        config_manager.write_param("targetLanguage", "Python")
        config_manager.write_param("fileSystemMapping.behavioralLayerDir", "src_mcbc")
        config_manager.write_param("fileSystemMapping.symbolicLayerDir", "src_mcpc")
        config_manager.write_param("fileSystemMapping.targetLayerDir", "src_main")
        config_manager.write_param("fileSystemMapping.is_extra_suffix", True)

        # 测试读取参数
        print("测试读取参数...")
        print(f"项目名称: {config_manager.read_param('projectName')}")
        print(f"目标语言: {config_manager.read_param('targetLanguage')}")
        print(f"行为层目录: {config_manager.read_param('fileSystemMapping.behavioralLayerDir')}")

        # 测试读取不存在的参数
        print("测试读取不存在的参数...")
        print(f"不存在的参数: {config_manager.read_param('nonexistent.param')}")

        # 测试获取所有配置
        print("测试获取所有配置...")
        all_config = config_manager.get_all_config()
        print(json.dumps(all_config, ensure_ascii=False, indent=2))

        print("所有测试完成成功")
    except Exception as e:
        print(f"测试过程中发生错误: {str(e)}")
    finally:
        # 清理临时目录
        shutil.rmtree(temp_dir)