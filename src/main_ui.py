# main_ui.py

import os

from PyQt5.QtCore import Qt, QSignalBlocker, QRect
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import QFileDialog
from PyQt5.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QMessageBox,
    QProgressDialog,
)

from core.app_context import AppContext
from core.image_pipeline import ImagePipeline
from core.opencv_operations import convert_cv_to_qpixmap
from core.param_utils import deserialize_rect_list, serialize_rect_list
from core.parameters import ProcessingParameters
from core.project_manager import ProjectManager
from core.task_manager import TaskManager, TaskName
from view.ImageComparisonWindow import ImageComparisonWindow
from view.control_panel import ControlPanel
from view.help_window import HelpWindow
from view.image_interaction_handler import ImageInteractionHandler
from view.image_viewer import ImageViewer


class MainUI(QMainWindow):
    def __init__(self, is_debug=False):
        super().__init__()
        self.setWindowTitle("图片处理与OCR工具")
        self.setGeometry(100, 100, 1400, 800)

        # --- 初始化核心组件 ---
        self.project_manager = ProjectManager()
        self.image_pipeline = ImagePipeline()
        self.task_manager = TaskManager(self.project_manager, self.image_pipeline)
        self.app_context = AppContext(self.project_manager, self.image_pipeline, is_debug=is_debug)

        # --- UI Handlers ---
        # Defer initialization until UI is created
        self.interaction_handler = None
        self.control_panel = None
        self.image_viewer = None


        # --- 连接信号 ---
        # AppContext -> MainUI
        self.app_context.signal_appcontext_image_loaded.connect(self._on_image_loaded)
        self.app_context.signal_appcontext_image_updated.connect(self.display_images)
        self.app_context.signal_appcontext_stage_changed.connect(self._on_stage_changed)
        self.app_context.signal_appcontext_params_applied_to_ui.connect(self._apply_params_to_ui)
        # ProjectManager -> MainUI
        self.project_manager.signal_projectmanager_project_activated.connect(self._on_project_activated)
        self.project_manager.signal_projectmanager_file_list_updated.connect(self._on_file_list_updated)
        self.project_manager.signal_projectmanager_scan_finished.connect(self._on_scan_finished)

        # TaskManager -> MainUI
        self.task_manager.signal_taskmanager_task_started.connect(self._on_task_started)
        self.task_manager.signal_taskmanager_task_finished.connect(self._on_task_finished)
        self.task_manager.signal_taskmanager_task_error.connect(self._handle_task_error)
        self.task_manager.signal_taskmanager_ocr_finished.connect(self._on_ocr_result)
        self.task_manager.signal_taskmanager_translation_finished.connect(self._on_translation_result)
        self.task_manager.signal_taskmanager_batch_progress.connect(self._on_batch_progress)
        self.task_manager.signal_taskmanager_batch_finished.connect(self._on_batch_finished)

        # --- 状态标志 ---
        self._reset_zoom_on_display = False
        self._fit_view_on_stage_change = False

        self.batch_progress_dialog = None

        # --- 初始化帮助窗口 ---
        self.help_window = HelpWindow(self)
        # 假设帮助文件在项目根目录的 assets/help/ 文件夹下
        help_file_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'assets', 'help', 'content.html'))
        self.help_window.load_content(help_file_path)
        
        # 这必须在init_ui之前调用，因为它需要UI元素
        self.task_handlers = {} 
        self.init_ui()
        self._load_stylesheet()

    def show_image_comparison(self):
        # 显示图像对比窗口
        if self.app_context.preview_image is None or self.app_context.main_result_image is None:
            QMessageBox.warning(self, "警告", "请先加载并处理图片。")
            return

        # 转换图像为 QPixmap
        main_result_pixmap = convert_cv_to_qpixmap(self.app_context.main_result_image)
        preview_pixmap = convert_cv_to_qpixmap(self.app_context.preview_image)

        # 创建并显示对比窗口
        self.comparison_window = ImageComparisonWindow(main_result_pixmap, preview_pixmap, self)
        self.comparison_window.show()

    def init_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)

        # 左侧图像查看器，占满整个左侧区域
        self.image_viewer = ImageViewer()
        main_layout.addWidget(self.image_viewer, 5)

        # --- Right Panel (Control Panel) ---
        self.control_panel = ControlPanel()
        main_layout.addWidget(self.control_panel, 2)

        # --- 初始化交互处理器 ---
        self.interaction_handler = ImageInteractionHandler(
            self.image_viewer.image_label,
            self.app_context
        )
        self.interaction_handler.signal_imageinteractionhandler_overlay_needs_update.connect(self._update_overlays_slot)

        # --- Connect Signals ---
        self._connect_control_panel_signals()
        self._connect_interaction_handler_signals()
        self.app_context.signal_appcontext_context_will_change.connect(self.interaction_handler.cancel_current_interaction)
        self._setup_task_handlers()

        self.set_project_ui_enabled(False)

    def _connect_control_panel_signals(self):
        self.control_panel.signal_controlpanel_new_project_requested.connect(self._new_project)
        self.control_panel.signal_controlpanel_open_project_requested.connect(self._open_project)
        self.control_panel.signal_controlpanel_import_images_requested.connect(self._import_images)
        self.control_panel.signal_controlpanel_show_comparison_requested.connect(self.show_image_comparison)
        self.control_panel.signal_controlpanel_file_selection_changed.connect(self.app_context.set_current_image)
        self.control_panel.signal_controlpanel_help_requested.connect(self.show_help)
        self.control_panel.signal_controlpanel_prev_stage_requested.connect(self.go_to_prev_stage)
        self.control_panel.signal_controlpanel_next_stage_requested.connect(self.go_to_next_stage)
        self.control_panel.signal_controlpanel_angle_reset_requested.connect(self.reset_angle)
        self.control_panel.signal_controlpanel_perspective_reset_requested.connect(self.reset_perspective)
        self.control_panel.signal_controlpanel_work_area_deleted.connect(self.delete_work_area)
        self.control_panel.signal_controlpanel_area_selection_changed.connect(self._update_overlays_slot)
        self.control_panel.signal_controlpanel_parameters_changed.connect(self.app_context.update_parameters)
        self.control_panel.signal_controlpanel_reset_all_parameters_requested.connect(self.reset_parameters)
        self.control_panel.signal_controlpanel_run_ocr_requested.connect(self.run_ocr)
        self.control_panel.signal_controlpanel_run_translation_requested.connect(self.run_translation)
        self.control_panel.signal_controlpanel_save_single_requested.connect(self.save_single_image_results)
        self.control_panel.signal_controlpanel_save_batch_requested.connect(self.save_all_images_batch)

    def _connect_interaction_handler_signals(self):
        stage1_page = self.control_panel.get_stage_page(0)
        stage1_page.signal_geometriccorrectionpage_angle_correction_requested.connect(self.interaction_handler.start_angle_correction)
        stage1_page.signal_geometriccorrectionpage_perspective_correction_requested.connect(self.interaction_handler.start_perspective_correction)
        stage1_page.signal_geometriccorrectionpage_area_selection_requested.connect(self.interaction_handler.start_area_selection)
        stage1_page.signal_geometriccorrectionpage_area_edit_requested.connect(self.interaction_handler.start_area_editing)
        stage1_page.signal_geometriccorrectionpage_standard_char_requested.connect(self.interaction_handler.start_standard_char_selection)
        stage1_page.signal_geometriccorrectionpage_min_symbol_requested.connect(self.interaction_handler.start_min_symbol_selection)

        # 当交互彻底结束时，清除工作区列表的选中状态
        ended_signal = self.interaction_handler.signal_imageinteractionhandler_interaction_ended
        ended_signal.connect(stage1_page.clear_work_area_selection) # 只连接这一个操作

    def _setup_task_handlers(self):
        # 将任务名称映射到具体的UI更新函数。
        page4 = self.control_panel.stage4_page

        self.task_start_handlers = {
            TaskName.OCR: lambda: (page4.run_ocr_btn.setEnabled(False), page4.run_ocr_btn.setText("正在OCR...")),
            TaskName.TRANSLATE: lambda: (page4.run_translation_btn.setEnabled(False), page4.run_translation_btn.setText("正在翻译...")),
            TaskName.BATCH_SAVE: lambda: (page4.save_batch_btn.setEnabled(False), page4.save_batch_btn.setText("正在批量保存..."), self._show_batch_progress_dialog()),
        }

        self.task_finish_handlers = {
            TaskName.OCR: lambda: (page4.run_ocr_btn.setEnabled(True), page4.run_ocr_btn.setText("运行OCR")),
            TaskName.TRANSLATE: lambda: (page4.run_translation_btn.setEnabled(True), page4.run_translation_btn.setText("翻译OCR")),
            TaskName.BATCH_SAVE: lambda: (
                page4.save_batch_btn.setEnabled(True),
                page4.save_batch_btn.setText("批量保存所有图片"),
                self.batch_progress_dialog.close() if self.batch_progress_dialog else None
            ),
        }

    def _load_stylesheet(self):
        # Loads an external stylesheet.
        style_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'assets', 'style.qss'))
        try:
            with open(style_path, "r", encoding="utf-8") as f:
                self.setStyleSheet(f.read())
        except FileNotFoundError:
            print(f"Warning: Stylesheet not found at {style_path}")


    # --- Project Management Slots & Methods ---

    def open_project_from_path(self, path):
        # 从给定的路径打开工程，用于命令行启动。
        if path and os.path.isdir(path):
            self.project_manager.activate_project(path)
        elif path:  # 如果提供了路径但无效
            QMessageBox.critical(self, "错误", f"工程路径无效或不存在: {path}")
        else:  # 如果没有提供路径，则弹出对话框
            self._open_project()

    def _new_project(self):
        # 弹出对话框，创建一个新工程。
        folder = QFileDialog.getExistingDirectory(self, "选择或创建一个新的工程文件夹")
        if folder:
            self.project_manager.activate_project(folder)
            QMessageBox.information(self, "成功", f"新工程已在以下位置创建：\n{folder}\n\n现在可以导入图片了。")

    def _open_project(self):
        # 弹出对话框，打开一个已有的工程。
        folder = QFileDialog.getExistingDirectory(self, "选择工程文件夹")
        if folder:
            self.project_manager.activate_project(folder)

    def _import_images(self):
        # 将外部图片复制到当前工程文件夹中。
        if not self.project_manager.project_path:
            QMessageBox.warning(self, "警告", "请先新建或打开一个工程。")
            return

        files, _ = QFileDialog.getOpenFileNames(self, "选择要导入的图片", "",
                                                "图片文件 (*.png *.jpg *.jpeg *.bmp *.tif *.tiff)")
        if files:
            if not self.project_manager.import_images(files):
                QMessageBox.warning(self, "导入失败", f"无法复制一个或多个文件，请查看控制台日志。")

    # --- End Project Management ---

    def keyPressEvent(self, event):
        # 处理主窗口的按键事件。
        if event.key() == Qt.Key_Escape:
            if self.interaction_handler and self.interaction_handler.handle_key_press(event.key()):
                return  # Event was handled by the interaction handler
        super().keyPressEvent(event)

    def delete_work_area(self, index):
        # 删除指定索引的工作区
        params = self.app_context.params
        work_areas = deserialize_rect_list(params.work_areas)

        if not (0 <= index < len(work_areas)):
            return

        area_to_delete_tuple = work_areas[index]
        area_to_delete_qrect = QRect(*area_to_delete_tuple)

        # 检查标准字或最小符号矩形是否在要删除的区域内
        std_char_rect_str = params.standard_char_rect
        min_sym_rect_str = params.min_symbol_rect

        std_char_is_inside = False
        if std_char_rect_str:
            std_char_qrect = QRect(*deserialize_rect_list(std_char_rect_str)[0])
            if area_to_delete_qrect.contains(std_char_qrect):
                std_char_is_inside = True

        min_sym_is_inside = False
        if min_sym_rect_str:
            min_sym_qrect = QRect(*deserialize_rect_list(min_sym_rect_str)[0])
            if area_to_delete_qrect.contains(min_sym_qrect):
                min_sym_is_inside = True

        # 如果没有包含任何内容，则直接删除
        if not std_char_is_inside and not min_sym_is_inside:
            del work_areas[index]
            self.app_context.update_parameters({'work_areas': serialize_rect_list(work_areas)})
            return

        # 如果包含内容，则请求用户确认
        reply = QMessageBox.question(
            self,
            "确认删除",
            "此工作区内包含“标准字”或“最小符号”的选区。\n"
            "删除此工作区将同时移除这些选区及其关联参数。\n\n"
            "您确定要继续吗？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            params_to_update = {}
            default_params = ProcessingParameters()

            # 1. 移除工作区
            del work_areas[index]
            params_to_update['work_areas'] = serialize_rect_list(work_areas)

            # 2. 如果标准字在内部，则重置它及其派生参数
            if std_char_is_inside:
                params_to_update['standard_char_rect'] = ''
                params_to_update['sample_char_height'] = default_params.sample_char_height
                params_to_update['thresh_blocksize'] = default_params.thresh_blocksize
                params_to_update['large_noise_thresh'] = default_params.large_noise_thresh

            # 3. 如果最小符号在内部，则重置它及其派生参数
            if min_sym_is_inside:
                params_to_update['min_symbol_rect'] = ''
                params_to_update['min_symbol_height'] = default_params.min_symbol_height
                params_to_update['small_noise_thresh'] = default_params.small_noise_thresh

            self.app_context.update_parameters(params_to_update)

    def reset_angle(self):
        # 重置旋转角度
        # 只重置角度，不影响透视
        self.app_context.update_parameters({'rotation_angle': 0.0})

    def reset_perspective(self):
        # 重置透视校正
        # 重置透视时，也应重置基于它的旋转
        self.app_context.update_parameters({'perspective_points': '', 'rotation_angle': 0.0})

    def set_project_ui_enabled(self, enabled: bool):
        # 根据是否有工程打开来启用/禁用相关UI组件。
        self.control_panel.set_project_ui_enabled(enabled)
        self.image_viewer.setEnabled(enabled)

        if enabled:
            self._update_navigation_buttons()

    def _on_project_activated(self, path, name):
        # 当一个工程被激活时更新UI。
        self.setWindowTitle(f"图片处理与OCR工具 - [{name}]")
        self.set_project_ui_enabled(True)

    def _on_file_list_updated(self, file_list):
        # 当工程文件列表更新时，刷新UI列表。
        self.control_panel.update_file_list(file_list)

    def _on_scan_finished(self, has_files):
        if not has_files:
            QMessageBox.information(self, "提示", "工程文件夹中没有找到支持的图片文件。")

    def show_help(self):
        # 根据当前阶段显示对应的帮助内容。
        stage_index = self.app_context.current_stage_index
        anchors = {
            0: "stage1",
            1: "stage2",
            2: "stage3",
            3: "stage4",
        }
        self.help_window.show_and_jump(anchors.get(stage_index))

    def reset_parameters(self):
        # 恢复图像处理参数到默认值
        self.app_context.reset_parameters()

    def go_to_prev_stage(self):
        # 切换到上一个处理阶段
        if self.app_context.current_stage_index > 0:
            self.app_context.set_stage(self.app_context.current_stage_index - 1)

    def go_to_next_stage(self):
        # 切换到下一个处理阶段
        if self.app_context.current_stage_index < self.control_panel.get_stage_count() - 1:
            # 如果从第一阶段进入后续阶段，设置一个标志，以便在显示时自动适应视图
            if self.app_context.current_stage_index == 0:
                self._fit_view_on_stage_change = True
            self.app_context.set_stage(self.app_context.current_stage_index + 1)

    def _update_navigation_buttons(self):
        # 根据当前阶段更新导航按钮的启用状态
        # 只有当工程打开且有图片被选中时，导航按钮才可用
        is_project_active = self.project_manager.project_path is not None and self.app_context.current_image_identifier is not None
        self.control_panel.update_navigation_buttons(
            is_project_active,
            self.app_context.current_stage_index,
            self.control_panel.get_stage_count()
        )

    def _apply_params_to_ui(self, params: ProcessingParameters):
        # 将加载的参数应用到UI控件上。
        # 如果没有加载参数，则重置UI到默认值
        if not params:
            self.reset_parameters()
            return

        # 委托给每个页面去设置自己的UI
        # QSignalBlocker 可以在设置多个控件值时，临时阻止信号发射，防止update_image被多次调用
        with QSignalBlocker(self.control_panel.stage1_page), QSignalBlocker(self.control_panel.stage2_page), QSignalBlocker(self.control_panel.stage3_page):
            self.control_panel.apply_params_to_ui(params)

    def _on_stage_changed(self, index):
        # 响应AppContext中阶段变化。
        self.control_panel.set_current_stage(index)
        self._update_navigation_buttons()

    def _on_image_loaded(self):
        # 当AppContext加载完一张新图片后，更新UI。
        try:
            if self.app_context.original_image is None:
                raise ValueError("无法加载图像")
            self._reset_zoom_on_display = True
            # The image processing is already triggered inside AppContext.set_current_image
            # Configure UI pages that depend on image size
            self.control_panel.stage2_page.configure_for_image(self.app_context.original_image)
            self.control_panel.set_comparison_button_enabled(True)
        except Exception as e:
            QMessageBox.critical(self, "错误", f"无法加载图片: {e}")
            self.display_images()
            self.control_panel.set_comparison_button_enabled(False)

    def display_images(self):
        # Main entry point to refresh the image display.
        # It decides whether to fit a new image or preserve the view for an updated one.
        preview_pixmap = convert_cv_to_qpixmap(self.app_context.preview_image)

        if preview_pixmap is None or preview_pixmap.isNull():
            self.image_viewer.set_pixmap(QPixmap())
            return

        self.image_viewer.set_pixmap(preview_pixmap)
        self._update_label_overlays(self.image_viewer.image_label)

        if self._reset_zoom_on_display:
            self.image_viewer.fit_to_view()
            self._reset_zoom_on_display = False
        elif self._fit_view_on_stage_change:
            self.image_viewer.fit_to_view()
            self._fit_view_on_stage_change = False

    def _update_label_overlays(self, image_label):
        # Updates the visual overlays on the image label, like work areas.
        params = self.app_context.params
        stage_index = self.app_context.current_stage_index

        # Work areas
        work_areas_source = params.relative_work_areas if stage_index > 0 else params.work_areas
        image_label.work_areas = deserialize_rect_list(work_areas_source) if work_areas_source else []
        image_label.selected_area_index = self.control_panel.stage1_page.work_areas_list.currentRow()

        # Standard char rect
        # These are only displayed if work areas are defined and we are in a later stage,
        # or if we are in stage 1.
        std_char_source = params.relative_standard_char_rect if stage_index > 0 else params.standard_char_rect
        image_label.standard_char_rect = None
        if std_char_source:
            rects = deserialize_rect_list(std_char_source)
            if rects:
                image_label.standard_char_rect = QRect(*rects[0])

        # Min symbol rect
        min_sym_source = params.relative_min_symbol_rect if stage_index > 0 else params.min_symbol_rect
        image_label.min_symbol_rect = None
        if min_sym_source:
            rects = deserialize_rect_list(min_sym_source)
            if rects:
                image_label.min_symbol_rect = QRect(*rects[0])

        image_label.update()

    def _update_overlays_slot(self):
        
        if self.image_viewer and self.image_viewer.image_label.pixmap():
            self._update_label_overlays(self.image_viewer.image_label)

    def _handle_task_error(self, error_info):
        # 处理工作线程中的错误。
        exception, tb = error_info
        print(tb)  # For debugging
        QMessageBox.critical(self, "任务出错", f"执行过程中发生错误:\n{exception}")

    def _on_task_started(self, task_name):
        # 当一个后台任务开始时，更新UI（例如，禁用按钮）。
        handler = self.task_start_handlers.get(task_name)
        if handler:
            handler()

    def _on_task_finished(self, task_name):
        # 当一个后台任务完成时，恢复UI。
        handler = self.task_finish_handlers.get(task_name)
        if handler:
            handler()

    def run_ocr(self):
        if self.app_context.main_result_image is None:
            QMessageBox.warning(self, "警告", "请先加载并处理图片。")
            return

        self.control_panel.stage4_page.set_ocr_text('')
        selected_lang = self.control_panel.stage4_page.get_selected_lang()
        self.task_manager.start_ocr(self.app_context.main_result_image.copy(), selected_lang)

    def _on_ocr_result(self, ocr_text):
        # OCR完成后的回调函数。
        self.control_panel.stage4_page.set_ocr_text(ocr_text)

    def run_translation(self):
        ocr_text = self.control_panel.stage4_page.get_ocr_text().strip()
        if not ocr_text:
            QMessageBox.warning(self, "警告", "OCR结果框中没有文本可供翻译。")
            self.control_panel.stage4_page.set_translation_text("无文本可翻译。")
            return

        self.control_panel.stage4_page.set_translation_text('')
        self.task_manager.start_translation(ocr_text)

    def _on_translation_result(self, translated_text):
        # 翻译完成后的回调函数。
        self.control_panel.stage4_page.set_translation_text(translated_text)

    def save_single_image_results(self):
        # 调用ProjectManager来保存当前图像的所有处理结果。
        if self.app_context.main_result_image is None:
            QMessageBox.warning(self, "警告", "没有处理后的图片可以保存。")
            return

        output_folder = QFileDialog.getExistingDirectory(self, "选择保存结果的文件夹")
        if not output_folder:
            return

        success = self.project_manager.export_results_to_folder(
            output_folder,
            self.app_context.current_image_identifier,
            self.app_context.main_result_image,
            self.control_panel.stage4_page.get_ocr_text(),
            self.control_panel.stage4_page.get_translation_text(),
        )

        if success:
            QMessageBox.information(self, "保存成功", f"文件已成功保存到:\n{output_folder}")
        else:
            QMessageBox.critical(self, "保存失败", "保存文件时发生错误，请查看控制台日志。")

    def save_all_images_batch(self):
        if not self.project_manager.file_list:
            QMessageBox.warning(self, "警告", "工程中没有图片可供处理。")
            return

        output_folder = QFileDialog.getExistingDirectory(self, "选择批量保存结果的文件夹")
        if not output_folder:
            return

        self.task_manager.start_batch_save(self.project_manager.file_list, output_folder)

    def _show_batch_progress_dialog(self):
        self.batch_progress_dialog = QProgressDialog("正在准备批量处理...", "取消", 0, len(self.project_manager.file_list), self)
        self.batch_progress_dialog.setWindowTitle("批量保存进度")
        self.batch_progress_dialog.setWindowModality(Qt.WindowModal)
        self.batch_progress_dialog.show()

    def _on_batch_progress(self, current, total, filename):
        if self.batch_progress_dialog:
            self.batch_progress_dialog.setLabelText(f"正在处理: {filename} ({current}/{total})")
            self.batch_progress_dialog.setValue(current)

    def _on_batch_finished(self, message):
        if self.batch_progress_dialog:
            self.batch_progress_dialog.close()
        QMessageBox.information(self, "批量处理完成", message)