"""
串口调试控制器
"""
from PySide6.QtCore import QObject
from ui.serial_debug_page import DevicesPage


class DevicesController(QObject):
    """串口调试页面控制器"""

    def __init__(self, devices_page: DevicesPage, parent=None):
        super().__init__(parent)
        self._devices_page = devices_page