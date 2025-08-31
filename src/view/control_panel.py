
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QListWidget,
    QStackedWidget, QScrollArea, QGridLayout
)

from core.image_identifier import ImageIdentifier
from .pages.binarization_page import BinarizationPage
from .pages.geometric_correction_page import GeometricCorrectionPage
from .pages.noise_removal_page import NoiseRemovalPage
from .pages.ocr_export_page import OcrExportPage


class ControlPanel(QWidget):
    
    # Project signals
    signal_controlpanel_new_project_requested = pyqtSignal()
    signal_controlpanel_open_project_requested = pyqtSignal()
    signal_controlpanel_import_images_requested = pyqtSignal()
    signal_controlpanel_show_comparison_requested = pyqtSignal()
    signal_controlpanel_file_selection_changed = pyqtSignal(int)

    # Navigation signals
    signal_controlpanel_help_requested = pyqtSignal()
    signal_controlpanel_prev_stage_requested = pyqtSignal()
    signal_controlpanel_next_stage_requested = pyqtSignal()

    # Page-specific signals forwarded from the pages
    # Stage 1
    signal_controlpanel_angle_reset_requested = pyqtSignal()
    signal_controlpanel_perspective_reset_requested = pyqtSignal()
    signal_controlpanel_work_area_deleted = pyqtSignal(int)
    signal_controlpanel_area_selection_changed = pyqtSignal()
    # Stage 2/3
    signal_controlpanel_parameters_changed = pyqtSignal(dict)
    signal_controlpanel_reset_all_parameters_requested = pyqtSignal()
    # Stage 4
    signal_controlpanel_run_ocr_requested = pyqtSignal()
    signal_controlpanel_run_translation_requested = pyqtSignal()
    signal_controlpanel_load_model_requested = pyqtSignal()
    signal_controlpanel_save_single_requested = pyqtSignal()
    signal_controlpanel_save_batch_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()
        self._connect_signals()
        self.set_project_ui_enabled(False)

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # --- Top Actions Grid ---
        top_button_layout = QGridLayout()
        self.show_comparison_btn = QPushButton("显示图像对比")
        self.new_project_btn = QPushButton("新建工程")
        self.open_project_btn = QPushButton("打开工程")
        self.import_images_btn = QPushButton("导入图片")

        self.show_comparison_btn.setEnabled(False) # Initially disabled

        top_button_layout.addWidget(self.show_comparison_btn, 0, 0)
        top_button_layout.addWidget(self.new_project_btn, 0, 1)
        top_button_layout.addWidget(self.open_project_btn, 1, 0)
        top_button_layout.addWidget(self.import_images_btn, 1, 1)

        layout.addLayout(top_button_layout)

        # --- File list ---
        self.file_list_widget = QListWidget()
        self.file_list_widget.setMaximumHeight(133)
        layout.addWidget(self.file_list_widget)

        # --- Parameter pages ---
        self.processing_stack = QStackedWidget()
        self.processing_stack.setMinimumWidth(0)
        self.stage1_page = GeometricCorrectionPage()
        self.stage2_page = BinarizationPage()
        self.stage3_page = NoiseRemovalPage()
        self.stage4_page = OcrExportPage()

        self.processing_stack.addWidget(self.stage1_page)
        self.processing_stack.addWidget(self.stage2_page)
        self.processing_stack.addWidget(self.stage3_page)
        self.processing_stack.addWidget(self.stage4_page)

        self.params_scroll_area = QScrollArea()
        self.params_scroll_area.setWidgetResizable(True)
        self.params_scroll_area.setWidget(self.processing_stack)
        self.params_scroll_area.setFrameShape(QScrollArea.NoFrame)
        layout.addWidget(self.params_scroll_area)

        # --- Navigation ---
        navigation_layout = QHBoxLayout()
        self.help_btn = QPushButton("帮助")
        self.prev_btn = QPushButton("<< 上一步")
        self.next_btn = QPushButton("下一步 >>")
        navigation_layout.addStretch()
        navigation_layout.addWidget(self.help_btn)
        navigation_layout.addWidget(self.prev_btn)
        navigation_layout.addWidget(self.next_btn)
        layout.addLayout(navigation_layout)

    def _connect_signals(self):
        # Project
        self.new_project_btn.clicked.connect(self.signal_controlpanel_new_project_requested)
        self.open_project_btn.clicked.connect(self.signal_controlpanel_open_project_requested)
        self.import_images_btn.clicked.connect(self.signal_controlpanel_import_images_requested)
        self.show_comparison_btn.clicked.connect(self.signal_controlpanel_show_comparison_requested)
        self.file_list_widget.currentRowChanged.connect(self.signal_controlpanel_file_selection_changed)

        # Navigation
        self.help_btn.clicked.connect(self.signal_controlpanel_help_requested)
        self.prev_btn.clicked.connect(self.signal_controlpanel_prev_stage_requested)
        self.next_btn.clicked.connect(self.signal_controlpanel_next_stage_requested)

        # Forward signals from pages
        self.stage1_page.signal_geometriccorrectionpage_angle_reset_requested.connect(self.signal_controlpanel_angle_reset_requested)
        self.stage1_page.signal_geometriccorrectionpage_perspective_reset_requested.connect(self.signal_controlpanel_perspective_reset_requested)
        self.stage1_page.signal_geometriccorrectionpage_work_area_deleted.connect(self.signal_controlpanel_work_area_deleted)
        self.stage1_page.signal_geometriccorrectionpage_area_selection_changed.connect(self.signal_controlpanel_area_selection_changed)
        self.stage2_page.parameters_changed.connect(self.signal_controlpanel_parameters_changed)
        self.stage3_page.parameters_changed.connect(self.signal_controlpanel_parameters_changed)
        self.stage3_page.reset_params_btn.clicked.connect(self.signal_controlpanel_reset_all_parameters_requested)
        self.stage4_page.run_ocr_requested.connect(self.signal_controlpanel_run_ocr_requested)
        self.stage4_page.run_translation_requested.connect(self.signal_controlpanel_run_translation_requested)
        self.stage4_page.save_single_requested.connect(self.signal_controlpanel_save_single_requested)
        self.stage4_page.save_batch_requested.connect(self.signal_controlpanel_save_batch_requested)

    def set_project_ui_enabled(self, enabled: bool):
        self.import_images_btn.setEnabled(enabled)
        self.help_btn.setEnabled(enabled)
        self.processing_stack.setEnabled(enabled)
        self.show_comparison_btn.setEnabled(False) # Always disable on project state change
        self.prev_btn.setEnabled(False)
        self.next_btn.setEnabled(False)

    def set_comparison_button_enabled(self, enabled: bool):
        self.show_comparison_btn.setEnabled(enabled)

    def update_navigation_buttons(self, is_project_active, current_stage, total_stages):
        self.prev_btn.setEnabled(is_project_active and current_stage > 0)
        self.next_btn.setEnabled(is_project_active and current_stage < total_stages - 1)

    def update_file_list(self, file_list: list[ImageIdentifier]):
        self.file_list_widget.clear()
        if file_list:
            for identifier in file_list:
                self.file_list_widget.addItem(identifier.display_name)
            self.file_list_widget.setCurrentRow(0)

    def set_current_stage(self, index):
        self.processing_stack.setCurrentIndex(index)
        self.params_scroll_area.verticalScrollBar().setValue(0)

    def apply_params_to_ui(self, params):
        self.stage1_page.set_params(params)
        self.stage2_page.set_params(params)
        self.stage3_page.set_params(params)

    def get_stage_page(self, index):
        return self.processing_stack.widget(index)

    def get_stage_count(self):
        return self.processing_stack.count()
