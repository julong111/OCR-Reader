# src/core/app_context.py
import dataclasses
from typing import Union

from PyQt5.QtCore import QObject, pyqtSignal

from .parameters import ProcessingParameters
from .param_utils import serialize_rect_list
from .image_identifier import ImageIdentifier


class AppContext(QObject):
    # 应用程序的单一状态管理器 (Single Source of Truth).
    # 持有所有核心数据，如当前图像、处理参数和阶段。
    # 当状态改变时，通过信号通知UI更新。

    # --- Signals ---
    # 当需要加载新图像并更新UI时发出
    signal_appcontext_image_loaded = pyqtSignal()
    # 当图像处理完成，需要刷新显示时发出
    signal_appcontext_image_updated = pyqtSignal()
    # 在上下文（当前图片或阶段）即将改变时发出
    signal_appcontext_context_will_change = pyqtSignal()
    # 当处理阶段改变时发出
    signal_appcontext_stage_changed = pyqtSignal(int)
    # 当参数需要被应用到UI时发出
    signal_appcontext_params_applied_to_ui = pyqtSignal(ProcessingParameters)

    def __init__(self, project_manager, image_pipeline, is_debug=False, parent=None):
        super().__init__(parent)
        self.project_manager = project_manager
        self.image_pipeline = image_pipeline
        self.is_debug_mode = is_debug

        # --- State Variables ---
        self.current_image_identifier: Union[ImageIdentifier, None] = None
        self.current_image_index = -1
        self.params: ProcessingParameters = ProcessingParameters()
        self.original_image = None
        self.preview_image = None
        self.main_result_image = None
        self.current_stage_index = 0

    def set_current_image(self, index):
        # 加载指定索引的图像及其状态。
        if index < 0 or index >= len(self.project_manager.file_list):
            return

        self.signal_appcontext_context_will_change.emit()

        self.current_image_index = index
        self.current_image_identifier = self.project_manager.file_list[index]

        loaded_params_dict = self.project_manager.load_params_for_image(self.current_image_identifier)
        self.params = ProcessingParameters.from_dict(loaded_params_dict)
        self.current_stage_index = self.params.current_stage

        self.original_image = self.image_pipeline.opencv_ops.load_raw_image(self.current_image_identifier)
        if self.original_image is None:
            # Handle error case
            self.preview_image = None
            self.main_result_image = None

        self.signal_appcontext_params_applied_to_ui.emit(self.params)
        self.signal_appcontext_stage_changed.emit(self.current_stage_index)
        self.signal_appcontext_image_loaded.emit()
        # 关键修复：加载完新图片后，必须立即执行一次流水线处理
        self._execute_pipeline()

    def update_parameters(self, params_to_update: dict):
        # Updates image parameters, saves them, and then triggers the processing pipeline.
        # 规范化传入的参数key为小写，防止因大小写问题导致重复键
        normalized_params = {k.lower(): v for k, v in params_to_update.items()}
        cls_fields = {f.name: f.type for f in dataclasses.fields(self.params)}

        for key, value in normalized_params.items():
            if key in cls_fields:
                expected_type = cls_fields[key]
                try:
                    # 强制将传入的值转换为数据类中定义的类型
                    converted_value = expected_type(value)
                    setattr(self.params, key, converted_value)
                except (ValueError, TypeError):
                    print(f"Warning: Could not convert UI value '{value}' for key '{key}' to {expected_type}.")

        # 每次更新都完整保存所有参数，确保原子性和一致性
        if self.current_image_identifier:
            self.project_manager.save_parameters(self.current_image_identifier, self.params)

        self._execute_pipeline()

    def reset_parameters(self):
        # Resets parameters to their default values.
        self.params = ProcessingParameters()
        if self.current_image_identifier:
            self.project_manager.save_parameters(self.current_image_identifier, self.params)
        self._execute_pipeline()

    def set_stage(self, new_index):
        # 切换处理阶段，只保存导航状态，然后触发流水线。
        if not (0 <= new_index < 4):  # Assuming 4 stages
            return

        self.signal_appcontext_context_will_change.emit()

        self.current_stage_index = new_index
        self.params.current_stage = new_index
        if self.current_image_identifier:
            self.project_manager.save_parameters(self.current_image_identifier, self.params)

        self.signal_appcontext_stage_changed.emit(self.current_stage_index)
        self._execute_pipeline()

    def _execute_pipeline(self):
        # The core logic for processing the image based on the current state.
        # This should be the single entry point for any image refresh.
        if self.original_image is None:
            return

        # 确定当前阶段应该使用哪个图像作为输入
        if self.current_stage_index == 0:
            input_image = self.original_image
        else:
            input_image = self.project_manager.load_stage_result(self.current_image_identifier, self.current_stage_index - 1)
            if input_image is None:
                # Fallback: if a previous stage result is missing, re-process from original.
                # This is a simple recovery, a more robust solution might re-run the entire pipeline.
                input_image = self.original_image

        debug_info = None
        if self.is_debug_mode:
            debug_info = {
                "project_path": self.project_manager.project_path,
                "identifier": self.current_image_identifier
            }

        preview, main_result, crop_rect, relative_areas, rel_std_char, _ = self.image_pipeline.process(
            input_image, self.current_stage_index, self.params, debug_info=debug_info
        )
        self.preview_image = preview
        self.main_result_image = main_result

        params_changed = False
        if self.current_stage_index == 0:
            new_crop_rect_str = serialize_rect_list([crop_rect]) if crop_rect else ""
            if self.params.work_area_crop_rect != new_crop_rect_str:
                self.params.work_area_crop_rect = new_crop_rect_str
                params_changed = True

            new_relative_areas_str = serialize_rect_list(relative_areas) if relative_areas else ""
            if self.params.relative_work_areas != new_relative_areas_str:
                self.params.relative_work_areas = new_relative_areas_str
                params_changed = True
            
            new_rel_std_char_str = serialize_rect_list(rel_std_char) if rel_std_char else ""
            if self.params.relative_standard_char_rect != new_rel_std_char_str:
                self.params.relative_standard_char_rect = new_rel_std_char_str
                params_changed = True

        # After processing, immediately save the results for this stage.
        if self.main_result_image is not None:
            self._save_stage_results()

        if params_changed and self.current_image_identifier:
            self.project_manager.save_parameters(self.current_image_identifier, self.params)

        self.signal_appcontext_image_updated.emit()
        self.signal_appcontext_params_applied_to_ui.emit(self.params)

    def _save_stage_results(self):
        # Saves the result images for the current stage.
        main_to_save = self.main_result_image
        preview_to_save = self.preview_image

        # For stages where preview and main are the same, we don't need to save a separate preview file.
        if main_to_save is preview_to_save:
            preview_to_save = None

        self.project_manager.save_stage_result(
            self.current_image_identifier,
            self.current_stage_index,
            main_to_save,
            preview_to_save
        )
