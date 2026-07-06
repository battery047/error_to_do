"""
设置管理器 - 读写settings.ini配置文件
"""
from configparser import ConfigParser
from pathlib import Path
from typing import Any, Dict

from .constants import SETTINGS_FILE, DEFAULT_SERIAL, SEND_INTERVAL_MS


class SettingsManager:
    """应用配置管理器"""

    def __init__(self):
        self._config = ConfigParser()
        self._config_file = SETTINGS_FILE
        self._load()

    def _load(self):
        if self._config_file.exists():
            self._config.read(self._config_file, encoding='utf-8')
        else:
            self._create_default()

    def _create_default(self):
        self._config['Serial'] = {
            'port': DEFAULT_SERIAL.get('port', 'COM3'),
            'baudrate': str(DEFAULT_SERIAL.get('baudrate', 9600)),
            'bytesize': str(DEFAULT_SERIAL.get('bytesize', 8)),
            'parity': DEFAULT_SERIAL.get('parity', 'N'),
            'stopbits': str(DEFAULT_SERIAL.get('stopbits', 1)),
        }
        self._config['Send'] = {
            'send_interval_ms': str(SEND_INTERVAL_MS),
        }
        self._config['CSV'] = {
            'last_directory': '',
            'voltage_column': '1',
            'skip_rows': '0',
            'fs': '1000',
            'max_points': '5000',
        }
        self._config['Paths'] = {
            'log_export_dir': 'logs',
            'compare_export_dir': 'analysis',
        }
        self._config['SSH'] = {
            'host': '192.168.1.100',
            'port': '22',
            'username': 'root',
            'password': '',
        }
        self.save()

    def save(self):
        self._config_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self._config_file, 'w', encoding='utf-8') as f:
            self._config.write(f)

    def get(self, section: str, key: str, fallback: str = '') -> str:
        return self._config.get(section, key, fallback=fallback)

    def getint(self, section: str, key: str, fallback: int = 0) -> int:
        return self._config.getint(section, key, fallback=fallback)

    def getboolean(self, section: str, key: str, fallback: bool = False) -> bool:
        return self._config.getboolean(section, key, fallback=fallback)

    def set(self, section: str, key: str, value: Any):
        if not self._config.has_section(section):
            self._config.add_section(section)
        self._config.set(section, key, str(value))
        self.save()

    def get_serial_settings(self) -> Dict:
        return {
            'port': self.get('Serial', 'port', 'COM3'),
            'baudrate': self.getint('Serial', 'baudrate', 9600),
            'bytesize': self.getint('Serial', 'bytesize', 8),
            'parity': self.get('Serial', 'parity', 'N'),
            'stopbits': self.getint('Serial', 'stopbits', 1),
        }

    def get_csv_settings(self) -> Dict:
        return {
            'last_directory': self.get('CSV', 'last_directory', ''),
            'voltage_column': self.getint('CSV', 'voltage_column', 1),
            'skip_rows': self.getint('CSV', 'skip_rows', 0),
            'fs': self.getint('CSV', 'fs', 1000),
            'max_points': self.getint('CSV', 'max_points', 5000),
        }

    def get_send_settings(self) -> Dict:
        return {
            'send_interval_ms': self.getint('Send', 'send_interval_ms', SEND_INTERVAL_MS),
        }

    def get_log_export_dir(self) -> str:
        return self.get('Paths', 'log_export_dir', 'logs')

    def get_compare_export_dir(self) -> str:
        return self.get('Paths', 'compare_export_dir', 'analysis')

    def get_ssh_settings(self) -> Dict:
        return {
            'host': self.get('SSH', 'host', '192.168.1.100'),
            'port': self.getint('SSH', 'port', 22),
            'username': self.get('SSH', 'username', 'root'),
            'password': self.get('SSH', 'password', ''),
        }

    def save_ssh_settings(self, host: str, port: int, username: str, password: str):
        self.set('SSH', 'host', host)
        self.set('SSH', 'port', str(port))
        self.set('SSH', 'username', username)
        self.set('SSH', 'password', password)