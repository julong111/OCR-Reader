# ini_manager.py
import configparser
import os


class IniManager:

    def load_params(self, file_path):

        config = configparser.ConfigParser()
        if not file_path or not os.path.exists(file_path):
            return {}

        config.read(file_path, encoding='utf-8')

        all_params = {}
        for section in config.sections():
            for key, value in config.items(section):
                all_params[key] = value # Keep it as a string
        return all_params

    def save_params(self, file_path, image_params, nav_params, system_params=None):

        if not file_path:
            return

        config = configparser.ConfigParser()
        config['system'] = {k: str(v) for k, v in (system_params or {}).items()}
        config['nav'] = {k: str(v) for k, v in nav_params.items()}
        config['image'] = {k: str(v) for k, v in image_params.items()}

        try:
            with open(file_path, 'w', encoding='utf-8') as configfile:
                config.write(configfile)
        except Exception as e:
            print(f"Error: Could not save parameter file {file_path}: {e}")
