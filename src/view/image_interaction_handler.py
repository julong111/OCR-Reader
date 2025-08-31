# src/view/image_interaction_handler.py
import math

from PyQt5.QtCore import QObject, pyqtSignal, QRect, Qt
from PyQt5.QtWidgets import QMessageBox

from core.param_utils import serialize_rect_list, deserialize_rect_list, serialize_point_list, deserialize_point_list
from .interaction_states import InteractionMode


class ImageInteractionHandler(QObject):
    
    # Signal to notify the UI that an interaction has changed the state
    # and a visual update might be needed.
    signal_imageinteractionhandler_overlay_needs_update = pyqtSignal() # 叠加层需要更新信号（交互中）
    signal_imageinteractionhandler_interaction_ended = pyqtSignal() # 交互结束信号（交互结束）

    def __init__(self, image_label, app_context, parent=None):
        super().__init__(parent)
        self.image_label = image_label
        self.app_context = app_context
        self._is_editing_work_area = False

    def start_angle_correction(self):
        
        self.image_label.set_interaction_mode(InteractionMode.ANGLE_CORRECTION)
        try:
            self.image_label.angle_points_selected.disconnect()
        except TypeError:
            pass
        self.image_label.angle_points_selected.connect(self._handle_angle_points_selected)

    def start_perspective_correction(self):
        
        self.image_label.set_interaction_mode(InteractionMode.PERSPECTIVE_CORRECTION)
        try:
            self.image_label.perspective_points_selected.disconnect()
        except TypeError:
            pass
        self.image_label.perspective_points_selected.connect(self._handle_perspective_points_selected)

    def start_area_selection(self):
        
        self.image_label.set_interaction_mode(InteractionMode.AREA_SELECTION)
        try:
            self.image_label.area_selected.disconnect()
        except TypeError:
            pass
        self.image_label.area_selected.connect(self._handle_area_selected)

    def start_area_editing(self, index):
        
        self.image_label._editing_area_index = index
        self.image_label.set_interaction_mode(InteractionMode.EDIT_AREA)
        try:
            self.image_label.area_edited.disconnect()
        except TypeError:
            pass
        self.image_label.area_edited.connect(self._handle_area_edited)
        self.image_label.update()

    def start_standard_char_selection(self):
        
        self.image_label.set_interaction_mode(InteractionMode.SAMPLE_SELECTION)
        try:
            self.image_label.area_selected.disconnect()
        except TypeError:
            pass
        self.image_label.area_selected.connect(self._handle_standard_char_selected)

    def start_min_symbol_selection(self):
        
        self.image_label.set_interaction_mode(InteractionMode.SAMPLE_SELECTION)
        try:
            self.image_label.area_selected.disconnect()
        except TypeError:
            pass
        self.image_label.area_selected.connect(self._handle_min_symbol_selected)
    
    def cancel_current_interaction(self):
        
        was_interacting = self.image_label.interaction_mode != InteractionMode.NONE

        # If we were in edit mode, commit the pending changes.
        if self.image_label.interaction_mode == InteractionMode.EDIT_AREA:
            self._commit_work_area_changes()

        if was_interacting:
            # Reset to idle state. This will also clear any temporary points/lines.
            self.image_label.set_interaction_mode(InteractionMode.NONE)
            self.signal_imageinteractionhandler_interaction_ended.emit() # 只广播交互已彻底结束

        return was_interacting

    def handle_key_press(self, key):
        
        if key == Qt.Key_Escape:
            return self.cancel_current_interaction()
        return False

    def _commit_work_area_changes(self):
        
        if self._is_editing_work_area:
            self._is_editing_work_area = False
            # The parameter is already updated in memory.
            # We just need to save it and trigger the pipeline.
            self.app_context.update_parameters({'work_areas': self.app_context.params.work_areas})

    def _is_rect_in_work_areas(self, rect_to_check: QRect) -> bool:
        # Checks if the given rectangle is fully contained within any of the defined work areas.
        work_areas_str = self.app_context.params.work_areas
        if not work_areas_str:
            return False

        work_areas = deserialize_rect_list(work_areas_str)
        if not work_areas:
            return False

        for area in work_areas:
            # 使用QRect的contains方法可以方便地检查包含关系
            work_area_qrect = QRect(*area)
            if work_area_qrect.contains(rect_to_check):
                return True

        return False

    # --- Private Handlers ---
    def _handle_area_selected(self, rect: QRect):
        work_areas_str = self.app_context.params.work_areas
        work_areas = deserialize_rect_list(work_areas_str)
        work_areas.append([rect.x(), rect.y(), rect.width(), rect.height()])
        self.app_context.update_parameters({'work_areas': serialize_rect_list(work_areas)})

    def _handle_area_edited(self, index, new_rect):
        self._is_editing_work_area = True
        work_areas_str = self.app_context.params.work_areas
        work_areas = deserialize_rect_list(work_areas_str)
        if 0 <= index < len(work_areas):
            work_areas[index] = [new_rect.x(), new_rect.y(), new_rect.width(), new_rect.height()]
            self.app_context.params.work_areas = serialize_rect_list(work_areas)
            self.signal_imageinteractionhandler_overlay_needs_update.emit()

    def _handle_angle_points_selected(self, p1, p2):
        try:
            self.image_label.angle_points_selected.disconnect()
        except TypeError:
            pass

        delta_x = p2.x() - p1.x()
        delta_y = p2.y() - p1.y()
        angle_rad = math.atan2(delta_y, delta_x)
        angle_deg = math.degrees(angle_rad)

        current_angle = self.app_context.params.rotation_angle
        new_total_angle = current_angle + angle_deg
        self.app_context.update_parameters({'rotation_angle': new_total_angle})

    def _handle_perspective_points_selected(self, points):
        try:
            self.image_label.perspective_points_selected.disconnect()
        except TypeError:
            pass

        points_as_list = [[p.x(), p.y()] for p in points]
        self.app_context.update_parameters({
            'perspective_points': serialize_point_list(points_as_list),
            'rotation_angle': 0.0
        })

    def _handle_standard_char_selected(self, rect: QRect):
        if not self._is_rect_in_work_areas(rect):
            QMessageBox.warning(
                None,
                "无效选择",
                "选择的“标准字”区域必须完全位于一个已定义的工作区内。"
            )
            return

        char_height = rect.height()
        char_area = rect.width() * rect.height()
        if char_height <= 0 or char_area <= 0 or self.app_context.original_image is None:
            return

        h, w = self.app_context.original_image.shape[:2]
        max_blocksize = min(h, w) // 4 | 1
        new_blocksize = char_height | 1

        new_large_noise_area_thresh = char_area * 1.5
        new_ksize = max(3, int(char_height * 0.5) | 1)

        self.app_context.update_parameters({
            'sample_char_height': char_height,
            'thresh_blocksize': new_blocksize,
            'preview_large_noise': True,
            'confirm_large_noise_removal': True,
            'large_noise_area_thresh': new_large_noise_area_thresh,
            'large_noise_morph_ksize': new_ksize,
            'standard_char_rect': serialize_rect_list([[rect.x(), rect.y(), rect.width(), rect.height()]])
        })

    def _handle_min_symbol_selected(self, rect: QRect):
        if not self._is_rect_in_work_areas(rect):
            QMessageBox.warning(
                None,
                "无效选择",
                "选择的“最小符号”区域必须完全位于一个已定义的工作区内。"
            )
            return

        symbol_height = rect.height()
        symbol_area = rect.width() * rect.height()
        if symbol_height <= 0 or symbol_area <= 0 or self.app_context.original_image is None:
            return

        new_small_noise_area_thresh = symbol_area * 0.8

        self.app_context.update_parameters({
            'min_symbol_height': symbol_height,
            'small_noise_area_thresh': new_small_noise_area_thresh,
            'min_symbol_rect': serialize_rect_list([[rect.x(), rect.y(), rect.width(), rect.height()]]),
            'preview_small_noise': True,
            'confirm_small_noise_removal': True
        })
