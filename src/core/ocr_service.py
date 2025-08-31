# src/core/ocr_service.py
import cv2
import pytesseract


class OcrService:

    def run(self, image_np, lang_code="eng"):
        if len(image_np.shape) == 3:
            image_np = cv2.cvtColor(image_np, cv2.COLOR_BGR2GRAY)

        custom_config = r'--psm 11'
        text = pytesseract.image_to_string(image_np, lang=lang_code, config=custom_config)
        return text