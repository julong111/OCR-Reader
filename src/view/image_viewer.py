# src/view/image_viewer.py
from PyQt5.QtCore import Qt, QPoint, QSize, QSignalBlocker
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea

from .custom_slider import CustomSlider
from .zoomable_label import ZoomableLabel


class ImageViewer(QWidget):
    

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()
        self._connect_signals()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.zoom_slider = CustomSlider(Qt.Horizontal)
        self.zoom_slider.setRange(10, 500)
        self.zoom_slider.setValue(100)
        main_layout.addWidget(self.zoom_slider)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(False)
        self.image_label = ZoomableLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.scroll_area.setWidget(self.image_label)

        scroll_container = QWidget()
        scroll_layout = QHBoxLayout(scroll_container)
        scroll_layout.setContentsMargins(0, 0, 0, 0)
        scroll_layout.setSpacing(0)

        self.h_pan_slider = CustomSlider(Qt.Horizontal)
        self.h_pan_slider.setRange(0, 0)
        self.v_pan_slider = CustomSlider(Qt.Vertical)
        self.v_pan_slider.setRange(0, 0)
        self.v_pan_slider.setInvertedAppearance(True)

        scroll_layout.addWidget(self.scroll_area, 1)
        scroll_layout.addWidget(self.v_pan_slider)
        main_layout.addWidget(scroll_container, 1)
        main_layout.addWidget(self.h_pan_slider)

    def _connect_signals(self):
        self.zoom_slider.valueChanged.connect(self._update_zoom)
        self.h_pan_slider.valueChanged.connect(self.scroll_area.horizontalScrollBar().setValue)
        self.v_pan_slider.valueChanged.connect(self.scroll_area.verticalScrollBar().setValue)
        self.scroll_area.horizontalScrollBar().valueChanged.connect(self.h_pan_slider.setValue)
        self.scroll_area.verticalScrollBar().valueChanged.connect(self.v_pan_slider.setValue)
        self.scroll_area.horizontalScrollBar().rangeChanged.connect(
            lambda min_val, max_val: self.h_pan_slider.setRange(min_val, max_val)
        )
        self.scroll_area.verticalScrollBar().rangeChanged.connect(
            lambda min_val, max_val: self.v_pan_slider.setRange(min_val, max_val)
        )

    def _update_zoom(self, value):
        scale_factor = value / 100.0
        self.image_label.scale_factor = scale_factor
        self.image_label.update_scaled_pixmap()

    def set_pixmap(self, pixmap):
        self.image_label.set_pixmap(pixmap)

    def fit_to_view(self):
        # 缩放图像以完全适应视口，根据需要放大或缩小。
        pixmap = self.image_label.original_pixmap
        if pixmap is None or pixmap.isNull():
            return

        image_size = pixmap.size()
        # 为滚动区域的边框进行微调，以防止不必要的滚动条出现。
        viewport_size = self.scroll_area.viewport().size() - QSize(2, 2)

        if image_size.isEmpty() or viewport_size.width() <= 2 or viewport_size.height() <= 2:
            target_scale = 1.0
        else:
            # 计算宽度和高度方向的缩放比例，取较小者以确保图像完整显示。
            w_scale = viewport_size.width() / image_size.width()
            h_scale = viewport_size.height() / image_size.height()
            target_scale = min(w_scale, h_scale)

        new_slider_value = int(target_scale * 100)
        # 临时阻塞信号，以防止在手动设置滑块和缩放比例时产生反馈循环。
        with QSignalBlocker(self.zoom_slider):
            clamped_value = max(self.zoom_slider.minimum(), min(new_slider_value, self.zoom_slider.maximum()))
            self.zoom_slider.setValue(clamped_value)

        # 直接应用计算出的精确缩放比例并更新图像。
        self.image_label.scale_factor = target_scale
        self.image_label.update_scaled_pixmap()

        # 将可能较小的图像在视口中居中显示。
        h_bar = self.scroll_area.horizontalScrollBar()
        v_bar = self.scroll_area.verticalScrollBar()
        h_bar.setValue((h_bar.maximum() + h_bar.minimum()) // 2)
        v_bar.setValue((v_bar.maximum() + v_bar.minimum()) // 2)

    def update_view_with_anchor(self):
        
        old_scale = self.image_label.scale_factor if self.image_label.scale_factor > 0 else 1.0
        viewport = self.scroll_area.viewport()
        h_scroll_val = self.scroll_area.horizontalScrollBar().value()
        v_scroll_val = self.scroll_area.verticalScrollBar().value()

        anchor_in_viewport = viewport.rect().center()
        anchor_in_image = (anchor_in_viewport + QPoint(h_scroll_val, v_scroll_val)) / old_scale

        # 图像内容已由调用者更新。此方法仅负责恢复滚动位置以保持视图居中。
        # 缩放比例在此过程中不应改变。
        current_scale = self.image_label.scale_factor
        new_anchor_in_widget = anchor_in_image * current_scale
        new_h_val = int(new_anchor_in_widget.x() - anchor_in_viewport.x())
        new_v_val = int(new_anchor_in_widget.y() - anchor_in_viewport.y())

        self.scroll_area.horizontalScrollBar().setValue(new_h_val)
        self.scroll_area.verticalScrollBar().setValue(new_v_val)