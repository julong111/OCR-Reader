# binarization_page.py
from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QComboBox, QLabel, QGroupBox, QCheckBox

from core.parameters import ProcessingParameters
from view.slider_spinbox import SliderSpinBox


class BinarizationPage(QWidget):
    
    parameters_changed = pyqtSignal(dict)  # 发送一个包含单个已更改参数的字典

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setAlignment(Qt.AlignTop)

        # --- 高斯模糊 ---
        blur_group = QGroupBox("高斯模糊 (预处理)")
        blur_layout = QVBoxLayout(blur_group)
        self.blur_ksize_label = QLabel("内核大小:")
        blur_layout.addWidget(self.blur_ksize_label)
        self.blur_ksize_control = SliderSpinBox(is_float=False)
        self.blur_ksize_control.setRange(1, 31)
        self.blur_ksize_control.slider.setSingleStep(2) # 保持步长为2
        self.blur_ksize_control.value_changed_finished.connect(
            lambda val: self.parameters_changed.emit({'blur_ksize': val}))
        blur_layout.addWidget(self.blur_ksize_control)
        main_layout.addWidget(blur_group)

        # --- 二值化方法 ---
        thresh_group = QGroupBox("二值化方法")
        thresh_layout = QVBoxLayout(thresh_group)

        self.thresh_method_combo = QComboBox()
        self.thresh_method_combo.addItem("全局阈值 (Global)", "global")
        self.thresh_method_combo.addItem("自适应阈值 (Adaptive)", "adaptive")
        self.thresh_method_combo.addItem("大津法 (Otsu)", "otsu")
        self.thresh_method_combo.currentIndexChanged.connect(self._on_thresh_method_changed)
        thresh_layout.addWidget(self.thresh_method_combo)

        # --- 全局阈值参数 ---
        self.global_params_widget = QWidget()
        global_layout = QVBoxLayout(self.global_params_widget)
        global_layout.setContentsMargins(0, 5, 0, 0)
        self.thresh_value_label = QLabel("阈值:")
        global_layout.addWidget(self.thresh_value_label)
        self.thresh_value_control = SliderSpinBox(is_float=False)
        self.thresh_value_control.setRange(0, 255)
        self.thresh_value_control.value_changed_finished.connect(
            lambda val: self.parameters_changed.emit({'thresh_value': val}))
        global_layout.addWidget(self.thresh_value_control)
        thresh_layout.addWidget(self.global_params_widget)

        # --- 自适应阈值参数 ---
        self.adaptive_params_widget = QWidget()
        adaptive_layout = QVBoxLayout(self.adaptive_params_widget)
        adaptive_layout.setContentsMargins(0, 5, 0, 0)

        self.thresh_blocksize_label = QLabel("块大小 (3-255):")
        adaptive_layout.addWidget(self.thresh_blocksize_label)
        self.thresh_blocksize_control = SliderSpinBox(is_float=False)
        self.thresh_blocksize_control.setRange(3, 255)
        self.thresh_blocksize_control.slider.setSingleStep(2)
        self.thresh_blocksize_control.value_changed_finished.connect(
            lambda val: self.parameters_changed.emit({'thresh_blocksize': val}))
        adaptive_layout.addWidget(self.thresh_blocksize_control)

        self.thresh_c_label = QLabel("常量 C:")
        adaptive_layout.addWidget(self.thresh_c_label)
        self.thresh_c_control = SliderSpinBox(is_float=False)
        self.thresh_c_control.setRange(0, 50)
        self.thresh_c_control.value_changed_finished.connect(
            lambda val: self.parameters_changed.emit({'thresh_c': val}))
        adaptive_layout.addWidget(self.thresh_c_control)
        thresh_layout.addWidget(self.adaptive_params_widget)
        main_layout.addWidget(thresh_group)

        # --- 智能噪点移除 ---
        noise_group = QGroupBox("智能小型噪点移除")
        noise_layout = QVBoxLayout(noise_group)

        self.preview_noise_checkbox = QCheckBox("预览将被移除的噪点")
        self.preview_noise_checkbox.setToolTip("开启后，小于“最小符号”的噪点将在预览图上用绿色框出。")
        self.preview_noise_checkbox.toggled.connect(
            lambda checked: self.parameters_changed.emit({'preview_small_noise': checked})
        )
        noise_layout.addWidget(self.preview_noise_checkbox)

        self.confirm_removal_checkbox = QCheckBox("确认移除小型噪点")
        self.confirm_removal_checkbox.setToolTip("开启后，将在本阶段的输出中移除预览到的小型噪点。")
        self.confirm_removal_checkbox.toggled.connect(
            lambda checked: self.parameters_changed.emit({'confirm_small_noise_removal': checked})
        )
        noise_layout.addWidget(self.confirm_removal_checkbox)

        main_layout.addWidget(noise_group)

        # --- 智能大型噪点移除 ---
        large_noise_group = QGroupBox("智能大型噪点移除")
        large_noise_layout = QVBoxLayout(large_noise_group)

        self.preview_large_noise_checkbox = QCheckBox("预览将被移除的大型噪点")
        self.preview_large_noise_checkbox.setToolTip("开启后，大于“标准字”的噪点将在预览图上用红色框出。")
        self.preview_large_noise_checkbox.toggled.connect(
            lambda checked: self.parameters_changed.emit({'preview_large_noise': checked})
        )
        large_noise_layout.addWidget(self.preview_large_noise_checkbox)

        self.confirm_large_noise_removal_checkbox = QCheckBox("确认移除大型噪点")
        self.confirm_large_noise_removal_checkbox.setToolTip("开启后，将在本阶段的输出中移除预览到的大型噪点。")
        self.confirm_large_noise_removal_checkbox.toggled.connect(
            lambda checked: self.parameters_changed.emit({'confirm_large_noise_removal': checked})
        )
        large_noise_layout.addWidget(self.confirm_large_noise_removal_checkbox)

        main_layout.addWidget(large_noise_group)

        # Initialize UI with default parameters
        self.set_params(ProcessingParameters())

    def _on_thresh_method_changed(self):
        method = self.thresh_method_combo.currentData()
        self.global_params_widget.setVisible(method == "global")
        self.adaptive_params_widget.setVisible(method == "adaptive")
        self.parameters_changed.emit({'thresh_method': method})

    def set_params(self, params: ProcessingParameters):

        blur_ksize = params.blur_ksize
        self.blur_ksize_control.setValue(blur_ksize)

        self.preview_noise_checkbox.setChecked(params.preview_small_noise)
        self.confirm_removal_checkbox.setChecked(params.confirm_small_noise_removal)

        self.preview_large_noise_checkbox.setChecked(params.preview_large_noise)
        self.confirm_large_noise_removal_checkbox.setChecked(params.confirm_large_noise_removal)

        method = params.thresh_method
        index = self.thresh_method_combo.findData(method)
        self.thresh_method_combo.setCurrentIndex(index if index != -1 else 0)

        # 根据方法显示/隐藏对应的参数面板
        self.global_params_widget.setVisible(method == "global")
        self.adaptive_params_widget.setVisible(method == "adaptive")

        # 设置全局阈值参数
        thresh_value = params.thresh_value
        self.thresh_value_control.setValue(thresh_value)

        # 设置自适应阈值参数
        block_size = params.thresh_blocksize
        self.thresh_blocksize_control.setValue(block_size)

        c_val = params.thresh_c
        self.thresh_c_control.setValue(c_val)

    def configure_for_image(self, image):
        
        if image is None:
            return
        h, w = image.shape[:2]
        max_blocksize = min(h, w) // 4 | 1
        if max_blocksize < 3: max_blocksize = 3
        self.thresh_blocksize_control.setRange(3, max_blocksize)
        self.thresh_blocksize_label.setText(f"块大小 (3-{max_blocksize}):")