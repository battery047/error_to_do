"""主窗口UI"""
import time
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout,
    QListWidget, QListWidgetItem, QStackedWidget,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QIcon, QPixmap, QPainter, QColor, QBrush, QPen

from core.constants import APP_NAME, APP_ID


class MainWindow(QMainWindow):
    """主窗口"""

    def __init__(self, serial_worker=None, batch_test_page=None):
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.setMinimumSize(1000, 600)

        self._serial_worker = serial_worker
        self._batch_test_page = batch_test_page

        self._set_window_icon()
        self._setup_ui()
        self._connect_serial_signals()

    def _set_window_icon(self):
        pixmap = QPixmap(32, 32)
        pixmap.fill(QColor("#1a237e"))
        painter = QPainter(pixmap)
        painter.setPen(QPen(QColor("#ffffff"), 2))
        painter.setBrush(QBrush(QColor("#42a5f5")))
        painter.drawEllipse(4, 4, 24, 24)
        painter.end()
        self.setWindowIcon(QIcon(pixmap))
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_ID)
        except Exception:
            pass

    def _setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.nav_list = QListWidget()
        self.nav_list.setFixedWidth(180)
        self.nav_list.setFont(QFont("Microsoft YaHei", 11))

        nav_items = ["接收日志", "串口调试", "设置", "批量调试", "终端存储读取", "性能评估", "文件传输", "关于"]
        for item in nav_items:
            list_item = QListWidgetItem(item)
            list_item.setTextAlignment(Qt.AlignCenter)
            self.nav_list.addItem(list_item)

        self.nav_list.setCurrentRow(0)

        self.stacked_widget = QStackedWidget()

        main_layout.addWidget(self.nav_list)
        main_layout.addWidget(self.stacked_widget, 1)

        self.nav_list.currentRowChanged.connect(self.stacked_widget.setCurrentIndex)

    def _connect_serial_signals(self):
        """连接串口信号"""
        if self._serial_worker is None or self._batch_test_page is None:
            return

        # 批量测试页面发送信号 -> 串口线程
        self._batch_test_page.send_requested.connect(
            self._serial_worker.send_waveform
        )
        self._batch_test_page.send_features_requested.connect(
            self._serial_worker.send_features_packet
        )

        # 串口线程接收数据 -> 批量测试页面
        self._serial_worker.data_received.connect(
            self._batch_test_page.set_dsp_result
        )

    def add_page(self, page_widget, name: str):
        self.stacked_widget.addWidget(page_widget)

    def set_serial_worker(self, serial_worker):
        """设置串口工作线程"""
        self._serial_worker = serial_worker
        self._connect_serial_signals()

    def set_batch_test_page(self, batch_test_page):
        """设置批量测试页面"""
        self._batch_test_page = batch_test_page
        self._connect_serial_signals()