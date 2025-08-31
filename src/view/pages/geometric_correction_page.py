# geometric_correction_page.py
from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QPushButton, QGroupBox, QHBoxLayout, QListWidget, QAbstractItemView, \
    QLabel, QMessageBox

from core.param_utils import deserialize_rect_list
from core.parameters import ProcessingParameters


class GeometricCorrectionPage(QWidget):
    
    # 定义信号，通知主窗口用户希望执行什么操作
    signal_geometriccorrectionpage_angle_correction_requested = pyqtSignal() # 角度校正信号
    signal_geometriccorrectionpage_angle_reset_requested = pyqtSignal() # 角度重置信号

    signal_geometriccorrectionpage_area_selection_requested = pyqtSignal() # 工作区选择信号
    signal_geometriccorrectionpage_area_selection_changed = pyqtSignal() # ？
    signal_geometriccorrectionpage_area_edit_requested = pyqtSignal(int) # 编辑工作区信号
    signal_geometriccorrectionpage_work_area_deleted = pyqtSignal(int)  # 删除工作区信号

    signal_geometriccorrectionpage_perspective_correction_requested = pyqtSignal()
    signal_geometriccorrectionpage_perspective_reset_requested = pyqtSignal()

    signal_geometriccorrectionpage_standard_char_requested = pyqtSignal() # 标准字符信号
    signal_geometriccorrectionpage_min_symbol_requested = pyqtSignal() # 最小字符信号


    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setAlignment(Qt.AlignTop)

        # --- 校正工具组 ---
        tools_group = QGroupBox("校正工具")
        tools_layout = QVBoxLayout(tools_group)

        # --- 透视校正 ---
        perspective_layout = QHBoxLayout()
        self.perspective_correction_btn = QPushButton("透视校正 (选择四点)")
        self.perspective_correction_btn.setToolTip("点击后，在图片上依次点击书页的四个角点，以校正透视形变。")
        self.perspective_correction_btn.clicked.connect(self.signal_geometriccorrectionpage_perspective_correction_requested)
        perspective_layout.addWidget(self.perspective_correction_btn)

        self.reset_perspective_btn = QPushButton("重置透视")
        self.reset_perspective_btn.clicked.connect(self.signal_geometriccorrectionpage_perspective_reset_requested)
        perspective_layout.addWidget(self.reset_perspective_btn)
        tools_layout.addLayout(perspective_layout)

        self.perspective_label = QLabel("透视校正: 未应用")
        tools_layout.addWidget(self.perspective_label)

        # --- 角度校正 ---
        angle_layout = QHBoxLayout()
        self.angle_correction_btn = QPushButton("角度校正 (选择两点)")
        self.angle_correction_btn.setToolTip("点击后，在图片上依次点击一行文字的头和尾，以自动校正旋转角度。")
        self.angle_correction_btn.clicked.connect(self.signal_geometriccorrectionpage_angle_correction_requested)
        angle_layout.addWidget(self.angle_correction_btn)

        self.reset_angle_btn = QPushButton("重置角度")
        self.reset_angle_btn.clicked.connect(self.signal_geometriccorrectionpage_angle_reset_requested)
        angle_layout.addWidget(self.reset_angle_btn)
        tools_layout.addLayout(angle_layout)

        self.angle_label = QLabel("当前角度: 0.00°")
        tools_layout.addWidget(self.angle_label)

        main_layout.addWidget(tools_group)

        # --- 工作区域组 ---
        area_group = QGroupBox("工作区域")
        area_layout = QVBoxLayout(area_group)

        self.area_selection_btn = QPushButton("添加新区域")
        self.area_selection_btn.setToolTip("点击后，在图片上依次点击矩形的左上角和右下角来选择一个工作区。")
        self.area_selection_btn.clicked.connect(self.signal_geometriccorrectionpage_area_selection_requested)
        area_layout.addWidget(self.area_selection_btn)

        self.edit_area_btn = QPushButton("编辑选中区域")
        self.edit_area_btn.setToolTip("在下方列表中选中一个区域，然后点击此按钮进入编辑模式。")
        self.edit_area_btn.clicked.connect(self._on_edit_area)
        area_layout.addWidget(self.edit_area_btn)

        self.delete_area_btn = QPushButton("删除选中区域")
        self.delete_area_btn.setToolTip("在下方列表中选中一个区域，然后点击此按钮删除。")
        self.delete_area_btn.clicked.connect(self._on_delete_area)
        area_layout.addWidget(self.delete_area_btn)

        area_list_layout = QHBoxLayout()
        self.work_areas_list = QListWidget()
        self.work_areas_list.setToolTip("当前已选择的工作区域列表。")
        self.work_areas_list.setMaximumHeight(60)
        self.work_areas_list.setSelectionMode(QAbstractItemView.SingleSelection)
        self.work_areas_list.currentRowChanged.connect(self.signal_geometriccorrectionpage_area_selection_changed)
        area_list_layout.addWidget(self.work_areas_list)

        area_layout.addLayout(area_list_layout)
        main_layout.addWidget(area_group)

        # --- 智能参数设置 ---
        smart_params_group = QGroupBox("智能参数设置")
        smart_params_layout = QVBoxLayout(smart_params_group)

        self.select_char_btn = QPushButton("框选标准字")
        self.select_char_btn.setToolTip("框选一个标准大小的文字，程序将据此自动设置相关参数。")
        self.select_char_btn.clicked.connect(self.signal_geometriccorrectionpage_standard_char_requested)
        smart_params_layout.addWidget(self.select_char_btn)
        self.standard_char_label = QLabel("标准字高: N/A")
        smart_params_layout.addWidget(self.standard_char_label)

        self.select_symbol_btn = QPushButton("框选最小符号")
        self.select_symbol_btn.setToolTip("框选一个最小的有效符号（如句号），程序将据此自动设置相关参数。")
        self.select_symbol_btn.clicked.connect(self.signal_geometriccorrectionpage_min_symbol_requested)
        smart_params_layout.addWidget(self.select_symbol_btn)
        self.min_symbol_label = QLabel("最小符号高: N/A")
        smart_params_layout.addWidget(self.min_symbol_label)

        main_layout.addWidget(smart_params_group)

        # 添加一个弹簧，吸收所有多余的垂直空间，使所有控件都紧凑地排列在顶部
        main_layout.addStretch(1)

    def _on_edit_area(self):
        current_row = self.work_areas_list.currentRow()
        if current_row >= 0:
            self.signal_geometriccorrectionpage_area_edit_requested.emit(current_row)
        else:
            QMessageBox.warning(self, "提示", "请先在列表中选择一个要编辑的区域。")

    def _on_delete_area(self):
        selected_items = self.work_areas_list.selectedItems()
        if not selected_items:
            return
        current_row = self.work_areas_list.row(selected_items[0])
        self.signal_geometriccorrectionpage_work_area_deleted.emit(current_row)

    def clear_work_area_selection(self):
        
        # 将当前行设置为-1会同时清除选中和焦点，并自动触发 currentRowChanged 信号
        self.work_areas_list.setCurrentRow(-1)

    def set_params(self, params: ProcessingParameters):
        
        self.work_areas_list.clear()
        # 更新角度显示
        angle = params.rotation_angle
        self.angle_label.setText(f"当前角度: {angle:.2f}°")

        # 更新透视校正状态显示
        if params.perspective_points:
            self.perspective_label.setText("透视校正: 已应用")
        else:
            self.perspective_label.setText("透视校正: 未应用")

        # 更新智能参数显示
        self.standard_char_label.setText(f"标准字高: {params.sample_char_height} px" if params.sample_char_height > 0 else "标准字高: N/A")
        self.min_symbol_label.setText(f"最小符号高: {params.min_symbol_height} px" if params.min_symbol_height > 0 else "最小符号高: N/A")

        # 'work_areas' 是我们将来在参数文件中存储区域信息的键
        work_areas_str = params.work_areas
        if work_areas_str:
            work_areas = deserialize_rect_list(work_areas_str)
            for i, area in enumerate(work_areas):
                self.work_areas_list.addItem(f"区域 {i + 1}: x={area[0]}, y={area[1]}, w={area[2]}, h={area[3]}")
