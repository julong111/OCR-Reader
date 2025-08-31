# src/view/smart_spinbox.py
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import QDoubleSpinBox, QSpinBox


class SmartDoubleSpinBox(QDoubleSpinBox):
    
    step_triggered = pyqtSignal()

    def keyPressEvent(self, event):
        # 检查按键生成的文本是否是英文句点或中文句号
        if event.text() == '.' or event.text() == '。':
            # 无论当前输入法是什么，都强制插入一个标准的小数点'.'
            self.lineEdit().insert('.')
            event.accept()
        else:
            # 对于其他所有按键，使用默认的处理方式
            super().keyPressEvent(event)

    def stepBy(self, steps):
        super().stepBy(steps)
        self.step_triggered.emit()


class SmartSpinBox(QSpinBox):
    
    step_triggered = pyqtSignal()

    def stepBy(self, steps):
        super().stepBy(steps)
        self.step_triggered.emit()