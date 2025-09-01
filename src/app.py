# app.py
import os
import argparse
import logging
import sys

# 确定程序启动目录。
from app_config import (
    SYSTEM, MACHINE, getAppRoot,
    setCUDADeviceCount, setCUDAVersion, setCUDADevice,setCUDAAvailable,
    isCUDAAvailable
)

# 在所有其他导入之前，首先设置日志系统
from core.app_logging import setup_logging, log_system_info

# 将日志初始化作为程序的第一步
setup_logging()

logger = logging.getLogger(__name__)
if SYSTEM =="Darwin" and MACHINE == "x86_64": # MAC x86_64 没有cuda
    logger.info("Darwin x86_64 不支持cuda")
else:
    import pynvml
    try:
        # 1. 初始化 NVML 库，这是所有操作的第一步。
        pynvml.nvmlInit()
        # 2. 获取系统中 GPU 的数量。
        device_count = pynvml.nvmlDeviceGetCount()
        if device_count > 0:
            cuda_version_raw = pynvml.nvmlSystemGetCudaDriverVersion()
            # 5. NVML 返回的版本号是整数形式，需要转换成常用的格式。
            cuda_version = f"{cuda_version_raw // 1000}.{cuda_version_raw % 1000}"
            # IS_CUDA_AVAILABLE = True
            # DEVICE = "cuda"
            # CUDA_DEVICE_COUNT = device_count
            setCUDAAvailable(True)
            setCUDADevice("cuda")
            setCUDADeviceCount(device_count)
            setCUDAVersion(cuda_version)
        else:
            logger.info("未找到cuda设备")
    except pynvml.NVMLError as e:
        logger.info("初始化 NVML 时出错。可能原因：NVIDIA 驱动未安装或服务未运行。")
    finally:
        # 无论成功或失败，最后都尝试解除初始化，释放资源。
        try:
            pynvml.nvmlShutdown()
        except pynvml.NVMLError_Uninitialized:
            # 如果初始化失败，这里会抛异常，可以忽略。
            pass

# 检查cuda可用性，如果cuda可用，为各平台加载cuda
if isCUDAAvailable():
    logger.info("cuda设备可用，尝试加载指定平台cuda lib包")
    lib_path = os.path.join(getAppRoot(), 'lib')
    if os.path.isdir(lib_path):
        logger.info("找到cuda lib包，确认系统架构。")
        if SYSTEM == "Windows" and (MACHINE == "AMD64" or MACHINE == "x86_64"):
            logger.info("操作系统:%s， 架构:%s", SYSTEM, MACHINE)
            windows_cuda_path = os.path.join(lib_path, 'windows-cuda')
            if os.path.isdir(windows_cuda_path):
                sys.path.insert(0, windows_cuda_path)
                logger.info("已加载 %s",windows_cuda_path)
            else:
                logger.info("未找到windows cuda lib包，请将cuda依赖复制到项目启动目录中")
        elif SYSTEM == "Linux" and (MACHINE == "AMD64" or MACHINE == "x86_64"):
            logger.info("暂未实现")
        else:
            logger.info("暂未支持的架构。 系统:%s 架构:%s", SYSTEM, MACHINE)
    else:
        logger.info("未找到cuda lib包，请将cuda依赖复制到项目启动目录中")

# 解决Windows上可能的OpenMP库冲突导致的静默崩溃问题。
# 这必须在导入任何可能使用OpenMP的库（如PyTorch, NumPy）之前完成。
# if sys.platform == "win32":
#     os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'
#     # 禁用tokenizers库的并行处理，以避免底层库冲突导致的静默崩溃。
#     os.environ['TOKENIZERS_PARALLELISM'] = 'false'

# 强制优先加载核心计算库，以解决Windows上的底层DLL冲突。
import torch
import cv2

# --- PyTorch & CUDA 配置 ---
TORCH_VERSION = torch.__version__
TORCH_LIB_PATH = torch.__file__
logger.info("Torch VERSION: %s", TORCH_VERSION)
logger.info("Torch PATH: %s", TORCH_LIB_PATH)

# 优先导入main_ui，它会间接加载PyTorch等库，以解决Windows上可能的底层DLL冲突。
from main_ui import MainUI

from PyQt5.QtCore import QLocale, QTimer
from PyQt5.QtWidgets import QApplication, QMessageBox

if __name__ == "__main__":

    log_system_info()

    # 强制设置一个标准区域，以确保小数点'.'可以被正常输入
    QLocale.setDefault(QLocale(QLocale.C))

    app = QApplication(sys.argv)

    try:
        parser = argparse.ArgumentParser(description="图片处理与OCR工具")
        parser.add_argument("--project", help="启动时自动打开的工程路径")
        parser.add_argument("--debug", action="store_true", help="启用调试模式，输出中间图像和日志")
        # Qt会处理它自己的参数，我们只解析我们自己的
        args, unknown = parser.parse_known_args(app.arguments()[1:])

        window = MainUI(is_debug=args.debug)
        window.showMaximized()

        # 根据命令行参数决定是打开指定工程还是弹出对话框
        QTimer.singleShot(0, lambda: window.open_project_from_path(args.project))

        sys.exit(app.exec_())

    except FileNotFoundError as e:
        logger.critical("应用程序因缺少组件而启动失败。", exc_info=True)
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Critical)
        msg_box.setWindowTitle("启动错误")
        msg_box.setText("应用程序无法启动，缺少必要的组件。")
        msg_box.setInformativeText(f"详细信息：{e}\n\n请确保 'vendor' 目录已正确放置在应用程序旁边。")
        msg_box.exec_()
        sys.exit(1)
