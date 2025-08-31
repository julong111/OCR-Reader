# worker.py
import traceback

from PyQt5.QtCore import QThread, pyqtSignal


class Worker(QThread):

    result = pyqtSignal(object)
    error = pyqtSignal(tuple)

    def __init__(self, func, *args, **kwargs):
        super().__init__()
        self.func = func
        self.args = args
        self.kwargs = kwargs

    def run(self):
        try:
            output = self.func(*self.args, **self.kwargs)
            self.result.emit(output)
        except Exception as e:
            self.error.emit((e, traceback.format_exc()))
