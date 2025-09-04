# src/view/pages/ocr_export_page.py
from PyQt5.QtCore import pyqtSignal, QSignalBlocker
from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QTextEdit,
    QComboBox,
)

class OcrExportPage(QWidget):
    
    # Signals for actions requested by the user
    run_ocr_requested = pyqtSignal()
    run_translation_requested = pyqtSignal()
    save_single_requested = pyqtSignal()
    save_batch_requested = pyqtSignal()
    parameters_changed = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()
        self._connect_signals()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        # OCR section
        ocr_layout = QHBoxLayout()
        self.ocr_label = QLabel("OCR结果")
        ocr_lang_label = QLabel("OCR语言:")
        self.ocr_lang_combo = QComboBox()
        self.ocr_lang_combo.addItem("英文 (English)", "eng")
        self.ocr_lang_combo.addItem("繁体中文 (Traditional)", "chi_tra")
        self.ocr_lang_combo.addItem("简体中文 (Simplified)", "chi_sim")
        self.run_ocr_btn = QPushButton("运行OCR")
        ocr_layout.addWidget(self.ocr_label)
        ocr_layout.addWidget(ocr_lang_label)
        ocr_layout.addWidget(self.ocr_lang_combo)
        ocr_layout.addWidget(self.run_ocr_btn)
        layout.addLayout(ocr_layout)

        self.ocr_result_edit = QTextEdit()
        self.ocr_result_edit.setReadOnly(False)
        self.ocr_result_edit.setAcceptRichText(False)
        self.ocr_result_edit.setMinimumHeight(100)
        layout.addWidget(self.ocr_result_edit, 1)

        # Translation section
        self.translate_label = QLabel("翻译结果")
        self.device_label = QLabel("翻译设备:")
        self.device_combo = QComboBox()
        translation_model_label = QLabel("翻译模型:")
        self.translation_model_combo = QComboBox()
        self.translation_model_combo.addItem("Opus-MT (英-中)", "opus-mt-en-zh")
        self.run_translation_btn = QPushButton("翻译OCR")

        title_layout = QHBoxLayout()
        title_layout.addWidget(self.translate_label)
        title_layout.addStretch()
        title_layout.addWidget(self.run_translation_btn)
        layout.addLayout(title_layout)

        settings_layout = QHBoxLayout()
        settings_layout.addWidget(self.device_label)
        settings_layout.addWidget(self.device_combo)
        settings_layout.addWidget(translation_model_label)
        settings_layout.addWidget(self.translation_model_combo)
        settings_layout.addStretch()
        layout.addLayout(settings_layout)

        self.translate_result_edit = QTextEdit()
        self.translate_result_edit.setReadOnly(False)
        self.translate_result_edit.setAcceptRichText(False)
        self.translate_result_edit.setMinimumHeight(100)
        layout.addWidget(self.translate_result_edit, 1)

        # Save section
        save_button_layout = QHBoxLayout()
        self.save_single_btn = QPushButton("保存当前图片结果")
        self.save_batch_btn = QPushButton("批量保存所有图片")
        save_button_layout.addWidget(self.save_single_btn)
        save_button_layout.addWidget(self.save_batch_btn)
        layout.addLayout(save_button_layout)

    def _connect_signals(self):
        self.run_ocr_btn.clicked.connect(self.run_ocr_requested.emit)
        self.run_translation_btn.clicked.connect(self.run_translation_requested.emit)
        self.save_single_btn.clicked.connect(self.save_single_requested.emit)
        self.save_batch_btn.clicked.connect(self.save_batch_requested.emit)
        self.ocr_lang_combo.currentIndexChanged.connect(self._on_ocr_lang_changed)
        self.device_combo.currentIndexChanged.connect(self._on_device_changed)

    def get_selected_lang(self):
        return self.ocr_lang_combo.currentData()

    def get_ocr_text(self):
        return self.ocr_result_edit.toPlainText()

    def set_ocr_text(self, text):
        self.ocr_result_edit.setText(text)

    def get_translation_text(self):
        return self.translate_result_edit.toPlainText()

    def set_translation_text(self, text):
        self.translate_result_edit.setText(text)

    def set_available_devices(self, has_cuda):
        self.device_combo.clear()
        self.device_combo.addItem("CPU", "cpu")
        if has_cuda:
            self.device_combo.addItem("GPU", "cuda")

    def _on_ocr_lang_changed(self):
        lang = self.ocr_lang_combo.currentData()
        if lang:
            self.parameters_changed.emit({'ocr_lang': lang})

    def _on_device_changed(self):
        device = self.device_combo.currentData()
        if device:
            self.parameters_changed.emit({'translation_device': device})

    def set_params(self, params):
        with QSignalBlocker(self.ocr_lang_combo):
            index = self.ocr_lang_combo.findData(params.ocr_lang)
            if index != -1:
                self.ocr_lang_combo.setCurrentIndex(index)

        with QSignalBlocker(self.device_combo):
            index = self.device_combo.findData(params.translation_device)
            if index != -1:
                self.device_combo.setCurrentIndex(index)