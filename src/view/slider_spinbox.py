# src/view/slider_spinbox.py

from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtWidgets import QWidget, QHBoxLayout

from .custom_slider import CustomSlider
from .smart_spinbox import SmartDoubleSpinBox, SmartSpinBox


class SliderSpinBox(QWidget):
    

    # 当用户完成交互（释放滑块或完成输入）时，发射此信号
    value_changed_finished = pyqtSignal(float)  # 使用float以兼容整数和浮点数

    def __init__(self, is_float=False, parent=None):
        super().__init__(parent)
        self._is_float = is_float
        # 根据是否为浮点数，设置滑块内部的乘数以处理精度
        self._slider_multiplier = 1.0

        self._init_ui()
        self._connect_signals()

    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self.slider = CustomSlider(Qt.Horizontal)

        if self._is_float:
            self.spinbox = SmartDoubleSpinBox()
            self.set_float_precision(2)  # 默认两位小数
        else:
            self.spinbox = SmartSpinBox()

        self.spinbox.setFixedWidth(70)  # 给输入框一个合适的固定宽度

        layout.addWidget(self.slider)
        layout.addWidget(self.spinbox)

    def _connect_signals(self):
        # 当滑块移动时，更新输入框的数字
        self.slider.valueChanged.connect(self._update_spinbox_from_slider)
        # 当输入框数字改变时，更新滑块的位置
        self.spinbox.valueChanged.connect(self._update_slider_from_spinbox)

        # 仅在交互结束时，才发射最终的信号
        self.slider.sliderReleased.connect(self._emit_final_value)
        self.spinbox.editingFinished.connect(self._emit_final_value)
        self.spinbox.step_triggered.connect(self._emit_final_value)

    def _update_spinbox_from_slider(self, slider_value):
        # 临时阻塞信号，防止无限循环
        blocked = self.spinbox.blockSignals(True)
        try:
            value = slider_value / self._slider_multiplier if self._is_float else slider_value
            self.spinbox.setValue(value)
        finally:
            self.spinbox.blockSignals(blocked)

    def _update_slider_from_spinbox(self, spinbox_value):
        # 临时阻塞信号，防止无限循环
        blocked = self.slider.blockSignals(True)
        try:
            value = int(spinbox_value * self._slider_multiplier) if self._is_float else int(spinbox_value)
            self.slider.setValue(value)
        finally:
            self.slider.blockSignals(blocked)

    def _emit_final_value(self):
        self.value_changed_finished.emit(self.value())

    # --- 公共API，用于从外部配置此控件 ---

    def set_float_precision(self, decimals: int):
        if not self._is_float: return
        self.spinbox.setDecimals(decimals)
        self._slider_multiplier = 10.0 ** decimals

    def setRange(self, min_val, max_val):
        self.spinbox.setRange(min_val, max_val)
        slider_min = int(min_val * self._slider_multiplier) if self._is_float else min_val
        slider_max = int(max_val * self._slider_multiplier) if self._is_float else max_val
        self.slider.setRange(slider_min, slider_max)

        # 智能设置步进
        step = (max_val - min_val) / 100.0
        self.spinbox.setSingleStep(step if self._is_float else max(1, round(step)))

    def setValue(self, value):
        self.spinbox.setValue(value)

    def value(self):
        return self.spinbox.value()
