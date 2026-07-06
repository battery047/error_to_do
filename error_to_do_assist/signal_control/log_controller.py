"""
日志控制器
"""
from PySide6.QtCore import QObject
from ui.log_page import LogPage
from core.serial_worker import SerialWorker


class LogController(QObject):
    """日志页面控制器"""

    def __init__(self, log_page: LogPage, serial_worker: SerialWorker, parent=None):
        super().__init__(parent)
        self._log_page = log_page
        self._serial_worker = serial_worker
        self._connect_signals()

    def _connect_signals(self):
        self._serial_worker.raw_log.connect(
            lambda msg: self._log_page.append_log(msg, "INFO")
        )
        self._serial_worker.error_occurred.connect(
            lambda msg: self._log_page.append_log(msg, "ERROR")
        )
        self._serial_worker.data_received.connect(self._log_page.add_received_data)
        self._serial_worker.send_progress.connect(
            lambda c, t, m: self._log_page.append_log(f"[发送] {m}", "DEBUG")
        )
        self._serial_worker.send_complete.connect(
            lambda s, m: self._log_page.append_log(f"[发送] {m}", "SUCCESS" if s else "ERROR")
        )
        self._serial_worker.connection_status.connect(self._on_connection_status)

    def _on_connection_status(self, connected: bool, msg: str):
        self._log_page.set_controls_enabled(not connected)
        level = "SUCCESS" if connected else "INFO"
        self._log_page.append_log(f"串口状态: {msg}", level)