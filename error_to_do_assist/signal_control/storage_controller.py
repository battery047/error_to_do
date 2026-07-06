"""
存储控制器
"""
from PySide6.QtCore import QObject
from ui.storage_page import StoragePage


class StorageController(QObject):
    """存储页面控制器"""

    def __init__(self, storage_page: StoragePage, parent=None):
        super().__init__(parent)
        self._storage_page = storage_page

    def _connect_signals(self):
        pass