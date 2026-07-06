"""
文件传输页面 - 左侧本地文件，右侧设备文件（SSH/SFTP），支持双向传输
"""
import os
import shutil
from pathlib import Path
from datetime import datetime

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTreeWidget, QTreeWidgetItem, QHeaderView,
    QMessageBox, QProgressBar, QLineEdit,
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QFont


class FileTreeWidget(QWidget):
    """本地文件树"""

    path_changed = Signal(str)

    def __init__(self, title="本地文件", root_path=None, parent=None):
        super().__init__(parent)
        self._root_path = root_path or str(Path.home())
        self._current_path = self._root_path
        self._setup_ui(title)

    def _setup_ui(self, title):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        title_label = QLabel(title)
        title_label.setStyleSheet("font-weight:bold;color:#1a237e;font-size:12px;background:transparent;padding:2px 0;")
        layout.addWidget(title_label)

        path_layout = QHBoxLayout()
        self.up_btn = QPushButton("↑")
        self.up_btn.setFixedSize(32, 26)
        self.up_btn.setToolTip("返回上级目录")
        self.up_btn.setStyleSheet("QPushButton{background:#1a237e;color:white;border:none;border-radius:3px;font-size:12px;font-weight:bold;}")
        self.up_btn.clicked.connect(self._go_up)
        path_layout.addWidget(self.up_btn)

        self.path_edit = QLineEdit(self._current_path)
        self.path_edit.setMinimumHeight(26)
        self.path_edit.setStyleSheet("QLineEdit{background:white;border:1px solid #d0d5dd;border-radius:3px;padding:2px 6px;font-size:11px;color:#333;}")
        self.path_edit.returnPressed.connect(self._on_path_entered)
        path_layout.addWidget(self.path_edit, 1)

        self.refresh_btn = QPushButton("刷新")
        self.refresh_btn.setFixedSize(48, 26)
        self.refresh_btn.setStyleSheet("QPushButton{background:#1a237e;color:white;border:none;border-radius:3px;font-size:11px;font-weight:bold;}")
        self.refresh_btn.clicked.connect(self.refresh)
        path_layout.addWidget(self.refresh_btn)

        layout.addLayout(path_layout)

        self.tree = QTreeWidget()
        self.tree.setColumnCount(4)
        self.tree.setHeaderLabels(["名称", "大小", "修改日期", "类型"])
        self.tree.setRootIsDecorated(True)
        self.tree.setSelectionMode(QTreeWidget.SingleSelection)
        self.tree.setIndentation(16)
        self.tree.setFont(QFont("Microsoft YaHei", 10))

        header = self.tree.header()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.Fixed)
        self.tree.setColumnWidth(1, 75)
        header.setSectionResizeMode(2, QHeaderView.Fixed)
        self.tree.setColumnWidth(2, 120)
        header.setSectionResizeMode(3, QHeaderView.Fixed)
        self.tree.setColumnWidth(3, 65)

        self.tree.setStyleSheet("""
            QTreeWidget { background-color: #fafbfc; border: 1px solid #e0e3e8; border-radius: 4px; outline: none; }
            QTreeWidget::item { padding: 2px 6px; color: #4a5568; border-bottom: 1px solid #f0f2f5; }
            QTreeWidget::item:hover { background-color: #edf2f7; color: #2d3748; }
            QTreeWidget::item:selected { background-color: #1a237e; color: white; }
            QHeaderView::section { background-color: #1a237e; color: white; padding: 5px 8px; border: none; font-weight: bold; font-size: 11px; }
        """)

        self.tree.itemDoubleClicked.connect(self._on_item_double_clicked)
        layout.addWidget(self.tree, 1)

    @property
    def current_path(self):
        return self._current_path

    def set_root_path(self, path):
        self._root_path = path
        self._current_path = path
        self.path_edit.setText(path)
        self.refresh()

    def get_selected_path(self):
        items = self.tree.selectedItems()
        if items:
            return items[0].data(0, Qt.UserRole)
        return None

    def get_selected_name(self):
        items = self.tree.selectedItems()
        if items:
            return items[0].text(0)
        return None

    def refresh(self):
        self.tree.clear()
        self.path_edit.setText(self._current_path)
        self.path_changed.emit(self._current_path)

        try:
            path = Path(self._current_path)
            if not path.exists():
                return
            entries = sorted(path.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
            for entry in entries:
                item = QTreeWidgetItem()
                item.setText(0, entry.name)
                if entry.is_dir():
                    item.setText(1, "")
                    item.setText(3, "文件夹")
                    item.setData(0, Qt.UserRole, str(entry))
                    QTreeWidgetItem(item)
                else:
                    size = entry.stat().st_size
                    item.setText(1, self._format_size(size))
                    item.setText(3, entry.suffix or "文件")
                    item.setData(0, Qt.UserRole, str(entry))
                mtime = datetime.fromtimestamp(entry.stat().st_mtime)
                item.setText(2, mtime.strftime("%Y-%m-%d %H:%M"))
                self.tree.addTopLevelItem(item)
        except PermissionError:
            pass
        except Exception as e:
            self.tree.clear()
            QTreeWidgetItem(self.tree).setText(0, f"错误: {e}")

    def _on_item_double_clicked(self, item, column):
        path_str = item.data(0, Qt.UserRole)
        if path_str:
            p = Path(path_str)
            if p.is_dir():
                self._current_path = str(p)
                self.refresh()

    def _go_up(self):
        parent = str(Path(self._current_path).parent)
        if parent != self._current_path:
            self._current_path = parent
            self.refresh()

    def _on_path_entered(self):
        new_path = self.path_edit.text()
        if os.path.isdir(new_path):
            self._current_path = new_path
            self.refresh()
        else:
            self.path_edit.setText(self._current_path)

    @staticmethod
    def _format_size(size):
        if size < 1024: return f"{size} B"
        elif size < 1024*1024: return f"{size/1024:.1f} KB"
        elif size < 1024*1024*1024: return f"{size/1024/1024:.1f} MB"
        return f"{size/1024/1024/1024:.1f} GB"


class RemoteFileTreeWidget(QWidget):
    """远程文件树（SSH/SFTP）"""

    path_changed = Signal(str)

    def __init__(self, ssh_manager, title="设备文件", parent=None):
        super().__init__(parent)
        self._ssh = ssh_manager
        self._current_path = "/"
        self._setup_ui(title)

    def _setup_ui(self, title):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        title_label = QLabel(title)
        title_label.setStyleSheet("font-weight:bold;color:#1a237e;font-size:12px;background:transparent;padding:2px 0;")
        layout.addWidget(title_label)

        path_layout = QHBoxLayout()
        self.up_btn = QPushButton("↑")
        self.up_btn.setFixedSize(32, 26)
        self.up_btn.setToolTip("返回上级目录")
        self.up_btn.setStyleSheet("QPushButton{background:#1a237e;color:white;border:none;border-radius:3px;font-size:12px;font-weight:bold;}")
        self.up_btn.clicked.connect(self._go_up)
        path_layout.addWidget(self.up_btn)

        self.path_edit = QLineEdit(self._current_path)
        self.path_edit.setMinimumHeight(26)
        self.path_edit.setStyleSheet("QLineEdit{background:white;border:1px solid #d0d5dd;border-radius:3px;padding:2px 6px;font-size:11px;color:#333;}")
        self.path_edit.returnPressed.connect(self._on_path_entered)
        path_layout.addWidget(self.path_edit, 1)

        self.home_btn = QPushButton("家目录")
        self.home_btn.setFixedSize(55, 26)
        self.home_btn.setStyleSheet("QPushButton{background:#1a237e;color:white;border:none;border-radius:3px;font-size:10px;font-weight:bold;}")
        self.home_btn.clicked.connect(self._go_home)
        path_layout.addWidget(self.home_btn)

        self.refresh_btn = QPushButton("刷新")
        self.refresh_btn.setFixedSize(48, 26)
        self.refresh_btn.setStyleSheet("QPushButton{background:#1a237e;color:white;border:none;border-radius:3px;font-size:11px;font-weight:bold;}")
        self.refresh_btn.clicked.connect(self.refresh)
        path_layout.addWidget(self.refresh_btn)

        layout.addLayout(path_layout)

        self.tree = QTreeWidget()
        self.tree.setColumnCount(4)
        self.tree.setHeaderLabels(["名称", "大小", "修改日期", "类型"])
        self.tree.setRootIsDecorated(True)
        self.tree.setSelectionMode(QTreeWidget.SingleSelection)
        self.tree.setIndentation(16)
        self.tree.setFont(QFont("Microsoft YaHei", 10))

        header = self.tree.header()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.Fixed)
        self.tree.setColumnWidth(1, 75)
        header.setSectionResizeMode(2, QHeaderView.Fixed)
        self.tree.setColumnWidth(2, 120)
        header.setSectionResizeMode(3, QHeaderView.Fixed)
        self.tree.setColumnWidth(3, 65)

        self.tree.setStyleSheet("""
            QTreeWidget { background-color: #fafbfc; border: 1px solid #e0e3e8; border-radius: 4px; outline: none; }
            QTreeWidget::item { padding: 2px 6px; color: #4a5568; border-bottom: 1px solid #f0f2f5; }
            QTreeWidget::item:hover { background-color: #edf2f7; color: #2d3748; }
            QTreeWidget::item:selected { background-color: #1a237e; color: white; }
            QHeaderView::section { background-color: #1a237e; color: white; padding: 5px 8px; border: none; font-weight: bold; font-size: 11px; }
        """)

        self.tree.itemDoubleClicked.connect(self._on_item_double_clicked)
        layout.addWidget(self.tree, 1)

    @property
    def current_path(self):
        return self._current_path

    def set_current_path(self, path):
        self._current_path = path
        self.path_edit.setText(path)
        self.refresh()

    def get_selected_path(self):
        items = self.tree.selectedItems()
        if items:
            return self._current_path + "/" + items[0].text(0) if self._current_path != "/" else "/" + items[0].text(0)
        return None

    def get_selected_name(self):
        items = self.tree.selectedItems()
        if items:
            return items[0].text(0)
        return None

    def refresh(self):
        self.tree.clear()
        if not self._ssh.is_connected:
            return
        self.path_edit.setText(self._current_path)
        self.path_changed.emit(self._current_path)

        entries = self._ssh.list_dir(self._current_path)
        for e in entries:
            item = QTreeWidgetItem()
            item.setText(0, e['name'])
            if e['is_dir']:
                item.setText(1, "")
                item.setText(3, "文件夹")
                QTreeWidgetItem(item)
            else:
                item.setText(1, FileTreeWidget._format_size(e['size']))
                item.setText(3, Path(e['name']).suffix or "文件")
            item.setText(2, e['mtime'].strftime("%Y-%m-%d %H:%M"))
            self.tree.addTopLevelItem(item)

    def _on_item_double_clicked(self, item, column):
        name = item.text(0)
        new_path = f"{self._current_path}/{name}" if self._current_path != "/" else f"/{name}"
        if self._ssh.is_dir(new_path):
            self._current_path = new_path
            self.refresh()

    def _go_up(self):
        if self._current_path != "/":
            self._current_path = str(Path(self._current_path).parent) or "/"
            self.refresh()

    def _go_home(self):
        self._current_path = "/home/root" if self._ssh.is_dir("/home/root") else "/"
        self.refresh()

    def _on_path_entered(self):
        new_path = self.path_edit.text()
        if self._ssh.is_dir(new_path):
            self._current_path = new_path
            self.refresh()
        else:
            self.path_edit.setText(self._current_path)


class TransferThread(QThread):
    progress = Signal(int, str)
    finished = Signal(bool, str)

    def __init__(self, ssh, src, dst, is_upload=True):
        super().__init__()
        self.ssh = ssh
        self.src = src
        self.dst = dst
        self.is_upload = is_upload

    def run(self):
        try:
            if self.is_upload:
                if os.path.isdir(self.src):
                    self.ssh.upload_dir(self.src, self.dst)
                else:
                    self.ssh.upload_file(self.src, self.dst)
            else:
                if self.ssh.is_dir(self.src):
                    self.ssh.download_dir(self.src, self.dst)
                else:
                    self.ssh.download_file(self.src, self.dst)
            self.finished.emit(True, "传输完成")
        except Exception as e:
            self.finished.emit(False, f"传输失败: {e}")


class FileTransferPage(QWidget):
    def __init__(self, ssh_manager=None, parent=None):
        super().__init__(parent)
        self._ssh = ssh_manager
        self._transfer_thread = None
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(6)

        toolbar = QHBoxLayout()
        self.status_label = QLabel("就绪")
        self.status_label.setStyleSheet("color:#718096;font-size:11px;")

        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(20)
        self.progress_bar.setFormat("")
        self.progress_bar.setMaximumWidth(250)
        self.progress_bar.setStyleSheet("""
            QProgressBar { background: #e8ebf0; border: 1px solid #d0d5dd; border-radius: 3px; text-align: center; color: #555; }
            QProgressBar::chunk { background: #1a237e; border-radius: 2px; }
        """)

        toolbar.addWidget(self.status_label)
        toolbar.addStretch()
        toolbar.addWidget(self.progress_bar)
        layout.addLayout(toolbar)

        content_layout = QHBoxLayout()
        content_layout.setSpacing(6)

        self.local_widget = FileTreeWidget("本地文件", root_path=str(Path.home()))
        content_layout.addWidget(self.local_widget, 1)

        btn_layout = QVBoxLayout()
        btn_layout.addStretch()
        self.upload_btn = QPushButton("→")
        self.upload_btn.setFixedSize(40, 40)
        self.upload_btn.setToolTip("上传到设备")
        self.upload_btn.setStyleSheet(
            "QPushButton{background:#1a237e;color:white;border:none;border-radius:5px;font-size:16px;font-weight:bold;}"
            "QPushButton:hover{background:#283593;}"
        )
        self.upload_btn.clicked.connect(self._upload)
        btn_layout.addWidget(self.upload_btn)

        self.download_btn = QPushButton("←")
        self.download_btn.setFixedSize(40, 40)
        self.download_btn.setToolTip("下载到本地")
        self.download_btn.setStyleSheet(
            "QPushButton{background:#1a237e;color:white;border:none;border-radius:5px;font-size:16px;font-weight:bold;}"
            "QPushButton:hover{background:#283593;}"
        )
        self.download_btn.clicked.connect(self._download)
        btn_layout.addWidget(self.download_btn)
        btn_layout.addStretch()
        content_layout.addLayout(btn_layout)

        self.remote_widget = RemoteFileTreeWidget(self._ssh, "设备文件")
        content_layout.addWidget(self.remote_widget, 1)

        layout.addLayout(content_layout, 1)

    def set_ssh_manager(self, ssh):
        self._ssh = ssh

    def _upload(self):
        if not self._ssh or not self._ssh.is_connected:
            QMessageBox.warning(self, "提示", "请先连接设备SSH")
            return
        src = self.local_widget.get_selected_path()
        if not src:
            QMessageBox.warning(self, "提示", "请先选择本地文件")
            return
        name = self.local_widget.get_selected_name()
        dst = f"{self.remote_widget.current_path}/{name}" if self.remote_widget.current_path != "/" else f"/{name}"
        self._start_transfer(src, dst, is_upload=True)

    def _download(self):
        if not self._ssh or not self._ssh.is_connected:
            QMessageBox.warning(self, "提示", "请先连接设备SSH")
            return
        src = self.remote_widget.get_selected_path()
        if not src:
            QMessageBox.warning(self, "提示", "请先选择设备文件")
            return
        name = self.remote_widget.get_selected_name()
        dst = os.path.join(self.local_widget.current_path, name)
        self._start_transfer(src, dst, is_upload=False)

    def _start_transfer(self, src, dst, is_upload):
        self.upload_btn.setEnabled(False)
        self.download_btn.setEnabled(False)
        self._transfer_thread = TransferThread(self._ssh, src, dst, is_upload)
        self._transfer_thread.finished.connect(self._on_finished)
        self._transfer_thread.start()
        self.status_label.setText("传输中...")

    def _on_finished(self, success, msg):
        self.upload_btn.setEnabled(True)
        self.download_btn.setEnabled(True)
        self.progress_bar.setValue(100 if success else 0)
        self.status_label.setText(msg)
        if success:
            self.local_widget.refresh()
            self.remote_widget.refresh()