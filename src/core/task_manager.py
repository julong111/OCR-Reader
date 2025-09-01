# task_manager.py
import os

from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtWidgets import QMessageBox

from .parameters import ProcessingParameters
from .task_definitions import TaskName
from .worker import Worker
from .ocr_service import OcrService
from .translation_service import TranslationService
from .image_identifier import ImageIdentifier


class TaskManager(QObject):
    
    # 为特定任务结果定义的信号
    signal_taskmanager_ocr_finished = pyqtSignal(str)
    signal_taskmanager_translation_finished = pyqtSignal(str)
    signal_taskmanager_model_loaded = pyqtSignal(tuple)
    signal_taskmanager_batch_progress = pyqtSignal(int, int, str)  # current, total, filename
    signal_taskmanager_batch_finished = pyqtSignal(str)  # message

    # 通用信号，用于管理UI状态（例如，禁用/启用按钮）
    signal_taskmanager_task_started = pyqtSignal(TaskName)
    signal_taskmanager_task_finished = pyqtSignal(TaskName)
    signal_taskmanager_task_error = pyqtSignal(tuple)

    def __init__(self, project_manager, image_pipeline, parent=None):
        super().__init__(parent)
        self.project_manager = project_manager
        self.image_pipeline = image_pipeline
        self.ocr_service = OcrService()
        self.translation_service = TranslationService()
        self.worker = None

    def _is_task_running(self):
        
        if self.worker and self.worker.isRunning():
            QMessageBox.warning(None, "警告", "另一个任务正在运行，请稍候。")
            return True
        return False

    def start_ocr(self, image, lang):
        if self._is_task_running():
            return
        self.signal_taskmanager_task_started.emit(TaskName.OCR)
        self.worker = Worker(self.ocr_service.run, image, lang)
        self.worker.result.connect(self.signal_taskmanager_ocr_finished.emit)
        self.worker.error.connect(self.signal_taskmanager_task_error.emit)
        self.worker.finished.connect(lambda: self.signal_taskmanager_task_finished.emit(TaskName.OCR))
        self.worker.start()

    def start_translation(self, text):
        if self._is_task_running():
            return
        self.signal_taskmanager_task_started.emit(TaskName.TRANSLATE)
        self.worker = Worker(self.translation_service.run, text)
        self.worker.result.connect(self.signal_taskmanager_translation_finished.emit)
        self.worker.error.connect(self.signal_taskmanager_task_error.emit)
        self.worker.finished.connect(lambda: self.signal_taskmanager_task_finished.emit(TaskName.TRANSLATE))
        self.worker.start()
        # result = self.translation_service.run(text)
        # self.signal_taskmanager_translation_finished.emit(result)
        # self.signal_taskmanager_task_finished.emit(TaskName.TRANSLATE)

    def start_load_model(self, model_path):
        if self._is_task_running():
            return
        self.signal_taskmanager_task_started.emit(TaskName.LOAD_MODEL)
        self.worker = Worker(self.translation_service.load_model, model_path)
        self.worker.result.connect(self.signal_taskmanager_model_loaded.emit)
        self.worker.error.connect(self.signal_taskmanager_task_error.emit)
        self.worker.finished.connect(lambda: self.signal_taskmanager_task_finished.emit(TaskName.LOAD_MODEL))
        self.worker.start()

    def start_batch_save(self, file_list, output_folder):
        if self._is_task_running():
            return
        self.signal_taskmanager_task_started.emit(TaskName.BATCH_SAVE)
        self.worker = Worker(self._run_batch_save, file_list, output_folder)
        self.worker.error.connect(self.signal_taskmanager_task_error.emit)
        self.worker.finished.connect(lambda: self.signal_taskmanager_task_finished.emit(TaskName.BATCH_SAVE))
        self.worker.start()

    def _run_batch_save(self, file_list, output_folder):
        total_files = len(file_list)
        for i, identifier in enumerate(file_list):

            self.signal_taskmanager_batch_progress.emit(i + 1, total_files, identifier.display_name)

            params_dict = self.project_manager.load_params_for_image(identifier)
            params_obj = ProcessingParameters.from_dict(params_dict)
            original_image = self.image_pipeline.opencv_ops.load_raw_image(identifier)
            if original_image is None:
                continue

            final_ocr_image = self.image_pipeline.process_fully(original_image, params_obj)
            if final_ocr_image is None:
                continue

            ocr_lang = params_obj.ocr_lang
            ocr_text = self.ocr_service.run(final_ocr_image, ocr_lang)

            translated_text = ""
            if ocr_text.strip() and self.translation_service.is_model_loaded():
                translated_text = self.translation_service.run(ocr_text)

            self.project_manager.export_results_to_folder(
                output_folder, identifier, final_ocr_image, ocr_text, translated_text
            )
        self.signal_taskmanager_batch_finished.emit(f"批量处理完成！共处理 {total_files} 个文件。")