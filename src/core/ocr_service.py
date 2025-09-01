# src/core/ocr_service.py
import os

import cv2
import pytesseract

from app_config import SYSTEM, MACHINE, TESSERACT_CMD_PATH, TESSDATA_PATH

class OcrService:

    def __init__(self):
        # 验证从配置模块获取的路径并配置pytesseract
        if not TESSERACT_CMD_PATH or not os.path.exists(TESSERACT_CMD_PATH):
            raise FileNotFoundError(
                f"未找到适用于 {SYSTEM} ({MACHINE}) 的Tesseract可执行文件。"
                f"期望路径: {TESSERACT_CMD_PATH}"
            )

        if not os.path.exists(TESSDATA_PATH):
            raise FileNotFoundError(f"Tesseract语言数据目录未找到。期望路径: {TESSDATA_PATH}")

        pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD_PATH
        os.environ['TESSDATA_PREFIX'] = TESSDATA_PATH

    def run(self, image_np, lang_code="eng"):
        if len(image_np.shape) == 3:
            image_np = cv2.cvtColor(image_np, cv2.COLOR_BGR2GRAY)

        custom_config = r'--psm 11'
        text = pytesseract.image_to_string(image_np, lang=lang_code, config=custom_config)
        return text