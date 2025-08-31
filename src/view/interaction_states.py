# src/view/interaction_states.py
import enum

from PyQt5.QtCore import Qt, QRect
from PyQt5.QtGui import QPen, QColor


class InteractionMode(enum.Enum):
    
    NONE = 0
    ANGLE_CORRECTION = 1
    AREA_SELECTION = 2
    PERSPECTIVE_CORRECTION = 3
    SAMPLE_SELECTION = 4
    EDIT_AREA = 5


class InteractionState:
    

    def __init__(self, label):
        self.label = label

    def mouse_press(self, event):
        pass

    def mouse_move(self, event):
        pass

    def mouse_release(self, event):
        pass

    def paint(self, painter):
        pass

    def _get_scaled_pen_width(self):
        return max(1, 2 / self.label.scale_factor)

    def _get_scaled_point_radius(self):
        return max(2, 5 / self.label.scale_factor)


class IdleState(InteractionState):
    
    pass


class AngleCorrectionState(InteractionState):
    

    def mouse_press(self, event):
        image_pos = self.label._to_image_coords(event.pos())
        self.label._points.append(image_pos)
        if len(self.label._points) == 2:
            self.label.angle_points_selected.emit(self.label._points[0], self.label._points[1])
            self.label.set_interaction_mode(InteractionMode.NONE)
        self.label.update()

    def mouse_move(self, event):
        if len(self.label._points) == 1:
            self.label.update()

    def paint(self, painter):
        painter.setPen(QPen(QColor("red"), self._get_scaled_pen_width()))
        for point in self.label._points:
            painter.drawEllipse(point, self._get_scaled_point_radius(), self._get_scaled_point_radius())
        if len(self.label._points) == 1:
            cursor_pos = self.label._to_image_coords(self.label.mapFromGlobal(self.label.cursor().pos()))
            painter.drawLine(self.label._points[0], cursor_pos)


class PerspectiveCorrectionState(InteractionState):
    

    def mouse_press(self, event):
        image_pos = self.label._to_image_coords(event.pos())
        self.label._points.append(image_pos)
        if len(self.label._points) == 4:
            self.label.perspective_points_selected.emit(self.label._points)
            self.label.set_interaction_mode(InteractionMode.NONE)
        self.label.update()

    def mouse_move(self, event):
        if 0 < len(self.label._points) < 4:
            self.label.update()

    def paint(self, painter):
        painter.setPen(QPen(QColor("red"), self._get_scaled_pen_width()))
        for point in self.label._points:
            painter.drawEllipse(point, self._get_scaled_point_radius(), self._get_scaled_point_radius())
        if len(self.label._points) > 1:
            for i in range(len(self.label._points) - 1):
                painter.drawLine(self.label._points[i], self.label._points[i + 1])
        if len(self.label._points) == 4:
            painter.drawLine(self.label._points[3], self.label._points[0])
        if 0 < len(self.label._points) < 4:
            cursor_pos = self.label._to_image_coords(self.label.mapFromGlobal(self.label.cursor().pos()))
            painter.drawLine(self.label._points[-1], cursor_pos)


class AreaSelectionState(InteractionState):
    

    def __init__(self, label, is_sample=False):
        super().__init__(label)
        self.is_sample = is_sample

    def mouse_press(self, event):
        image_pos = self.label._to_image_coords(event.pos())
        self.label._points.append(image_pos)
        if len(self.label._points) == 2:
            rect = QRect(self.label._points[0], self.label._points[1]).normalized()
            self.label.area_selected.emit(rect)
            self.label.set_interaction_mode(InteractionMode.NONE)
        self.label.update()

    def mouse_move(self, event):
        if len(self.label._points) == 1:
            self.label.update()

    def paint(self, painter):
        if self.is_sample:
            pen = QPen(QColor("green"), self._get_scaled_pen_width(), Qt.DashLine)
        else:
            pen = QPen(QColor("red"), self._get_scaled_pen_width(), Qt.DashLine)

        painter.setPen(pen)
        if len(self.label._points) == 1:
            cursor_pos = self.label._to_image_coords(self.label.mapFromGlobal(self.label.cursor().pos()))
            painter.drawRect(QRect(self.label._points[0], cursor_pos))


class EditAreaState(InteractionState):
    

    def mouse_press(self, event):
        if self.label._editing_area_index != -1:
            image_pos = self.label._to_image_coords(event.pos())
            handle = self.label._get_handle_at(image_pos)
            if handle:
                self.label._drag_handle = handle
                self.label._drag_start_pos = image_pos
                self.label.update()

    def mouse_move(self, event):
        self.label._update_edit_cursor(self.label._to_image_coords(event.pos()))
        if self.label._drag_handle:
            self.label._perform_drag(self.label._to_image_coords(event.pos()))
            self.label.update()

    def mouse_release(self, event):
        if self.label._drag_handle:
            self.label.area_edited.emit(self.label._editing_area_index, QRect(*self.label.work_areas[self.label._editing_area_index]))
            self.label._drag_handle = None
            self.label.update()

    def paint(self, painter):
        if not (0 <= self.label._editing_area_index < len(self.label.work_areas)):
            return

        handle_rects = self.label._get_handle_rects(self.label._editing_area_index)
        painter.setBrush(QColor("blue"))
        painter.setPen(Qt.NoPen)
        for handle, h_rect in handle_rects.items():
            if handle != 'body':
                painter.drawRect(h_rect)