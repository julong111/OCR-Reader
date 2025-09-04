# custom_slider.py
from PyQt5.QtCore import Qt, QEvent
from PyQt5.QtWidgets import QSlider

class CustomSlider(QSlider):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 禁用触摸事件，这是最直接的方法。
        self.setAttribute(Qt.WA_AcceptTouchEvents, False)
        # 允许通过点击和Tab键获得焦点，以获得一致的用户体验。
        self.setFocusPolicy(Qt.StrongFocus)

    def event(self, event):
        # 进一步确保触摸和手势事件被阻止，以增加代码的健壮性。
        if event.type() in [
            QEvent.TouchBegin, QEvent.TouchUpdate, QEvent.TouchEnd, QEvent.Gesture
        ]:
            return True  # 消费事件，不让父类处理
        return super().event(event)

    def wheelEvent(self, event):
        # 忽略鼠标滚轮事件，以防止在滚动面板时意外更改滑块值
        event.ignore()

    # 移除了以下冗余或不正确的方法:
    # - mousePressEvent, mouseMoveEvent, mouseReleaseEvent: QSlider的默认行为已满足需求。
    # - eventFilter, closeEvent: 事件过滤器逻辑未被正确使用，移除以避免潜在错误。
