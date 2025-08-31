# project_manager.py

import os
import shutil

import cv2
from PIL import Image
from PyQt5.QtCore import QObject, pyqtSignal

from .image_data_store import ImageDataStore
from .ini_manager import IniManager
from .image_identifier import ImageIdentifier


class ProjectManager(QObject):
    
    # Signals
    signal_projectmanager_project_activated = pyqtSignal(str, str)  # path, name
    signal_projectmanager_file_list_updated = pyqtSignal(list)
    signal_projectmanager_scan_finished = pyqtSignal(bool)  # True if files were found

    def __init__(self, parent=None):
        super().__init__(parent)
        self.project_path = None
        self.file_list = []
        self.ini_manager = IniManager()

    def activate_project(self, folder_path):
        
        if not folder_path or not os.path.isdir(folder_path):
            # Silently fail. The caller (UI) is responsible for user feedback.
            return

        self.project_path = folder_path
        self.signal_projectmanager_project_activated.emit(folder_path, os.path.basename(folder_path))
        self.scan_project_files()

    def import_images(self, source_files):
        
        if not self.project_path:
            return False  # No active project

        copied_something = False
        for file_path in source_files:
            try:
                shutil.copy(file_path, self.project_path)
                copied_something = True
            except Exception as e:
                # Log the error, but don't show a message box.
                print(f"无法复制文件 {file_path}: {e}")

        if copied_something:
            self.scan_project_files()

        return copied_something

    def scan_project_files(self):
        
        if not self.project_path:
            return

        self.file_list = []
        supported_formats = (".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff")

        try:
            filenames = sorted(os.listdir(self.project_path))
        except FileNotFoundError:
            print(f"错误: 工程路径不存在: {self.project_path}")
            return

        for f in filenames:
            filepath = os.path.join(self.project_path, f)
            # --- 关键修改：只将文件（而非文件夹）加入列表 ---
            if os.path.isfile(filepath) and f.lower().endswith(supported_formats):
                if f.lower().endswith((".tif", ".tiff")):
                    try:
                        with Image.open(filepath) as img:
                            page_count = img.n_frames
                            for i in range(page_count):
                                self.file_list.append(ImageIdentifier(path=filepath, page=i))
                    except Exception as e:
                        print(f"无法读取多页TIFF文件 {f}: {e}")
                        continue
                else:
                    self.file_list.append(ImageIdentifier(path=filepath, page=-1))

        self.signal_projectmanager_file_list_updated.emit(self.file_list)
        self.signal_projectmanager_scan_finished.emit(bool(self.file_list))

    def load_params_for_image(self, identifier: ImageIdentifier):
        
        store = ImageDataStore(self.project_path, identifier, self.ini_manager)
        return store.load_params()

    def save_parameters(self, identifier: ImageIdentifier, params):
        
        store = ImageDataStore(self.project_path, identifier, self.ini_manager)
        store.save_params(params)

    def load_stage_result(self, identifier: ImageIdentifier, stage_index):
        
        store = ImageDataStore(self.project_path, identifier, self.ini_manager)
        return store.load_stage_result(stage_index)

    def save_stage_result(self, identifier: ImageIdentifier, stage_index, main_image_data, preview_image_data=None):
        
        store = ImageDataStore(self.project_path, identifier, self.ini_manager)
        store.save_stage_result(stage_index, main_image_data, preview_image_data)

    def export_results_to_folder(self, output_folder, identifier: ImageIdentifier, processed_image, ocr_text, translated_text):
        
        if processed_image is None:
            print(f"Warning: No processed image to save for {identifier}")
            return False

        # 1. 构造唯一的文件名
        base_filename = os.path.basename(identifier.path)
        name, ext = os.path.splitext(base_filename)

        # 处理多页TIFF的文件名，确保唯一性
        if identifier.page > -1:
            name = f"p{identifier.page + 1}_{name}"

        output_image_path = os.path.join(output_folder, f"{name}_processed{ext}")
        output_text_path = os.path.join(output_folder, f"{name}_ocr.txt")
        output_translated_path = os.path.join(output_folder, f"{name}_translated.txt")

        # 2. 保存所有文件
        try:
            cv2.imwrite(output_image_path, processed_image)
            with open(output_text_path, "w", encoding="utf-8") as f:
                f.write(ocr_text)
            with open(output_translated_path, "w", encoding="utf-8") as f:
                f.write(translated_text)
            return True
        except Exception as e:
            print(f"Error saving files for {identifier} to {output_folder}: {e}")
            return False
