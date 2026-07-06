'''
@Description: 
@Author: batterymain
@Date: 2026-06-30 23:08:16
@LastEditTime: 2026-06-30 23:08:23
@LastEditors: batterymain
@version: v1
'''
"""
设置控制器
"""
from PySide6.QtCore import QObject
from ui.settings_page import SettingsPage
from core.settings_manager import SettingsManager


class SettingsController(QObject):
    """设置页面控制器"""

    def __init__(self, settings_page: SettingsPage, settings_manager: SettingsManager, parent=None):
        super().__init__(parent)
        self._settings_page = settings_page
        self._settings_manager = settings_manager
        self._connect_signals()
        self._load_settings()

    def _connect_signals(self):
        self._settings_page.save_settings.connect(self._on_save_settings)

    def _load_settings(self):
        """加载设置到页面"""
        serial_settings = self._settings_manager.get_serial_settings()
        self._settings_page.set_settings(serial_settings)

    def _on_save_settings(self, settings: dict):
        """保存设置"""
        for key, value in settings.items():
            self._settings_manager.set('Serial', key, str(value))