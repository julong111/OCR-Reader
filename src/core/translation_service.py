# src/core/translation_service.py
import re
import os
import logging

from app_config import getAppRoot, getCUDADevice
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

# 获取此模块的日志记录器
logger = logging.getLogger(__name__)

class TranslationService:

    def __init__(self):
        logger.debug("正在初始化 TranslationService...")
        self.tokenizer = None
        self.model = None
        self.device = None
        self.model_path = None

        self.model_path = os.path.join(getAppRoot(), "vendor", "opus-mt-en-zh")
        logger.info("翻译模型路径已设置为: %s", self.model_path)
        logger.debug("TranslationService 初始化完成。")

    def load_model(self):
        logger.info("正在尝试加载翻译模型...")
        # 如果模型已加载，则直接返回。
        if self.is_model_loaded():
            logger.info("模型已加载，跳过。")
            return

        logger.debug("正在检查模型目录: %s", self.model_path)
        # 检查模型路径是否存在
        if not os.path.isdir(self.model_path):
            logger.error("模型目录未找到: %s", self.model_path)
            raise FileNotFoundError(f"翻译模型目录未找到。期望路径: {self.model_path}")
        logger.debug("模型目录已找到。")

        try:
            self.device = getCUDADevice()
            logger.info("设备已设置为: %s", self.device)

            logger.debug("正在从 %s 加载分词器...", self.model_path)
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_path, local_files_only=True)
            logger.info("分词器加载成功。")

            logger.debug("正在从 %s 加载模型...", self.model_path)
            self.model = AutoModelForSeq2SeqLM.from_pretrained(
                self.model_path, local_files_only=True
            )
            logger.info("模型加载成功。")

            # 将模型移动到检测到的设备
            logger.debug("正在将模型移动到设备: %s", self.device)
            self.model.to(self.device)
            logger.info("模型移动到设备成功。")

            # 为生成过程设置推荐参数，以提高质量和避免错误。
            logger.debug("正在设置模型生成配置...")
            self.model.generation_config.max_length = 512
            self.model.generation_config.num_beams = 5
            self.model.generation_config.early_stopping = True
            logger.debug("生成配置设置完成。")
            logger.info("翻译模型加载流程完成。")
        except Exception as e:
            logger.error("加载模型时发生异常: %s", e, exc_info=True)
            # 将底层异常包装成一个更明确的运行时错误
            raise RuntimeError(f"加载翻译模型时出错: {e}") from e

    def is_model_loaded(self):
        return self.model is not None and self.tokenizer is not None

    def run(self, text):
        logger.info("翻译任务已开始。")
        # 实现懒加载：如果模型未加载，则在第一次运行时自动加载。
        if not self.is_model_loaded():
            logger.info("模型未加载，将进行懒加载。")
            self.load_model()

        logger.debug("正在清理输入文本。")
        # 清理并过滤掉空行
        cleaned_lines = [
            self._clean_text(line).strip() for line in text.split("\n") if line.strip()
        ]

        if not cleaned_lines:
            logger.warning("清理后没有可供翻译的非空行。")
            return ""
        logger.debug("找到 %d 行待翻译文本。", len(cleaned_lines))

        # 对所有行进行批处理，以大幅提升性能
        logger.debug("正在为模型分词...")
        inputs = self.tokenizer(
            cleaned_lines,
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=512,
        )
        logger.debug("分词完成。")

        # 将输入数据移动到与模型相同的设备
        logger.debug("正在将输入张量移动到设备: %s", self.device)
        inputs = {k: v.to(self.device) for k, v in inputs.items()}
        logger.debug("输入张量移动完成。")

        logger.debug("正在调用 model.generate()...")
        outputs = self.model.generate(**inputs)
        logger.info("模型生成完成。输出张量形状: %s", outputs.shape)

        logger.debug("正在解码模型输出。")
        # 使用batch_decode一次性解码所有结果
        translated_lines = self.tokenizer.batch_decode(
            outputs, skip_special_tokens=True
        )
        logger.debug("解码完成。")
        logger.info("翻译任务成功结束。")
        return "\n".join(translated_lines)

    def _clean_text(self, text: str) -> str:
        clean_text = re.sub(r"<[^>]+>", "", text)
        clean_text = re.sub(r"[^\w\s.,!?;:()\-\'\"]", "", clean_text)
        return clean_text