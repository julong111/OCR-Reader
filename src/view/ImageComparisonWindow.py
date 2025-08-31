from PyQt5.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QComboBox,
    QStackedLayout
)

from .image_viewer import ImageViewer


class ImageComparisonWindow(QMainWindow):
    def __init__(self, original_pixmap, processed_pixmap, parent=None):
        super().__init__(parent)
        self.setWindowTitle("图像对比窗口")
        self.setGeometry(150, 150, 1200, 600)

        # 存储图像
        self.original_pixmap = original_pixmap
        self.processed_pixmap = processed_pixmap

        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # 创建顶部控制栏
        control_layout = QHBoxLayout()
        layout_label = QLabel("图片布局:")
        self.layout_combo = QComboBox()
        self.layout_combo.addItem("水平布局")
        self.layout_combo.addItem("垂直布局")
        self.layout_combo.setCurrentIndex(0)
        self.layout_combo.currentIndexChanged.connect(self.update_image_layout)

        control_layout.addWidget(layout_label)
        control_layout.addWidget(self.layout_combo)
        control_layout.addStretch(1)
        main_layout.addLayout(control_layout)

        # 创建图像显示区域
        self.image_stacked_layout = QStackedLayout()

        # 水平布局容器
        horizontal_container = QWidget()
        image_preview_layout_h = QHBoxLayout(horizontal_container)
        self.viewer_h1 = ImageViewer("OCR图像")
        self.viewer_h2 = ImageViewer("预览图像")
        image_preview_layout_h.addWidget(self.viewer_h1, 1)
        image_preview_layout_h.addWidget(self.viewer_h2, 1)

        # 垂直布局容器
        vertical_container = QWidget()
        image_preview_layout_v = QVBoxLayout(vertical_container)
        self.viewer_v1 = ImageViewer("OCR图像")
        self.viewer_v2 = ImageViewer("预览图像")
        image_preview_layout_v.addWidget(self.viewer_v1, 1)
        image_preview_layout_v.addWidget(self.viewer_v2, 1)

        self.image_stacked_layout.addWidget(horizontal_container)
        self.image_stacked_layout.addWidget(vertical_container)
        main_layout.addLayout(self.image_stacked_layout, 1)

        # 显示图像
        self.display_images()

        # 同步两个视图的滚动和缩放
        self._sync_viewers(self.viewer_h1, self.viewer_h2)
        self._sync_viewers(self.viewer_v1, self.viewer_v2)

    def update_image_layout(self, index):
        self.image_stacked_layout.setCurrentIndex(index)

    def _sync_viewers(self, viewer1, viewer2):
        

        # 1. 同步缩放滑块
        viewer1.zoom_slider.valueChanged.connect(viewer2.zoom_slider.setValue)
        viewer2.zoom_slider.valueChanged.connect(viewer1.zoom_slider.setValue)

        # 2. 同步水平滚动条
        scroll_bar1_h = viewer1.scroll_area.horizontalScrollBar()
        scroll_bar2_h = viewer2.scroll_area.horizontalScrollBar()
        scroll_bar1_h.valueChanged.connect(scroll_bar2_h.setValue)
        scroll_bar2_h.valueChanged.connect(scroll_bar1_h.setValue)

        # 3. 同步垂直滚动条
        scroll_bar1_v = viewer1.scroll_area.verticalScrollBar()
        scroll_bar2_v = viewer2.scroll_area.verticalScrollBar()
        scroll_bar1_v.valueChanged.connect(scroll_bar2_v.setValue)
        scroll_bar2_v.valueChanged.connect(scroll_bar1_v.setValue)

    def display_images(self):
        # 显示原始图像
        self.viewer_h1.set_pixmap(self.original_pixmap)
        self.viewer_v1.set_pixmap(self.original_pixmap)

        # 显示处理后图像
        self.viewer_h2.set_pixmap(self.processed_pixmap)
        self.viewer_v2.set_pixmap(self.processed_pixmap)
