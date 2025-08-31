# zoomable_label.py

from PyQt5.QtCore import Qt, pyqtSignal, QPoint, QRect, QRectF
from PyQt5.QtGui import QPainter, QPen, QColor, QPixmap, QPainterPath
from PyQt5.QtWidgets import QLabel

from .interaction_states import (InteractionState, IdleState, AngleCorrectionState, AreaSelectionState,
                                 PerspectiveCorrectionState, EditAreaState,
                                 InteractionMode)


class ZoomableLabel(QLabel):
    # 定义信号，当交互完成时发射
    angle_points_selected = pyqtSignal(QPoint, QPoint)
    area_selected = pyqtSignal(QRect)
    perspective_points_selected = pyqtSignal(list)
    area_edited = pyqtSignal(int, QRect)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setScaledContents(False)
        self.original_pixmap = None
        self.scale_factor = 1.0

        self.interaction_mode = InteractionMode.NONE
        self.current_state: InteractionState = IdleState(self)
        self.state_map = {
            InteractionMode.NONE: IdleState,
            InteractionMode.ANGLE_CORRECTION: AngleCorrectionState,
            InteractionMode.AREA_SELECTION: lambda lbl: AreaSelectionState(lbl, is_sample=False),
            InteractionMode.PERSPECTIVE_CORRECTION: PerspectiveCorrectionState,
            InteractionMode.SAMPLE_SELECTION: lambda lbl: AreaSelectionState(lbl, is_sample=True),
            InteractionMode.EDIT_AREA: EditAreaState,
        }

        self.setMouseTracking(True)  # 开启鼠标跟踪以实时绘制辅助线

        # 用于存储交互过程中的临时数据
        self._points = []

        # 用于绘制工作区
        self.work_areas = []
        self.selected_area_index = -1
        self.draw_overlay = False # 这个我没有动，只是为了diff格式正确
        self.standard_char_rect = None
        self.min_symbol_rect = None

        # 用于编辑工作区
        self._editing_area_index = -1
        self._drag_handle = None  # e.g., 'top-left', 'bottom', 'body'
        self._drag_start_pos = QPoint()

    def clear_interaction_points(self):
        # 清除在交互模式下已选择的点，并刷新显示。
        if self.interaction_mode != InteractionMode.NONE:
            self._points = []
            self.update()  # 触发重绘以清除辅助线

    def set_interaction_mode(self, mode: InteractionMode):
        # 设置当前的交互模式
        self.interaction_mode = mode
        self.current_state = self.state_map[mode](self)

        self._points = []  # 切换模式时清空所有临时点和矩形
        if mode != InteractionMode.EDIT_AREA:
            self._editing_area_index = -1
            self._drag_handle = None
            self.setCursor(Qt.ArrowCursor)
        self.update()  # 触发重绘，清除屏幕上的旧辅助线

    def _to_image_coords(self, pos: QPoint) -> QPoint:
        # 将控件内的点击坐标转换为原始图片的坐标
        if self.original_pixmap is None or self.scale_factor == 0:
            return pos
        return pos / self.scale_factor

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.current_state.mouse_press(event)
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        self.current_state.mouse_move(event)

    def mouseReleaseEvent(self, event):
        self.current_state.mouse_release(event)

    def paintEvent(self, event):
        super().paintEvent(event)

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.scale(self.scale_factor, self.scale_factor)

        self._paint_work_areas(painter)
        self._paint_sample_rects(painter)
        self.current_state.paint(painter)

    def set_pixmap(self, pixmap):
        self.original_pixmap = pixmap
        self.scale_factor = 1.0
        self.update_scaled_pixmap()

    def update_scaled_pixmap(self):
        if self.original_pixmap is None or self.original_pixmap.isNull():
            super().setPixmap(QPixmap())  # 传递一个空的QPixmap来清空标签
            return
        scaled_pixmap = self.original_pixmap.scaled(
            self.original_pixmap.size() * self.scale_factor,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )
        super().setPixmap(scaled_pixmap)
        self.resize(scaled_pixmap.size())

    def _get_handle_rects(self, area_index):
        if not (0 <= area_index < len(self.work_areas)):
            return {}

        rect = QRect(*self.work_areas[area_index])
        handle_size = max(4, 8 / self.scale_factor)
        half_handle = handle_size / 2

        return {
            'top-left': QRect(rect.left() - half_handle, rect.top() - half_handle, handle_size, handle_size),
            'top-right': QRect(rect.right() - half_handle, rect.top() - half_handle, handle_size, handle_size),
            'bottom-left': QRect(rect.left() - half_handle, rect.bottom() - half_handle, handle_size, handle_size),
            'bottom-right': QRect(rect.right() - half_handle, rect.bottom() - half_handle, handle_size, handle_size),
            'top': QRect(rect.center().x() - half_handle, rect.top() - half_handle, handle_size, handle_size),
            'bottom': QRect(rect.center().x() - half_handle, rect.bottom() - half_handle, handle_size, handle_size),
            'left': QRect(rect.left() - half_handle, rect.center().y() - half_handle, handle_size, handle_size),
            'right': QRect(rect.right() - half_handle, rect.center().y() - half_handle, handle_size, handle_size),
            'body': rect
        }

    def _get_handle_at(self, pos):
        if self._editing_area_index == -1:
            return None

        handle_rects = self._get_handle_rects(self._editing_area_index)
        # Check handles first, as they are on top
        for handle, h_rect in handle_rects.items():
            if handle != 'body' and h_rect.contains(pos):
                return handle
        # Check body last
        if handle_rects['body'].contains(pos):
            return 'body'
        return None

    def _update_edit_cursor(self, pos):
        if self.interaction_mode != InteractionMode.EDIT_AREA:
            self.setCursor(Qt.ArrowCursor)
            return

        handle = self._get_handle_at(pos)
        if handle in ['top-left', 'bottom-right']:
            self.setCursor(Qt.SizeFDiagCursor)
        elif handle in ['top-right', 'bottom-left']:
            self.setCursor(Qt.SizeBDiagCursor)
        elif handle in ['top', 'bottom']:
            self.setCursor(Qt.SizeVerCursor)
        elif handle in ['left', 'right']:
            self.setCursor(Qt.SizeHorCursor)
        elif handle == 'body':
            self.setCursor(Qt.SizeAllCursor)
        else:
            self.setCursor(Qt.ArrowCursor)

    def _perform_drag(self, pos):
        if not self._drag_handle or self._editing_area_index == -1:
            return

        delta = pos - self._drag_start_pos
        rect_coords = self.work_areas[self._editing_area_index]
        rect = QRect(*rect_coords)

        if self._drag_handle == 'body':
            rect.translate(delta)
        elif 'top' in self._drag_handle:
            rect.setTop(rect.top() + delta.y())
        elif 'bottom' in self._drag_handle:
            rect.setBottom(rect.bottom() + delta.y())

        if 'left' in self._drag_handle:
            rect.setLeft(rect.left() + delta.x())
        elif 'right' in self._drag_handle:
            rect.setRight(rect.right() + delta.x())

        self.work_areas[self._editing_area_index] = [rect.x(), rect.y(), rect.width(), rect.height()]
        self._drag_start_pos = pos  # Update start pos for next move event

    def _paint_work_areas(self, painter):
        # 绘制已确定的工作区域和蒙版
        if not self.work_areas:
            return

        # 绘制蒙版
        if self.draw_overlay:
            full_rect = self.original_pixmap.rect()
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(255, 0, 0, 80)) # 半透明红色

            # 使用 QPainterPath 来创建复杂的“挖洞”形状
            path = QPainterPath()
            path.addRect(QRectF(full_rect))
            for i, area_coords in enumerate(self.work_areas):
                rect = QRect(*area_coords)
                path.addRect(QRectF(rect))
            path.setFillRule(Qt.OddEvenFill) # 关键：设置填充规则以实现挖洞效果
            painter.drawPath(path)

        # 绘制工作区边框rect = QRect(*area_coords)
        for i, area_coords in enumerate(self.work_areas):
            rect = QRect(*area_coords)
            # 如果此区域是当前列表选中的区域，则高亮显示
            if i == self.selected_area_index:
                # 高亮选中的区域（蓝色）
                pen = QPen(QColor("blue"), max(2, 4 / self.scale_factor))
            else:
                # 普通区域（红色）
                pen = QPen(QColor("red"), max(1, 2 / self.scale_factor))

            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)
            painter.drawRect(rect)

    def _paint_sample_rects(self, painter):
        # 绘制标准字和最小符号的采样框
        pen = QPen(QColor(0, 255, 0), max(1, 2 / self.scale_factor), Qt.DashLine)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)

        if self.standard_char_rect:
            painter.drawRect(self.standard_char_rect)

        if self.min_symbol_rect:
            painter.drawRect(self.min_symbol_rect)