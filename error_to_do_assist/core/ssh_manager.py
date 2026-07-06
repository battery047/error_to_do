"""
SSH/SFTP连接管理器 - 管理RK3588远程连接
"""
import os
import stat
from pathlib import Path
from datetime import datetime

import paramiko


class SSHManager:
    """SSH/SFTP连接管理器"""

    def __init__(self):
        self._client: paramiko.SSHClient = None
        self._sftp: paramiko.SFTPClient = None
        self._connected = False
        self._settings = {
            'host': '192.168.1.100',
            'port': 22,
            'username': 'root',
            'password': '',
        }

    @property
    def is_connected(self):
        return self._connected

    def set_params(self, host, port=22, username='root', password=''):
        self._settings = {
            'host': host,
            'port': port,
            'username': username,
            'password': password,
        }

    def connect(self):
        try:
            self._client = paramiko.SSHClient()
            self._client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self._client.connect(
                hostname=self._settings['host'],
                port=self._settings['port'],
                username=self._settings['username'],
                password=self._settings['password'],
                timeout=10,
            )
            self._sftp = self._client.open_sftp()
            self._connected = True
            return True, f"已连接 {self._settings['host']}"
        except Exception as e:
            self._connected = False
            return False, f"连接失败: {e}"

    def disconnect(self):
        if self._sftp:
            self._sftp.close()
        if self._client:
            self._client.close()
        self._connected = False

    def list_dir(self, path='/'):
        """列出远程目录"""
        if not self._sftp:
            return []
        entries = []
        try:
            for entry in self._sftp.listdir_attr(path):
                entries.append({
                    'name': entry.filename,
                    'size': entry.st_size,
                    'is_dir': stat.S_ISDIR(entry.st_mode),
                    'mtime': datetime.fromtimestamp(entry.st_mtime),
                    'permissions': entry.st_mode,
                })
            entries.sort(key=lambda e: (not e['is_dir'], e['name'].lower()))
        except Exception:
            pass
        return entries

    def file_exists(self, path):
        try:
            self._sftp.stat(path)
            return True
        except FileNotFoundError:
            return False

    def is_dir(self, path):
        try:
            return stat.S_ISDIR(self._sftp.stat(path).st_mode)
        except FileNotFoundError:
            return False

    def download_file(self, remote_path, local_path):
        """下载文件"""
        self._sftp.get(remote_path, local_path)

    def upload_file(self, local_path, remote_path):
        """上传文件"""
        self._sftp.put(local_path, remote_path)

    def download_dir(self, remote_dir, local_dir):
        """递归下载目录"""
        os.makedirs(local_dir, exist_ok=True)
        for entry in self.list_dir(remote_dir):
            rp = f"{remote_dir}/{entry['name']}"
            lp = os.path.join(local_dir, entry['name'])
            if entry['is_dir']:
                self.download_dir(rp, lp)
            else:
                self._sftp.get(rp, lp)

    def upload_dir(self, local_dir, remote_dir):
        """递归上传目录"""
        self._sftp.mkdir(remote_dir, ignore_existing=True)
        for entry in os.listdir(local_dir):
            lp = os.path.join(local_dir, entry)
            rp = f"{remote_dir}/{entry}"
            if os.path.isdir(lp):
                self.upload_dir(lp, rp)
            else:
                self._sftp.put(lp, rp)

    def mkdir(self, path):
        """创建远程目录"""
        try:
            self._sftp.mkdir(path)
        except Exception:
            pass