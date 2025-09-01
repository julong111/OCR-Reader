# src/app_config.py
import os
import sys
import platform

# --- 系统与架构 ---
SYSTEM = platform.system()
MACHINE = platform.machine()

_IS_CUDA_AVAILABLE = False
_CUDA_VERSION = "0"
_CUDA_DEVICE_COUNT = 0
_CUDA_DEVICE = "cpu"
def setCUDAAvailable(val):
    global _IS_CUDA_AVAILABLE
    _IS_CUDA_AVAILABLE = val
def setCUDAVersion(val):
    global _CUDA_VERSION
    _CUDA_VERSION = val
def setCUDADeviceCount(val):
    global _CUDA_DEVICE_COUNT
    _CUDA_DEVICE_COUNT = val
def setCUDADevice(val):
    global _CUDA_DEVICE
    _CUDA_DEVICE = val
def isCUDAAvailable():
    return _IS_CUDA_AVAILABLE
def getCUDAVersion():
    return _CUDA_VERSION
def getCUDADeviceCount():
    return _CUDA_DEVICE_COUNT
def getCUDADevice():
    return _CUDA_DEVICE

def getAppRoot():
    # 确定应用程序根目录，此方法对开发模式和PyInstaller打包后的程序均有效。
    if getattr(sys, 'frozen', False):
        # 如果程序被打包，根目录是可执行文件所在的目录。
        return os.path.dirname(sys.executable)
    else:
        # 在开发模式下，根目录是当前脚本(src/app_config.py)所在目录的上级目录。
        return os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

# 一个唯一的、在所有模块中共享的应用程序根目录常量。
APP_ROOT = getAppRoot()

# --- Tesseract 配置 ---
_TESSERACT_VENDOR_PATH = os.path.join(APP_ROOT, "vendor", "tesseract")
TESSDATA_PATH = os.path.join(_TESSERACT_VENDOR_PATH, "tessdata")

def _get_tesseract_cmd():
    # 根据操作系统和CPU架构确定Tesseract可执行文件路径
    if SYSTEM == "Darwin":  # macOS
        if MACHINE == "arm64":
            return os.path.join(_TESSERACT_VENDOR_PATH, "macos-arm64", "bin", "tesseract")
        else:  # x86_64
            return os.path.join(_TESSERACT_VENDOR_PATH, "macos-x86_64", "bin", "tesseract")
    elif SYSTEM == "Windows":
        return os.path.join(_TESSERACT_VENDOR_PATH, "windows-x86_64", "tesseract.exe")
    elif SYSTEM == "Linux":
        return os.path.join(_TESSERACT_VENDOR_PATH, "linux-x86_64", "bin", "tesseract")
    return None

TESSERACT_CMD_PATH = _get_tesseract_cmd()

