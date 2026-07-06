'''
@Description: 
@Author: batterymain
@Date: 2026-06-30 22:00:24
@LastEditTime: 2026-06-30 22:00:32
@LastEditors: batterymain
@version: v1
'''
"""
设备管理器 - 管理电梯设备列表
"""
import json
from datetime import datetime
from typing import Dict, Optional

from .constants import DEVICES_FILE


class DeviceManager:
    """设备管理器"""

    def __init__(self):
        self._devices: Dict[str, dict] = {}
        self._devices_file = DEVICES_FILE
        self.load()

    def load(self):
        """从文件加载设备列表"""
        if self._devices_file.exists():
            try:
                with open(self._devices_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self._devices = data.get('devices', {})
            except (json.JSONDecodeError, IOError) as e:
                print(f"加载设备列表失败: {e}")
                self._devices = {}
        else:
            self._create_default()

    def _create_default(self):
        """创建默认设备列表"""
        self._devices = {
            "ELV-001": {
                "name": "电梯01",
                "location": "A栋-1号梯",
                "type": "乘客电梯",
                "serial_port": "COM3",
                "status": "offline",
                "last_seen": "",
                "created": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
        }
        self.save()

    def save(self):
        """保存设备列表到文件"""
        data = {
            'devices': self._devices,
            'last_updated': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        with open(self._devices_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    # ========== CRUD操作 ==========

    def get_all(self) -> Dict[str, dict]:
        return self._devices.copy()

    def get(self, device_id: str) -> Optional[dict]:
        return self._devices.get(device_id)

    def add(self, device_id: str, info: dict) -> bool:
        if device_id in self._devices:
            return False
        info.setdefault('created', datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        info.setdefault('last_seen', "")
        info.setdefault('status', "offline")
        self._devices[device_id] = info
        self.save()
        return True

    def update(self, device_id: str, info: dict) -> bool:
        if device_id not in self._devices:
            return False
        info['updated'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self._devices[device_id].update(info)
        self.save()
        return True

    def remove(self, device_id: str) -> bool:
        if device_id not in self._devices:
            return False
        del self._devices[device_id]
        self.save()
        return True

    def update_status(self, device_id: str, status: str):
        if device_id in self._devices:
            self._devices[device_id]['status'] = status
            self._devices[device_id]['last_seen'] = datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            )
            self.save()