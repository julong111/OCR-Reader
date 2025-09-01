# src/core/app_logging.py
import logging
import os
import platform
import subprocess
import sys
from datetime import datetime

from app_config import isCUDAAvailable, getCUDAVersion, getCUDADeviceCount

logger = logging.getLogger(__name__)

def setup_logging():
    # 确定日志文件的根路径
    if getattr(sys, 'frozen', False):
        # 打包后的程序
        base_path = os.path.dirname(sys.executable)
    else:
        # 开发模式
        base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

    # 1. 创建 logs 目录
    logs_dir = os.path.join(base_path, 'logs')
    os.makedirs(logs_dir, exist_ok=True)

    # 2. 生成带时间戳的文件名
    timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    log_file_path = os.path.join(logs_dir, f"{timestamp}.log")

    # 配置日志记录
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file_path, mode='w', encoding='utf-8'),
            logging.StreamHandler(sys.stdout)  # 同时输出到控制台，便于调试
        ]
    )
    logger.info("日志系统已初始化。日志文件位于: %s", log_file_path)

def log_system_info():
    logger.info("="*50)
    logger.info("开始记录系统和库的诊断信息...")

    # 1. 操作系统信息
    logger.info("操作系统: %s %s (%s)", platform.system(), platform.release(), platform.version())
    logger.info("CPU架构: %s", platform.machine())

    # 2. Python版本
    logger.info("Python版本: %s", sys.version)

    # 3. PyTorch 和 CUDA 信息
    logger.info("CUDA是否可用: %s", isCUDAAvailable())
    if isCUDAAvailable():
        logger.info("CUDA版本 (PyTorch编译时): %s", getCUDAVersion())
        # logger.info("cuDNN版本: %s", CUDNN_VERSION)
        logger.info("找到 %d 个CUDA设备。", getCUDADeviceCount())
        # for device_info in CUDA_DEVICES:
        #     logger.info("  设备 %d: %s", device_info["id"], device_info["name"])

    # 4. NVIDIA驱动信息 (通过 nvidia-smi)
    command = ["nvidia-smi"]
    try:
        logger.info("正在尝试执行 'nvidia-smi' 命令...")
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='ignore',
            check=False  # 不在返回码非0时抛出异常
        )
        if result.returncode == 0:
            logger.info("nvidia-smi 输出:\n%s", result.stdout)
        else:
            logger.warning("'nvidia-smi' 命令执行失败或未找到。返回码: %d", result.returncode)
            if result.stderr:
                logger.warning("nvidia-smi 错误输出:\n%s", result.stderr)
    except FileNotFoundError:
        logger.warning("'nvidia-smi' 命令未找到。请确保NVIDIA驱动已正确安装并配置在系统PATH中。")
    except Exception as e:
        logger.error("执行 'nvidia-smi' 时发生未知错误: %s", e)

    logger.info("诊断信息记录完毕。")
    logger.info("="*50)