# app.py
import argparse
import sys

from PyQt5.QtCore import QLocale, QTimer
from PyQt5.QtWidgets import QApplication, QMessageBox

from main_ui import MainUI

if __name__ == "__main__":
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
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Critical)
        msg_box.setWindowTitle("启动错误")
        msg_box.setText("应用程序无法启动，缺少必要的组件。")
        msg_box.setInformativeText(f"详细信息：{e}\n\n请确保 'vendor' 目录已正确放置在应用程序旁边。")
        msg_box.exec_()
        sys.exit(1)
