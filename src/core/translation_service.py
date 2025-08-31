# src/core/translation_service.py
import re

from transformers import AutoModelForSeq2SeqLM, AutoTokenizer


class TranslationService:
    

    def __init__(self):
        self.tokenizer = None
        self.model = None

    def load_model(self, model_path):
        
        try:
            self.tokenizer = AutoTokenizer.from_pretrained(model_path, local_files_only=True)
            self.model = AutoModelForSeq2SeqLM.from_pretrained(
                model_path, local_files_only=True
            )
            return True, "翻译模型已加载！"
        except Exception as e:
            return False, f"加载翻译模型时出错: {e}"

    def is_model_loaded(self):
        
        return self.model is not None and self.tokenizer is not None

    def run(self, text):
        
        if not self.is_model_loaded():
            raise RuntimeError("翻译模型未加载，请先加载模型。")

        lines = text.split('\n')
        non_empty_lines = [line for line in lines if line.strip()]

        translated_lines = []
        for line in non_empty_lines:
            clean_text_result = self._clean_text(line).strip()
            inputs = self.tokenizer(
                clean_text_result,
                return_tensors="pt",
                padding=True,
                truncation=True,
                max_length=512,
            )
            outputs = self.model.generate(**inputs)
            translated_text = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            translated_lines.append(translated_text)

        return '\n'.join(translated_lines)

    def _clean_text(self, text: str) -> str:
        
        clean_text = re.sub(r"<[^>]+>", "", text)
        clean_text = re.sub(r"[^\w\s.,!?;:()\-\'\"]", "", clean_text)
        return clean_text