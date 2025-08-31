# src/core/ocr_service.py
import os
import platform
import sys

import cv2
import pytesseract


class OcrService:

    def __init__(self):
        # 智能配置Tesseract路径，使其完全自包含。
        # 1. 确定根路径 (兼容开发模式和PyInstaller打包后)
        if getattr(sys, 'frozen', False):
            # 程序被PyInstaller打包
            # 根据新的分发策略，vendor目录位于可执行文件旁边，
            # 而不是在_MEIPASS临时目录中。
            base_path = os.path.dirname(sys.executable)
        else:
            # 在开发模式下运行
            # 从当前文件路径推断出项目根目录
            base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

        vendor_path = os.path.join(base_path, "vendor", "tesseract")
        tessdata_path = os.path.join(vendor_path, "tessdata")

        # 2. 根据操作系统和CPU架构确定Tesseract可执行文件路径
        system = platform.system()
        machine = platform.machine()
        tesseract_cmd = None

        if system == "Darwin":  # macOS
            if machine == "arm64":
                tesseract_cmd = os.path.join(vendor_path, "macos-arm64", "bin", "tesseract")
            else:  # x86_64
                tesseract_cmd = os.path.join(vendor_path, "macos-x86_64", "bin", "tesseract")
        elif system == "Windows":
            tesseract_cmd = os.path.join(vendor_path, "windows-x86_64", "tesseract.exe")
        elif system == "Linux":
            tesseract_cmd = os.path.join(vendor_path, "linux-x86_64", "bin", "tesseract")

        # 3. 验证路径并配置pytesseract
        if not tesseract_cmd or not os.path.exists(tesseract_cmd):
            raise FileNotFoundError(
                f"未找到适用于 {system} ({machine}) 的Tesseract可执行文件。"
                f"期望路径: {tesseract_cmd}"
            )

        if not os.path.exists(tessdata_path):
            raise FileNotFoundError(f"Tesseract语言数据目录未找到。期望路径: {tessdata_path}")

        pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
        os.environ['TESSDATA_PREFIX'] = tessdata_path

    def run(self, image_np, lang_code="eng"):
        if len(image_np.shape) == 3:
            image_np = cv2.cvtColor(image_np, cv2.COLOR_BGR2GRAY)

        custom_config = r'--psm 11'
        text = pytesseract.image_to_string(image_np, lang=lang_code, config=custom_config)
        return text