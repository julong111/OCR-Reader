# src/core/image_data_store.py
import os

import cv2

from .parameters import ProcessingParameters
from .image_identifier import ImageIdentifier

STAGE_NAMES = [
    "stage1_redress",
    "stage2_binary",
    "stage3_noisefree",
    "stage4_final"
]


class ImageDataStore:
    

    def __init__(self, project_path, identifier: ImageIdentifier, ini_manager):
        self.project_path = project_path
        self.identifier = identifier
        self.ini_manager = ini_manager

    def load_params(self):
        
        param_file_path = self._get_param_path()
        return self.ini_manager.load_params(param_file_path)

    def save_params(self, params: ProcessingParameters):
        
        param_file_path = self._get_param_path(create_if_needed=True)
        if param_file_path:
            image_params, nav_params = params.to_dicts()
            self.ini_manager.save_params(param_file_path, image_params, nav_params)

    def load_stage_result(self, stage_index):
        
        stage_path = self._get_stage_result_path(stage_index)
        if stage_path and os.path.exists(stage_path):
            return cv2.imread(stage_path, cv2.IMREAD_UNCHANGED)
        return None

    def save_stage_result(self, stage_index, main_image_data, preview_image_data=None):
        
        base_path = self._get_base_path_for_stage(stage_index, create_if_needed=True)
        if not base_path:
            return

        main_image_path = f"{base_path}.png"
        try:
            cv2.imwrite(main_image_path, main_image_data)
        except Exception as e:
            print(f"无法保存阶段性文件 {main_image_path}: {e}")

        if preview_image_data is not None:
            preview_image_path = f"{base_path}_preview.png"
            try:
                cv2.imwrite(preview_image_path, preview_image_data)
            except Exception as e:
                print(f"无法保存预览文件 {preview_image_path}: {e}")

    def _get_param_path(self, create_if_needed=False):
        
        subfolder_path = self._get_data_subfolder(create_if_needed=create_if_needed)
        if not subfolder_path:
            return None

        if self.identifier.page > -1:
            param_filename = f"p{self.identifier.page + 1}_params.ini"
        else:
            param_filename = "params.ini"
        return os.path.join(subfolder_path, param_filename)

    def _get_data_subfolder(self, create_if_needed=False):
        
        base_name, _ = os.path.splitext(os.path.basename(self.identifier.path))
        subfolder_name = f"{base_name}.files"
        subfolder_path = os.path.join(self.project_path, subfolder_name)

        if create_if_needed and not os.path.exists(subfolder_path):
            os.makedirs(subfolder_path)
        return subfolder_path

    def _get_base_path_for_stage(self, stage_index, create_if_needed=False):
        
        subfolder_path = self._get_data_subfolder(create_if_needed=create_if_needed)
        if not subfolder_path or not (0 <= stage_index < len(STAGE_NAMES)):
            return None

        if self.identifier.page > -1:
            return os.path.join(subfolder_path, f"p{self.identifier.page + 1}_{STAGE_NAMES[stage_index]}")
        else:
            return os.path.join(subfolder_path, STAGE_NAMES[stage_index])

    def _get_stage_result_path(self, stage_index):
        
        base_path = self._get_base_path_for_stage(stage_index)
        return f"{base_path}.png" if base_path else None