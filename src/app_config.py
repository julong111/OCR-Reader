# src/app_config.py
import os
import sys
import platform

IS_DEBUG = False
def setIsDEBUG(val):
    global IS_DEBUG 
    IS_DEBUG = val
def isDEBUG():
    return IS_DEBUG

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


def checkCUDAInfomation():
    if SYSTEM =="Darwin" and MACHINE == "x86_64": # MAC x86_64 没有cuda
        #logger.info("Darwin x86_64 不支持cuda")
        pass
    else:
        try:
            import pynvml
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
            # else:
                #logger.info("未找到cuda设备")

        except pynvml.NVMLError as e:
            pass
            # logger.info("初始化 NVML 时出错。可能原因：NVIDIA 驱动未安装或服务未运行。")
        finally:
            # 无论成功或失败，最后都尝试解除初始化，释放资源。
            try:
                pynvml.nvmlShutdown()
            except pynvml.NVMLError_Uninitialized:
                # 如果初始化失败，这里会抛异常，可以忽略。
                pass