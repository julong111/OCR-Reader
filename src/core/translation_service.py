# src/core/translation_service.py
import re
import os
import logging
import sys

# 确定程序启动目录。
from app_config import (
    SYSTEM, MACHINE, getAppRoot,getCUDADevice,
    setCUDADeviceCount, setCUDAVersion, setCUDADevice,setCUDAAvailable,
    isCUDAAvailable,
    setIsDEBUG
) 

# 获取此模块的日志记录器
logger = logging.getLogger(__name__)

class TranslationService:

    def __init__(self):
        logger.debug("正在初始化 TranslationService...")
        self.tokenizer = None
        self.model = None
        self.current_device = None
        self.model_path = None

        self.model_path = os.path.join(getAppRoot(), "vendor", "opus-mt-en-zh")
        logger.info("翻译模型路径已设置为: %s", self.model_path)
        logger.debug("TranslationService 初始化完成。")


    def load_model(self, target_device):
        logger.info("正在尝试将翻译模型加载到 %s...", target_device)
        # 如果模型已加载并且在正确的设备上，则直接返回。
        if self.is_model_loaded() and self.current_device == target_device:
            logger.info("模型已在目标设备 %s 上加载，跳过。", target_device)
            return
        
        logger.debug("正在检查模型目录: %s", self.model_path)
        # 检查模型路径是否存在
        if not os.path.isdir(self.model_path):
            logger.error("模型目录未找到: %s", self.model_path)
            raise FileNotFoundError(f"翻译模型目录未找到。期望路径: {self.model_path}")
        logger.debug("模型目录已找到。")

        # 检查cuda可用性，如果cuda可用，为各平台加载cuda
        if isCUDAAvailable():
            logger.info("cuda设备可用，尝试加载指定平台cuda包")
            vendor_path = os.path.join(getAppRoot(), 'vendor')
            if os.path.isdir(vendor_path):
                logger.info("找到vendor目录，确认系统架构。")
                if SYSTEM == "Windows" and (MACHINE == "AMD64" or MACHINE == "x86_64"):
                    logger.info("操作系统:%s， 架构:%s", SYSTEM, MACHINE)
                    windows_cuda_path = os.path.join(vendor_path, 'torch-222-cu118-cp39-win-amd64')
                    if os.path.isdir(windows_cuda_path):
                        sys.path.insert(0, windows_cuda_path)
                        logger.info("已加载 %s",windows_cuda_path)
                    else:
                        logger.info("未找到windows cuda依赖包，请将cuda依赖复制到项目启动目录vendor/torch-222-cu118-cp39-win-amd64中")
                elif SYSTEM == "Linux" and (MACHINE == "AMD64" or MACHINE == "x86_64"):
                    logger.info("待实现")
                else:
                    logger.info("不支持的架构。 系统:%s 架构:%s", SYSTEM, MACHINE)
            else:
                logger.info("未找到vendor目录，请将cuda依赖复制到vendor目录中")

        # 解决Windows上可能的OpenMP库冲突导致的静默崩溃问题。
        # 这必须在导入任何可能使用OpenMP的库（如PyTorch, NumPy）之前完成。
        # if sys.platform == "win32":
        #     os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'
        #     # 禁用tokenizers库的并行处理，以避免底层库冲突导致的静默崩溃。
        #     os.environ['TOKENIZERS_PARALLELISM'] = 'false'

        # 强制优先加载核心计算库，以解决Windows上的底层DLL冲突。
        import torch
        # import cv2

        # --- PyTorch & CUDA 配置 ---
        TORCH_VERSION = torch.__version__
        TORCH_LIB_PATH = torch.__file__
        logger.info("Torch VERSION: %s", TORCH_VERSION)
        logger.info("Torch PATH: %s", TORCH_LIB_PATH)

        from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

        try:
            self.current_device = target_device
            logger.info("设备已设置为: %s", self.current_device)

            if self.tokenizer is None:
                logger.debug("正在从 %s 加载分词器...", self.model_path)
                self.tokenizer = AutoTokenizer.from_pretrained(self.model_path, local_files_only=True)
                logger.info("分词器加载成功。")

            if self.model is None:
                logger.debug("正在从 %s 加载模型...", self.model_path)
                self.model = AutoModelForSeq2SeqLM.from_pretrained(
                    self.model_path, local_files_only=True
                )
                logger.info("模型加载成功。")

            # 将模型移动到检测到的设备
            logger.debug("正在将模型移动到设备: %s", self.current_device)
            self.model.to(self.current_device)
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

    def run(self, text, target_device):
        logger.info("翻译任务已开始。")
        # 实现懒加载：如果模型未加载或目标设备已更改，则加载/重新加载。
        if not self.is_model_loaded() or self.current_device != target_device:
            logger.info("模型未加载或目标设备已更改 (%s)。正在加载/重新加载模型。", target_device)
            self.load_model(target_device)

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
        logger.debug("正在将输入张量移动到设备: %s", self.current_device)
        inputs = {k: v.to(self.current_device) for k, v in inputs.items()}
        logger.debug("输入张量移动完成。")

        logger.debug("正在调用 model.generate()...")
        outputs = self.model.generate(
            **inputs,
            num_beams=self.model.generation_config.num_beams,
            max_length=self.model.generation_config.max_length,
            early_stopping=self.model.generation_config.early_stopping,
        )
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