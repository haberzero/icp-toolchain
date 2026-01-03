import os
import json
from typing import Dict, Optional, List
from .path_manager import get_instance as get_path_manager

class ToolchainStore:
    """
    Manages toolchain-level data: System Prompts, User Prompt Templates, and App Data.
    """
    def __init__(self):
        self.path_manager = get_path_manager()
        self._sys_prompts: Dict[str, str] = {}
        self._user_templates: Dict[str, str] = {}
        self._app_data: Dict[str, Any] = {}
        self._load_app_data()

    # --- Prompt Management ---

    def load_prompts(self):
        """Reloads all prompts from disk."""
        self._sys_prompts = self._load_prompts_from_dir(self.path_manager.get_sys_prompt_dir())
        self._user_templates = self._load_prompts_from_dir(self.path_manager.get_user_prompt_dir())

    def _load_prompts_from_dir(self, dir_path: str) -> Dict[str, str]:
        prompts = {}
        if not os.path.exists(dir_path):
            return prompts
        
        for root, _, files in os.walk(dir_path):
            for file in files:
                if file.endswith('.md'):
                    name = os.path.splitext(file)[0]
                    path = os.path.join(root, file)
                    try:
                        with open(path, 'r', encoding='utf-8') as f:
                            prompts[name] = f.read()
                    except Exception as e:
                        print(f"Error reading prompt {path}: {e}")
        return prompts

    def get_sys_prompt(self, name: str) -> str:
        if not self._sys_prompts:
            self.load_prompts()
        return self._sys_prompts.get(name, "")

    def get_user_template(self, name: str) -> str:
        if not self._user_templates:
            self.load_prompts()
        return self._user_templates.get(name, "")

    def build_user_prompt(self, template_name: str, mapping: Dict[str, str]) -> str:
        template = self.get_user_template(template_name)
        if not template:
            return ""
        
        result = template
        for key, value in mapping.items():
            result = result.replace(key, value)
        return result

    # --- App Data Management ---

    def _load_app_data(self):
        app_data_path = self.path_manager.get_app_data_file("app_data.json")
        if os.path.exists(app_data_path):
            try:
                with open(app_data_path, 'r', encoding='utf-8') as f:
                    self._app_data = json.load(f)
            except Exception as e:
                print(f"Error loading app data: {e}")
                self._app_data = {}

    def get_last_proj_path(self) -> str:
        return self._app_data.get("proj_root_dict", "")

    def save_last_proj_path(self, path: str):
        self._app_data["proj_root_dict"] = path
        self._save_app_data()

    def _save_app_data(self):
        app_data_path = self.path_manager.get_app_data_file("app_data.json")
        os.makedirs(os.path.dirname(app_data_path), exist_ok=True)
        try:
            with open(app_data_path, 'w', encoding='utf-8') as f:
                json.dump(self._app_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving app data: {e}")

