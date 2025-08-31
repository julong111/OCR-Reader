# custom_slider.py
from PyQt5.QtCore import Qt, QEvent
from PyQt5.QtWidgets import QSlider

class CustomSlider(QSlider):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setAttribute(Qt.WA_AcceptTouchEvents, False)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setMouseTracking(False)
        self.click_pos = None

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            # 记录点击位置
            self.click_pos = event.pos()
            # 转发事件
            super().mousePressEvent(event)
        else:
            event.ignore()

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton and self.click_pos is not None:
            super().mouseMoveEvent(event)
        else:
            event.ignore()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.click_pos = None
            super().mouseReleaseEvent(event)
        else:
            event.ignore()

    def event(self, event):
        # 阻止所有触摸相关事件
        if event.type() in [QEvent.TouchBegin, QEvent.TouchUpdate, QEvent.TouchEnd]:
            return True  # 阻止事件传播

        # 阻止手势事件
        if event.type() == QEvent.Gesture:
            return True

        return super().event(event)

    def eventFilter(self, obj, event):
        try:
            # 确保父类方法被正确调用
            return super().eventFilter(obj, event)
        except Exception as e:
            # 捕获异常避免程序崩溃
            print(f"Event filter error: {e}")
            return False

    def closeEvent(self, event):
        # 清理事件过滤器
        try:
            # 移除所有事件过滤器
            self.removeEventFilter(self)
        except:
            pass
        event.accept()

    def wheelEvent(self, event):
        # 忽略鼠标滚轮事件，以防止在滚动面板时意外更改滑块值
        event.ignore()
