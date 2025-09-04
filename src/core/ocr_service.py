# src/core/ocr_service.py
import os
import platform
import subprocess
import tempfile

import cv2

from app_config import TESSERACT_CMD_PATH, TESSDATA_PATH

class OcrService:

    def __init__(self):
        # 初始化逻辑被推迟到run方法中，以便在任务执行时处理错误，而不是在程序启动时。
        pass

    def run(self, image_np, lang_code="eng"):
        # 1. 验证路径
        if not TESSERACT_CMD_PATH or not os.path.exists(TESSERACT_CMD_PATH):
            raise FileNotFoundError(f"Tesseract可执行文件未找到: {TESSERACT_CMD_PATH}")
        if not TESSDATA_PATH or not os.path.exists(TESSDATA_PATH):
            raise FileNotFoundError(f"Tesseract语言数据目录未找到: {TESSDATA_PATH}")

        # 2. 准备临时文件
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as temp_input_file:
            input_path = temp_input_file.name
            cv2.imwrite(input_path, image_np)

        # Tesseract会自动添加.txt后缀
        output_base = os.path.join(tempfile.gettempdir(), os.urandom(24).hex())
        output_path_with_ext = f"{output_base}.txt"

        try:
            # 3. 准备命令
            command = [
                TESSERACT_CMD_PATH,
                input_path,
                output_base,
                "-l", lang_code,
                "--psm", "11",  # 保持原有行为
                "--tessdata-dir", TESSDATA_PATH
            ]

            # 4. 为特定平台准备环境变量以解决动态库问题
            env = os.environ.copy()
            system = platform.system()
            if system == "Darwin":
                tesseract_bin_dir = os.path.dirname(TESSERACT_CMD_PATH)
                tesseract_base_dir = os.path.dirname(tesseract_bin_dir)
                lib_path = os.path.join(tesseract_base_dir, "lib")
                if os.path.isdir(lib_path):
                    env["DYLD_LIBRARY_PATH"] = lib_path
            elif system == "Windows":
                tesseract_bin_dir = os.path.dirname(TESSERACT_CMD_PATH)
                tesseract_base_dir = os.path.dirname(tesseract_bin_dir)
                lib_path = os.path.join(tesseract_base_dir, "lib")
                if os.path.isdir(lib_path):
                    existing_path = env.get("PATH", "")
                    env["PATH"] = f"{lib_path}{os.pathsep}{existing_path}"

            # 5. 运行子进程
            subprocess.run(
                command, check=True, capture_output=True, text=True, encoding='utf-8', env=env
            )

            # 6. 读取结果
            with open(output_path_with_ext, "r", encoding="utf-8") as f:
                return f.read()

        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Tesseract执行失败: {e.stderr}") from e
        finally:
            # 7. 清理临时文件
            if os.path.exists(input_path):
                os.remove(input_path)
            if os.path.exists(output_path_with_ext):
                os.remove(output_path_with_ext)