"""
主程序入口 - 两电平电力电子设备故障识别与定位
"""
import sys
import os
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ui.main_window import MainWindow
from ui.log_page import LogPage
from ui.serial_debug_page import DevicesPage
from ui.settings_page import SettingsPage
from ui.batch_test_page import BatchTestPage
from ui.storage_page import StoragePage
from ui.evaluation_page import EvaluationPage
from ui.file_transfer_page import FileTransferPage
from ui.about_page import AboutPage

from core.serial_worker import SerialWorker
from core.device_manager import DeviceManager
from core.settings_manager import SettingsManager
from core.ssh_manager import SSHManager

from signal_control.log_controller import LogController
from signal_control.devices_controller import DevicesController
from signal_control.settings_controller import SettingsController
from signal_control.storage_controller import StorageController

from resources import ResourceManager


class Application:
    """应用程序类"""

    def __init__(self):
        self.app = QApplication(sys.argv)
        self.app.setApplicationName("故障诊断系统")
        self.app.setApplicationVersion("1.0.0")
        self.app.setFont(QFont("Microsoft YaHei", 10))

        self.app.setStyleSheet("""
            QMainWindow {
                background-color: #f0f2f5;
            }
            QWidget {
                background-color: #f0f2f5;
                color: #2c3e50;
                font-size: 13px;
            }
            QGroupBox {
                background-color: #ffffff;
                border: 1px solid #e0e3e8;
                border-radius: 8px;
                margin-top: 14px;
                padding: 16px 12px 12px 12px;
                font-weight: bold;
                color: #2c3e50;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 14px;
                padding: 0 8px;
                color: #1a237e;
            }
            QLabel {
                color: #555;
                background: transparent;
            }
            QComboBox, QSpinBox, QDoubleSpinBox, QLineEdit {
                background-color: #ffffff;
                border: 1px solid #d0d5dd;
                border-radius: 4px;
                padding: 5px 8px;
                color: #2c3e50;
            }
            QComboBox:hover, QSpinBox:hover {
                border-color: #1a237e;
            }
            QComboBox::drop-down {
                border: none;
                padding-right: 6px;
            }
            QPushButton {
                background-color: #1a237e;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 6px 12px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #283593;
            }
            QPushButton:pressed {
                background-color: #0d1642;
            }
            QPushButton:disabled {
                background-color: #c5cae9;
                color: #7986cb;
            }
            QTableWidget {
                background-color: #ffffff;
                alternate-background-color: #f8f9fb;
                gridline-color: #e8ebf0;
                border: 1px solid #e0e3e8;
                border-radius: 4px;
                font-size: 12px;
            }
            QTableWidget::item {
                padding: 4px 8px;
            }
            QHeaderView::section {
                background-color: #1a237e;
                color: white;
                padding: 8px;
                font-weight: bold;
                border: none;
            }
            QProgressBar {
                background-color: #e8ebf0;
                border: 1px solid #d0d5dd;
                border-radius: 4px;
                text-align: center;
                color: #2c3e50;
            }
            QProgressBar::chunk {
                background-color: #1a237e;
                border-radius: 3px;
            }
            QTextEdit {
                background-color: #1e1e2e;
                color: #cdd6f4;
                border: 1px solid #313244;
                border-radius: 4px;
                padding: 8px;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 12px;
            }
            QListWidget {
                background-color: #1a1a2e;
                color: #cdd6f4;
                border: none;
                outline: none;
            }
            QListWidget::item {
                padding: 14px 16px;
                border-bottom: 1px solid #16213e;
                color: #a6adc8;
            }
            QListWidget::item:selected {
                background-color: #1a237e;
                color: #ffffff;
                font-weight: bold;
            }
            QListWidget::item:hover {
                background-color: #16213e;
                color: #cdd6f4;
            }
            QTabWidget::pane {
                background-color: #ffffff;
                border: 1px solid #e0e3e8;
                border-radius: 6px;
            }
            QTabBar::tab {
                background-color: #e8ebf0;
                color: #555;
                padding: 8px 20px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
            }
            QTabBar::tab:selected {
                background-color: #ffffff;
                color: #1a237e;
                font-weight: bold;
            }
            QTabBar::tab:hover {
                background-color: #d0d5dd;
            }
            QScrollBar:vertical {
                background: #f0f2f5;
                width: 10px;
                border: none;
            }
            QScrollBar::handle:vertical {
                background: #c0c4cc;
                border-radius: 5px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background: #909399;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QScrollBar:horizontal {
                background: #f0f2f5;
                height: 10px;
                border: none;
            }
            QScrollBar::handle:horizontal {
                background: #c0c4cc;
                border-radius: 5px;
                min-width: 20px;
            }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                width: 0px;
            }
        """)

        ResourceManager.ensure_resources_dir()

        self.serial_worker = SerialWorker()
        self.device_manager = DeviceManager()
        self.settings_manager = SettingsManager()
        self.ssh_manager = SSHManager()
        

        self.main_window = MainWindow()

        self.log_page = LogPage()
        self.devices_page = DevicesPage()
        self.settings_page = SettingsPage()
        self.batch_page = BatchTestPage()
        self.storage_page = StoragePage()
        self.evaluation_page = EvaluationPage()
        self.file_transfer_page = FileTransferPage(ssh_manager=self.ssh_manager)
        self.about_page = AboutPage()

        self.log_controller = LogController(self.log_page, self.serial_worker)
        self.devices_controller = DevicesController(self.devices_page)
        self.settings_controller = SettingsController(self.settings_page, self.settings_manager)
        self.storage_controller = StorageController(self.storage_page)
        
        self._connect_cross_signals()

        self.main_window.add_page(self.log_page, "接收日志")
        self.main_window.add_page(self.devices_page, "串口调试")
        self.main_window.add_page(self.settings_page, "设置")
        self.main_window.add_page(self.batch_page, "批量测试")
        self.main_window.add_page(self.storage_page, "终端存储读取")
        self.main_window.add_page(self.evaluation_page, "性能评估")
        self.main_window.add_page(self.file_transfer_page, "文件传输")
        self.main_window.add_page(self.about_page, "关于")

        ports = SerialWorker.get_available_ports()

        self.settings_page.update_port_list(ports)
        self.log_page.update_port_list(ports)
        self.devices_page.update_port_list(ports)

        serial_settings = self.settings_manager.get_serial_settings()
        saved_port = serial_settings.get('port', '')
        if saved_port:
            idx = self.settings_page.port_combo.findText(saved_port)
            if idx >= 0:
                self.settings_page.port_combo.setCurrentIndex(idx)
            idx2 = self.log_page.port_combo.findText(saved_port)
            if idx2 >= 0:
                self.log_page.port_combo.setCurrentIndex(idx2)

    def _connect_cross_signals(self):
        self.serial_worker.connection_status.connect(self.settings_page.update_connection_status)
        self.serial_worker.send_progress.connect(self.settings_page.on_send_progress)
        self.serial_worker.send_complete.connect(self.settings_page.on_send_complete)

        self.settings_page.connect_requested.connect(self._on_connect)
        self.settings_page.disconnect_requested.connect(self._on_disconnect)
        self.settings_page.send_requested.connect(self._on_send_waveform)
        self.settings_page.send_features_requested.connect(self._on_send_features)
        self.settings_page.waveform_loaded.connect(self.log_page.set_waveform)

        # 批量测试页面
        self.batch_page.send_requested.connect(self._on_send_waveform)
        self.batch_page.send_features_requested.connect(self._on_send_features)
        self.serial_worker.data_received.connect(self._on_dsp_data_for_batch)

        self.log_page.refresh_ports.connect(self._refresh_ports)
        
        # SSH连接
        self.settings_page.ssh_connect_requested.connect(self._on_ssh_connect)
        self.settings_page.ssh_disconnect_requested.connect(self._on_ssh_disconnect)

    def _on_connect(self, port, baudrate):
        if not port:
            return
        self.serial_worker.set_serial_params(port, baudrate)
        settings = self.settings_page.get_serial_settings()
        self.serial_worker.bytesize = settings['bytesize']
        self.serial_worker.parity = settings['parity']
        self.serial_worker.stopbits = settings['stopbits']

        self.settings_manager.set('Serial', 'port', port)
        self.settings_manager.set('Serial', 'baudrate', str(baudrate))

        if self.serial_worker.connect():
            self.serial_worker.start()
            idx = self.log_page.port_combo.findText(port)
            if idx >= 0:
                self.log_page.port_combo.setCurrentIndex(idx)
            idx2 = self.devices_page.port_combo.findText(port)
            if idx2 >= 0:
                self.devices_page.port_combo.setCurrentIndex(idx2)

    def _on_disconnect(self):
        self.serial_worker.stop()
        self.serial_worker.disconnect()

    def _on_send_waveform(self, data):
        interval = self.settings_page.get_send_interval()
        self.serial_worker.send_interval_ms = interval
        csv_name = self.settings_page.get_csv_name()
        self.log_page.set_csv_name(csv_name)
        self.serial_worker.send_waveform(data)

    def _on_send_features(self, features):
        self.serial_worker.send_features_packet(features)
        self.serial_worker.raw_log.emit("[发送] 本地特征已发送到RK3566")

    def _on_dsp_data_for_batch(self, features: list, dsp_time_ms: float):
        """接收DSP返回的特征数据，直接传递给批量测试页面"""
        self.batch_page.set_dsp_result(features, dsp_time_ms)

    def _refresh_ports(self):
        ports = SerialWorker.get_available_ports()
        self.settings_page.update_port_list(ports)
        self.log_page.update_port_list(ports)
        self.devices_page.update_port_list(ports)

    def run(self):
        self.main_window.show()
        self.app.aboutToQuit.connect(self._cleanup)
        return self.app.exec()
    
    def _on_ssh_connect(self, host, port, user, pwd):
        self.ssh_manager.set_params(host, port, user, pwd)
        ok, msg = self.ssh_manager.connect()
        self.settings_page.update_ssh_status(ok, msg)
        if ok:
            self.file_transfer_page.remote_widget.set_current_path("/")

    def _on_ssh_disconnect(self):
        self.ssh_manager.disconnect()
        self.settings_page.update_ssh_status(False, "已断开")
        
    def _cleanup(self):
        if self.serial_worker.isRunning():
            self.serial_worker.stop()
            self.serial_worker.wait(2000)
        self.serial_worker.disconnect()
        self.ssh_manager.disconnect()  # 添加这行


def main():
    app = Application()
    sys.exit(app.run())


if __name__ == "__main__":
    main()