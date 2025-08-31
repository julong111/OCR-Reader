# src/view/help_window.py
import os

from PyQt5.QtWidgets import QDialog, QVBoxLayout, QTextBrowser, QApplication


class HelpWindow(QDialog):
    

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("帮助文档")

        # 1. 定义尺寸
        height = 600
        # 使用黄金比例计算高度
        width = int(height * 1.618)

        # 2. 计算并设置居中位置
        try:
            # 获取主屏幕的可用几何区域（不包括任务栏等）
            screen_geometry = QApplication.primaryScreen().availableGeometry()
            # 确保窗口高度不超过屏幕可用高度
            height = min(height, screen_geometry.height())
            # 计算使窗口居中的左上角坐标
            x = screen_geometry.left() + (screen_geometry.width() - width) // 2
            y = screen_geometry.top() + (screen_geometry.height() - height) // 2
            self.setGeometry(x, y, width, height)
        except AttributeError:
            # 如果无法检测到屏幕（罕见情况），则使用一个默认的回退值
            height = 600  # 回退高度
            self.setGeometry(200, 200, width, height)

        self.setMinimumSize(400, min(600, height))

        self.text_browser = QTextBrowser()
        self.text_browser.setOpenExternalLinks(True)

        layout = QVBoxLayout(self)
        layout.addWidget(self.text_browser)

    def load_content(self, file_path):
        
        try:
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"帮助文件未找到: {file_path}")

            with open(file_path, 'r', encoding='utf-8') as f:
                self.text_browser.setHtml(f.read())

        except Exception as e:
            error_message = f"无法加载帮助文档 '{file_path}':\n\n{e}"
            self.text_browser.setText(error_message)

    def show_and_jump(self, anchor=None):
        
        self.show()
        self.raise_()
        self.activateWindow()
        if anchor:
            self.text_browser.scrollToAnchor(anchor)
