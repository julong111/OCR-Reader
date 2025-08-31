# src/core/translation_service.py
import re
import os
import platform
import torch
import sys

from transformers import AutoModelForSeq2SeqLM, AutoTokenizer


class TranslationService:

    def __init__(self):
        self.tokenizer = None
        self.model = None
        self.device = None
        self.model_path = None

        # 自动路径发现
        if getattr(sys, 'frozen', False):
            # 程序被PyInstaller打包
            base_path = os.path.dirname(sys.executable)
        else:
            # 在开发模式下运行
            base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

        self.model_path = os.path.join(base_path, "vendor", "opus-mt-en-zh")

    def load_model(self):
        # 如果模型已加载，则直接返回。
        if self.is_model_loaded():
            return

        # 检查模型路径是否存在
        if not os.path.isdir(self.model_path):
            raise FileNotFoundError(f"翻译模型目录未找到。期望路径: {self.model_path}")

        try:
            # 自动检测可用设备 (GPU或CPU)
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_path, local_files_only=True)
            self.model = AutoModelForSeq2SeqLM.from_pretrained(
                self.model_path, local_files_only=True
            )
            # 将模型移动到检测到的设备
            self.model.to(self.device)
            # 为生成过程设置推荐参数，以提高质量和避免错误。
            self.model.generation_config.max_length = 512
            self.model.generation_config.num_beams = 5
            self.model.generation_config.early_stopping = True
        except Exception as e:
            # 将底层异常包装成一个更明确的运行时错误
            raise RuntimeError(f"加载翻译模型时出错: {e}") from e

    def is_model_loaded(self):
        return self.model is not None and self.tokenizer is not None

    def run(self, text):
        # 实现懒加载：如果模型未加载，则在第一次运行时自动加载。
        if not self.is_model_loaded():
            self.load_model()

        # 清理并过滤掉空行
        cleaned_lines = [
            self._clean_text(line).strip() for line in text.split("\n") if line.strip()
        ]

        if not cleaned_lines:
            return ""

        # 对所有行进行批处理，以大幅提升性能
        inputs = self.tokenizer(
            cleaned_lines,
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=512,
        )

        # 将输入数据移动到与模型相同的设备
        inputs = {k: v.to(self.device) for k, v in inputs.items()}

        outputs = self.model.generate(**inputs)
        # 使用batch_decode一次性解码所有结果
        translated_lines = self.tokenizer.batch_decode(
            outputs, skip_special_tokens=True
        )
        return "\n".join(translated_lines)

    def _clean_text(self, text: str) -> str:
        clean_text = re.sub(r"<[^>]+>", "", text)
        clean_text = re.sub(r"[^\w\s.,!?;:()\-\'\"]", "", clean_text)
        return clean_text