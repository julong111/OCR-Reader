# noise_removal_page.py
from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QCheckBox, QComboBox, QLabel, QGroupBox, QPushButton, QHBoxLayout, \
    QSpinBox

from core.parameters import ProcessingParameters
from view.slider_spinbox import SliderSpinBox


class NoiseRemovalPage(QWidget):
    
    parameters_changed = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setAlignment(Qt.AlignTop)

        # --- 形态学操作 ---
        morph_group = QGroupBox("形态学操作") # 保持分组和标题
        morph_layout = QVBoxLayout(morph_group)

        # 将启用开关和操作类型选择放在同一行
        op_selection_layout = QHBoxLayout()
        self.morph_checkbox = QCheckBox() # 无文字的独立开关
        self.morph_checkbox.setToolTip("启用/禁用形态学操作")
        op_selection_layout.addWidget(self.morph_checkbox)

        self.morph_op_combo = QComboBox()
        self.morph_op_combo.addItem("开运算 (去外部噪点)", 0)
        self.morph_op_combo.addItem("闭运算 (连通内部区域)", 1)
        self.morph_op_combo.currentIndexChanged.connect(
            lambda: self.parameters_changed.emit({'morph_op': self.morph_op_combo.currentData()})
        )
        op_selection_layout.addWidget(self.morph_op_combo)
        op_selection_layout.addStretch()
        morph_layout.addLayout(op_selection_layout)

        # 将参数控件分组，以便统一启用/禁用
        self.morph_params_widget = QWidget()
        params_layout = QVBoxLayout(self.morph_params_widget)
        params_layout.setContentsMargins(0, 0, 0, 0)
        self.morph_ksize_label = QLabel("内核大小:")
        params_layout.addWidget(self.morph_ksize_label)
        self.morph_ksize_control = SliderSpinBox(is_float=False)
        self.morph_ksize_control.setRange(1, 21)
        self.morph_ksize_control.slider.setSingleStep(2)
        self.morph_ksize_control.value_changed_finished.connect(
            lambda val: self.parameters_changed.emit({'morph_ksize': val}))
        params_layout.addWidget(self.morph_ksize_control)
        morph_layout.addWidget(self.morph_params_widget)

        main_layout.addWidget(morph_group)

        # --- 膨胀操作 ---
        dilate_group = QGroupBox("膨胀") # 保持分组和标题
        dilate_layout = QVBoxLayout(dilate_group)

        # 将启用开关和内核大小标签放在同一行
        top_layout = QHBoxLayout()
        self.dilate_checkbox = QCheckBox() # 无文字的独立开关
        self.dilate_checkbox.setToolTip("启用/禁用膨胀操作")
        top_layout.addWidget(self.dilate_checkbox)

        self.dilate_ksize_label = QLabel("内核大小:")
        top_layout.addWidget(self.dilate_ksize_label)
        top_layout.addStretch()
        dilate_layout.addLayout(top_layout)

        # 内核大小滑块保持在下方
        self.dilate_ksize_control = SliderSpinBox(is_float=False)
        self.dilate_ksize_control.setRange(1, 21)
        self.dilate_ksize_control.slider.setSingleStep(2)
        self.dilate_ksize_control.value_changed_finished.connect(
            lambda val: self.parameters_changed.emit({'dilate_ksize': val}))
        dilate_layout.addWidget(self.dilate_ksize_control)
        main_layout.addWidget(dilate_group)

        # --- 按尺寸过滤 ---
        area_filter_group = QGroupBox("按尺寸过滤")
        area_filter_group.setCheckable(True)
        area_filter_group.toggled.connect(lambda checked: self.parameters_changed.emit({'noise_removal': checked}))
        area_filter_layout = QVBoxLayout(area_filter_group)

        self.small_noise_label = QLabel("最小面积阈值 (像素):")
        area_filter_layout.addWidget(self.small_noise_label)
        self.small_noise_area_thresh_control = SliderSpinBox(is_float=True) #
        self.small_noise_area_thresh_control.set_float_precision(1)
        self.small_noise_area_thresh_control.setRange(0, 1000.0)
        self.small_noise_area_thresh_control.value_changed_finished.connect(
            lambda val: self.parameters_changed.emit({'small_noise_area_thresh': val}))
        area_filter_layout.addWidget(self.small_noise_area_thresh_control)

        self.large_noise_label = QLabel("最大面积阈值 (像素):")
        area_filter_layout.addWidget(self.large_noise_label)
        self.large_noise_area_thresh_control = SliderSpinBox(is_float=True)
        self.large_noise_area_thresh_control.set_float_precision(1)
        self.large_noise_area_thresh_control.setRange(0, 10000.0)
        self.large_noise_area_thresh_control.value_changed_finished.connect(
            lambda val: self.parameters_changed.emit({'large_noise_area_thresh': val}))
        area_filter_layout.addWidget(self.large_noise_area_thresh_control)
        main_layout.addWidget(area_filter_group)

        # --- 按形状过滤 ---
        shape_filter_group = QGroupBox("按形状过滤")
        shape_filter_layout = QVBoxLayout(shape_filter_group)

        # 长宽比
        self.aspect_ratio_checkbox = QCheckBox("按长宽比筛选")
        self.aspect_ratio_checkbox.toggled.connect(
            lambda checked: self.parameters_changed.emit({'filter_by_aspect_ratio': checked}))
        shape_filter_layout.addWidget(self.aspect_ratio_checkbox)

        self.min_aspect_label = QLabel("最小长宽比 (0-5):")
        shape_filter_layout.addWidget(self.min_aspect_label)
        self.min_aspect_control = SliderSpinBox(is_float=True)
        self.min_aspect_control.set_float_precision(3)
        self.min_aspect_control.setRange(0, 5.0)
        self.min_aspect_control.value_changed_finished.connect(
            lambda val: self.parameters_changed.emit({'min_aspect_ratio': val}))
        shape_filter_layout.addWidget(self.min_aspect_control)

        self.max_aspect_label = QLabel("最大长宽比 (0-5):")
        shape_filter_layout.addWidget(self.max_aspect_label)
        self.max_aspect_control = SliderSpinBox(is_float=True)
        self.max_aspect_control.set_float_precision(3)
        self.max_aspect_control.setRange(0, 5.0)
        self.max_aspect_control.value_changed_finished.connect(
            lambda val: self.parameters_changed.emit({'max_aspect_ratio': val}))
        shape_filter_layout.addWidget(self.max_aspect_control)

        # 凸性比
        self.convexity_checkbox = QCheckBox("按凸性比筛选")
        self.convexity_checkbox.toggled.connect(
            lambda checked: self.parameters_changed.emit({'filter_by_convexity': checked}))
        shape_filter_layout.addWidget(self.convexity_checkbox)

        self.min_convexity_label = QLabel("最小凸性比 (0.8-1.0):")
        shape_filter_layout.addWidget(self.min_convexity_label)
        self.min_convexity_control = SliderSpinBox(is_float=True)
        self.min_convexity_control.set_float_precision(3)
        self.min_convexity_control.setRange(0.800, 1.000)
        self.min_convexity_control.value_changed_finished.connect(
            lambda val: self.parameters_changed.emit({'min_convexity_ratio': val}))
        shape_filter_layout.addWidget(self.min_convexity_control)

        # 顶点数
        self.vertices_checkbox = QCheckBox("按顶点数筛选")
        self.vertices_checkbox.toggled.connect(
            lambda checked: self.parameters_changed.emit({'filter_by_vertices': checked}))
        shape_filter_layout.addWidget(self.vertices_checkbox)

        vertices_layout = QHBoxLayout()
        vertices_layout.addWidget(QLabel("最小顶点数:"))
        self.vertex_count_spinbox = QSpinBox()
        self.vertex_count_spinbox.setRange(3, 100)
        self.vertex_count_spinbox.valueChanged.connect(
            lambda val: self.parameters_changed.emit({'vertex_count': val}))
        vertices_layout.addWidget(self.vertex_count_spinbox)
        vertices_layout.addStretch()
        shape_filter_layout.addLayout(vertices_layout)

        main_layout.addWidget(shape_filter_group)

        # --- 重置按钮 ---
        self.reset_params_btn = QPushButton("恢复默认参数")
        main_layout.addWidget(self.reset_params_btn)

        self.groups = {
            'noise_removal': area_filter_group,
        }

        # Initialize UI with default parameters
        self.set_params(ProcessingParameters())
        # 连接信号
        self.morph_checkbox.toggled.connect(self._on_morph_toggled)
        self.dilate_checkbox.toggled.connect(self._on_dilate_toggled)

    def _on_morph_toggled(self, checked):
        # 控制UI显隐和参数更新
        self.morph_op_combo.setEnabled(checked)
        self.morph_params_widget.setEnabled(checked)
        self.parameters_changed.emit({'morph': checked})

    def _on_dilate_toggled(self, checked):
        # 控制UI显隐和参数更新
        self.dilate_ksize_label.setEnabled(checked)
        self.dilate_ksize_control.setEnabled(checked)
        self.parameters_changed.emit({'dilate': checked})


    def set_params(self, params: ProcessingParameters):
        
        self.morph_checkbox.setChecked(params.morph)
        self._on_morph_toggled(params.morph) # 确保UI状态正确初始化

        op_index = self.morph_op_combo.findData(params.morph_op)
        self.morph_op_combo.setCurrentIndex(op_index if op_index != -1 else 0)
        self.morph_ksize_control.setValue(params.morph_ksize)

        self.dilate_checkbox.setChecked(params.dilate)
        self.dilate_ksize_control.setValue(params.dilate_ksize)
        self._on_dilate_toggled(params.dilate) # 确保UI状态正确初始化

        self.groups['noise_removal'].setChecked(params.noise_removal)
        self.small_noise_area_thresh_control.setValue(params.small_noise_area_thresh)
        self.large_noise_area_thresh_control.setValue(params.large_noise_area_thresh)

        self.aspect_ratio_checkbox.setChecked(params.filter_by_aspect_ratio)
        self.min_aspect_control.setValue(params.min_aspect_ratio)
        self.max_aspect_control.setValue(params.max_aspect_ratio)

        self.convexity_checkbox.setChecked(params.filter_by_convexity)
        self.min_convexity_control.setValue(params.min_convexity_ratio)

        self.vertices_checkbox.setChecked(params.filter_by_vertices)
        self.vertex_count_spinbox.setValue(params.vertex_count)